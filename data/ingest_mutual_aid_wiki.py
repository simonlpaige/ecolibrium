"""
Mutual Aid Wiki + Mutual Aid Hub ingest. Two community-maintained datasets
of mutual aid groups, used in tandem because between them they cover the
UK and the US fairly well, and the rest of the world thinly.

Source 1: Mutual Aid Wiki (mutualaid.wiki).
  The live API endpoint at mutualaid.wiki/api/* is currently returning 502.
  But the canonical groups list is checked into the project's GitHub repo
  at github.com/Covid-Mutual-Aid/mutual-aid-wiki/blob/master/groups.json.
  The file is shaped like an AWS Lambda response: {statusCode, headers,
  body=<json string>} where body parses to a list of group dicts. About
  4,253 groups, mostly UK, COVID-era. Licence: CC BY-NC-SA 4.0.

Source 2: Mutual Aid Hub (mutualaidhub.org).
  US-focused dataset hosted on a Firebase / Firestore document collection
  at firestore.googleapis.com/v1/projects/townhallproject-86312/databases/
  (default)/documents/mutual_aid_networks. Public read is enabled, no API
  key needed. The footer of the page declares the data PDDL-1.0 (Open
  Data Commons Public Domain Dedication and Licence).

Both are tagged legibility='informal'. Most of these groups were never
incorporated. They are neighborhood support networks, mailing lists, and
WhatsApp circles. Every row gets framework_area='democracy' (mutual aid
is a community-organising practice) unless a category hint pulls it
elsewhere. Every row also lists model_type='mutual_aid'.

Idempotency: source_id is the dataset's own primary key. MAW uses UUIDs;
MAH uses Firestore document ids. Re-running adds zero rows.

Usage:
    python ingest_mutual_aid_wiki.py             # real run
    python ingest_mutual_aid_wiki.py --dry-run   # parse + count only
    python ingest_mutual_aid_wiki.py --refresh   # ignore cache, re-fetch
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

CACHE_DIR = os.path.join(DATA_DIR, 'sources', 'mutualaid-cache')
LOG_PATH = os.path.join(DATA_DIR, 'ingest-mutualaid-run.log')

USER_AGENT = (
    'Mozilla/5.0 (compatible; Commonweave/1.0 directory bot; '
    '+https://commonweave.earth; hello@simonlpaige.com)'
)
SLEEP_BETWEEN = 1.5

MAW_GROUPS_URL = (
    'https://raw.githubusercontent.com/Covid-Mutual-Aid/mutual-aid-wiki/'
    'master/groups.json'
)
MAH_FIRESTORE_URL = (
    'https://firestore.googleapis.com/v1/projects/townhallproject-86312/'
    'databases/(default)/documents/mutual_aid_networks'
)

COUNTRY_NAME_TO_ISO = {
    'usa': 'US', 'united states': 'US', 'united states of america': 'US',
    'uk': 'GB', 'united kingdom': 'GB', 'great britain': 'GB',
    'ireland': 'IE', 'canada': 'CA', 'australia': 'AU',
    'new zealand': 'NZ', 'south africa': 'ZA', 'india': 'IN',
    'germany': 'DE', 'france': 'FR', 'spain': 'ES', 'italy': 'IT',
    'netherlands': 'NL', 'belgium': 'BE', 'sweden': 'SE',
    'norway': 'NO', 'denmark': 'DK', 'finland': 'FI', 'iceland': 'IS',
    'mexico': 'MX', 'brazil': 'BR', 'argentina': 'AR',
    'portugal': 'PT', 'austria': 'AT', 'switzerland': 'CH',
    'poland': 'PL', 'czech republic': 'CZ', 'czechia': 'CZ',
    'hungary': 'HU', 'romania': 'RO', 'greece': 'GR',
    'japan': 'JP', 'south korea': 'KR', 'china': 'CN',
}

# UK county names that show up as the last comma part in MAW location_name
# strings. When we see one of these we know the row is GB even though the
# explicit country marker fell off the end of the address. Keeping this
# list explicit and finite is better than guessing from coordinates.
UK_REGIONS = {
    'london', 'somerset', 'surrey', 'devon', 'hampshire', 'oxfordshire',
    'scotland', 'norfolk', 'derbyshire', 'manchester', 'shropshire',
    'north yorkshire', 'birmingham', 'cambridgeshire', 'essex', 'kent',
    'sheffield', 'bedfordshire', 'suffolk', 'chester', 'maidstone',
    'east sussex', 'west sussex', 'gloucestershire', 'wales', 'wiltshire',
    'leicestershire', 'staffordshire', 'lancashire', 'merseyside',
    'cumbria', 'cornwall', 'durham', 'tyne and wear', 'yorkshire',
    'south yorkshire', 'west yorkshire', 'northumberland', 'cheshire',
    'dorset', 'warwickshire', 'worcestershire', 'herefordshire',
    'nottinghamshire', 'lincolnshire', 'rutland', 'isle of wight',
    'northamptonshire', 'buckinghamshire', 'berkshire', 'hertfordshire',
    'liverpool', 'leeds', 'bristol', 'edinburgh', 'glasgow', 'cardiff',
    'belfast', 'northern ireland', 'middlesex', 'greater manchester',
    'greater london', 'aberdeen', 'aberdeenshire', 'angus', 'argyll',
    'ayrshire', 'banffshire', 'berwickshire', 'caithness', 'clackmannanshire',
    'dumfriesshire', 'east lothian', 'fife', 'inverness-shire', 'kinross',
    'kirkcudbrightshire', 'lanarkshire', 'midlothian', 'morayshire',
    'nairnshire', 'orkney', 'peeblesshire', 'perth', 'perthshire',
    'renfrewshire', 'ross-shire', 'roxburghshire', 'selkirkshire',
    'shetland', 'stirlingshire', 'sutherland', 'west lothian', 'wigtownshire',
}

CATEGORY_TO_FRAMEWORK = [
    (re.compile(r'food|grocer|meal', re.I), 'food'),
    (re.compile(r'health|medic|prescription|covid', re.I), 'healthcare'),
    (re.compile(r'housing|rent|eviction|shelter|land', re.I), 'housing_land'),
    (re.compile(r'energy|digital|tech', re.I), 'energy_digital'),
    (re.compile(r'education|youth|tutor|school', re.I), 'education'),
    (re.compile(r'arts|culture|festival', re.I), 'recreation_arts'),
    (re.compile(r'climate|environment|ecology|garden', re.I), 'ecology'),
]


def cache_path(name):
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = hashlib.sha1(name.encode('utf-8')).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f'{safe}.json')


def http_get(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch_cached(url, refresh=False):
    p = cache_path(url)
    if not refresh and os.path.exists(p) and os.path.getsize(p) > 32:
        with open(p, 'rb') as f:
            return f.read()
    body = http_get(url)
    with open(p, 'wb') as f:
        f.write(body)
    time.sleep(SLEEP_BETWEEN)
    return body


def fetch_maw_groups(refresh=False):
    body = fetch_cached(MAW_GROUPS_URL, refresh=refresh)
    wrapper = json.loads(body.decode('utf-8'))
    inner = wrapper.get('body')
    if isinstance(inner, str):
        return json.loads(inner)
    if isinstance(inner, list):
        return inner
    return []


def fetch_mah_docs(refresh=False):
    """Walk the Firestore listDocuments pages until nextPageToken stops.
    The cache key carries the pageToken because the URL itself does, so the
    cache stays correct without an extra page counter."""
    docs = []
    next_token = None
    page = 1
    while True:
        url = f'{MAH_FIRESTORE_URL}?pageSize=300'
        if next_token:
            url += '&pageToken=' + urllib.parse.quote(next_token)
        body = fetch_cached(url, refresh=refresh)
        page_data = json.loads(body.decode('utf-8'))
        these = page_data.get('documents') or []
        docs.extend(these)
        print(f'  MAH page {page}: {len(these)} documents')
        next_token = page_data.get('nextPageToken')
        if not next_token or not these:
            break
        page += 1
        if page > 50:
            print('  MAH safety break at 50 pages')
            break
    return docs


# ── parse Mutual Aid Wiki rows ────────────────────────────────────────────

def derive_maw_country(loc):
    parts = [p.strip() for p in (loc or '').split(',') if p.strip()]
    if not parts:
        return ('', '')
    last = parts[-1]
    iso = COUNTRY_NAME_TO_ISO.get(last.lower())
    if iso:
        return (iso, last)
    # if last looks like a UK county, mark as GB
    if last.lower() in UK_REGIONS:
        return ('GB', 'United Kingdom')
    # one more pass: any of the last few parts a UK region?
    for p in parts[-3:]:
        if p.lower() in UK_REGIONS:
            return ('GB', 'United Kingdom')
    # 2-letter ISO codes appearing at the end of US addresses (e.g. 'CA')
    # would mistakenly map here; require length >= 3 for the alpha-2 check.
    if len(last) == 2 and last.isalpha() and last.upper() in COUNTRY_NAME_TO_ISO.values():
        return (last.upper(), last.upper())
    return ('', last)


def maw_to_row(g):
    name = (g.get('name') or '').strip()
    if not name:
        return None
    loc = g.get('location_name') or ''
    iso, cname = derive_maw_country(loc)
    coord = g.get('location_coord') or {}
    contact = g.get('contact') or {}
    desc = (g.get('description') or '').strip()
    return {
        'name': name,
        'country_code': iso,
        'country_name': cname,
        'city': '',
        'state_province': '',
        'lat': coord.get('lat'),
        'lon': coord.get('lng'),
        'website': (g.get('link_facebook') or '').strip(),
        'email': (contact.get('email') or '').strip(),
        'phone': (contact.get('phone') or '').strip(),
        'description': desc[:1500] if desc else '',
        'framework_area': 'democracy',
        'model_type': 'mutual_aid',
        'tags': 'mutual_aid',
        'source_id': g.get('id') or hashlib.sha1((name + loc).encode('utf-8')).hexdigest()[:16],
        'evidence_url': MAW_GROUPS_URL,
    }


# ── parse Mutual Aid Hub Firestore docs ──────────────────────────────────

def fs_value(field):
    """Pull a primitive value out of a Firestore Value union type."""
    if not isinstance(field, dict):
        return None
    if 'stringValue' in field:
        return field['stringValue']
    if 'doubleValue' in field:
        return field['doubleValue']
    if 'integerValue' in field:
        return int(field['integerValue'])
    if 'booleanValue' in field:
        return field['booleanValue']
    if 'arrayValue' in field:
        return [fs_value(v) for v in (field['arrayValue'].get('values') or [])]
    return None


def mah_to_row(doc):
    fields = doc.get('fields') or {}
    title = (fs_value(fields.get('title')) or '').strip()
    if not title:
        return None
    country_raw = (fs_value(fields.get('country')) or '').strip()
    iso = COUNTRY_NAME_TO_ISO.get(country_raw.lower(), country_raw if len(country_raw) == 2 else '')
    cname = country_raw if country_raw else ''
    state = (fs_value(fields.get('state')) or '').strip()
    city = (fs_value(fields.get('city')) or '').strip()
    cat = fs_value(fields.get('category')) or ''
    community = fs_value(fields.get('community')) or ''
    tags_list = fs_value(fields.get('displayFilterTags')) or []
    haystack = ' '.join([cat, community] + (tags_list if isinstance(tags_list, list) else []))
    framework = 'democracy'
    for pat, area in CATEGORY_TO_FRAMEWORK:
        if pat.search(haystack):
            framework = area
            break
    name_parts = doc.get('name', '').split('/')
    doc_id = name_parts[-1] if name_parts else ''
    desc_bits = []
    if community:
        desc_bits.append(f'community: {community}')
    if cat and cat.lower() != 'general':
        desc_bits.append(f'category: {cat}')
    if isinstance(tags_list, list) and tags_list:
        desc_bits.append('tags: ' + ', '.join(t for t in tags_list if t))
    return {
        'name': title,
        'country_code': iso or 'US',
        'country_name': cname or 'United States',
        'state_province': state,
        'city': city,
        'lat': fs_value(fields.get('lat')),
        'lon': fs_value(fields.get('lng')),
        'website': (fs_value(fields.get('facebookPage')) or '').strip(),
        'email': '',
        'phone': '',
        'description': '. '.join(desc_bits)[:1500],
        'framework_area': framework,
        'model_type': 'mutual_aid',
        'tags': ', '.join(t for t in tags_list if t) if isinstance(tags_list, list) else '',
        'source_id': doc_id,
        'evidence_url': 'https://www.mutualaidhub.org/',
    }


def run_migration(db):
    for col, typedef in [
        ('evidence_url', 'TEXT'),
        ('evidence_quote', 'TEXT'),
        ('evidence_fetched_at', 'TEXT'),
        ('legibility', "TEXT DEFAULT 'unknown'"),
    ]:
        ensure_column(db, 'organizations', col, typedef)


def upsert(db, source_name, rows, dry_run=False):
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
            (source_name, r['source_id']),
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
                       lat=COALESCE(lat, ?),
                       lon=COALESCE(lon, ?),
                       geo_source=COALESCE(NULLIF(geo_source,''), ?),
                       website=COALESCE(NULLIF(website,''), ?),
                       email=COALESCE(NULLIF(email,''), ?),
                       phone=COALESCE(NULLIF(phone,''), ?),
                       description=COALESCE(NULLIF(description,''), ?),
                       framework_area=COALESCE(NULLIF(framework_area,''), ?),
                       model_type=?,
                       tags=COALESCE(NULLIF(tags,''), ?),
                       alignment_score=MAX(COALESCE(alignment_score,0), ?),
                       evidence_url=COALESCE(NULLIF(evidence_url,''), ?),
                       evidence_fetched_at=?,
                       legibility='informal'
                   WHERE id=?""",
                (
                    r['name'], r['country_code'], r['country_name'],
                    r['state_province'], r['city'],
                    r.get('lat'), r.get('lon'), source_name,
                    r.get('website', ''), r.get('email', ''), r.get('phone', ''),
                    r.get('description', ''), r['framework_area'],
                    r['model_type'], r.get('tags', ''),
                    1, r['evidence_url'], now, existing[0],
                ),
            )
            updated += 1
        else:
            c.execute(
                """INSERT OR IGNORE INTO organizations
                   (name, country_code, country_name, state_province, city,
                    lat, lon, geo_source,
                    website, email, phone,
                    description, framework_area, model_type, tags,
                    source, source_id, alignment_score,
                    status, date_added,
                    legibility, evidence_url, evidence_fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?)""",
                (
                    r['name'], r['country_code'], r['country_name'],
                    r['state_province'], r['city'],
                    r.get('lat'), r.get('lon'), source_name,
                    r.get('website', ''), r.get('email', ''), r.get('phone', ''),
                    r.get('description', ''), r['framework_area'],
                    r['model_type'], r.get('tags', ''),
                    source_name, r['source_id'], 1,
                    now,
                    'informal', r['evidence_url'], now,
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
        f.write(f'\n# ingest_mutual_aid_wiki run - {today}\n\n')
        for line in lines:
            f.write(line + '\n')


def main():
    ap = argparse.ArgumentParser(description='Mutual Aid Wiki + Hub ingest')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--refresh', action='store_true')
    args = ap.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Ingesting Mutual Aid Wiki + Mutual Aid Hub")

    print('  Fetching Mutual Aid Wiki groups.json...')
    maw = fetch_maw_groups(refresh=args.refresh)
    print(f'  MAW groups parsed: {len(maw)}')
    maw_rows = [maw_to_row(g) for g in maw]
    maw_rows = [r for r in maw_rows if r]
    print(f'  MAW usable rows: {len(maw_rows)}')

    print('  Fetching Mutual Aid Hub Firestore docs...')
    mah = fetch_mah_docs(refresh=args.refresh)
    print(f'  MAH docs parsed: {len(mah)}')
    mah_rows = [mah_to_row(d) for d in mah]
    mah_rows = [r for r in mah_rows if r]
    print(f'  MAH usable rows: {len(mah_rows)}')

    db = sqlite3.connect(DB_PATH)
    run_migration(db)
    maw_ins, maw_upd = upsert(db, 'mutual_aid_wiki', maw_rows, dry_run=args.dry_run)
    mah_ins, mah_upd = upsert(db, 'mutual_aid_hub', mah_rows, dry_run=args.dry_run)
    db.close()

    mode = '[DRY RUN] Would insert' if args.dry_run else 'Inserted'
    summary = [
        f"Mode: {'dry-run' if args.dry_run else 'real'}",
        f"MAW source: {MAW_GROUPS_URL}",
        f"MAH source: {MAH_FIRESTORE_URL}",
        f"MAW rows parsed/usable: {len(maw)}/{len(maw_rows)}",
        f"MAH docs parsed/usable: {len(mah)}/{len(mah_rows)}",
        f"MAW {mode}: {maw_ins} (updated {maw_upd})",
        f"MAH {mode}: {mah_ins} (updated {mah_upd})",
        "MAW licence: CC BY-NC-SA 4.0",
        "MAH licence: PDDL-1.0",
    ]
    print('\n' + '\n'.join(summary))
    write_log(summary)
    print(f'\nLog appended: {LOG_PATH}')


if __name__ == '__main__':
    main()
