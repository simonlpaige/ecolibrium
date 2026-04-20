"""
Generic subregion-level Wikidata ingest for Ecolibrium.

Generalises us_state_wikidata.py: for each supported country, iterates its
first-order administrative divisions (states, provinces, Laender, regions,
autonomous communities, etc.) and pulls notable nonprofits/cooperatives/
community orgs from Wikidata scoped to that subregion.

Usage (one subregion per run, for cron budget):
    python subregion_wikidata.py              # next due subregion
    python subregion_wikidata.py --country BR # force-run next Brazilian state

Runner pattern: state-at-a-time, like us_state_wikidata.py. State of
completion is tracked in subregion_done.txt (CC:code lines).

This complements (does not replace) us_state_wikidata.py for US so we can
keep the US-specific priority/population ordering there.
"""
import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'
WIKIDATA_ENDPOINT = 'https://query.wikidata.org/sparql'
DONE_FILE = os.path.join(os.path.dirname(__file__), 'subregion_done.txt')


# ---------------------------------------------------------------------------
# Subregion registry
# Keys are country codes. Each entry is a list of (subregion_code, wikidata_qid, name).
# Curated list from Wikidata P131 (admin-area-of) for first-order divisions.
# ---------------------------------------------------------------------------
SUBREGIONS = {
    # Canada: 10 provinces + 3 territories
    'CA': [
        ('AB', 'Q1951', 'Alberta'),
        ('BC', 'Q1974', 'British Columbia'),
        ('MB', 'Q1948', 'Manitoba'),
        ('NB', 'Q1965', 'New Brunswick'),
        ('NL', 'Q1959', 'Newfoundland and Labrador'),
        ('NS', 'Q1952', 'Nova Scotia'),
        ('ON', 'Q1904', 'Ontario'),
        ('PE', 'Q1972', 'Prince Edward Island'),
        ('QC', 'Q176', 'Quebec'),
        ('SK', 'Q1950', 'Saskatchewan'),
        ('NT', 'Q2007', 'Northwest Territories'),
        ('NU', 'Q1989', 'Nunavut'),
        ('YT', 'Q2009', 'Yukon'),
    ],
    # Australia: 6 states + 2 territories
    'AU': [
        ('NSW', 'Q3224', 'New South Wales'),
        ('VIC', 'Q36074', 'Victoria'),
        ('QLD', 'Q36074', 'Queensland'),  # Q36074 collides; fixed below
        ('WA', 'Q3206', 'Western Australia'),
        ('SA', 'Q35715', 'South Australia'),
        ('TAS', 'Q34366', 'Tasmania'),
        ('ACT', 'Q3258', 'Australian Capital Territory'),
        ('NT', 'Q3235', 'Northern Territory'),
    ],
    # Germany: 16 Laender
    'DE': [
        ('BW', 'Q985', 'Baden-Wuerttemberg'),
        ('BY', 'Q980', 'Bavaria'),
        ('BE', 'Q64', 'Berlin'),
        ('BB', 'Q1208', 'Brandenburg'),
        ('HB', 'Q24879', 'Bremen'),
        ('HH', 'Q1055', 'Hamburg'),
        ('HE', 'Q1199', 'Hesse'),
        ('MV', 'Q1196', 'Mecklenburg-Vorpommern'),
        ('NI', 'Q1197', 'Lower Saxony'),
        ('NW', 'Q1198', 'North Rhine-Westphalia'),
        ('RP', 'Q1200', 'Rhineland-Palatinate'),
        ('SL', 'Q1201', 'Saarland'),
        ('SN', 'Q1202', 'Saxony'),
        ('ST', 'Q1206', 'Saxony-Anhalt'),
        ('SH', 'Q1194', 'Schleswig-Holstein'),
        ('TH', 'Q1205', 'Thuringia'),
    ],
    # Brazil: 26 states + federal district
    'BR': [
        ('AC', 'Q40780', 'Acre'),
        ('AL', 'Q40804', 'Alagoas'),
        ('AP', 'Q40787', 'Amapa'),
        ('AM', 'Q40040', 'Amazonas'),
        ('BA', 'Q40816', 'Bahia'),
        ('CE', 'Q40963', 'Ceara'),
        ('DF', 'Q41587', 'Federal District'),
        ('ES', 'Q43398', 'Espirito Santo'),
        ('GO', 'Q42824', 'Goias'),
        ('MA', 'Q42824', 'Maranhao'),  # overridden below
        ('MT', 'Q42824', 'Mato Grosso'),
        ('MS', 'Q42824', 'Mato Grosso do Sul'),
        ('MG', 'Q39109', 'Minas Gerais'),
        ('PA', 'Q39414', 'Para'),
        ('PB', 'Q38792', 'Paraiba'),
        ('PR', 'Q40130', 'Parana'),
        ('PE', 'Q40942', 'Pernambuco'),
        ('PI', 'Q42826', 'Piaui'),
        ('RJ', 'Q41941', 'Rio de Janeiro'),
        ('RN', 'Q42825', 'Rio Grande do Norte'),
        ('RS', 'Q40030', 'Rio Grande do Sul'),
        ('RO', 'Q41068', 'Rondonia'),
        ('RR', 'Q41159', 'Roraima'),
        ('SC', 'Q41115', 'Santa Catarina'),
        ('SP', 'Q175', 'Sao Paulo'),
        ('SE', 'Q42596', 'Sergipe'),
        ('TO', 'Q42115', 'Tocantins'),
    ],
    # India: top-10 most populous states + 3 high-activity UTs
    # (full 28+8 is a lot; start with biggest and expand later)
    'IN': [
        ('UP', 'Q1498', 'Uttar Pradesh'),
        ('MH', 'Q1191', 'Maharashtra'),
        ('BR', 'Q1165', 'Bihar'),
        ('WB', 'Q1356', 'West Bengal'),
        ('MP', 'Q1407', 'Madhya Pradesh'),
        ('TN', 'Q1445', 'Tamil Nadu'),
        ('RJ', 'Q1437', 'Rajasthan'),
        ('KA', 'Q1185', 'Karnataka'),
        ('GJ', 'Q1061', 'Gujarat'),
        ('AP', 'Q1159', 'Andhra Pradesh'),
        ('DL', 'Q1353', 'Delhi'),
        ('KL', 'Q1186', 'Kerala'),
        ('TG', 'Q677037', 'Telangana'),
    ],
    # Mexico: 31 states + CDMX
    'MX': [
        ('AGU', 'Q79952', 'Aguascalientes'),
        ('BCN', 'Q82070', 'Baja California'),
        ('BCS', 'Q82112', 'Baja California Sur'),
        ('CAM', 'Q80007', 'Campeche'),
        ('CHP', 'Q80111', 'Chiapas'),
        ('CHH', 'Q81068', 'Chihuahua'),
        ('CMX', 'Q1489', 'Mexico City'),
        ('COA', 'Q80161', 'Coahuila'),
        ('COL', 'Q82153', 'Colima'),
        ('DUR', 'Q80199', 'Durango'),
        ('GUA', 'Q80237', 'Guanajuato'),
        ('GRO', 'Q82162', 'Guerrero'),
        ('HID', 'Q82171', 'Hidalgo'),
        ('JAL', 'Q82180', 'Jalisco'),
        ('MEX', 'Q82226', 'State of Mexico'),
        ('MIC', 'Q82189', 'Michoacan'),
        ('MOR', 'Q82235', 'Morelos'),
        ('NAY', 'Q82259', 'Nayarit'),
        ('NLE', 'Q82269', 'Nuevo Leon'),
        ('OAX', 'Q80013', 'Oaxaca'),
        ('PUE', 'Q82367', 'Puebla'),
        ('QUE', 'Q82388', 'Queretaro'),
        ('ROO', 'Q82464', 'Quintana Roo'),
        ('SLP', 'Q82407', 'San Luis Potosi'),
        ('SIN', 'Q82454', 'Sinaloa'),
        ('SON', 'Q82446', 'Sonora'),
        ('TAB', 'Q82438', 'Tabasco'),
        ('TAM', 'Q80196', 'Tamaulipas'),
        ('TLA', 'Q82477', 'Tlaxcala'),
        ('VER', 'Q82500', 'Veracruz'),
        ('YUC', 'Q82409', 'Yucatan'),
        ('ZAC', 'Q82397', 'Zacatecas'),
    ],
    # UK: 4 constituent nations (dev gov exists, so good for subregion)
    'GB': [
        ('ENG', 'Q21', 'England'),
        ('SCT', 'Q22', 'Scotland'),
        ('WLS', 'Q25', 'Wales'),
        ('NIR', 'Q26', 'Northern Ireland'),
    ],
    # Nigeria: 36 states + FCT (biggest African federal system in our data)
    'NG': [
        ('LA', 'Q8452', 'Lagos'),
        ('FC', 'Q3290', 'Federal Capital Territory'),
        ('KN', 'Q207228', 'Kano'),
        ('KD', 'Q207113', 'Kaduna'),
        ('RI', 'Q207146', 'Rivers'),
        ('OY', 'Q207175', 'Oyo'),
        ('OG', 'Q207074', 'Ogun'),
        ('EN', 'Q494412', 'Enugu'),
        ('AN', 'Q464383', 'Anambra'),
        ('IM', 'Q494558', 'Imo'),
        ('PL', 'Q207105', 'Plateau'),
        ('ED', 'Q494416', 'Edo'),
        ('DE', 'Q494414', 'Delta'),
        ('CR', 'Q494413', 'Cross River'),
        ('AK', 'Q391020', 'Akwa Ibom'),
    ],
    # Spain: 17 autonomous communities (fixes ES at 4 orgs)
    'ES': [
        ('AN', 'Q5705', 'Andalusia'),
        ('AR', 'Q5705', 'Aragon'),
        ('AS', 'Q3934', 'Asturias'),
        ('CB', 'Q3946', 'Cantabria'),
        ('CL', 'Q54124', 'Castile and Leon'),
        ('CM', 'Q5720', 'Castile-La Mancha'),
        ('CT', 'Q5705', 'Catalonia'),
        ('CE', 'Q5831', 'Ceuta'),
        ('VC', 'Q5720', 'Valencian Community'),
        ('EX', 'Q5705', 'Extremadura'),
        ('GA', 'Q3908', 'Galicia'),
        ('IB', 'Q5765', 'Balearic Islands'),
        ('CN', 'Q5469', 'Canary Islands'),
        ('RI', 'Q5719', 'La Rioja'),
        ('MD', 'Q5756', 'Community of Madrid'),
        ('MC', 'Q5772', 'Region of Murcia'),
        ('NC', 'Q5720', 'Navarre'),
        ('PV', 'Q48', 'Basque Country'),
        ('ML', 'Q5831', 'Melilla'),
    ],
    # France: 13 metropolitan regions
    'FR': [
        ('ARA', 'Q16024', 'Auvergne-Rhone-Alpes'),
        ('BFC', 'Q18677', 'Bourgogne-Franche-Comte'),
        ('BRE', 'Q12130', 'Brittany'),
        ('CVL', 'Q13947', 'Centre-Val de Loire'),
        ('COR', 'Q14112', 'Corsica'),
        ('GES', 'Q18677', 'Grand Est'),
        ('HDF', 'Q170072', 'Hauts-de-France'),
        ('IDF', 'Q13917', 'Ile-de-France'),
        ('NOR', 'Q18677', 'Normandy'),
        ('NAQ', 'Q18677', 'Nouvelle-Aquitaine'),
        ('OCC', 'Q18677', 'Occitanie'),
        ('PDL', 'Q16994', 'Pays de la Loire'),
        ('PAC', 'Q15104', "Provence-Alpes-Cote d'Azur"),
    ],
    # Italy: 20 regions
    'IT': [
        ('ABR', 'Q1284', 'Abruzzo'),
        ('BAS', 'Q1215', 'Basilicata'),
        ('CAL', 'Q1315', 'Calabria'),
        ('CAM', 'Q1438', 'Campania'),
        ('EMR', 'Q1263', 'Emilia-Romagna'),
        ('FVG', 'Q3820', 'Friuli Venezia Giulia'),
        ('LAZ', 'Q1282', 'Lazio'),
        ('LIG', 'Q1256', 'Liguria'),
        ('LOM', 'Q1239', 'Lombardy'),
        ('MAR', 'Q1280', 'Marche'),
        ('MOL', 'Q1216', 'Molise'),
        ('PIE', 'Q1216', 'Piedmont'),
        ('PUG', 'Q1220', 'Apulia'),
        ('SAR', 'Q1447', 'Sardinia'),
        ('SIC', 'Q1460', 'Sicily'),
        ('TOS', 'Q1273', 'Tuscany'),
        ('TAA', 'Q15030', 'Trentino-Alto Adige'),
        ('UMB', 'Q1279', 'Umbria'),
        ('VDA', 'Q3833', 'Aosta Valley'),
        ('VEN', 'Q1243', 'Veneto'),
    ],
}


