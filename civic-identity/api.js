// civic-identity/api.js
// Minimal HTTP API server. No framework - pure Node.js http module.
// Designed to run on a neighborhood node (WaldoNet Raspberry Pi or similar).
//
// Routes:
//   POST /signup                    - Register anonymous user (returns one-time private key)
//   POST /verify-email              - Submit email for verification
//   POST /confirm-email             - Confirm email token
//   POST /vouch                     - Vouch for another user
//   GET  /users/:handle             - Get public user profile
//   GET  /stats                     - Node stats (user counts by trust level)
//   POST /logout                    - Destroy current session
//
//   GET  /proposals                 - List open proposals
//   GET  /proposals/:id             - Get proposal detail + current tally
//   POST /proposals                 - Create a proposal
//   POST /proposals/:id/open        - Open a draft for voting
//   POST /proposals/:id/vote        - Cast a vote
//   GET  /proposals/:id/voted       - Has the current session voted?
//   POST /proposals/:id/close       - Close voting
//   GET  /proposals/:id/verify-body - Check body_hash vs stored body
//
//   GET  /commitments               - List commitments (?status=, ?overdue=1)
//   POST /commitments               - Create a commitment (trust 3+)
//   POST /commitments/:id/resolve   - Close out a commitment (trust 4+)
//   GET  /commitments/follow-through - Per-person follow-through scores
//
//   GET  /issues                    - List resident issues
//   POST /issues                    - File an issue (auth)
//   POST /issues/:id/ack            - Acknowledge (trust 3+)
//   POST /issues/:id/resolve        - Resolve (trust 4+)
//
//   GET  /federation/peers          - List federation peers (admin)
//   POST /federation/peers          - Add a peer request (admin)
//   POST /federation/peers/request  - Inbound: a peer announces itself
//   POST /federation/peers/:node/accept - Flip pending_in to active (admin)
//   POST /federation/receive        - Receive a data bundle from a peer
//   GET  /federation/bundle/:peer   - Generate outbound bundle (admin)
//
//   GET  /audit                     - Admin audit log view
//   GET  /health                    - Node liveness

import http from 'http';
import crypto from 'crypto';
import { readFileSync } from 'fs';
import { openDB, registerAnonymous, addEmail, verifyEmail, vouchFor, getUser,
         getUserByHandle, getTrustHistory, nodeStats, createSession,
         resolveSession, destroySession } from './identity.js';
import { createProposal, openProposal, closeProposal, castVote, tallyVotes,
         listProposals, getProposal, getVoteCount, hasVoted,
         verifyBody } from './voting.js';
import { addPeer, activatePeer, getActivePeers, buildShareBundle,
         receiveBundle, ensureFederationTable } from './federation.js';
import { logAction, recentAudit } from './audit.js';
import { rateLimitCheck, LIMITS } from './rate-limit.js';
import { createIssue, listIssues, getIssue, acknowledgeIssue, resolveIssue } from './issues.js';
import { addCommitment, listCommitments, getCommitment,
         resolveCommitment, followThroughScores,
         ensureCommitmentsTable } from './commitments.js';

// ----------------------------------------------------------------
// Config (override via environment variables)
// ----------------------------------------------------------------

const PORT = parseInt(process.env.PORT || '4242');
const DB_PATH = process.env.DB_PATH || './civic-identity.db';
const NODE_SLUG = process.env.NODE_SLUG || 'local@waldonet.local';
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || null; // Required for admin routes
const ALLOW_OPEN_ADMIN = process.env.ALLOW_OPEN_ADMIN === '1';
const CORS_ORIGIN = process.env.CORS_ORIGIN || '*';
const MAX_BODY_BYTES = parseInt(process.env.MAX_BODY_BYTES || String(64 * 1024)); // 64KB default
const NODE_PRIVKEY = process.env.NODE_PRIVKEY_PATH
  ? readFileSync(process.env.NODE_PRIVKEY_PATH) : null;

