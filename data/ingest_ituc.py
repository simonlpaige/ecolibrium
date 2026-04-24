"""
ITUC (International Trade Union Confederation) affiliate ingest.

Source order:
  1. https://www.ituc-csi.org/list-of-affiliated-organisations  (primary)
  2. Wikipedia: 'International Trade Union Confederation', 'Affiliated
     Organisations' section, parsed from wikitext.                (fallback)

As of 2026-04-24 the primary URL returns 403 Forbidden to non-browser
clients regardless of User-Agent. The script records that attempt in the
cache, then falls back to Wikipedia, whose community-maintained affiliate
table is the public mirror of the ITUC list. Every ITUC affiliate is by
definition federation-tier, so inserts use category='labor/union_federation'
and legibility='formal'.

HTML and wikitext responses are cached under data/sources/ituc-cache/ so
re-runs do not re-hit the server. Re-runs are idempotent on
(source='ituc_affiliates', source_id=<slugified affiliate URL or acronym>).

Usage:
    python ingest_ituc.py               # normal run
    python ingest_ituc.py --dry-run     # parse + count only, no writes
    python ingest_ituc.py --refresh     # ignore cache, re-fetch
"""
import argparse
import hashlib
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

CACHE_DIR = os.path.join(DATA_DIR, 'sources', 'ituc-cache')
LOG_PATH = os.path.join(DATA_DIR, 'ingest-unions-run.log')

ITUC_URL = 'https://www.ituc-csi.org/list-of-affiliated-organisations'
WIKIPEDIA_API = 'https://en.wikipedia.org/w/api.php'
WIKIPEDIA_PAGE = 'International Trade Union Confederation'

USER_AGENT = 'Commonweave/1.0 (https://commonweave.earth; directory@commonweave.earth)'
SLEEP_BETWEEN = 1  # seconds between network hits


