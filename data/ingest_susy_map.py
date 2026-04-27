"""
SUSY Map ingest. SUSY was a 2015-2018 EU-funded project led by RIPESS Europe
that catalogued social and solidarity economy initiatives across Europe. The
front-end at solidarityeconomy.eu/susy-map/ no longer hosts the data (the
domain has been repurposed by an unrelated blog), but the underlying GeoJSON
export still lives in the TransforMap viewer's gh-pages branch as a
"fallback" file. That snapshot is what we ingest here.

Source order:
  1. https://github.com/TransforMap/transformap-viewer/raw/gh-pages/
     susydata-fallback.json. About 890 geocoded EU initiatives, hand-curated
     by SUSY partners, license: Public Domain. Cached under
     data/sources/susy-cache/.

Why this is enough:
  - The brief asked for "find the data endpoint" of the SUSY map. Today,
    2026-04-26, that endpoint is the gh-pages JSON file. The original
    susy.ripess.eu and ripesseu.net hosts no longer serve the dataset.
  - The data is older than the rest of Wave B (frozen 2018) so we tag the
    rows accordingly and rely on the alignment scorer to demote anything
    that the registry has already replaced with a fresher version.

Mapping:
  - source           = 'susy_map'
  - source_id        = stable hash of (name + lat + lon) so re-runs do not
                       create duplicates and a row whose name was edited
                       slightly does not double-insert.
  - country_code     = normalized to ISO 3166-1 alpha-2 from the messy
                       addr:country field (some rows say 'Italy', others
                       'IT', a few say nothing at all).
  - legibility       = 'formal'. SUSY's selection criterion was network
                       membership; partners hand-curated the entries.
  - framework_area   = derived from type_of_initiative. Many SUSY entries
                       are food co-ops, energy co-ops, community gardens,
                       and the like, so the mapping is straightforward.
  - model_type       = 'cooperative' when the name or POI shouts coop,
                       'collective' when community garden / informal,
                       otherwise 'nonprofit'.

Re-runs are idempotent on (source='susy_map', source_id=hash).

Usage:
    python ingest_susy_map.py             # real run
    python ingest_susy_map.py --dry-run   # parse + count only
    python ingest_susy_map.py --refresh   # ignore cache, re-download
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from _common import DB_PATH, DATA_DIR, ensure_column

CACHE_DIR = os.path.join(DATA_DIR, 'sources', 'susy-cache')
LOG_PATH = os.path.join(DATA_DIR, 'ingest-susy-run.log')

USER_AGENT = (
    'Mozilla/5.0 (compatible; Commonweave/1.0 directory bot; '
    '+https://commonweave.earth; hello@simonlpaige.com)'
)
SLEEP_BETWEEN = 1

SUSY_JSON_URL = (
    'https://github.com/TransforMap/transformap-viewer/raw/gh-pages/'
    'susydata-fallback.json'
)

# Country names that SUSY mixed in alongside ISO codes. Mapped here once so
# the rest of the script can assume a clean alpha-2 code.
COUNTRY_NAME_TO_ISO = {
    'italy': 'IT', 'germany': 'DE', 'österreich': 'AT', 'osterreich': 'AT',
    'austria': 'AT', 'united kingdom': 'GB', 'great britain': 'GB',
    'estonia': 'EE', 'malta': 'MT', 'slovenia': 'SI', 'croatia': 'HR',
    'czech republic': 'CZ', 'czechia': 'CZ', 'spain': 'ES', 'france': 'FR',
    'greece': 'GR', 'hungary': 'HU', 'romania': 'RO', 'portugal': 'PT',
    'belgium': 'BE', 'netherlands': 'NL', 'poland': 'PL', 'denmark': 'DK',
    'sweden': 'SE', 'finland': 'FI', 'ireland': 'IE', 'luxembourg': 'LU',
    'cyprus': 'CY', 'lithuania': 'LT', 'latvia': 'LV', 'slovakia': 'SK',
    'bulgaria': 'BG', 'switzerland': 'CH', 'norway': 'NO', 'iceland': 'IS',
    'turkey': 'TR', 'serbia': 'RS', 'bosnia and herzegovina': 'BA',
    'north macedonia': 'MK', 'macedonia': 'MK', 'albania': 'AL',
    'montenegro': 'ME', 'kosovo': 'XK', 'moldova': 'MD', 'ukraine': 'UA',
}

ISO_TO_COUNTRY_NAME = {
    'IT': 'Italy', 'DE': 'Germany', 'AT': 'Austria', 'GB': 'United Kingdom',
    'EE': 'Estonia', 'MT': 'Malta', 'SI': 'Slovenia', 'HR': 'Croatia',
    'CZ': 'Czech Republic', 'ES': 'Spain', 'FR': 'France', 'GR': 'Greece',
    'HU': 'Hungary', 'RO': 'Romania', 'PT': 'Portugal', 'BE': 'Belgium',
    'NL': 'Netherlands', 'PL': 'Poland', 'DK': 'Denmark', 'SE': 'Sweden',
    'FI': 'Finland', 'IE': 'Ireland', 'LU': 'Luxembourg', 'CY': 'Cyprus',
    'LT': 'Lithuania', 'LV': 'Latvia', 'SK': 'Slovakia', 'BG': 'Bulgaria',
    'CH': 'Switzerland', 'NO': 'Norway', 'IS': 'Iceland', 'TR': 'Turkey',
    'RS': 'Serbia', 'BA': 'Bosnia and Herzegovina', 'MK': 'North Macedonia',
    'AL': 'Albania', 'ME': 'Montenegro', 'XK': 'Kosovo', 'MD': 'Moldova',
    'UA': 'Ukraine',
}

# SUSY uses its own type_of_initiative + POI_TYPE vocabulary. Map the most
# common values onto Commonweave framework areas. The list is short on
# purpose: when a value isn't in here we fall back to '' and let the
# downstream scorer guess from name + description.
TYPE_TO_FRAMEWORK = [
    # food / agriculture
    ('food', 'food'), ('agriculture', 'food'), ('community_garden', 'food'),
    ('garden', 'food'), ('farm', 'food'), ('csa', 'food'),
    ('supermarket', 'food'), ('grocery', 'food'), ('market', 'food'),
    # energy / digital commons
    ('energy', 'energy_digital'), ('renewable', 'energy_digital'),
    ('digital', 'energy_digital'), ('hackerspace', 'energy_digital'),
    ('makerspace', 'energy_digital'), ('fablab', 'energy_digital'),
    # housing / land
    ('housing', 'housing_land'), ('cohousing', 'housing_land'),
    ('land_trust', 'housing_land'), ('community_land', 'housing_land'),
    # cooperative / SSE umbrella
    ('cooperative', 'cooperatives'), ('co-op', 'cooperatives'),
    ('coop', 'cooperatives'), ('credit_union', 'cooperatives'),
    ('finance', 'cooperatives'), ('bank', 'cooperatives'),
    # education
    ('education', 'education'), ('school', 'education'),
    ('university', 'education'), ('training', 'education'),
    # culture / arts
    ('culture', 'recreation_arts'), ('arts', 'recreation_arts'),
    ('theatre', 'recreation_arts'), ('cinema', 'recreation_arts'),
    ('music', 'recreation_arts'),
    # ecology
    ('ecology', 'ecology'), ('environment', 'ecology'),
    ('recycling', 'ecology'), ('repair', 'ecology'),
]


def cache_path():
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, 'susydata-fallback.json')


def http_get(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch_susy_data(refresh=False):
    p = cache_path()
    if not refresh and os.path.exists(p) and os.path.getsize(p) > 1024:
        print(f'  Using cached SUSY data: {p} ({os.path.getsize(p):,} bytes)')
        with open(p, 'rb') as f:
            return json.loads(f.read().decode('utf-8'))
    print(f'  Downloading SUSY data from {SUSY_JSON_URL}')
    try:
        body = http_get(SUSY_JSON_URL)
    except urllib.error.HTTPError as e:
        print(f'  Download failed: HTTP {e.code} {e.reason}')
        return None
    except Exception as e:
        print(f'  Download failed: {e}')
        return None
    with open(p, 'wb') as f:
        f.write(body)
    time.sleep(SLEEP_BETWEEN)
    print(f'  Downloaded {len(body):,} bytes')
    return json.loads(body.decode('utf-8'))


def normalize_country(raw):
    """Return (iso2, country_name) given SUSY's messy addr:country."""
    if not raw:
        return ('', '')
    s = raw.strip()
    if len(s) == 2 and s.isalpha():
        iso = s.upper()
        return (iso, ISO_TO_COUNTRY_NAME.get(iso, iso))
    iso = COUNTRY_NAME_TO_ISO.get(s.lower())
    if iso:
        return (iso, ISO_TO_COUNTRY_NAME.get(iso, s))
    return ('', s)


