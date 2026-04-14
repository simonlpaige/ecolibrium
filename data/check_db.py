import sqlite3
conn = sqlite3.connect('ecolibrium_directory.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  {t}: {cur.fetchone()[0]} rows")
    # Get most recent entries
    try:
        cur.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 3")
        cols = [d[0] for d in cur.description]
        print(f"  Cols: {cols}")
        for row in cur.fetchall():
            print(f"    {row}")
    except Exception as e:
        print(f"  Error: {e}")
conn.close()
