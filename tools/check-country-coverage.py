"""Check which countries are below the scarcity threshold after the cutline run."""
import sqlite3, os
conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'commonweave_directory.db'))
c = conn.cursor()
c.execute("SELECT country_code, COUNT(*) as n FROM organizations WHERE status='active' GROUP BY country_code ORDER BY n")
rows = c.fetchall()
thin = [(cc, n) for cc, n in rows if n <= 50]
print(f'Countries with <= 50 active orgs: {len(thin)}')
for cc, n in thin:
    print(f'  {cc}: {n}')
print(f'\nTotal countries: {len(rows)}')
conn.close()
