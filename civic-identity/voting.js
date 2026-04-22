// civic-identity/voting.js
// Proposal creation, voting, tallying, and result verification.
// Works with identity.js for trust gating.
//
// Voting methods supported:
//   binary   - yes / no / abstain
//   approval - vote for any/all options you support
//   ranked   - rank options 1, 2, 3... (instant runoff ready)
//   score    - give each option a score 1-5
//   liquid   - yes/no or delegate to another user
//
// Privacy model:
//   - We blind voter IDs so we can prove "each person voted once"
//     without recording who voted for what.
//   - Signatures let voters prove (to themselves) that their vote was counted.
//   - Tallies are public. Individual vote-to-voter mapping is not.

import crypto from 'crypto';
import Database from 'better-sqlite3';

// ----------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------

function newId() {
  return crypto.randomUUID();
}

// Blind a voter ID for a specific proposal.
// Using HMAC-SHA256 with the proposal's salt so the same user
// gets a different blind ID on every proposal.
function blindVoterId(userId, proposalId, salt) {
  return crypto
    .createHmac('sha256', salt)
    .update(`${userId}:${proposalId}`)
    .digest('hex');
}

// Hash the proposal body so we can detect retroactive edits.
function hashBody(body) {
  return crypto.createHash('sha256').update(body).digest('hex');
}

// Parse a SQLite datetime('now') string, which is "YYYY-MM-DD HH:MM:SS" in
// UTC, as an actual Date. The bare form is interpreted as local time by
// Date, which is subtly wrong.
function parseSqliteUtc(s) {
  if (!s) return null;
  // Already ISO (trailing Z or explicit offset)? trust it.
  if (/[Zz]$|[+\-]\d{2}:?\d{2}$/.test(s)) return new Date(s);
  // Convert "YYYY-MM-DD HH:MM:SS" -> "YYYY-MM-DDTHH:MM:SSZ"
  return new Date(s.replace(' ', 'T') + 'Z');
}

// Read the per-proposal voting salt. Prefer the dedicated voting_salt
// column (post-migration 0001). Fall back to the legacy "body_hash:salt"
// packing only if the new column is unpopulated, so old rows still work.
function getProposalSalt(proposal) {
  if (proposal.voting_salt) return proposal.voting_salt;
  if (proposal.body_hash && proposal.body_hash.includes(':')) {
    return proposal.body_hash.split(':')[1];
  }
  return null;
}

// Verify that a proposal body still matches the hash recorded when it was
// opened. Exported so an admin route can surface tampering.
export function verifyBody(db, proposalId) {
  const proposal = getProposal(db, proposalId);
  if (!proposal) throw new Error('Proposal not found');
  if (!proposal.body_hash) return { verified: false, reason: 'no body_hash recorded' };
  // Strip legacy ":salt" suffix if present for back-compat.
  const pureHash = proposal.body_hash.includes(':')
    ? proposal.body_hash.split(':')[0]
    : proposal.body_hash;
  const current = hashBody(proposal.body);
  return { verified: current === pureHash, expected: pureHash, current };
}

// ----------------------------------------------------------------
// PROPOSALS
// ----------------------------------------------------------------

