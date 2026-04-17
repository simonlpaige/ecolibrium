"""
Wikidata SPARQL ingest for Ecolibrium.
Queries multiple org types per country - nonprofits, cooperatives, NGOs, trade unions,
environmental orgs, community orgs, foundations, etc.
Free, no API key, returns structured data with descriptions and coordinates.
"""
import json
import sqlite3
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'
WIKIDATA_ENDPOINT = 'https://query.wikidata.org/sparql'

# ISO 3166-1 alpha-2 to Wikidata country QID
COUNTRY_QID = {
    'CR':'Q800','MX':'Q96','CO':'Q739','AR':'Q414','PE':'Q419',
    'CL':'Q298','VE':'Q717','BO':'Q750','EC':'Q736','PY':'Q733',
    'UY':'Q77','GT':'Q774','HN':'Q783','NI':'Q811','PA':'Q804',
    'CU':'Q241','DO':'Q786','SR':'Q730','GY':'Q734','BR':'Q155',
    'IN':'Q668','BD':'Q902','NP':'Q837','LK':'Q854','PK':'Q843',
    'ID':'Q252','PH':'Q928','VN':'Q881','TH':'Q869','KH':'Q424',
    'MM':'Q836','MY':'Q833','CN':'Q148','JP':'Q17','KR':'Q884',
    'TW':'Q865','DE':'Q183','FR':'Q142','GB':'Q145','IT':'Q38',
    'ES':'Q29','PL':'Q36','UA':'Q212','TR':'Q43','EG':'Q79',
    'MA':'Q1028','GH':'Q117','ET':'Q115','TZ':'Q924','UG':'Q1036',
    'RW':'Q1037','MZ':'Q1029','ZM':'Q953','ZA':'Q258','KE':'Q114',
    'NG':'Q1033','SN':'Q1041','CI':'Q1008','CM':'Q1009','MG':'Q1019',
    'TN':'Q948','JO':'Q810','LB':'Q822','CA':'Q16','AU':'Q408',
    'NZ':'Q664','FJ':'Q712','PG':'Q691','JM':'Q766','TT':'Q754',
    'HT':'Q790','SE':'Q34','NO':'Q20','DK':'Q35','FI':'Q33',
    'CH':'Q39','AT':'Q40','IE':'Q27','NL':'Q55','BE':'Q31',
    'PT':'Q45','GR':'Q41','RO':'Q218','HU':'Q28','RS':'Q403',
    'BG':'Q219','GE':'Q230','AM':'Q399','KZ':'Q232','UZ':'Q265',
}

# Wikidata classes that represent org types we care about
ORG_TYPES = [
    ('Q163740', 'nonprofit'),        # nonprofit organization
    ('Q4830453', 'cooperative'),      # business (too broad alone, but subclassed)
    ('Q49773', 'cooperative'),        # social movement
    ('Q15911314', 'cooperative'),     # cooperative
    ('Q7210356', 'cooperative'),      # political organization
    ('Q2659904', 'nonprofit'),        # government agency (some overlap)
    ('Q43229', 'nonprofit'),          # organization (very broad - use with country filter)
    ('Q476068', 'nonprofit'),         # environmental organization
    ('Q708676', 'nonprofit'),         # workers' union / trade union
    ('Q1127126', 'nonprofit'),        # international NGO
    ('Q38026614', 'foundation'),      # foundation (charity)
    ('Q157031', 'foundation'),        # foundation
    ('Q484652', 'nonprofit'),         # international organization
    ('Q11032', 'nonprofit'),          # newspaper (skip)
]