if (!ADMIN_TOKEN && !ALLOW_OPEN_ADMIN) {
  console.warn('[civic-identity] WARNING: ADMIN_TOKEN is not set. Admin routes are disabled.');
  console.warn('[civic-identity] Set ADMIN_TOKEN=<secret> to enable federation routes,');
  console.warn('[civic-identity] or ALLOW_OPEN_ADMIN=1 for local dev only (never in production).');
}

// ----------------------------------------------------------------
// Init
// ----------------------------------------------------------------

const db = openDB(DB_PATH);
ensureFederationTable(db);
ensureCommitmentsTable(db);

// ----------------------------------------------------------------
// Routing
// ----------------------------------------------------------------

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const path = url.pathname;
  const method = req.method;
  const ip = callerIp(req);

  // CORS for local UI dev. Set CORS_ORIGIN=https://your-ui.example to lock down in prod.
  res.setHeader('Access-Control-Allow-Origin', CORS_ORIGIN);
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Vary', 'Origin');
  if (method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

  // Generic per-IP rate limit for every request. Specific budgets below
  // layer on top of this.
  const general = rateLimitCheck(db, `ip:${ip}`, LIMITS.generic);
  if (!general.allowed) return respond(res, 429, { error: 'Too many requests', retryMs: general.resetMs });

  // Auth: resolve session from Authorization header
  const token = (req.headers.authorization || '').replace('Bearer ', '').trim();
  const session = token ? resolveSession(db, token) : null;

  try {
    // ---- Users ----

    if (method === 'POST' && path === '/signup') {
      const rl = rateLimitCheck(db, `signup:${ip}`, LIMITS.signup);
      if (!rl.allowed) return respond(res, 429, { error: 'Signup rate limit', retryMs: rl.resetMs });
      const body = await readBody(req);
      const user = registerAnonymous(db, body.handle, NODE_SLUG);
      const sessionToken = createSession(db, user.id);
      logAction(db, { actorUserId: user.id, actorIp: ip, action: 'signup', targetType: 'user', targetId: user.id });
      // One-time private key: returned now, never stored. Client must save it.
      const { _oneTimePrivateKey, ...publicFields } = user;
      return respond(res, 201, {
        user: publicUser(publicFields),
        token: sessionToken,
        privateKey: _oneTimePrivateKey,
        notice: 'Save the private key now. It is never stored on the server and cannot be retrieved again.'
      });
    }

    if (method === 'POST' && path === '/verify-email') {
      requireAuth(session);
      const rl = rateLimitCheck(db, `email:${session.userId}`, LIMITS.verifyEmail);
      if (!rl.allowed) return respond(res, 429, { error: 'Verification rate limit', retryMs: rl.resetMs });
      const body = await readBody(req);
      if (!isValidEmail(body.email)) return respond(res, 400, { error: 'Invalid email address' });
      const verifyToken = addEmail(db, session.userId, body.email);
      // In production, email this token. Here we return it (dev mode).
      return respond(res, 200, { message: 'Verification token issued', verifyToken });
    }

    if (method === 'POST' && path === '/confirm-email') {
      requireAuth(session);
      const body = await readBody(req);
      const updated = verifyEmail(db, session.userId, body.token);
      return respond(res, 200, { user: publicUser(updated) });
    }

    if (method === 'POST' && path === '/vouch') {
      requireAuth(session);
      const body = await readBody(req);
      const updated = vouchFor(db, session.userId, body.voucheeId, body.note);
      logAction(db, { actorUserId: session.userId, actorIp: ip, action: 'vouch',
                      targetType: 'user', targetId: body.voucheeId, payload: { note: body.note || null } });
      return respond(res, 200, { user: publicUser(updated) });
    }

    if (method === 'GET' && path === '/me') {
      requireAuth(session);
      const user = getUser(db, session.userId);
      const history = getTrustHistory(db, session.userId);
      return respond(res, 200, { user: publicUser(user), trustHistory: history });
    }

    if (method === 'GET' && path.startsWith('/users/')) {
      const handle = path.split('/users/')[1];
      const user = getUserByHandle(db, handle);
      if (!user) return respond(res, 404, { error: 'User not found' });
      return respond(res, 200, { user: publicUser(user) });
    }

    if (method === 'GET' && path === '/stats') {
      return respond(res, 200, nodeStats(db));
    }

    if (method === 'POST' && path === '/logout') {
      if (token) destroySession(db, token);
      return respond(res, 200, { ok: true });
    }

    // ---- Proposals ----

    if (method === 'GET' && path === '/proposals') {
      const status = url.searchParams.get('status') || 'open';
      const category = url.searchParams.get('category') || null;
      const proposals = listProposals(db, { status, category });
      return respond(res, 200, { proposals: proposals.map(p => proposalSummary(p)) });
    }

    if (method === 'GET' && path.match(/^\/proposals\/[^/]+$/)) {
      const id = path.split('/proposals/')[1];
      const proposal = getProposal(db, id);
      if (!proposal) return respond(res, 404, { error: 'Proposal not found' });

      const tally = ['open', 'closed', 'passed', 'failed'].includes(proposal.status)
        ? tallyVotes(db, id) : null;
      const voted = session ? hasVoted(db, session.userId, id) : false;

      return respond(res, 200, {
        proposal: proposalDetail(proposal),
        tally,
        voteCount: getVoteCount(db, id),
        voted
      });
    }

    if (method === 'GET' && path.match(/^\/proposals\/[^/]+\/verify-body$/)) {
      const id = path.split('/proposals/')[1].split('/verify-body')[0];
      return respond(res, 200, verifyBody(db, id));
    }

    if (method === 'POST' && path === '/proposals') {
      requireAuth(session);
      const body = await readBody(req);
      // Cap sizes so a single POST cannot bloat the DB.
      if (body.title && body.title.length > 200) return respond(res, 400, { error: 'Title too long (max 200)' });
      if (body.body && body.body.length > 20000) return respond(res, 400, { error: 'Body too long (max 20000)' });
      const proposal = createProposal(db, {
        ...body,
        authorId: session.userId,
        authorNode: NODE_SLUG
      });
      return respond(res, 201, { proposal: proposalDetail(proposal) });
    }

    if (method === 'POST' && path.match(/^\/proposals\/[^/]+\/open$/)) {
      requireAuth(session);
      const id = path.split('/proposals/')[1].split('/open')[0];
      const proposal = openProposal(db, id, session.userId);
      logAction(db, { actorUserId: session.userId, actorIp: ip, action: 'proposal.open',
                      targetType: 'proposal', targetId: id });
      return respond(res, 200, { proposal: proposalDetail(proposal) });
    }

    if (method === 'POST' && path.match(/^\/proposals\/[^/]+\/vote$/)) {
      requireAuth(session);
      const rl = rateLimitCheck(db, `vote:${session.userId}`, LIMITS.vote);
      if (!rl.allowed) return respond(res, 429, { error: 'Vote rate limit', retryMs: rl.resetMs });
      const id = path.split('/proposals/')[1].split('/vote')[0];
      const body = await readBody(req);
      const result = castVote(db, {
        userId: session.userId,
        proposalId: id,
        value: body.value,
        userPrivKey: body.privateKey || null
      });
      return respond(res, 200, { receipt: result.receipt });
    }

    if (method === 'GET' && path.match(/^\/proposals\/[^/]+\/voted$/)) {
      requireAuth(session);
      const id = path.split('/proposals/')[1].split('/voted')[0];
      return respond(res, 200, { voted: hasVoted(db, session.userId, id) });
    }

    if (method === 'POST' && path.match(/^\/proposals\/[^/]+\/close$/)) {
      requireAuth(session);
      const id = path.split('/proposals/')[1].split('/close')[0];
      const result = closeProposal(db, id, session.userId);
      logAction(db, { actorUserId: session.userId, actorIp: ip, action: 'proposal.close',
                      targetType: 'proposal', targetId: id,
                      payload: { passed: result.passed } });
      return respond(res, 200, result);
    }

    // ---- Commitments ----

    if (method === 'GET' && path === '/commitments') {
      const status = url.searchParams.get('status');
      const overdue = url.searchParams.get('overdue') === '1';
      return respond(res, 200, { commitments: listCommitments(db, { status, overdue }) });
    }

    if (method === 'POST' && path === '/commitments') {
      requireAuth(session);
      requireTrust(db, session.userId, 3);
      const body = await readBody(req);
      const c = addCommitment(db, body);
      logAction(db, { actorUserId: session.userId, actorIp: ip, action: 'commitment.create',
                      targetType: 'commitment', targetId: c.id });
      return respond(res, 201, { commitment: c });
    }

    if (method === 'POST' && path.match(/^\/commitments\/[^/]+\/resolve$/)) {
      requireAuth(session);
      const id = path.split('/commitments/')[1].split('/resolve')[0];
      const body = await readBody(req);
      const c = resolveCommitment(db, id, session.userId, body.note);
      logAction(db, { actorUserId: session.userId, actorIp: ip, action: 'commitment.resolve',
                      targetType: 'commitment', targetId: id });
      return respond(res, 200, { commitment: c });
    }

    if (method === 'GET' && path === '/commitments/follow-through') {
      return respond(res, 200, { scores: followThroughScores(db) });
    }

    // ---- Resident issues ----

    if (method === 'GET' && path === '/issues') {
      const status = url.searchParams.get('status');
      const category = url.searchParams.get('category');
      return respond(res, 200, { issues: listIssues(db, { status, category }) });
    }

    if (method === 'GET' && path.match(/^\/issues\/[^/]+$/)) {
      const id = path.split('/issues/')[1];
      const issue = getIssue(db, id);
      if (!issue) return respond(res, 404, { error: 'Issue not found' });
      return respond(res, 200, { issue });
    }

    if (method === 'POST' && path === '/issues') {
      requireAuth(session);
      const body = await readBody(req);
      const issue = createIssue(db, { ...body, reporterUserId: session.userId });
      logAction(db, { actorUserId: session.userId, actorIp: ip, action: 'issue.create',
                      targetType: 'issue', targetId: issue.id,
                      payload: { category: issue.category } });
      return respond(res, 201, { issue });
    }

    if (method === 'POST' && path.match(/^\/issues\/[^/]+\/ack$/)) {
      requireAuth(session);
      const id = path.split('/issues/')[1].split('/ack')[0];
      const issue = acknowledgeIssue(db, id, session.userId);
      logAction(db, { actorUserId: session.userId, actorIp: ip, action: 'issue.ack',
                      targetType: 'issue', targetId: id });
      return respond(res, 200, { issue });
    }

    if (method === 'POST' && path.match(/^\/issues\/[^/]+\/resolve$/)) {
      requireAuth(session);
      const id = path.split('/issues/')[1].split('/resolve')[0];
      const body = await readBody(req);
      const issue = resolveIssue(db, id, session.userId, body.note);
      logAction(db, { actorUserId: session.userId, actorIp: ip, action: 'issue.resolve',
                      targetType: 'issue', targetId: id });
      return respond(res, 200, { issue });
    }

    // ---- Federation ----

    if (method === 'GET' && path === '/federation/peers') {
      requireAdmin(req);
      return respond(res, 200, { peers: getActivePeers(db) });
    }

    if (method === 'POST' && path === '/federation/peers') {
      requireAdmin(req);
      const body = await readBody(req);
      const peer = addPeer(db, body);
      logAction(db, { actorIp: ip, action: 'federation.peer.add',
                      targetType: 'peer', targetId: peer.peer_node });
      return respond(res, 201, { peer });
    }

    // Inbound peer request. Anyone can announce themselves; they land as
    // pending_in and require an admin accept to become active.
    if (method === 'POST' && path === '/federation/peers/request') {
      const body = await readBody(req);
      if (!body.peerNode || !body.peerPubkey) {
        return respond(res, 400, { error: 'peerNode and peerPubkey required' });
      }
      // Size-limit pubkey so we don't gulp down megabytes.
      if (typeof body.peerPubkey !== 'string' || body.peerPubkey.length > 8000) {
        return respond(res, 400, { error: 'peerPubkey invalid' });
      }
      // If we already have this peer, don't create a duplicate.
      const existing = db.prepare(`SELECT * FROM federation_peers WHERE peer_node = ?`).get(body.peerNode);
      if (existing) return respond(res, 409, { error: 'Peer already known', status: existing.status });
      // Mark pending_in (incoming request). An admin must accept.
      const id = crypto.randomUUID();
      db.prepare(`
        INSERT INTO federation_peers
          (id, peer_node, peer_name, peer_url, peer_pubkey, status, share_scope, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'pending_in', ?, datetime('now'), datetime('now'))
      `).run(
        id,
        body.peerNode,
        body.peerName || null,
        body.peerUrl || null,
        body.peerPubkey,
        JSON.stringify(body.shareScope || ['aggregated_votes', 'user_count'])
      );
      logAction(db, { actorIp: ip, action: 'federation.peer.request',
                      targetType: 'peer', targetId: body.peerNode });
      return respond(res, 202, { status: 'pending_in', message: 'Awaiting admin approval' });
    }

    if (method === 'POST' && path.match(/^\/federation\/peers\/[^/]+\/accept$/)) {
      requireAdmin(req);
      const peerNode = decodeURIComponent(path.split('/federation/peers/')[1].split('/accept')[0]);
      const body = await readBody(req);
      activatePeer(db, peerNode, body.recvScope);
      const peer = db.prepare(`SELECT * FROM federation_peers WHERE peer_node = ?`).get(peerNode);
      if (!peer) return respond(res, 404, { error: 'Peer not found' });
      logAction(db, { actorIp: ip, action: 'federation.peer.accept',
                      targetType: 'peer', targetId: peerNode });
      return respond(res, 200, { peer });
    }

    if (method === 'POST' && path === '/federation/receive') {
      const body = await readBody(req);
      const peerKey = body?.sourceNode ? `fed:${body.sourceNode}` : `fed:ip:${ip}`;
      const rl = rateLimitCheck(db, peerKey, LIMITS.federationReceive);
      if (!rl.allowed) return respond(res, 429, { error: 'Federation rate limit', retryMs: rl.resetMs });
      const result = receiveBundle(db, body);
      logAction(db, { actorIp: ip, action: 'federation.bundle.receive',
                      targetType: 'peer', targetId: body?.sourceNode || null,
                      payload: { bundleId: result.bundleId } });
      return respond(res, 200, result);
    }

    if (method === 'GET' && path.startsWith('/federation/bundle/')) {
      requireAdmin(req);
      const peerNode = decodeURIComponent(path.split('/federation/bundle/')[1]);
      if (!NODE_PRIVKEY) return respond(res, 500, { error: 'Node private key not configured' });
      const bundle = buildShareBundle(db, NODE_SLUG, NODE_PRIVKEY, peerNode);
      return respond(res, 200, bundle);
    }

    // ---- Audit log (admin) ----

    if (method === 'GET' && path === '/audit') {
      requireAdmin(req);
      const action = url.searchParams.get('action');
      const limit = Math.min(parseInt(url.searchParams.get('limit') || '200'), 1000);
      return respond(res, 200, { entries: recentAudit(db, { action, limit }) });
    }

    // ---- Health ----

    if (method === 'GET' && path === '/health') {
      return respond(res, 200, { ok: true, node: NODE_SLUG, time: new Date().toISOString() });
    }

    respond(res, 404, { error: 'Not found' });

  } catch (err) {
    const { status, message } = toPublicError(err);
    // Log the real error internally; return a scrubbed message to the caller.
    if (status >= 500) console.error(`[api:${method} ${path}]`, err);
    respond(res, status, { error: message });
  }
});