# Country name (as it appears in the Wikipedia affiliates table) -> ISO 3166-1 alpha-2
# Only the names used on the ITUC page. Extend when new affiliates land.
COUNTRY_NAME_TO_CC = {
    'Albania': 'AL', 'Algeria': 'DZ', 'Angola': 'AO', 'Antigua & Barbuda': 'AG',
    'Antigua and Barbuda': 'AG', 'Argentina': 'AR', 'Armenia': 'AM', 'Aruba': 'AW',
    'Australia': 'AU', 'Austria': 'AT', 'Azerbaijan': 'AZ', 'Bahamas': 'BS',
    'Bahrain': 'BH', 'Bangladesh': 'BD', 'Barbados': 'BB', 'Belarus': 'BY',
    'Belgium': 'BE', 'Belize': 'BZ', 'Benin': 'BJ', 'Bermuda': 'BM',
    'Bolivia': 'BO', 'Bonaire': 'BQ', 'Bosnia and Herzegovina': 'BA',
    'Bosnia-Herzegovina': 'BA', 'Botswana': 'BW',
    'Brazil': 'BR', 'Bulgaria': 'BG', 'Burkina Faso': 'BF',
    'Burma': 'MM', 'Burundi': 'BI',
    'Cambodia': 'KH', 'Cameroon': 'CM', 'Canada': 'CA', 'Cape Verde': 'CV',
    'Central African Republic': 'CF', 'Chad': 'TD', 'Chile': 'CL', 'Colombia': 'CO',
    'Comoros': 'KM', 'Congo': 'CG', 'Democratic Republic of the Congo': 'CD',
    'Democratic Republic of Congo': 'CD', 'DR Congo': 'CD',
    'Cook Islands': 'CK', 'Costa Rica': 'CR', "Cote d'Ivoire": 'CI',
    "Côte d'Ivoire": 'CI', 'Ivory Coast': 'CI', 'Croatia': 'HR',
    'Cuba': 'CU', 'Curaçao': 'CW', 'Curacao': 'CW', 'Cyprus': 'CY',
    'Czech Republic': 'CZ', 'Czechia': 'CZ', 'Denmark': 'DK', 'Djibouti': 'DJ',
    'Dominica': 'DM', 'Dominican Republic': 'DO', 'Ecuador': 'EC', 'Egypt': 'EG',
    'El Salvador': 'SV', 'Equatorial Guinea': 'GQ', 'Estonia': 'EE',
    'Eswatini': 'SZ', 'Swaziland': 'SZ', 'Ethiopia': 'ET', 'Fiji': 'FJ',
    'Finland': 'FI', 'France': 'FR', 'French Polynesia': 'PF', 'Gabon': 'GA',
    'Gambia': 'GM', 'The Gambia': 'GM', 'Georgia': 'GE', 'Germany': 'DE',
    'Ghana': 'GH', 'Greece': 'GR', 'Grenada': 'GD', 'Guatemala': 'GT',
    'Guinea': 'GN', 'Guinea-Bissau': 'GW', 'Guyana': 'GY', 'Haiti': 'HT',
    'Honduras': 'HN', 'Hong Kong': 'HK', 'Hong Kong SAR, China': 'HK',
    'Hungary': 'HU', 'Iceland': 'IS',
    'India': 'IN', 'Indonesia': 'ID', 'Iran': 'IR', 'Iraq': 'IQ',
    'Ireland': 'IE', 'Israel': 'IL', 'Italy': 'IT', 'Jamaica': 'JM',
    'Japan': 'JP', 'Jordan': 'JO', 'Kazakhstan': 'KZ', 'Kenya': 'KE',
    'Kiribati': 'KI', 'Korea, South': 'KR', 'South Korea': 'KR',
    'Kosovo': 'XK', 'Kuwait': 'KW', 'Kyrgyzstan': 'KG', 'Laos': 'LA',
    'Latvia': 'LV', 'Republic of Latvia': 'LV',
    'Lebanon': 'LB', 'Lesotho': 'LS', 'Liberia': 'LR',
    'Libya': 'LY', 'Liechtenstein': 'LI', 'Lithuania': 'LT',
    'Republic of Lithuania': 'LT', 'Luxembourg': 'LU',
    'Macau': 'MO', 'Madagascar': 'MG', 'Malawi': 'MW', 'Malaysia': 'MY',
    'Maldives': 'MV', 'Mali': 'ML', 'Malta': 'MT', 'Mauritania': 'MR',
    'Mauritius': 'MU', 'Mexico': 'MX', 'Moldova': 'MD', 'Mongolia': 'MN',
    'Montenegro': 'ME', 'Republic of Montenegro': 'ME',
    'Morocco': 'MA', 'Mozambique': 'MZ', 'Myanmar': 'MM',
    'Namibia': 'NA', 'Nepal': 'NP', 'Netherlands': 'NL', 'New Caledonia': 'NC',
    'New Zealand': 'NZ', 'Nicaragua': 'NI', 'Niger': 'NE', 'Nigeria': 'NG',
    'North Macedonia': 'MK', 'Macedonia': 'MK', 'Norway': 'NO', 'Pakistan': 'PK',
    'Palestine': 'PS', 'Panama': 'PA', 'Papua New Guinea': 'PG',
    'Paraguay': 'PY', 'Peru': 'PE', 'Philippines': 'PH', 'Poland': 'PL',
    'Portugal': 'PT', 'Puerto Rico': 'PR', 'Qatar': 'QA', 'Romania': 'RO',
    'Russia': 'RU', 'Russian Federation': 'RU', 'Rwanda': 'RW',
    'Saint Lucia': 'LC', 'St. Lucia': 'LC',
    'Samoa': 'WS', 'San Marino': 'SM', 'Sao Tome and Principe': 'ST',
    'São Tomé and Príncipe': 'ST', 'Saudi Arabia': 'SA',
    'Senegal': 'SN', 'Serbia': 'RS', 'Seychelles': 'SC', 'Sierra Leone': 'SL',
    'Singapore': 'SG', 'Slovakia': 'SK', 'Slovenia': 'SI',
    'Solomon Islands': 'SB', 'Somalia': 'SO', 'South Africa': 'ZA',
    'South Sudan': 'SS', 'Spain': 'ES', 'Sri Lanka': 'LK', 'Sudan': 'SD',
    'Suriname': 'SR', 'Surinam': 'SR', 'Sweden': 'SE', 'Switzerland': 'CH', 'Syria': 'SY',
    'Taiwan': 'TW', 'Tajikistan': 'TJ', 'Tanzania': 'TZ', 'Thailand': 'TH',
    'Timor Leste': 'TL', 'Timor-Leste': 'TL', 'East Timor': 'TL',
    'Togo': 'TG', 'Tonga': 'TO', 'Trinidad and Tobago': 'TT',
    'Tunisia': 'TN', 'Turkey': 'TR', 'Türkiye': 'TR',
    'Turkmenistan': 'TM', 'Tuvalu': 'TV', 'Uganda': 'UG', 'Ukraine': 'UA',
    'United Arab Emirates': 'AE', 'United Kingdom': 'GB', 'UK': 'GB',
    'Great Britain': 'GB', 'England': 'GB', 'United States': 'US',
    'USA': 'US', 'U.S.': 'US', 'Uruguay': 'UY', 'Uzbekistan': 'UZ',
    'Vanuatu': 'VU', 'Vatican City': 'VA', 'Vatican': 'VA',
    'Venezuela': 'VE', 'Vietnam': 'VN', 'Viet Nam': 'VN', 'Yemen': 'YE',
    'Zambia': 'ZM', 'Zimbabwe': 'ZW',
}


