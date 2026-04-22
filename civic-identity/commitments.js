// civic-identity/commitments.js
// API-facing wrapper around legistar_commitments.
//
// The connector creates the table and can ingest commitments from meeting
// minutes. This module exposes the read and write surface for a web UI, so
// residents can see who promised what and when, and coordinators can close
// the loop when a promise is kept.

import crypto from 'crypto';

export function ensureCommitmentsTable(db) {
  // Match what the legistar connector creates, so this module is usable
  // even on nodes that never loaded the connector.
  db.exec(`
    CREATE TABLE IF NOT EXISTS legistar_commitments (
      id               TEXT PRIMARY KEY,
      matter_id        INTEGER,
      event_id         INTEGER,
      description      TEXT NOT NULL,
      committed_by     TEXT,
      due_date         TEXT,
      status           TEXT NOT NULL DEFAULT 'open',
      created_at       TEXT NOT NULL DEFAULT (datetime('now')),
      resolved_at      TEXT,
      resolution       TEXT,
      origin_issue_id  TEXT
    );
  `);
}

export function addCommitment(db, {
  matterId = null, eventId = null,
  description, committedBy = null, dueDate = null,
  originIssueId = null
}) {
  ensureCommitmentsTable(db);
  if (!description || description.length < 5 || description.length > 2000) {
    throw new Error('Description must be 5-2000 characters');
  }
  const id = crypto.randomUUID();
  db.prepare(`
    INSERT INTO legistar_commitments
      (id, matter_id, event_id, description, committed_by, due_date, status, origin_issue_id)
    VALUES (?, ?, ?, ?, ?, ?, 'open', ?)
  `).run(id, matterId, eventId, description, committedBy, dueDate, originIssueId);
  return getCommitment(db, id);
}

export function getCommitment(db, id) {
  return db.prepare(`SELECT * FROM legistar_commitments WHERE id = ?`).get(id);
}

export function listCommitments(db, { status = null, overdue = false, limit = 100 } = {}) {
  let q = `SELECT * FROM legistar_commitments`;
  const where = [];
  const params = [];
  if (status)  { where.push(`status = ?`); params.push(status); }
  if (overdue) { where.push(`status = 'open' AND due_date IS NOT NULL AND due_date < date('now')`); }
  if (where.length) q += ` WHERE ` + where.join(' AND ');
  q += ` ORDER BY due_date ASC NULLS LAST, created_at DESC LIMIT ?`;
  params.push(limit);
  return db.prepare(q).all(...params);
}

export function resolveCommitment(db, id, actorUserId, note = '') {
  const actor = db.prepare(`SELECT trust_level FROM users WHERE id = ? AND active = 1`).get(actorUserId);
  if (!actor) throw new Error('Acting user not found');
  if (actor.trust_level < 4) throw new Error('Trust level 4+ required to resolve commitments');

  const res = db.prepare(`
    UPDATE legistar_commitments
    SET status = 'resolved', resolved_at = datetime('now'), resolution = ?
    WHERE id = ? AND status != 'resolved'
  `).run(note || null, id);
  if (res.changes === 0) throw new Error('Commitment not found or already resolved');
  return getCommitment(db, id);
}

// Per-person follow-through: for each committed_by, return promises made,
// promises kept (status='resolved'), and rolling 12-month percentage.
export function followThroughScores(db) {
  return db.prepare(`
    SELECT committed_by,
           COUNT(*) as promises_made,
           SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as promises_kept,
           SUM(CASE WHEN status = 'open' AND due_date < date('now') THEN 1 ELSE 0 END) as promises_overdue
    FROM legistar_commitments
    WHERE committed_by IS NOT NULL
      AND created_at > date('now', '-12 months')
    GROUP BY committed_by
    ORDER BY promises_made DESC
  `).all().map(r => ({
    ...r,
    kept_pct: r.promises_made > 0
      ? Math.round((r.promises_kept / r.promises_made) * 100) : 0
  }));
}
