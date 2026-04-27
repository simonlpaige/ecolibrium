"""
RIPESS family ingest. Pulls what we can scrape across the RIPESS umbrella
and its continental networks.

Source landscape, audited 2026-04-26:
  - ripess.org              live, ~9 named affiliates on /membres/
  - ripess.eu               live, points members at socioeco.org reseau 471
  - socioeco.org reseau-471 live JSON, 45 RIPESS Europe members geocoded
  - socioeco.org reseau-472 live JSON, 20 RIPESS LAC members
  - socioeco.org reseau-473 live JSON,  3 RIPESS NA members
  - raess.org               DNS does not resolve (RIPESS Africa)
  - asec.coop               DNS does not resolve (RIPESS Asia)
  - riless.org              domain hijacked by an unrelated blog

The two dead RIPESS sites get a partnership TODO at
tools/mycelial-outreach/drafts/pending/ripess-africa-and-asia-2026-04-26.md
so Simon can chase them through info@ripess.org. We do not block Wave B
on outreach.

Data sources actually used:
  1. SEED_APEX: hand-curated list of the RIPESS umbrella plus its named
     continental affiliates (RIPESS itself, RIPESS LAC, RAESS, ASEC,
     RIPESS NA, RIPESS EU, RIPESS Oceania) and the three international
     organisations RIPESS lists alongside them (Urgenci, GSEF, INAISE).
     Stable seed because these names do not move.
  2. socioeco.org reseau-<id>_en.json for IDs 471, 472, 473. Each member
     comes back as a GeoJSON Feature with id, name, subtitle, url,
     contact, lat/long, year founded, and category tags.

source='ripess_family'. Idempotent on (source, source_id) where
source_id is 'apex:<slug>' for the seed and 'socioeco:<id>' for the
GeoJSON members. legibility='formal' (RIPESS membership implies
registered legal form).

Usage:
    python ingest_ripess_family.py             # real run
    python ingest_ripess_family.py --dry-run   # parse + count, no writes
    python ingest_ripess_family.py --refresh   # ignore cache, re-fetch
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

CACHE_DIR = os.path.join(DATA_DIR, 'sources', 'ripess-cache')
LOG_PATH = os.path.join(DATA_DIR, 'ingest-ripess-run.log')

USER_AGENT = (
    'Mozilla/5.0 (compatible; Commonweave/1.0 directory bot; '
    '+https://commonweave.earth; hello@simonlpaige.com)'
)
SLEEP_BETWEEN = 1.5

# socioeco network IDs that hold the RIPESS-family rosters as of 2026-04-26.
RESEAU_IDS = {
    471: ('RIPESS Europe', 'EU', 'Europe'),
    472: ('RIPESS LAC', 'LAC', 'Latin America and the Caribbean'),
    473: ('RIPESS NA', 'NA', 'North America'),
}
RESEAU_URL_TMPL = 'http://www.socioeco.org/reseau-{id}_en.json'

# Hand-seeded apex orgs. Each entry: (slug, name, country_code,
# country_name, website, description). Country codes are 'GLOBAL' for
# borderless networks per the brief; the directory column country_code
# stores 'GLOBAL' there. country_name carries the human-readable scope.
SEED_APEX = [
    ('ripess', 'RIPESS - Intercontinental Network for the Promotion of Social Solidarity Economy',
     'GLOBAL', 'Global', 'https://www.ripess.org/',
     'Intercontinental network of continental SSE networks. RIPESS aggregates RIPESS LAC (Latin America), RAESS (Africa), ASEC (Asia), RIPESS NA (North America), RIPESS EU (Europe), and RIPESS Oceania.'),
    ('ripess-lac', 'RIPESS LAC - Red Intercontinental de Promocion de la Economia Social Solidaria, Latinoamerica y Caribe',
     'GLOBAL', 'Latin America and the Caribbean', 'https://www.ripess.org/membres/',
     'Latin America and Caribbean continental chapter of RIPESS. Member network of national SSE federations.'),
    ('raess', 'RAESS - Reseau Africain de l\'Economie Sociale et Solidaire',
     'GLOBAL', 'Africa and Middle East', 'https://www.ripess.org/membres/',
     'Africa and Middle East continental chapter of RIPESS. Domain raess.org currently unreachable; outreach pending.'),
    ('asec', 'ASEC - Asian Solidarity Economy Council',
     'GLOBAL', 'Asia', 'https://www.ripess.org/membres/',
     'Asian continental chapter of RIPESS. Domain asec.coop currently unreachable; outreach pending.'),
    ('ripess-na', 'RIPESS NA - North American Network for the Solidarity Economy',
     'GLOBAL', 'North America', 'https://www.ripess.org/membres/',
     'North America continental chapter of RIPESS. Includes the US Solidarity Economy Network and Canadian co-op networks.'),
    ('ripess-eu', 'RIPESS EU - Solidarity Economy Europe',
     'GLOBAL', 'Europe', 'https://www.ripess.eu/',
     'European continental chapter of RIPESS. Members listed via the socioeco.org mirror, network id 471.'),
    ('ripess-oceania', 'RIPESS Oceania',
     'GLOBAL', 'Oceania', 'https://www.ripess.org/membres/',
     'Oceania continental chapter of RIPESS.'),
    ('urgenci', 'Urgenci - International Network for Community Supported Agriculture',
     'GLOBAL', 'Global', 'http://urgenci.net/',
     'International network of Community Supported Agriculture initiatives, listed alongside RIPESS continental chapters as a partner network.'),
    ('gsef', 'GSEF - Global Social Economy Forum',
     'GLOBAL', 'Global', 'https://www.gsef-net.org/',
     'Global Social Economy Forum, a network of city governments, civil society organisations, and SSE networks. RIPESS partner organisation.'),
    ('inaise', 'INAISE - International Association of Investors in the Social Economy',
     'GLOBAL', 'Global', 'https://www.inaise.org/',
     'International Association of Investors in the Social Economy. RIPESS partner organisation.'),
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


# Country derivation for socioeco features. The portee field tells us
# the scope (LOC/REG/NAT/CNT/INT) but not the country. We crack the
# country off the URL hostname's TLD where possible, then fall back to
# checking the contact line for a country name.
HOSTNAME_TLD_TO_ISO = {
    'es': 'ES', 'it': 'IT', 'fr': 'FR', 'de': 'DE', 'be': 'BE',
    'nl': 'NL', 'gr': 'GR', 'pt': 'PT', 'cz': 'CZ', 'pl': 'PL',
    'ro': 'RO', 'hu': 'HU', 'ch': 'CH', 'at': 'AT', 'se': 'SE',
    'no': 'NO', 'dk': 'DK', 'fi': 'FI', 'gal': 'ES',  # gal == Galicia, ES
    'cat': 'ES',  # catalan
    'br': 'BR', 'ar': 'AR', 'cl': 'CL', 'mx': 'MX', 'uy': 'UY',
    'co': 'CO', 'pe': 'PE', 'bo': 'BO', 'ec': 'EC', 'py': 'PY', 've': 'VE',
    'ca': 'CA', 'us': 'US', 'au': 'AU', 'nz': 'NZ',
    'jp': 'JP', 'kr': 'KR', 'tw': 'TW', 'ph': 'PH', 'in': 'IN',
    'id': 'ID', 'my': 'MY', 'th': 'TH', 'vn': 'VN',
    'za': 'ZA', 'ke': 'KE', 'ng': 'NG', 'ma': 'MA', 'tn': 'TN',
    'eg': 'EG', 'gh': 'GH',
    'tr': 'TR', 'il': 'IL', 'ru': 'RU', 'ua': 'UA',
    'uk': 'GB', 'ie': 'IE', 'eu': '',  # .eu is multi-country, leave blank
}


def derive_country_from_url(url):
    if not url:
        return ''
    m = re.search(r'://(?:www\.)?[^/]+\.([a-z]{2,3})(?:/|$)', url.lower())
    if not m:
        return ''
    return HOSTNAME_TLD_TO_ISO.get(m.group(1), '')


def parse_socioeco_feature(feat, network_label, network_id):
    geom = feat.get('geometry') or {}
    coords = geom.get('coordinates') or []
    lat = lon = None
    if geom.get('type') == 'Point' and len(coords) >= 2:
        lon, lat = float(coords[0]), float(coords[1])
    props = feat.get('properties') or {}
    name = (props.get('name') or '').strip()
    if not name:
        return None
    sid = props.get('id')
    if sid is None:
        return None
    url = (props.get('url') or '').strip()
    desc_bits = []
    sub = strip_html(props.get('subtitle') or '')
    if sub:
        desc_bits.append(sub)
    annee = props.get('annee')
    if annee:
        desc_bits.append(f'founded: {annee}')
    portee = props.get('portee')
    portee_label = {
        'LOC': 'local', 'REG': 'regional', 'NAT': 'national',
        'CNT': 'continental', 'INT': 'international', 'SCT': 'sectoral',
    }.get(portee, '')
    if portee_label:
        desc_bits.append(f'scope: {portee_label}')
    desc_bits.append(f'member of: {network_label}')
    description = '. '.join(desc_bits)[:1500]
    cc = derive_country_from_url(url)
    return {
        'name': name,
        'country_code': cc,
        'country_name': '',
        'state_province': '',
        'city': '',
        'lat': lat,
        'lon': lon,
        'description': description,
        'website': url,
        'email': (props.get('contact') or '').replace('[at]', '@').strip(),
        'phone': '',
        'framework_area': 'cooperatives',
        'model_type': 'cooperative',
        'tags': f'ripess_member, {network_label}',
        'source_id': f'socioeco:{network_id}:{sid}',
        'evidence_url': f'https://www.socioeco.org/bdf_organisme-{sid}_en.html',
    }


def seed_rows():
    rows = []
    for slug, name, cc, cname, url, desc in SEED_APEX:
        rows.append({
            'name': name,
            'country_code': cc,
            'country_name': cname,
            'state_province': '',
            'city': '',
            'lat': None,
            'lon': None,
            'description': desc,
            'website': url,
            'email': '',
            'phone': '',
            'framework_area': 'cooperatives',
            'model_type': 'nonprofit',
            'tags': 'ripess_apex',
            'source_id': f'apex:{slug}',
            'evidence_url': url,
        })
    return rows


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
            ('ripess_family', r['source_id']),
        )
        existing = c.fetchone()
        if existing:
            c.execute(
                """UPDATE organizations
                   SET name=?,
                       country_code=COALESCE(NULLIF(country_code,''), ?),
                       country_name=COALESCE(NULLIF(country_name,''), ?),
                       lat=COALESCE(lat, ?),
                       lon=COALESCE(lon, ?),
                       geo_source=COALESCE(NULLIF(geo_source,''), 'ripess_family'),
                       description=COALESCE(NULLIF(description,''), ?),
                       framework_area=COALESCE(NULLIF(framework_area,''), ?),
                       model_type=?,
                       website=COALESCE(NULLIF(website,''), ?),
                       email=COALESCE(NULLIF(email,''), ?),
                       tags=COALESCE(NULLIF(tags,''), ?),
                       alignment_score=MAX(COALESCE(alignment_score,0), ?),
                       evidence_url=COALESCE(NULLIF(evidence_url,''), ?),
                       evidence_fetched_at=?,
                       legibility='formal'
                   WHERE id=?""",
                (
                    r['name'], r['country_code'], r['country_name'],
                    r.get('lat'), r.get('lon'),
                    r['description'], r['framework_area'],
                    r['model_type'], r['website'], r['email'],
                    r['tags'], 3, r['evidence_url'], now, existing[0],
                ),
            )
            updated += 1
        else:
            c.execute(
                """INSERT OR IGNORE INTO organizations
                   (name, country_code, country_name,
                    lat, lon, geo_source,
                    description, framework_area, model_type,
                    website, email, tags,
                    source, source_id, alignment_score,
                    status, date_added,
                    legibility, evidence_url, evidence_fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?)""",
                (
                    r['name'], r['country_code'], r['country_name'],
                    r.get('lat'), r.get('lon'), 'ripess_family',
                    r['description'], r['framework_area'],
                    r['model_type'], r['website'], r['email'], r['tags'],
                    'ripess_family', r['source_id'], 3,
                    now,
                    'formal', r['evidence_url'], now,
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
        f.write(f'\n# ingest_ripess_family run - {today}\n\n')
        for line in lines:
            f.write(line + '\n')


def main():
    ap = argparse.ArgumentParser(description='RIPESS family ingest (umbrella + EU + LAC + NA)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--refresh', action='store_true')
    args = ap.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Ingesting RIPESS family")

    rows = []
    rows.extend(seed_rows())
    print(f'  Seed apex orgs: {len(rows)}')

    for net_id, (label, _, _) in RESEAU_IDS.items():
        url = RESEAU_URL_TMPL.format(id=net_id)
        try:
            data = fetch_json(url, refresh=args.refresh)
        except Exception as e:
            print(f'  reseau-{net_id} failed: {e}')
            continue
        feats = (data or {}).get('features') or []
        before = len(rows)
        for feat in feats:
            row = parse_socioeco_feature(feat, label, net_id)
            if row:
                rows.append(row)
        print(f'  reseau-{net_id} ({label}): added {len(rows) - before} rows')

    print(f'  Total rows: {len(rows)}')

    db = sqlite3.connect(DB_PATH)
    run_migration(db)
    inserted, updated = upsert(db, rows, dry_run=args.dry_run)
    db.close()

    mode = '[DRY RUN] Would insert' if args.dry_run else 'Inserted'
    summary = [
        f"Mode: {'dry-run' if args.dry_run else 'real'}",
        f"Apex seed rows: {len(SEED_APEX)}",
        f"socioeco network IDs walked: {sorted(RESEAU_IDS.keys())}",
        f"Total rows: {len(rows)}",
        f"{mode}: {inserted}",
        f"Updated: {updated}",
        "Skipped sources: raess.org and asec.coop (DNS unreachable);",
        "  outreach TODO at tools/mycelial-outreach/drafts/pending/",
        "  ripess-africa-and-asia-2026-04-26.md.",
    ]
    print('\n' + '\n'.join(summary))
    write_log(summary)
    print(f'\nLog appended: {LOG_PATH}')


if __name__ == '__main__':
    main()
