import sqlite3
conn = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\commonweave\data\commonweave_directory.db')
c = conn.cursor()
c.execute("PRAGMA table_info(organizations)")
cols = [row[1] for row in c.fetchall()]
print('Columns:', cols)
# Check for CN orgs
country_col = None
for col in cols:
    if 'country' in col.lower() or col.lower() == 'cc':
        country_col = col
        break
print('Country column:', country_col)
if country_col:
    c.execute(f"SELECT COUNT(*) FROM organizations WHERE {country_col}='CN'")
    print('CN orgs:', c.fetchone()[0])
# Show most recent countries
c.execute(f"SELECT {country_col}, COUNT(*) FROM organizations GROUP BY {country_col} ORDER BY COUNT(*) DESC LIMIT 10")
print('Top countries:', c.fetchall())
conn.close()
