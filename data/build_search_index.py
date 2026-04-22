"""
Build static JSON search indexes from ecolibrium_directory.db + regional markdown files.
Output:
  data/search/index.json      - country list + stats (lightweight, loaded on page load)
  data/search/US.json         - US orgs (chunked by state, loaded on demand)
  data/search/KE.json         - Kenya orgs (from DB + regional MD)
  data/search/BO.json         - Bolivia orgs
  ... etc for each country
"""
import sqlite3
import json
import os
import re
import glob
from datetime import datetime

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'
REGIONAL_DIR = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\regional'
OUTPUT_DIR = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\search'
ECOLIBRIUM_DIR = r'C:\Users\simon\.openclaw\workspace\ecolibrium'
ACTIVE_WHERE = "status='active'"

os.makedirs(OUTPUT_DIR, exist_ok=True)

db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row
c = db.cursor()

NTEE_NAMES = {
    'A': 'Arts & Culture', 'B': 'Education', 'C': 'Environment',
    'D': 'Animal-Related', 'E': 'Health Care', 'F': 'Mental Health',
    'G': 'Disease Research', 'H': 'Medical Research', 'I': 'Crime & Legal',
    'J': 'Employment', 'K': 'Food & Agriculture', 'L': 'Housing & Shelter',
    'M': 'Public Safety', 'N': 'Recreation & Sports', 'O': 'Youth Dev',
    'P': 'Human Services', 'Q': 'International Affairs', 'R': 'Civil Rights',
    'S': 'Community Dev', 'T': 'Philanthropy', 'U': 'Science & Tech',
    'V': 'Social Science', 'W': 'Public Benefit', 'X': 'Religion',
    'Y': 'Mutual Benefit', 'Z': 'Unknown',
}

US_STATE_NAMES = {
    'AK':'Alaska','AL':'Alabama','AR':'Arkansas','AZ':'Arizona','CA':'California',
    'CO':'Colorado','CT':'Connecticut','DC':'District of Columbia','DE':'Delaware',
    'FL':'Florida','GA':'Georgia','HI':'Hawaii','IA':'Iowa','ID':'Idaho',
    'IL':'Illinois','IN':'Indiana','KS':'Kansas','KY':'Kentucky','LA':'Louisiana',
    'MA':'Massachusetts','MD':'Maryland','ME':'Maine','MI':'Michigan','MN':'Minnesota',
    'MO':'Missouri','MS':'Mississippi','MT':'Montana','NC':'North Carolina',
    'ND':'North Dakota','NE':'Nebraska','NH':'New Hampshire','NJ':'New Jersey',
    'NM':'New Mexico','NV':'Nevada','NY':'New York','OH':'Ohio','OK':'Oklahoma',
    'OR':'Oregon','PA':'Pennsylvania','PR':'Puerto Rico','RI':'Rhode Island',
    'SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas',
    'UT':'Utah','VA':'Virginia','VT':'Vermont','WA':'Washington','WI':'Wisconsin',
    'WV':'West Virginia','WY':'Wyoming'
}

# ── 1. Country index ──────────────────────────────────────────────────────────
print("Building country index...")

c.execute(f"SELECT COUNT(*) FROM organizations WHERE {ACTIVE_WHERE}")
total_orgs = c.fetchone()[0]

c.execute("""
    SELECT country_code, country_name, COUNT(*) as n
    FROM organizations
    WHERE country_code IS NOT NULL AND country_code != '' AND status='active'
    GROUP BY country_code
    ORDER BY n DESC
""")
db_countries = {r['country_code']: {'name': r['country_name'] or r['country_code'], 'count': r['n']} for r in c.fetchall()}

# Add regional markdown countries
regional_files = sorted(glob.glob(os.path.join(REGIONAL_DIR, 'DIRECTORY_*.md')))
regional_countries = {}
for f in regional_files:
    cc = re.search(r'DIRECTORY_([A-Z]+)\.md', os.path.basename(f))
    if not cc:
        continue
    code = cc.group(1)
    if len(code) > 3 or code == 'P2':
        continue  # skip bogus codes
    with open(f, encoding='utf-8') as fh:
        content = fh.read()
    # Get country name
    m = re.search(r'# .+? (.+?) \(', content)
    name = m.group(1).strip() if m else code
    db_count = db_countries.get(code, {}).get('count', 0)
    if db_count > 0:
        regional_countries[code] = {'name': name, 'count': db_count, 'source': 'research'}

