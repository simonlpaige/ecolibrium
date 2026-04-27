"""
Australia ACNC Charity Register ingest.

The ACNC (Australian Charities and Not-for-profits Commission) publishes the
full register of registered charities as a weekly CSV on data.gov.au. That
file is the cleanest national charity dataset we know about: about 60-70k
rows, every one carrying an ABN, charitable purpose flags, beneficiary
flags, address fields, and a website where the charity supplies one. We use
it as Wave A's first opener because pulling Australian charities by legal
form, rather than by English-keyword scoring, is exactly the methodological
move the new wave doc points at.

Source order:
  1. Bulk CSV from data.gov.au (resource b050b242-... -> 8fb32972-...).
     Cached under data/sources/acnc-cache/. Refreshed weekly when --refresh.
  2. (Documented but not implemented) ACNC public API at
     acnc-public-api.azure-api.net. Not wired up because the bulk CSV
     covers the same fields and is one HTTP call rather than thousands.

Filters applied at ingest time:
  - The bulk CSV is the live register, so revoked / deregistered charities
    do not appear at all. No status filter needed.
  - Drop rows whose ONLY charitable purpose is "Advancing Religion." Rows
    that hit Religion plus any other purpose (education, health, social
    welfare, etc.) are kept, as are Public Benevolent Institutions and
    Health Promotion Charities regardless of religion flag. This matches
    the brief's "drop pure religious-only" rule.

Mapping:
  - source        = 'acnc_charity_register'
  - source_id     = ABN (always set, eleven digits)
  - registration_id = ABN
  - registration_type = 'ACNC_REGISTRATION'
  - country_code  = 'AU'
  - legibility    = 'formal'
  - model_type    = 'nonprofit' by default; bumped to 'cooperative' or
                    'foundation' if name hints at it
  - framework_area = derived from charitable-purpose flags (advancing
                    health -> healthcare, advancing education -> education,
                    advancing social or public welfare -> housing_land or
                    democracy depending on PBI flag, etc.)

Re-runs are idempotent: keyed on (source='acnc_charity_register', source_id=ABN).

Usage:
    python ingest_acnc.py                  # real run
    python ingest_acnc.py --dry-run        # parse + count, no writes
    python ingest_acnc.py --refresh        # ignore cache, re-download
    python ingest_acnc.py --limit 1000     # cap rows for smoke test
"""
import argparse
import csv
import io
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from _common import DB_PATH, DATA_DIR, ensure_column

CACHE_DIR = os.path.join(DATA_DIR, 'sources', 'acnc-cache')
LOG_PATH = os.path.join(DATA_DIR, 'ingest-acnc-run.log')

USER_AGENT = (
    'Mozilla/5.0 (compatible; Commonweave/1.0; '
    '+https://commonweave.earth; directory@commonweave.earth)'
)
SLEEP_BETWEEN = 1

ACNC_CSV_URL = (
    'https://data.gov.au/data/dataset/b050b242-4487-4306-abf5-07ca073e5594/'
    'resource/8fb32972-24e9-4c95-885e-7140be51be8a/download/datadotgov_main.csv'
)

# Charitable-purpose columns from the ACNC dataset header. The Y/N flags
# tell us why a charity is registered. We keep this list explicit so the
# mapping to framework_area below is auditable.
PURPOSE_COLUMNS = [
    'Preventing_or_relieving_suffering_of_animals',
    'Advancing_Culture',
    'Advancing_Education',
    'Advancing_Health',
    'Promote_or_oppose_a_change_to_law__government_poll_or_prac',
    'Advancing_natual_environment',  # ACNC's own typo, kept verbatim
    'Promoting_or_protecting_human_rights',
    'Purposes_beneficial_to_ther_general_public_and_other_analogous',
    'Promoting_reconciliation__mutual_respect_and_tolerance',
    'Advancing_Religion',
    'Advancing_social_or_public_welfare',
    'Advancing_security_or_safety_of_Australia_or_Australian_public',
]

# Map a single charitable-purpose column name to a Commonweave framework
# area. When several apply, the first one in this priority order wins.
PURPOSE_TO_FRAMEWORK = [
    ('Advancing_Health',                                              'healthcare'),
    ('Advancing_social_or_public_welfare',                            'housing_land'),
    ('Advancing_Education',                                           'education'),
    ('Advancing_natual_environment',                                  'ecology'),
    ('Promoting_or_protecting_human_rights',                          'democracy'),
    ('Promoting_reconciliation__mutual_respect_and_tolerance',        'democracy'),
    ('Promote_or_oppose_a_change_to_law__government_poll_or_prac',    'democracy'),
    ('Advancing_Culture',                                             'recreation_arts'),
    ('Preventing_or_relieving_suffering_of_animals',                  'ecology'),
    ('Purposes_beneficial_to_ther_general_public_and_other_analogous','democracy'),
    ('Advancing_security_or_safety_of_Australia_or_Australian_public','conflict'),
]