server.listen(PORT, () => {
  console.log(`Civic Identity API running on port ${PORT}`);
  console.log(`Node: ${NODE_SLUG}`);
  console.log(`DB: ${DB_PATH}`);
});

// ----------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    let size = 0;
    req.on('data', chunk => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        req.destroy();
        reject(new Error('Request body too large'));
        return;
      }
      data += chunk;
    });
    req.on('end', () => {
      try { resolve(JSON.parse(data || '{}')); }
      catch { reject(new Error('Invalid JSON body')); }
    });
    req.on('error', reject);
  });
}

function respond(res, status, data) {
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data, null, 2));
}

function requireAuth(session) {
  if (!session) throw Object.assign(new Error('Authentication required'), { statusCode: 401 });
}

function requireTrust(db, userId, level) {
  const u = db.prepare(`SELECT trust_level FROM users WHERE id = ? AND active = 1`).get(userId);
  if (!u || u.trust_level < level) {
    throw Object.assign(new Error(`Trust level ${level}+ required`), { statusCode: 403 });
  }
}

function requireAdmin(req) {
  // Fail closed: if no ADMIN_TOKEN is configured, admin routes are disabled
  // unless the operator explicitly set ALLOW_OPEN_ADMIN=1 (dev only).
  if (!ADMIN_TOKEN) {
    if (ALLOW_OPEN_ADMIN) return;
    throw Object.assign(new Error('Admin disabled: ADMIN_TOKEN not configured'), { statusCode: 503 });
  }
  const token = (req.headers.authorization || '').replace('Bearer ', '').trim();
  if (!token || !timingSafeEqualStr(token, ADMIN_TOKEN)) {
    throw Object.assign(new Error('Admin required'), { statusCode: 401 });
  }
}

