import sqlite3
conn = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db')
c = conn.cursor()

# Add missing columns
for col, typedef in [('phone','TEXT'),('icnpo_code','TEXT'),('employee_count','INTEGER')]:
    try:
        c.execute(f'ALTER TABLE organizations ADD COLUMN {col} {typedef}')
        print(f'Added: {col}')
    except: print(f'Skip: {col}')

# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT, url TEXT, org_count INTEGER,
    coverage TEXT, last_pulled TEXT, notes TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS framework_areas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE, name TEXT, description TEXT)''')

areas = [
    ('democracy','Democratic Infrastructure & Governance','Civic participation, voting, transparency, human rights, governance'),
    ('cooperatives','Wealth Distribution / UBI / Cooperatives','Worker-owned orgs, mutual aid, basic income, credit unions, solidarity economy'),
    ('healthcare','Healthcare','Community health, mental health, medical research, disability'),
    ('food','Food Distribution & Sovereignty','Food banks, agroecology, food sovereignty, hunger, seed saving'),
    ('education','Education','Schools, literacy, open education, libraries, training'),
    ('housing_land','Housing & Land Stewardship','Affordable housing, community land trusts, homelessness, land rights'),
    ('conflict','Conflict Resolution & Restorative Justice','Peacebuilding, mediation, restorative justice, prison reform'),
    ('energy_digital','Energy & Digital Commons','Community energy, renewable co-ops, open source, digital rights'),
    ('recreation_arts','Recreation, Art & Humanities','Arts, culture, museums, public space, creative commons'),
    ('ecology','Ecological Restoration & Environment','Conservation, rewilding, climate, biodiversity, watershed'),
    ('cross_cutting','Cross-Cutting / Human Services','Multi-area, international development, philanthropy, public benefit'),
]
c.executemany('INSERT OR IGNORE INTO framework_areas (code,name,description) VALUES (?,?,?)', areas)

c.execute('''INSERT OR IGNORE INTO sources (name,url,org_count,coverage,last_pulled,notes) VALUES (?,?,?,?,date('now'),?)''',
    ('IRS_EO_BMF','https://www.irs.gov/pub/irs-soi/eo_{state}.csv',688429,'USA all 53 files','688K filtered from 1.95M total'))

conn.commit()
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print('Tables:', tables)
count = conn.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]
print(f'Org count: {count:,}')
conn.close()
print('Done.')
