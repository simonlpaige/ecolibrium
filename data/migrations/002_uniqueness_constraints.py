"""
Migration 002: add real uniqueness constraints to organizations.

This migration:
1. Finds duplicate rows by source/source_id and by country_code/registration_type/registration_id.
2. Keeps the lowest id in each duplicate group.
3. Exports duplicates to an audit CSV before deleting them.
4. Adds the partial unique indexes the ingest scripts depend on.
"""

import csv
import os
import sqlite3
from collections import defaultdict
from datetime import datetime

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.dirname(_THIS_DIR)

DB_PATH = os.path.join(_DATA_DIR, "ecolibrium_directory.db")
AUDIT_DIR = os.path.join(_DATA_DIR, "audit")

UNIQ_SOURCE_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uniq_org_source
ON organizations(source, source_id)
WHERE source_id IS NOT NULL AND TRIM(source_id) != ''
"""

UNIQ_REGISTRATION_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uniq_org_registration
ON organizations(country_code, registration_type, registration_id)
WHERE registration_id IS NOT NULL AND TRIM(registration_id) != ''
"""


def table_columns(cursor):
    cursor.execute("PRAGMA table_info(organizations)")
    return [row[1] for row in cursor.fetchall()]


def fetch_duplicate_groups(cursor, query):
    groups = defaultdict(list)
    cursor.execute(query)
    for row in cursor.fetchall():
        groups[row[1:]].append(row[0])
    return {key: ids for key, ids in groups.items() if len(ids) > 1}


def build_duplicate_plan(cursor):
    delete_plan = {}

    source_groups = fetch_duplicate_groups(
        cursor,
        """
        SELECT id, source, source_id
        FROM organizations
        WHERE source_id IS NOT NULL AND TRIM(source_id) != ''
        ORDER BY source, source_id, id
        """,
    )
    for key, ids in source_groups.items():
        keep_id = min(ids)
        for duplicate_id in ids:
            if duplicate_id == keep_id:
                continue
            delete_plan.setdefault(duplicate_id, {
                "reason": "duplicate_source",
                "duplicate_key": "|".join("" if part is None else str(part) for part in key),
                "kept_id": keep_id,
            })

    registration_groups = fetch_duplicate_groups(
        cursor,
        """
        SELECT id, country_code, registration_type, registration_id
        FROM organizations
        WHERE registration_id IS NOT NULL AND TRIM(registration_id) != ''
        ORDER BY country_code, registration_type, registration_id, id
        """,
    )
    for key, ids in registration_groups.items():
        remaining_ids = [row_id for row_id in ids if row_id not in delete_plan]
        if len(remaining_ids) <= 1:
            continue
        keep_id = min(remaining_ids)
        for duplicate_id in remaining_ids:
            if duplicate_id == keep_id:
                continue
            delete_plan.setdefault(duplicate_id, {
                "reason": "duplicate_registration",
                "duplicate_key": "|".join("" if part is None else str(part) for part in key),
                "kept_id": keep_id,
            })

    return delete_plan


def export_duplicates(cursor, columns, delete_plan):
    if not delete_plan:
        return None

    os.makedirs(AUDIT_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(AUDIT_DIR, f"duplicate_orgs_{timestamp}.csv")
    ordered_ids = sorted(delete_plan)
    placeholders = ",".join("?" for _ in ordered_ids)
    cursor.execute(
        f"SELECT {', '.join(columns)} FROM organizations WHERE id IN ({placeholders}) ORDER BY id",
        ordered_ids,
    )
    rows = cursor.fetchall()

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(columns + ["duplicate_reason", "duplicate_key", "kept_id"])
        for row in rows:
            meta = delete_plan[row[0]]
            writer.writerow(list(row) + [meta["reason"], meta["duplicate_key"], meta["kept_id"]])

    return out_path


def apply_unique_indexes(cursor):
    cursor.execute(UNIQ_SOURCE_SQL)
    cursor.execute(UNIQ_REGISTRATION_SQL)


def run():
    db = sqlite3.connect(DB_PATH)
    cursor = db.cursor()
    columns = table_columns(cursor)

    delete_plan = build_duplicate_plan(cursor)
    audit_path = export_duplicates(cursor, columns, delete_plan)

    if delete_plan:
        cursor.executemany(
            "DELETE FROM organizations WHERE id = ?",
            [(row_id,) for row_id in sorted(delete_plan)],
        )
        print(f"Deleted {len(delete_plan):,} duplicate rows")
        print(f"Audit CSV: {audit_path}")
    else:
        print("No duplicate rows found")

    apply_unique_indexes(cursor)
    db.commit()
    db.close()
    print("Unique indexes are in place")


if __name__ == "__main__":
    run()