export function createProposal(db, {
  authorId,
  authorNode,
  title,
  body,
  category = 'policy',
  minTrust = 2,
  voteMethod = 'binary',
  quorumRules = null,
  defaultDelegates = null,
  federationNodes = null,
  opensAt = null,
  closesAt = null,
  options = []   // Array of {label, description} for approval/ranked/score
}) {
  if (!title || title.length < 5) throw new Error('Title too short');
  if (!body || body.length < 20) throw new Error('Proposal body too short');
  if (!['binary', 'approval', 'ranked', 'score', 'liquid'].includes(voteMethod)) {
    throw new Error('Invalid vote method');
  }
  if (!['policy', 'budget', 'board', 'priority', 'federation', 'constitutional', 'recall', 'survey'].includes(category)) {
    throw new Error('Invalid category');
  }

  const id = newId();
  const bodyHash = hashBody(body);

  db.prepare(`
    INSERT INTO proposals
      (id, author_id, author_node, title, body, category, min_trust,
       vote_method, default_delegates, quorum_rules, federation_nodes,
       opens_at, closes_at, created_at, updated_at, body_hash, status)
    VALUES
      (?, ?, ?, ?, ?, ?, ?,
       ?, ?, ?, ?,
       ?, ?, datetime('now'), datetime('now'), ?, 'draft')
  `).run(
    id, authorId, authorNode, title, body, category, minTrust,
    voteMethod,
    defaultDelegates ? JSON.stringify(defaultDelegates) : null,
    quorumRules ? JSON.stringify(quorumRules) : null,
    federationNodes ? JSON.stringify(federationNodes) : null,
    opensAt, closesAt,
    bodyHash
  );

  // Add options for multi-choice methods
  if (['approval', 'ranked', 'score'].includes(voteMethod) && options.length > 0) {
    const optStmt = db.prepare(`
      INSERT INTO vote_options (id, proposal_id, label, description, sort_order)
      VALUES (?, ?, ?, ?, ?)
    `);
    options.forEach((opt, i) => {
      optStmt.run(newId(), id, opt.label, opt.description || null, i);
    });
  }

  return getProposal(db, id);
}

// Open a draft proposal for voting.
// Once opened, the body is locked (body_hash stays pure and the per-proposal
// voting_salt is stored separately). Only the author, or a trust-4+ user,
// can open a proposal.
export function openProposal(db, proposalId, actingUserId) {
  const proposal = getProposal(db, proposalId);
  if (!proposal) throw new Error('Proposal not found');
  if (proposal.status !== 'draft') throw new Error('Can only open draft proposals');

  if (actingUserId) {
    const actor = db.prepare(`SELECT * FROM users WHERE id = ? AND active = 1`).get(actingUserId);
    if (!actor) throw new Error('Acting user not found');
    const isAuthor = actor.id === proposal.author_id;
    const isCoordinator = actor.trust_level >= 4;
    if (!isAuthor && !isCoordinator) {
      throw new Error('Only the author or a trust-4+ coordinator can open a proposal');
    }
  }

  // Generate a per-proposal salt for blinded voter IDs. Stored in its own
  // column so body_hash stays a pure hash of the body and can still be used
  // to detect retroactive edits.
  const salt = crypto.randomBytes(32).toString('hex');

  db.prepare(`
    UPDATE proposals
    SET status = 'open',
        opens_at = COALESCE(opens_at, datetime('now')),
        updated_at = datetime('now'),
        voting_salt = ?
    WHERE id = ?
  `).run(salt, proposalId);

  return getProposal(db, proposalId);
}

// Close voting manually (or it closes automatically when closes_at passes).
// Only the author, or a trust-4+ user, can close a proposal.
export function closeProposal(db, proposalId, actingUserId = null) {
  const proposal = getProposal(db, proposalId);
  if (!proposal) throw new Error('Proposal not found');
  if (proposal.status !== 'open') throw new Error('Proposal is not open');

  if (actingUserId) {
    const actor = db.prepare(`SELECT * FROM users WHERE id = ? AND active = 1`).get(actingUserId);
    if (!actor) throw new Error('Acting user not found');
    const isAuthor = actor.id === proposal.author_id;
    const isCoordinator = actor.trust_level >= 4;
    if (!isAuthor && !isCoordinator) {
      throw new Error('Only the author or a trust-4+ coordinator can close a proposal');
    }
  }

  const tally = tallyVotes(db, proposalId);
  const passed = determineOutcome(proposal, tally);

  db.prepare(`
    UPDATE proposals
    SET status = ?,
        closes_at = COALESCE(closes_at, datetime('now')),
        updated_at = datetime('now')
    WHERE id = ?
  `).run(passed ? 'passed' : 'failed', proposalId);

  return { proposal: getProposal(db, proposalId), tally, passed };
}

