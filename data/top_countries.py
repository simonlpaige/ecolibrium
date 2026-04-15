import sqlite3
db = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db')
c = db.cursor()
c.execute("SELECT country_code, COUNT(*) as cnt FROM organizations WHERE status != 'removed' GROUP BY country_code ORDER BY cnt DESC LIMIT 20")
for r in c.fetchall():
    print(f"{r[0]}: {r[1]:,}")
print()
c.execute("SELECT COUNT(*) FROM organizations WHERE status != 'removed' AND country_code = 'IN'")
india = c.fetchone()[0]
print(f"India total: {india:,}")
c.execute("SELECT framework_area, COUNT(*) FROM organizations WHERE status != 'removed' AND country_code = 'IN' GROUP BY framework_area ORDER BY COUNT(*) DESC")
print("India by section:")
for area, cnt in c.fetchall():
    print(f"  {area}: {cnt:,}")
db.close()
