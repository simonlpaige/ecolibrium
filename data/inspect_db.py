import sqlite3
db = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db')
c = db.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print('Tables:', tables)
for t in tables:
    c.execute(f'SELECT COUNT(*) FROM "{t}"')
    print(f'  {t}:', c.fetchone()[0])
if 'organizations' in tables:
    c.execute('SELECT * FROM organizations LIMIT 1')
    cols = [d[0] for d in c.description]
    print('Org cols:', ', '.join(cols))
    c.execute('SELECT country_code, COUNT(*) as n FROM organizations GROUP BY country_code ORDER BY n DESC LIMIT 15')
    rows = c.fetchall()
    print('Top countries:', rows)
db.close()
