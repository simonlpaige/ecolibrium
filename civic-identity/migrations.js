// civic-identity/migrations.js
// Tiny migrations runner. Reads .sql files from ./migrations/ in order and
// applies anything newer than the recorded schema_version.
//
// Why this exists:
//   The original schema uses CREATE TABLE IF NOT EXISTS everywhere, which
//   means you can add tables but you cannot evolve columns, add indexes on
//   existing tables, or drop anything. A real neighborhood node will need
//   all three at some point. Adding the runner before any live deploys is
//   cheap; retrofitting it later is not.
//
// Migration file naming: migrations/NNNN_name.sql
//   NNNN is a zero-padded sequence number. They run in numeric order.
//
// Each migration runs inside a transaction. If it throws, nothing is
// committed and the version is not advanced.

import { readFileSync, readdirSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dir = dirname(fileURLToPath(import.meta.url));
const MIGRATIONS_DIR = join(__dir, 'migrations');

export function ensureMigrationsTable(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS schema_version (
      version     INTEGER PRIMARY KEY,
      name        TEXT NOT NULL,
      applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);
}

export function currentVersion(db) {
  ensureMigrationsTable(db);
  const row = db.prepare(`SELECT MAX(version) as v FROM schema_version`).get();
  return row?.v || 0;
}

export function runMigrations(db, { verbose = false } = {}) {
  ensureMigrationsTable(db);
  if (!existsSync(MIGRATIONS_DIR)) return { applied: 0, current: currentVersion(db) };

  const files = readdirSync(MIGRATIONS_DIR)
    .filter(f => f.endsWith('.sql'))
    .sort();

  const applied = [];
  for (const file of files) {
    const match = file.match(/^(\d+)_(.+)\.sql$/);
    if (!match) {
      if (verbose) console.warn(`[migrations] skipping unrecognized file: ${file}`);
      continue;
    }
    const version = parseInt(match[1], 10);
    const name = match[2];

    const already = db.prepare(`SELECT 1 FROM schema_version WHERE version = ?`).get(version);
    if (already) continue;

    const sql = readFileSync(join(MIGRATIONS_DIR, file), 'utf8');
    const tx = db.transaction(() => {
      db.exec(sql);
      db.prepare(`INSERT INTO schema_version (version, name) VALUES (?, ?)`).run(version, name);
    });

    try {
      tx();
      applied.push({ version, name });
      if (verbose) console.log(`[migrations] applied ${version} ${name}`);
    } catch (err) {
      throw new Error(`Migration ${file} failed: ${err.message}`);
    }
  }

  return { applied: applied.length, current: currentVersion(db), details: applied };
}
