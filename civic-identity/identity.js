// civic-identity/identity.js
// User registration, trust level management, and session handling.
// No framework dependencies. Pure Node.js + better-sqlite3 + bcrypt.
//
// Trust levels:
//   0 - Anonymous: picked a handle, nothing verified. Can read, can comment.
//   1 - Self-identified: provided name or contact info (not yet verified).
//   2 - Email-verified: clicked a link in their inbox. Can vote on surveys.
//   3 - Neighbor-vouched: a trust-4+ resident vouched for them. Full neighborhood vote access.
//   4 - Address-verified: utility bill / lease match on file. Highest local trust.
//   5 - Full resident: address-verified + at least one year of active participation.

import Database from 'better-sqlite3';
import bcrypt from 'bcrypt';
import crypto from 'crypto';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { runMigrations } from './migrations.js';

const __dir = dirname(fileURLToPath(import.meta.url));
const SCHEMA = readFileSync(join(__dir, 'schema.sql'), 'utf8');

const BCRYPT_ROUNDS = 12;

// ----------------------------------------------------------------
// DB init
// ----------------------------------------------------------------

export function openDB(dbPath) {
  const db = new Database(dbPath);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');

  // Run base schema first (idempotent - all CREATE TABLE IF NOT EXISTS),
  // then layer versioned migrations on top. The migrations runner is the
  // only path that adds columns or changes shapes from here on.
  db.exec(SCHEMA);
  runMigrations(db);

  return db;
}

// ----------------------------------------------------------------
// ID generation
// ----------------------------------------------------------------

function newId() {
  // Simple UUID v4
  return crypto.randomUUID();
}

// ----------------------------------------------------------------
// REGISTRATION
// ----------------------------------------------------------------

// Register a new anonymous user (just a handle).
// Also mints an Ed25519 keypair. Public key is stored on the user row so
// vote signatures can be verified later. The private key is returned once
// and never stored server-side. If the client loses it, signed receipts
// can still be cast, they just cannot be re-signed from this server.
export function registerAnonymous(db, handle, homeNode) {
  if (!handle || handle.length < 2 || handle.length > 30) {
    throw new Error('Handle must be 2-30 characters');
  }
  if (!/^[a-zA-Z0-9_-]+$/.test(handle)) {
    throw new Error('Handle can only contain letters, numbers, underscores, dashes');
  }

  const id = newId();

  // Ed25519 keypair. Stored as SPKI / PKCS8 PEM so crypto.createPublicKey
  // and crypto.createPrivateKey can pick them up directly.
  const { publicKey, privateKey } = crypto.generateKeyPairSync('ed25519');
  const pubkeyPem = publicKey.export({ type: 'spki', format: 'pem' });
  const privkeyPem = privateKey.export({ type: 'pkcs8', format: 'pem' });

  const stmt = db.prepare(`
    INSERT INTO users (id, handle, home_node, trust_level, pubkey, created_at)
    VALUES (?, ?, ?, 0, ?, datetime('now'))
  `);

  try {
    stmt.run(id, handle, homeNode, pubkeyPem);
  } catch (err) {
    if (err.message.includes('UNIQUE constraint')) {
      throw new Error('That handle is already taken');
    }
    throw err;
  }

  // Log the trust event
  logTrustEvent(db, {
    userId: id,
    fromLevel: 0,
    toLevel: 0,
    method: 'self_register',
    note: 'Anonymous registration'
  });

  // Attach the one-time-return private key to the returned user object.
  // Callers (like /signup) should hand it to the client once and never
  // persist it. It is NOT stored in the DB.
  const user = getUser(db, id);
  return { ...user, _oneTimePrivateKey: privkeyPem };
}

// Add email to an existing account (returns a verification token).
// The token is emailed to the user; calling verifyEmail() with it
// promotes them to trust level 2.
export function addEmail(db, userId, emailAddress) {
  const user = getUser(db, userId);
  if (!user) throw new Error('User not found');

  const normalized = String(emailAddress || '').toLowerCase().trim();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized) || normalized.length > 254) {
    throw new Error('Invalid email address');
  }
  const emailHash = bcrypt.hashSync(normalized, BCRYPT_ROUNDS);

  // Store a short-lived verification token (24h)
  const token = crypto.randomBytes(32).toString('hex');
  const tokenHash = bcrypt.hashSync(token, BCRYPT_ROUNDS);

  const fromLevel = user.trust_level;
  const toLevel = Math.max(fromLevel, 1);

  // Invalidate any prior pending verification tokens for this user so a
  // leaked older token cannot be reused.
  db.prepare(`
    UPDATE trust_events SET method = 'email_pending_superseded'
    WHERE user_id = ? AND method = 'email_pending'
  `).run(userId);

  db.prepare(`
    UPDATE users SET email_hash = ?, trust_level = ?,
    last_active = datetime('now') WHERE id = ?
  `).run(emailHash, toLevel, userId);

  logTrustEvent(db, {
    userId,
    fromLevel,
    toLevel,
    method: 'email_pending',
    proofHash: tokenHash,
    note: 'Email added, pending verification'
  });

  // Return raw token - caller is responsible for emailing this link
  return token;
}