# Merge: DB countries + regional countries
all_countries = {}
for code, info in db_countries.items():
    all_countries[code] = {**info, 'source': 'registry', 'has_data': True}
for code, info in regional_countries.items():
    if code in all_countries:
        all_countries[code]['research_count'] = info['count']
        all_countries[code]['has_research'] = True
    else:
        all_countries[code] = {**info, 'has_data': True}

index = {
    'generated': datetime.utcnow().isoformat() + 'Z',
    'total_orgs': total_orgs,
    'total_countries': len(all_countries),
    'countries': all_countries,
    'ntee_categories': NTEE_NAMES,
}

with open(os.path.join(OUTPUT_DIR, 'index.json'), 'w', encoding='utf-8') as f:
    json.dump(index, f, separators=(',', ':'))
print(f"  index.json: {len(all_countries)} countries, {total_orgs:,} orgs")

# ── 2. US data: chunked by state ──────────────────────────────────────────────
print("Building US state index...")
c.execute("""
    SELECT state_province, COUNT(*) as n
    FROM organizations
    WHERE country_code='US' AND status='active' AND state_province IS NOT NULL AND state_province != ''
    GROUP BY state_province ORDER BY state_province
""")
states = {r['state_province']: r['n'] for r in c.fetchall()}

c.execute(f"SELECT COUNT(*) FROM organizations WHERE country_code='US' AND {ACTIVE_WHERE}")
us_total_orgs = c.fetchone()[0]

us_meta = {
    'country_code': 'US',
    'country_name': 'United States',
    'total': us_total_orgs,
    'source': 'IRS EO Business Master File',
    'states': {code: {'name': US_STATE_NAMES.get(code, code), 'count': n} for code, n in states.items()},
    'ntee_counts': {}
}

# NTEE category counts
for letter in NTEE_NAMES:
    c.execute(f"SELECT COUNT(*) FROM organizations WHERE country_code='US' AND {ACTIVE_WHERE} AND ntee_code LIKE ?", (f'{letter}%',))
    us_meta['ntee_counts'][letter] = c.fetchone()[0]

with open(os.path.join(OUTPUT_DIR, 'US_meta.json'), 'w', encoding='utf-8') as f:
    json.dump(us_meta, f, separators=(',', ':'))
print(f"  US_meta.json: {len(states)} states")

