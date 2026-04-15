"""
Pass 3: NTEE-based exclusion for US orgs.
Only keeps NTEE categories directly relevant to Ecolibrium's mission.
"""
import sqlite3

db = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db')
c = db.cursor()

c.execute("""SELECT COUNT(*) FROM organizations 
    WHERE status NOT IN ('removed', 'excluded_audit_p1', 'excluded_audit_p2')
    AND country_code = 'US'""")
before = c.fetchone()[0]

# NTEE categories to KEEP (directly aligned with Ecolibrium mission)
KEEP_NTEE = ['C', 'E', 'F', 'I', 'J', 'K', 'L', 'O', 'P', 'Q', 'R', 'S', 'W']

# Exclude US orgs whose NTEE major code is NOT in the keep list
c.execute("""
    UPDATE organizations
    SET status = 'excluded_audit_p3'
    WHERE status NOT IN ('removed', 'excluded_audit_p1', 'excluded_audit_p2', 'excluded_audit_p3')
    AND country_code = 'US'
    AND ntee_code IS NOT NULL 
    AND ntee_code != ''
    AND UPPER(SUBSTR(ntee_code, 1, 1)) NOT IN ({})
""".format(','.join(f"'{x}'" for x in KEEP_NTEE)))
excluded = c.rowcount
db.commit()

c.execute("""SELECT COUNT(*) FROM organizations 
    WHERE status NOT IN ('removed', 'excluded_audit_p1', 'excluded_audit_p2', 'excluded_audit_p3')""")
total_after = c.fetchone()[0]

c.execute("""SELECT COUNT(*) FROM organizations 
    WHERE status NOT IN ('removed', 'excluded_audit_p1', 'excluded_audit_p2', 'excluded_audit_p3')
    AND country_code = 'US'""")
us_after = c.fetchone()[0]

print(f"=== PASS 3 (NTEE) RESULTS ===")
print(f"US before:    {before:>10,}")
print(f"US excluded:  {excluded:>10,}")
print(f"US after:     {us_after:>10,}")
print(f"Total after:  {total_after:>10,}")

# By section
print(f"\n=== SURVIVING BY SECTION ===")
c.execute("""
    SELECT framework_area, COUNT(*) FROM organizations 
    WHERE status NOT IN ('removed', 'excluded_audit_p1', 'excluded_audit_p2', 'excluded_audit_p3')
    GROUP BY framework_area ORDER BY COUNT(*) DESC
""")
for area, cnt in c.fetchall():
    print(f"  {area or 'unclassified':<25} {cnt:>8,}")

# By country top 20
print(f"\n=== TOP 20 COUNTRIES ===")
c.execute("""
    SELECT country_code, COUNT(*) FROM organizations 
    WHERE status NOT IN ('removed', 'excluded_audit_p1', 'excluded_audit_p2', 'excluded_audit_p3')
    GROUP BY country_code ORDER BY COUNT(*) DESC LIMIT 20
""")
for cc, cnt in c.fetchall():
    print(f"  {cc:<4} {cnt:>8,}")

# Random sample
print(f"\n=== RANDOM SAMPLE (20 survivors) ===")
c.execute("""
    SELECT name, country_code, framework_area, ntee_code FROM organizations 
    WHERE status NOT IN ('removed', 'excluded_audit_p1', 'excluded_audit_p2', 'excluded_audit_p3')
    ORDER BY RANDOM() LIMIT 20
""")
for name, cc, area, ntee in c.fetchall():
    print(f"  [{cc}] {ntee or '?':>4} {area or '?':<20} {name[:70]}")

# Grand total audit summary
print(f"\n=== GRAND AUDIT SUMMARY ===")
for status_val in ['active', 'excluded_audit_p1', 'excluded_audit_p2', 'excluded_audit_p3', 'removed']:
    c.execute("SELECT COUNT(*) FROM organizations WHERE status = ?", (status_val,))
    cnt = c.fetchone()[0]
    if cnt > 0:
        print(f"  {status_val:<25} {cnt:>10,}")

db.close()
