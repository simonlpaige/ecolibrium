"""
audit-sample.py -- Pull random org samples for USA, India, Spanish-speaking countries.
Writes audit_sample.json for human review + training analysis.
"""
import sqlite3, json, random, os, sys

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'commonweave_directory.db')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'trim_audit', 'audit-sample-2026-04-27.json')

SPANISH = ['MX','CO','AR','CL','PE','VE','EC','BO','PY','UY','DO','GT','HN','SV','NI','CR','PA','CU','ES','PR']

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

def sample_countries(cc_list, n):
    ph = ','.join(['?' for _ in cc_list])
    c.execute(f"""SELECT id, name, country_code, state_province, city, source,
                         framework_area, alignment_score, description, website,
                         registration_id, legibility, model_type, tags
                  FROM organizations
                  WHERE status='active' AND country_code IN ({ph})
                  ORDER BY RANDOM() LIMIT ?""", cc_list + [n])
    return [dict(r) for r in c.fetchall()]

def counts_by_country(cc_list):
    ph = ','.join(['?' for _ in cc_list])
    c.execute(f"""SELECT country_code, COUNT(*) as n
                  FROM organizations WHERE status='active' AND country_code IN ({ph})
                  GROUP BY country_code ORDER BY n DESC""", cc_list)
    return {r['country_code']: r['n'] for r in c.fetchall()}

print('Pulling samples...')
usa   = sample_countries(['US'], 30)
india = sample_countries(['IN'], 30)
latam = sample_countries(SPANISH, 40)

# Spread latam evenly across countries with data
latam_counts = counts_by_country(SPANISH)
print('LatAm by country:', latam_counts)

# Stratified latam sample -- at least 1 per country that has data, rest random
stratified = []
has_data = [cc for cc in SPANISH if latam_counts.get(cc, 0) > 0]
for cc in has_data:
    ph = '?'
    c.execute(f"""SELECT id, name, country_code, state_province, city, source,
                         framework_area, alignment_score, description, website,
                         registration_id, legibility, model_type, tags
                  FROM organizations WHERE status='active' AND country_code={ph}
                  ORDER BY RANDOM() LIMIT 2""", [cc])
    stratified.extend([dict(r) for r in c.fetchall()])

conn.close()

result = {
    'generated': '2026-04-27',
    'purpose': 'Audit sample for USA, India, Spanish-speaking countries -- quality review and ingest training',
    'usa': {'n': len(usa), 'orgs': usa},
    'india': {'n': len(india), 'orgs': india},
    'latam_random': {'n': len(latam), 'orgs': latam},
    'latam_stratified': {'n': len(stratified), 'countries_covered': len(has_data), 'orgs': stratified},
    'latam_counts_by_country': latam_counts,
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f'USA: {len(usa)} | India: {len(india)} | LatAm random: {len(latam)} | LatAm stratified: {len(stratified)} ({len(has_data)} countries)')
print(f'Written to: {OUT}')
