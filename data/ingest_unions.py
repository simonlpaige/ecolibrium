"""
Wikidata SPARQL bulk ingest for labor unions (federations and national-level only).

Models on ingest_wikidata_bulk.py. Pulls three classes:

  * Q3395115  trade union federation
  * Q11038979 national trade union center
  * Q178790   trade union (filtered to orgs with country + HQ set, to
              exclude local chapters)
  * Q1141395  works council (legally-mandated worker representation bodies)

Every row inserted is tagged legibility=formal (Wikidata-notable = registered
and documented by definition) and category=labor/<subtype>, with the Wikidata
item URL as evidence_url. source='wikidata_unions'. Re-runs are idempotent
via INSERT OR IGNORE on (source, source_id).

Federations + nationals only. No locals. Locals are a v2 conversation.

Usage:
    python ingest_unions.py --dry-run    # count, no writes
    python ingest_unions.py              # real run
    python ingest_unions.py --limit 200  # per-class cap (default 500)
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
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from _common import DB_PATH, DATA_DIR, ensure_column

WIKIDATA_ENDPOINT = 'https://query.wikidata.org/sparql'
SLEEP_BETWEEN = 2
LOG_PATH = os.path.join(DATA_DIR, 'ingest-unions-run.log')

# (wikidata_class_qid, taxonomy_subtype, model_type, needs_hq_filter)
# needs_hq_filter=True requires P17 (country) and P159 (HQ) to be set, which
# is how we exclude local union chapters from the broad trade-union class.
UNION_CLASSES = [
    ('Q3395115',  'union_federation',     'labor_union',    False),
    ('Q11038979', 'union_federation',     'labor_union',    False),
    ('Q178790',   'national_union',       'labor_union',    True),
    ('Q1141395',  'works_council_system', 'works_council',  False),
]

# SPARQL templates.
# Both variants require P17 (country). The "strict" template additionally
# requires P159 (HQ) so we can exclude local union branches on the broad
# trade-union class.
SPARQL_LOOSE = """
SELECT DISTINCT ?org ?orgLabel ?desc ?website ?country ?countryLabel ?countryCode ?inceptionYear ?hqLabel WHERE {{
  ?org wdt:P31/wdt:P279* wd:{class_qid} .
  ?org wdt:P17 ?country .
  OPTIONAL {{ ?country wdt:P297 ?countryCode }}
  OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
  OPTIONAL {{ ?org wdt:P856 ?website }}
  OPTIONAL {{ ?org wdt:P571 ?inception }}
  BIND(YEAR(?inception) AS ?inceptionYear)
  OPTIONAL {{ ?org wdt:P159 ?hq }}
  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "en,es,fr,pt,de,it,nl,sv".
    ?org rdfs:label ?orgLabel .
    ?country rdfs:label ?countryLabel .
    ?hq rdfs:label ?hqLabel .
  }}
}} LIMIT {limit}
"""

SPARQL_STRICT = """
SELECT DISTINCT ?org ?orgLabel ?desc ?website ?country ?countryLabel ?countryCode ?inceptionYear ?hqLabel WHERE {{
  ?org wdt:P31/wdt:P279* wd:{class_qid} .
  ?org wdt:P17 ?country .
  ?org wdt:P159 ?hq .
  OPTIONAL {{ ?country wdt:P297 ?countryCode }}
  OPTIONAL {{ ?org schema:description ?desc . FILTER(LANG(?desc) = "en") }}
  OPTIONAL {{ ?org wdt:P856 ?website }}
  OPTIONAL {{ ?org wdt:P571 ?inception }}
  BIND(YEAR(?inception) AS ?inceptionYear)
  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "en,es,fr,pt,de,it,nl,sv".
    ?org rdfs:label ?orgLabel .
    ?country rdfs:label ?countryLabel .
    ?hq rdfs:label ?hqLabel .
  }}
}} LIMIT {limit}
"""


def sparql_query(sparql, timeout=90):
    """Run a SPARQL query and return parsed bindings, or [] on error."""
    url = WIKIDATA_ENDPOINT + '?' + urllib.parse.urlencode({
        'query': sparql,
        'format': 'json',
    })
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Commonweave/1.0 (https://commonweave.earth; directory@commonweave.earth)',
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


def bindings_to_orgs(bindings, subtype, model_type):
    """Convert SPARQL bindings to org dicts ready for insert."""
    orgs = []
    for b in bindings:
        qid_url = b.get('org', {}).get('value', '')
        qid = qid_url.split('/')[-1] if qid_url else ''
        name = b.get('orgLabel', {}).get('value', '')
        if not qid or not name or name.startswith('Q'):
            continue
        orgs.append({
            'source_id': qid,
            'evidence_url': qid_url,
            'name': name,
            'description': b.get('desc', {}).get('value', ''),
            'website': b.get('website', {}).get('value', ''),
            'country_code': (b.get('countryCode', {}).get('value', '') or '').upper(),
            'country_name': b.get('countryLabel', {}).get('value', ''),
            'city': b.get('hqLabel', {}).get('value', ''),
            'last_filing_year': b.get('inceptionYear', {}).get('value', ''),
            'registration_type': f'labor/{subtype}',
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


def upsert_orgs(db, orgs, dry_run=False):
    """Insert orgs. Returns (inserted, updated, skipped_excluded)."""
    if not orgs:
        return 0, 0, 0

    # Import classifier lazily; fall back to a permissive default if missing.
    try:
        from ingest_gov_registry import classify_org_ml
    except Exception:
        classify_org_ml = None

    c = db.cursor()
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    updated = 0
    skipped_excluded = 0

    for org in orgs:
        name = (org.get('name') or '').strip()
        qid = org.get('source_id') or ''
        if not name or not qid:
            continue

        # Run the classifier mostly to catch exclusions (e.g. names that
        # match a hard exclude keyword). Labor unions are inherently in
        # scope, so we force framework_area='cooperatives' and a minimum
        # alignment_score of 2 to survive trim_to_aligned.py.
        area = 'cooperatives'
        score = 2
        exclude = False
        if classify_org_ml:
            try:
                a, s, x = classify_org_ml(name, org.get('description', ''))
                exclude = bool(x)
                if not exclude:
                    area = a or 'cooperatives'
                    score = max(int(s or 0), 2)
            except Exception:
                pass
        if exclude:
            skipped_excluded += 1
            continue

        if dry_run:
            inserted += 1
            continue

        # Does a row already exist for this source + qid? Update if so.
        c.execute(
            "SELECT id FROM organizations WHERE source=? AND source_id=?",
            ('wikidata_unions', qid),
        )
        existing = c.fetchone()

        if existing:
            c.execute(
                """UPDATE organizations
                   SET name=?, description=COALESCE(NULLIF(description,''), ?),
                       website=COALESCE(NULLIF(website,''), ?),
                       country_code=COALESCE(NULLIF(country_code,''), ?),
                       country_name=COALESCE(NULLIF(country_name,''), ?),
                       city=COALESCE(NULLIF(city,''), ?),
                       registration_type=?,
                       model_type=?,
                       framework_area=COALESCE(NULLIF(framework_area,''), ?),
                       alignment_score=MAX(COALESCE(alignment_score,0), ?),
                       evidence_url=?,
                       evidence_fetched_at=?,
                       legibility='formal'
                   WHERE id=?""",
                (
                    name,
                    org.get('description', ''),
                    org.get('website', ''),
                    org.get('country_code', ''),
                    org.get('country_name', ''),
                    org.get('city', ''),
                    org.get('registration_type', ''),
                    org.get('model_type', 'labor_union'),
                    area,
                    score,
                    org.get('evidence_url', ''),
                    now,
                    existing[0],
                ),
            )
            updated += 1
        else:
            c.execute(
                """INSERT OR IGNORE INTO organizations
                   (name, country_code, country_name, city, description, website,
                    source, source_id, registration_type, model_type,
                    framework_area, alignment_score, status, date_added,
                    last_filing_year, legibility, evidence_url, evidence_fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?,?)""",
                (
                    name,
                    org.get('country_code', ''),
                    org.get('country_name', ''),
                    org.get('city', ''),
                    org.get('description', ''),
                    org.get('website', ''),
                    'wikidata_unions',
                    qid,
                    org.get('registration_type', ''),
                    org.get('model_type', 'labor_union'),
                    area,
                    score,
                    now,
                    org.get('last_filing_year', ''),
                    'formal',
                    org.get('evidence_url', ''),
                    now,
                ),
            )
            if c.rowcount:
                inserted += 1

    if not dry_run:
        db.commit()

    return inserted, updated, skipped_excluded


def write_log(summary_lines):
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
    header = f'# ingest_unions run - {today}\n\n'
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write('\n' + header)
        for line in summary_lines:
            f.write(line + '\n')


def main():
    ap = argparse.ArgumentParser(
        description='Ingest labor union federations and nationals from Wikidata'
    )
    ap.add_argument('--dry-run', action='store_true',
                    help='Query Wikidata and count what would be inserted, no writes')
    ap.add_argument('--limit', type=int, default=500,
                    help='Max results per SPARQL class (default 500)')
    args = ap.parse_args()

    db = sqlite3.connect(DB_PATH)
    run_migration(db)

    totals = {
        'queried': 0,
        'inserted': 0,
        'updated': 0,
        'skipped_excluded': 0,
    }
    per_subtype = {}

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Ingesting labor unions from Wikidata")
    print(f"  Target subtypes: {sorted(set(s[1] for s in UNION_CLASSES))}")
    print(f"  Per-class limit: {args.limit}")

    for class_qid, subtype, model_type, strict in UNION_CLASSES:
        tmpl = SPARQL_STRICT if strict else SPARQL_LOOSE
        sparql = tmpl.format(class_qid=class_qid, limit=args.limit)
        print(f"\n  SPARQL: class={class_qid} subtype={subtype} strict={strict}")
        bindings = sparql_query(sparql)
        print(f"    -> {len(bindings)} results")
        orgs = bindings_to_orgs(bindings, subtype, model_type)
        totals['queried'] += len(orgs)

        inserted, updated, skipped = upsert_orgs(db, orgs, dry_run=args.dry_run)
        totals['inserted'] += inserted
        totals['updated'] += updated
        totals['skipped_excluded'] += skipped

        key = subtype
        per_subtype.setdefault(key, {'queried': 0, 'inserted': 0, 'updated': 0, 'skipped_excluded': 0})
        per_subtype[key]['queried'] += len(orgs)
        per_subtype[key]['inserted'] += inserted
        per_subtype[key]['updated'] += updated
        per_subtype[key]['skipped_excluded'] += skipped

        print(f"    inserted={inserted} updated={updated} excluded={skipped}")
        time.sleep(SLEEP_BETWEEN)

    db.close()

    mode = '[DRY RUN] Would insert' if args.dry_run else 'Inserted'
    lines = [
        f"Mode: {'dry-run' if args.dry_run else 'real'}",
        f"Per-class SPARQL limit: {args.limit}",
        '',
        f"Queried total:  {totals['queried']}",
        f"{mode}: {totals['inserted']}",
        f"Updated:        {totals['updated']}",
        f"Excluded:       {totals['skipped_excluded']}",
        '',
        'Per subtype:',
    ]
    for st, d in sorted(per_subtype.items()):
        lines.append(f"  {st:25s} queried={d['queried']:4d} inserted={d['inserted']:4d} "
                     f"updated={d['updated']:4d} excluded={d['skipped_excluded']:4d}")

    print('\n' + '\n'.join(lines))
    write_log(lines)
    print(f"\nLog appended: {LOG_PATH}")


if __name__ == '__main__':
    main()
