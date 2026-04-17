"""
US state-level Wikidata ingest for Ecolibrium.
Queries Wikidata for notable nonprofits, cooperatives, community orgs, etc.
by US state. The IRS data has 667K orgs but they're all generic tax filings -
this adds the notable, mission-driven orgs with real descriptions and coordinates.
"""
import json
import sqlite3
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import os
from datetime import datetime, timezone

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'
WIKIDATA_ENDPOINT = 'https://query.wikidata.org/sparql'
DONE_FILE = os.path.join(os.path.dirname(__file__), 'us_states_done.txt')

# US states with Wikidata QIDs
US_STATES = {
    'AL': ('Q173', 'Alabama'), 'AK': ('Q797', 'Alaska'), 'AZ': ('Q816', 'Arizona'),
    'AR': ('Q1612', 'Arkansas'), 'CA': ('Q99', 'California'), 'CO': ('Q1261', 'Colorado'),
    'CT': ('Q779', 'Connecticut'), 'DE': ('Q1393', 'Delaware'), 'FL': ('Q812', 'Florida'),
    'GA': ('Q1428', 'Georgia'), 'HI': ('Q782', 'Hawaii'), 'ID': ('Q1221', 'Idaho'),
    'IL': ('Q1204', 'Illinois'), 'IN': ('Q1415', 'Indiana'), 'IA': ('Q1546', 'Iowa'),
    'KS': ('Q1558', 'Kansas'), 'KY': ('Q1603', 'Kentucky'), 'LA': ('Q1588', 'Louisiana'),
    'ME': ('Q724', 'Maine'), 'MD': ('Q1391', 'Maryland'), 'MA': ('Q771', 'Massachusetts'),
    'MI': ('Q1166', 'Michigan'), 'MN': ('Q1527', 'Minnesota'), 'MS': ('Q1494', 'Mississippi'),
    'MO': ('Q1581', 'Missouri'), 'MT': ('Q1212', 'Montana'), 'NE': ('Q1553', 'Nebraska'),
    'NV': ('Q1227', 'Nevada'), 'NH': ('Q759', 'New Hampshire'), 'NJ': ('Q1408', 'New Jersey'),
    'NM': ('Q1522', 'New Mexico'), 'NY': ('Q1384', 'New York'), 'NC': ('Q1454', 'North Carolina'),
    'ND': ('Q1207', 'North Dakota'), 'OH': ('Q1397', 'Ohio'), 'OK': ('Q1649', 'Oklahoma'),
    'OR': ('Q824', 'Oregon'), 'PA': ('Q1400', 'Pennsylvania'), 'RI': ('Q1387', 'Rhode Island'),
    'SC': ('Q1456', 'South Carolina'), 'SD': ('Q1211', 'South Dakota'), 'TN': ('Q1509', 'Tennessee'),
    'TX': ('Q1439', 'Texas'), 'UT': ('Q829', 'Utah'), 'VT': ('Q738', 'Vermont'),
    'VA': ('Q1370', 'Virginia'), 'WA': ('Q1223', 'Washington'), 'WV': ('Q1371', 'West Virginia'),
    'WI': ('Q1537', 'Wisconsin'), 'WY': ('Q1214', 'Wyoming'), 'DC': ('Q3551781', 'District of Columbia'),
}

FILTER_KEYWORDS = [
    'football club', 'soccer club', 'basketball team', 'rugby', 'cricket',
    'association football', 'f.c.', ' fc ', 'sport club', 'sports club',
    'country club', 'golf club', 'yacht club', 'polo club', 'tennis club',
    'diocese', 'archdiocese', 'parish', 'cathedral',
    'roman catholic', 'evangelical church', 'pentecostal church', 'baptist church',
    'political party', 'military', 'armed forces', 'air force base',
    'national team', 'olympic committee', 'beauty pageant',
    'nfl', 'nba', 'mlb', 'nhl', 'mls',
]

FRAMEWORK_KEYWORDS = {
    'healthcare': ['health','clinic','hospital','medical','medicine','nurse','hiv','aids'],
    'food': ['food','farm','agri','seed','nutrition','hunger','agroecol','permaculture'],
    'education': ['education','school','learn','literacy','teach','library','university','college'],
    'ecology': ['environment','ecology','conservation','climate','biodiversity','forest','wildlife'],
    'housing_land': ['housing','shelter','land trust','tenure','homeless','affordable housing','habitat'],
    'democracy': ['democracy','civic','governance','voting','election','human rights','civil liberties','aclu'],
    'cooperatives': ['cooperative','co-op','worker-owned','mutual','solidarity','credit union'],
    'energy_digital': ['energy','solar','wind','renewable','digital','open source','internet'],
    'conflict': ['justice','conflict','mediation','peace','restorative','prison','legal aid'],
    'recreation_arts': ['arts','culture','recreation','sport','music','theater','museum','heritage'],
}


