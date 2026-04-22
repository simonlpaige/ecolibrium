// civic-identity/federation.js
// Federation: how two neighborhood nodes share data and run joint votes.
//
// Design principles:
//   - Each node is sovereign. No central server.
//   - Federation is bilateral - both sides opt in explicitly.
//   - Shared data is minimal by default (just aggregated counts and vote totals).
//   - Full proposal text is only shared if both nodes consent.
//   - Vote records are NEVER shared cross-node. Aggregated tallies only.
//   - All cross-node bundles are signed with the sending node's private key.

import crypto from 'crypto';

// ----------------------------------------------------------------
// Federation peer management
// ----------------------------------------------------------------

export function addPeer(db, { peerNode, peerName, peerUrl, peerPubkey, shareScope }) {
  const id = crypto.randomUUID();
  const defaultScope = JSON.stringify(['aggregated_votes', 'user_count']);

  db.prepare(`
    INSERT INTO federation_peers
      (id, peer_node, peer_name, peer_url, peer_pubkey, status, share_scope, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, 'pending_out', ?, datetime('now'), datetime('now'))
  `).run(
    id, peerNode, peerName || null, peerUrl || null, peerPubkey,
    shareScope ? JSON.stringify(shareScope) : defaultScope
  );

  return db.prepare(`SELECT * FROM federation_peers WHERE id = ?`).get(id);
}

// Called when the remote node accepts our federation request
export function activatePeer(db, peerNode, recvScope) {
  db.prepare(`
    UPDATE federation_peers
    SET status = 'active',
        recv_scope = ?,
        updated_at = datetime('now')
    WHERE peer_node = ? AND status IN ('pending_out', 'pending_in')
  `).run(recvScope ? JSON.stringify(recvScope) : null, peerNode);
}

export function suspendPeer(db, peerNode) {
  db.prepare(`
    UPDATE federation_peers SET status = 'suspended', updated_at = datetime('now')
    WHERE peer_node = ?
  `).run(peerNode);
}

export function revokePeer(db, peerNode) {
  db.prepare(`
    UPDATE federation_peers SET status = 'revoked', updated_at = datetime('now')
    WHERE peer_node = ?
  `).run(peerNode);
}

export function getActivePeers(db) {
  return db.prepare(`SELECT * FROM federation_peers WHERE status = 'active'`).all();
}

// ----------------------------------------------------------------
// Generating a shareable bundle from this node
// (What we send to peers)
// ----------------------------------------------------------------

export function buildShareBundle(db, nodeSlug, nodePrivKey, targetPeerNode) {
  const peer = db.prepare(`SELECT * FROM federation_peers WHERE peer_node = ? AND status = 'active'`).get(targetPeerNode);
  if (!peer) throw new Error('No active federation with that peer');

  const shareScope = JSON.parse(peer.share_scope || '[]');
  const bundle = {
    sourceNode: nodeSlug,
    targetNode: targetPeerNode,
    generatedAt: new Date().toISOString(),
    data: {}
  };

  // user_count: how many verified residents we have at each trust level
  if (shareScope.includes('user_count')) {
    bundle.data.userCounts = db.prepare(`
      SELECT trust_level, COUNT(*) as cnt FROM users WHERE active = 1 GROUP BY trust_level
    `).all();
  }

  // aggregated_votes: tally results for closed proposals (no individual votes)
  if (shareScope.includes('aggregated_votes')) {
    const closedProps = db.prepare(`
      SELECT id, title, category, status, closes_at FROM proposals
      WHERE status IN ('passed', 'failed') AND author_node = ?
      ORDER BY closes_at DESC LIMIT 100
    `).all(nodeSlug);

    bundle.data.proposalResults = closedProps.map(p => {
      const voteCount = db.prepare(`SELECT COUNT(*) as cnt FROM votes WHERE proposal_id = ?`).get(p.id).cnt;
      return {
        id: p.id,
        title: p.title,
        category: p.category,
        status: p.status,
        closedAt: p.closes_at,
        voteCount
        // Note: we don't share the actual tally breakdown in the default scope
        // A richer scope would include that
      };
    });
  }

  // proposal_text: full text of passed proposals (for cross-node awareness)
  if (shareScope.includes('proposal_text')) {
    bundle.data.proposals = db.prepare(`
      SELECT id, title, body, category, status, opens_at, closes_at
      FROM proposals WHERE status IN ('passed', 'failed') AND author_node = ?
      ORDER BY created_at DESC LIMIT 50
    `).all(nodeSlug);
  }

  // Sign over the whole bundle envelope, not just data, so a replay
  // with a fresh generatedAt timestamp cannot survive verification.
  const payload = JSON.stringify({
    sourceNode: bundle.sourceNode,
    targetNode: bundle.targetNode,
    generatedAt: bundle.generatedAt,
    data: bundle.data
  });
  const signature = crypto
    .sign(null, Buffer.from(payload), nodePrivKey)
    .toString('base64');

  return { ...bundle, signature };
}