# Per-state JSON files (loaded on demand when user selects a state)
for state_code, state_count in states.items():
    c.execute("""
        SELECT name, city, ntee_code, website, annual_revenue, description, registration_id
        FROM organizations
        WHERE country_code='US' AND status='active' AND state_province=?
        ORDER BY COALESCE(annual_revenue,0) DESC, name ASC
    """, (state_code,))
    orgs = []
    for row in c.fetchall():
        org = {
            'n': row['name'],
            'c': row['city'] or '',
            't': row['ntee_code'] or '',
            'w': row['website'] or '',
            'r': int(row['annual_revenue']) if row['annual_revenue'] else 0,
        }
        if row['description']:
            org['d'] = row['description'][:200]
        orgs.append(org)
    
    state_data = {
        'state': state_code,
        'name': US_STATE_NAMES.get(state_code, state_code),
        'count': state_count,
        'orgs': orgs
    }
    out_path = os.path.join(OUTPUT_DIR, f'US_{state_code}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(state_data, f, separators=(',', ':'))

total_state_files = len(states)
print(f"  {total_state_files} state JSON files written")

# ── 3. Regional research countries ───────────────────────────────────────────
print("Building regional country files...")
for f in regional_files:
    cc = re.search(r'DIRECTORY_([A-Z]+)\.md', os.path.basename(f))
    if not cc:
        continue
    code = cc.group(1)
    if len(code) > 3 or code == 'P2':
        continue
    
    with open(f, encoding='utf-8') as fh:
        content = fh.read()
    
    # Parse org entries - handles both ### headers and table rows
    orgs = []
    seen_names = set()
    current_org = None
    lines = content.split('\n')
    in_table = False
    table_headers = []
    
    for line in lines:
        # ### header format
        if line.startswith('### '):
            if current_org and current_org['n'] not in seen_names:
                orgs.append(current_org)
                seen_names.add(current_org['n'])
            current_org = {'n': line[4:].strip(), 'd': '', 'w': ''}
        elif current_org and line.startswith('> '):
            current_org['d'] = line[2:].strip()[:200]
        elif current_org and 'http' in line:
            m = re.search(r'https?://[^\s\)\|]+', line)
            if m:
                current_org['w'] = m.group(0)
        # Table format: | Name | Location | ... |
        elif line.startswith('|') and '|' in line[1:]:
            cells = [c.strip() for c in line.strip('|').split('|')]
            if not cells or not cells[0]:
                continue
            # Detect header row
            if cells[0].lower() in ('name', 'organization', 'org'):
                table_headers = [h.lower() for h in cells]
                in_table = True
                continue
            # Skip separator rows
            if all(set(c) <= set('-: ') for c in cells if c):
                continue
            if in_table and len(cells) >= 2:
                name = cells[0]
                if not name or name.startswith('Found via') or len(name) < 3:
                    continue
                # Clean up encoding artifacts
                name = name.replace('\ufffd', '').strip()
                if not name or name in seen_names:
                    continue
                org = {'n': name, 'd': '', 'w': ''}
                # Try to get description (usually col 3 or 4)
                if len(cells) > 3:
                    desc = cells[3].strip()
                    if desc and not desc.startswith('Found via') and len(desc) > 5:
                        org['d'] = desc[:200]
                # Try to get website
                for cell in cells:
                    if 'http' in cell:
                        m = re.search(r'https?://[^\s\)\|]+', cell)
                        if m:
                            org['w'] = m.group(0)
                            break
                orgs.append(org)
                seen_names.add(name)
        else:
            if current_org and line.strip() == '':
                pass  # keep current_org open
    
    if current_org and current_org['n'] not in seen_names:
        orgs.append(current_org)
    
    # Get country name
    name_m = re.search(r'# .+? (.+?) \(', content)
    country_name = name_m.group(1).strip() if name_m else code

    # Merge with DB orgs (Wikidata ingest etc.) - DB takes priority, markdown fills gaps
    db.row_factory = sqlite3.Row
    dc = db.cursor()
    dc.execute("""
        SELECT name, description, website, city, framework_area, alignment_score
        FROM organizations
        WHERE country_code=? AND status='active'
        ORDER BY COALESCE(alignment_score,0) DESC, name ASC
    """, (code,))
    db_orgs_seen = set(o['n'] for o in orgs)
    for row in dc.fetchall():
        if row['name'] and row['name'] not in db_orgs_seen:
            org = {'n': row['name'], 'd': (row['description'] or '')[:200], 'w': row['website'] or ''}
            orgs.append(org)
            db_orgs_seen.add(row['name'])

    country_data = {
        'country_code': code,
        'country_name': country_name,
        'source': 'Field research + Wikidata' if len(orgs) > 1 else 'Field research',
        'count': len(orgs),
        'orgs': orgs
    }
    out_path = os.path.join(OUTPUT_DIR, f'{code}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(country_data, f, ensure_ascii=False, separators=(',', ':'))
    print(f"  {code}.json: {len(orgs)} orgs")

db.close()

# ── Summary ───────────────────────────────────────────────────────────────────
files = os.listdir(OUTPUT_DIR)
total_size = sum(os.path.getsize(os.path.join(OUTPUT_DIR, fn)) for fn in files)
print(f"\nDone: {len(files)} files, {total_size/1024/1024:.1f} MB total in {OUTPUT_DIR}")
print("Largest files:")
sizes = [(fn, os.path.getsize(os.path.join(OUTPUT_DIR, fn))) for fn in files]
for fn, sz in sorted(sizes, key=lambda x: -x[1])[:5]:
    print(f"  {fn}: {sz/1024:.0f} KB")
