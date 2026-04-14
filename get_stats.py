import sqlite3
db = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db')
c = db.cursor()
c.execute("SELECT COUNT(*) FROM organizations WHERE status != 'removed'")
active = c.fetchone()[0]
c.execute("SELECT COUNT(DISTINCT country_code) FROM organizations WHERE status != 'removed'")
countries = c.fetchone()[0]
print(f'ACTIVE={active}')
print(f'COUNTRIES={countries}')
db.close()
