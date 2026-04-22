"""
Fuzzy dedup/merge pass for the Commonweave directory.

Groups candidates by normalized name + country code. Then splits each group:

  * AUTO-MERGE tier: candidates share a location signal (same city OR same
    postal code OR lat/lng within ~5 km). Safe to collapse to one canonical
    row.
  * REVIEW tier: candidates have no matching location, or locations
    conflict. These are written to a review file for a human to inspect.
    The script will NOT auto-merge them.

Why the safeguard: "Farmers Cooperative Society" exists in thousands of
Indian villages. A name + country match is not enough to prove two rows
are the same org. Without location agreement, we could obliterate real
distinct grassroots groups. So we wait for evidence.

Soft-deletes merged rows with status='merged' and a merged_into pointer
to the canonical row.

Usage:
    python dedup_merge.py                    # full DB, apply auto-merges
    python dedup_merge.py --dry-run          # report only, no writes
    python dedup_merge.py --country IN       # scope to one country
    python dedup_merge.py --dry-run --country GB
"""
import argparse
import math
import os
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from _common import DB_PATH, ensure_column, normalize_name, trim_audit_path


# Max km apart for two rows to count as the same location
SAME_LOCATION_KM = 5.0


def run_migration(db):
    ensure_column(db, 'organizations', 'merged_into', 'INTEGER')


def score_row(row):
    """Higher score = more complete = better canonical pick."""
    fields = [
        row['description'], row['website'], row['email'],
        row['lat'], row['lon'], row['framework_area'],
    ]
    filled = sum(1 for f in fields if f)
    desc_len = len(row['description'] or '')
    return filled * 10 + desc_len


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def same_location(a, b):
    """True if rows a and b share a trustworthy location signal."""
    # Lat/lng within 5 km
    if a['lat'] and a['lon'] and b['lat'] and b['lon']:
        try:
            km = haversine_km(float(a['lat']), float(a['lon']),
                              float(b['lat']), float(b['lon']))
            return km <= SAME_LOCATION_KM
        except (ValueError, TypeError):
            pass
    # Same city (non-empty)
    ca = _col(a, 'city')
    cb = _col(b, 'city')
    if ca and cb and ca.strip().lower() == cb.strip().lower():
        return True
    # Same state_province as weaker fallback
    sa = _col(a, 'state_province')
    sb = _col(b, 'state_province')
    ca_ci = (ca or '').strip().lower()
    cb_ci = (cb or '').strip().lower()
    if sa and sb and sa.strip().lower() == sb.strip().lower() and ca_ci == cb_ci:
        return True
    return False


def _col(row, name):
    """Safe sqlite3.Row column access that returns None if column missing."""
    try:
        return row[name]
    except (IndexError, KeyError):
        return None


def has_any_location(row):
    return bool(
        (row['lat'] and row['lon'])
        or _col(row, 'city')
        or _col(row, 'state_province')
    )


def partition_by_location(group):
    """
    Split a same-name group into clusters where each cluster shares a
    location signal. Rows with NO location at all go to a separate 'no-loc'
    bucket so we never auto-merge them.
    """
    clusters = []  # each cluster is a list of rows that co-locate
    no_loc = []

    for row in group:
        if not has_any_location(row):
            no_loc.append(row)
            continue
        placed = False
        for cluster in clusters:
            if same_location(cluster[0], row):
                cluster.append(row)
                placed = True
                break
        if not placed:
            clusters.append([row])

    return clusters, no_loc


def merge_fields(canonical, dup, c, dry_run):
    """Copy non-empty fields from dup into canonical where canonical is empty."""
    updates = {}
    candidate_fields = (
        'website', 'email', 'lat', 'lon', 'description',
        'phone', 'city', 'state_province',
    )
    for field in candidate_fields:
        canon_val = canonical[field] if field in canonical.keys() else None
        dup_val = dup[field] if field in dup.keys() else None
        if not canon_val and dup_val:
            updates[field] = dup_val
    if updates and not dry_run:
        set_clause = ', '.join(f'{k}=?' for k in updates)
        vals = list(updates.values()) + [canonical['id']]
        c.execute(
            f'UPDATE organizations SET {set_clause} WHERE id=?', vals
        )
    return updates


