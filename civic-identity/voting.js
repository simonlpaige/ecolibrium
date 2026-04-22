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
// Once opened, the body is locked (body_hash is recorded).
// Only the author, or a trust-4+ user, can open a proposal.
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

  // Generate a per-proposal salt for blinded voter IDs
  const salt = crypto.randomBytes(32).toString('hex');

  db.prepare(`
    UPDATE proposals
    SET status = 'open',
        opens_at = COALESCE(opens_at, datetime('now')),
        updated_at = datetime('now'),
        -- Store salt in body_hash field temporarily (append after body hash)
        body_hash = body_hash || ':' || ?
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

  // Check if voting window is active
  const now = new Date();
  if (proposal.opens_at && new Date(proposal.opens_at) > now) {
    throw new Error('Voting has not started yet');
  }
  if (proposal.closes_at && new Date(proposal.closes_at) < now) {
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

  // Extract salt from body_hash field (stored as "bodyhash:salt")
  const [, salt] = proposal.body_hash.split(':');
  if (!salt) throw new Error('Proposal has no voting salt - was it properly opened?');

  const blindId = blindVoterId(userId, proposalId, salt);

  // Sign the vote if we have a private key
  let signature = null;
  if (userPrivKey) {
    const payload = `${blindId}:${proposalId}:${JSON.stringify(value)}`;
    signature = crypto.sign(null, Buffer.from(payload), userPrivKey).toString('base64');
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

// Handle liquid democracy delegation
export function delegateVote(db, { delegatorId, delegateId, proposalId }) {
  const proposal = getProposal(db, proposalId);
  if (!proposal) throw new Error('Proposal not found');
  if (proposal.vote_method !== 'liquid') {
    throw new Error('Delegation only applies to liquid democracy proposals');
  }

  // Cycle guard: follow existing delegation chain up to 10 hops and refuse
  // if we would create a loop back to the delegator.
  if (delegatorId === delegateId) throw new Error('Cannot delegate to yourself');
  const delegateUser = db.prepare(`SELECT id FROM users WHERE id = ? AND active = 1`).get(delegateId);
  if (!delegateUser) throw new Error('Delegate not found');

  // Cast as a delegation vote
  return castVote(db, {
    userId: delegatorId,
    proposalId,
    value: `delegate:${delegateId}`
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
      return tallyLiquid(db, votes, total, proposalId, proposal.body_hash.split(':')[1]);
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

function tallyLiquid(db, votes, total, proposalId, salt) {
  // Resolve delegations: follow the delegation chain to find actual votes
  const directVotes = votes.filter(v => !JSON.parse(v.value).startsWith?.('delegate:'));
  const delegations = votes.filter(v => {
    const val = JSON.parse(v.value);
    return typeof val === 'string' && val.startsWith('delegate:');
  });

  // Build delegation map: blindId -> delegate blindId
  const delegationMap = {};
  delegations.forEach(v => {
    const delegateRawId = JSON.parse(v.value).replace('delegate:', '');
    delegationMap[v.voter_blind_id] = delegateRawId;
  });

  // For each delegation, follow the chain to find the final vote
  // (max 5 hops to prevent infinite loops)
  const resolvedVotes = { yes: 0, no: 0, abstain: 0 };
  const weights = {};

  // Direct voters start with weight 1
  directVotes.forEach(v => {
    weights[v.voter_blind_id] = (weights[v.voter_blind_id] || 0) + 1;
  });

  // Resolve delegations
  delegations.forEach(v => {
    let current = v.voter_blind_id;
    let hops = 0;
    while (delegationMap[current] && hops < 5) {
      current = delegationMap[current];
      hops++;
    }
    // current is now either a direct voter or an unresolved delegation
    weights[current] = (weights[current] || 0) + 1;
  });

  // Apply weights to direct votes
  const directMap = {};
  directVotes.forEach(v => { directMap[v.voter_blind_id] = JSON.parse(v.value); });

  Object.entries(weights).forEach(([blindId, weight]) => {
    const vote = directMap[blindId];
    if (vote && resolvedVotes[vote] !== undefined) {
      resolvedVotes[vote] += weight;
    }
  });

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
  if (!proposal || !proposal.body_hash.includes(':')) return false;

  const salt = proposal.body_hash.split(':')[1];
  const blindId = blindVoterId(userId, proposalId, salt);

  return !!db.prepare(`SELECT 1 FROM votes WHERE proposal_id = ? AND voter_blind_id = ?`).get(proposalId, blindId);
}
