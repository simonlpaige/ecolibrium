"""
Schumacher Center Community Land Trust World Map (CLT World Map) ingest.

Source: https://centerforneweconomics.org/community-land-trust/. The page
the brief points at (.../cltwm/) is a 404 today (2026-04-26); the directory
itself moved to /community-land-trust/ a while back.

The directory is rendered by Toolset Views (a WordPress plugin) into a
plain HTML table. Each row carries name, town, state/province, country,
and website. Pagination uses ?wpv_view_count=21099&wpv_paged=N up to 44
pages of about ten rows each (so ~430 to 440 CLTs).

Per-row detail pages exist at /clt/<slug>/ but the listing already gives
us enough fields. We skip the detail fetch by default and add ~440 rows
in about a minute.

Mapping:
  - source           = 'clt_world_map'
  - source_id        = the slug from the row's profile link
                       (e.g. 'abbotts-ann-community-land-trust')
  - country_code     = mapped from the country column value. Schumacher
                       enters countries as 'England', 'United States',
                       'Canada', 'Belgium', etc.; we normalise to ISO 3166.
                       'England', 'Scotland', 'Wales', 'Northern Ireland'
                       all map to GB.
  - legibility       = 'formal'. Every CLT in this database is a
                       registered legal entity - it is the whole point
                       of a CLT.
  - framework_area   = 'housing_land' on every row.
  - model_type       = 'community_org' by default, 'cooperative' if the
                       name says coop / cohousing.

Many of these CLTs already exist in the directory from
ingest_grounded_solutions.py (US) or from Wikidata. Idempotent upsert by
(source='clt_world_map', source_id=slug); name-collision dedup happens
later in phase2_filter / dedup pass, not here.

Usage:
    python ingest_clt_world_map.py             # real run
    python ingest_clt_world_map.py --dry-run   # parse + count, no writes
    python ingest_clt_world_map.py --refresh   # ignore cache, re-fetch
"""
import argparse
import hashlib
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

CACHE_DIR = os.path.join(DATA_DIR, 'sources', 'clt-cache')
LOG_PATH = os.path.join(DATA_DIR, 'ingest-clt-run.log')

USER_AGENT = (
    'Mozilla/5.0 (compatible; Commonweave/1.0 directory bot; '
    '+https://commonweave.earth; hello@simonlpaige.com)'
)
SLEEP_BETWEEN = 1.5

LIST_URL_TMPL = (
    'https://centerforneweconomics.org/community-land-trust/'
    '?wpv_view_count=21099&wpv_paged={page}'
)
TOTAL_PAGES = 44  # the page-1 HTML names this number explicitly

ROW_RE = re.compile(
    r'<tr>\s*'
    r'<td[^>]*>\s*<a href="https://centerforneweconomics\.org/clt/([^"]+?)/?"[^>]*>([^<]+)</a>\s*</td>\s*'
    r'<td[^>]*>\s*([^<]*)\s*</td>\s*'
    r'<td[^>]*>\s*([^<]*)\s*</td>\s*'
    r'<td[^>]*>\s*([^<]*)\s*</td>\s*'
    r'<td[^>]*>(?:\s*<a href="(https?://[^"]+)"[^>]*>[^<]*</a>)?\s*</td>\s*'
    r'</tr>',
    re.DOTALL,
)

# Schumacher's country column uses English-language names; UK constituent
# countries get folded back to GB.
COUNTRY_TO_ISO = {
    'united states': 'US', 'usa': 'US', 'us': 'US',
    'canada': 'CA',
    'united kingdom': 'GB', 'uk': 'GB', 'great britain': 'GB',
    'england': 'GB', 'scotland': 'GB', 'wales': 'GB', 'northern ireland': 'GB',
    'ireland': 'IE', 'republic of ireland': 'IE',
    'belgium': 'BE', 'netherlands': 'NL', 'germany': 'DE', 'france': 'FR',
    'spain': 'ES', 'italy': 'IT', 'portugal': 'PT',
    'australia': 'AU', 'new zealand': 'NZ',
    'kenya': 'KE', 'south africa': 'ZA', 'tanzania': 'TZ', 'uganda': 'UG',
    'india': 'IN', 'japan': 'JP', 'taiwan': 'TW',
    'mexico': 'MX', 'brazil': 'BR', 'argentina': 'AR', 'chile': 'CL',
    'puerto rico': 'PR', 'jamaica': 'JM',
    'sweden': 'SE', 'denmark': 'DK', 'norway': 'NO', 'finland': 'FI',
    'austria': 'AT', 'switzerland': 'CH',
    'czech republic': 'CZ', 'czechia': 'CZ', 'poland': 'PL',
    'kosovo': 'XK', 'serbia': 'RS', 'croatia': 'HR',
    'lebanon': 'LB', 'palestine': 'PS', 'israel': 'IL',
    'colombia': 'CO', 'ecuador': 'EC', 'peru': 'PE',
}


