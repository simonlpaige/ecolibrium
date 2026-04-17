"""
Aggressive trim of ecolibrium directory.

Keeps only:  status='active' AND alignment_score >= 2
Hard-deletes: every row with status != 'active'   (prior audit exclusions + soft-removed)
Relabels:    status='active' AND alignment_score < 2 (or NULL) -> status='excluded_low_signal'
             (rows are deleted at the end; relabel exists only for the audit CSV export)

Before any destructive operation:
  1. Full CSV dump of every row that will be deleted, grouped by reason.
  2. Backup file created separately outside this script.

Idempotent: re-running after first trim should be a no-op.
"""
import csv
import os
import sqlite3
import sys
from datetime import datetime, timezone

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'
OUT_DIR = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\trim_audit'

KEEP_SCORE_MIN = 2  # rows with active + alignment_score >= 2 survive


def timestamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    ts = timestamp()

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    c = db.cursor()

    # snapshot before
    c.execute("SELECT status, COUNT(*) FROM organizations GROUP BY status ORDER BY 2 DESC")
    before = c.fetchall()
    print('BEFORE:')
    total_before = 0
    for row in before:
        print(f'  {row[0]:<25s} {row[1]:>9,}')
        total_before += row[1]
    print(f'  {"TOTAL":<25s} {total_before:>9,}')

    # what will be kept
    c.execute(
        "SELECT COUNT(*) FROM organizations WHERE status='active' AND alignment_score IS NOT NULL AND alignment_score >= ?",
        (KEEP_SCORE_MIN,),
    )
    keep_count = c.fetchone()[0]
    print(f'\nWill keep (status=active AND alignment_score>={KEEP_SCORE_MIN}): {keep_count:,}')

    if keep_count == total_before:
        print('\nNothing to do. Database already matches the keep criteria.')
        db.close()
        return

    # export CSV of everything we're about to delete, partitioned by reason
    partitions = {
        'audit_excluded_p1': "status='excluded_audit_p1'",
        'audit_excluded_p2': "status='excluded_audit_p2'",
        'audit_excluded_p3': "status='excluded_audit_p3'",
        'soft_removed':      "status='removed'",
        'active_low_signal': f"status='active' AND (alignment_score IS NULL OR alignment_score < {KEEP_SCORE_MIN})",
    }

    print('\nEXPORTING deletion audit CSVs:')
    for label, where_clause in partitions.items():
        csv_path = os.path.join(OUT_DIR, f'{ts}_{label}.csv')
        c.execute(f"SELECT * FROM organizations WHERE {where_clause}")
        rows = c.fetchall()
        if not rows:
            print(f'  {label:<22s} (0 rows, skipped)')
            continue
        cols = rows[0].keys()
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(cols)
            for row in rows:
                w.writerow([row[k] for k in cols])
        print(f'  {label:<22s} {len(rows):>8,} rows -> {os.path.basename(csv_path)}')

    # execute the delete in one transaction
    print('\nDELETING rows...')
    deleted_total = 0
    for label, where_clause in partitions.items():
        c.execute(f"DELETE FROM organizations WHERE {where_clause}")
        deleted_total += c.rowcount
        print(f'  {label:<22s} deleted {c.rowcount:,}')
    db.commit()
    print(f'  TOTAL DELETED: {deleted_total:,}')

    # VACUUM to actually reclaim space
    print('\nVACUUM (reclaiming disk space)...')
    db.isolation_level = None
    c.execute('VACUUM')
    db.isolation_level = ''

    # snapshot after
    c.execute("SELECT COUNT(*) FROM organizations")
    total_after = c.fetchone()[0]
    c.execute("SELECT status, COUNT(*) FROM organizations GROUP BY status ORDER BY 2 DESC")
    print('\nAFTER:')
    for row in c.fetchall():
        print(f'  {row[0]:<25s} {row[1]:>9,}')
    print(f'  {"TOTAL":<25s} {total_after:>9,}')

    c.execute("SELECT COUNT(DISTINCT country_code) FROM organizations WHERE country_code IS NOT NULL")
    countries_after = c.fetchone()[0]
    print(f'\nDistinct countries remaining: {countries_after}')

    c.execute("SELECT framework_area, COUNT(*) FROM organizations GROUP BY framework_area ORDER BY 2 DESC")
    print('\nFramework area distribution:')
    for row in c.fetchall():
        print(f'  {str(row[0]):<20s} {row[1]:>7,}')

    db.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
