"""
New Economy Coalition members ingest.

Source: https://neweconomy.net/member-directory. The page hard-codes a
JavaScript variable, `nec_org_parameters`, that lists every member's name
and profile URL. We parse that variable directly off the HTML rather than
walking the visible-list pagination, which is the same data shaped for
the in-page filter widget.

For each member we then GET its profile page (one HTTP call per org with
the polite 1.5s sleep) and read the og:description meta tag for a short
description blurb. The profile pages do not publish the member's website
or address, just the description and a logo. That is enough: the row's
real evidence is membership of the New Economy Coalition.

Defaults:
  - source           = 'nec_members'
  - source_id        = profile slug (the last path segment of the URL),
                       which is stable.
  - country_code     = 'CA' when the name shouts Canada or the description
                       references a Canadian province, else 'US'. The brief
                       calls this dataset "US/Canada".
  - legibility       = 'formal' per the brief: NEC members are deliberately
                       organised orgs, mostly cooperatives, foundations,
                       community development corporations.
  - framework_area   = derived from name + description keywords. Most rows
                       map to 'cooperatives', 'housing_land', 'food', or
                       'democracy'.
  - model_type       = 'cooperative' when the name says so, otherwise
                       'nonprofit'.
  - alignment_score  = 3 (NEC membership is a stronger alignment signal
                       than mere registration).

Idempotent on (source='nec_members', source_id=slug).

Usage:
    python ingest_nec_members.py             # real run, fetches each profile
    python ingest_nec_members.py --dry-run   # parse + count, no writes
    python ingest_nec_members.py --refresh   # ignore cache, re-download
    python ingest_nec_members.py --no-detail # skip per-org profile fetch,
                                            # use names + URLs only (fast)
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

CACHE_DIR = os.path.join(DATA_DIR, 'sources', 'nec-cache')
LOG_PATH = os.path.join(DATA_DIR, 'ingest-nec-run.log')

USER_AGENT = (
    'Mozilla/5.0 (compatible; Commonweave/1.0 directory bot; '
    '+https://commonweave.earth; hello@simonlpaige.com)'
)
SLEEP_BETWEEN = 1.5

DIRECTORY_URL = 'https://neweconomy.net/member-directory/'

NEC_PARAMS_RE = re.compile(r'var nec_org_parameters = (\{.+?\});', re.DOTALL)
OG_DESC_RE = re.compile(
    r'<meta property="og:description" content="([^"]+)"', re.IGNORECASE
)
OG_TITLE_RE = re.compile(
    r'<meta property="og:title" content="([^"]+)"', re.IGNORECASE
)

CANADA_HINTS = re.compile(
    r'\bcanad|\b(toronto|montreal|vancouver|ottawa|calgary|winnipeg|halifax|'
    r'quebec|ontario|alberta|saskatchewan|manitoba|british columbia|nova scotia|'
    r'new brunswick|newfoundland)\b',
    re.IGNORECASE,
)

FRAMEWORK_RULES = [
    (re.compile(r'cooperat|co-op|coop\b', re.I), 'cooperatives'),
    (re.compile(r'land trust|land cooperative|community land|housing|tenant', re.I), 'housing_land'),
    (re.compile(r'food|farm|grocery|agricultur|csa\b', re.I), 'food'),
    (re.compile(r'health|wellness|clinic|medic', re.I), 'healthcare'),
    (re.compile(r'energy|solar|wind|renewable|climate', re.I), 'energy_digital'),
    (re.compile(r'school|education|training|teach|learn|youth', re.I), 'education'),
    (re.compile(r'art|culture|storytelling|media|film', re.I), 'recreation_arts'),
    (re.compile(r'environment|ecolog|river|forest|conservation', re.I), 'ecology'),
    (re.compile(r'organiz|organis|advocac|justice|democracy|community', re.I), 'democracy'),
]


def cache_path(key):
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = hashlib.sha1(key.encode('utf-8')).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f'{safe}.html')


def http_get(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml',
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', errors='replace')


def fetch_html(url, refresh=False):
    p = cache_path(url)
    if not refresh and os.path.exists(p) and os.path.getsize(p) > 256:
        with open(p, 'r', encoding='utf-8') as f:
            return f.read()
    html = http_get(url)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(html)
    time.sleep(SLEEP_BETWEEN)
    return html


def fetch_directory(refresh=False):
    """Pull the directory HTML and extract the nec_org_parameters JSON
    blob. Returns a dict {name: profile_url}."""
    html = fetch_html(DIRECTORY_URL, refresh=refresh)
    m = NEC_PARAMS_RE.search(html)
    if not m:
        return {}
    blob = json.loads(m.group(1))
    return blob.get('org_key') or {}


def slug_from_url(url):
    return (url or '').rstrip('/').rsplit('/', 1)[-1]


def derive_framework(text):
    for pat, area in FRAMEWORK_RULES:
        if pat.search(text):
            return area
    return ''


def derive_country(name, description):
    blob = f'{name} {description}'
    if CANADA_HINTS.search(blob):
        return ('CA', 'Canada')
    return ('US', 'United States')


def derive_model_type(name):
    low = name.lower()
    if 'cooperat' in low or 'co-op' in low or 'coop' in low or 'credit union' in low:
        return 'cooperative'
    if 'foundation' in low or 'trust' in low:
        return 'foundation'
    if 'mutual' in low:
        return 'mutual_aid'
    return 'nonprofit'


def parse_member(name, profile_url, refresh, fetch_detail):
    description = ''
    if fetch_detail:
        try:
            html = fetch_html(profile_url, refresh=refresh)
        except urllib.error.HTTPError as e:
            print(f'  {name!r} profile fetch -> HTTP {e.code}; using name only')
            html = ''
        except Exception as e:
            print(f'  {name!r} profile fetch -> {e}; using name only')
            html = ''
        if html:
            md = OG_DESC_RE.search(html)
            if md:
                description = md.group(1).strip()
                description = (description.replace('&#038;', '&')
                                          .replace('&amp;', '&')
                                          .replace('&#8217;', "'")
                                          .replace('&quot;', '"'))
                if len(description) > 1500:
                    description = description[:1497] + '...'
    iso, cname = derive_country(name, description)
    framework = derive_framework(name + ' ' + description) or 'cooperatives'
    return {
        'name': name,
        'country_code': iso,
        'country_name': cname,
        'state_province': '',
        'city': '',
        'description': description,
        'framework_area': framework,
        'model_type': derive_model_type(name),
        'website': profile_url,
        'source_id': slug_from_url(profile_url) or hashlib.sha1(name.encode('utf-8')).hexdigest()[:12],
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
            ('nec_members', r['source_id']),
        )
        existing = c.fetchone()
        if existing:
            c.execute(
                """UPDATE organizations
                   SET name=?,
                       country_code=COALESCE(NULLIF(country_code,''), ?),
                       country_name=COALESCE(NULLIF(country_name,''), ?),
                       description=COALESCE(NULLIF(description,''), ?),
                       framework_area=COALESCE(NULLIF(framework_area,''), ?),
                       model_type=?,
                       website=COALESCE(NULLIF(website,''), ?),
                       alignment_score=MAX(COALESCE(alignment_score,0), ?),
                       evidence_url=COALESCE(NULLIF(evidence_url,''), ?),
                       evidence_fetched_at=?,
                       legibility='formal'
                   WHERE id=?""",
                (
                    r['name'], r['country_code'], r['country_name'],
                    r['description'], r['framework_area'], r['model_type'],
                    r['website'], 3, r['evidence_url'], now, existing[0],
                ),
            )
            updated += 1
        else:
            c.execute(
                """INSERT OR IGNORE INTO organizations
                   (name, country_code, country_name,
                    description, framework_area, model_type, website,
                    source, source_id, alignment_score,
                    status, date_added,
                    legibility, evidence_url, evidence_fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?)""",
                (
                    r['name'], r['country_code'], r['country_name'],
                    r['description'], r['framework_area'],
                    r['model_type'], r['website'],
                    'nec_members', r['source_id'], 3,
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
        f.write(f'\n# ingest_nec_members run - {today}\n\n')
        for line in lines:
            f.write(line + '\n')


def main():
    ap = argparse.ArgumentParser(description='New Economy Coalition members ingest')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--refresh', action='store_true')
    ap.add_argument('--no-detail', action='store_true', help='Skip per-org profile fetch')
    args = ap.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Ingesting NEC member directory")

    org_key = fetch_directory(refresh=args.refresh)
    print(f'  Members listed: {len(org_key)}')
    if not org_key:
        print('  FATAL: nec_org_parameters not found on member directory page.')
        sys.exit(1)

    rows = []
    for i, (name, url) in enumerate(org_key.items(), start=1):
        if i == 1 or i % 25 == 0:
            print(f'  [{i}/{len(org_key)}] {name}')
        row = parse_member(name, url, refresh=args.refresh, fetch_detail=not args.no_detail)
        rows.append(row)

    db = sqlite3.connect(DB_PATH)
    run_migration(db)
    inserted, updated = upsert(db, rows, dry_run=args.dry_run)
    db.close()

    mode = '[DRY RUN] Would insert' if args.dry_run else 'Inserted'
    summary = [
        f"Mode: {'dry-run' if args.dry_run else 'real'}",
        f"Source: {DIRECTORY_URL}",
        f"Members listed: {len(org_key)}",
        f"Detail fetched per-org: {not args.no_detail}",
        f"Rows parsed: {len(rows)}",
        f"{mode}: {inserted}",
        f"Updated: {updated}",
    ]
    print('\n' + '\n'.join(summary))
    write_log(summary)
    print(f'\nLog appended: {LOG_PATH}')


if __name__ == '__main__':
    main()