def cache_path(page):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f'page-{page:03d}.html')


def http_get(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml',
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', errors='replace')


def fetch_page(page, refresh=False):
    p = cache_path(page)
    if not refresh and os.path.exists(p) and os.path.getsize(p) > 1024:
        with open(p, 'r', encoding='utf-8') as f:
            return f.read()
    url = LIST_URL_TMPL.format(page=page)
    html = http_get(url)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(html)
    time.sleep(SLEEP_BETWEEN)
    return html


def parse_rows(html):
    """Pull (slug, name, town, state, country, website) from the listing
    table. Cleans up HTML entities and strips whitespace."""
    rows = []
    for m in ROW_RE.finditer(html):
        slug, name, town, state, country, website = m.groups()
        name = (name or '').strip().replace('&amp;', '&').replace('&#038;', '&')
        if not name:
            continue
        rows.append({
            'slug': slug.strip(),
            'name': name,
            'town': (town or '').strip(),
            'state': (state or '').strip(),
            'country_raw': (country or '').strip(),
            'website': (website or '').strip(),
        })
    return rows


def normalize_country(raw):
    if not raw:
        return ('', '')
    iso = COUNTRY_TO_ISO.get(raw.lower())
    return (iso or '', raw)


def derive_model_type(name):
    low = name.lower()
    if 'cooperative' in low or 'co-op' in low or 'cohous' in low:
        return 'cooperative'
    return 'community_org'


def to_row(r):
    iso, cname = normalize_country(r['country_raw'])
    profile_url = f'https://centerforneweconomics.org/clt/{r["slug"]}/'
    return {
        'name': r['name'],
        'country_code': iso,
        'country_name': cname,
        'state_province': r['state'],
        'city': r['town'],
        'description': f'Community Land Trust listed in the Schumacher Center CLT World Map. Country: {cname or "unspecified"}',
        'framework_area': 'housing_land',
        'model_type': derive_model_type(r['name']),
        'website': r['website'] or profile_url,
        'tags': 'community_land_trust',
        'source_id': r['slug'],
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
        if dry_run:
            inserted += 1
            continue
        c.execute(
            "SELECT id FROM organizations WHERE source=? AND source_id=?",
            ('clt_world_map', r['source_id']),
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
                       legibility='formal'
                   WHERE id=?""",
                (
                    r['name'], r['country_code'], r['country_name'],
                    r['state_province'], r['city'],
                    r['description'], r['framework_area'],
                    r['model_type'], r['website'], r['tags'],
                    3, r['evidence_url'], now, existing[0],
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
                    'clt_world_map', r['source_id'], 3,
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
        f.write(f'\n# ingest_clt_world_map run - {today}\n\n')
        for line in lines:
            f.write(line + '\n')


def main():
    ap = argparse.ArgumentParser(description='Schumacher CLT World Map ingest')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--refresh', action='store_true')
    args = ap.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Ingesting Schumacher CLT World Map")

    raw_rows = []
    for page in range(1, TOTAL_PAGES + 1):
        try:
            html = fetch_page(page, refresh=args.refresh)
        except Exception as e:
            print(f'  page {page} failed: {e}')
            continue
        page_rows = parse_rows(html)
        raw_rows.extend(page_rows)
        if page == 1 or page % 10 == 0 or page == TOTAL_PAGES:
            print(f'  page {page}/{TOTAL_PAGES}: {len(page_rows)} rows; running total {len(raw_rows)}')

    rows = [to_row(r) for r in raw_rows]
    print(f'  Total CLT rows parsed: {len(rows)}')

    db = sqlite3.connect(DB_PATH)
    run_migration(db)
    inserted, updated = upsert(db, rows, dry_run=args.dry_run)
    db.close()

    mode = '[DRY RUN] Would insert' if args.dry_run else 'Inserted'
    summary = [
        f"Mode: {'dry-run' if args.dry_run else 'real'}",
        f"Source: https://centerforneweconomics.org/community-land-trust/",
        f"Pages walked: {TOTAL_PAGES}",
        f"Rows parsed: {len(rows)}",
        f"{mode}: {inserted}",
        f"Updated: {updated}",
    ]
    print('\n' + '\n'.join(summary))
    write_log(summary)
    print(f'\nLog appended: {LOG_PATH}')


if __name__ == '__main__':
    main()
