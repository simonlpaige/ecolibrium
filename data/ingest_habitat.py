"""
Habitat for Humanity affiliate ingest.

Habitat has ~1,100 US affiliates and offices in roughly 70 countries. Getting
a clean machine-readable list turns out to be harder than it sounds because
habitat.org renders its country and state affiliate lists client-side (Drupal
views hydrated via JS), so a plain GET returns a shell with no affiliate
data. Sitemap.xml does not include country-specific pages. The zip-code
"find an affiliate" widget requires a POST with a CAPTCHA.

So this ingester does two things:

  1. Enrich the US affiliates that are already in the database via
     IRS_EO_BMF. A WHERE name LIKE '%HABITAT%' AND name LIKE '%HUMANITY%'
     query finds about 355 rows. We update those rows in place with
     registration_type='land_and_housing/sweat_equity_program',
     framework_area='housing_land', model_type='sweat_equity_program',
     legibility='formal', and add 'habitat_affiliate' to tags. No new rows
     are inserted for these - duplication is not the goal.

  2. Add a hand-seeded list of Habitat for Humanity country offices
     outside the US. These are documented on habitat.org/where-we-work and
     its regional sub-pages. The JS hydration keeps us from scraping them
     cleanly, so the list is maintained here in Python. Each office gets a
     new row with source='habitat_affiliates' and a stable source_id that
     is the ISO country code.

Legibility='formal' on every row touched. Cache goes to
data/sources/habitat-cache/ - today the only thing cached is the fetch
attempt on www.habitat.org/where-we-work, which is enough evidence for a
future operator to see that we tried.

Usage:
    python ingest_habitat.py              # real run
    python ingest_habitat.py --dry-run    # count, no writes
    python ingest_habitat.py --refresh    # ignore cache
"""
import argparse
import hashlib
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from _common import DB_PATH, DATA_DIR, ensure_column

CACHE_DIR = os.path.join(DATA_DIR, 'sources', 'habitat-cache')
LOG_PATH = os.path.join(DATA_DIR, 'ingest-land-trusts-run.log')

USER_AGENT = 'Commonweave/1.0 (https://commonweave.earth; directory@commonweave.earth)'
SLEEP_BETWEEN = 1

PRIMARY_URL = 'https://www.habitat.org/where-we-work'

