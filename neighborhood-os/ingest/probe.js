// neighborhood-os/ingest/probe.js
// Lightweight connector health check. Runs before each sync, asks each
// configured dataset for one record, and writes a row to connector_status
// so operators can see when a Socrata schema change or a Legistar outage is
// about to break things.
//
// Not a full test. A probe. If it comes back yellow or red, don't trust the
// next sync's numbers without a look.

import { fetchDataset, DATASETS } from '../connectors/kc-open-data.js';

export async function probeKcOpenData(db) {
  const results = [];
  for (const [key, meta] of Object.entries(DATASETS)) {
    const status = await probeOne(key, meta);
    writeStatus(db, key, status);
    results.push({ key, ...status });
  }
  return results;
}

async function probeOne(key, meta) {
  try {
    const rows = await fetchDataset(meta.id, { limit: 1 });
    if (!Array.isArray(rows)) return { status: 'red', detail: 'response was not an array' };
    if (rows.length === 0) return { status: 'yellow', detail: 'dataset returned zero rows' };
    // Sanity check: expected date field present?
    if (meta.dateField && meta.dateField !== 'casenumber' && !(meta.dateField in rows[0])) {
      return {
        status: 'yellow',
        detail: `expected field "${meta.dateField}" missing from first row`
      };
    }
    return { status: 'green', detail: `ok (sample keys: ${Object.keys(rows[0]).slice(0, 4).join(', ')})` };
  } catch (err) {
    return { status: 'red', detail: err.message.slice(0, 200) };
  }
}

function writeStatus(db, key, { status, detail }) {
  ensureTable(db);
  db.prepare(`
    INSERT INTO connector_status (connector_key, status, last_checked, last_ok, detail)
    VALUES (?, ?, datetime('now'),
            CASE WHEN ? = 'green' THEN datetime('now') ELSE NULL END,
            ?)
    ON CONFLICT(connector_key) DO UPDATE SET
      status = excluded.status,
      last_checked = datetime('now'),
      last_ok = CASE WHEN excluded.status = 'green' THEN datetime('now') ELSE connector_status.last_ok END,
      detail = excluded.detail
  `).run(key, status, status, detail);
}

function ensureTable(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS connector_status (
      connector_key  TEXT PRIMARY KEY,
      status         TEXT NOT NULL,
      last_checked   TEXT NOT NULL DEFAULT (datetime('now')),
      last_ok        TEXT,
      detail         TEXT
    );
  `);
}

export function getConnectorStatus(db) {
  ensureTable(db);
  return db.prepare(`SELECT * FROM connector_status ORDER BY connector_key`).all();
}
