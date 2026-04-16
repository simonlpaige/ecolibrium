import sqlite3
db = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db')
c = db.cursor()

# Quick sample at score 2
c.execute("SELECT name, framework_area, ntee_code FROM organizations WHERE source='IRS_EO_BMF' AND alignment_score=2 LIMIT 10")
print("=== SCORE 2 ===")
for r in c.fetchall():
    print(f"  {r[0][:55]:55s} | {r[1]:18s} | {r[2]}")

c.execute("SELECT name, framework_area, ntee_code FROM organizations WHERE source='IRS_EO_BMF' AND alignment_score=3 LIMIT 10")
print("\n=== SCORE 3 ===")
for r in c.fetchall():
    print(f"  {r[0][:55]:55s} | {r[1]:18s} | {r[2]}")

c.execute("SELECT name, framework_area, ntee_code FROM organizations WHERE source='IRS_EO_BMF' AND alignment_score=4 LIMIT 10")
print("\n=== SCORE 4 ===")
for r in c.fetchall():
    print(f"  {r[0][:55]:55s} | {r[1]:18s} | {r[2]}")

c.execute("SELECT name, framework_area, ntee_code FROM organizations WHERE source='IRS_EO_BMF' AND alignment_score=5 LIMIT 10")
print("\n=== SCORE 5 ===")
for r in c.fetchall():
    print(f"  {r[0][:55]:55s} | {r[1]:18s} | {r[2]}")

c.execute("SELECT name, framework_area, ntee_code FROM organizations WHERE source='IRS_EO_BMF' AND alignment_score>=6 LIMIT 10")
print("\n=== SCORE 6+ ===")
for r in c.fetchall():
    print(f"  {r[0][:55]:55s} | {r[1]:18s} | {r[2]}")

# Non-IRS with coords
c.execute("SELECT source, COUNT(*) FROM organizations WHERE status='active' AND lat IS NOT NULL AND source != 'IRS_EO_BMF' GROUP BY source")
print("\n=== NON-IRS WITH COORDS ===")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")

db.close()
