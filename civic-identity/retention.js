// civic-identity/retention.js
// Runs periodically (daily is fine) to prune data that has served its
// purpose. Keep things that serve accountability (trust_events, audit_log,
// commitments). Prune things that bloat (expired sessions, stale rate-limit
// rows, old raw social posts, old federation bundles).
//
// Defaults are conservative and overridable via env:
//   RETENTION_SOCIAL_DAYS        default 90
//   RETENTION_FEDERATION_DAYS    default 365
//   RETENTION_RATE_LIMIT_MIN     default 10
//
// This module is pure functions; the CLI wrapper is below.

import { purgeExpiredSessions } from './identity.js';
import { purgeRateLimits } from './rate-limit.js';

export function runRetention(db) {
  const socialDays = parseInt(process.env.RETENTION_SOCIAL_DAYS || '90');
  const fedDays    = parseInt(process.env.RETENTION_FEDERATION_DAYS || '365');
  const rlMin      = parseInt(process.env.RETENTION_RATE_LIMIT_MIN || '10');

  const sessionsDropped = purgeExpiredSessions(db);
  const rateLimitDropped = purgeRateLimits(db, rlMin * 60_000);

  // Social posts, if the connector is installed.
  let socialDropped = 0;
  try {
    socialDropped = db.prepare(`
      DELETE FROM social_posts WHERE posted_at < datetime('now', ?)
    `).run(`-${socialDays} days`).changes;
  } catch { /* table missing, skip */ }

  // Federation received bundles older than N days.
  let federationDropped = 0;
  try {
    federationDropped = db.prepare(`
      DELETE FROM federation_received WHERE received_at < datetime('now', ?)
    `).run(`-${fedDays} days`).changes;
  } catch { /* table missing, skip */ }

  // Superseded email-pending trust events older than 30 days. trust_events
  // is otherwise append-only and audit-critical; only the superseded ones
  // are safe to prune.
  const supersededDropped = db.prepare(`
    DELETE FROM trust_events
    WHERE method = 'email_pending_superseded'
      AND created_at < datetime('now', '-30 days')
  `).run().changes;

  return {
    sessionsDropped,
    rateLimitDropped,
    socialDropped,
    federationDropped,
    supersededDropped
  };
}
