"""
Bulgaria nonprofit / NPO register ingest.

The Bulgarian Registry Agency (Агенция по вписванията) runs the unified
portal at portal.registryagency.bg. The Register of Non-profit Legal
Entities (Регистър на юридическите лица с нестопанска цел) is integrated
with the Commercial Register inside that portal. Bulk export is not public,
the search interface is JavaScript-rendered, and the public API surfaces
behind the ЕПЗЕУ single-sign-on portal. We tried the public root and got
back a Bulgarian-only login frame; an unauthenticated bulk pull is not on
the table.

So Wave A's Bulgaria opener uses Wikidata as the realistic source. Wikidata
covers Bulgarian organizations whose nonprofit status is encoded as
"instance of nonprofit organization (Q163740)" or "instance of association
(Q48204)" or "instance of foundation (Q157031)" with country (P17) set to
Bulgaria (Q219). Around 600 such rows exist as of April 2026 (we counted
during dev). That is small but it is real, every row is verifiable against
its Wikidata QID, and it gets us a non-zero Bulgarian formal-sector
footprint to anchor Wave B Bulgaria work against.

Source order:
  1. Wikidata SPARQL for Bulgarian NPOs / associations / foundations.
     Recorded with source='wikidata_bg_npo' so the provenance is obvious.
  2. (Documented but not implemented) The Registry Agency portal at
     portal.registryagency.bg. Fetched to cache as a smoke test only;
     parser is a TODO for Wave B when we have a SSO solution.

Re-runs are idempotent on (source='wikidata_bg_npo', source_id=<QID>).
Records the Wikidata item URL as the evidence URL so a reviewer can verify
each row.

Usage:
    python ingest_bulgaria_npo.py
    python ingest_bulgaria_npo.py --dry-run
    python ingest_bulgaria_npo.py --refresh
    python ingest_bulgaria_npo.py --limit 100
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from _common import DB_PATH, DATA_DIR, ensure_column

CACHE_DIR = os.path.join(DATA_DIR, 'sources', 'bulgaria-npo-cache')
LOG_PATH = os.path.join(DATA_DIR, 'ingest-bulgaria-npo-run.log')

USER_AGENT = (
    'Mozilla/5.0 (compatible; Commonweave/1.0; '
    '+https://commonweave.earth; directory@commonweave.earth)'
)
SLEEP_BETWEEN = 2

WIKIDATA_ENDPOINT = 'https://query.wikidata.org/sparql'
PRIMARY_PORTAL = 'https://portal.registryagency.bg/'

# Wikidata classes worth pulling for "Bulgarian nonprofit-like entity":
#   Q163740 = nonprofit organization
#   Q48204  = voluntary association
#   Q157031 = foundation
#   Q43229  = organization (catch-all, but only used with NPO subclass via P279*)
#   Q294163 = chitalishte (a Bulgaria-specific community-cultural-center form)
WIKIDATA_CLASSES = [
    ('Q163740',  'npo',         'nonprofit'),
    ('Q48204',   'association', 'nonprofit'),
    ('Q157031',  'foundation',  'foundation'),
    ('Q294163',  'chitalishte', 'nonprofit'),
]

# Single SPARQL template. Pulls all instances of a given class (and any
# subclass via P279*) whose country (P17) is Bulgaria (Q219). We keep the
# label service language list permissive because Bulgarian Cyrillic is the
# canonical name and English is rarely populated.
SPARQL = """
SELECT DISTINCT ?org ?orgLabelBg ?orgLabelEn ?desc ?website ?inceptionYear ?cityLabel WHERE {{
  ?org wdt:P31/wdt:P279* wd:{class_qid} .
  ?org wdt:P17 wd:Q219 .
  OPTIONAL {{ ?org rdfs:label ?orgLabelBg . FILTER(LANG(?orgLabelBg) = "bg") }}
  OPTIONAL {{ ?org rdfs:label ?orgLabelEn . FILTER(LANG(?orgLabelEn) = "en") }}
  OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
  OPTIONAL {{ ?org wdt:P856 ?website }}
  OPTIONAL {{ ?org wdt:P571 ?inception }}
  BIND(YEAR(?inception) AS ?inceptionYear)
  OPTIONAL {{ ?org wdt:P159 ?city . ?city rdfs:label ?cityLabel . FILTER(LANG(?cityLabel) = "en") }}
}} LIMIT {limit}
"""


def cache_path(key):
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = hashlib.sha1(key.encode('utf-8')).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f'{safe}.txt')


def read_cache(key):
    p = cache_path(key)
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def write_cache(key, content):
    with open(cache_path(key), 'w', encoding='utf-8') as f:
        f.write(content)


def http_get(url, accept='application/json', timeout=90):
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': accept,
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', errors='replace')


def try_primary_portal(refresh):
    """Smoke-test that the Bulgarian Registry Agency portal still returns a
    response. Cache the body so a future Wave-B operator with a SSO token
    can replay it. We do NOT parse anything here; this is purely a record
    that we kept trying."""
    key = 'primary:' + PRIMARY_PORTAL
    if not refresh:
        cached = read_cache(key)
        if cached:
            return None if cached.startswith('FETCH_FAILED:') else 'cached'
    try:
        body = http_get(PRIMARY_PORTAL, accept='text/html', timeout=20)
        write_cache(key, body)
        time.sleep(SLEEP_BETWEEN)
        return 'fetched'
    except Exception as e:
        msg = f'FETCH_FAILED: {e}'
        write_cache(key, msg)
        print(f'  Portal fetch failed: {msg}')
        return None


def sparql_query(sparql, refresh=False, cache_key=None, timeout=120):
    """Run a SPARQL query, with cache. Returns parsed bindings or []."""
    if cache_key and not refresh:
        cached = read_cache(cache_key)
        if cached:
            try:
                return json.loads(cached).get('results', {}).get('bindings', [])
            except Exception:
                pass
    url = WIKIDATA_ENDPOINT + '?' + urllib.parse.urlencode({
        'query': sparql, 'format': 'json',
    })
    try:
        body = http_get(url, accept='application/sparql-results+json', timeout=timeout)
        if cache_key:
            write_cache(cache_key, body)
        data = json.loads(body)
        return data.get('results', {}).get('bindings', [])
    except urllib.error.HTTPError as e:
        print(f'  SPARQL HTTP {e.code}: {e.reason}')
        return []
    except Exception as e:
        print(f'  SPARQL error: {e}')
        return []


def bindings_to_orgs(bindings, subtype, model_type):
    """Convert SPARQL bindings into row dicts. Bulgarian Cyrillic is the
    primary name; we keep the English label only when the Bulgarian one is
    missing, so the directory shows what locals would call the org."""
    orgs = []
    for b in bindings:
        qid_url = b.get('org', {}).get('value', '')
        qid = qid_url.split('/')[-1] if qid_url else ''
        bg_label = (b.get('orgLabelBg', {}) or {}).get('value', '')
        en_label = (b.get('orgLabelEn', {}) or {}).get('value', '')
        # Pick a name. Prefer Bulgarian; fall back to English if Bulgarian
        # is empty. Skip the row if neither is set or the only label is the
        # raw QID (Wikidata returns that when no rdfs:label exists).
        primary = bg_label or en_label
        if not primary or primary.startswith('Q'):
            continue
        # If both are present and they differ, append the English form in
        # parens so the search index can match either.
        if bg_label and en_label and bg_label != en_label:
            name = f'{bg_label} ({en_label})'
        else:
            name = primary
        orgs.append({
            'source_id': qid,
            'evidence_url': qid_url,
            'name': name,
            'description': (b.get('desc', {}) or {}).get('value', ''),
            'website': (b.get('website', {}) or {}).get('value', ''),
            'city': (b.get('cityLabel', {}) or {}).get('value', ''),
            'last_filing_year': (b.get('inceptionYear', {}) or {}).get('value', ''),
            'subtype': subtype,
            'model_type': model_type,
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


def upsert(db, orgs, dry_run=False):
    c = db.cursor()
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    updated = 0

    for org in orgs:
        name = (org.get('name') or '').strip()
        sid = (org.get('source_id') or '').strip()
        if not name or not sid:
            continue
        if dry_run:
            inserted += 1
            continue
        # framework_area is left blank here. phase2_filter and the
        # legal-form bumps will assign one based on description text and
        # registration_type.
        c.execute(
            "SELECT id FROM organizations WHERE source=? AND source_id=?",
            ('wikidata_bg_npo', sid),
        )
        existing = c.fetchone()
        if existing:
            c.execute(
                """UPDATE organizations
                   SET name=?,
                       country_code='BG', country_name='Bulgaria',
                       city=COALESCE(NULLIF(city,''), ?),
                       description=COALESCE(NULLIF(description,''), ?),
                       website=COALESCE(NULLIF(website,''), ?),
                       registration_type=?,
                       model_type=?,
                       alignment_score=MAX(COALESCE(alignment_score,0), ?),
                       evidence_url=COALESCE(NULLIF(evidence_url,''), ?),
                       evidence_fetched_at=?,
                       legibility='formal'
                   WHERE id=?""",
                (
                    name,
                    org.get('city', ''),
                    org.get('description', ''),
                    org.get('website', ''),
                    'BG_NPO_REGISTER',
                    org.get('model_type', 'nonprofit'),
                    2,
                    org.get('evidence_url', ''),
                    now,
                    existing[0],
                ),
            )
            updated += 1
        else:
            c.execute(
                """INSERT OR IGNORE INTO organizations
                   (name, country_code, country_name, city,
                    description, website,
                    source, source_id,
                    registration_type, model_type,
                    alignment_score, status, date_added,
                    last_filing_year,
                    legibility, evidence_url, evidence_fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?,?)""",
                (
                    name, 'BG', 'Bulgaria', org.get('city', ''),
                    org.get('description', ''), org.get('website', ''),
                    'wikidata_bg_npo', sid,
                    'BG_NPO_REGISTER', org.get('model_type', 'nonprofit'),
                    2, now,
                    org.get('last_filing_year', ''),
                    'formal', org.get('evidence_url', ''), now,
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
        f.write(f'\n# ingest_bulgaria_npo run - {today}\n\n')
        for line in lines:
            f.write(line + '\n')


def main():
    ap = argparse.ArgumentParser(description='Bulgaria NPO ingest (Wikidata fallback)')
    ap.add_argument('--dry-run', action='store_true', help='Query + count, no writes')
    ap.add_argument('--refresh', action='store_true', help='Ignore cache, re-fetch')
    ap.add_argument('--limit', type=int, default=2000, help='Per-class SPARQL limit')
    args = ap.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Ingesting Bulgaria NPOs (Wikidata fallback)")

    portal_status = try_primary_portal(args.refresh)
    print(f'  Primary portal smoke-test: {portal_status or "unreachable"}')

    db = sqlite3.connect(DB_PATH)
    run_migration(db)

    totals = {'queried': 0, 'inserted': 0, 'updated': 0}
    per_subtype = {}

    for class_qid, subtype, model_type in WIKIDATA_CLASSES:
        sparql = SPARQL.format(class_qid=class_qid, limit=args.limit)
        cache_key = f'sparql:bg:{class_qid}:{args.limit}'
        print(f'  SPARQL class={class_qid} ({subtype})')
        bindings = sparql_query(sparql, refresh=args.refresh, cache_key=cache_key)
        print(f'    -> {len(bindings)} bindings')
        orgs = bindings_to_orgs(bindings, subtype, model_type)
        totals['queried'] += len(orgs)

        inserted, updated = upsert(db, orgs, dry_run=args.dry_run)
        totals['inserted'] += inserted
        totals['updated'] += updated

        per_subtype.setdefault(subtype, {'queried': 0, 'inserted': 0, 'updated': 0})
        per_subtype[subtype]['queried'] += len(orgs)
        per_subtype[subtype]['inserted'] += inserted
        per_subtype[subtype]['updated'] += updated

        time.sleep(SLEEP_BETWEEN)

    db.close()

    mode = '[DRY RUN] Would insert' if args.dry_run else 'Inserted'
    summary = [
        f"Mode: {'dry-run' if args.dry_run else 'real'}",
        f"Per-class SPARQL limit: {args.limit}",
        f"Primary portal: {PRIMARY_PORTAL} ({'reachable' if portal_status else 'unreachable'})",
        '',
        f"Queried total:  {totals['queried']}",
        f"{mode}:          {totals['inserted']}",
        f"Updated:        {totals['updated']}",
        '',
        'Per subtype:',
    ]
    for st, d in sorted(per_subtype.items()):
        summary.append(
            f"  {st:14s} queried={d['queried']:4d} "
            f"inserted={d['inserted']:4d} updated={d['updated']:4d}"
        )

    print('\n' + '\n'.join(summary))
    write_log(summary)
    print(f'\nLog appended: {LOG_PATH}')


if __name__ == '__main__':
    main()
