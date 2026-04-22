#!/usr/bin/env node
// ingest/sync.js
// Master sync script for NeighborhoodOS.
// Pulls all data sources and updates the local SQLite database.
//
// Usage:
//   node ingest/sync.js                    # Full sync all sources
//   node ingest/sync.js --source kc-data   # Only KC Open Data
//   node ingest/sync.js --source legistar  # Only legislative data
//   node ingest/sync.js --source social    # Only social (if tokens configured)
//   node ingest/sync.js --status           # Show sync status without pulling

import Database from 'better-sqlite3';
import { syncDataset, getIngestSummary, WEST_WALDO_BOUNDS, DATASETS }
  from '../connectors/kc-open-data.js';
import { syncRecentMatters, syncRecentEvents, getOverdueCommitments }
  from '../connectors/legistar.js';
import { getSocialSummary, scrapeNextdoorPublicPage }
  from '../connectors/social.js';
import { probeKcOpenData, getConnectorStatus } from './probe.js';

// ----------------------------------------------------------------
// Config
// ----------------------------------------------------------------

const DB_PATH = process.env.NOS_DB_PATH || './neighborhood-os.db';
const NEIGHBORHOOD = process.env.NOS_NEIGHBORHOOD || 'westwaldo';
const BOUNDS = JSON.parse(process.env.NOS_BOUNDS || JSON.stringify(WEST_WALDO_BOUNDS));
const NEXTDOOR_SLUG = process.env.NEXTDOOR_SLUG || 'westwaldomo';

// Parse args
const args = process.argv.slice(2);
const sourceFilter = args.includes('--source') ? args[args.indexOf('--source') + 1] : null;
const statusOnly = args.includes('--status');
const verbose = args.includes('--verbose') || args.includes('-v');

// ----------------------------------------------------------------
// Main
// ----------------------------------------------------------------

const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

if (statusOnly) {
  await printStatus();
  process.exit(0);
}

console.log(`\nNeighborhoodOS Sync — ${NEIGHBORHOOD}`);
console.log(`DB: ${DB_PATH}`);
console.log(`Time: ${new Date().toISOString()}`);
console.log('─'.repeat(50));

const results = {};

// ---- KC Open Data ----
if (!sourceFilter || sourceFilter === 'kc-data') {
  console.log('\n📊 KC Open Data...');

  // Probe first so we know which datasets changed shape or went dark
  // before we trust the sync numbers.
  try {
    const probes = await probeKcOpenData(db);
    const red = probes.filter(p => p.status === 'red');
    const yellow = probes.filter(p => p.status === 'yellow');
    if (red.length || yellow.length) {
      console.log(`  ⚠ probe: ${red.length} red, ${yellow.length} yellow (see connector_status table)`);
      for (const p of [...red, ...yellow]) {
        console.log(`     [${p.status}] ${p.key}: ${p.detail}`);
      }
    } else {
      console.log(`  ✓ probe: all ${probes.length} datasets green`);
    }
  } catch (err) {
    console.log(`  ✗ probe failed: ${err.message}`);
  }

  const datasets = ['requests_311', 'permits', 'crime', 'violations',
                    'dangerous_buildings', 'budget_expenditures', 'vendor_payments'];

  for (const key of datasets) {
    try {
      const result = await syncDataset(db, key, BOUNDS);
      results[key] = result;
      console.log(`  ✓ ${key}: ${result.fetched} records`);
    } catch (err) {
      results[key] = { error: err.message };
      console.log(`  ✗ ${key}: ${err.message}`);
    }
  }
}

// ---- Legistar ----
if (!sourceFilter || sourceFilter === 'legistar') {
  console.log('\n🏛️  Legistar (legislative record)...');

  try {
    const matters = await syncRecentMatters(db, { days: 14 });
    results.legistar_matters = matters;
    console.log(`  ✓ matters: ${matters.synced} records`);
  } catch (err) {
    results.legistar_matters = { error: err.message };
    console.log(`  ✗ matters: ${err.message}`);
  }

  try {
    const events = await syncRecentEvents(db, { days: 14 });
    results.legistar_events = events;
    console.log(`  ✓ events: ${events.synced} records`);
  } catch (err) {
    results.legistar_events = { error: err.message };
    console.log(`  ✗ events: ${err.message}`);
  }
}

// ---- Social ----
if (!sourceFilter || sourceFilter === 'social') {
  console.log('\n💬 Social platforms...');

  try {
    const nd = await scrapeNextdoorPublicPage(NEXTDOOR_SLUG);
    results.nextdoor_public = nd;
    if (nd.membersApprox) {
      console.log(`  ✓ Nextdoor public page: ~${nd.membersApprox} members`);
    } else {
      console.log(`  ℹ Nextdoor: public page available, content login-gated`);
      console.log(`    Apply for Agency access: partners.nextdoor.com/agency`);
    }
  } catch (err) {
    results.nextdoor_public = { error: err.message };
    console.log(`  ✗ Nextdoor: ${err.message}`);
  }

  if (process.env.FB_ACCESS_TOKEN) {
    console.log(`  ✓ Facebook: token configured (run fetchFacebookGroupPosts() to pull)`);
  } else {
    console.log(`  ℹ Facebook: no token. Set FB_ACCESS_TOKEN after app review.`);
    console.log(`    Manual export: use ingestFacebookExport() with downloaded group data`);
  }
}

// ---- Summary ----
console.log('\n' + '─'.repeat(50));
console.log('Sync complete.\n');

const overdue = getOverdueCommitments(db);
if (overdue.length > 0) {
  console.log(`⚠️  ${overdue.length} overdue commitment(s):`);
  overdue.forEach(c => {
    console.log(`   - ${c.description} (due: ${c.due_date}, by: ${c.committed_by || 'unknown'})`);
  });
  console.log('');
}

if (verbose) {
  console.log('Ingest summary (last 7 days):');
  const summary = getIngestSummary(db, 7);
  summary.forEach(row => {
    console.log(`  ${row.dataset_key}: ${row.count} records`);
  });
}

db.close();

// ----------------------------------------------------------------
// Status display
// ----------------------------------------------------------------

async function printStatus() {
  console.log(`\nNeighborhoodOS Status — ${NEIGHBORHOOD}`);
  console.log('─'.repeat(50));

  const summary = getIngestSummary(db, 7);
  console.log('\nData (last 7 days):');
  if (summary.length === 0) {
    console.log('  No data synced yet. Run: node ingest/sync.js');
  } else {
    summary.forEach(row => {
      console.log(`  ${row.dataset_key.padEnd(25)} ${row.count} records`);
    });
  }

  const social = getSocialSummary(db, NEIGHBORHOOD);
  console.log('\nSocial:');
  console.log(`  Total posts ingested: ${social.totalPosts}`);
  console.log(`  Last 7 days: ${social.last7days}`);
  if (social.topTopics.length > 0) {
    console.log(`  Top topics: ${social.topTopics.map(t => t.tag).join(', ')}`);
  }

  const overdue = getOverdueCommitments(db);
  console.log(`\nCommitment tracker:`);
  console.log(`  Overdue: ${overdue.length}`);

  db.close();
}
