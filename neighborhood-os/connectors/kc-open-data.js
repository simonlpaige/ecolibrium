// connectors/kc-open-data.js
// Kansas City Open Data connector.
// Pulls from the Socrata API endpoints confirmed live as of April 2026.
// All fetches are incremental - stores a cursor so we don't re-pull everything.

import Database from 'better-sqlite3';
import crypto from 'crypto';

const BASE = 'https://data.kcmo.org/resource';
const APP_TOKEN = process.env.KC_OPEN_DATA_TOKEN || ''; // Optional - raises rate limit

// Dataset registry. Each entry is a named feed we track.
export const DATASETS = {
  requests_311: {
    id: '7at3-sxhp',
    name: '311 Service Requests',
    dateField: 'creation_date',
    geoFields: ['latitude', 'longitude'],
    layer: 'health_index'
  },
  permits: {
    id: 'ntw8-aacc',
    name: 'Building Permits',
    dateField: 'issue_date',
    geoFields: ['mapped_location'],
    layer: 'health_index'
  },
  crime: {
    id: 'gqy2-yvmn',
    name: 'KCPD Reported Crime (since 2015)',
    dateField: 'reported_date',
    geoFields: ['latitude', 'longitude'],
    layer: 'health_index'
  },
  violations: {
    id: 'tezm-fh2e',
    name: 'Property Violations',
    dateField: 'violation_entry_date',
    geoFields: ['latitude', 'longitude'],
    layer: 'health_index'
  },
  dangerous_buildings: {
    id: 'ax3m-jhxx',
    name: 'Dangerous Buildings',
    dateField: 'casenumber', // no good date field - use as static
    geoFields: ['latitude', 'longitude'],
    layer: 'health_index'
  },
  budget_expenditures: {
    id: 'ygzn-3xmu',
    name: 'Budget Expenditures',
    dateField: 'fiscal_year',
    layer: 'civic_intel'
  },
  budget_revenue: {
    id: 'rv2u-bdnp',
    name: 'Budget Revenue',
    dateField: 'fiscal_year',
    layer: 'civic_intel'
  },
  vendor_payments: {
    id: '39kh-2k2z',
    name: 'Vendor Payments 2024',
    dateField: 'check_date',
    layer: 'civic_intel'
  },
  zoning: {
    id: 'n88a-7et5',
    name: 'Zoning',
    geoFields: ['the_geom'],
    layer: 'civic_intel'
  },
  business_licenses: {
    id: 'kkhs-93m4',
    name: 'Business Licenses',
    geoFields: ['latitude', 'longitude'],
    layer: 'health_index'
  }
};

// ----------------------------------------------------------------
// Fetch a page of records from a dataset
// ----------------------------------------------------------------

export async function fetchDataset(datasetId, {
  limit = 1000,
  offset = 0,
  where = null,
  orderBy = null,
  select = null
} = {}) {
  const params = new URLSearchParams({ '$limit': limit, '$offset': offset });
  if (where) params.set('$where', where);
  if (orderBy) params.set('$order', orderBy);
  if (select) params.set('$select', select);
  if (APP_TOKEN) params.set('$$app_token', APP_TOKEN);

  const url = `${BASE}/${datasetId}.json?${params}`;
  const res = await fetch(url, {
    headers: { 'Accept': 'application/json' }
  });

  if (!res.ok) throw new Error(`KC Open Data ${datasetId}: HTTP ${res.status}`);
  return res.json();
}

// ----------------------------------------------------------------
// Bounding box filter for a neighborhood
// Returns a SoQL $where clause string
// ----------------------------------------------------------------

export function bboxWhere(bounds, latField = 'latitude', lonField = 'longitude') {
  // bounds: { north, south, east, west } in decimal degrees.
  // Coerce to numbers so a malformed bounds object cannot inject SoQL.
  const n = Number(bounds.north);
  const s = Number(bounds.south);
  const e = Number(bounds.east);
  const w = Number(bounds.west);
  if (![n, s, e, w].every(Number.isFinite)) {
    throw new Error('bboxWhere: bounds must be numeric {north, south, east, west}');
  }
  // SoQL numeric comparisons do not need quotes.
  return [
    `${latField} >= ${s}`,
    `${latField} <= ${n}`,
    `${lonField} >= ${w}`,
    `${lonField} <= ${e}`
  ].join(' AND ');
}