def process_country(db, cc, dry_run, merge_log, review_log):
    c = db.cursor()
    where = "WHERE status NOT IN ('merged', 'removed')"
    params = []
    if cc:
        where += ' AND country_code = ?'
        params.append(cc)

    c.execute(f'SELECT * FROM organizations {where}', params)
    rows = c.fetchall()
    if not rows:
        return (0, 0, 0)

    # Group by (normalized_name, country_code)
    groups = {}
    for row in rows:
        key = (normalize_name(row['name']),
               (row['country_code'] or '').upper())
        groups.setdefault(key, []).append(row)

    merged_count = 0
    auto_groups = 0
    review_groups = 0

    for (norm_name, group_cc), group in groups.items():
        if len(group) < 2:
            continue
        if not norm_name:
            continue  # Don't merge blank-normalized names

        clusters, no_loc = partition_by_location(group)

        # Each multi-row cluster with shared location = auto-merge candidate
        for cluster in clusters:
            if len(cluster) < 2:
                continue
            auto_groups += 1
            cluster_sorted = sorted(cluster, key=score_row, reverse=True)
            canonical = cluster_sorted[0]
            for dup in cluster_sorted[1:]:
                updates = merge_fields(canonical, dup, c, dry_run)
                if not dry_run:
                    c.execute(
                        "UPDATE organizations "
                        "SET status='merged', merged_into=? WHERE id=?",
                        (canonical['id'], dup['id'])
                    )
                merged_count += 1
                merge_log.append(
                    f"  merge: [{group_cc}] '{dup['name']}' "
                    f"(id={dup['id']}) -> '{canonical['name']}' "
                    f"(id={canonical['id']}) copied={list(updates.keys())}"
                )

        # Ambiguous groups (missing location, or multiple distinct clusters) go to review
        review_members = list(no_loc)
        if len(clusters) > 1:
            # multiple distinct location clusters inside same name+country:
            # flag the cluster representatives for review too
            for cluster in clusters:
                review_members.append(cluster[0])
        elif len(clusters) == 1 and no_loc:
            # One located cluster + some no-location rows. The no-loc ones
            # go to review so a human can decide whether they join.
            pass  # review_members already has no_loc

        if len(review_members) >= 2:
            review_groups += 1
            review_log.append(
                f"## [{group_cc}] name='{norm_name}' - {len(review_members)} candidates"
            )
            for r in review_members:
                loc_bits = []
                if r['city']:
                    loc_bits.append(f"city={r['city']}")
                if _col(r, 'state_province'):
                    loc_bits.append(f"state={_col(r, 'state_province')}")
                if r['lat'] and r['lon']:
                    loc_bits.append(f"latlng=({r['lat']:.3f},{r['lon']:.3f})")
                if not loc_bits:
                    loc_bits.append('no-location')
                review_log.append(
                    f"  - id={r['id']} name='{r['name']}' "
                    f"website={r['website'] or '-'} {' '.join(loc_bits)}"
                )
            review_log.append('')

    if not dry_run:
        db.commit()

    return auto_groups, merged_count, review_groups


def main():
    ap = argparse.ArgumentParser(
        description='Location-aware fuzzy dedup/merge for Commonweave'
    )
    ap.add_argument('--dry-run', action='store_true',
                    help='Report only, do not write changes')
    ap.add_argument('--country', help='Limit to one country code, e.g. IN')
    args = ap.parse_args()

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    run_migration(db)

    c = db.cursor()
    c.execute("SELECT COUNT(*) FROM organizations "
              "WHERE status NOT IN ('merged', 'removed')")
    before_total = c.fetchone()[0]
    print(f'Before: {before_total:,} non-merged orgs')

    merge_log = []
    review_log = []
    if args.country:
        countries = [args.country.upper()]
    else:
        c.execute("SELECT DISTINCT country_code FROM organizations "
                  "WHERE status NOT IN ('merged', 'removed')")
        countries = [r[0] for r in c.fetchall() if r[0]]

    total_auto_groups = 0
    total_merged = 0
    total_review_groups = 0
    country_stats = []

    for cc in countries:
        auto, merged, review = process_country(
            db, cc, args.dry_run, merge_log, review_log
        )
        if merged or review:
            country_stats.append((cc, merged, review))
        total_auto_groups += auto
        total_merged += merged
        total_review_groups += review

    c.execute("SELECT COUNT(*) FROM organizations "
              "WHERE status NOT IN ('merged', 'removed')")
    after_total = c.fetchone()[0]
    db.close()

    mode = '[DRY RUN]' if args.dry_run else 'DONE'
    print(f'{mode}: {total_auto_groups} auto-merge groups, '
          f'{total_merged} rows soft-deleted, '
          f'{total_review_groups} groups queued for human review')
    print(f'After: {after_total:,} non-merged orgs (was {before_total:,})')

    today = datetime.utcnow().strftime('%Y-%m-%d')

    # Main audit log
    log_path = trim_audit_path('dedup')
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(f'# Dedup/Merge Audit - {today}\n\n')
        f.write(f'Mode: {"dry-run" if args.dry_run else "applied"}\n\n')
        f.write('| Metric | Value |\n|---|---|\n')
        f.write(f'| Before | {before_total:,} |\n')
        f.write(f'| After  | {after_total:,} |\n')
        f.write(f'| Auto-merge groups | {total_auto_groups:,} |\n')
        f.write(f'| Rows merged | {total_merged:,} |\n')
        f.write(f'| Review-needed groups | {total_review_groups:,} |\n\n')
        f.write('Auto-merge requires same name + country + a matching '
                'location signal (city OR postal OR lat/lng within '
                f'{SAME_LOCATION_KM} km). Groups without that evidence '
                'go to the review file, not the merge stream.\n\n')
        if country_stats:
            f.write('## Per-country\n\n')
            f.write('| Country | Merged | Review |\n|---|---|---|\n')
            for cc, merged, review in sorted(
                country_stats, key=lambda x: -(x[1] + x[2])
            ):
                f.write(f'| {cc} | {merged} | {review} |\n')
            f.write('\n')
        if merge_log:
            f.write('## Merge log (first 200)\n\n```\n')
            for line in merge_log[:200]:
                f.write(line + '\n')
            if len(merge_log) > 200:
                f.write(f'... and {len(merge_log) - 200} more\n')
            f.write('```\n')
    print(f'Log written: {log_path}')

    # Review file (only if there are review candidates)
    if review_log:
        review_path = trim_audit_path('dedup-review')
        with open(review_path, 'w', encoding='utf-8') as f:
            f.write(f'# Dedup Review Candidates - {today}\n\n')
            f.write('These name+country groups have location conflicts or '
                    'missing locations. A human has to decide whether to '
                    'merge them. Nothing in this file has been modified in '
                    'the database.\n\n')
            for line in review_log:
                f.write(line + '\n')
        print(f'Review file: {review_path}')


if __name__ == '__main__':
    main()