# Habitat country offices outside the US. Country code is ISO 3166-1 alpha-2.
# Website is the country affiliate's site where it exists, otherwise a stable
# habitat.org sub-page. Name is the branded country name.
# Source: https://www.habitat.org/where-we-work (rendered via JS; visited
# manually on 2026-04-24) and the country-office domains listed there.
COUNTRY_OFFICES = [
    ('Habitat for Humanity Argentina',      'AR', 'Buenos Aires',  'https://www.hphargentina.org.ar/'),
    ('Habitat for Humanity Armenia',        'AM', 'Yerevan',       'https://www.habitat.am/'),
    ('Habitat for Humanity Australia',      'AU', 'Sydney',        'https://www.habitat.org.au/'),
    ('Habitat for Humanity Bangladesh',     'BD', 'Dhaka',         'https://habitatbangladesh.org/'),
    ('Habitat for Humanity Bolivia',        'BO', 'La Paz',        'https://www.hpf-bolivia.org/'),
    ('Habitat for Humanity Botswana',       'BW', 'Gaborone',      'https://www.habitatbotswana.org/'),
    ('Habitat for Humanity Brazil',         'BR', 'Sao Paulo',     'https://habitatbrasil.org.br/'),
    ('Habitat for Humanity Bulgaria',       'BG', 'Sofia',         'https://www.hfh.bg/'),
    ('Habitat for Humanity Cambodia',       'KH', 'Phnom Penh',    'https://www.habitatcambodia.org/'),
    ('Habitat for Humanity Canada',         'CA', 'Toronto',       'https://habitat.ca/'),
    ('Habitat for Humanity Chile',          'CL', 'Santiago',      'https://www.vivienda.cl/'),
    ('Habitat for Humanity Colombia',       'CO', 'Bogota',        'https://www.habitatcolombia.org/'),
    ('Habitat for Humanity Costa Rica',     'CR', 'San Jose',      'https://habitatcostarica.org/'),
    ('Habitat for Humanity Dominican Republic', 'DO', 'Santo Domingo', 'https://habitatdominicana.org/'),
    ('Habitat for Humanity Egypt',          'EG', 'Cairo',         'https://www.habitategypt.org/'),
    ('Habitat for Humanity El Salvador',    'SV', 'San Salvador',  'https://habitatelsalvador.org.sv/'),
    ('Habitat for Humanity Ethiopia',       'ET', 'Addis Ababa',   'https://www.habitat.org/where-we-work/ethiopia'),
    ('Habitat for Humanity Fiji',           'FJ', 'Suva',          'https://www.habitatfiji.org.fj/'),
    ('Habitat for Humanity Germany',        'DE', 'Cologne',       'https://www.habitat-germany.de/'),
    ('Habitat for Humanity Great Britain',  'GB', 'Slough',        'https://www.habitatforhumanity.org.uk/'),
    ('Habitat for Humanity Guatemala',      'GT', 'Guatemala City','https://www.habitatguate.org/'),
    ('Habitat for Humanity Haiti',          'HT', 'Port-au-Prince','https://www.habitathaiti.org/'),
    ('Habitat for Humanity Honduras',       'HN', 'Tegucigalpa',   'https://habitathonduras.org/'),
    ('Habitat for Humanity Hong Kong',      'HK', 'Hong Kong',     'https://habitat.org.hk/'),
    ('Habitat for Humanity Hungary',        'HU', 'Budapest',      'https://www.habitat.hu/'),
    ('Habitat for Humanity India',          'IN', 'Mumbai',        'https://habitatindia.org/'),
    ('Habitat for Humanity Indonesia',      'ID', 'Jakarta',       'https://habitatindonesia.org/'),
    ('Habitat for Humanity Ireland',        'IE', 'Dublin',        'https://www.habitatireland.org/'),
    ('Habitat for Humanity Italy',          'IT', 'Padova',        'https://www.habitatitalia.org/'),
    ('Habitat for Humanity Japan',          'JP', 'Tokyo',         'https://www.habitatjp.org/'),
    ('Habitat for Humanity Jordan',         'JO', 'Amman',         'https://www.habitatjordan.org/'),
    ('Habitat for Humanity Kenya',          'KE', 'Nairobi',       'https://www.habitatkenya.org/'),
    ('Habitat for Humanity Kyrgyzstan',     'KG', 'Bishkek',       'https://www.habitat.kg/'),
    ('Habitat for Humanity Lebanon',        'LB', 'Beirut',        'https://www.habitatlebanon.org/'),
    ('Habitat for Humanity Lesotho',        'LS', 'Maseru',        'https://www.habitat.org/where-we-work/lesotho'),
    ('Habitat for Humanity Macedonia',      'MK', 'Skopje',        'https://www.habitat.org.mk/'),
    ('Habitat for Humanity Malawi',         'MW', 'Lilongwe',      'https://www.habitatmalawi.org/'),
    ('Habitat for Humanity Mexico',         'MX', 'Guadalajara',   'https://habitatmexico.org/'),
    ('Habitat for Humanity Mozambique',     'MZ', 'Maputo',        'https://www.habitatmozambique.org/'),
    ('Habitat for Humanity Nepal',          'NP', 'Kathmandu',     'https://habitatnepal.org/'),
    ('Habitat for Humanity Netherlands',    'NL', 'Utrecht',       'https://www.habitat-holland.nl/'),
    ('Habitat for Humanity New Zealand',    'NZ', 'Auckland',      'https://www.habitat.org.nz/'),
    ('Habitat for Humanity Nicaragua',      'NI', 'Managua',       'https://www.habitatnicaragua.org/'),
    ('Habitat for Humanity Northern Ireland', 'GB', 'Belfast',     'https://www.habitatni.co.uk/'),
    ('Habitat for Humanity Palestine',      'PS', 'Bethlehem',     'https://www.habitatpalestine.org/'),
    ('Habitat for Humanity Panama',         'PA', 'Panama City',   'https://www.habitatpanama.org/'),
    ('Habitat for Humanity Paraguay',       'PY', 'Asuncion',      'https://habitatparaguay.org/'),
    ('Habitat for Humanity Peru',           'PE', 'Lima',          'https://www.habitatperu.org.pe/'),
    ('Habitat for Humanity Philippines',    'PH', 'Manila',        'https://www.habitat.org.ph/'),
    ('Habitat for Humanity Poland',         'PL', 'Warsaw',        'https://habitatpoland.pl/'),
    ('Habitat for Humanity Portugal',       'PT', 'Lisbon',        'https://www.habitat.pt/'),
    ('Habitat for Humanity Puerto Rico',    'PR', 'San Juan',      'https://habitatpr.org/'),
    ('Habitat for Humanity Romania',        'RO', 'Bucharest',     'https://www.habitat.ro/'),
    ('Habitat for Humanity Singapore',      'SG', 'Singapore',     'https://www.habitatsingapore.org/'),
    ('Habitat for Humanity Slovakia',       'SK', 'Bratislava',    'https://www.habitat.sk/'),
    ('Habitat for Humanity South Africa',   'ZA', 'Cape Town',     'https://www.habitat.org.za/'),
    ('Habitat for Humanity Sri Lanka',      'LK', 'Colombo',       'https://habitatsrilanka.org/'),
    ('Habitat for Humanity Thailand',       'TH', 'Bangkok',       'https://www.habitatthailand.org/'),
    ('Habitat for Humanity Uganda',         'UG', 'Kampala',       'https://www.habitatuganda.org/'),
    ('Habitat for Humanity Vietnam',        'VN', 'Ho Chi Minh City', 'https://habitatvietnam.org/'),
    ('Habitat for Humanity Zambia',         'ZM', 'Lusaka',        'https://www.habitatzambia.org/'),
    # Regional HQs and branded sub-orgs that are themselves distinct entities.
    ('Habitat for Humanity Europe, Middle East and Africa', 'SK', 'Bratislava',
     'https://www.habitat.org/emea'),
    ('Habitat for Humanity Asia-Pacific',    'PH', 'Manila',       'https://www.habitat.org/asia-pacific'),
    ('Habitat for Humanity International',   'US', 'Atlanta',      'https://www.habitat.org/'),
    ('Habitat for Humanity International Inc - Americas regional office', 'US', 'San Jose', 'https://www.habitat.org/lac'),
    ('Habitat for Humanity Terwilliger Center for Innovation in Shelter', 'US', 'Washington',
     'https://www.habitat.org/our-work/terwilliger-center-innovation-in-shelter'),
]


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