def cache_path(key):
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = hashlib.sha1(key.encode('utf-8')).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f'{safe}.txt')


def read_cache(key):
    path = cache_path(key)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def write_cache(key, content):
    path = cache_path(key)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def http_get(url, headers=None, timeout=30):
    h = {'User-Agent': USER_AGENT, 'Accept': 'text/html,application/xhtml+xml'}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='replace')


def try_primary(refresh):
    """Try the ITUC canonical URL. Cache success or failure note either way."""
    cache_key = 'primary:' + ITUC_URL
    if not refresh:
        cached = read_cache(cache_key)
        if cached:
            return cached if not cached.startswith('FETCH_FAILED:') else None
    print(f'  Fetching primary: {ITUC_URL}')
    try:
        content = http_get(ITUC_URL)
        write_cache(cache_key, content)
        time.sleep(SLEEP_BETWEEN)
        return content
    except urllib.error.HTTPError as e:
        msg = f'FETCH_FAILED: HTTP {e.code} {e.reason}'
        print(f'    {msg}. Falling back to Wikipedia.')
        write_cache(cache_key, msg)
        return None
    except Exception as e:
        msg = f'FETCH_FAILED: {e}'
        print(f'    {msg}. Falling back to Wikipedia.')
        write_cache(cache_key, msg)
        return None


def try_fallback(refresh):
    """Fetch Wikipedia wikitext for the ITUC article, which includes the
    Affiliated Organisations table."""
    cache_key = 'wikipedia:' + WIKIPEDIA_PAGE
    if not refresh:
        cached = read_cache(cache_key)
        if cached:
            return cached
    url = WIKIPEDIA_API + '?' + urllib.parse.urlencode({
        'action': 'parse',
        'page': WIKIPEDIA_PAGE,
        'prop': 'wikitext',
        'format': 'json',
        'formatversion': '2',
    })
    print(f'  Fetching fallback (Wikipedia): {WIKIPEDIA_PAGE}')
    content = http_get(url, headers={'Accept': 'application/json'})
    write_cache(cache_key, content)
    time.sleep(SLEEP_BETWEEN)
    return content


# Wikitext table parsing.
# Rows look like:
#   |[[Article title|Display Name (ACRONYM)]]
#   |[[Country]]
#   |1,234,567
#   |-
# Sometimes the display name is a plain string or has no acronym. Membership
# cell can be blank. We read cells in the order Organisation, Country,
# Membership.

LINK_RE = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')
ACRONYM_RE = re.compile(r'\(([^()]{2,12})\)\s*$')
PARENS_RE = re.compile(r'\s*\([^()]{2,40}\)\s*$')
COMMA_NUM_RE = re.compile(r'^[\d,\.]+$')


def strip_wikilinks(cell):
    """Replace [[target|display]] with display, or [[target]] with target."""
    def repl(m):
        return m.group(2) if m.group(2) else m.group(1)
    return LINK_RE.sub(repl, cell).strip()


def first_wikilink_target(cell):
    m = LINK_RE.search(cell)
    if not m:
        return ''
    return m.group(1).strip()