# More targeted queries that return better results
SPARQL_QUERIES = [
    # Nonprofits, NGOs, foundations
    """
    SELECT DISTINCT ?org ?orgLabel ?desc ?website ?lat ?lon ?inception WHERE {{
      VALUES ?type {{ wd:Q163740 wd:Q1127126 wd:Q157031 wd:Q38026614 wd:Q476068 }}
      ?org wdt:P31/wdt:P279* ?type .
      ?org wdt:P17 wd:{qid} .
      OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
      OPTIONAL {{ ?org wdt:P856 ?website }}
      OPTIONAL {{ ?org p:P625 ?coordStmt . ?coordStmt psv:P625 ?coordNode .
                  ?coordNode wikibase:geoLatitude ?lat . ?coordNode wikibase:geoLongitude ?lon . }}
      OPTIONAL {{ ?org wdt:P571 ?inception }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,es,fr,pt,de" }}
    }} LIMIT 500
    """,
    # Cooperatives
    """
    SELECT DISTINCT ?org ?orgLabel ?desc ?website ?lat ?lon ?inception WHERE {{
      ?org wdt:P31/wdt:P279* wd:Q15911314 .
      ?org wdt:P17 wd:{qid} .
      OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
      OPTIONAL {{ ?org wdt:P856 ?website }}
      OPTIONAL {{ ?org p:P625 ?coordStmt . ?coordStmt psv:P625 ?coordNode .
                  ?coordNode wikibase:geoLatitude ?lat . ?coordNode wikibase:geoLongitude ?lon . }}
      OPTIONAL {{ ?org wdt:P571 ?inception }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,es,fr,pt,de" }}
    }} LIMIT 500
    """,
    # Trade unions, workers' organizations
    """
    SELECT DISTINCT ?org ?orgLabel ?desc ?website ?lat ?lon ?inception WHERE {{
      VALUES ?type {{ wd:Q708676 wd:Q178790 }}
      ?org wdt:P31/wdt:P279* ?type .
      ?org wdt:P17 wd:{qid} .
      OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
      OPTIONAL {{ ?org wdt:P856 ?website }}
      OPTIONAL {{ ?org p:P625 ?coordStmt . ?coordStmt psv:P625 ?coordNode .
                  ?coordNode wikibase:geoLatitude ?lat . ?coordNode wikibase:geoLongitude ?lon . }}
      OPTIONAL {{ ?org wdt:P571 ?inception }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,es,fr,pt,de" }}
    }} LIMIT 500
    """,
    # Educational institutions, research institutes
    """
    SELECT DISTINCT ?org ?orgLabel ?desc ?website ?lat ?lon ?inception WHERE {{
      VALUES ?type {{ wd:Q31855 wd:Q3918 wd:Q1664720 }}
      ?org wdt:P31/wdt:P279* ?type .
      ?org wdt:P17 wd:{qid} .
      OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
      OPTIONAL {{ ?org wdt:P856 ?website }}
      OPTIONAL {{ ?org p:P625 ?coordStmt . ?coordStmt psv:P625 ?coordNode .
                  ?coordNode wikibase:geoLatitude ?lat . ?coordNode wikibase:geoLongitude ?lon . }}
      OPTIONAL {{ ?org wdt:P571 ?inception }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,es,fr,pt,de" }}
    }} LIMIT 300
    """,
    # Community organizations, social enterprises, mutual aid
    """
    SELECT DISTINCT ?org ?orgLabel ?desc ?website ?lat ?lon ?inception WHERE {{
      VALUES ?type {{ wd:Q49773 wd:Q7210356 wd:Q15925165 }}
      ?org wdt:P31/wdt:P279* ?type .
      ?org wdt:P17 wd:{qid} .
      OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
      OPTIONAL {{ ?org wdt:P856 ?website }}
      OPTIONAL {{ ?org p:P625 ?coordStmt . ?coordStmt psv:P625 ?coordNode .
                  ?coordNode wikibase:geoLatitude ?lat . ?coordNode wikibase:geoLongitude ?lon . }}
      OPTIONAL {{ ?org wdt:P571 ?inception }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,es,fr,pt,de" }}
    }} LIMIT 300
    """,
    # Hospitals, clinics, health organizations
    """
    SELECT DISTINCT ?org ?orgLabel ?desc ?website ?lat ?lon ?inception WHERE {{
      VALUES ?type {{ wd:Q16917 wd:Q7075 wd:Q35535 }}
      ?org wdt:P31/wdt:P279* ?type .
      ?org wdt:P17 wd:{qid} .
      OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
      OPTIONAL {{ ?org wdt:P856 ?website }}
      OPTIONAL {{ ?org p:P625 ?coordStmt . ?coordStmt psv:P625 ?coordNode .
                  ?coordNode wikibase:geoLatitude ?lat . ?coordNode wikibase:geoLongitude ?lon . }}
      OPTIONAL {{ ?org wdt:P571 ?inception }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,es,fr,pt,de" }}
    }} LIMIT 300
    """,
]

