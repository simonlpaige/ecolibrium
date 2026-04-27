"""
Foundation for Intentional Community (FIC) directory ingest.

Source: ic.org publishes its full intentional-community directory through a
custom WordPress REST endpoint at /wp-json/v1/directory/entries/. The
endpoint returns 25 entries per page (the per_page parameter is ignored
above 25), totalCount comes back in the envelope, and pagination works
with ?page=N. As of 2026-04 there are about 1,100 listed communities.

Per-row fields available from the summary endpoint:
  id, name, slug, country, city, state, communityTypes, communityStatus,
  openToVisitors, openToMembership, thumbnailUrl, createdAt, updatedAt.

A richer per-community endpoint exists at /wp-json/v1/directory/entry/?
slug=X. We make that fetch optional behind --detail because pulling 1,100
profiles at the polite 1.5s sleep takes about half an hour. The summary
fields are enough for a useful directory row.

Mapping:
  - source           = 'ic_directory'
  - source_id        = numeric id from the API.
  - country_code     = mapped from the API's full country name (which is
                       English-language and reasonably tidy).
  - legibility       = 'hybrid'. Some intentional communities are
                       registered as nonprofits, cooperatives, or LLCs;
                       many are informal. The brief explicitly tags this
                       source 'hybrid'.
  - framework_area   = 'housing_land' for everything that is a literal
                       community of place (most of the directory). When
                       the community types include education / spiritual /
                       commune the area picks the matching alternative.
  - model_type       = 'cooperative' when types mention cohousing or
                       cooperative, 'collective' when commune, otherwise
                       'community_org'.

Re-runs are idempotent on (source='ic_directory', source_id=id).

Usage:
    python ingest_ic_directory.py             # real run
    python ingest_ic_directory.py --dry-run   # parse + count, no writes
    python ingest_ic_directory.py --refresh   # ignore cache, re-fetch
    python ingest_ic_directory.py --detail    # fetch per-community profile
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
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from _common import DB_PATH, DATA_DIR, ensure_column

CACHE_DIR = os.path.join(DATA_DIR, 'sources', 'ic-cache')
LOG_PATH = os.path.join(DATA_DIR, 'ingest-ic-run.log')

USER_AGENT = (
    'Mozilla/5.0 (compatible; Commonweave/1.0 directory bot; '
    '+https://commonweave.earth; hello@simonlpaige.com)'
)
SLEEP_BETWEEN = 1.5

ENTRIES_URL = 'https://www.ic.org/wp-json/v1/directory/entries/'
ENTRY_URL = 'https://www.ic.org/wp-json/v1/directory/entry/'

COUNTRY_NAME_TO_ISO = {
    'united states': 'US', 'usa': 'US', 'us': 'US',
    'united kingdom': 'GB', 'uk': 'GB', 'great britain': 'GB',
    'canada': 'CA', 'australia': 'AU', 'new zealand': 'NZ',
    'germany': 'DE', 'france': 'FR', 'spain': 'ES', 'italy': 'IT',
    'portugal': 'PT', 'netherlands': 'NL', 'belgium': 'BE',
    'denmark': 'DK', 'sweden': 'SE', 'norway': 'NO', 'finland': 'FI',
    'iceland': 'IS', 'austria': 'AT', 'switzerland': 'CH',
    'ireland': 'IE', 'poland': 'PL', 'czech republic': 'CZ',
    'czechia': 'CZ', 'hungary': 'HU', 'romania': 'RO', 'bulgaria': 'BG',
    'greece': 'GR', 'cyprus': 'CY', 'malta': 'MT',
    'slovakia': 'SK', 'slovenia': 'SI', 'croatia': 'HR',
    'serbia': 'RS', 'lithuania': 'LT', 'latvia': 'LV', 'estonia': 'EE',
    'mexico': 'MX', 'brazil': 'BR', 'argentina': 'AR', 'chile': 'CL',
    'peru': 'PE', 'colombia': 'CO', 'ecuador': 'EC', 'uruguay': 'UY',
    'paraguay': 'PY', 'bolivia': 'BO', 'venezuela': 'VE',
    'costa rica': 'CR', 'guatemala': 'GT', 'panama': 'PA',
    'nicaragua': 'NI', 'honduras': 'HN', 'el salvador': 'SV',
    'cuba': 'CU', 'jamaica': 'JM', 'haiti': 'HT',
    'india': 'IN', 'china': 'CN', 'japan': 'JP', 'south korea': 'KR',
    'korea': 'KR', 'thailand': 'TH', 'vietnam': 'VN', 'philippines': 'PH',
    'indonesia': 'ID', 'malaysia': 'MY', 'singapore': 'SG',
    'taiwan': 'TW', 'sri lanka': 'LK', 'bangladesh': 'BD',
    'nepal': 'NP', 'pakistan': 'PK',
    'south africa': 'ZA', 'kenya': 'KE', 'nigeria': 'NG',
    'tanzania': 'TZ', 'uganda': 'UG', 'ghana': 'GH', 'morocco': 'MA',
    'egypt': 'EG', 'tunisia': 'TN', 'algeria': 'DZ', 'ethiopia': 'ET',
    'rwanda': 'RW', 'senegal': 'SN', 'cameroon': 'CM',
    'turkey': 'TR', 'israel': 'IL', 'lebanon': 'LB',
    'russia': 'RU', 'ukraine': 'UA', 'belarus': 'BY',
    'georgia': 'GE', 'armenia': 'AM', 'kazakhstan': 'KZ',
}

COMMUNITY_TYPE_TO_FRAMEWORK = [
    (re.compile(r'school|education|learning|university', re.I), 'education'),
    (re.compile(r'farm|agricultur|food', re.I), 'food'),
    (re.compile(r'spiritual|monaster|ashram|sangha|religious', re.I), 'recreation_arts'),
    (re.compile(r'arts|cultural|performance', re.I), 'recreation_arts'),
    (re.compile(r'cohous|coopera|land trust|housing|condo', re.I), 'housing_land'),
    (re.compile(r'ecovillage|eco-village|ecology', re.I), 'ecology'),
]


def cache_path(key):
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = hashlib.sha1(key.encode('utf-8')).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f'{safe}.json')


def http_get(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def fetch_json(url, refresh=False):
    p = cache_path(url)
    if not refresh and os.path.exists(p) and os.path.getsize(p) > 32:
        with open(p, 'rb') as f:
            return json.loads(f.read().decode('utf-8'))
    body = http_get(url)
    with open(p, 'wb') as f:
        f.write(body)
    time.sleep(SLEEP_BETWEEN)
    return json.loads(body.decode('utf-8'))


def fetch_entries(refresh=False):
    """Walk the entries endpoint until we have totalCount rows."""
    page = 1
    items = []
    total = None
    while True:
        url = f'{ENTRIES_URL}?per_page=25&page={page}'
        try:
            data = fetch_json(url, refresh=refresh)
        except urllib.error.HTTPError as e:
            if e.code == 400 or e.code == 404:
                break
            raise
        listings = data.get('listings') or []
        if not listings:
            break
        items.extend(listings)
        if total is None:
            total = data.get('totalCount') or 0
        if page == 1 or page % 10 == 0:
            print(f'  page {page}: {len(items)}/{total}')
        page += 1
        if total and len(items) >= total:
            break
        if page > 200:
            print('  safety break at page 200')
            break
    return items, total


HTML_TAG_RE = re.compile(r'<[^>]+>')
WHITESPACE_RE = re.compile(r'\s+')


def strip_html(s):
    if not s:
        return ''
    s = HTML_TAG_RE.sub(' ', s)
    s = (s.replace('&nbsp;', ' ').replace('&amp;', '&')
           .replace('&#8217;', "'").replace('&#8211;', '-')
           .replace('&#8220;', '"').replace('&#8221;', '"')
           .replace('&rsquo;', "'").replace('&lsquo;', "'"))
    return WHITESPACE_RE.sub(' ', s).strip()


def normalize_country(raw):
    if not raw:
        return ('', '')
    s = raw.strip()
    iso = COUNTRY_NAME_TO_ISO.get(s.lower())
    return (iso or '', s)


def derive_framework(types):
    blob = ' '.join(types) if isinstance(types, list) else (types or '')
    for pat, area in COMMUNITY_TYPE_TO_FRAMEWORK:
        if pat.search(blob):
            return area
    return 'housing_land'


def derive_model_type(types):
    blob = ' '.join(types) if isinstance(types, list) else (types or '')
    low = blob.lower()
    if 'cohous' in low or 'cooperative' in low or 'co-op' in low:
        return 'cooperative'
    if 'commune' in low:
        return 'collective'
    if 'cohouseholding' in low or 'shared housing' in low:
        return 'cooperative'
    return 'community_org'


def parse_summary(item, refresh=False, fetch_detail=False):
    name = (item.get('name') or '').strip()
    if not name:
        return None
    iso, cname = normalize_country(item.get('country') or '')
    types = item.get('communityTypes') or []
    framework = derive_framework(types)
    model = derive_model_type(types)
    description_bits = []
    if item.get('communityStatus'):
        description_bits.append(f'status: {item["communityStatus"]}')
    if types:
        description_bits.append('type: ' + ', '.join(types))
    if item.get('openToMembership'):
        description_bits.append(f'open to membership: {item["openToMembership"]}')
    description = '. '.join(description_bits)

    website = ''
    if fetch_detail:
        slug = item.get('slug') or ''
        if slug:
            try:
                detail = fetch_json(f'{ENTRY_URL}?slug={urllib.parse.quote(slug)}',
                                    refresh=refresh)
                if isinstance(detail, dict):
                    website = (detail.get('websiteUrl') or '').strip()
                    mission = strip_html(detail.get('missionStatement') or '')
                    desc = strip_html(detail.get('description') or '')
                    if mission or desc:
                        description = (mission + ' ' + desc).strip()[:1500]
            except Exception as e:
                print(f'  detail fetch failed for {slug}: {e}')

    profile_url = f'https://www.ic.org/directory/{item.get("slug") or ""}/'
    return {
        'name': name,
        'country_code': iso,
        'country_name': cname,
        'state_province': (item.get('state') or '').strip(),
        'city': (item.get('city') or '').strip(),
        'description': description[:1500],
        'framework_area': framework,
        'model_type': model,
        'website': website or profile_url,
        'tags': ', '.join(types) if types else 'intentional_community',
        'source_id': str(item.get('id')),
        'evidence_url': profile_url,
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
            ('ic_directory', r['source_id']),
        )
        existing = c.fetchone()
        if existing:
            c.execute(
                """UPDATE organizations
                   SET name=?,
                       country_code=COALESCE(NULLIF(country_code,''), ?),
                       country_name=COALESCE(NULLIF(country_name,''), ?),
                       state_province=COALESCE(NULLIF(state_province,''), ?),
                       city=COALESCE(NULLIF(city,''), ?),
                       description=COALESCE(NULLIF(description,''), ?),
                       framework_area=COALESCE(NULLIF(framework_area,''), ?),
                       model_type=?,
                       website=COALESCE(NULLIF(website,''), ?),
                       tags=COALESCE(NULLIF(tags,''), ?),
                       alignment_score=MAX(COALESCE(alignment_score,0), ?),
                       evidence_url=COALESCE(NULLIF(evidence_url,''), ?),
                       evidence_fetched_at=?,
                       legibility='hybrid'
                   WHERE id=?""",
                (
                    r['name'], r['country_code'], r['country_name'],
                    r['state_province'], r['city'], r['description'],
                    r['framework_area'], r['model_type'],
                    r['website'], r['tags'],
                    2, r['evidence_url'], now, existing[0],
                ),
            )
            updated += 1
        else:
            c.execute(
                """INSERT OR IGNORE INTO organizations
                   (name, country_code, country_name, state_province, city,
                    description, framework_area, model_type, website, tags,
                    source, source_id, alignment_score,
                    status, date_added,
                    legibility, evidence_url, evidence_fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?)""",
                (
                    r['name'], r['country_code'], r['country_name'],
                    r['state_province'], r['city'],
                    r['description'], r['framework_area'],
                    r['model_type'], r['website'], r['tags'],
                    'ic_directory', r['source_id'], 2,
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
        f.write(f'\n# ingest_ic_directory run - {today}\n\n')
        for line in lines:
            f.write(line + '\n')


def main():
    ap = argparse.ArgumentParser(description='Foundation for Intentional Community directory ingest')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--refresh', action='store_true')
    ap.add_argument('--detail', action='store_true', help='Fetch each community profile (slow)')
    args = ap.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Ingesting IC.org directory")
    print('  Walking entries pages...')
    entries, total = fetch_entries(refresh=args.refresh)
    print(f'  Got {len(entries)} entries (totalCount reported: {total})')

    rows = [parse_summary(e, refresh=args.refresh, fetch_detail=args.detail) for e in entries]
    rows = [r for r in rows if r]
    print(f'  Parsed {len(rows)} usable rows')

    db = sqlite3.connect(DB_PATH)
    run_migration(db)
    inserted, updated = upsert(db, rows, dry_run=args.dry_run)
    db.close()

    mode = '[DRY RUN] Would insert' if args.dry_run else 'Inserted'
    summary = [
        f"Mode: {'dry-run' if args.dry_run else 'real'}",
        f"Source: {ENTRIES_URL}",
        f"Total reported by API: {total}",
        f"Entries parsed: {len(entries)}",
        f"Detail per-community: {args.detail}",
        f"{mode}: {inserted}",
        f"Updated: {updated}",
    ]
    print('\n' + '\n'.join(summary))
    write_log(summary)
    print(f'\nLog appended: {LOG_PATH}')


if __name__ == '__main__':
    main()