// ----------------------------------------------------------------
// CASTING VOTES
// ----------------------------------------------------------------

export function castVote(db, { userId, proposalId, value, userPrivKey = null }) {
  const proposal = getProposal(db, proposalId);
  if (!proposal) throw new Error('Proposal not found');
  if (proposal.status !== 'open') throw new Error('This proposal is not open for voting');

  // Check if voting window is active. SQLite's datetime('now') returns a
  // naive "YYYY-MM-DD HH:MM:SS" string in UTC, but the JS Date constructor
  // parses naive strings as local time. Explicitly treat the stored times
  // as UTC so a timezone-offset from local does not lock anyone out.
  const now = new Date();
  if (proposal.opens_at && parseSqliteUtc(proposal.opens_at) > now) {
    throw new Error('Voting has not started yet');
  }
  if (proposal.closes_at && parseSqliteUtc(proposal.closes_at) < now) {
    throw new Error('Voting has closed');
  }

  // Get the user and check trust level
  const user = db.prepare(`SELECT * FROM users WHERE id = ? AND active = 1`).get(userId);
  if (!user) throw new Error('User not found');
  if (user.trust_level < proposal.min_trust) {
    throw new Error(
      `This vote requires trust level ${proposal.min_trust}. ` +
      `Your trust level is ${user.trust_level}. ` +
      `Verify your email or get vouched by a neighbor to participate.`
    );
  }

  // Validate the vote value for the method
  validateVoteValue(proposal.vote_method, value);

  const salt = getProposalSalt(proposal);
  if (!salt) throw new Error('Proposal has no voting salt - was it properly opened?');

  const blindId = blindVoterId(userId, proposalId, salt);

  // Sign the vote if the caller provided a private key. The client holds the
  // private key (returned once at signup); we verify here against the user's
  // stored pubkey so a bad signature is rejected instead of silently stored.
  let signature = null;
  if (userPrivKey) {
    const payload = `${blindId}:${proposalId}:${JSON.stringify(value)}`;
    try {
      const keyObj = typeof userPrivKey === 'string'
        ? crypto.createPrivateKey(userPrivKey) : userPrivKey;
      signature = crypto.sign(null, Buffer.from(payload), keyObj).toString('base64');
      if (user.pubkey) {
        const ok = crypto.verify(
          null, Buffer.from(payload),
          crypto.createPublicKey(user.pubkey),
          Buffer.from(signature, 'base64')
        );
        if (!ok) throw new Error('Vote signature does not match your registered public key');
      }
    } catch (err) {
      throw new Error(`Vote signature failed: ${err.message}`);
    }
  }

  try {
    db.prepare(`
      INSERT INTO votes (id, proposal_id, voter_blind_id, value, signature, cast_at)
      VALUES (?, ?, ?, ?, ?, datetime('now'))
    `).run(newId(), proposalId, blindId, JSON.stringify(value), signature);
  } catch (err) {
    if (err.message.includes('UNIQUE constraint')) {
      throw new Error('You have already voted on this proposal');
    }
    throw err;
  }

  return {
    receipt: {
      blindId,
      proposalId,
      value,
      signature,
      castAt: new Date().toISOString()
    }
  };
}

// Handle liquid democracy delegation.
//
// The trick: we store the delegation in blind-space. The vote value is
// `delegate:<blind_id_of_delegate>`, where the delegate's blind_id is
// computed with the same per-proposal salt as every other blinded voter
// on this proposal. That way tallyLiquid can walk the chain in blind-space
// without ever touching raw user ids and the resolver actually works.
export function delegateVote(db, { delegatorId, delegateId, proposalId }) {
  const proposal = getProposal(db, proposalId);
  if (!proposal) throw new Error('Proposal not found');
  if (proposal.vote_method !== 'liquid') {
    throw new Error('Delegation only applies to liquid democracy proposals');
  }
  if (delegatorId === delegateId) throw new Error('Cannot delegate to yourself');

  const delegateUser = db.prepare(`SELECT id FROM users WHERE id = ? AND active = 1`).get(delegateId);
  if (!delegateUser) throw new Error('Delegate not found');

  const salt = getProposalSalt(proposal);
  if (!salt) throw new Error('Proposal has no voting salt - was it properly opened?');

  const delegateBlindId = blindVoterId(delegateId, proposalId, salt);

  return castVote(db, {
    userId: delegatorId,
    proposalId,
    value: `delegate:${delegateBlindId}`
  });
}