FRAMEWORK_KEYWORDS = {
    'healthcare': ['health','clinic','hospital','medical','medicine','nurse','hiv','aids','malaria','maternal','salud'],
    'food': ['food','farm','agri','seed','nutrition','hunger','crop','agroecol','permaculture','harvest','aliment'],
    'education': ['education','school','learn','literacy','teach','library','university','college','training','escuela','universidad'],
    'ecology': ['environment','ecology','conservation','climate','biodiversity','forest','ocean','wildlife','restoration','ambiente','naturaleza'],
    'housing_land': ['housing','shelter','land trust','tenure','homeless','affordable housing','vivienda','tierra'],
    'democracy': ['democracy','civic','governance','participat','voting','election','human rights','civil liberties','derechos','democracia'],
    'cooperatives': ['cooperative','co-op','worker-owned','mutual','solidarity','credit union','cooperativa','solidaria'],
    'energy_digital': ['energy','solar','wind','renewable','digital','open source','internet','data','technology','energia'],
    'conflict': ['justice','conflict','mediation','reconciliation','peace','restorative','prison','justicia','paz'],
    'recreation_arts': ['arts','culture','recreation','sport','music','theater','museum','heritage','creative','cultura','arte'],
}


# Orgs to filter out - sports clubs, churches, political parties, etc.
FILTER_KEYWORDS = [
    'football club', 'soccer club', 'basketball club', 'rugby club', 'cricket club',
    'association football', 'f.c.', ' fc ', 'cf ', 'sport club', 'sports club',
    'club de futbol', 'club deportivo', 'racing club', 'tennis club',
    'country club', 'golf club', 'yacht club', 'polo club',
    'diocese', 'archdiocese', 'parish', 'cathedral', 'church of',
    'roman catholic', 'evangelical', 'pentecostal', 'baptist church',
    'political party', 'partido politico', 'military', 'armed forces',
    'national team', 'seleccion nacional', 'olympic committee',
    'beauty pageant', 'miss universe', 'miss world',
    'national football', 'futbol club', 'atletico',
]

def is_relevant_org(name, desc):
    """Filter out sports clubs, religious institutions, political parties."""
    combined = (name + ' ' + desc).lower()
    for kw in FILTER_KEYWORDS:
        if kw in combined:
            return False
    return True


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
    best_area = None
    best_score = 0
    for area, keywords in FRAMEWORK_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > best_score:
            best_score = score
            best_area = area
    return best_area or 'democracy'


def run_sparql(query):
    """Execute a SPARQL query against Wikidata."""
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
            print(f'  Rate limited, waiting 30s...')
            time.sleep(30)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data.get('results', {}).get('bindings', [])
        print(f'  SPARQL error: {e.code} {e.reason}')
        return []
    except Exception as e:
        print(f'  SPARQL error: {e}')
        return []


def get_val(binding, key):
    """Extract a value from a SPARQL binding."""
    if key in binding:
        return binding[key].get('value', '')
    return ''


