import sqlite3
conn = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\commonweave\data\commonweave_directory.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print('Tables:', tables)
for (t,) in tables:
    c.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  {t}: {c.fetchone()[0]} rows")
conn.close()
