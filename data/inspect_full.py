import sqlite3
db = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db')
db.row_factory = sqlite3.Row
c = db.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('TABLES:', [r[0] for r in c.fetchall()])

c.execute('SELECT COUNT(*) as n FROM organizations'); print('Total orgs:', c.fetchone()[0])

c.execute('PRAGMA table_info(organizations)')
cols = [r['name'] for r in c.fetchall()]
print('COLUMNS:', cols)

c.execute('SELECT country_code, COUNT(*) as n FROM organizations GROUP BY country_code ORDER BY n DESC LIMIT 15')
print('\nCOUNTRY BREAKDOWN:')
for r in c.fetchall(): print(f'  {r[0]}: {r[1]:,}')

c.execute('SELECT framework_area, COUNT(*) as n FROM organizations GROUP BY framework_area ORDER BY n DESC')
print('\nFRAMEWORK_AREA:')
for r in c.fetchall(): print(f'  {r[0]!r}: {r[1]:,}')

c.execute('SELECT source, COUNT(*) as n FROM organizations GROUP BY source ORDER BY n DESC')
print('\nSOURCES:')
for r in c.fetchall(): print(f'  {r[0]}: {r[1]:,}')

for field in ['website','city','state_province','description','ntee_code','icnpo_code','annual_revenue']:
    try:
        c.execute(f'SELECT COUNT(*) as n FROM organizations WHERE {field} IS NOT NULL AND {field} != ""')
        print(f'  {field} filled: {c.fetchone()[0]:,}')
    except Exception as e:
        print(f'  {field}: missing - {e}')

# Check for lat/lon columns
try:
    c.execute('SELECT COUNT(*) as n FROM organizations WHERE lat IS NOT NULL')
    print('HAS LAT:', c.fetchone()[0])
except:
    print('NO lat/lon columns')

# Sample international org to see what data looks like
c.execute("SELECT name, country_code, city, description, website, framework_area, ntee_code, source FROM organizations WHERE country_code != 'US' LIMIT 5")
print('\nSAMPLE INTL ORGS:')
for r in c.fetchall():
    print(dict(r))

db.close()