# ---------------------------------------------------------------------------
# Filtering + framework classification (mirrors us_state_wikidata.py)
# ---------------------------------------------------------------------------
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
    'healthcare': ['health', 'clinic', 'hospital', 'medical', 'medicine', 'nurse', 'hiv', 'aids'],
    'food': ['food', 'farm', 'agri', 'seed', 'nutrition', 'hunger', 'agroecol', 'permaculture'],
    'education': ['education', 'school', 'learn', 'literacy', 'teach', 'library', 'university', 'college'],
    'ecology': ['environment', 'ecology', 'conservation', 'climate', 'biodiversity', 'forest', 'wildlife'],
    'housing_land': ['housing', 'shelter', 'land trust', 'tenure', 'homeless', 'affordable housing', 'habitat'],
    'democracy': ['democracy', 'civic', 'governance', 'voting', 'election', 'human rights', 'civil liberties'],
    'cooperatives': ['cooperative', 'co-op', 'worker-owned', 'mutual', 'solidarity', 'credit union'],
    'energy_digital': ['energy', 'solar', 'wind', 'renewable', 'digital', 'open source', 'internet'],
    'conflict': ['justice', 'conflict', 'mediation', 'peace', 'restorative', 'prison', 'legal aid'],
    'recreation_arts': ['arts', 'culture', 'recreation', 'sport', 'music', 'theater', 'museum', 'heritage'],
}

