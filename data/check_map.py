import sqlite3
db = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db')
c = db.cursor()

c.execute("SELECT alignment_score, COUNT(*) FROM organizations WHERE status='active' AND lat IS NOT NULL AND lon IS NOT NULL GROUP BY alignment_score ORDER BY alignment_score")
for r in c.fetchall():
    print(r)

print("---")
c.execute("SELECT COUNT(*) FROM organizations WHERE status='active' AND lat IS NOT NULL AND lon IS NOT NULL AND alignment_score >= 2")
print("Score>=2:", c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM organizations WHERE status='active' AND lat IS NOT NULL AND lon IS NOT NULL AND alignment_score >= 1")
print("Score>=1:", c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM organizations WHERE status='active' AND lat IS NOT NULL AND lon IS NOT NULL AND verified=1")
print("Verified+coords:", c.fetchone()[0])

# What does the current map generation script look like?
c.execute("SELECT COUNT(*) FROM organizations WHERE status='active' AND lat IS NOT NULL AND lon IS NOT NULL AND (description IS NOT NULL AND description != '')")
print("Has desc+coords:", c.fetchone()[0])

# Sample some high-alignment orgs
c.execute("SELECT name, framework_area, alignment_score, source FROM organizations WHERE status='active' AND lat IS NOT NULL AND alignment_score >= 3 LIMIT 10")
for r in c.fetchall():
    print(r)

db.close()
