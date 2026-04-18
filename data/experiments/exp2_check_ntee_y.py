"""
Experiment 2: NTEE 'Y' exclusion preview.

'Y' (Mutual/Membership Benefit) was reviewed and is NOT in KEEP_NTEE.
This script confirms the current impact: how many active/kept orgs have
NTEE codes starting with 'Y', and what they are.

Read-only. No data is modified.
"""
import sqlite3

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'

# These are the statuses that mean an org is still in the kept/active set
KEPT_STATUSES_EXCLUSION = (
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
    print("Experiment 2: NTEE 'Y' -- impact review")
    print("=" * 70)
    print()

    # Count orgs in the kept set that have NTEE starting with Y
    c.execute("""
        SELECT COUNT(*) FROM organizations
        WHERE status NOT IN ('removed','excluded_audit_p1','excluded_audit_p2','excluded_audit_p3')
        AND UPPER(SUBSTR(COALESCE(ntee_code,''), 1, 1)) = 'Y'
    """)
    count_y_kept = c.fetchone()[0]

    # Count total Y-coded orgs regardless of status
    c.execute("""
        SELECT COUNT(*) FROM organizations
        WHERE UPPER(SUBSTR(COALESCE(ntee_code,''), 1, 1)) = 'Y'
    """)
    count_y_total = c.fetchone()[0]

    print(f"Total orgs with NTEE starting 'Y' (all statuses): {count_y_total:,}")
    print(f"Orgs with NTEE 'Y' that are currently KEPT/active: {count_y_kept:,}")
    print()

    if count_y_kept == 0:
        print("Good news: NTEE 'Y' is already fully excluded from the kept set.")
        print("No orgs would be removed by the audit_pass3_ntee.py change.")
    else:
        print(f"WARNING: {count_y_kept} kept orgs have NTEE 'Y'. If 'Y' were added")
        print("to KEEP_NTEE they would survive; since it is not, the next audit run")
        print("will exclude them. Samples below for review.")

    print()
    print("Sample orgs with NTEE 'Y' in the kept set (up to 10):")
    c.execute("""
        SELECT name, country_code, ntee_code, framework_area, alignment_score, status
        FROM organizations
        WHERE status NOT IN ('removed','excluded_audit_p1','excluded_audit_p2','excluded_audit_p3')
        AND UPPER(SUBSTR(COALESCE(ntee_code,''), 1, 1)) = 'Y'
        LIMIT 10
    """)
    rows = c.fetchall()
    if not rows:
        print("  (none found)")
    else:
        for row in rows:
            name = (row["name"] or "")[:60]
            cc = row["country_code"] or "??"
            ntee = row["ntee_code"] or "?"
            area = (row["framework_area"] or "?")[:20]
            score = row["alignment_score"]
            status = row["status"] or "?"
            print(f"  [{cc}] ntee={ntee:<6} score={score:>3}  {area:<22} {name}")

    print()

    # Also show what NTEE Y subcategories look like across all statuses
    print("NTEE 'Y' subcategory breakdown (all statuses, top 10):")
    c.execute("""
        SELECT SUBSTR(ntee_code, 1, 2) AS sub, COUNT(*) AS cnt
        FROM organizations
        WHERE UPPER(SUBSTR(COALESCE(ntee_code,''), 1, 1)) = 'Y'
        GROUP BY sub
        ORDER BY cnt DESC
        LIMIT 10
    """)
    for row in c.fetchall():
        print(f"  {row[0]:<8} {row[1]:>6,} orgs")

    print()
    print("Conclusion: 'Y' is NOT in KEEP_NTEE. The comment added to")
    print("audit_pass3_ntee.py documents this was an intentional decision.")

    conn.close()


if __name__ == "__main__":
    main()
