// connectors/legistar.js
// Kansas City legislative record connector via the Legistar Web API.
// API is public, no key required.
// Confirmed working as of April 2026: webapi.legistar.com/v1/kansascity/

import crypto from 'crypto';

const BASE = 'https://webapi.legistar.com/v1/kansascity';

// ----------------------------------------------------------------
// Core fetch
// ----------------------------------------------------------------

async function legistarGet(path, params = {}) {
  const url = new URL(`${BASE}${path}`);
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  const res = await fetch(url.toString(), { headers: { 'Accept': 'application/json' } });
  if (!res.ok) throw new Error(`Legistar ${path}: HTTP ${res.status}`);
  return res.json();
}

// ----------------------------------------------------------------
// Committees / Bodies
// ----------------------------------------------------------------

// Get all active committees. Returns 50+ bodies including:
// Council (138), Finance & Governance (140), City Plan Commission, etc.
export async function getBodies() {
  return legistarGet('/bodies', { '$filter': 'BodyActiveFlag eq 1' });
}

// ----------------------------------------------------------------
// Meetings / Events
// ----------------------------------------------------------------

// Get upcoming meetings, optionally filtered to a specific body
export async function getUpcomingMeetings({ bodyId = null, limit = 20 } = {}) {
  const params = {
    '$orderby': 'EventDate desc',
    '$top': limit
  };
  if (bodyId) params['$filter'] = `EventBodyId eq ${bodyId}`;
  return legistarGet('/events', params);
}

// Get recent meetings (past 90 days by default)
export async function getRecentMeetings({ days = 90, bodyId = null } = {}) {
  const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
  const filters = [`EventDate ge datetime'${since}'`];
  if (bodyId) filters.push(`EventBodyId eq ${bodyId}`);

  return legistarGet('/events', {
    '$filter': filters.join(' and '),
    '$orderby': 'EventDate desc',
    '$top': 100
  });
}

// Get agenda items for a specific meeting
export async function getMeetingAgenda(eventId) {
  return legistarGet(`/events/${eventId}/eventitems`, {
    '$expand': 'EventItemMatterAttachments'
  });
}

// ----------------------------------------------------------------
// Legislation / Matters
// ----------------------------------------------------------------

// Search matters (ordinances, resolutions, etc.) by keyword
// Escapes single quotes in the keyword so callers cannot break the OData filter.
export async function searchMatters(keyword, { limit = 50 } = {}) {
  const safe = String(keyword || '').replace(/'/g, "''");
  return legistarGet('/matters', {
    '$filter': `substringof('${safe}', MatterTitle)`,
    '$orderby': 'MatterIntroDate desc',
    '$top': limit
  });
}

// Get recent legislation
export async function getRecentMatters({ days = 90, limit = 100 } = {}) {
  const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
  return legistarGet('/matters', {
    '$filter': `MatterIntroDate ge datetime'${since}'`,
    '$orderby': 'MatterIntroDate desc',
    '$top': limit
  });
}

// Get the vote history for a specific matter
export async function getMatterHistory(matterId) {
  return legistarGet(`/matters/${matterId}/histories`);
}

// Get attachments (PDFs, agenda packets) for a matter
export async function getMatterAttachments(matterId) {
  return legistarGet(`/matters/${matterId}/attachments`);
}

// ----------------------------------------------------------------
// Sync: store meetings and matters in the local DB
// ----------------------------------------------------------------

export function ensureLegistarTables(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS legistar_events (
      id           INTEGER PRIMARY KEY,
      body_id      INTEGER,
      body_name    TEXT,
      event_date   TEXT,
      location     TEXT,
      agenda_url   TEXT,
      minutes_url  TEXT,
      raw_json     TEXT,
      synced_at    TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS legistar_matters (
      id              INTEGER PRIMARY KEY,
      matter_type     TEXT,
      title           TEXT,
      status          TEXT,
      intro_date      TEXT,
      final_date      TEXT,
      sponsors        TEXT,
      body_name       TEXT,
      raw_json        TEXT,
      synced_at       TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS legistar_commitments (
      id           TEXT PRIMARY KEY,
      matter_id    INTEGER REFERENCES legistar_matters(id),
      event_id     INTEGER REFERENCES legistar_events(id),
      description  TEXT NOT NULL,
      committed_by TEXT,
      due_date     TEXT,
      status       TEXT NOT NULL DEFAULT 'open',
      created_at   TEXT NOT NULL DEFAULT (datetime('now')),
      resolved_at  TEXT,
      resolution   TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_le_events_date ON legistar_events(event_date);
    CREATE INDEX IF NOT EXISTS idx_le_matters_intro ON legistar_matters(intro_date);
    CREATE INDEX IF NOT EXISTS idx_le_matters_status ON legistar_matters(status);
    CREATE INDEX IF NOT EXISTS idx_le_commitments_status ON legistar_commitments(status);
  `);
}

export async function syncRecentMatters(db, { days = 7 } = {}) {
  ensureLegistarTables(db);
  const matters = await getRecentMatters({ days, limit: 200 });

  const stmt = db.prepare(`
    INSERT OR REPLACE INTO legistar_matters
      (id, matter_type, title, status, intro_date, final_date, sponsors, body_name, raw_json, synced_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
  `);

  const insert = db.transaction((items) => {
    for (const m of items) {
      stmt.run(
        m.MatterId, m.MatterTypeName, m.MatterTitle, m.MatterStatusName,
        m.MatterIntroDate, m.MatterFinalDate,
        m.MatterSponsors?.map(s => s.MatterSponsorName).join(', ') || null,
        m.MatterBodyName, JSON.stringify(m)
      );
    }
  });

  insert(matters);
  return { synced: matters.length };
}

export async function syncRecentEvents(db, { days = 14 } = {}) {
  ensureLegistarTables(db);
  const events = await getRecentMeetings({ days });

  const stmt = db.prepare(`
    INSERT OR REPLACE INTO legistar_events
      (id, body_id, body_name, event_date, location, agenda_url, minutes_url, raw_json, synced_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
  `);

  const insert = db.transaction((items) => {
    for (const e of items) {
      stmt.run(
        e.EventId, e.EventBodyId, e.EventBodyName, e.EventDate,
        e.EventLocation, e.EventAgendaFile, e.EventMinutesFile,
        JSON.stringify(e)
      );
    }
  });

  insert(events);
  return { synced: events.length };
}

// ----------------------------------------------------------------
// Commitment tracker
// ----------------------------------------------------------------

// Manually add a tracked commitment (from meeting minutes)
export function addCommitment(db, { matterId, eventId, description, committedBy, dueDate }) {
  ensureLegistarTables(db);
  const id = crypto.randomUUID?.() ||
    Math.random().toString(36).slice(2) + Date.now().toString(36);

  db.prepare(`
    INSERT INTO legistar_commitments (id, matter_id, event_id, description, committed_by, due_date)
    VALUES (?, ?, ?, ?, ?, ?)
  `).run(id, matterId || null, eventId || null, description, committedBy || null, dueDate || null);

  return id;
}

// Get overdue open commitments
export function getOverdueCommitments(db) {
  ensureLegistarTables(db);
  return db.prepare(`
    SELECT c.*, m.title as matter_title, e.event_date, e.body_name
    FROM legistar_commitments c
    LEFT JOIN legistar_matters m ON c.matter_id = m.id
    LEFT JOIN legistar_events e ON c.event_id = e.id
    WHERE c.status = 'open'
      AND c.due_date IS NOT NULL
      AND c.due_date < date('now')
    ORDER BY c.due_date ASC
  `).all();
}
