"""
gen-audit-data.py -- Generate audit JSON for the web portal.

Modes:
  --mode random      Pure random sample (baseline)
  --mode outlier     Outlier-weighted sample (default) -- highest review value
  --mode thin        Thin-coverage countries only

Usage:
  python tools/gen-audit-data.py --region usa --n 60
  python tools/gen-audit-data.py --region india --n 60 --mode outlier
  python tools/gen-audit-data.py --region latam --n 80 --stratified
"""
import sqlite3, json, os, sys, argparse, random, re
from collections import defaultdict

DB      = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'commonweave_directory.db'))
OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'audit'))
STATE_MAP_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'state_province_map.json'))


# ---- Subregion variant resolution -------------------------------------------

_STATE_MAP_CACHE = None

def _load_state_map():
    """Load and cache data/state_province_map.json. Returns the dict, or {} if missing."""
    global _STATE_MAP_CACHE
    if _STATE_MAP_CACHE is not None:
        return _STATE_MAP_CACHE
    if not os.path.exists(STATE_MAP_PATH):
        _STATE_MAP_CACHE = {}
        return _STATE_MAP_CACHE
    try:
        with open(STATE_MAP_PATH, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        # Drop comment fields like _comment
        _STATE_MAP_CACHE = {k: v for k, v in raw.items() if not k.startswith('_')}
    except Exception:
        _STATE_MAP_CACHE = {}
    return _STATE_MAP_CACHE


def resolve_subregion(subregion_input, country_code=None):
    """Expand a single subregion input ("MO", "Missouri", etc.) into the full
    list of variants from the state/province map.

    Args:
        subregion_input: free-text subregion as supplied by the caller.
        country_code: optional 2-letter country code or list of codes; when given,
            we prefer matches inside that country to break ambiguity (e.g. "PR"
            could be Puerto Rico or Parana).

    Returns:
        A list of variant strings to use in OR LIKE queries. Falls back to
        [subregion_input] if no match is found.
    """
    if not subregion_input:
        return []
    needle = subregion_input.strip().lower()
    if not needle:
        return [subregion_input]

    iso_map = _load_state_map()
    if not iso_map:
        return [subregion_input]

    # Normalise country_code to a set for membership tests.
    if isinstance(country_code, str):
        country_set = {country_code.strip().upper()}
    elif country_code:
        country_set = {str(cc).strip().upper() for cc in country_code if cc}
    else:
        country_set = None

    matches = []  # list of (iso_code, variants)
    for iso, variants in iso_map.items():
        for v in variants:
            if v.strip().lower() == needle:
                matches.append((iso, variants))
                break

    if not matches:
        return [subregion_input]

    # If we have a country filter and at least one match agrees with it, keep
    # only the in-country matches. This disambiguates short codes like "PR".
    if country_set:
        in_country = [m for m in matches if m[0].split('-', 1)[0] in country_set]
        if in_country:
            matches = in_country

    # If multiple matches survive, union their variants.
    out = []
    seen = set()
    for iso, variants in matches:
        for v in variants:
            key = v.strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(v)
    return out or [subregion_input]

SPANISH = ['MX','CO','AR','CL','PE','VE','EC','BO','PY','UY','DO','GT','HN','SV','NI','CR','PA','CU','ES','PR']

TRUST_SOURCES = {
    'ica_directory','ituc_affiliates','construction_coops','susy_map',
    'clt_world_map','nec_members','mutual_aid_hub','transition_network',
    'ripess_family','habitat_affiliates','grounded_solutions','manual_curation',
    'ic_directory','wikidata_land_trusts','wikidata_unions','web_research',
}

NOISY_SOURCES = {'wikidata', 'wikidata_subregion', 'wikidata_bg_npo'}

# Section keyword signals for mismatch detection
SECTION_SIGNALS = {
    'food':        ['food','farm','agri','seed','garden','hunger','nutrition','harvest'],
    'healthcare':  ['health','clinic','hospital','medical','care','nurse','patient'],
    'education':   ['school','learn','educat','student','teach','college','university','training'],
    'housing_land':['hous','land','shelter','tenants','rent','evict','homelessness','clt'],
    'democracy':   ['civic','democ','vote','rights','justice','policy','govern','participat'],
    'ecology':     ['ecology','environment','conservation','wildlife','forest','climate','sustain','agroforest'],
    'conflict':    ['peace','justice','conflict','restor','mediat','nonviolent','rights','legal'],
    'cooperatives':['cooperative','co-op','coop','worker','mutual','credit union','solidarity'],
    'energy_digital':['energy','solar','wind','renewable','digital','open source','tech','data commons'],
    'recreation_arts':['arts','culture','recreation','sport','music','theater','community center'],
}

SOURCE_LABELS = {
    'mapa_oscs_brazil': 'Mapa das OSCs (Brazil)', 'acnc_charity_register': 'ACNC (Australia)',
    'uk_charity_commission': 'UK Charity Commission', 'IRS_EO_BMF': 'IRS EO BMF (USA)',
    'mutual_aid_wiki': 'Mutual Aid Wiki', 'wikidata': 'Wikidata',
    'wikidata_bg_npo': 'Wikidata (Bulgaria)', 'ic_directory': 'Intentional Communities Dir.',
    'transition_network': 'Transition Network', 'mutual_aid_hub': 'Mutual Aid Hub',
    'susy_map': 'SUSY Map', 'ProPublica': 'ProPublica',
    'wikidata_subregion': 'Wikidata (subregion)', 'wikidata_land_trusts': 'Wikidata (land trusts)',
    'clt_world_map': 'CLT World Map', 'wikidata_unions': 'Wikidata (labor unions)',
    'ica_directory': 'ICA Member Directory', 'ituc_affiliates': 'ITUC Affiliates',
    'nec_members': 'New Economy Coalition', 'construction_coops': 'Construction Cooperatives',
    'ripess_family': 'RIPESS Network', 'habitat_affiliates': 'Habitat for Humanity',
    'web_research': 'Web Research', 'grounded_solutions': 'Grounded Solutions',
    'manual_curation': 'Manual Curation',
}

SECTION_LABELS = {
    'healthcare': 'Healthcare', 'education': 'Education', 'food': 'Food Sovereignty',
    'democracy': 'Democratic Infrastructure', 'housing_land': 'Land & Housing',
    'ecology': 'Ecological Restoration', 'conflict': 'Conflict Resolution',
    'cooperatives': 'Cooperatives & Solidarity', 'recreation_arts': 'Recreation & Arts',
    'energy_digital': 'Energy & Digital Commons',
}

# ---- Outlier detection -------------------------------------------------------

def detect_outliers(o, country_counts):
    """Return list of outlier flags for an org. Each flag has a type and reason."""
    flags = []
    name   = (o.get('name') or '').lower()
    desc   = (o.get('description') or '').lower()
    src    = o.get('source') or ''
    score  = o.get('alignment_score') or 0
    leg    = o.get('legibility') or 'unknown'
    area   = o.get('framework_area') or ''
    cc     = o.get('country_code') or ''
    text   = name + ' ' + desc

    # FP risk: high score from noisy source
    if src in NOISY_SOURCES and score >= 5:
        flags.append({'type': 'fp_risk', 'label': '⚠️ High score, noisy source',
                      'detail': f'Score {score} from {src} -- verify this is genuinely aligned'})

    # FP risk: scored on name alone (no description)
    if score >= 4 and (not o.get('description') or str(o.get('description')) in ('None','')):
        flags.append({'type': 'fp_risk', 'label': '⚠️ No description, score {}'.format(score),
                      'detail': 'Scored on name only -- could be keyword coincidence'})

    # FP risk: trust source, score = 0
    if src in TRUST_SOURCES and score == 0:
        flags.append({'type': 'scoring_bug', 'label': '🐛 Trust source, score 0',
                      'detail': f'{src} is a curated source -- score=0 suggests a scoring bug, not a bad org'})

    # FN risk: thin-coverage country, low score
    country_n = country_counts.get(cc, 999)
    if country_n <= 20 and score <= 2:
        flags.append({'type': 'fn_risk', 'label': f'🌍 Thin coverage ({country_n} orgs in {cc})',
                      'detail': 'Low score may mean underdocumented, not misaligned -- this country has very few entries'})

    # FN risk: informal legibility, low score
    if leg == 'informal' and score <= 2:
        flags.append({'type': 'fn_risk', 'label': '🤝 Informal org, low score',
                      'detail': 'Community/mutual aid orgs often lack digital presence and alignment keywords -- score may underestimate importance'})

    # Classification mismatch: name/desc signal doesn't match assigned section
    if area:
        top_match = None
        top_hits  = 0
        for section, keywords in SECTION_SIGNALS.items():
            hits = sum(1 for kw in keywords if kw in text)
            if hits > top_hits:
                top_hits  = hits
                top_match = section
        if top_match and top_match != area and top_hits >= 2:
            flags.append({'type': 'section_mismatch', 'label': f'🔄 Possible wrong section',
                          'detail': f'Assigned: {SECTION_LABELS.get(area, area)} -- text signals suggest: {SECTION_LABELS.get(top_match, top_match)}'})

    return flags


# ---- Sampling ----------------------------------------------------------------

def fetch_orgs(conn, cc_list, extra_where='', extra_params=None, limit=500):
    c = conn.cursor()
    where = "status='active'"
    params = []
    if cc_list is not None:
        ph = ','.join(['?' for _ in cc_list])
        where += f" AND country_code IN ({ph})"
        params += list(cc_list)
    sub_clause, sub_params = _subregion_clause()
    if sub_clause:
        where += ' ' + sub_clause
        params += sub_params
    if extra_where:
        where += ' AND ' + extra_where
    params += (extra_params or [])
    params.append(limit)
    c.execute(f"""SELECT id, name, country_code, state_province, city, source,
                         framework_area, alignment_score, description, website,
                         registration_id, legibility, model_type, tags, email, phone
                  FROM organizations WHERE {where} ORDER BY RANDOM() LIMIT ?""", params)
    return [dict(r) for r in c.fetchall()]


def build_outlier_sample(conn, cc_list, n, country_counts):
    """Pull a sample weighted toward outlier cases."""
    buckets = {}
    c = conn.cursor()

    cc_clause, cc_params = _country_clause()
    sub_clause, sub_params = _subregion_clause()

    base_select = (
        "SELECT id, name, country_code, state_province, city, source, "
        "framework_area, alignment_score, description, website, "
        "registration_id, legibility, model_type, tags, email, phone "
        "FROM organizations WHERE status='active' "
        + cc_clause + ' ' + sub_clause + ' '
    )

    def _run(extra_sql, extra_params, lim):
        sql = base_select + extra_sql + ' ORDER BY RANDOM() LIMIT ?'
        params = cc_params + sub_params + extra_params + [lim]
        c.execute(sql, params)
        return [dict(r) for r in c.fetchall()]

    # FP risk: high score from Wikidata
    noisy_ph = ','.join(['?' for _ in NOISY_SOURCES])
    buckets['fp_noisy_high'] = _run(
        f"AND source IN ({noisy_ph}) AND alignment_score >= 5",
        list(NOISY_SOURCES),
        n // 6,
    )

    # FP risk: no description, score >= 4
    buckets['fp_no_desc'] = _run(
        "AND (description IS NULL OR description='') AND alignment_score >= 4",
        [],
        n // 6,
    )

    # Scoring bug: trust source, score = 0
    trust_ph = ','.join(['?' for _ in TRUST_SOURCES])
    buckets['scoring_bug'] = _run(
        f"AND source IN ({trust_ph}) AND alignment_score = 0",
        list(TRUST_SOURCES),
        n // 8,
    )

    # FN risk: thin-coverage countries (<=20 orgs), score <= 2.
    # Skip when region=world (cc_list is None) or when no thin ccs apply.
    if cc_list is not None:
        thin_ccs = [cc for cc in cc_list if country_counts.get(cc, 0) <= 20]
        if thin_ccs:
            thin_ph = ','.join(['?' for _ in thin_ccs])
            sql = (
                "SELECT id, name, country_code, state_province, city, source, "
                "framework_area, alignment_score, description, website, "
                "registration_id, legibility, model_type, tags, email, phone "
                "FROM organizations WHERE status='active' "
                f"AND country_code IN ({thin_ph}) "
                + sub_clause + ' '
                + 'AND alignment_score <= 2 ORDER BY RANDOM() LIMIT ?'
            )
            params = thin_ccs + sub_params + [n // 6]
            c.execute(sql, params)
            buckets['fn_thin'] = [dict(r) for r in c.fetchall()]

    # FN risk: informal, low score
    buckets['fn_informal'] = _run(
        "AND legibility='informal' AND alignment_score <= 2",
        [],
        n // 6,
    )

    # Baseline random (fill remainder)
    seen_ids = set()
    all_outliers = []
    for key, items in buckets.items():
        for item in items:
            if item['id'] not in seen_ids:
                seen_ids.add(item['id'])
                all_outliers.append(item)

    # Fill to n with random orgs not already included
    remaining = max(0, n - len(all_outliers))
    if remaining > 0:
        for d in _run('', [], remaining * 3):
            if d['id'] not in seen_ids:
                seen_ids.add(d['id'])
                all_outliers.append(d)
                if len(all_outliers) >= n:
                    break

    random.shuffle(all_outliers)
    return all_outliers[:n]


# ---- Main --------------------------------------------------------------------

parser = argparse.ArgumentParser()
parser.add_argument('--region', default='usa', choices=['usa','india','latam','world'])
parser.add_argument('--subregion', default=None,
                    help='Filter inside a region by state_province OR city '
                         '(LIKE, case-insensitive). Example: --subregion MO')
parser.add_argument('--n', type=int, default=60)
parser.add_argument('--mode', default='outlier', choices=['random','outlier','thin'])
parser.add_argument('--stratified', action='store_true')
parser.add_argument('--out', default=None)
args = parser.parse_args()

if args.region == 'usa':
    cc_list = ['US']
    label   = 'USA'
elif args.region == 'india':
    cc_list = ['IN']
    label   = 'India'
elif args.region == 'world':
    cc_list = None  # sentinel: do not filter by country_code
    label   = 'World'
else:
    cc_list = SPANISH
    label   = 'Spanish-Speaking Countries'

# ---- Subregion filter ---------------------------------------------------
# When --subregion is set, we narrow the WHERE clause inside fetch_orgs and
# build_outlier_sample below. The filter matches state_province OR city,
# both with LIKE and case-insensitive (LOWER()) so an input like "MO" or
# "Missouri" or "st. louis" all work. We also expand the input through
# resolve_subregion() so that --subregion MO matches "Missouri" and "Mo." too.
SUBREGION = (args.subregion or '').strip()
if SUBREGION:
    # Pass cc_list (e.g. ['US'] when region=usa) in as a country hint so short
    # codes like "PR" or "GA" disambiguate to the correct subdivision.
    SUBREGION_VARIANTS = resolve_subregion(SUBREGION, country_code=cc_list)
else:
    SUBREGION_VARIANTS = []
SUBREGION_LIKES = ['%' + v.lower() + '%' for v in SUBREGION_VARIANTS]


def _subregion_clause(prefix='AND '):
    """Return ('AND (...)', [params]) for the active subregion filter, or ('', []).

    Builds an OR-of-LIKEs: state_province LIKE %v1% OR state_province LIKE %v2%
    OR city LIKE %v1% OR city LIKE %v2% ... so a single --subregion input
    matches all known variants from data/state_province_map.json.
    """
    if not SUBREGION_LIKES:
        return '', []
    parts = []
    params = []
    for like in SUBREGION_LIKES:
        parts.append("LOWER(COALESCE(state_province,'')) LIKE ?")
        params.append(like)
        parts.append("LOWER(COALESCE(city,'')) LIKE ?")
        params.append(like)
    clause = prefix + '(' + ' OR '.join(parts) + ')'
    return clause, params


def _country_clause(field='country_code', prefix='AND '):
    """Return ('AND country_code IN (...)', [params]) or ('', []) for region=world."""
    if cc_list is None:
        return '', []
    ph = ','.join(['?' for _ in cc_list])
    return f"{prefix}{field} IN ({ph})", list(cc_list)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Build country counts for scarcity detection
c2 = conn.cursor()
c2.execute("SELECT country_code, COUNT(*) FROM organizations WHERE status='active' GROUP BY country_code")
country_counts = {r[0]: r[1] for r in c2.fetchall()}

if args.mode == 'outlier':
    if args.stratified and len(cc_list) > 1:
        # Stratified outlier: run outlier detection per country, merge
        orgs = build_outlier_sample(conn, cc_list, args.n, country_counts)
    else:
        orgs = build_outlier_sample(conn, cc_list, args.n, country_counts)
elif args.mode == 'thin':
    if cc_list is None:
        # region=world: pull thin countries globally
        thin_ccs = [cc for cc, n in country_counts.items() if n <= 50]
    else:
        thin_ccs = [cc for cc in cc_list if country_counts.get(cc, 0) <= 50]
        if not thin_ccs:
            thin_ccs = cc_list
    orgs = []
    c3 = conn.cursor()
    sub_clause, sub_params = _subregion_clause()
    for cc in thin_ccs:
        sql = (
            "SELECT id, name, country_code, state_province, city, source, "
            "framework_area, alignment_score, description, website, "
            "registration_id, legibility, model_type, tags, email, phone "
            "FROM organizations WHERE status='active' AND country_code=? "
            + sub_clause + ' ORDER BY RANDOM() LIMIT 3'
        )
        c3.execute(sql, [cc] + sub_params)
        orgs.extend([dict(r) for r in c3.fetchall()])
    random.shuffle(orgs)
    orgs = orgs[:args.n]
else:
    # Pure random
    c4 = conn.cursor()
    cc_clause, cc_params = _country_clause()
    sub_clause, sub_params = _subregion_clause()
    sql = (
        "SELECT id, name, country_code, state_province, city, source, "
        "framework_area, alignment_score, description, website, "
        "registration_id, legibility, model_type, tags, email, phone "
        "FROM organizations WHERE status='active' "
        + cc_clause + ' ' + sub_clause + ' '
        + 'ORDER BY RANDOM() LIMIT ?'
    )
    c4.execute(sql, cc_params + sub_params + [args.n])
    orgs = [dict(r) for r in c4.fetchall()]

conn.close()

# Enrich
for o in orgs:
    o['source_label'] = SOURCE_LABELS.get(o.get('source') or '', o.get('source') or '')
    o['section_label'] = SECTION_LABELS.get(o.get('framework_area') or '', o.get('framework_area') or '')
    o['tags_list'] = [t.strip() for t in (o.get('tags') or '').split(',') if t.strip()]
    o['outlier_flags'] = detect_outliers(o, country_counts)
    o['country_total'] = country_counts.get(o.get('country_code') or '', 0)

if args.out:
    out_path = args.out
elif SUBREGION:
    safe_sub = re.sub(r'[^A-Za-z0-9]+', '-', SUBREGION).strip('-').lower() or 'sub'
    out_path = os.path.join(OUT_DIR, f'{args.region}-{safe_sub}.json')
else:
    out_path = os.path.join(OUT_DIR, f'{args.region}.json')
out_path = os.path.abspath(out_path)
os.makedirs(os.path.dirname(out_path), exist_ok=True)

payload = {
    'region': args.region,
    'subregion': SUBREGION or None,
    'label': label + (f' \u2014 {SUBREGION}' if SUBREGION else ''),
    'mode': args.mode,
    'generated': '2026-04-27',
    'total': len(orgs),
    'sections': SECTION_LABELS,
    'orgs': orgs,
}

with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(payload, f, indent=2, ensure_ascii=False)

flag_counts = defaultdict(int)
for o in orgs:
    for fl in o['outlier_flags']:
        flag_counts[fl['type']] += 1

print(f'Written {len(orgs)} orgs to {out_path}')
print(f'Outlier flags: {dict(flag_counts)}')
