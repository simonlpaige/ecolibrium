"""
Experiment 3: Website requirement for trim-keep -- preview only.

Counts orgs that are currently active, alignment_score >= 2, but have
NO website. Shows 20 samples so Simon can decide whether requiring a
website would unfairly drop informal mutual-aid groups.

Read-only. No data is modified. trim_to_aligned.py is NOT changed.
"""
import sqlite3

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'


def main():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print("=" * 70)
    print("Experiment 3: Website-required filter -- preview only")
    print("=" * 70)
    print()

    # Total active orgs with score >= 2 (the trim-keep population)
    c.execute("""
        SELECT COUNT(*) FROM organizations
        WHERE status = 'active'
        AND alignment_score >= 2
    """)
    total_kept = c.fetchone()[0]

    # Subset with no website
    c.execute("""
        SELECT COUNT(*) FROM organizations
        WHERE status = 'active'
        AND alignment_score >= 2
        AND (website IS NULL OR TRIM(website) = '')
    """)
    no_website_count = c.fetchone()[0]

    pct = (no_website_count / total_kept * 100) if total_kept > 0 else 0

    print(f"Active orgs with alignment_score >= 2:          {total_kept:>10,}")
    print(f"Of those, with NO website:                      {no_website_count:>10,}  ({pct:.1f}%)")
    print()
    print("If trim_to_aligned.py were changed to require a website,")
    print(f"these {no_website_count:,} orgs would be dropped on the next trim run.")
    print()
    print("Sample orgs (up to 20) that would be dropped:")
    print(f"  {'Name':<50} {'Country':<8} {'Framework Area':<25} {'Score'}")
    print("  " + "-" * 95)

    c.execute("""
        SELECT name, country_code, framework_area, alignment_score
        FROM organizations
        WHERE status = 'active'
        AND alignment_score >= 2
        AND (website IS NULL OR TRIM(website) = '')
        ORDER BY alignment_score DESC, name
        LIMIT 20
    """)
    rows = c.fetchall()
    if not rows:
        print("  (none found)")
    else:
        for row in rows:
            name = (row["name"] or "")[:50]
            cc = (row["country_code"] or "??")[:7]
            area = (row["framework_area"] or "?")[:25]
            score = row["alignment_score"]
            print(f"  {name:<50} {cc:<8} {area:<25} {score}")

    print()
    print("=" * 70)
    print("IMPORTANT TENSION TO CONSIDER BEFORE APPLYING THIS CHANGE:")
    print("=" * 70)
    print()
    print("The BOT-CRITIQUE flagged 'informal mutual aid groups' as a known")
    print("false-negative problem -- orgs that ARE aligned but lack an online")
    print("footprint. Many are:")
    print("  - Community kitchens / food pantries in rural or low-income areas")
    print("  - Indigenous land stewardship groups")
    print("  - Informal cooperatives in the Global South")
    print()
    print("Requiring a website would systematically exclude exactly these groups,")
    print("reinforcing the Western / high-digital-footprint bias the critique")
    print("already identified as a problem.")
    print()
    print("Recommendation: eyeball the samples above. If most are clearly")
    print("low-quality entries (duplicates, dead stubs), proceed. If you see")
    print("legitimate mutual-aid orgs, consider a softer rule (e.g. website OR")
    print("score >= 5, or website required only for score == 2).")

    conn.close()


if __name__ == "__main__":
    main()