def http_get_streaming(url, dest_path):
    """Download `url` to `dest_path`. Streams the body so a 300+ MB file
    does not blow up memory."""
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'text/csv,application/octet-stream',
    })
    tmp = dest_path + '.partial'
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, 'wb') as out:
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            out.write(chunk)
    os.replace(tmp, dest_path)


def cache_csv_path():
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, 'acnc-register.csv')


def fetch_csv(refresh=False):
    """Return the local path to the ACNC CSV. Downloads if missing or
    --refresh."""
    path = cache_csv_path()
    if not refresh and os.path.exists(path) and os.path.getsize(path) > 1024:
        print(f'  Using cached ACNC CSV: {path} ({os.path.getsize(path):,} bytes)')
        return path
    print(f'  Downloading ACNC CSV from {ACNC_CSV_URL}')
    try:
        http_get_streaming(ACNC_CSV_URL, path)
        time.sleep(SLEEP_BETWEEN)
    except urllib.error.HTTPError as e:
        print(f'  Download failed: HTTP {e.code} {e.reason}')
        return None
    except Exception as e:
        print(f'  Download failed: {e}')
        return None
    print(f'  Downloaded {os.path.getsize(path):,} bytes')
    return path


def is_yes(value):
    return (value or '').strip().upper() == 'Y'


def looks_pure_religious(row):
    """True when Advancing_Religion is the only purpose flag set. PBIs and
    Health Promotion Charities are NEVER pure-religious by definition, so
    this returns False for them even if their religion flag is also Y."""
    if is_yes(row.get('PBI', '')) or is_yes(row.get('HPC', '')):
        return False
    other_purposes = [p for p in PURPOSE_COLUMNS if p != 'Advancing_Religion']
    has_religion = is_yes(row.get('Advancing_Religion', ''))
    has_other = any(is_yes(row.get(col, '')) for col in other_purposes)
    return has_religion and not has_other


def derive_framework_area(row):
    """Pick a framework area from the charitable-purpose flags."""
    if is_yes(row.get('PBI', '')):
        # Public Benevolent Institutions exist to relieve poverty / suffering.
        # Default them into housing_land (social welfare) unless health is
        # also flagged.
        if is_yes(row.get('Advancing_Health', '')):
            return 'healthcare'
        return 'housing_land'
    if is_yes(row.get('HPC', '')):
        return 'healthcare'
    for col, area in PURPOSE_TO_FRAMEWORK:
        if is_yes(row.get(col, '')):
            return area
    return ''


def derive_model_type(name):
    """Default to 'nonprofit'. Promote to cooperative or foundation when
    the legal name itself shouts the legal form."""
    low = (name or '').lower()
    if 'cooperative' in low or 'co-operative' in low or 'co-op ' in low:
        return 'cooperative'
    if 'foundation' in low or 'trust' in low:
        return 'foundation'
    if 'mutual' in low:
        return 'mutual_aid'
    return 'nonprofit'


def derive_description(row):
    """Build a short purpose-summary from the flag columns. The CSV does not
    expose each charity's free-text purpose, so we synthesize from the Y
    flags that are set. This gives the alignment scorer something to work
    with even though no English description was published."""
    parts = []
    if is_yes(row.get('PBI', '')):
        parts.append('Public Benevolent Institution')
    if is_yes(row.get('HPC', '')):
        parts.append('Health Promotion Charity')
    purpose_phrases = {
        'Advancing_Health': 'advancing health',
        'Advancing_Education': 'advancing education',
        'Advancing_social_or_public_welfare': 'advancing social or public welfare',
        'Advancing_natual_environment': 'advancing the natural environment',
        'Advancing_Culture': 'advancing culture',
        'Promoting_or_protecting_human_rights': 'protecting human rights',
        'Promoting_reconciliation__mutual_respect_and_tolerance': 'promoting reconciliation and mutual respect',
        'Promote_or_oppose_a_change_to_law__government_poll_or_prac': 'public policy advocacy',
        'Preventing_or_relieving_suffering_of_animals': 'animal welfare',
        'Purposes_beneficial_to_ther_general_public_and_other_analogous': 'other public benefit',
        'Advancing_security_or_safety_of_Australia_or_Australian_public': 'public safety',
    }
    purposes_hit = [phrase for col, phrase in purpose_phrases.items() if is_yes(row.get(col, ''))]
    if purposes_hit:
        parts.append('purposes: ' + ', '.join(purposes_hit))
    op_countries = (row.get('Operating_Countries') or '').strip()
    if op_countries and op_countries.upper() != 'AUS':
        parts.append('operates in: ' + op_countries)
    return '. '.join(parts).strip()