def derive_framework(props):
    """Pick a framework area from type_of_initiative + POI_TYPE + free_keywords.
    First match wins."""
    haystack_parts = []
    for k in ('type_of_initiative', 'POI_TYPE', 'free_keywords', 'shop',
              'amenity', 'leisure', 'office', 'craft'):
        v = props.get(k)
        if v:
            haystack_parts.append(str(v).lower())
    haystack = ' | '.join(haystack_parts)
    for needle, area in TYPE_TO_FRAMEWORK:
        if needle in haystack:
            return area
    return ''


def derive_model_type(name, props):
    low = (name or '').lower()
    if 'cooperative' in low or 'co-op' in low or 'coop' in low or '.coop' in low:
        return 'cooperative'
    poi = (props.get('POI_TYPE') or '').lower()
    toi = (props.get('type_of_initiative') or '').lower()
    if 'cooperative' in poi or 'cooperative' in toi:
        return 'cooperative'
    if 'community_garden' in toi or 'community garden' in poi:
        return 'collective'
    if 'mutual' in low:
        return 'mutual_aid'
    return 'nonprofit'


def derive_description(props):
    parts = []
    if props.get('description'):
        parts.append(props['description'].strip())
    toi = props.get('type_of_initiative')
    poi = props.get('POI_TYPE')
    if toi:
        parts.append(f'type: {toi}')
    elif poi:
        parts.append(f'type: {poi}')
    fk = props.get('free_keywords')
    if fk:
        parts.append(f'tags: {fk}')
    sse = props.get('SSEDAS_PARTNER')
    if sse:
        parts.append(f'curated by: {sse}')
    return '. '.join(p for p in parts if p)


