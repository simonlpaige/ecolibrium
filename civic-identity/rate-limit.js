// civic-identity/rate-limit.js
// Tiny in-process sliding-window rate limiter.
//
// Keyed by whatever string the caller hands in: IP for signup, user id for
// vote, peer node slug for federation receive. The limiter records hits in
// the rate_limits table (so counts survive a quick restart on a Pi) and
// rolls windows by replacing the start timestamp when one expires.
//
// Not designed to survive a coordinated flood. Designed to stop a single
// misbehaving client or peer from filling the DB.

const DEFAULT_WINDOW_MS = 60_000; // 1 minute
const DEFAULT_MAX = 60;

export function rateLimitCheck(db, key, { max = DEFAULT_MAX, windowMs = DEFAULT_WINDOW_MS } = {}) {
  if (!key) return { allowed: true, remaining: max, resetMs: windowMs };

  const now = Date.now();
  const row = db.prepare(`SELECT count, window_start FROM rate_limits WHERE key = ?`).get(key);

  if (!row || now - row.window_start > windowMs) {
    // Fresh window.
    db.prepare(`
      INSERT INTO rate_limits (key, count, window_start) VALUES (?, 1, ?)
      ON CONFLICT(key) DO UPDATE SET count = 1, window_start = excluded.window_start
    `).run(key, now);
    return { allowed: true, remaining: max - 1, resetMs: windowMs };
  }

  if (row.count >= max) {
    const resetMs = Math.max(0, windowMs - (now - row.window_start));
    return { allowed: false, remaining: 0, resetMs };
  }

  db.prepare(`UPDATE rate_limits SET count = count + 1 WHERE key = ?`).run(key);
  return { allowed: true, remaining: max - row.count - 1, resetMs: windowMs - (now - row.window_start) };
}

// Purge old entries. Call from a retention job.
export function purgeRateLimits(db, olderThanMs = 10 * 60_000) {
  const cutoff = Date.now() - olderThanMs;
  return db.prepare(`DELETE FROM rate_limits WHERE window_start < ?`).run(cutoff).changes;
}

// Preset budgets. Tune via env if needed.
export const LIMITS = {
  signup:            { max: parseInt(process.env.RL_SIGNUP_MAX || '5'),   windowMs: 60 * 60_000 }, // 5/hour/IP
  vote:              { max: parseInt(process.env.RL_VOTE_MAX || '60'),     windowMs: 60_000 },      // 60/min/user
  verifyEmail:       { max: parseInt(process.env.RL_EMAIL_MAX || '5'),     windowMs: 60 * 60_000 }, // 5/hour/user
  federationReceive: { max: parseInt(process.env.RL_FED_MAX || '10'),      windowMs: 60_000 },      // 10/min/peer
  generic:           { max: parseInt(process.env.RL_GENERIC_MAX || '120'), windowMs: 60_000 }       // 120/min/IP
};