def parse_wikipedia_wikitext(payload):
    """Accept raw Wikipedia API JSON, return list of affiliate dicts."""
    import json as _json
    data = _json.loads(payload)
    # formatversion=2 -> data['parse']['wikitext']
    parse_obj = data.get('parse', {})
    wikitext = parse_obj.get('wikitext')
    if isinstance(wikitext, dict):
        wikitext = wikitext.get('*', '')
    if not wikitext:
        return []

    # Find the 'Affiliated Organisations' section's wikitable
    hdr = wikitext.find('Affiliated Organisations')
    if hdr < 0:
        # be lenient about punctuation
        hdr = wikitext.find('Affiliates')
    section = wikitext[hdr:] if hdr >= 0 else wikitext
    # find first {| ... |} wikitable in this section
    start = section.find('{|')
    if start < 0:
        return []
    end = section.find('\n|}', start)
    if end < 0:
        end = len(section)
    table = section[start:end]

    affiliates = []
    rows = re.split(r'\n\|-\s*\n', table)
    # rows[0] is the header block with "!Organisation", etc.
    for row in rows[1:]:
        # A cell starts with a line beginning with a single |
        cells = [c.strip() for c in re.split(r'\n\|', '\n' + row.strip())]
        cells = [c for c in cells if c]  # drop empties
        if len(cells) < 2:
            continue
        org_cell, country_cell = cells[0], cells[1]
        member_cell = cells[2] if len(cells) >= 3 else ''

        # Organisation - get both the linked page title (for source_id) and
        # the display name.
        wiki_target = first_wikilink_target(org_cell)
        display = strip_wikilinks(org_cell).strip()
        # drop stray refs / html
        display = re.sub(r'<ref[^<]*?</ref>', '', display, flags=re.DOTALL)
        display = re.sub(r'<ref[^/]*/>', '', display)
        display = re.sub(r'<[^>]+>', '', display).strip()

        # Acronym lives in trailing parens
        acronym = ''
        m = ACRONYM_RE.search(display)
        if m:
            acronym = m.group(1).strip()
            display = PARENS_RE.sub('', display).strip()

        # Country cell
        country_raw = strip_wikilinks(country_cell).strip()
        country_raw = re.sub(r'<[^>]+>', '', country_raw).strip()
        # strip any trailing punct
        country_raw = country_raw.rstrip(' .,')

        # Membership count
        mem_clean = re.sub(r'<ref[^<]*?</ref>', '', member_cell, flags=re.DOTALL)
        mem_clean = re.sub(r'<[^>]+>', '', mem_clean).strip()
        mem_count = None
        mem_match = re.search(r'([\d,]+)', mem_clean)
        if mem_match and COMMA_NUM_RE.match(mem_match.group(1)):
            try:
                mem_count = int(mem_match.group(1).replace(',', ''))
            except ValueError:
                mem_count = None

        if not display or not country_raw:
            continue

        cc = COUNTRY_NAME_TO_CC.get(country_raw, '')

        # Source identifier: prefer the Wikipedia article title if present,
        # else the display name + country. Stable across re-runs.
        if wiki_target:
            sid = 'wp:' + wiki_target.replace(' ', '_')
        else:
            sid = 'name:' + display + '|' + country_raw
        sid = sid[:200]

        # evidence URL points at the Wikipedia article for human review
        evidence = ''
        if wiki_target:
            evidence = 'https://en.wikipedia.org/wiki/' + urllib.parse.quote(
                wiki_target.replace(' ', '_')
            )

        affiliates.append({
            'name': display,
            'acronym': acronym,
            'country_name': country_raw,
            'country_code': cc,
            'member_count': mem_count,
            'source_id': sid,
            'evidence_url': evidence,
        })

    return affiliates


def run_migration(db):
    for col, typedef in [
        ('evidence_url', 'TEXT'),
        ('evidence_quote', 'TEXT'),
        ('evidence_fetched_at', 'TEXT'),
        ('legibility', "TEXT DEFAULT 'unknown'"),
    ]:
        ensure_column(db, 'organizations', col, typedef)


