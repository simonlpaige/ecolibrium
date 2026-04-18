"""
Experiment 1: Non-Western + semantic expansion preview.

For each NEW term added to STRONG_POS in phase2_filter.py (2026-04-17),
count how many orgs in the DB contain that term (case-insensitive) in their
name or description AND are currently excluded or scored below 2.

This answers: "Would we recover more orgs on the next phase2 run?"

Read-only. No data is modified.
"""
import sqlite3

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'

# New terms added in the 2026-04-17 expansion (these did NOT previously exist
# in STRONG_POS, so any match here represents a potential new pickup).
NEW_TERMS = [
    "ejido",
    "cooperativa",
    "cooperative",       # French-casing: coopérative handled separately below
    "coop\u00e9rative",
    "solidaridad",
    "gotong-royong",
    "gotong royong",
    "waqf",
    "minga",
    "genossenschaft",
    "sharikat ta'awuniya",
    "sociedad cooperativa",
    "soci\u00e9t\u00e9 coop\u00e9rative",
    "collective",
    "employee-owned",
]

# Status values that mean the org is excluded or low-scored
EXCLUDED_STATUSES = (
    'removed',
    'excluded_audit_p1',
    'excluded_audit_p2',
    'excluded_audit_p3',
)


def main():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print("=" * 70)
    print("Experiment 1: New non-Western / semantic terms -- pickup preview")
    print("=" * 70)
    print()
    print("Searching for orgs that:")
    print("  (a) contain each new term (case-insensitive) in name or description")
    print("  (b) are currently excluded OR have alignment_score < 2")
    print()

    total_new_pickups = 0

    for term in NEW_TERMS:
        # Count orgs that match the term and are low-scored or excluded
        c.execute("""
            SELECT COUNT(*) FROM organizations
            WHERE (
                LOWER(name) LIKE ? OR LOWER(description) LIKE ?
            )
            AND (
                status IN ('removed','excluded_audit_p1','excluded_audit_p2','excluded_audit_p3')
                OR alignment_score < 2
            )
        """, (f"%{term.lower()}%", f"%{term.lower()}%"))
        count = c.fetchone()[0]
        total_new_pickups += count

        print(f"Term: '{term}'  -->  {count} potential new pickups")

        if count == 0:
            print("  (no matches)")
        else:
            # Show up to 10 sample names
            c.execute("""
                SELECT name, country_code, alignment_score, status
                FROM organizations
                WHERE (
                    LOWER(name) LIKE ? OR LOWER(description) LIKE ?
                )
                AND (
                    status IN ('removed','excluded_audit_p1','excluded_audit_p2','excluded_audit_p3')
                    OR alignment_score < 2
                )
                LIMIT 10
            """, (f"%{term.lower()}%", f"%{term.lower()}%"))
            samples = c.fetchall()
            for row in samples:
                name = (row["name"] or "")[:65]
                cc = row["country_code"] or "??"
                score = row["alignment_score"]
                status = row["status"] or "?"
                print(f"  [{cc}] score={score:>3}  status={status:<25}  {name}")
        print()

    print(f"Total potential new pickups across all new terms: {total_new_pickups}")
    print()
    print("NOTE: counts overlap -- one org matching multiple terms is counted")
    print("multiple times above. This is intentional for per-term signal.")

    conn.close()


if __name__ == "__main__":
    main()
