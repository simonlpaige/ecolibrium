"""
normalize-state-province.py -- Normalize organizations.state_province toward ISO 3166-2.

Reads data/state_province_map.json. For each org with a non-null state_province,
search the variant lists for a case-insensitive match. If found and the current
value differs from the canonical 2-letter (or compound) subdivision code, update.

Usage:
  python tools/normalize-state-province.py            # dry run (default)
  python tools/normalize-state-province.py --apply    # actually write to DB
"""
import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict


HERE     = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
ROOT     = os.path.abspath(os.path.join(HERE, '..'))
DB       = os.path.abspath(os.path.join(ROOT, 'data', 'commonweave_directory.db'))
MAP_PATH = os.path.abspath(os.path.join(ROOT, 'data', 'state_province_map.json'))


def load_map(path):
    """Load the state/province map and build a lowercase variant -> ISO code lookup."""
    with open(path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    # Drop any comment fields (keys starting with _)
    raw = {k: v for k, v in raw.items() if not k.startswith('_')}
    # Build reverse lookup: lowercase variant -> ISO code.
    # Multiple ISO codes can claim the same short variant (e.g. "PR" appears in
    # US-PR and BR-PR). We keep the FIRST one only and warn if collisions appear.
    variant_to_iso = {}
    collisions = defaultdict(list)
    for iso, variants in raw.items():
        for v in variants:
            key = v.strip().lower()
            if not key:
                continue
            if key in variant_to_iso and variant_to_iso[key] != iso:
                collisions[key].append(iso)
            else:
                variant_to_iso.setdefault(key, iso)
    return raw, variant_to_iso, collisions


def canonical_short_code(iso_code):
    """Return the part after the country prefix, e.g. US-MO -> MO."""
    if '-' in iso_code:
        return iso_code.split('-', 1)[1]
    return iso_code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true',
                    help='Write changes to the DB. Default is a dry run.')
    ap.add_argument('--dry-run', action='store_true',
                    help='Explicitly run in dry-run mode (this is the default; '
                         'flag is accepted for clarity).')
    ap.add_argument('--db', default=DB, help='Path to SQLite DB.')
    ap.add_argument('--map', default=MAP_PATH, help='Path to state_province_map.json.')
    ap.add_argument('--limit', type=int, default=None,
                    help='Optional limit for testing.')
    args = ap.parse_args()

    if not os.path.exists(args.map):
        print('[error] map file not found: ' + args.map)
        return 1

    iso_map, variant_to_iso, collisions = load_map(args.map)
    print('Loaded ' + str(len(iso_map)) + ' subdivisions, '
          + str(len(variant_to_iso)) + ' lowercase variants.')
    if collisions:
        print('[warn] ' + str(len(collisions)) + ' ambiguous variants (kept first match): '
              + ', '.join(sorted(collisions.keys())[:10])
              + ('...' if len(collisions) > 10 else ''))

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    sql = ("SELECT id, country_code, state_province FROM organizations "
           "WHERE state_province IS NOT NULL AND state_province != ''")
    if args.limit:
        sql += ' LIMIT ' + str(int(args.limit))
    c.execute(sql)
    rows = c.fetchall()
    print('Inspecting ' + str(len(rows)) + ' org rows with non-null state_province.')

    # Group changes by canonical ISO code to produce the requested per-bucket lines.
    # For each ISO, count distinct (old_value -> new_short) updates.
    changes_by_iso = defaultdict(lambda: defaultdict(list))
    skipped_no_match = 0
    skipped_already_canonical = 0
    cross_country_skipped = 0

    for row in rows:
        org_id = row['id']
        cc     = (row['country_code'] or '').strip().upper()
        sp_raw = (row['state_province'] or '').strip()
        sp_lc  = sp_raw.lower()

        iso = variant_to_iso.get(sp_lc)
        if not iso:
            skipped_no_match += 1
            continue

        # If we have a country_code on the org, prefer matches that agree with it.
        # If the matched ISO is for a different country, skip rather than mangle.
        iso_country = iso.split('-', 1)[0]
        if cc and iso_country != cc:
            cross_country_skipped += 1
            continue

        canonical = canonical_short_code(iso)
        if sp_raw == canonical:
            skipped_already_canonical += 1
            continue

        changes_by_iso[iso][sp_raw].append(org_id)

    # Print a tidy report ordered by total row count desc.
    summary_rows = []
    total_orgs_to_update = 0
    for iso, by_old in changes_by_iso.items():
        canonical = canonical_short_code(iso)
        bucket_total = sum(len(ids) for ids in by_old.values())
        total_orgs_to_update += bucket_total
        for old_val, ids in by_old.items():
            summary_rows.append((iso, canonical, old_val, len(ids), ids))

    summary_rows.sort(key=lambda r: (-r[3], r[0]))

    for iso, canonical, old_val, n, ids in summary_rows:
        print(iso + ": '" + old_val + "' -> '" + canonical + "' (" + str(n) + " orgs)")

    # Apply if requested.
    applied = 0
    if args.apply and summary_rows:
        for iso, canonical, old_val, n, ids in summary_rows:
            placeholders = ','.join(['?'] * len(ids))
            c.execute(
                "UPDATE organizations SET state_province=? WHERE id IN (" + placeholders + ")",
                [canonical] + ids,
            )
            applied += n
        conn.commit()

    # Final summary report.
    print('')
    print('=' * 60)
    print('SUMMARY')
    print('=' * 60)
    print('Rows inspected:                 ' + str(len(rows)))
    print('Already canonical (skipped):    ' + str(skipped_already_canonical))
    print('No variant match (skipped):     ' + str(skipped_no_match))
    print('Cross-country mismatch skipped: ' + str(cross_country_skipped))
    print('Distinct (ISO, old_value) buckets: ' + str(len(summary_rows)))
    print('Total orgs that would update:   ' + str(total_orgs_to_update))
    if args.apply:
        print('Total orgs UPDATED:             ' + str(applied))
    else:
        print('Dry run -- pass --apply to write changes.')

    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