// Verify the email token. On success, promotes user to trust_level 2.
export function verifyEmail(db, userId, token) {
  // Find the pending email_pending event for this user
  const event = db.prepare(`
    SELECT * FROM trust_events
    WHERE user_id = ? AND method = 'email_pending'
    ORDER BY created_at DESC LIMIT 1
  `).get(userId);

  if (!event) throw new Error('No pending email verification found');

  // Check token age (24h)
  const age = Date.now() - new Date(event.created_at).getTime();
  if (age > 24 * 60 * 60 * 1000) throw new Error('Verification token expired');

  if (!bcrypt.compareSync(token, event.proof_hash)) {
    throw new Error('Invalid verification token');
  }

  const user = getUser(db, userId);
  const newLevel = Math.max(user.trust_level, 2);

  db.prepare(`
    UPDATE users SET trust_level = ?, last_active = datetime('now') WHERE id = ?
  `).run(newLevel, userId);

  // Consume the token so it cannot be replayed.
  db.prepare(`
    UPDATE trust_events SET method = 'email_pending_used'
    WHERE id = ?
  `).run(event.id);

  logTrustEvent(db, {
    userId,
    fromLevel: user.trust_level,
    toLevel: newLevel,
    method: 'email_verify',
    note: 'Email verified'
  });

  return getUser(db, userId);
}

// ----------------------------------------------------------------
// VOUCHING
// ----------------------------------------------------------------

// A trust-4+ resident vouches for another user.
// Raises vouchee to trust_level 3 if they're not already higher.
export function vouchFor(db, voucherId, voucheeId, note = '') {
  const voucher = getUser(db, voucherId);
  if (!voucher) throw new Error('Voucher not found');
  if (voucher.trust_level < 4) {
    throw new Error('Only address-verified residents (trust level 4+) can vouch for others');
  }

  const vouchee = getUser(db, voucheeId);
  if (!vouchee) throw new Error('Vouchee not found');

  // Check for existing active vouch
  const existing = db.prepare(`
    SELECT * FROM vouches WHERE voucher_id = ? AND vouchee_id = ? AND active = 1
  `).get(voucherId, voucheeId);
  if (existing) throw new Error('Already vouched for this user');

  const id = newId();
  db.prepare(`
    INSERT INTO vouches (id, voucher_id, vouchee_id, note, active, created_at)
    VALUES (?, ?, ?, ?, 1, datetime('now'))
  `).run(id, voucherId, voucheeId, note);

  // Raise trust level if needed
  const newLevel = Math.max(vouchee.trust_level, 3);
  db.prepare(`
    UPDATE users SET trust_level = ? WHERE id = ?
  `).run(newLevel, voucheeId);

  logTrustEvent(db, {
    userId: voucheeId,
    fromLevel: vouchee.trust_level,
    toLevel: newLevel,
    method: 'vouched_by',
    actorUserId: voucherId,
    note: note || 'Vouched by resident'
  });

  return getUser(db, voucheeId);
}

// Revoke a vouch. Re-evaluates trust level from remaining vouches.
export function revokeVouch(db, voucherId, voucheeId) {
  db.prepare(`
    UPDATE vouches SET active = 0, revoked_at = datetime('now')
    WHERE voucher_id = ? AND vouchee_id = ? AND active = 1
  `).run(voucherId, voucheeId);

  // Re-check how many active vouches remain
  const remaining = db.prepare(`
    SELECT COUNT(*) as cnt FROM vouches WHERE vouchee_id = ? AND active = 1
  `).get(voucheeId);

  const vouchee = getUser(db, voucheeId);

  // If no remaining vouches and they were only at level 3, drop to 2
  if (remaining.cnt === 0 && vouchee.trust_level === 3) {
    db.prepare(`UPDATE users SET trust_level = 2 WHERE id = ?`).run(voucheeId);
    logTrustEvent(db, {
      userId: voucheeId,
      fromLevel: 3,
      toLevel: 2,
      method: 'revoked',
      actorUserId: voucherId,
      note: 'Last vouch revoked'
    });
  }
}

