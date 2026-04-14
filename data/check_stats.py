import sqlite3, os, glob

# Find the DB
for f in glob.glob("*.db") + glob.glob("*.sqlite"):
    print(f"DB: {f} ({os.path.getsize(f)} bytes)")

db = "ecolibrium_directory.db"
if not os.path.exists(db):
    print("DB not found, checking parent...")
    db = "../ecolibrium_directory.db"

conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print("Tables:", tables)

if "organizations" in tables:
    c.execute("SELECT status, COUNT(*) FROM organizations GROUP BY status")
    print("By status:", c.fetchall())
    c.execute("SELECT COUNT(DISTINCT country_code) FROM organizations")
    print("Total countries:", c.fetchone()[0])
elif tables:
    for t in tables[:5]:
        c.execute(f"SELECT COUNT(*) FROM [{t}]")
        print(f"  {t}: {c.fetchone()[0]} rows")
        c.execute(f"PRAGMA table_info([{t}])")
        cols = [r[1] for r in c.fetchall()]
        print(f"    cols: {cols[:10]}")