def upsert(db, affiliates, dry_run):
    c = db.cursor()
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    updated = 0
    skipped_no_country = 0
    for a in affiliates:
        name = (a.get('name') or '').strip()
        sid = a.get('source_id')
        if not name or not sid:
            continue
        cc = a.get('country_code') or ''
        if not cc:
            # keep the row but flag; search index needs country_code so we
            # skip anything we cannot attribute to a country.
            skipped_no_country += 1
            continue

        if dry_run:
            inserted += 1
            continue

        # build description with member count and acronym if present
        desc_parts = ['ITUC affiliate']
        if a.get('acronym'):
            desc_parts.append(a['acronym'])
        if a.get('member_count'):
            desc_parts.append(f"{a['member_count']:,} members")
        description = '. '.join(desc_parts) + '.'
        tags = 'labor_union,ituc_affiliate'

        c.execute(
            "SELECT id FROM organizations WHERE source=? AND source_id=?",
            ('ituc_affiliates', sid),
        )
        existing = c.fetchone()
        if existing:
            c.execute(
                """UPDATE organizations
                   SET name=?, country_code=?, country_name=?,
                       description=COALESCE(NULLIF(description,''), ?),
                       registration_type=?,
                       model_type=?,
                       tags=COALESCE(NULLIF(tags,''), ?),
                       framework_area=COALESCE(NULLIF(framework_area,''), ?),
                       alignment_score=MAX(COALESCE(alignment_score,0), ?),
                       evidence_url=COALESCE(NULLIF(evidence_url,''), ?),
                       evidence_fetched_at=?,
                       legibility='formal'
                   WHERE id=?""",
                (
                    name, cc, a.get('country_name', ''),
                    description,
                    'labor/union_federation',
                    'labor_union',
                    tags,
                    'cooperatives',
                    2,
                    a.get('evidence_url', ''),
                    now,
                    existing[0],
                ),
            )
            updated += 1
        else:
            c.execute(
                """INSERT OR IGNORE INTO organizations
                   (name, country_code, country_name, description,
                    source, source_id, registration_type, model_type,
                    framework_area, alignment_score, status, date_added,
                    legibility, evidence_url, evidence_fetched_at, tags)
                   VALUES (?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?,?)""",
                (
                    name, cc, a.get('country_name', ''), description,
                    'ituc_affiliates', sid,
                    'labor/union_federation',
                    'labor_union',
                    'cooperatives', 2,
                    now,
                    'formal',
                    a.get('evidence_url', ''), now,
                    tags,
                ),
            )
            if c.rowcount:
                inserted += 1

    if not dry_run:
        db.commit()
    return inserted, updated, skipped_no_country


def write_log(lines):
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f'\n# ingest_ituc run - {today}\n\n')
        for line in lines:
            f.write(line + '\n')


def main():
    ap = argparse.ArgumentParser(description='ITUC affiliate ingest')
    ap.add_argument('--dry-run', action='store_true', help='Parse + count, no writes')
    ap.add_argument('--refresh', action='store_true', help='Ignore cache, re-fetch')
    args = ap.parse_args()

    print('Ingesting ITUC affiliates')

    content = try_primary(args.refresh)
    source_used = 'ituc-csi.org'
    if not content:
        content = try_fallback(args.refresh)
        source_used = 'wikipedia:ITUC'

    if not content:
        print('  FATAL: neither ITUC nor Wikipedia fetch succeeded')
        sys.exit(1)

    # Parse. Today we only have a parser for the Wikipedia wikitext format.
    if source_used == 'ituc-csi.org':
        # If/when ITUC HTML becomes reachable, add a parser here. For now,
        # if we got HTML we still defer to Wikipedia because the ITUC page
        # relies on JavaScript to hydrate the list.
        print('  Primary fetched but HTML parser not implemented; using Wikipedia')
        content = try_fallback(args.refresh)
        source_used = 'wikipedia:ITUC'

    affiliates = parse_wikipedia_wikitext(content)
    print(f'  Parsed {len(affiliates)} affiliate rows from {source_used}')

    no_cc = sum(1 for a in affiliates if not a.get('country_code'))
    if no_cc:
        print(f'  Warning: {no_cc} rows had a country name we cannot map to ISO-2:')
        seen = set()
        for a in affiliates:
            if not a.get('country_code'):
                name = a.get('country_name', '')
                if name and name not in seen:
                    seen.add(name)
                    print(f'    - {name}')

    db = sqlite3.connect(DB_PATH)
    run_migration(db)
    inserted, updated, skipped = upsert(db, affiliates, args.dry_run)
    db.close()

    mode = '[DRY RUN] Would insert' if args.dry_run else 'Inserted'
    lines = [
        f"Source used: {source_used}",
        f"Parsed rows: {len(affiliates)}",
        f"{mode}: {inserted}",
        f"Updated:     {updated}",
        f"Skipped (no country mapping): {skipped}",
    ]
    print('\n' + '\n'.join(lines))
    write_log(lines)
    print(f'\nLog appended: {LOG_PATH}')


if __name__ == '__main__':
    main()