def fetch_country(cc, country_name):
    """Fetch all org types from Wikidata for a country."""
    qid = COUNTRY_QID.get(cc)
    if not qid:
        print(f'  No Wikidata QID for {cc}, skipping')
        return []

    all_orgs = {}
    for i, query_template in enumerate(SPARQL_QUERIES):
        query = query_template.format(qid=qid)
        print(f'  Query {i+1}/{len(SPARQL_QUERIES)}...')
        results = run_sparql(query)
        print(f'    Got {len(results)} results')

        for r in results:
            name = get_val(r, 'orgLabel')
            if not name or name.startswith('Q') and name[1:].isdigit():
                continue
            wikidata_id = get_val(r, 'org').split('/')[-1]
            desc = get_val(r, 'desc')
            website = get_val(r, 'website')
            lat = get_val(r, 'lat')
            lon = get_val(r, 'lon')

            if wikidata_id not in all_orgs:
                if not is_relevant_org(name, desc):
                    continue
                all_orgs[wikidata_id] = {
                    'name': name,
                    'wikidata_id': wikidata_id,
                    'description': desc[:500] if desc else '',
                    'website': website,
                    'lat': float(lat) if lat else None,
                    'lon': float(lon) if lon else None,
                    'country_code': cc,
                    'country_name': country_name,
                    'framework_area': classify_framework(name, desc),
                }

        time.sleep(2)  # Be nice to Wikidata

    return list(all_orgs.values())


def ingest_to_db(orgs, cc, country_name):
    """Insert Wikidata orgs into the Ecolibrium DB."""
    if not orgs:
        return 0

    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    now = datetime.utcnow().isoformat()
    inserted = 0
    rejected = 0

    for org in orgs:
        try:
            # Gate: skip low-signal orgs (score >= 2 required, consistent with DB trim)
            score = _alignment_score(org['name'], org.get('description', ''))
            if score < 2:
                rejected += 1
                continue

            # Check for existing by name + country to avoid duplicates
            c.execute("SELECT id FROM organizations WHERE name=? AND country_code=?",
                      (org['name'], cc))
            if c.fetchone():
                continue

            c.execute("""INSERT INTO organizations
                (name, country_code, country_name, description, website, source, source_id,
                 date_added, status, framework_area, model_type, alignment_score,
                 lat, lon, geo_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (org['name'], cc, country_name, org['description'], org['website'],
                 'wikidata', org['wikidata_id'], now, 'active',
                 org['framework_area'], 'nonprofit', score,
                 org.get('lat'), org.get('lon'),
                 'wikidata' if org.get('lat') else None))
            inserted += c.rowcount
        except Exception as e:
            pass
    if rejected:
        print(f'  Rejected {rejected} low-signal orgs before DB insert')

    db.commit()
    c.execute("SELECT COUNT(*) FROM organizations WHERE status != 'removed'")
    total = c.fetchone()[0]
    db.close()
    print(f'  DB: +{inserted} new from Wikidata, total active={total:,}')
    return inserted


def main():
    if len(sys.argv) < 2:
        print('Usage: python wikidata_ingest.py <CC> [country_name]')
        print('  e.g. python wikidata_ingest.py CR "Costa Rica"')
        print('  or:  python wikidata_ingest.py ALL  (run all countries)')
        sys.exit(1)

    cc = sys.argv[1].upper()

    if cc == 'ALL':
        total_inserted = 0
        for country_cc in sorted(COUNTRY_QID.keys()):
            print(f'\n=== {country_cc} ===')
            orgs = fetch_country(country_cc, country_cc)
            inserted = ingest_to_db(orgs, country_cc, country_cc)
            total_inserted += inserted
            print(f'  {country_cc}: {len(orgs)} found, {inserted} new')
            time.sleep(3)
        print(f'\nTotal inserted across all countries: {total_inserted}')
        return

    country_name = sys.argv[2] if len(sys.argv) > 2 else cc
    print(f'\n=== Wikidata ingest: {country_name} ({cc}) ===')
    orgs = fetch_country(cc, country_name)
    print(f'Found {len(orgs)} unique organizations')
    inserted = ingest_to_db(orgs, cc, country_name)
    print(f'Done: {inserted} new orgs inserted')

    # Print sample
    for org in orgs[:10]:
        print(f"  - {org['name']}: {org['description'][:80]}")


if __name__ == '__main__':
    main()
