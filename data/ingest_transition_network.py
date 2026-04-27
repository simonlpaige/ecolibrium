"""
Transition Network groups ingest.

Source: https://maps.transitionnetwork.org/wp-json/cds/v1/groups/. Documented
public API at https://maps.transitionnetwork.org/api/. The data is licensed
under the Open Data Commons Open Database License (ODbL); we credit
Transition Network and its contributors at the source level and in DATA.md.

About 1,000 local Transition initiatives globally, each with a geocoded
location, hub assignment, country, free-text description, and a tag set
that maps cleanly onto the framework areas Commonweave already uses.
We ingest two endpoints:

  1. /wp-json/cds/v1/groups/  - the local groups (~1,000 entries).
  2. /wp-json/cds/v1/hubs/    - the regional and national hubs (a few dozen).
                                Hubs are the regional federations of groups.

Both are paginated, per_page=100, sleep one second between calls.

Mapping:
  - source            = 'transition_network'
  - source_id         = numeric id from the API for groups, or 'hub:'+slug
                        for hubs.
  - country_code      = derived from the 'countries' field (free-text country
                        name) via a name -> ISO mapping. The API also accepts
                        ISO alpha-2 as a query param but the response is in
                        full country names.
  - legibility        = 'hybrid'. Some Transition initiatives are registered
                        charities or community-interest companies; many are
                        informal local meet-ups. The brief explicitly tags
                        Transition Network as hybrid.
  - framework_area    = derived from the tag list. A Transition group with
                        food-tagged work goes to 'food', a renewable energy
                        group goes to 'energy_digital', a community building
                        group goes to 'democracy', and so on.
  - model_type        = 'collective' for groups (no fixed legal form to
                        assume), 'nonprofit' for hubs.

Re-runs are idempotent on (source='transition_network', source_id=id).

Usage:
    python ingest_transition_network.py             # real run
    python ingest_transition_network.py --dry-run   # parse + count, no writes
    python ingest_transition_network.py --refresh   # ignore cache, re-fetch
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from _common import DB_PATH, DATA_DIR, ensure_column

CACHE_DIR = os.path.join(DATA_DIR, 'sources', 'transition-cache')
LOG_PATH = os.path.join(DATA_DIR, 'ingest-transition-run.log')

USER_AGENT = (
    'Mozilla/5.0 (compatible; Commonweave/1.0 directory bot; '
    '+https://commonweave.earth; hello@simonlpaige.com)'
)
SLEEP_BETWEEN = 1.5

GROUPS_API = 'https://maps.transitionnetwork.org/wp-json/cds/v1/groups/'
HUBS_API = 'https://maps.transitionnetwork.org/wp-json/cds/v1/hubs/'

# Country full-name -> ISO alpha-2. Generously covers everywhere Transition
# groups are actually known to exist; any country we don't recognise falls
# through to '' and the row still saves with country_name set.
COUNTRY_NAME_TO_ISO = {
    'australia': 'AU', 'austria': 'AT', 'belgium': 'BE', 'brazil': 'BR',
    'canada': 'CA', 'chile': 'CL', 'china': 'CN', 'colombia': 'CO',
    'croatia': 'HR', 'czech republic': 'CZ', 'czechia': 'CZ', 'denmark': 'DK',
    'estonia': 'EE', 'finland': 'FI', 'france': 'FR', 'germany': 'DE',
    'greece': 'GR', 'hungary': 'HU', 'iceland': 'IS', 'india': 'IN',
    'indonesia': 'ID', 'ireland': 'IE', 'israel': 'IL', 'italy': 'IT',
    'japan': 'JP', 'lebanon': 'LB', 'luxembourg': 'LU', 'malaysia': 'MY',
    'mexico': 'MX', 'netherlands': 'NL', 'new zealand': 'NZ', 'norway': 'NO',
    'poland': 'PL', 'portugal': 'PT', 'romania': 'RO', 'slovakia': 'SK',
    'slovenia': 'SI', 'south africa': 'ZA', 'south korea': 'KR',
    'spain': 'ES', 'sweden': 'SE', 'switzerland': 'CH', 'thailand': 'TH',
    'turkey': 'TR', 'ukraine': 'UA', 'united kingdom': 'GB',
    'united states': 'US', 'usa': 'US', 'us': 'US', 'argentina': 'AR',
    'peru': 'PE', 'ecuador': 'EC', 'venezuela': 'VE', 'guatemala': 'GT',
    'costa rica': 'CR', 'panama': 'PA', 'taiwan': 'TW', 'philippines': 'PH',
    'singapore': 'SG', 'vietnam': 'VN', 'kenya': 'KE', 'nigeria': 'NG',
    'morocco': 'MA', 'egypt': 'EG', 'tunisia': 'TN', 'algeria': 'DZ',
    'ghana': 'GH', 'uganda': 'UG', 'tanzania': 'TZ',
    'bosnia and herzegovina': 'BA', 'serbia': 'RS', 'montenegro': 'ME',
    'north macedonia': 'MK', 'macedonia': 'MK', 'bulgaria': 'BG',
    'lithuania': 'LT', 'latvia': 'LV', 'malta': 'MT', 'cyprus': 'CY',
    'jersey': 'JE', 'guernsey': 'GG', 'isle of man': 'IM',
}

# Transition Network's tag vocabulary -> Commonweave framework areas. The
# tag list per group can be long; first match in priority order wins.
TAG_TO_FRAMEWORK = [
    # food-and-land tags are by far the most common
    (re.compile(r'food|grow|farm|garden|csa|orchard|allotment', re.I), 'food'),
    # housing / land
    (re.compile(r'housing|land trust|community land|cohousing', re.I), 'housing_land'),
    # energy & digital commons
    (re.compile(r'energy|solar|wind|renewables?|low carbon|digital|hacker|maker|fablab', re.I), 'energy_digital'),
    # ecology
    (re.compile(r'nature|biodiversity|wildlife|forest|river|conservation|climate|ecology', re.I), 'ecology'),
    # democracy / community
    (re.compile(r'community visioning|building local networks|just transition|social justice|equity|democracy|political|advocacy', re.I), 'democracy'),
    # education
    (re.compile(r'youth|education|school|learning|training|workshop', re.I), 'education'),
    # arts / culture
    (re.compile(r'festivals|fairs|arts|culture|theatre|cinema|music', re.I), 'recreation_arts'),
    # cooperatives / solidarity finance
    (re.compile(r'cooperative|coop|credit union|currency|reinventing money', re.I), 'cooperatives'),
    # share, repair, reuse maps to ecology (circular economy)
    (re.compile(r'repair|reuse|share|circular|waste', re.I), 'ecology'),
    # wellbeing / inner transition -> healthcare
    (re.compile(r'wellbeing|inner transition|health|wellness', re.I), 'healthcare'),
    # transport
    (re.compile(r'transport|cycling|mobility', re.I), 'ecology'),
]


def cache_path(name):
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = hashlib.sha1(name.encode('utf-8')).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f'{safe}-{name.replace("/", "_")[:60]}.json')


def http_get_json(url, refresh=False):
    p = cache_path(url)
    if not refresh and os.path.exists(p) and os.path.getsize(p) > 32:
        with open(p, 'rb') as f:
            return json.loads(f.read().decode('utf-8'))
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
    with open(p, 'wb') as f:
        f.write(body)
    time.sleep(SLEEP_BETWEEN)
    return json.loads(body.decode('utf-8'))


def fetch_pages(base, refresh=False):
    """Walk every page of a Transition Network endpoint. Stops when
    page_number >= total_pages."""
    all_items = []
    page = 1
    while True:
        url = f'{base}?per_page=100&page={page}'
        try:
            data = http_get_json(url, refresh=refresh)
        except Exception as e:
            print(f'  page {page} failed: {e}')
            break
        items = data.get('body') or []
        all_items.extend(items)
        total_pages = int(data.get('total_pages') or 1)
        print(f'  page {page}/{total_pages}: {len(items)} items')
        if page >= total_pages:
            break
        page += 1
    return all_items


HTML_TAG_RE = re.compile(r'<[^>]+>')
WHITESPACE_RE = re.compile(r'\s+')


def strip_html(s):
    if not s:
        return ''
    s = HTML_TAG_RE.sub(' ', s)
    s = (s.replace('&nbsp;', ' ').replace('&amp;', '&')
           .replace('&#8217;', "'").replace('&#8211;', '-')
           .replace('&#8220;', '"').replace('&#8221;', '"'))
    return WHITESPACE_RE.sub(' ', s).strip()


def normalize_country(raw):
    if not raw:
        return ('', '')
    s = raw.strip()
    if len(s) == 2 and s.isalpha():
        return (s.upper(), s.upper())
    iso = COUNTRY_NAME_TO_ISO.get(s.lower())
    return (iso or '', s)


def derive_framework(tags):
    if not tags:
        return ''
    blob = ' | '.join(tags)
    for pat, area in TAG_TO_FRAMEWORK:
        if pat.search(blob):
            return area
    return ''


def parse_group(item):
    title = (item.get('title') or '').strip()
    if not title:
        return None
    loc = item.get('location') or {}
    contact = item.get('contact') or {}
    iso, cname = normalize_country(item.get('countries') or '')
    desc = strip_html(item.get('description') or '')
    if len(desc) > 1500:
        desc = desc[:1497] + '...'
    return {
        'name': title,
        'country_code': iso,
        'country_name': cname,
        'state_province': (loc.get('province') or '').strip(),
        'city': (loc.get('city') or '').strip(),
        'lat': loc.get('lat'),
        'lon': loc.get('lng'),
        'website': (contact.get('website') or '').strip() or item.get('url', ''),
        'description': desc,
        'framework_area': derive_framework(item.get('tags') or []),
        'model_type': 'collective',
        'tags': ', '.join(item.get('tags') or []),
        'source_id': str(item.get('id')),
        'evidence_url': item.get('url') or GROUPS_API,
    }


def parse_hub(item):
    title = (item.get('title') or '').strip()
    if not title:
        return None
    loc = item.get('location') or {}
    iso, cname = normalize_country(item.get('countries') or '')
    desc = strip_html(item.get('description') or '')
    if len(desc) > 1500:
        desc = desc[:1497] + '...'
    # Hubs do not always carry a numeric id in the response, so derive a
    # stable id from the URL slug.
    url = item.get('url', '') or ''
    slug = url.rstrip('/').rsplit('/', 1)[-1] or hashlib.sha1(title.encode('utf-8')).hexdigest()[:12]
    return {
        'name': f'{title} (Transition Hub)',
        'country_code': iso,
        'country_name': cname,
        'state_province': (loc.get('province') or '').strip(),
        'city': (loc.get('city') or '').strip(),
        'lat': loc.get('lat'),
        'lon': loc.get('lng'),
        'website': url,
        'description': desc,
        'framework_area': 'democracy',
        'model_type': 'nonprofit',
        'tags': item.get('status') or 'Hub',
        'source_id': 'hub:' + slug,
        'evidence_url': url or HUBS_API,
        'email': (item.get('email') or '').strip(),
    }


def run_migration(db):
    for col, typedef in [
        ('evidence_url', 'TEXT'),
        ('evidence_quote', 'TEXT'),
        ('evidence_fetched_at', 'TEXT'),
        ('legibility', "TEXT DEFAULT 'unknown'"),
    ]:
        ensure_column(db, 'organizations', col, typedef)


def upsert(db, rows, dry_run=False):
    c = db.cursor()
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    updated = 0
    for r in rows:
        if not r:
            continue
        if dry_run:
            inserted += 1
            continue
        c.execute(
            "SELECT id FROM organizations WHERE source=? AND source_id=?",
            ('transition_network', r['source_id']),
        )
        existing = c.fetchone()
        lat = r.get('lat')
        lon = r.get('lon')
        if existing:
            c.execute(
                """UPDATE organizations
                   SET name=?,
                       country_code=COALESCE(NULLIF(country_code,''), ?),
                       country_name=COALESCE(NULLIF(country_name,''), ?),
                       state_province=COALESCE(NULLIF(state_province,''), ?),
                       city=COALESCE(NULLIF(city,''), ?),
                       lat=COALESCE(lat, ?),
                       lon=COALESCE(lon, ?),
                       geo_source=COALESCE(NULLIF(geo_source,''), 'transition_network'),
                       website=COALESCE(NULLIF(website,''), ?),
                       email=COALESCE(NULLIF(email,''), ?),
                       description=COALESCE(NULLIF(description,''), ?),
                       framework_area=COALESCE(NULLIF(framework_area,''), ?),
                       model_type=?,
                       tags=COALESCE(NULLIF(tags,''), ?),
                       alignment_score=MAX(COALESCE(alignment_score,0), ?),
                       evidence_url=COALESCE(NULLIF(evidence_url,''), ?),
                       evidence_fetched_at=?,
                       legibility='hybrid'
                   WHERE id=?""",
                (
                    r['name'], r['country_code'], r['country_name'],
                    r['state_province'], r['city'], lat, lon,
                    r['website'], r.get('email', ''),
                    r['description'], r['framework_area'],
                    r['model_type'], r['tags'],
                    2, r['evidence_url'], now, existing[0],
                ),
            )
            updated += 1
        else:
            c.execute(
                """INSERT OR IGNORE INTO organizations
                   (name, country_code, country_name, state_province, city,
                    lat, lon, geo_source,
                    website, email,
                    description, framework_area, model_type, tags,
                    source, source_id, alignment_score,
                    status, date_added,
                    legibility, evidence_url, evidence_fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?)""",
                (
                    r['name'], r['country_code'], r['country_name'],
                    r['state_province'], r['city'],
                    lat, lon, 'transition_network',
                    r['website'], r.get('email', ''),
                    r['description'], r['framework_area'],
                    r['model_type'], r['tags'],
                    'transition_network', r['source_id'], 2,
                    now,
                    'hybrid', r['evidence_url'], now,
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
        f.write(f'\n# ingest_transition_network run - {today}\n\n')
        for line in lines:
            f.write(line + '\n')


def main():
    ap = argparse.ArgumentParser(description='Transition Network groups + hubs ingest')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--refresh', action='store_true')
    args = ap.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Ingesting Transition Network")

    print('  Fetching groups...')
    groups = fetch_pages(GROUPS_API, refresh=args.refresh)
    print(f'  Total group items: {len(groups)}')
    print('  Fetching hubs...')
    hubs = fetch_pages(HUBS_API, refresh=args.refresh)
    print(f'  Total hub items: {len(hubs)}')

    rows = [parse_group(g) for g in groups] + [parse_hub(h) for h in hubs]
    rows = [r for r in rows if r]
    print(f'  Parsed {len(rows)} usable rows')

    db = sqlite3.connect(DB_PATH)
    run_migration(db)
    inserted, updated = upsert(db, rows, dry_run=args.dry_run)
    db.close()

    mode = '[DRY RUN] Would insert' if args.dry_run else 'Inserted'
    summary = [
        f"Mode: {'dry-run' if args.dry_run else 'real'}",
        f"Groups endpoint: {GROUPS_API}",
        f"Hubs endpoint: {HUBS_API}",
        f"Groups parsed: {len(groups)}",
        f"Hubs parsed: {len(hubs)}",
        f"Rows total: {len(rows)}",
        f"{mode}: {inserted}",
        f"Updated: {updated}",
        "License: ODbL (https://maps.transitionnetwork.org/licence/)",
    ]
    print('\n' + '\n'.join(summary))
    write_log(summary)
    print(f'\nLog appended: {LOG_PATH}')


if __name__ == '__main__':
    main()