// ----------------------------------------------------------------
// TALLYING
// ----------------------------------------------------------------

export function tallyVotes(db, proposalId) {
  const proposal = getProposal(db, proposalId);
  if (!proposal) throw new Error('Proposal not found');

  const votes = db.prepare(`SELECT * FROM votes WHERE proposal_id = ?`).all(proposalId);
  const options = db.prepare(`SELECT * FROM vote_options WHERE proposal_id = ? ORDER BY sort_order`).all(proposalId);

  const total = votes.length;

  switch (proposal.vote_method) {
    case 'binary':
      return tallyBinary(votes, total);
    case 'approval':
      return tallyApproval(votes, options, total);
    case 'ranked':
      return tallyRanked(votes, options, total);
    case 'score':
      return tallyScore(votes, options, total);
    case 'liquid':
      return tallyLiquid(db, votes, total, proposalId, getProposalSalt(proposal));
    default:
      throw new Error('Unknown vote method');
  }
}

function tallyBinary(votes, total) {
  const counts = { yes: 0, no: 0, abstain: 0 };
  votes.forEach(v => {
    const val = JSON.parse(v.value);
    if (counts[val] !== undefined) counts[val]++;
  });
  return {
    method: 'binary',
    total,
    counts,
    yesPercent: total > 0 ? Math.round((counts.yes / total) * 100) : 0
  };
}

function tallyApproval(votes, options, total) {
  const counts = {};
  options.forEach(o => { counts[o.id] = 0; });

  votes.forEach(v => {
    const selected = JSON.parse(v.value);
    if (Array.isArray(selected)) {
      selected.forEach(optId => {
        if (counts[optId] !== undefined) counts[optId]++;
      });
    }
  });

  const ranked = options
    .map(o => ({ ...o, votes: counts[o.id] || 0 }))
    .sort((a, b) => b.votes - a.votes);

  return { method: 'approval', total, results: ranked };
}

function tallyRanked(votes, options, total) {
  // Instant runoff voting (IRV)
  const ballots = votes.map(v => JSON.parse(v.value));
  const optionIds = options.map(o => o.id);

  let remaining = [...optionIds];
  const rounds = [];

  while (remaining.length > 1) {
    // Count first-choice votes for remaining candidates
    const firstChoiceCounts = {};
    remaining.forEach(id => { firstChoiceCounts[id] = 0; });

    ballots.forEach(ballot => {
      // Find the first choice still in the race
      const choice = ballot.find(id => remaining.includes(id));
      if (choice) firstChoiceCounts[choice]++;
    });

    const roundTotal = Object.values(firstChoiceCounts).reduce((a, b) => a + b, 0);
    rounds.push({ ...firstChoiceCounts });

    // Check majority
    const winner = remaining.find(id => firstChoiceCounts[id] > roundTotal / 2);
    if (winner) {
      return { method: 'ranked', total, winner, rounds };
    }

    // Eliminate lowest
    const lowestCount = Math.min(...Object.values(firstChoiceCounts));
    const toEliminate = remaining.find(id => firstChoiceCounts[id] === lowestCount);
    remaining = remaining.filter(id => id !== toEliminate);
  }

  return { method: 'ranked', total, winner: remaining[0] || null, rounds };
}