// West Waldo default bounds
export const WEST_WALDO_BOUNDS = {
  north: 38.9920,  // ~75th St
  south: 38.9540,  // ~85th St
  east:  -94.5890, // Wornall Rd
  west:  -94.6140  // Ward Pkwy
};

// ----------------------------------------------------------------
// Incremental sync: fetch new records since last cursor
// ----------------------------------------------------------------

export async function syncDataset(db, key, bounds = null, sinceDate = null) {
  const dataset = DATASETS[key];
  if (!dataset) throw new Error(`Unknown dataset: ${key}`);

  // Get or create the sync cursor
  ensureSyncTable(db);
  const cursor = db.prepare(`SELECT cursor_val FROM sync_cursors WHERE dataset_key = ?`).get(key);
  const since = sinceDate || cursor?.cursor_val || '2020-01-01T00:00:00';

  let where = null;
  const clauses = [];

  // Geographic filter
  if (bounds && dataset.geoFields?.includes('latitude')) {
    clauses.push(bboxWhere(bounds));
  }

  // Incremental filter by date. Reject anything that is not an ISO-looking
  // string so a poisoned cursor cannot break out of the quoted literal.
  if (dataset.dateField && since && dataset.dateField !== 'casenumber') {
    if (!/^[0-9T:\-.Z+ ]+$/.test(String(since))) {
      throw new Error(`Invalid since value for dataset ${key}`);
    }
    clauses.push(`${dataset.dateField} > '${since}'`);
  }

  if (clauses.length) where = clauses.join(' AND ');

  const records = [];
  let offset = 0;
  let page;

  do {
    page = await fetchDataset(dataset.id, {
      limit: 1000,
      offset,
      where,
      orderBy: dataset.dateField && dataset.dateField !== 'casenumber'
        ? `${dataset.dateField} ASC` : null
    });
    records.push(...page);
    offset += page.length;
  } while (page.length === 1000);

  // Store raw records
  storeRawRecords(db, key, records, dataset.layer);

  // Update cursor to now
  const newCursor = new Date().toISOString();
  db.prepare(`
    INSERT OR REPLACE INTO sync_cursors (dataset_key, cursor_val, last_synced)
    VALUES (?, ?, datetime('now'))
  `).run(key, newCursor);

  return { dataset: key, fetched: records.length, cursor: newCursor };
}

// ----------------------------------------------------------------
// Storage
// ----------------------------------------------------------------

function ensureSyncTable(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS sync_cursors (
      dataset_key  TEXT PRIMARY KEY,
      cursor_val   TEXT,
      last_synced  TEXT
    );
    CREATE TABLE IF NOT EXISTS raw_records (
      id           TEXT PRIMARY KEY,
      dataset_key  TEXT NOT NULL,
      layer        TEXT NOT NULL,
      record_json  TEXT NOT NULL,
      ingested_at  TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_raw_records_dataset ON raw_records(dataset_key);
    CREATE INDEX IF NOT EXISTS idx_raw_records_layer ON raw_records(layer);
  `);
}

function storeRawRecords(db, key, records, layer) {
  const stmt = db.prepare(`
    INSERT OR IGNORE INTO raw_records (id, dataset_key, layer, record_json)
    VALUES (?, ?, ?, ?)
  `);

  const insert = db.transaction((recs) => {
    for (const rec of recs) {
      const id = `${key}:${crypto.createHash('sha256').update(JSON.stringify(rec)).digest('hex').slice(0, 16)}`;
      stmt.run(id, key, layer, JSON.stringify(rec));
    }
  });

  insert(records);
}

// ----------------------------------------------------------------
// Query helpers
// ----------------------------------------------------------------

// Get recent records for a layer, optionally filtered by date
export function getRecentRecords(db, datasetKey, { limit = 100, since = null } = {}) {
  ensureSyncTable(db);
  let query = `SELECT * FROM raw_records WHERE dataset_key = ?`;
  const params = [datasetKey];
  if (since) { query += ` AND ingested_at > ?`; params.push(since); }
  query += ` ORDER BY ingested_at DESC LIMIT ?`;
  params.push(limit);
  return db.prepare(query).all(...params).map(r => ({ ...r, data: JSON.parse(r.record_json) }));
}

// Count records by dataset in the last N days
export function getIngestSummary(db, days = 7) {
  ensureSyncTable(db);
  return db.prepare(`
    SELECT dataset_key, layer, COUNT(*) as count
    FROM raw_records
    WHERE ingested_at > datetime('now', '-${days} days')
    GROUP BY dataset_key, layer
    ORDER BY count DESC
  `).all();
}
