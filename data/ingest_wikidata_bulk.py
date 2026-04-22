"""
Wikidata SPARQL bulk ingest for Commonweave.

Pulls cooperative-economy org types globally or per-country. Deduplicates
by Wikidata QID stored in source_id. Respects the public endpoint's rate
limits with sleep(2) between queries.

Usage:
    python ingest_wikidata_bulk.py --country IN              # one country
    python ingest_wikidata_bulk.py --class Q4539             # one class globally
    python ingest_wikidata_bulk.py --country IN --class Q4539
    python ingest_wikidata_bulk.py --all --limit 50          # dry-run style
    python ingest_wikidata_bulk.py --all                     # full run (slow)
    python ingest_wikidata_bulk.py --dry-run --country IN
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
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from _common import DB_PATH, ensure_column, is_nonprofit_entity_type

WIKIDATA_ENDPOINT = 'https://query.wikidata.org/sparql'
BATCH_SIZE = 500
SLEEP_BETWEEN = 2  # seconds between SPARQL calls - be polite

# Wikidata QIDs for org classes we care about.
# Each entry: (qid, label, model_type)
ORG_CLASSES = [
    ('Q4539',      'cooperative',              'cooperative'),
    ('Q1365976',   'credit_union',             'cooperative'),
    ('Q23901820',  'mutual_aid_society',       'cooperative'),
    ('Q5164801',   'consumer_cooperative',     'cooperative'),
    ('Q1164282',   'worker_cooperative',       'cooperative'),
    ('Q1129318',   'housing_cooperative',      'cooperative'),
    ('Q1120762',   'agricultural_cooperative', 'cooperative'),
    ('Q849068',    'microfinance_institution', 'cooperative'),
]

# ISO 3166-1 alpha-2 -> Wikidata country QID
COUNTRY_QID = {
    'AF':'Q889','AL':'Q222','DZ':'Q262','AO':'Q916','AR':'Q414',
    'AM':'Q399','AU':'Q408','AT':'Q40','AZ':'Q227','BD':'Q902',
    'BE':'Q31','BJ':'Q962','BO':'Q750','BA':'Q225','BR':'Q155',
    'BG':'Q219','BF':'Q967','MM':'Q836','BI':'Q967','KH':'Q424',
    'CM':'Q1009','CA':'Q16','CF':'Q929','TD':'Q657','CL':'Q298',
    'CN':'Q148','CO':'Q739','CG':'Q971','CR':'Q800','CI':'Q1008',
    'HR':'Q224','CU':'Q241','CY':'Q229','CZ':'Q213','DK':'Q35',
    'DO':'Q786','EC':'Q736','EG':'Q79','SV':'Q792','ET':'Q115',
    'FI':'Q33','FR':'Q142','GA':'Q1000','GE':'Q230','DE':'Q183',
    'GH':'Q117','GR':'Q41','GT':'Q774','GN':'Q1006','GY':'Q734',
    'HT':'Q790','HN':'Q783','HU':'Q28','IN':'Q668','ID':'Q252',
    'IQ':'Q796','IE':'Q27','IL':'Q801','IT':'Q38','JM':'Q766',
    'JP':'Q17','JO':'Q810','KZ':'Q232','KE':'Q114','KR':'Q884',
    'XK':'Q1246','KW':'Q817','KG':'Q813','LA':'Q819','LB':'Q822',
    'LR':'Q1014','LY':'Q1016','LT':'Q37','MG':'Q1019','MW':'Q1020',
    'MY':'Q833','ML':'Q912','MR':'Q1025','MX':'Q96','MD':'Q217',
    'MN':'Q711','MA':'Q1028','MZ':'Q1029','NA':'Q1030','NP':'Q837',
    'NL':'Q55','NZ':'Q664','NI':'Q811','NE':'Q1032','NG':'Q1033',
    'NO':'Q20','PK':'Q843','PA':'Q804','PG':'Q691','PY':'Q733',
    'PE':'Q419','PH':'Q928','PL':'Q36','PT':'Q45','RO':'Q218',
    'RW':'Q1037','RS':'Q403','SN':'Q1041','SL':'Q1044','SO':'Q1045',
    'ZA':'Q258','ES':'Q29','LK':'Q854','SD':'Q1049','SR':'Q730',
    'SE':'Q34','CH':'Q39','SY':'Q858','TW':'Q865','TZ':'Q924',
    'TH':'Q869','TG':'Q945','TN':'Q948','TR':'Q43','TM':'Q874',
    'UG':'Q1036','UA':'Q212','GB':'Q145','US':'Q30','UY':'Q77',
    'UZ':'Q265','VE':'Q717','VN':'Q881','YE':'Q805','ZM':'Q953',
    'ZW':'Q954',
}

SPARQL_TEMPLATE = """
SELECT DISTINCT ?org ?orgLabel ?desc ?website ?countryLabel ?inceptionYear ?hqLabel WHERE {{
  ?org wdt:P31/wdt:P279* wd:{class_qid} .
  {country_filter}
  OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
  OPTIONAL {{ ?org wdt:P856 ?website }}
  OPTIONAL {{ ?org wdt:P17 ?country }}
  OPTIONAL {{ ?org wdt:P571 ?inception }}
  BIND(YEAR(?inception) AS ?inceptionYear)
  OPTIONAL {{ ?org wdt:P159 ?hq }}
  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "en,es,fr,pt,de,hi,bn,ar,zh".
    ?org rdfs:label ?orgLabel .
    ?country rdfs:label ?countryLabel .
    ?hq rdfs:label ?hqLabel .
  }}
}} LIMIT {limit}
"""

SPARQL_COUNTRY_FILTER = 'OPTIONAL {{ ?org wdt:P17 ?country }} FILTER(?country = wd:{qid}) .'
SPARQL_COUNTRY_ONLY = '?org wdt:P17 wd:{qid} .'


def sparql_query(sparql, timeout=55):
    """Run a SPARQL query and return parsed JSON bindings, or [] on error."""
    url = WIKIDATA_ENDPOINT + '?' + urllib.parse.urlencode({
        'query': sparql,
        'format': 'json',
    })
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Commonweave/1.0 (https://commonweave.org; directory@commonweave.org)',
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


def bindings_to_orgs(bindings, country_cc, class_label, model_type):
    """Convert raw SPARQL bindings to org dicts."""
    orgs = []
    for b in bindings:
        qid = b.get('org', {}).get('value', '')
        if qid:
            qid = qid.split('/')[-1]  # Q12345
        name = b.get('orgLabel', {}).get('value', '')
        if not name or name.startswith('Q'):  # no label = skip
            continue
        desc = b.get('desc', {}).get('value', '')
        website = b.get('website', {}).get('value', '')
        country_label = b.get('countryLabel', {}).get('value', '')
        inception = b.get('inceptionYear', {}).get('value', '')
        hq = b.get('hqLabel', {}).get('value', '')
        orgs.append({
            'name': name,
            'description': desc,
            'website': website,
            'country_code': country_cc,
            'country_name': country_label or country_cc,
            'source': 'wikidata_bulk',
            'source_id': qid,
            'registration_type': class_label,
            'model_type': model_type,
            'city': hq,
            'last_filing_year': inception,
        })
    return orgs


def run_migration(db):
    """Add columns that wikidata_bulk needs."""
    # evidence_url / evidence_quote may already exist from other runs
    for col, typedef in [
        ('evidence_url', 'TEXT'),
        ('evidence_quote', 'TEXT'),
        ('evidence_fetched_at', 'TEXT'),
    ]:
        ensure_column(db, 'organizations', col, typedef)


def upsert_orgs(db, orgs, dry_run=False):
    """Insert orgs; skip if source_id (QID) already exists."""
    if not orgs:
        return 0
    c = db.cursor()
    now = datetime.utcnow().isoformat()
    inserted = 0

    for batch_start in range(0, len(orgs), BATCH_SIZE):
        batch = orgs[batch_start:batch_start + BATCH_SIZE]
        for org in batch:
            name = (org.get('name') or '').strip()
            if not name:
                continue
            qid = org.get('source_id', '')
            if not qid:
                continue
            # Check alignment
            try:
                from _common import classify_org_ml
                area, score, exclude = classify_org_ml(name, org.get('description', ''))
            except Exception:
                area, score, exclude = 'cooperatives', 2, False
            if exclude:
                continue
            # Auto-pass if model_type is cooperative/credit_union/etc.
            nonprofit_pass = is_nonprofit_entity_type(name) or score >= 1
            if not nonprofit_pass:
                continue

            if dry_run:
                inserted += 1
                continue

            try:
                c.execute("""
                    INSERT OR IGNORE INTO organizations
                    (name, country_code, country_name, city, description, website,
                     source, source_id, registration_type, model_type,
                     framework_area, alignment_score, status, date_added,
                     last_filing_year, legibility)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?)
                """, (
                    name,
                    org.get('country_code', ''),
                    org.get('country_name', ''),
                    org.get('city', ''),
                    org.get('description', ''),
                    org.get('website', ''),
                    'wikidata_bulk',
                    qid,
                    org.get('registration_type', ''),
                    org.get('model_type', 'cooperative'),
                    area,
                    score,
                    now,
                    org.get('last_filing_year', ''),
                    # Wikidata is registry-notable orgs, so formal by default.
                    # Be honest in the commit: this pass biases toward
                    # already-documented, Western-notable entities.
                    'formal',
                ))
                inserted += c.rowcount
            except Exception as e:
                print(f'  Insert error ({name}): {e}')

        if not dry_run:
            db.commit()
        print(f'  Batch {batch_start + len(batch)}/{len(orgs)}: +{inserted} inserted so far')

    return inserted


def fetch_class_country(class_qid, class_label, model_type, country_cc, per_class_limit=500):
    """Pull one class for one country from Wikidata. Returns org dicts."""
    country_filter_qid = COUNTRY_QID.get(country_cc)
    if not country_filter_qid:
        print(f'  No Wikidata QID for country {country_cc}, skipping')
        return []
    sparql = SPARQL_TEMPLATE.format(
        class_qid=class_qid,
        country_filter=SPARQL_COUNTRY_ONLY.format(qid=country_filter_qid),
        limit=per_class_limit,
    )
    print(f'  SPARQL: class={class_qid}({class_label}) country={country_cc}...')
    bindings = sparql_query(sparql)
    print(f'    -> {len(bindings)} results')
    time.sleep(SLEEP_BETWEEN)
    return bindings_to_orgs(bindings, country_cc, class_label, model_type)


def fetch_class_global(class_qid, class_label, model_type, per_class_limit=500):
    """Pull one class globally (no country filter). Returns org dicts."""
    sparql = SPARQL_TEMPLATE.format(
        class_qid=class_qid,
        country_filter='',
        limit=per_class_limit,
    )
    print(f'  SPARQL: class={class_qid}({class_label}) global...')
    bindings = sparql_query(sparql)
    print(f'    -> {len(bindings)} results')
    time.sleep(SLEEP_BETWEEN)
    # Try to resolve country code from countryLabel
    orgs = []
    for b in bindings:
        # We don't have cc here; leave blank - geocode pass can fill later
        country_label = b.get('countryLabel', {}).get('value', '')
        qid = b.get('org', {}).get('value', '').split('/')[-1]
        name = b.get('orgLabel', {}).get('value', '')
        if not name or name.startswith('Q'):
            continue
        orgs.append({
            'name': name,
            'description': b.get('desc', {}).get('value', ''),
            'website': b.get('website', {}).get('value', ''),
            'country_code': '',
            'country_name': country_label,
            'source': 'wikidata_bulk',
            'source_id': qid,
            'registration_type': class_label,
            'model_type': model_type,
            'city': b.get('hqLabel', {}).get('value', ''),
            'last_filing_year': b.get('inceptionYear', {}).get('value', ''),
        })
    return orgs


def main():
    ap = argparse.ArgumentParser(description='Wikidata SPARQL bulk ingest for Commonweave')
    ap.add_argument('--country', help='ISO 3166-1 alpha-2 country code, e.g. IN')
    ap.add_argument('--class', dest='class_qid', help='Wikidata QID for org class, e.g. Q4539')
    ap.add_argument('--all', action='store_true', help='Run all classes for all countries')
    ap.add_argument('--limit', type=int, default=500, help='Max results per SPARQL query (default 500)')
    ap.add_argument('--dry-run', action='store_true', help='Count matches without writing to DB')
    args = ap.parse_args()

    if not args.country and not args.class_qid and not args.all:
        ap.print_help()
        sys.exit(1)

    db = sqlite3.connect(DB_PATH)
    run_migration(db)

    # Build list of (class_qid, label, model) to process
    if args.class_qid:
        # Look up in ORG_CLASSES or use raw QID
        match = next((x for x in ORG_CLASSES if x[0] == args.class_qid), None)
        classes = [match] if match else [(args.class_qid, args.class_qid, 'cooperative')]
    else:
        classes = ORG_CLASSES

    # Build list of countries
    if args.country:
        countries = [args.country.upper()]
    elif args.all:
        countries = list(COUNTRY_QID.keys())
    else:
        countries = None  # global query

    total_inserted = 0
    for class_qid, class_label, model_type in classes:
        if countries:
            for cc in countries:
                orgs = fetch_class_country(class_qid, class_label, model_type, cc, args.limit)
                total_inserted += upsert_orgs(db, orgs, dry_run=args.dry_run)
        else:
            orgs = fetch_class_global(class_qid, class_label, model_type, args.limit)
            total_inserted += upsert_orgs(db, orgs, dry_run=args.dry_run)

    db.close()
    mode = '[DRY RUN] Would insert' if args.dry_run else 'Inserted'
    print(f'\nDone. {mode} {total_inserted} new orgs.')


if __name__ == '__main__':
    main()