function tallyScore(votes, options, total) {
  const sums = {};
  const counts = {};
  options.forEach(o => { sums[o.id] = 0; counts[o.id] = 0; });

  votes.forEach(v => {
    const scores = JSON.parse(v.value);
    Object.entries(scores).forEach(([optId, score]) => {
      if (sums[optId] !== undefined) {
        sums[optId] += Number(score);
        counts[optId]++;
      }
    });
  });

  const results = options.map(o => ({
    ...o,
    totalScore: sums[o.id] || 0,
    voteCount: counts[o.id] || 0,
    avgScore: counts[o.id] > 0 ? (sums[o.id] / counts[o.id]).toFixed(2) : 0
  })).sort((a, b) => b.totalScore - a.totalScore);

  return { method: 'score', total, results };
}

function tallyLiquid(db, votes, total, proposalId /* salt unused but kept for signature */) {
  // All ids in this resolver are BLIND ids. delegateVote now stores
  // `delegate:<delegate_blind_id>`, matching the voter_blind_id column,
  // so the delegation chain can be walked without leaking raw user ids.
  const directVotes = [];
  const delegations = [];

  for (const v of votes) {
    let val;
    try { val = JSON.parse(v.value); } catch { continue; }
    if (typeof val === 'string' && val.startsWith('delegate:')) {
      delegations.push({ from: v.voter_blind_id, to: val.slice('delegate:'.length) });
    } else {
      directVotes.push({ blindId: v.voter_blind_id, vote: val });
    }
  }

  // Build the delegation map in blind-space.
  const delegationMap = Object.fromEntries(delegations.map(d => [d.from, d.to]));

  // Direct voters start with weight 1.
  const weights = {};
  for (const d of directVotes) {
    weights[d.blindId] = (weights[d.blindId] || 0) + 1;
  }

  // Walk each delegation chain up to 10 hops and credit its weight to the
  // terminal direct voter (if any). Loops are broken with a visited set.
  for (const d of delegations) {
    let current = d.to;
    const visited = new Set([d.from]);
    let hops = 0;
    while (delegationMap[current] && hops < 10 && !visited.has(current)) {
      visited.add(current);
      current = delegationMap[current];
      hops++;
    }
    // If the chain terminates on a direct voter, add weight there.
    // If it terminates on an unresolved blind id (delegated to someone who
    // never voted) the weight is dropped, which matches liquid democracy
    // norms: delegation without a downstream vote does not count.
    if (directVotes.some(v => v.blindId === current)) {
      weights[current] = (weights[current] || 0) + 1;
    }
  }

  // Apply weights to direct votes.
  const resolvedVotes = { yes: 0, no: 0, abstain: 0 };
  for (const d of directVotes) {
    const w = weights[d.blindId] || 1;
    if (resolvedVotes[d.vote] !== undefined) resolvedVotes[d.vote] += w;
  }

  const resolvedTotal = Object.values(resolvedVotes).reduce((a, b) => a + b, 0);

  return {
    method: 'liquid',
    totalParticipants: total,
    resolvedVotes: resolvedTotal,
    directVoters: directVotes.length,
    delegators: delegations.length,
    counts: resolvedVotes,
    yesPercent: resolvedTotal > 0 ? Math.round((resolvedVotes.yes / resolvedTotal) * 100) : 0
  };
}

// ----------------------------------------------------------------
// QUORUM CHECK
// ----------------------------------------------------------------

export function checkQuorum(db, proposalId, eligibleVoterCount) {
  const proposal = getProposal(db, proposalId);
  if (!proposal || !proposal.quorum_rules) return { met: true, required: null, actual: 0 };

  const rules = JSON.parse(proposal.quorum_rules);
  const voteCount = db.prepare(`SELECT COUNT(*) as cnt FROM votes WHERE proposal_id = ?`).get(proposalId).cnt;

  const minVotes = rules.min_votes || 0;
  const minPct = rules.min_pct_eligible || 0;
  const required = Math.max(minVotes, Math.ceil(eligibleVoterCount * minPct));

  return {
    met: voteCount >= required,
    required,
    actual: voteCount,
    eligibleCount: eligibleVoterCount
  };
}