def parse_rows(csv_path, limit=None):
    """Yield row dicts from the ACNC CSV. We open with utf-8 and replace
    bad bytes since the file occasionally contains characters that are not
    strict UTF-8 (the leaked encoding shows up in town names like 'S\xc3O
    PAULO'-style mojibake elsewhere; ACNC has been clean in our checks)."""
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            yield row


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
    skipped_no_abn = 0
    skipped_pure_religion = 0

    for row in rows:
        abn = (row.get('ABN') or '').strip()
        name = (row.get('Charity_Legal_Name') or '').strip()
        if not abn or not name:
            skipped_no_abn += 1
            continue
        if looks_pure_religious(row):
            skipped_pure_religion += 1
            continue

        framework = derive_framework_area(row)
        model_type = derive_model_type(name)
        description = derive_description(row)
        website = (row.get('Charity_Website') or '').strip()
        city = (row.get('Town_City') or '').strip()
        state = (row.get('State') or '').strip()
        # Country in the CSV is usually "Australia"; force AU regardless to
        # match the rest of the directory's country_code convention.
        country_code = 'AU'
        country_name = 'Australia'

        # Alignment score baseline: 2 for any registered ACNC charity (all
        # are formal nonprofits with a public-benefit purpose). PBI and HPC
        # are stronger signals so they get +1.
        score = 2
        if is_yes(row.get('PBI', '')) or is_yes(row.get('HPC', '')):
            score = 3

        if dry_run:
            inserted += 1
            continue

        c.execute(
            "SELECT id FROM organizations WHERE source=? AND source_id=?",
            ('acnc_charity_register', abn),
        )
        existing = c.fetchone()

        if existing:
            c.execute(
                """UPDATE organizations
                   SET name=?,
                       country_code=?, country_name=?,
                       state_province=COALESCE(NULLIF(state_province,''), ?),
                       city=COALESCE(NULLIF(city,''), ?),
                       registration_id=?,
                       registration_type=?,
                       description=COALESCE(NULLIF(description,''), ?),
                       website=COALESCE(NULLIF(website,''), ?),
                       framework_area=COALESCE(NULLIF(framework_area,''), ?),
                       model_type=?,
                       alignment_score=MAX(COALESCE(alignment_score,0), ?),
                       evidence_url=COALESCE(NULLIF(evidence_url,''), ?),
                       evidence_fetched_at=?,
                       legibility='formal'
                   WHERE id=?""",
                (
                    name, country_code, country_name, state, city,
                    abn, 'ACNC_REGISTRATION',
                    description, website,
                    framework, model_type, score,
                    ACNC_CSV_URL, now, existing[0],
                ),
            )
            updated += 1
        else:
            c.execute(
                """INSERT OR IGNORE INTO organizations
                   (name, country_code, country_name, state_province, city,
                    registration_id, registration_type,
                    description, website,
                    source, source_id,
                    framework_area, model_type, alignment_score,
                    status, date_added,
                    legibility, evidence_url, evidence_fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?)""",
                (
                    name, country_code, country_name, state, city,
                    abn, 'ACNC_REGISTRATION',
                    description, website,
                    'acnc_charity_register', abn,
                    framework, model_type, score,
                    now,
                    'formal', ACNC_CSV_URL, now,
                ),
            )
            if c.rowcount:
                inserted += 1

    if not dry_run:
        db.commit()

    return inserted, updated, skipped_no_abn, skipped_pure_religion


def write_log(lines):
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f'\n# ingest_acnc run - {today}\n\n')
        for line in lines:
            f.write(line + '\n')


def main():
    ap = argparse.ArgumentParser(description='ACNC Charity Register ingest')
    ap.add_argument('--dry-run', action='store_true', help='Parse + count, no writes')
    ap.add_argument('--refresh', action='store_true', help='Ignore cache, re-download CSV')
    ap.add_argument('--limit', type=int, default=0, help='Cap rows parsed (0 = all)')
    args = ap.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Ingesting ACNC charity register")

    csv_path = fetch_csv(refresh=args.refresh)
    if not csv_path:
        print('  FATAL: could not obtain ACNC CSV. Stopping.')
        sys.exit(1)

    rows = list(parse_rows(csv_path, limit=args.limit or None))
    print(f'  Parsed {len(rows):,} rows from CSV')

    db = sqlite3.connect(DB_PATH)
    run_migration(db)
    inserted, updated, skipped_no_abn, skipped_relig = upsert(db, rows, dry_run=args.dry_run)
    db.close()

    mode = '[DRY RUN] Would insert' if args.dry_run else 'Inserted'
    summary = [
        f"Mode: {'dry-run' if args.dry_run else 'real'}",
        f"Source CSV: {ACNC_CSV_URL}",
        f"Rows parsed: {len(rows)}",
        f"Skipped (missing ABN/name): {skipped_no_abn}",
        f"Skipped (pure-religious): {skipped_relig}",
        f"{mode}: {inserted}",
        f"Updated: {updated}",
    ]
    print('\n' + '\n'.join(summary))
    write_log(summary)
    print(f'\nLog appended: {LOG_PATH}')


if __name__ == '__main__':
    main()