def is_relevant(name, desc):
    combined = (name + ' ' + desc).lower()
    return not any(kw in combined for kw in FILTER_KEYWORDS)


# Alignment scoring constants (mirrors classify_org in run_next_country.py)
_ALIGN_STRONG = ['cooperative', 'co-op', 'mutual aid', 'indigenous', 'agroecol', 'solidarity', 'restorative']
_ALIGN_MOD    = ['community', 'environmental', 'health', 'education', 'housing', 'food', 'energy', 'justice', 'rights']
_ALIGN_NEG    = ['church', 'parish', 'fraternal', 'golf', 'country club', 'hoa', 'booster', 'cemetery']

def _alignment_score(name, desc=''):
    """Compute alignment score for ingest gate (score >= 2 required)."""
    t = ((name or '') + ' ' + (desc or '')).lower()
    s = (sum(3 for k in _ALIGN_STRONG if k in t)
         + sum(1 for k in _ALIGN_MOD if k in t)
         - sum(3 for k in _ALIGN_NEG if k in t))
    return max(-5, min(5, s))


def classify_framework(name, desc):
    combined = (name + ' ' + desc).lower()
    best_area, best_score = None, 0
    for area, keywords in FRAMEWORK_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > best_score:
            best_score = score
            best_area = area
    return best_area or 'democracy'


def run_sparql(query):
    params = urllib.parse.urlencode({'format': 'json', 'query': query})
    url = f'{WIKIDATA_ENDPOINT}?{params}'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Ecolibrium/1.0 (https://github.com/simonlpaige/ecolibrium)',
        'Accept': 'application/sparql-results+json'
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('results', {}).get('bindings', [])
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f'    Rate limited, waiting 60s...')
            time.sleep(60)
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    return data.get('results', {}).get('bindings', [])
            except:
                return []
        print(f'    SPARQL error: {e.code}')
        return []
    except Exception as e:
        print(f'    SPARQL error: {e}')
        return []


QUERIES = [
    # Nonprofits, NGOs, foundations in state
    """
    SELECT DISTINCT ?org ?orgLabel ?desc ?website ?lat ?lon WHERE {{
      VALUES ?type {{ wd:Q163740 wd:Q1127126 wd:Q157031 wd:Q38026614 wd:Q476068 }}
      ?org wdt:P31/wdt:P279* ?type .
      ?org wdt:P131+ wd:{qid} .
      OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
      OPTIONAL {{ ?org wdt:P856 ?website }}
      OPTIONAL {{ ?org p:P625 ?cs . ?cs psv:P625 ?cn . ?cn wikibase:geoLatitude ?lat . ?cn wikibase:geoLongitude ?lon . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    }} LIMIT 500
    """,
    # Cooperatives, credit unions
    """
    SELECT DISTINCT ?org ?orgLabel ?desc ?website ?lat ?lon WHERE {{
      VALUES ?type {{ wd:Q15911314 wd:Q745877 }}
      ?org wdt:P31/wdt:P279* ?type .
      ?org wdt:P131+ wd:{qid} .
      OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
      OPTIONAL {{ ?org wdt:P856 ?website }}
      OPTIONAL {{ ?org p:P625 ?cs . ?cs psv:P625 ?cn . ?cn wikibase:geoLatitude ?lat . ?cn wikibase:geoLongitude ?lon . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    }} LIMIT 300
    """,
    # Hospitals, community health centers
    """
    SELECT DISTINCT ?org ?orgLabel ?desc ?website ?lat ?lon WHERE {{
      VALUES ?type {{ wd:Q16917 wd:Q7075 }}
      ?org wdt:P31/wdt:P279* ?type .
      ?org wdt:P131+ wd:{qid} .
      OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
      OPTIONAL {{ ?org wdt:P856 ?website }}
      OPTIONAL {{ ?org p:P625 ?cs . ?cs psv:P625 ?cn . ?cn wikibase:geoLatitude ?lat . ?cn wikibase:geoLongitude ?lon . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    }} LIMIT 300
    """,
    # Community land trusts, housing organizations
    """
    SELECT DISTINCT ?org ?orgLabel ?desc ?website ?lat ?lon WHERE {{
      VALUES ?type {{ wd:Q667509 wd:Q11707 wd:Q3152824 }}
      ?org wdt:P31/wdt:P279* ?type .
      ?org wdt:P131+ wd:{qid} .
      OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
      OPTIONAL {{ ?org wdt:P856 ?website }}
      OPTIONAL {{ ?org p:P625 ?cs . ?cs psv:P625 ?cn . ?cn wikibase:geoLatitude ?lat . ?cn wikibase:geoLongitude ?lon . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    }} LIMIT 300
    """,
]