// ----------------------------------------------------------------
// Receiving and verifying a bundle from a peer
// ----------------------------------------------------------------

// How stale a bundle can be (signed more than this long ago) before we reject.
// Default 24 hours. Override with FEDERATION_MAX_STALENESS_SECONDS.
const MAX_BUNDLE_STALENESS_MS = (() => {
  const n = parseInt(process.env.FEDERATION_MAX_STALENESS_SECONDS || '');
  return Number.isFinite(n) && n > 0 ? n * 1000 : 24 * 60 * 60 * 1000;
})();

export function receiveBundle(db, bundle) {
  if (!bundle || typeof bundle !== 'object') throw new Error('Invalid bundle');
  if (!bundle.sourceNode || !bundle.signature || !bundle.data || !bundle.generatedAt) {
    throw new Error('Bundle missing required fields');
  }

  // Bound bundle size so a peer cannot fill our disk.
  const raw = JSON.stringify(bundle);
  if (raw.length > 2_000_000) throw new Error('Bundle too large');

  // Reject bundles that are stale or too far in the future.
  const ts = Date.parse(bundle.generatedAt);
  if (!Number.isFinite(ts)) throw new Error('Invalid generatedAt');
  const skew = Math.abs(Date.now() - ts);
  if (skew > MAX_BUNDLE_STALENESS_MS) {
    throw new Error(`Bundle timestamp outside accepted window (${Math.round(skew / 1000)}s)`);
  }

  const peer = db.prepare(`
    SELECT * FROM federation_peers WHERE peer_node = ? AND status = 'active'
  `).get(bundle.sourceNode);

  if (!peer) throw new Error(`No active federation with ${bundle.sourceNode}`);

  // Verify signature over the full envelope (matches buildShareBundle).
  const payload = JSON.stringify({
    sourceNode: bundle.sourceNode,
    targetNode: bundle.targetNode,
    generatedAt: bundle.generatedAt,
    data: bundle.data
  });
  let valid = false;
  try {
    const pubkeyObj = crypto.createPublicKey(peer.peer_pubkey);
    valid = crypto.verify(
      null,
      Buffer.from(payload),
      pubkeyObj,
      Buffer.from(bundle.signature, 'base64')
    );
  } catch (err) {
    throw new Error(`Bundle signature verification failed: ${err.message}`);
  }

  if (!valid) throw new Error(`Bundle signature invalid from ${bundle.sourceNode}`);

  // Replay guard: reject a bundle whose exact signature we have already stored.
  const seen = db.prepare(`
    SELECT 1 FROM federation_received
    WHERE source_node = ? AND json_extract(bundle_json, '$.signature') = ?
    LIMIT 1
  `).get(bundle.sourceNode, bundle.signature);
  if (seen) throw new Error('Bundle already received (replay blocked)');

  const id = crypto.randomUUID();
  db.prepare(`
    INSERT INTO federation_received (id, source_node, received_at, bundle_json)
    VALUES (?, ?, datetime('now'), ?)
  `).run(id, bundle.sourceNode, JSON.stringify(bundle));

  return { accepted: true, bundleId: id };
}

// ----------------------------------------------------------------
// Cross-node proposals (federation-wide votes)
// ----------------------------------------------------------------

// When a proposal is flagged as federation-wide, each participating node
// runs the vote locally and then shares aggregated results.
// This function computes this node's contribution to a federation vote.

export function getFederationVoteSummary(db, proposalId) {
  const proposal = db.prepare(`SELECT * FROM proposals WHERE id = ?`).get(proposalId);
  if (!proposal) throw new Error('Proposal not found');
  if (!proposal.federation_nodes) throw new Error('Not a federation proposal');

  const voteCount = db.prepare(`SELECT COUNT(*) as cnt FROM votes WHERE proposal_id = ?`).get(proposalId).cnt;
  const binaryTally = db.prepare(`
    SELECT value, COUNT(*) as cnt FROM votes WHERE proposal_id = ? GROUP BY value
  `).all(proposalId);

  const tallySummary = {};
  binaryTally.forEach(row => {
    try { tallySummary[JSON.parse(row.value)] = row.cnt; }
    catch { tallySummary[row.value] = row.cnt; }
  });

  return {
    proposalId,
    nodeSlug: proposal.author_node,
    totalVotes: voteCount,
    tally: tallySummary,
    status: proposal.status,
    reportedAt: new Date().toISOString()
  };
}

// ----------------------------------------------------------------
// Schema migration: add the federation_received table
// (not in schema.sql to keep it separate from core identity)
// ----------------------------------------------------------------

export function ensureFederationTable(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS federation_received (
      id           TEXT PRIMARY KEY,
      source_node  TEXT NOT NULL,
      received_at  TEXT NOT NULL,
      bundle_json  TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_fed_received_node ON federation_received(source_node);
  `);
}
