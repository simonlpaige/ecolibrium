"""
International Cooperative Alliance directory ingest.

Source: ica.coop publishes its global member directory through the Digital
Commons Co-op map at maps.coop/ica/, which itself reads from a Linked Open
Data dataset at lod.coop/ica/. Digital Commons also serves a flat CSV bulk
export at https://data.digitalcommons.coop/ica/standard.csv. We pull that
file directly and parse with csv.DictReader, which is much friendlier than
walking 322 individual RDF documents.

The dataset is the global directory of cooperative apex organisations and
member co-ops. About 322 rows as of 2026-04-26, geocoded, with addresses,
sector codes, websites, phone, and structured organisational structure /
primary activity / membership type fields (linked to ESS Global standard
vocabularies at lod.coop/essglobal/).

Mapping:
  - source           = 'ica_directory'
  - source_id        = the Identifier column (numeric, stable, the same
                       one that appears in lod.coop/ica/<id> and the
                       ICA member URL).
  - country_code     = the 'Country ID' column (already ISO 3166-1
                       alpha-2; we trust it).
  - legibility       = 'formal'. Every ICA member is a registered
                       cooperative apex or registered co-op.
  - framework_area   = 'cooperatives' on every row. The Primary Activity
                       column is interesting but maps to ICA-internal
                       sector codes; the row already proves cooperative
                       legibility, so we keep the framework area uniform.
  - model_type       = 'cooperative'.
  - alignment_score  = 3 (apex membership is a strong signal).

Re-runs are idempotent on (source='ica_directory', source_id=Identifier).

Usage:
    python ingest_ica_directory.py             # real run
    python ingest_ica_directory.py --dry-run   # parse + count only
    python ingest_ica_directory.py --refresh   # ignore cache, re-download
"""
import argparse
import csv
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

CACHE_DIR = os.path.join(DATA_DIR, 'sources', 'ica-cache')
LOG_PATH = os.path.join(DATA_DIR, 'ingest-ica-run.log')

USER_AGENT = (
    'Mozilla/5.0 (compatible; Commonweave/1.0 directory bot; '
    '+https://commonweave.earth; hello@simonlpaige.com)'
)
SLEEP_BETWEEN = 1

ICA_CSV_URL = 'https://data.digitalcommons.coop/ica/standard.csv'

HTML_TAG_RE = re.compile(r'<[^>]+>')
WHITESPACE_RE = re.compile(r'\s+')
HTML_ENTITY_FIXES = [
    ('&nbsp;', ' '),
    ('&amp;', '&'),
    ('&#39;', "'"),
    ('&#34;', '"'),
    ('&quot;', '"'),
    ('&apos;', "'"),
    ('&#8217;', "'"),
    ('&#8211;', '-'),
    ('&#8220;', '"'),
    ('&#8221;', '"'),
]


def cache_path():
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, 'ica-standard.csv')


