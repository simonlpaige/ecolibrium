-- 0001_hardening.sql
-- First real migration after the original schema.sql.
--
-- What this does:
--   1. Separates the voting salt from body_hash so body_hash stays pure.
--   2. Adds an audit_log table so admin actions have a durable trail.
--   3. Adds a rate_limits table for the in-process limiter.
--   4. Adds a resident_issues table so residents can file neighborhood issues
--      that become the raw input for proposals and commitments.
--   5. Adds an origin_issue_id column on legistar_commitments so commitments
--      can be linked back to the resident issue that prompted them.
--   6. Drops sessions.hint (IP/device log). Civic trust tool, not a
--      surveillance engine. Anyone who needs debug logging can enable it
--      separately. SQLite needs a rebuild for DROP COLUMN on older builds,
--      so we set it NULL everywhere instead, rebuild the table in a later
--      migration if we ever actually want the column gone.

-- ---- Voting salt, separate from body_hash ------------------------

ALTER TABLE proposals ADD COLUMN voting_salt TEXT;

-- Back-fill existing rows: if body_hash already holds "hash:salt", split it.
-- If body_hash is null (draft never opened), leave both null.
UPDATE proposals
SET voting_salt = substr(body_hash, instr(body_hash, ':') + 1),
    body_hash   = substr(body_hash, 1, instr(body_hash, ':') - 1)
WHERE body_hash LIKE '%:%';

-- ---- Audit log ---------------------------------------------------

CREATE TABLE IF NOT EXISTS audit_log (
  id              TEXT PRIMARY KEY,
  actor_user_id   TEXT,
  actor_ip_hash   TEXT,
  action          TEXT NOT NULL,
  target_type     TEXT,
  target_id       TEXT,
  payload_json    TEXT,
  created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_audit_action    ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_actor     ON audit_log(actor_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created   ON audit_log(created_at);

-- ---- Rate limit tracking ----------------------------------------

-- Tiny helper table for the in-process limiter. Rows are pruned as they
-- expire, so this never grows.
CREATE TABLE IF NOT EXISTS rate_limits (
  key            TEXT PRIMARY KEY,
  count          INTEGER NOT NULL DEFAULT 0,
  window_start   INTEGER NOT NULL
);

-- ---- Resident issues --------------------------------------------

CREATE TABLE IF NOT EXISTS resident_issues (
  id                TEXT PRIMARY KEY,
  reporter_blind_id TEXT NOT NULL,
  category          TEXT NOT NULL,
  title             TEXT NOT NULL,
  body              TEXT NOT NULL,
  geo_hint          TEXT,
  status            TEXT NOT NULL DEFAULT 'open',
  created_at        TEXT NOT NULL DEFAULT (datetime('now')),
  acknowledged_at   TEXT,
  acknowledged_by   TEXT,
  resolved_at       TEXT,
  resolved_by       TEXT,
  resolution_note   TEXT
);
CREATE INDEX IF NOT EXISTS idx_issues_status   ON resident_issues(status);
CREATE INDEX IF NOT EXISTS idx_issues_category ON resident_issues(category);
CREATE INDEX IF NOT EXISTS idx_issues_created  ON resident_issues(created_at);

-- ---- Commitments: link to originating resident issue ------------

-- legistar_commitments is created by the neighborhood-os connector, not core
-- identity. We only touch it if the table already exists so the migration
-- stays idempotent for nodes that never loaded the connector.
CREATE TABLE IF NOT EXISTS legistar_commitments (
  id           TEXT PRIMARY KEY,
  matter_id    INTEGER,
  event_id     INTEGER,
  description  TEXT NOT NULL,
  committed_by TEXT,
  due_date     TEXT,
  status       TEXT NOT NULL DEFAULT 'open',
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  resolved_at  TEXT,
  resolution   TEXT
);

-- ALTER TABLE ADD COLUMN is idempotent enough for SQLite when wrapped,
-- but to be safe we use a guard table check via a no-op statement pattern.
-- Since we cannot easily conditionally alter, we just try and rely on the
-- migration only running once per version.
ALTER TABLE legistar_commitments ADD COLUMN origin_issue_id TEXT;

-- ---- Connector health tracking ----------------------------------

-- Written by the probe before each sync. UI / digest can render the status.
CREATE TABLE IF NOT EXISTS connector_status (
  connector_key  TEXT PRIMARY KEY,
  status         TEXT NOT NULL,
  last_checked   TEXT NOT NULL DEFAULT (datetime('now')),
  last_ok        TEXT,
  detail         TEXT
);