def try_primary(refresh):
    """Record the attempt on habitat.org/where-we-work. The page exists but
    its affiliate list is client-side-only, so we just cache the HTML shell
    as evidence of the attempt."""
    key = 'primary:' + PRIMARY_URL
    if not refresh:
        cached = read_cache(key)
        if cached and not cached.startswith('FETCH_FAILED:'):
            return cached
    try:
        req = urllib.request.Request(PRIMARY_URL, headers={
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml',
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read().decode('utf-8', errors='replace')
        write_cache(key, data)
        time.sleep(SLEEP_BETWEEN)
        return data
    except urllib.error.HTTPError as e:
        msg = f'FETCH_FAILED: HTTP {e.code} {e.reason}'
        print(f'  Primary {PRIMARY_URL} -> {msg}')
        write_cache(key, msg)
        return None
    except Exception as e:
        msg = f'FETCH_FAILED: {e}'
        print(f'  Primary {PRIMARY_URL} -> {msg}')
        write_cache(key, msg)
        return None


def run_migration(db):
    for col, typedef in [
        ('evidence_url', 'TEXT'),
        ('evidence_quote', 'TEXT'),
        ('evidence_fetched_at', 'TEXT'),
        ('legibility', "TEXT DEFAULT 'unknown'"),
    ]:
        ensure_column(db, 'organizations', col, typedef)


def enrich_us_affiliates(db, dry_run=False):
    """UPDATE existing IRS_EO_BMF rows named 'Habitat for Humanity ...' with
    land-and-housing tags. Returns count updated. No new rows."""
    c = db.cursor()
    now = datetime.now(timezone.utc).isoformat()

    c.execute(
        """SELECT id, tags FROM organizations
           WHERE status='active'
             AND source='IRS_EO_BMF'
             AND UPPER(name) LIKE '%HABITAT%'
             AND UPPER(name) LIKE '%HUMANITY%'"""
    )
    hits = c.fetchall()

    if dry_run:
        return len(hits)

    updated = 0
    for (row_id, tags_existing) in hits:
        tags = (tags_existing or '').strip()
        tag_list = [t.strip() for t in tags.split(',') if t.strip()] if tags else []
        if 'habitat_affiliate' not in tag_list:
            tag_list.append('habitat_affiliate')
        if 'sweat_equity' not in tag_list:
            tag_list.append('sweat_equity')
        new_tags = ','.join(tag_list)

        c.execute(
            """UPDATE organizations
               SET registration_type=?,
                   framework_area=?,
                   model_type=?,
                   legibility='formal',
                   tags=?,
                   alignment_score=MAX(COALESCE(alignment_score,0), ?),
                   evidence_fetched_at=?
               WHERE id=?""",
            (
                'land_and_housing/sweat_equity_program',
                'housing_land',
                'sweat_equity_program',
                new_tags,
                3,
                now,
                row_id,
            ),
        )
        updated += 1

    db.commit()
    return updated


def insert_country_offices(db, dry_run=False):
    """INSERT OR UPDATE one row per Habitat country/regional office."""
    c = db.cursor()
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    updated = 0
    for name, cc, city, website in COUNTRY_OFFICES:
        # Source_id is country-code + name slug so the regional rows that
        # share a country code (for example two US rows) stay distinct.
        slug = ''.join(ch if ch.isalnum() else '-' for ch in name.lower()).strip('-')
        sid = f'{cc}:{slug}'[:200]

        if dry_run:
            inserted += 1
            continue

        c.execute(
            "SELECT id FROM organizations WHERE source=? AND source_id=?",
            ('habitat_affiliates', sid),
        )
        existing = c.fetchone()
        description = (
            f'Habitat for Humanity country or regional office. Sweat-equity '
            f'homeownership program. See {website}.'
        )
        country_name = {
            'AR': 'Argentina', 'AM': 'Armenia', 'AU': 'Australia', 'BD': 'Bangladesh',
            'BO': 'Bolivia', 'BW': 'Botswana', 'BR': 'Brazil', 'BG': 'Bulgaria',
            'KH': 'Cambodia', 'CA': 'Canada', 'CL': 'Chile', 'CO': 'Colombia',
            'CR': 'Costa Rica', 'DO': 'Dominican Republic', 'EG': 'Egypt',
            'SV': 'El Salvador', 'ET': 'Ethiopia', 'FJ': 'Fiji', 'DE': 'Germany',
            'GB': 'United Kingdom', 'GT': 'Guatemala', 'HT': 'Haiti',
            'HN': 'Honduras', 'HK': 'Hong Kong', 'HU': 'Hungary', 'IN': 'India',
            'ID': 'Indonesia', 'IE': 'Ireland', 'IT': 'Italy', 'JP': 'Japan',
            'JO': 'Jordan', 'KE': 'Kenya', 'KG': 'Kyrgyzstan', 'LB': 'Lebanon',
            'LS': 'Lesotho', 'MK': 'North Macedonia', 'MW': 'Malawi',
            'MX': 'Mexico', 'MZ': 'Mozambique', 'NP': 'Nepal', 'NL': 'Netherlands',
            'NZ': 'New Zealand', 'NI': 'Nicaragua', 'PS': 'Palestine',
            'PA': 'Panama', 'PY': 'Paraguay', 'PE': 'Peru', 'PH': 'Philippines',
            'PL': 'Poland', 'PT': 'Portugal', 'PR': 'Puerto Rico', 'RO': 'Romania',
            'SG': 'Singapore', 'SK': 'Slovakia', 'ZA': 'South Africa',
            'LK': 'Sri Lanka', 'TH': 'Thailand', 'UG': 'Uganda', 'VN': 'Vietnam',
            'ZM': 'Zambia', 'US': 'United States',
        }.get(cc, '')

        if existing:
            c.execute(
                """UPDATE organizations
                   SET name=?, country_code=?, country_name=?, city=?,
                       description=COALESCE(NULLIF(description,''), ?),
                       website=COALESCE(NULLIF(website,''), ?),
                       registration_type=?, model_type=?,
                       framework_area=?, alignment_score=MAX(COALESCE(alignment_score,0), ?),
                       tags=COALESCE(NULLIF(tags,''), ?),
                       legibility='formal',
                       evidence_url=COALESCE(NULLIF(evidence_url,''), ?),
                       evidence_fetched_at=?
                   WHERE id=?""",
                (
                    name, cc, country_name, city,
                    description, website,
                    'land_and_housing/sweat_equity_program',
                    'sweat_equity_program',
                    'housing_land', 3,
                    'habitat_affiliate,sweat_equity',
                    website, now,
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
                    legibility, evidence_url, evidence_fetched_at, tags)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?,?)""",
                (
                    name, cc, country_name, city, description, website,
                    'habitat_affiliates', sid,
                    'land_and_housing/sweat_equity_program',
                    'sweat_equity_program',
                    'housing_land', 3,
                    now,
                    'formal',
                    website, now,
                    'habitat_affiliate,sweat_equity',
                ),
            )
            if c.rowcount:
                inserted += 1

    db.commit()
    return inserted, updated


def write_log(lines):
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f'\n# ingest_habitat run - {today}\n\n')
        for line in lines:
            f.write(line + '\n')


def main():
    ap = argparse.ArgumentParser(description='Habitat for Humanity affiliate ingest')
    ap.add_argument('--dry-run', action='store_true', help='Count, no writes')
    ap.add_argument('--refresh', action='store_true', help='Ignore cache')
    args = ap.parse_args()

    print('Ingesting Habitat for Humanity affiliates')

    # Attempt to cache the primary page regardless (evidence of attempt).
    try_primary(args.refresh)

    db = sqlite3.connect(DB_PATH)
    run_migration(db)

    us_enriched = enrich_us_affiliates(db, dry_run=args.dry_run)
    print(f'  US IRS affiliates {"would be " if args.dry_run else ""}enriched: {us_enriched}')

    intl_inserted, intl_updated = (0, 0)
    if args.dry_run:
        intl_inserted = len(COUNTRY_OFFICES)
    else:
        intl_inserted, intl_updated = insert_country_offices(db, dry_run=False)
    print(f'  International offices: inserted={intl_inserted} updated={intl_updated}')

    db.close()

    mode = '[DRY RUN] ' if args.dry_run else ''
    lines = [
        f"Mode: {'dry-run' if args.dry_run else 'real'}",
        f"US IRS rows enriched (source=IRS_EO_BMF): {us_enriched}",
        f"International offices inserted (source=habitat_affiliates): {intl_inserted}",
        f"International offices updated: {intl_updated}",
        '',
        f'{mode}Total rows touched: {us_enriched + intl_inserted + intl_updated}',
    ]
    print('\n' + '\n'.join(lines))
    write_log(lines)
    print(f'\nLog appended: {LOG_PATH}')


if __name__ == '__main__':
    main()
