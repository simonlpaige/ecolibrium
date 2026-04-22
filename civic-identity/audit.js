// civic-identity/audit.js
// Durable record of privileged actions.
//
// Every admin route, every trust promotion by a coordinator, every federation
// peer change, every proposal close should flow through logAction. The
// trust_events table only covers trust changes; audit_log is the bigger net.
//
// We hash caller IPs with a node-local salt instead of storing plaintext IPs.
// This keeps us inside the "transparency applies to power and resources, not
// to people made vulnerable by visibility" principle from VISION.md. You can
// tell that someone did X from IP bucket N-hash, but the bucket does not
// round-trip to the raw address without the salt, which lives on the node.

import crypto from 'crypto';

const IP_HASH_SALT = process.env.AUDIT_IP_SALT
  || crypto.randomBytes(16).toString('hex');

export function hashIp(ip) {
  if (!ip) return null;
  return crypto.createHmac('sha256', IP_HASH_SALT)
    .update(String(ip)).digest('hex').slice(0, 16);
}

export function logAction(db, {
  actorUserId = null,
  actorIp = null,
  action,
  targetType = null,
  targetId = null,
  payload = null
}) {
  if (!action) throw new Error('audit: action is required');
  const id = crypto.randomUUID();
  db.prepare(`
    INSERT INTO audit_log
      (id, actor_user_id, actor_ip_hash, action, target_type, target_id, payload_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
  `).run(
    id,
    actorUserId,
    actorIp ? hashIp(actorIp) : null,
    action,
    targetType,
    targetId,
    payload ? JSON.stringify(payload) : null
  );
  return id;
}

export function recentAudit(db, { limit = 200, action = null } = {}) {
  if (action) {
    return db.prepare(`
      SELECT * FROM audit_log WHERE action = ?
      ORDER BY created_at DESC LIMIT ?
    `).all(action, limit);
  }
  return db.prepare(`
    SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?
  `).all(limit);
}
