"""
Export ecolibrium DB + regional files into ecolibrium/DIRECTORY.md
Strategy: curated summary page with stats + regional research embedded.
US data: top orgs per category (not all 689K - that's a separate search tool).
"""
import sqlite3
import os
import glob
import re
from datetime import datetime

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'
REGIONAL_DIR = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\regional'
OUTPUT_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\DIRECTORY.md'
ACTIVE_WHERE = "status='active'"

db = sqlite3.connect(DB_PATH)
c = db.cursor()

c.execute(f"SELECT COUNT(*) FROM organizations WHERE {ACTIVE_WHERE}")
total_orgs = c.fetchone()[0]
c.execute(f"""
    SELECT country_code, COUNT(*)
    FROM organizations
    WHERE {ACTIVE_WHERE} AND country_code IS NOT NULL AND country_code != ''
    GROUP BY country_code
""")
country_counts = {code: count for code, count in c.fetchall()}

c.execute(f"SELECT COUNT(*) FROM organizations WHERE country_code='US' AND {ACTIVE_WHERE}")
us_total_orgs = c.fetchone()[0]

regional_files = sorted(glob.glob(os.path.join(REGIONAL_DIR, 'DIRECTORY_*.md')))
regional_countries = len(regional_files)

now = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')

def get_country_name(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
    # "# 🇧🇴 Bolivia (BO) Civil Society Directory" -> "Bolivia"
    m = re.search(r'# .+? (.+?) \(', first_line)
    return m.group(1) if m else os.path.basename(filepath)

lines = []
lines.append("# 🌍 Ecolibrium Global Civil Society Directory\n")
lines.append(f"*Last updated: {now}*\n")
lines.append("")

# Build coverage table
lines.append("## Coverage\n")
lines.append("| Country / Region | Organizations | Source | Status |")
lines.append("|-----------------|--------------|--------|--------|")
lines.append(f"| 🇺🇸 United States | {us_total_orgs:,} | IRS EO Business Master File | ✅ Complete |")

for f in regional_files:
    cc = re.search(r'DIRECTORY_([A-Z]+)\.md', os.path.basename(f))
    code = cc.group(1) if cc else '??'
    country = get_country_name(f)
    n = country_counts.get(code, 0)
    lines.append(f"| 🌐 {country} ({code}) | {n:,} | Field Research | ✅ |")

# Planned countries (from Paperclip todo issues)
lines.append("| 🌐 Ecuador, Kenya, Bangladesh, Indonesia... | TBD | In progress | 🔄 |")
lines.append("")
lines.append(f"**Total: {total_orgs:,} organizations indexed** across {len(country_counts):,} countries\n")
lines.append("")
lines.append("---\n")

# US section - top orgs by NTEE category (not all 689K)
lines.append("## 🇺🇸 United States\n")
lines.append(f"*{us_total_orgs:,} active registered nonprofits from IRS EO Business Master File (all 53 state/territory files)*\n")
lines.append("")
lines.append("### Top Organizations by Category\n")

NTEE_CATEGORIES = {
    'A': 'Arts, Culture & Humanities',
    'B': 'Education',
    'C': 'Environment',
    'D': 'Animal-Related',
    'E': 'Health Care',
    'F': 'Mental Health',
    'G': 'Disease & Disorder Research',
    'H': 'Medical Research',
    'I': 'Crime & Legal-Related',
    'J': 'Employment',
    'K': 'Food, Agriculture & Nutrition',
    'L': 'Housing & Shelter',
    'M': 'Public Safety',
    'N': 'Recreation & Sports',
    'O': 'Youth Development',
    'P': 'Human Services',
    'Q': 'International & Foreign Affairs',
    'R': 'Civil Rights & Advocacy',
    'S': 'Community Improvement',
    'T': 'Philanthropy & Voluntarism',
    'U': 'Science & Technology',
    'V': 'Social Science',
    'W': 'Public & Societal Benefit',
    'X': 'Religion',
    'Y': 'Mutual & Membership Benefit',
    'Z': 'Unknown/Unclassified',
}

for code, name in NTEE_CATEGORIES.items():
    c.execute("""
        SELECT COUNT(*) FROM organizations
        WHERE country_code='US' AND status='active' AND ntee_code LIKE ?
    """, (f'{code}%',))
    cat_count = c.fetchone()[0]
    if cat_count == 0:
        continue
    
    lines.append(f"\n#### {name} ({cat_count:,} orgs)\n")
    
    # Top 20 with highest revenue
    c.execute("""
        SELECT name, city, state_province, ntee_code, website, annual_revenue
        FROM organizations
        WHERE country_code='US' AND status='active' AND ntee_code LIKE ?
          AND name IS NOT NULL AND name != ''
        ORDER BY COALESCE(annual_revenue, 0) DESC
        LIMIT 20
    """, (f'{code}%',))
    orgs = c.fetchall()
    
    for name_org, city, state, ntee, website, revenue in orgs:
        loc = f"{city}, {state}" if city and state else (state or city or '')
        loc_str = f" — {loc}" if loc else ''
        ntee_str = f" `{ntee}`" if ntee else ''
        rev_str = f" (${revenue:,.0f}/yr)" if revenue and revenue > 0 else ''
        ws_str = f" [{website}]({website})" if website and str(website).startswith('http') else ''
        lines.append(f"- **{name_org}**{loc_str}{ntee_str}{rev_str}{ws_str}")

lines.append("")
lines.append("---\n")

# Regional research sections
lines.append("## 🌐 International Research\n")
lines.append("*Compiled via structured web research, official nonprofit registries, and field sources*\n")
lines.append("")

for f in regional_files:
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    lines.append(content)
    lines.append("\n---\n")

db.close()

output = '\n'.join(lines)
with open(OUTPUT_PATH, 'w', encoding='utf-8') as fh:
    fh.write(output)

size_kb = os.path.getsize(OUTPUT_PATH) / 1024
print(f"Written: {OUTPUT_PATH}")
print(f"Size: {size_kb:.0f} KB")
print(f"Lines: {len(lines)}")