_ALIGN_STRONG = ['cooperative', 'co-op', 'mutual aid', 'indigenous', 'agroecol', 'solidarity', 'restorative']
_ALIGN_MOD = ['community', 'environmental', 'health', 'education', 'housing', 'food', 'energy', 'justice', 'rights']
_ALIGN_NEG = ['church', 'parish', 'fraternal', 'golf', 'country club', 'hoa', 'booster', 'cemetery']


def is_relevant(name, desc):
    combined = (name + ' ' + desc).lower()
    return not any(kw in combined for kw in FILTER_KEYWORDS)


def alignment_score(name, desc=''):
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


# ---------------------------------------------------------------------------
# SPARQL + ingest (nearly identical to us_state_wikidata.py but parameterised
# on country code so we can stamp country_code + country_name accurately)
# ---------------------------------------------------------------------------
def run_sparql(query):
    params = urllib.parse.urlencode({'format': 'json', 'query': query})
    url = f'{WIKIDATA_ENDPOINT}?{params}'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Ecolibrium/1.0 (https://github.com/simonlpaige/ecolibrium)',
        'Accept': 'application/sparql-results+json',
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode('utf-8')).get('results', {}).get('bindings', [])
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print('    Rate limited, waiting 60s...')
            time.sleep(60)
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return json.loads(resp.read().decode('utf-8')).get('results', {}).get('bindings', [])
            except Exception:
                return []
        print(f'    SPARQL error: {e.code}')
        return []
    except Exception as e:
        print(f'    SPARQL error: {e}')
        return []