def fetch_state(state_code, qid, state_name):
    all_orgs = {}
    for i, qt in enumerate(QUERIES):
        query = qt.format(qid=qid)
        print(f'    Q{i+1}/{len(QUERIES)}...', end=' ')
        results = run_sparql(query)
        print(f'{len(results)} results')
        for r in results:
            name = r.get('orgLabel', {}).get('value', '')
            if not name or (name.startswith('Q') and name[1:].isdigit()):
                continue
            wid = r.get('org', {}).get('value', '').split('/')[-1]
            desc = r.get('desc', {}).get('value', '') if 'desc' in r else ''
            if not is_relevant(name, desc):
                continue
            if wid not in all_orgs:
                lat = r.get('lat', {}).get('value') if 'lat' in r else None
                lon = r.get('lon', {}).get('value') if 'lon' in r else None
                all_orgs[wid] = {
                    'name': name, 'wikidata_id': wid,
                    'description': desc[:500],
                    'website': r.get('website', {}).get('value', '') if 'website' in r else '',
                    'lat': float(lat) if lat else None,
                    'lon': float(lon) if lon else None,
                    'state': state_code, 'state_name': state_name,
                    'framework_area': classify_framework(name, desc),
                }
        time.sleep(3)
    return list(all_orgs.values())


def ingest(orgs, state_code):
    if not orgs:
        return 0
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    rejected = 0
    for org in orgs:
        try:
            # Gate: skip low-signal orgs (score >= 2 required, consistent with DB trim)
            score = _alignment_score(org['name'], org.get('description', ''))
            if score < 2:
                rejected += 1
                continue
            c.execute("SELECT id FROM organizations WHERE name=? AND country_code='US' AND state_province=?",
                      (org['name'], state_code))
            if c.fetchone():
                continue
            c.execute("""INSERT INTO organizations
                (name, country_code, country_name, state_province, description, website,
                 source, source_id, date_added, status, framework_area, model_type,
                 alignment_score, lat, lon, geo_source)
                VALUES (?, 'US', 'United States', ?, ?, ?, 'wikidata', ?, ?, 'active',
                        ?, 'nonprofit', ?, ?, ?, ?)""",
                (org['name'], state_code, org['description'], org['website'],
                 org['wikidata_id'], now, org['framework_area'], score,
                 org.get('lat'), org.get('lon'),
                 'wikidata' if org.get('lat') else None))
            inserted += c.rowcount
        except:
            pass
    if rejected:
        print(f'  Rejected {rejected} low-signal orgs before DB insert')
    db.commit()
    db.close()
    return inserted


def get_done():
    if os.path.exists(DONE_FILE):
        with open(DONE_FILE) as f:
            return set(line.strip() for line in f if line.strip())
    return set()


def mark_done(code):
    with open(DONE_FILE, 'a') as f:
        f.write(code + '\n')


def main():
    done = get_done()
    # Sort by population (biggest states first for most impact)
    priority = ['CA','TX','NY','FL','IL','PA','OH','GA','NC','MI',
                'NJ','VA','WA','AZ','MA','TN','IN','MO','MD','WI',
                'CO','MN','SC','AL','LA','KY','OR','OK','CT','UT',
                'IA','NV','AR','MS','KS','NM','NE','ID','WV','HI',
                'NH','ME','MT','RI','DE','SD','ND','AK','VT','WY','DC']

    for state in priority:
        if state in done or state not in US_STATES:
            continue
        qid, name = US_STATES[state]
        print(f'\n  === {name} ({state}) ===')
        orgs = fetch_state(state, qid, name)
        inserted = ingest(orgs, state)
        mark_done(state)
        print(f'  {name}: {len(orgs)} found, {inserted} new')
        return  # One state per invocation

    print('All US states done!')


if __name__ == '__main__':
    main()