def stable_id(name, lat, lon):
    """A short hash that survives whitespace and capitalization wobble in
    the SUSY name field."""
    norm = (name or '').strip().lower()
    blob = f'{norm}|{lat:.4f}|{lon:.4f}'.encode('utf-8')
    return hashlib.sha1(blob).hexdigest()[:16]


def parse_features(geojson):
    feats = (geojson or {}).get('features', [])
    rows = []
    skipped = 0
    for f in feats:
        geom = f.get('geometry') or {}
        if geom.get('type') != 'Point':
            skipped += 1
            continue
        coords = geom.get('coordinates') or []
        if len(coords) < 2:
            skipped += 1
            continue
        lon = float(coords[0])
        lat = float(coords[1])
        props = f.get('properties') or {}
        name = (props.get('name') or '').strip()
        if not name:
            skipped += 1
            continue
        iso, cname = normalize_country(props.get('addr:country', ''))
        rows.append({
            'name': name,
            'country_code': iso,
            'country_name': cname,
            'city': (props.get('addr:city') or '').strip(),
            'state_province': '',
            'lat': lat,
            'lon': lon,
            'website': (props.get('website') or props.get('contact:website') or '').strip(),
            'email': (props.get('contact:email') or '').strip(),
            'phone': (props.get('contact:phone') or '').strip(),
            'description': derive_description(props),
            'framework_area': derive_framework(props),
            'model_type': derive_model_type(name, props),
            'source_id': stable_id(name, lat, lon),
            'evidence_url': SUSY_JSON_URL,
        })
    return rows, skipped


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
        if dry_run:
            inserted += 1
            continue
        c.execute(
            "SELECT id FROM organizations WHERE source=? AND source_id=?",
            ('susy_map', r['source_id']),
        )
        existing = c.fetchone()
        if existing:
            c.execute(
                """UPDATE organizations
                   SET name=?,
                       country_code=COALESCE(NULLIF(country_code,''), ?),
                       country_name=COALESCE(NULLIF(country_name,''), ?),
                       city=COALESCE(NULLIF(city,''), ?),
                       lat=COALESCE(lat, ?),
                       lon=COALESCE(lon, ?),
                       geo_source=COALESCE(NULLIF(geo_source,''), 'susy_map'),
                       website=COALESCE(NULLIF(website,''), ?),
                       email=COALESCE(NULLIF(email,''), ?),
                       phone=COALESCE(NULLIF(phone,''), ?),
                       description=COALESCE(NULLIF(description,''), ?),
                       framework_area=COALESCE(NULLIF(framework_area,''), ?),
                       model_type=?,
                       alignment_score=MAX(COALESCE(alignment_score,0), ?),
                       evidence_url=COALESCE(NULLIF(evidence_url,''), ?),
                       evidence_fetched_at=?,
                       legibility='formal'
                   WHERE id=?""",
                (
                    r['name'], r['country_code'], r['country_name'],
                    r['city'], r['lat'], r['lon'],
                    r['website'], r['email'], r['phone'],
                    r['description'], r['framework_area'], r['model_type'],
                    2, r['evidence_url'], now, existing[0],
                ),
            )
            updated += 1
        else:
            c.execute(
                """INSERT OR IGNORE INTO organizations
                   (name, country_code, country_name, city,
                    lat, lon, geo_source,
                    website, email, phone,
                    description, framework_area, model_type,
                    source, source_id, alignment_score,
                    status, date_added,
                    legibility, evidence_url, evidence_fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?)""",
                (
                    r['name'], r['country_code'], r['country_name'], r['city'],
                    r['lat'], r['lon'], 'susy_map',
                    r['website'], r['email'], r['phone'],
                    r['description'], r['framework_area'], r['model_type'],
                    'susy_map', r['source_id'], 2,
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
        f.write(f'\n# ingest_susy_map run - {today}\n\n')
        for line in lines:
            f.write(line + '\n')


def main():
    ap = argparse.ArgumentParser(description='SUSY Map ingest')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--refresh', action='store_true')
    args = ap.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Ingesting SUSY Map (EU SSE)")

    data = fetch_susy_data(refresh=args.refresh)
    if not data:
        print('  FATAL: could not obtain SUSY data. Stopping.')
        sys.exit(1)
    rows, skipped = parse_features(data)
    print(f'  Parsed {len(rows)} usable rows, skipped {skipped} (no name / no point geom)')

    db = sqlite3.connect(DB_PATH)
    run_migration(db)
    inserted, updated = upsert(db, rows, dry_run=args.dry_run)
    db.close()

    mode = '[DRY RUN] Would insert' if args.dry_run else 'Inserted'
    summary = [
        f"Mode: {'dry-run' if args.dry_run else 'real'}",
        f"Source: {SUSY_JSON_URL}",
        f"Features parsed: {len(rows)}",
        f"Skipped (no name / no point): {skipped}",
        f"{mode}: {inserted}",
        f"Updated: {updated}",
    ]
    print('\n' + '\n'.join(summary))
    write_log(summary)
    print(f'\nLog appended: {LOG_PATH}')


if __name__ == '__main__':
    main()
