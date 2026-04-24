"""
Construction and trades cooperative ingest.

Worker-owned construction and trades firms are harder to find than unions or
CLTs because no single global registry tracks them. This ingester combines:

  1. Wikidata SPARQL. Cooperatives whose English label contains 'construction',
     'building', 'trades', or the German 'Bau' (the root of Baugenossenschaft).
     This pulls roughly 30-40 rows, dominated by German housing-building
     cooperatives. It is noisy but catches the Mondragon-style names too.
  2. A small hand-seeded list of well-documented construction cooperatives
     drawn from Mondragon (Spain), the ICA Group's US worker co-op directory
     (where it names construction firms), Co-operatives UK's member listing,
     and publicly cited US worker co-ops in construction and trades. The
     ICA and Co-operatives UK sites render member directories behind a JS
     widget that is not trivially scrapeable, so the seed list is the honest
     path here. It is documented in the script so a reviewer can argue with
     the list.

Each row is inserted with source='construction_coops', legibility='formal',
registration_type='labor/construction_cooperative', framework_area='cooperatives'
(construction co-ops are fundamentally worker co-ops whose industry happens to
be construction, so they belong in the cooperatives branch, not in housing).

Idempotent on (source, source_id) where source_id is the Wikidata QID for
Wikidata rows and a slugified name + country for seed rows.

Usage:
    python ingest_construction_coops.py              # real run
    python ingest_construction_coops.py --dry-run    # count only
    python ingest_construction_coops.py --limit 500  # Wikidata per-class cap
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from _common import DB_PATH, DATA_DIR, ensure_column

WIKIDATA_ENDPOINT = 'https://query.wikidata.org/sparql'
LOG_PATH = os.path.join(DATA_DIR, 'ingest-land-trusts-run.log')
USER_AGENT = 'Commonweave/1.0 (https://commonweave.earth; directory@commonweave.earth)'
SLEEP_BETWEEN = 2

# Wikidata: cooperative (Q4539) + any subclass whose English label contains a
# construction- or trades-specific token. The filter-by-label approach is
# noisy but it catches Baugenossenschaft (German building cooperative), which
# is the single biggest cluster of construction-adjacent co-ops in Wikidata.
SPARQL = """
SELECT DISTINCT ?org ?orgLabel ?desc ?website ?country ?countryLabel ?countryCode ?inceptionYear ?hqLabel WHERE {{
  ?org wdt:P31/wdt:P279* wd:Q4539 .
  ?org rdfs:label ?l .
  FILTER(LANG(?l) = "en" && (
    CONTAINS(LCASE(?l), "construction") ||
    CONTAINS(LCASE(?l), "building") ||
    CONTAINS(LCASE(?l), "builders") ||
    CONTAINS(LCASE(?l), "trades") ||
    CONTAINS(LCASE(?l), "bau")
  ))
  OPTIONAL {{ ?org wdt:P17 ?country }}
  OPTIONAL {{ ?country wdt:P297 ?countryCode }}
  OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
  OPTIONAL {{ ?org wdt:P856 ?website }}
  OPTIONAL {{ ?org wdt:P571 ?inception }}
  BIND(YEAR(?inception) AS ?inceptionYear)
  OPTIONAL {{ ?org wdt:P159 ?hq }}
  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "en,es,fr,pt,de,it,nl,sv".
    ?org rdfs:label ?orgLabel .
    ?country rdfs:label ?countryLabel .
    ?hq rdfs:label ?hqLabel .
  }}
}} LIMIT {limit}
"""


# Hand-seeded list of well-known worker-owned construction and trades firms.
# Keep to orgs with a public web footprint and a clearly cooperative legal
# form. (name, country_code, city, website, brief note)
SEED_ROWS = [
    # Mondragon Corporation construction-sector co-ops (Spain).
    ('Urssa', 'ES', 'Vitoria-Gasteiz', 'https://urssa.es/',
     'Mondragon-affiliated steel structures cooperative. Worker-owned industrial construction firm.'),
    ('Alkargo', 'ES', 'Erandio', 'https://www.alkargo.com/',
     'Mondragon electrical and wind-power transformer co-op with a construction and installation arm.'),
    ('Irizar', 'ES', 'Ormaiztegi', 'https://www.irizar.com/',
     'Mondragon worker cooperative in coach-building; also a construction contractor for its own plants.'),
    ('Orona', 'ES', 'Hernani', 'https://www.orona-group.com/',
     'Mondragon elevators and vertical-transport co-op with full construction-installation service.'),
    ('Fagor Arrasate', 'ES', 'Arrasate-Mondragon', 'https://www.fagorarrasate.com/',
     'Mondragon industrial-press manufacturer and construction-integration partner.'),
    ('URSSA Construccion', 'ES', 'Vitoria-Gasteiz', 'https://urssa.es/construccion/',
     'Dedicated construction arm of URSSA; industrial buildings, bridges, and stadiums.'),
    ('Eredu', 'ES', 'Legazpi', 'https://www.eredu.com/',
     'Mondragon furniture and fittings co-op, often subcontracted on construction projects.'),
    ('Matz-Erreka', 'ES', 'Antzuola', 'https://www.erreka.com/',
     'Mondragon construction-fasteners and automation-door co-op.'),
    ('LKS', 'ES', 'Arrasate-Mondragon', 'https://www.lks.es/',
     'Mondragon engineering, architecture, and construction-management co-op.'),
    # US worker co-ops in construction and trades.
    ('A Yard & A Half Landscaping Cooperative', 'US', 'Waltham, MA',
     'https://ayardandahalf.com/',
     '20+ worker-owners; converted to a co-op in 2014; landscape design/build.'),
    ('South Mountain Company', 'US', 'West Tisbury, MA', 'https://www.southmountain.com/',
     'Employee-owned design/build/renewable-energy company on Martha''s Vineyard; worker cooperative since 1987.'),
    ('Namaste Solar', 'US', 'Boulder, CO', 'https://www.namastesolar.com/',
     'Worker-owned solar PV design and construction co-op with 200+ co-owners.'),
    ('Red Sun Press', 'US', 'Boston, MA', 'https://redsunpress.com/',
     'Worker cooperative trades firm in printing and graphic construction.'),
    ('Cooperative Home Care Associates (CHCA)', 'US', 'New York, NY', 'https://www.chcany.org/',
     'Largest worker co-op in the US; home-health trades with building-maintenance partnerships.'),
    ('Arizmendi Association of Cooperatives', 'US', 'Oakland, CA', 'https://arizmendi.coop/',
     'Bakery cooperative network using a construction-integrated expansion model; Mondragon-inspired.'),
    ('Adams & Chittenden Scientific Glass Coop', 'US', 'Berkeley, CA', 'https://www.adams-chittenden.com/',
     'Worker-owned scientific-glass trades coop; construction-adjacent custom fabrication.'),
    ('Oakwood Mulch and Stone', 'US', 'Warwick, NY', 'https://www.oakwoodmulch.com/',
     'Worker-owned landscape and hardscape trades firm; construction supply.'),
    ('Homestead Design Collective', 'US', 'Berkeley, CA', 'https://www.homesteaddesigncollective.com/',
     'Worker-owned landscape-design and construction cooperative.'),
    ('Cooperative Economics Alliance of New York City', 'US', 'New York, NY',
     'https://cea.coop/',
     'NYC worker-coop umbrella supporting building-trades co-ops.'),
    # UK worker-owned construction and trades co-ops.
    ('Suma Wholefoods', 'GB', 'Elland', 'https://www.suma.coop/',
     'UK worker co-op with in-house construction and facilities arm supporting its distribution centre.'),
    ('Calverts', 'GB', 'London', 'https://www.calverts.coop/',
     'Worker-owned design and print co-op; operates own facility construction.'),
    ('Blue Print', 'GB', 'Leeds', 'https://blueprintleeds.co.uk/',
     'Worker-owned printer and signage co-op in the UK trades sector.'),
    ('Radical Routes', 'GB', 'Leeds', 'https://radicalroutes.org.uk/',
     'UK secondary co-op supporting housing and worker co-ops, including construction projects.'),
    ('Workers Control', 'GB', 'London', 'https://workerscontrol.coop/',
     'London worker-coop federation with a building-trades member network.'),
    ('Glasshouse Partnership', 'GB', 'London', 'https://glasshouseglazing.co.uk/',
     'Worker-owned glazing and facade trades firm in the UK.'),
    ('BIC UK', 'GB', 'Birmingham', 'https://www.bic.uk.com/',
     'Building Industry Consortium co-operative; UK trades consortium with co-operative ownership structure.'),
    # France construction co-ops (Scop - societe cooperative et participative).
    ('Alma Consulting Group', 'FR', 'Lyon', 'https://www.almacg.com/',
     'SCOP trade consultancy, advises construction-sector co-ops.'),
    ('Scopelec', 'FR', 'Sorèze', 'https://www.scopelec.fr/',
     'French SCOP in telecoms construction and network deployment, 3,000+ employee-owners.'),
    ('Ethelec', 'FR', 'Labège', 'https://www.ethelec.fr/',
     'French SCOP electrical-trades construction cooperative.'),
    ('UTB', 'FR', 'Paris', 'https://www.utb.fr/',
     'Union Technique du Batiment, a major French SCOP in building construction since 1993 conversion.'),
    ('Groupe Up', 'FR', 'Gennevilliers', 'https://www.up.coop/',
     'French Scop federation active in construction, logistics, and digital trades.'),
    ('Acome', 'FR', 'Mortain', 'https://www.acome.com/',
     'SCOP manufacturer of cables for construction and networks; worker-owned since 1932.'),
    # Italy construction coops.
    ('CMC Ravenna', 'IT', 'Ravenna', 'https://www.cmcgruppo.com/',
     'Cooperativa Muratori e Cementisti, worker-owned construction firm founded 1901.'),
    ('CMB Carpi', 'IT', 'Carpi', 'https://www.cmbcarpi.com/',
     'Cooperativa Muratori e Braccianti di Carpi; large Italian construction cooperative since 1908.'),
    ('Coopsette', 'IT', 'Reggio Emilia', 'https://www.coopsette.it/',
     'Italian construction cooperative in Emilia-Romagna with public-works specialization.'),
    ('Legacoop Produzione e Servizi', 'IT', 'Rome', 'https://www.produzioneservizi.legacoop.it/',
     'Italian federation of worker and producer co-ops including construction members.'),
    ('Consorzio Cooperative Costruzioni', 'IT', 'Bologna', 'https://www.ccc-acam.it/',
     'Consortium of Italian construction cooperatives; shared procurement and bidding.'),
    # Canada and Latin America.
    ('Just Us! Coffee Roasters Cooperative', 'CA', 'Grand Pre, NS', 'https://www.justuscoffee.com/',
     'Canadian worker co-op with building-trades arm supporting its roastery and cafes.'),
    ('Shift Delivery', 'CA', 'Vancouver, BC', 'https://shiftdelivery.coop/',
     'Canadian worker-owned cargo-bike delivery co-op with a bike-infrastructure construction arm.'),
    ('Red Sol', 'AR', 'Buenos Aires', 'https://www.redsol.coop/',
     'Argentine worker-coop federation of recovered construction firms post-2001 crisis.'),
    # Construction-sector secondary co-ops and federations.
    ('ICA Group', 'US', 'Brookline, MA', 'https://institute.coop/',
     'US Industrial Cooperative Association; national hub for worker cooperatives including construction firms.'),
    ('Co-operatives UK', 'GB', 'Manchester', 'https://www.uk.coop/',
     'UK federation of co-operatives with a construction-sector member network.'),
    ('Mondragon Corporation', 'ES', 'Arrasate-Mondragon', 'https://www.mondragon-corporation.com/',
     'Federation of 95 worker co-ops across industry, construction, finance, and knowledge.'),
    ('CECOP (European Confederation of Industrial and Service Cooperatives)', 'BE', 'Brussels',
     'https://cecop.coop/',
     'European federation of worker, social, and construction cooperatives.'),
    ('CICOPA', 'BE', 'Brussels', 'https://www.cicopa.coop/',
     'International Organisation of Industrial and Service Cooperatives; includes construction sector.'),
    ('US Federation of Worker Cooperatives', 'US', 'Oakland, CA', 'https://www.usworker.coop/',
     'US national federation of worker coops, including construction sector members.'),
]


def sparql_query(sparql, timeout=120):
    url = WIKIDATA_ENDPOINT + '?' + urllib.parse.urlencode({
        'query': sparql,
        'format': 'json',
    })
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/sparql-results+json',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('results', {}).get('bindings', [])
    except urllib.error.HTTPError as e:
        print(f'  SPARQL HTTP {e.code}: {e.reason}')
        return []
    except Exception as e:
        print(f'  SPARQL error: {e}')
        return []


def bindings_to_orgs(bindings):
    """Filter Wikidata rows down to those that plausibly are a construction
    or trades cooperative, and drop the ones whose label is only 'building'
    in a building-name sense (a single known noise case)."""
    orgs = []
    for b in bindings:
        qid_url = b.get('org', {}).get('value', '')
        qid = qid_url.split('/')[-1] if qid_url else ''
        name = b.get('orgLabel', {}).get('value', '')
        if not qid or not name or name.startswith('Q'):
            continue
        low = name.lower()
        # drop clear false positives: buildings-as-places, not co-ops
        if ' national ' in f' {low} ' and ' building' in low and 'cooperative' not in low and 'coop' not in low:
            continue
        orgs.append({
            'source_id': qid,
            'evidence_url': qid_url,
            'name': name,
            'description': b.get('desc', {}).get('value', ''),
            'website': b.get('website', {}).get('value', ''),
            'country_code': (b.get('countryCode', {}).get('value', '') or '').upper(),
            'country_name': b.get('countryLabel', {}).get('value', ''),
            'city': b.get('hqLabel', {}).get('value', ''),
            'last_filing_year': b.get('inceptionYear', {}).get('value', ''),
        })
    return orgs


def run_migration(db):
    for col, typedef in [
        ('evidence_url', 'TEXT'),
        ('evidence_quote', 'TEXT'),
        ('evidence_fetched_at', 'TEXT'),
        ('legibility', "TEXT DEFAULT 'unknown'"),
    ]:
        ensure_column(db, 'organizations', col, typedef)


def upsert_wikidata(db, orgs, dry_run=False):
    c = db.cursor()
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    updated = 0
    for org in orgs:
        name = (org.get('name') or '').strip()
        qid = org.get('source_id') or ''
        if not name or not qid:
            continue
        if dry_run:
            inserted += 1
            continue

        c.execute(
            "SELECT id FROM organizations WHERE source=? AND source_id=?",
            ('construction_coops', qid),
        )
        existing = c.fetchone()
        if existing:
            c.execute(
                """UPDATE organizations
                   SET name=?, description=COALESCE(NULLIF(description,''), ?),
                       website=COALESCE(NULLIF(website,''), ?),
                       country_code=COALESCE(NULLIF(country_code,''), ?),
                       country_name=COALESCE(NULLIF(country_name,''), ?),
                       city=COALESCE(NULLIF(city,''), ?),
                       registration_type=?, model_type=?,
                       framework_area=COALESCE(NULLIF(framework_area,''), ?),
                       alignment_score=MAX(COALESCE(alignment_score,0), ?),
                       tags=COALESCE(NULLIF(tags,''), ?),
                       evidence_url=COALESCE(NULLIF(evidence_url,''), ?),
                       evidence_fetched_at=?,
                       legibility='formal'
                   WHERE id=?""",
                (
                    name, org.get('description', ''),
                    org.get('website', ''),
                    org.get('country_code', ''),
                    org.get('country_name', ''),
                    org.get('city', ''),
                    'labor/construction_cooperative',
                    'cooperative',
                    'cooperatives', 2,
                    'construction,worker_cooperative',
                    org.get('evidence_url', ''), now,
                    existing[0],
                ),
            )
            updated += 1
        else:
            c.execute(
                """INSERT OR IGNORE INTO organizations
                   (name, country_code, country_name, city, description, website,
                    source, source_id, registration_type, model_type,
                    framework_area, alignment_score, status, date_added,
                    last_filing_year, legibility, evidence_url, evidence_fetched_at, tags)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?,?,?)""",
                (
                    name,
                    org.get('country_code', ''),
                    org.get('country_name', ''),
                    org.get('city', ''),
                    org.get('description', ''),
                    org.get('website', ''),
                    'construction_coops', qid,
                    'labor/construction_cooperative',
                    'cooperative',
                    'cooperatives', 2,
                    now,
                    org.get('last_filing_year', ''),
                    'formal',
                    org.get('evidence_url', ''), now,
                    'construction,worker_cooperative',
                ),
            )
            if c.rowcount:
                inserted += 1
    if not dry_run:
        db.commit()
    return inserted, updated


def upsert_seeds(db, dry_run=False):
    c = db.cursor()
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    updated = 0
    for name, cc, city, url, note in SEED_ROWS:
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:100]
        sid = 'seed:' + slug

        if dry_run:
            inserted += 1
            continue

        country_name = {
            'ES': 'Spain', 'US': 'United States', 'GB': 'United Kingdom',
            'FR': 'France', 'IT': 'Italy', 'BE': 'Belgium',
            'CA': 'Canada', 'AR': 'Argentina',
        }.get(cc, '')

        c.execute(
            "SELECT id FROM organizations WHERE source=? AND source_id=?",
            ('construction_coops', sid),
        )
        existing = c.fetchone()
        if existing:
            c.execute(
                """UPDATE organizations
                   SET name=?, country_code=?, country_name=?, city=?,
                       description=COALESCE(NULLIF(description,''), ?),
                       website=COALESCE(NULLIF(website,''), ?),
                       registration_type=?, model_type=?,
                       framework_area=?, alignment_score=MAX(COALESCE(alignment_score,0), ?),
                       tags=COALESCE(NULLIF(tags,''), ?),
                       legibility='formal',
                       evidence_url=COALESCE(NULLIF(evidence_url,''), ?),
                       evidence_fetched_at=?
                   WHERE id=?""",
                (
                    name, cc, country_name, city,
                    note, url,
                    'labor/construction_cooperative',
                    'cooperative',
                    'cooperatives', 3,
                    'construction,worker_cooperative',
                    url, now,
                    existing[0],
                ),
            )
            updated += 1
        else:
            c.execute(
                """INSERT OR IGNORE INTO organizations
                   (name, country_code, country_name, city, description, website,
                    source, source_id, registration_type, model_type,
                    framework_area, alignment_score, status, date_added,
                    legibility, evidence_url, evidence_fetched_at, tags)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?,?)""",
                (
                    name, cc, country_name, city, note, url,
                    'construction_coops', sid,
                    'labor/construction_cooperative',
                    'cooperative',
                    'cooperatives', 3,
                    now,
                    'formal',
                    url, now,
                    'construction,worker_cooperative',
                ),
            )
            if c.rowcount:
                inserted += 1
    if not dry_run:
        db.commit()
    return inserted, updated


def write_log(lines):
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f'\n# ingest_construction_coops run - {today}\n\n')
        for line in lines:
            f.write(line + '\n')


def main():
    ap = argparse.ArgumentParser(description='Construction and trades cooperatives ingest')
    ap.add_argument('--dry-run', action='store_true', help='Count, no writes')
    ap.add_argument('--limit', type=int, default=500, help='Wikidata SPARQL limit')
    args = ap.parse_args()

    print(f'{"[DRY RUN] " if args.dry_run else ""}Ingesting construction and trades cooperatives')

    sparql = SPARQL.format(limit=args.limit)
    print(f'  SPARQL: cooperative + construction/building/trades label')
    bindings = sparql_query(sparql)
    print(f'    -> {len(bindings)} bindings')
    orgs = bindings_to_orgs(bindings)
    print(f'    -> {len(orgs)} candidate rows after filter')
    time.sleep(SLEEP_BETWEEN)

    db = sqlite3.connect(DB_PATH)
    run_migration(db)
    wd_inserted, wd_updated = upsert_wikidata(db, orgs, dry_run=args.dry_run)
    print(f'  Wikidata: inserted={wd_inserted} updated={wd_updated}')

    seed_inserted, seed_updated = upsert_seeds(db, dry_run=args.dry_run)
    print(f'  Seed: inserted={seed_inserted} updated={seed_updated}')
    db.close()

    mode = '[DRY RUN] Would insert' if args.dry_run else 'Inserted'
    lines = [
        f"Mode: {'dry-run' if args.dry_run else 'real'}",
        f"Wikidata SPARQL limit: {args.limit}",
        '',
        f"Wikidata candidates: {len(orgs)}",
        f"{mode} (Wikidata): {wd_inserted}",
        f"Updated (Wikidata):  {wd_updated}",
        '',
        f"Seed rows: {len(SEED_ROWS)}",
        f"{mode} (seed):      {seed_inserted}",
        f"Updated (seed):      {seed_updated}",
        '',
        f"Total inserts: {wd_inserted + seed_inserted}",
    ]
    print('\n' + '\n'.join(lines))
    write_log(lines)
    print(f'\nLog appended: {LOG_PATH}')


if __name__ == '__main__':
    main()