function timingSafeEqualStr(a, b) {
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  if (ab.length !== bb.length) return false;
  return crypto.timingSafeEqual(ab, bb);
}

// Best-effort caller IP. Respect X-Forwarded-For only if we see it, since in
// a Pi-behind-Caddy setup we will.
function callerIp(req) {
  const xff = req.headers['x-forwarded-for'];
  if (typeof xff === 'string' && xff.length) return xff.split(',')[0].trim();
  return req.socket?.remoteAddress || null;
}

// Map internal errors into short, non-leaky public messages. The internals
// still land in the server log for operators.
function toPublicError(err) {
  const msg = err?.message || '';
  const direct = err?.statusCode;
  if (direct) return { status: direct, message: msg || 'Error' };

  // Known-shape error strings from our own modules.
  if (/required|must|invalid/i.test(msg))            return { status: 400, message: msg };
  if (/not found/i.test(msg))                         return { status: 404, message: msg };
  if (/trust level/i.test(msg))                       return { status: 403, message: msg };
  if (/already|unique constraint/i.test(msg))         return { status: 409, message: msg };
  if (/rate limit|too many/i.test(msg))               return { status: 429, message: msg };
  if (/body too large|request body too large/i.test(msg)) return { status: 413, message: msg };
  if (/not open|has closed|has not started|voting salt/i.test(msg)) return { status: 409, message: msg };

  // Anything else: SQLite or crypto bleed-through. Log internally, scrub externally.
  return { status: 500, message: 'Internal error' };
}

// Basic email shape check. Not bulletproof, just keeps junk out.
function isValidEmail(s) {
  return typeof s === 'string' && s.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);
}

// Public-safe user fields (never expose email_hash, phone_hash)
function publicUser(user) {
  if (!user) return null;
  return {
    id: user.id,
    handle: user.handle,
    trustLevel: user.trust_level,
    homeNode: user.home_node,
    pubkey: user.pubkey || null,
    createdAt: user.created_at,
    lastActive: user.last_active
  };
}

function proposalSummary(p) {
  return {
    id: p.id,
    title: p.title,
    category: p.category,
    voteMethod: p.vote_method,
    minTrust: p.min_trust,
    status: p.status,
    authorHandle: p.author_handle,
    opensAt: p.opens_at,
    closesAt: p.closes_at,
    createdAt: p.created_at
  };
}

function proposalDetail(p) {
  return {
    ...proposalSummary(p),
    body: p.body,
    federationNodes: p.federation_nodes ? JSON.parse(p.federation_nodes) : null,
    quorumRules: p.quorum_rules ? JSON.parse(p.quorum_rules) : null
  };
}