def http_get(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'text/csv,application/octet-stream',
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch_csv(refresh=False):
    p = cache_path()
    if not refresh and os.path.exists(p) and os.path.getsize(p) > 1024:
        print(f'  Using cached ICA CSV: {p} ({os.path.getsize(p):,} bytes)')
        return p
    print(f'  Downloading ICA CSV from {ICA_CSV_URL}')
    body = http_get(ICA_CSV_URL)
    with open(p, 'wb') as f:
        f.write(body)
    time.sleep(SLEEP_BETWEEN)
    print(f'  Downloaded {len(body):,} bytes')
    return p


def strip_html(s):
    if not s:
        return ''
    s = HTML_TAG_RE.sub(' ', s)
    for needle, repl in HTML_ENTITY_FIXES:
        s = s.replace(needle, repl)
    return WHITESPACE_RE.sub(' ', s).strip()


def to_row(r):
    name = (r.get('Name') or '').strip()
    if not name:
        return None
    desc = strip_html(r.get('Description') or '')
    if len(desc) > 1500:
        desc = desc[:1497] + '...'
    cc = (r.get('Country ID') or '').strip().upper()
    locality = (r.get('Locality') or '').strip()
    region = (r.get('Region') or '').strip()
    website = (r.get('Website') or '').strip()
    lat_s = (r.get('Latitude') or '').strip()
    lon_s = (r.get('Longitude') or '').strip()
    lat = float(lat_s) if lat_s else None
    lon = float(lon_s) if lon_s else None
    sid = (r.get('Identifier') or '').strip()
    return {
        'name': name,
        'country_code': cc,
        'country_name': '',
        'state_province': region,
        'city': locality,
        'lat': lat,
        'lon': lon,
        'description': desc,
        'website': website,
        'email': (r.get('Email') or '').strip(),
        'phone': (r.get('Phone') or '').strip(),
        'framework_area': 'cooperatives',
        'model_type': 'cooperative',
        'tags': 'ica_member',
        'source_id': sid,
        'evidence_url': f'https://lod.coop/ica/{sid}' if sid else ICA_CSV_URL,
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
            ('ica_directory', r['source_id']),
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
                       geo_source=COALESCE(NULLIF(geo_source,''), 'ica_directory'),
                       description=COALESCE(NULLIF(description,''), ?),
                       framework_area=COALESCE(NULLIF(framework_area,''), ?),
                       model_type=?,
                       website=COALESCE(NULLIF(website,''), ?),
                       email=COALESCE(NULLIF(email,''), ?),
                       phone=COALESCE(NULLIF(phone,''), ?),
                       tags=COALESCE(NULLIF(tags,''), ?),
                       alignment_score=MAX(COALESCE(alignment_score,0), ?),
                       evidence_url=COALESCE(NULLIF(evidence_url,''), ?),
                       evidence_fetched_at=?,
                       legibility='formal'
                   WHERE id=?""",
                (
                    r['name'], r['country_code'], r['country_name'],
                    r['state_province'], r['city'],
                    r.get('lat'), r.get('lon'),
                    r['description'], r['framework_area'],
                    r['model_type'], r['website'],
                    r['email'], r['phone'], r['tags'],
                    3, r['evidence_url'], now, existing[0],
                ),
            )
            updated += 1
        else:
            c.execute(
                """INSERT OR IGNORE INTO organizations
                   (name, country_code, country_name, state_province, city,
                    lat, lon, geo_source,
                    description, framework_area, model_type,
                    website, email, phone, tags,
                    source, source_id, alignment_score,
                    status, date_added,
                    legibility, evidence_url, evidence_fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?)""",
                (
                    r['name'], r['country_code'], r['country_name'],
                    r['state_province'], r['city'],
                    r.get('lat'), r.get('lon'), 'ica_directory',
                    r['description'], r['framework_area'],
                    r['model_type'],
                    r['website'], r['email'], r['phone'], r['tags'],
                    'ica_directory', r['source_id'], 3,
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
        f.write(f'\n# ingest_ica_directory run - {today}\n\n')
        for line in lines:
            f.write(line + '\n')


def main():
    ap = argparse.ArgumentParser(description='International Cooperative Alliance ingest')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--refresh', action='store_true')
    args = ap.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Ingesting ICA directory")
    csv_path = fetch_csv(refresh=args.refresh)

    rows = []
    skipped = 0
    with open(csv_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = to_row(raw)
            if row:
                rows.append(row)
            else:
                skipped += 1
    print(f'  Parsed {len(rows)} rows (skipped {skipped})')

    db = sqlite3.connect(DB_PATH)
    run_migration(db)
    inserted, updated = upsert(db, rows, dry_run=args.dry_run)
    db.close()

    mode = '[DRY RUN] Would insert' if args.dry_run else 'Inserted'
    summary = [
        f"Mode: {'dry-run' if args.dry_run else 'real'}",
        f"Source: {ICA_CSV_URL}",
        f"Rows parsed: {len(rows)}",
        f"Skipped (no name): {skipped}",
        f"{mode}: {inserted}",
        f"Updated: {updated}",
    ]
    print('\n' + '\n'.join(summary))
    write_log(summary)
    print(f'\nLog appended: {LOG_PATH}')


if __name__ == '__main__':
    main()