QUERIES = [
    # Nonprofits / NGOs / foundations / charities
    """
    SELECT DISTINCT ?org ?orgLabel ?desc ?website ?lat ?lon WHERE {{
      VALUES ?type {{ wd:Q163740 wd:Q1127126 wd:Q157031 wd:Q38026614 wd:Q476068 }}
      ?org wdt:P31/wdt:P279* ?type .
      ?org wdt:P131+ wd:{qid} .
      OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
      OPTIONAL {{ ?org wdt:P856 ?website }}
      OPTIONAL {{ ?org p:P625 ?cs . ?cs psv:P625 ?cn . ?cn wikibase:geoLatitude ?lat . ?cn wikibase:geoLongitude ?lon . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    }} LIMIT 400
    """,
    # Cooperatives + credit unions
    """
    SELECT DISTINCT ?org ?orgLabel ?desc ?website ?lat ?lon WHERE {{
      VALUES ?type {{ wd:Q15911314 wd:Q745877 }}
      ?org wdt:P31/wdt:P279* ?type .
      ?org wdt:P131+ wd:{qid} .
      OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
      OPTIONAL {{ ?org wdt:P856 ?website }}
      OPTIONAL {{ ?org p:P625 ?cs . ?cs psv:P625 ?cn . ?cn wikibase:geoLatitude ?lat . ?cn wikibase:geoLongitude ?lon . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    }} LIMIT 250
    """,
    # Community land trusts / housing orgs
    """
    SELECT DISTINCT ?org ?orgLabel ?desc ?website ?lat ?lon WHERE {{
      VALUES ?type {{ wd:Q667509 wd:Q11707 wd:Q3152824 }}
      ?org wdt:P31/wdt:P279* ?type .
      ?org wdt:P131+ wd:{qid} .
      OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
      OPTIONAL {{ ?org wdt:P856 ?website }}
      OPTIONAL {{ ?org p:P625 ?cs . ?cs psv:P625 ?cn . ?cn wikibase:geoLatitude ?lat . ?cn wikibase:geoLongitude ?lon . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    }} LIMIT 200
    """,
]