// ----------------------------------------------------------------
// OUTCOME DETERMINATION
// ----------------------------------------------------------------

function determineOutcome(proposal, tally) {
  switch (proposal.vote_method) {
    case 'binary':
    case 'liquid':
      // Simple majority yes > no (excluding abstains)
      return tally.counts.yes > tally.counts.no;
    case 'approval':
    case 'ranked':
    case 'score':
      // These don't have a simple pass/fail - outcome is the ranking
      return true;
    default:
      return false;
  }
}

// ----------------------------------------------------------------
// VALIDATION
// ----------------------------------------------------------------

function validateVoteValue(method, value) {
  switch (method) {
    case 'binary':
      if (!['yes', 'no', 'abstain'].includes(value)) {
        throw new Error('Binary vote must be yes, no, or abstain');
      }
      break;
    case 'approval':
      if (!Array.isArray(value) || value.length === 0) {
        throw new Error('Approval vote must be a non-empty array of option ids');
      }
      if (!value.every(v => typeof v === 'string' && v.length <= 100)) {
        throw new Error('Approval vote option ids must be strings');
      }
      if (new Set(value).size !== value.length) {
        throw new Error('Approval vote cannot contain duplicate options');
      }
      break;
    case 'ranked':
      if (!Array.isArray(value) || value.length === 0) {
        throw new Error('Ranked vote must be a non-empty array of option ids in order');
      }
      if (!value.every(v => typeof v === 'string' && v.length <= 100)) {
        throw new Error('Ranked vote option ids must be strings');
      }
      if (new Set(value).size !== value.length) {
        throw new Error('Ranked vote cannot repeat an option');
      }
      break;
    case 'score':
      if (typeof value !== 'object' || value === null || Array.isArray(value)) {
        throw new Error('Score vote must be an object {optionId: score}');
      }
      for (const [k, v] of Object.entries(value)) {
        if (typeof k !== 'string' || k.length > 100) throw new Error('Score option id invalid');
        const n = Number(v);
        if (!Number.isFinite(n) || n < 0 || n > 10) {
          throw new Error('Score values must be numbers between 0 and 10');
        }
      }
      break;
    case 'liquid':
      if (typeof value === 'string' && value.startsWith('delegate:')) break;
      if (!['yes', 'no', 'abstain'].includes(value)) {
        throw new Error('Liquid vote must be yes/no/abstain or delegate:<userId>');
      }
      break;
    default:
      throw new Error('Unknown vote method');
  }
}

// ----------------------------------------------------------------
// READS
// ----------------------------------------------------------------

export function getProposal(db, id) {
  return db.prepare(`SELECT * FROM proposals WHERE id = ?`).get(id);
}

export function listProposals(db, { status = null, category = null, limit = 50, offset = 0 } = {}) {
  let query = `SELECT p.*, u.handle as author_handle FROM proposals p JOIN users u ON p.author_id = u.id`;
  const params = [];
  const conditions = [];

  if (status) { conditions.push(`p.status = ?`); params.push(status); }
  if (category) { conditions.push(`p.category = ?`); params.push(category); }
  if (conditions.length) query += ` WHERE ` + conditions.join(' AND ');
  query += ` ORDER BY p.created_at DESC LIMIT ? OFFSET ?`;
  params.push(limit, offset);

  return db.prepare(query).all(...params);
}

export function getVoteCount(db, proposalId) {
  return db.prepare(`SELECT COUNT(*) as cnt FROM votes WHERE proposal_id = ?`).get(proposalId).cnt;
}

// Check if a user has voted (uses blinded check - doesn't reveal their vote)
export function hasVoted(db, userId, proposalId) {
  const proposal = getProposal(db, proposalId);
  if (!proposal) return false;

  const salt = getProposalSalt(proposal);
  if (!salt) return false;

  const blindId = blindVoterId(userId, proposalId, salt);
  return !!db.prepare(`SELECT 1 FROM votes WHERE proposal_id = ? AND voter_blind_id = ?`).get(proposalId, blindId);
}
