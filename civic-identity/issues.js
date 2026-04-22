// civic-identity/issues.js
// Resident issue lifecycle.
//
// A resident reports a thing (pothole, overflowing dumpster, suspicious
// activity, a promise someone made at a meeting that never happened). A
// coordinator acknowledges it, then later marks it resolved. A commitment
// from legistar can cite the originating issue so we know where it came from.
//
// Reporter identity is blinded: we store a per-issue blind id based on the
// reporting user, so the same user can file multiple issues without it
// being obvious which ones came from whom at the row level.
//
// Categories are open-vocabulary strings. Expected values: infrastructure,
// safety, neighbor, policy, meeting, other.

import crypto from 'crypto';

function newId() { return crypto.randomUUID(); }

function blindReporter(userId, issueId) {
  return crypto.createHash('sha256')
    .update(`${userId}:${issueId}:issue`).digest('hex');
}

export function createIssue(db, { reporterUserId, category, title, body, geoHint = null }) {
  if (!reporterUserId) throw new Error('Reporter required');
  if (!title || title.length < 3 || title.length > 200) {
    throw new Error('Title must be 3-200 characters');
  }
  if (!body || body.length > 5000) {
    throw new Error('Body must be 1-5000 characters');
  }
  const cat = String(category || 'other').toLowerCase();
  if (!/^[a-z_]{2,40}$/.test(cat)) throw new Error('Invalid category');

  const id = newId();
  const blind = blindReporter(reporterUserId, id);

  db.prepare(`
    INSERT INTO resident_issues
      (id, reporter_blind_id, category, title, body, geo_hint, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, 'open', datetime('now'))
  `).run(id, blind, cat, title, body, geoHint || null);

  return getIssue(db, id);
}

export function listIssues(db, { status = null, category = null, limit = 50 } = {}) {
  let q = `SELECT * FROM resident_issues`;
  const where = [];
  const params = [];
  if (status)   { where.push(`status = ?`);   params.push(status); }
  if (category) { where.push(`category = ?`); params.push(category); }
  if (where.length) q += ` WHERE ` + where.join(' AND ');
  q += ` ORDER BY created_at DESC LIMIT ?`;
  params.push(limit);
  return db.prepare(q).all(...params);
}

export function getIssue(db, id) {
  return db.prepare(`SELECT * FROM resident_issues WHERE id = ?`).get(id);
}

// Coordinator acknowledges - trust 3+ is enough to acknowledge (say "we see
// you"), trust 4+ required to resolve (close out). This matches how a real
// neighborhood association works: anyone with some standing can triage, but
// closing the loop needs a committed coordinator.
export function acknowledgeIssue(db, issueId, actorUserId) {
  const actor = db.prepare(`SELECT trust_level FROM users WHERE id = ? AND active = 1`).get(actorUserId);
  if (!actor) throw new Error('Acting user not found');
  if (actor.trust_level < 3) throw new Error('Trust level 3+ required to acknowledge issues');

  const res = db.prepare(`
    UPDATE resident_issues
    SET status = 'acknowledged',
        acknowledged_at = datetime('now'),
        acknowledged_by = ?
    WHERE id = ? AND status = 'open'
  `).run(actorUserId, issueId);
  if (res.changes === 0) throw new Error('Issue not found or not open');
  return getIssue(db, issueId);
}

export function resolveIssue(db, issueId, actorUserId, note = '') {
  const actor = db.prepare(`SELECT trust_level FROM users WHERE id = ? AND active = 1`).get(actorUserId);
  if (!actor) throw new Error('Acting user not found');
  if (actor.trust_level < 4) throw new Error('Trust level 4+ required to resolve issues');

  const res = db.prepare(`
    UPDATE resident_issues
    SET status = 'resolved',
        resolved_at = datetime('now'),
        resolved_by = ?,
        resolution_note = ?
    WHERE id = ? AND status != 'resolved'
  `).run(actorUserId, note || null, issueId);
  if (res.changes === 0) throw new Error('Issue not found or already resolved');
  return getIssue(db, issueId);
}