// ----------------------------------------------------------------
// ADDRESS VERIFICATION
// This is the manual / admin step. A neighborhood coordinator
// reviews proof (utility bill, lease, etc.) and marks verified.
// ----------------------------------------------------------------

export function verifyAddress(db, adminUserId, targetUserId, note = '') {
  const admin = getUser(db, adminUserId);
  if (!admin || admin.trust_level < 4) {
    throw new Error('Only trust-4+ users can verify addresses');
  }

  const target = getUser(db, targetUserId);
  if (!target) throw new Error('User not found');

  const newLevel = Math.max(target.trust_level, 4);
  db.prepare(`UPDATE users SET trust_level = ? WHERE id = ?`).run(newLevel, targetUserId);

  logTrustEvent(db, {
    userId: targetUserId,
    fromLevel: target.trust_level,
    toLevel: newLevel,
    method: 'address_check',
    actorUserId: adminUserId,
    note: note || 'Address verified by coordinator'
  });

  return getUser(db, targetUserId);
}

// ----------------------------------------------------------------
// SESSIONS
// ----------------------------------------------------------------

export function createSession(db, userId) {
  const token = crypto.randomBytes(48).toString('base64url');
  const expiresAt = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(); // 30 days

  db.prepare(`
    INSERT INTO sessions (token, user_id, created_at, expires_at)
    VALUES (?, ?, datetime('now'), ?)
  `).run(token, userId, expiresAt);

  db.prepare(`UPDATE users SET last_active = datetime('now') WHERE id = ?`).run(userId);

  return token;
}

export function resolveSession(db, token) {
  const session = db.prepare(`
    SELECT s.*, u.id as uid, u.handle, u.trust_level, u.home_node, u.active
    FROM sessions s
    JOIN users u ON s.user_id = u.id
    WHERE s.token = ? AND s.expires_at > datetime('now')
  `).get(token);

  if (!session || !session.active) return null;

  return {
    userId: session.uid,
    handle: session.handle,
    trustLevel: session.trust_level,
    homeNode: session.home_node
  };
}

export function destroySession(db, token) {
  db.prepare(`DELETE FROM sessions WHERE token = ?`).run(token);
}

// Expire old sessions (run periodically)
export function purgeExpiredSessions(db) {
  const result = db.prepare(`DELETE FROM sessions WHERE expires_at < datetime('now')`).run();
  return result.changes;
}

// ----------------------------------------------------------------
// READS
// ----------------------------------------------------------------

export function getUser(db, id) {
  return db.prepare(`SELECT * FROM users WHERE id = ?`).get(id);
}

export function getUserByHandle(db, handle) {
  return db.prepare(`SELECT * FROM users WHERE handle = ? AND active = 1`).get(handle);
}

export function getTrustHistory(db, userId) {
  return db.prepare(`
    SELECT te.*, u.handle as actor_handle
    FROM trust_events te
    LEFT JOIN users u ON te.actor_user_id = u.id
    WHERE te.user_id = ?
    ORDER BY te.created_at DESC
  `).all(userId);
}

export function getUserVouches(db, userId) {
  return db.prepare(`
    SELECT v.*, u.handle as voucher_handle, u.trust_level as voucher_trust
    FROM vouches v
    JOIN users u ON v.voucher_id = u.id
    WHERE v.vouchee_id = ? AND v.active = 1
  `).all(userId);
}

// Summary stats for a node
export function nodeStats(db) {
  const levels = db.prepare(`
    SELECT trust_level, COUNT(*) as cnt
    FROM users WHERE active = 1
    GROUP BY trust_level ORDER BY trust_level
  `).all();

  const total = db.prepare(`SELECT COUNT(*) as cnt FROM users WHERE active = 1`).get();
  const activeMonth = db.prepare(`
    SELECT COUNT(*) as cnt FROM users
    WHERE active = 1 AND last_active > datetime('now', '-30 days')
  `).get();

  return {
    total: total.cnt,
    activeMonth: activeMonth.cnt,
    byTrustLevel: levels
  };
}

// ----------------------------------------------------------------
// INTERNAL
// ----------------------------------------------------------------

function logTrustEvent(db, { userId, fromLevel, toLevel, method, actorUserId, proofHash, note }) {
  db.prepare(`
    INSERT INTO trust_events
      (id, user_id, from_level, to_level, method, actor_user_id, proof_hash, actor_note, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
  `).run(
    newId(), userId, fromLevel, toLevel, method,
    actorUserId || null, proofHash || null, note || null
  );
}