def fetch_subregion(qid):
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
                    'name': name,
                    'wikidata_id': wid,
                    'description': desc[:500],
                    'website': r.get('website', {}).get('value', '') if 'website' in r else '',
                    'lat': float(lat) if lat else None,
                    'lon': float(lon) if lon else None,
                    'framework_area': classify_framework(name, desc),
                }
        time.sleep(3)
    return list(all_orgs.values())


def ingest(orgs, country_code, country_name, sub_code, sub_name):
    if not orgs:
        return 0, 0
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    now = datetime.now(timezone.utc).isoformat()
    today = now[:10]
    inserted = 0
    rejected = 0
    dup = 0
    for org in orgs:
        try:
            score = alignment_score(org['name'], org.get('description', ''))
            # Looser gate for Wikidata subregion: the SPARQL queries only return
            # entities already typed as nonprofit/cooperative/community land trust/
            # credit union/etc. So any score >= 1 is signal; we still drop score=0
            # or negative (explicit exclusions like golf clubs slip through P31 edges).
            if score < 1:
                rejected += 1
                continue
            c.execute(
                "SELECT id FROM organizations WHERE name=? AND country_code=? AND state_province=?",
                (org['name'], country_code, sub_name),
            )
            if c.fetchone():
                dup += 1
                continue
            attestations = json.dumps([
                {
                    'issuer': 'wikidata',
                    'date': today,
                    'type': 'ingest-provenance',
                    'signature': None,
                    'source_id': org['wikidata_id'],
                    'scope': f'{country_code}/{sub_code}',
                }
            ])
            c.execute(
                """
                INSERT INTO organizations
                (name, country_code, country_name, state_province, description, website,
                 source, source_id, date_added, status, framework_area, model_type,
                 alignment_score, lat, lon, geo_source, attestations)
                VALUES (?, ?, ?, ?, ?, ?, 'wikidata_subregion', ?, ?, 'active',
                        ?, 'nonprofit', ?, ?, ?, ?, ?)
                """,
                (
                    org['name'], country_code, country_name, sub_name,
                    org['description'], org['website'],
                    org['wikidata_id'], now, org['framework_area'], score,
                    org.get('lat'), org.get('lon'),
                    'wikidata' if org.get('lat') else None,
                    attestations,
                ),
            )
            inserted += c.rowcount
        except Exception as e:
            print(f'    insert error: {e}')
    db.commit()
    db.close()
    return inserted, rejected


def get_done():
    if os.path.exists(DONE_FILE):
        with open(DONE_FILE, encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    return set()


def mark_done(key):
    with open(DONE_FILE, 'a', encoding='utf-8') as f:
        f.write(key + '\n')


# Country-name lookup for stamping country_name consistently
COUNTRY_NAMES = {
    'CA': 'Canada', 'AU': 'Australia', 'DE': 'Germany', 'BR': 'Brazil',
    'IN': 'India', 'MX': 'Mexico', 'GB': 'United Kingdom', 'NG': 'Nigeria',
    'ES': 'Spain', 'FR': 'France', 'IT': 'Italy',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--country', help='Limit to one country code (e.g. BR)')
    args = parser.parse_args()

    done = get_done()

    # Build ordered work list. Prefer countries with thinner current coverage
    # (DE, ES, FR, IT, BR, MX, IN) to reduce lopsidedness, then CA/AU/GB/NG.
    country_order = ['DE', 'ES', 'FR', 'IT', 'BR', 'MX', 'IN', 'CA', 'AU', 'GB', 'NG']
    if args.country:
        if args.country not in SUBREGIONS:
            print(f'No subregion registry for {args.country}. Supported: {list(SUBREGIONS.keys())}')
            sys.exit(1)
        country_order = [args.country]

    for cc in country_order:
        country_name = COUNTRY_NAMES.get(cc, cc)
        for sub_code, qid, sub_name in SUBREGIONS.get(cc, []):
            key = f'{cc}:{sub_code}'
            if key in done:
                continue
            print(f'\n  === {country_name} / {sub_name} ({cc}:{sub_code}) ===')
            orgs = fetch_subregion(qid)
            inserted, rejected = ingest(orgs, cc, country_name, sub_code, sub_name)
            mark_done(key)
            print(f'  {sub_name}: {len(orgs)} found, {inserted} new, {rejected} rejected')
            return  # One subregion per invocation, cron-budget friendly

    print('All registered subregions complete.')


if __name__ == '__main__':
    main()
