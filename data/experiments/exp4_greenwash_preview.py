"""
Experiment 4: Greenwashing / corporate-foundation penalty -- preview only.

Finds orgs whose name contains 'foundation' AND whose description contains
corporate signals ('corporation', ', inc', ' inc.', 'corp.'). These are
potential corporate-PR foundations masquerading as nonprofits.

Shows count + 20 samples for review before any penalty is applied.

Read-only. No data is modified.
"""
import sqlite3

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'


def main():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print("=" * 70)
    print("Experiment 4: Greenwashing / corporate-foundation penalty preview")
    print("=" * 70)
    print()

    # Count orgs matching the greenwashing heuristic
    c.execute("""
        SELECT COUNT(*) FROM organizations
        WHERE LOWER(name) LIKE '%foundation%'
        AND (
            LOWER(description) LIKE '%corporation%'
            OR LOWER(description) LIKE '%, inc%'
            OR LOWER(description) LIKE '% inc.%'
            OR LOWER(description) LIKE '%corp.%'
        )
    """)
    total_flagged = c.fetchone()[0]

    # Break out by status so we know how many are currently active
    c.execute("""
        SELECT status, COUNT(*) AS cnt
        FROM organizations
        WHERE LOWER(name) LIKE '%foundation%'
        AND (
            LOWER(description) LIKE '%corporation%'
            OR LOWER(description) LIKE '%, inc%'
            OR LOWER(description) LIKE '% inc.%'
            OR LOWER(description) LIKE '%corp.%'
        )
        GROUP BY status
        ORDER BY cnt DESC
    """)
    by_status = c.fetchall()

    print(f"Total orgs flagged by this heuristic: {total_flagged:,}")
    print()
    print("Breakdown by current status:")
    for row in by_status:
        print(f"  {(row['status'] or 'NULL'):<30} {row['cnt']:>6,}")
    print()

    print("Sample flagged orgs (up to 20) -- name + description snippet:")
    print(f"  {'Name':<50} {'Score':>6}  Description snippet")
    print("  " + "-" * 100)

    c.execute("""
        SELECT name, description, alignment_score, status, country_code
        FROM organizations
        WHERE LOWER(name) LIKE '%foundation%'
        AND (
            LOWER(description) LIKE '%corporation%'
            OR LOWER(description) LIKE '%, inc%'
            OR LOWER(description) LIKE '% inc.%'
            OR LOWER(description) LIKE '%corp.%'
        )
        ORDER BY alignment_score DESC
        LIMIT 20
    """)
    rows = c.fetchall()
    if not rows:
        print("  (none found)")
    else:
        for row in rows:
            name = (row["name"] or "")[:50]
            score = row["alignment_score"]
            desc = (row["description"] or "")[:80].replace("\n", " ")
            cc = row["country_code"] or "??"
            status = row["status"] or "?"
            print(f"  {name:<50} {score:>6}  [{cc}] {desc}")

    print()
    print("=" * 70)
    print("NOTE: If Experiment 4 proceeds, these orgs would lose 5 points.")
    print("Review samples to confirm the heuristic is not catching legit")
    print("community foundations (e.g., 'Smith Community Foundation, Inc.'")
    print("is a real charity, not a corporate front).")
    print()
    print("The heuristic is coarse: any org with 'foundation' in the name AND")
    print("a description mentioning 'corporation' or 'inc' gets penalized.")
    print("False positives are likely -- especially for community foundations")
    print("that are legally incorporated as corporations.")
    print()
    print("Suggested refinement before applying: add a whitelist of terms that")
    print("indicate a genuine community org (e.g., 'community foundation',")
    print("'family foundation', 'public foundation') to exempt from the penalty.")

    conn.close()


if __name__ == "__main__":
    main()
