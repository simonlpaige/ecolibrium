"""
Brazil Mapa das OSCs (IPEA) ingest.

The Mapa das Organizações da Sociedade Civil, run by IPEA, is the most
complete public catalog of Brazilian civil-society organizations: about
860,000 OSCs with CNPJ, legal-form code, primary CNAE activity code, and
IPEA's own area-of-activity classification (assistencia social, saude,
educacao, cultura, desenvolvimento, religiao, etc.). The bulk dataset is
published as a CSV at mapaosc.ipea.gov.br/download/<date>_MOSC_baseresumida.csv,
about 330 MB, refreshed roughly annually.

Two reasons we use this and not the raw Receita Federal CNPJ dump:
  - The Receita CNPJ file is multi-GB, requires assembling several files
    per-state, and lacks the IPEA area classification. The Mapa already
    did the joining work for us.
  - The Mapa pre-tags each row with whether it falls into one or more
    eight IPEA "areas," which lets us pre-filter by purpose without doing
    our own CNAE arithmetic.

Filters applied at ingest time:
  - Skip rows where situacao_cadastral != "Ativa" (only currently-active OSCs)
  - Skip rows whose ONLY area is "Religiao" (pure religious orgs out of
    scope; mixed-area orgs that include religion plus social welfare or
    education stay)
  - Skip rows whose ONLY area is "Associacoes patronais e profissionais"
    (employer / professional associations; equivalents of US chambers of
    commerce)
  - For everything else: keep if natureza_juridica is in the aligned
    legal-form whitelist (3220 Associacao Privada, 3999 Outras Fundacoes,
    2143 Cooperativa, 3069 Organizacao Religiosa as a fallback only when
    the row also has Area_Saude or Area_Educacao or Area_Assistencia, etc.)
    OR the CNAE matches one of the brief's whitelist prefixes (86, 87, 88
    health/social, 85 education, 8130 environmental, 94 associative
    activities, 0113 / 0162 / 03 food and ag co-ops).

Mapping:
  - source        = 'mapa_oscs_brazil'
  - source_id     = CNPJ (14 digits)
  - registration_id = CNPJ
  - registration_type = 'BR_CNPJ'
  - country_code  = 'BR'
  - legibility    = 'formal'
  - description   = razao_social, nome_fantasia (where different),
                    natureza juridica name, CNAE code, IPEA areas hit
  - framework_area derived from IPEA areas (Saude -> healthcare, etc.)
  - model_type    = 'cooperative' for natureza 2143, 'foundation' for 3999,
                    else 'nonprofit'

Re-runs are idempotent on (source='mapa_oscs_brazil', source_id=CNPJ).

Usage:
    python ingest_brazil_oscs.py
    python ingest_brazil_oscs.py --dry-run
    python ingest_brazil_oscs.py --refresh
    python ingest_brazil_oscs.py --limit 5000
    python ingest_brazil_oscs.py --cnae-filter 86,87,88,85,94,01,03  # override default
"""
import argparse
import csv
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from _common import DB_PATH, DATA_DIR, ensure_column

CACHE_DIR = os.path.join(DATA_DIR, 'sources', 'mapa-oscs-cache')
LOG_PATH = os.path.join(DATA_DIR, 'ingest-brazil-oscs-run.log')

USER_AGENT = (
    'Mozilla/5.0 (compatible; Commonweave/1.0; '
    '+https://commonweave.earth; directory@commonweave.earth)'
)
SLEEP_BETWEEN = 1

# This URL is the most recent bulk dump as of 2026-04-25. The dataset name
# encodes the publish date (YYYYMMDD). When IPEA refreshes, update here.
MAPA_CSV_URL = 'https://mapaosc.ipea.gov.br/download/20260310_MOSC_baseresumida.csv'

# Aligned legal-form whitelist. Codes follow Brazil's IBGE Tabela de
# Naturezas Juridicas. Keys are the raw integer code; value is a (label,
# model_type, score_bump) tuple.
LEGAL_FORM_WHITELIST = {
    '2143': ('Cooperativa',                     'cooperative', 1),
    '2240': ('Sociedade Cooperativa de Credito','cooperative', 1),
    '3220': ('Associacao Privada',              'nonprofit',   0),
    '3069': ('Organizacao Religiosa',           'nonprofit',   0),
    '3999': ('Outras Fundacoes ou Associacoes', 'foundation',  0),
    '3204': ('Organizacao Internacional',       'nonprofit',   0),
    '3050': ('Servico Social Autonomo',         'nonprofit',   0),
    '3107': ('Comunidade Indigena',             'nonprofit',   1),
    '3220': ('Associacao Privada',              'nonprofit',   0),
}

# IPEA area columns in the bulk CSV. Each is a 0/1 flag. Mapping into
# Commonweave framework_area is the obvious one.
AREA_COLS = [
    'Area_Assistencia_social',
    'Area_Associacoes_patronais_e_profissionais',
    'Area_Cultura_e_recreacao',
    'Area_Desenvolvimento_e_defesa_de_direitos_e_interesses',
    'Area_Educacao_e_pesquisa',
    'Area_Outras_atividades_associativas',
    'Area_Religiao',
    'Area_Saude',
]
AREA_TO_FRAMEWORK = [
    ('Area_Saude',                                                  'healthcare'),
    ('Area_Educacao_e_pesquisa',                                    'education'),
    ('Area_Assistencia_social',                                     'housing_land'),
    ('Area_Desenvolvimento_e_defesa_de_direitos_e_interesses',      'democracy'),
    ('Area_Cultura_e_recreacao',                                    'recreation_arts'),
    ('Area_Outras_atividades_associativas',                         'cooperatives'),
]

# Default CNAE prefix whitelist (the brief's list, narrowed). The CSV
# exposes CNAE as digits-only (e.g. 86304, 94308). We compare by
# string-prefix. Note: CNAE 94 (generic associative activities) is
# deliberately NOT in the default list because it catches 540k+ rows on
# its own, which would make Brazil dominate the directory. Any row with a
# real purpose (health, education, etc.) is reachable through the IPEA
# area columns instead. Pass --cnae-filter to widen if you want it.
DEFAULT_CNAE_PREFIXES = [
    '86', '87', '88',          # Saude humana / atencao saude / assistencia social
    '85',                       # Educacao
    '8130', '3900',            # Servicos paisagismo / coleta / saneamento
    '0113', '0162', '03',      # Cultivo cereais, atividades de apoio agricultura, pesca/aquicultura
    '0142',                     # Coffee, sugar etc producer cooperatives
]

# Areas IPEA classifies that are aligned with Commonweave's framework.
# Religion and patronal/professional are deliberately not here.
ALIGNED_AREA_COLS = (
    'Area_Saude',
    'Area_Educacao_e_pesquisa',
    'Area_Assistencia_social',
    'Area_Desenvolvimento_e_defesa_de_direitos_e_interesses',
    'Area_Cultura_e_recreacao',
    'Area_Outras_atividades_associativas',
)
# A subset of areas strong enough to keep a row on their own. Saude and
# Educacao are unambiguous purpose signals; the others are kept only when
# at least two are flagged together (a single "Desenvolvimento de direitos"
# flag turns out to also catch generic neighborhood associations, so we
# need a second signal).
STRONG_AREA_COLS = ('Area_Saude', 'Area_Educacao_e_pesquisa')


def cache_csv_path(url):
    os.makedirs(CACHE_DIR, exist_ok=True)
    fname = url.rsplit('/', 1)[-1]
    return os.path.join(CACHE_DIR, fname)


def http_get_streaming(url, dest_path):
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'text/csv,application/octet-stream',
    })
    tmp = dest_path + '.partial'
    with urllib.request.urlopen(req, timeout=300) as resp, open(tmp, 'wb') as out:
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            out.write(chunk)
    os.replace(tmp, dest_path)


def fetch_csv(url, refresh=False):
    path = cache_csv_path(url)
    if not refresh and os.path.exists(path) and os.path.getsize(path) > 1024:
        print(f'  Using cached Mapa CSV: {path} ({os.path.getsize(path):,} bytes)')
        return path
    print(f'  Downloading Mapa OSCs CSV from {url}')
    try:
        http_get_streaming(url, path)
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
    return (value or '').strip() == '1'


def derive_framework_area(row):
    """Pick the strongest IPEA-area signal as framework_area."""
    for col, area in AREA_TO_FRAMEWORK:
        if is_yes(row.get(col, '')):
            return area
    return ''


def is_pure_religion(row):
    """True when Religiao is the only flagged area."""
    if not is_yes(row.get('Area_Religiao', '')):
        return False
    other = [c for c in AREA_COLS if c not in ('Area_Religiao',)]
    return not any(is_yes(row.get(c, '')) for c in other)


def is_pure_patronal(row):
    """True when patronal/professional associations is the only area."""
    if not is_yes(row.get('Area_Associacoes_patronais_e_profissionais', '')):
        return False
    other = [c for c in AREA_COLS if c != 'Area_Associacoes_patronais_e_profissionais']
    return not any(is_yes(row.get(c, '')) for c in other)


def cnae_matches(cnae_text, prefixes):
    """Return True if any prefix matches the row's primary CNAE code."""
    cnae = (cnae_text or '').strip()
    if not cnae:
        return False
    return any(cnae.startswith(p) for p in prefixes)


def keep_row(row, cnae_prefixes):
    """Decide whether a row clears the alignment pre-filter.

    The shape of the data: ~672k active OSCs, of which ~226k are pure
    religion, ~28k are pure patronal/professional, and the remaining ~418k
    are spread across IPEA areas. The brief asks for ~30-60k aligned rows,
    so the filter has to be tighter than "any aligned area set."

    Logic:
      1. Status must be Ativa.
      2. Drop pure religion and pure patronal as the brief requires.
      3. Cooperatives (2143/2240) are kept on the legal-form signal alone.
         (The Mapa today has zero of these; they are regulated separately
         in Brazil. Kept here so the code is correct if Mapa adds them.)
      4. Otherwise the row needs a strong purpose signal:
         - Area_Saude or Area_Educacao_e_pesquisa (single flag is fine
           because health and education are unambiguous), OR
         - At least 2 of the aligned IPEA areas flagged together
           (one alone, especially "Desenvolvimento e defesa de direitos,"
           also catches generic neighborhood associations), OR
         - A CNAE prefix match (the explicit health/education/environment
           codes from the brief).
    """
    if (row.get('situacao_cadastral') or '').strip() != 'Ativa':
        return False
    if is_pure_religion(row):
        return False
    if is_pure_patronal(row):
        return False
    nat = (row.get('natureza_juridica') or '').strip()
    if nat not in LEGAL_FORM_WHITELIST:
        return False
    if nat in ('2143', '2240'):
        return True

    has_strong_area = any(is_yes(row.get(c, '')) for c in STRONG_AREA_COLS)
    aligned_area_count = sum(1 for c in ALIGNED_AREA_COLS if is_yes(row.get(c, '')))
    in_cnae = cnae_matches(row.get('cnae'), cnae_prefixes)

    if has_strong_area:
        return True
    if aligned_area_count >= 2:
        return True
    if in_cnae:
        return True
    return False


def derive_description(row):
    parts = []
    razao = (row.get('tx_razao_social_osc') or '').strip()
    fantasia = (row.get('tx_nome_fantasia_osc') or '').strip()
    if fantasia and fantasia != razao:
        parts.append(f'Nome fantasia: {fantasia}')
    nat = (row.get('natureza_juridica') or '').strip()
    if nat in LEGAL_FORM_WHITELIST:
        label, _, _ = LEGAL_FORM_WHITELIST[nat]
        parts.append(f'Natureza juridica: {label}')
    cnae = (row.get('cnae') or '').strip()
    if cnae:
        parts.append(f'CNAE primaria: {cnae}')
    areas = [
        col.replace('Area_', '').replace('_', ' ')
        for col in AREA_COLS
        if is_yes(row.get(col, ''))
    ]
    if areas:
        parts.append('Areas IPEA: ' + ', '.join(areas))
    return '. '.join(parts)


def derive_model_type(row):
    nat = (row.get('natureza_juridica') or '').strip()
    if nat in LEGAL_FORM_WHITELIST:
        _, model_type, _ = LEGAL_FORM_WHITELIST[nat]
        return model_type
    return 'nonprofit'


def fix_mojibake(text):
    """The Mapa CSV stores Portuguese characters in latin-1 inside a
    nominally UTF-8 file, so e.g. SAO PAULO becomes 'S\xc3O PAULO'. We
    re-encode through latin-1 -> utf-8 to repair that. Cheap and lossless
    for ASCII rows."""
    if not text:
        return ''
    try:
        return text.encode('latin-1', 'ignore').decode('utf-8', 'ignore') or text
    except Exception:
        return text


def parse_address(row):
    """Pull city / state out of the row."""
    city = fix_mojibake((row.get('municipio_nome') or '').strip())
    state = (row.get('UF_Sigla') or '').strip()
    return city, state


def parse_rows(csv_path, cnae_prefixes, limit=None):
    """Iterate the CSV, applying the alignment pre-filter, and yield row
    dicts. Bytes are decoded with errors='replace' since Mapa OSC ships
    mixed-encoding cells."""
    kept = 0
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if not keep_row(row, cnae_prefixes):
                continue
            kept += 1
            yield row
            if limit and kept >= limit:
                return


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
    for row in rows:
        cnpj = (row.get('cnpj') or '').strip()
        razao = fix_mojibake((row.get('tx_razao_social_osc') or '').strip())
        if not cnpj or not razao:
            continue

        city, state = parse_address(row)
        framework = derive_framework_area(row)
        model_type = derive_model_type(row)
        description = fix_mojibake(derive_description(row))
        evidence = f'https://mapaosc.ipea.gov.br/osc/{row.get("id_osc","")}'.strip('/')

        nat = (row.get('natureza_juridica') or '').strip()
        # Score: 2 baseline; 3 for cooperatives or rows with multiple area
        # flags hit (richer purpose signal).
        area_hits = sum(1 for col in AREA_COLS if is_yes(row.get(col, '')))
        score = 2
        if nat in ('2143', '2240'):
            score = 3
        elif area_hits >= 2:
            score = 3

        if dry_run:
            inserted += 1
            continue

        c.execute(
            "SELECT id FROM organizations WHERE source=? AND source_id=?",
            ('mapa_oscs_brazil', cnpj),
        )
        existing = c.fetchone()
        if existing:
            c.execute(
                """UPDATE organizations
                   SET name=?,
                       country_code='BR', country_name='Brazil',
                       state_province=COALESCE(NULLIF(state_province,''), ?),
                       city=COALESCE(NULLIF(city,''), ?),
                       registration_id=?,
                       registration_type=?,
                       description=COALESCE(NULLIF(description,''), ?),
                       framework_area=COALESCE(NULLIF(framework_area,''), ?),
                       model_type=?,
                       alignment_score=MAX(COALESCE(alignment_score,0), ?),
                       evidence_url=COALESCE(NULLIF(evidence_url,''), ?),
                       evidence_fetched_at=?,
                       legibility='formal'
                   WHERE id=?""",
                (
                    razao, state, city,
                    cnpj, 'BR_CNPJ',
                    description, framework, model_type, score,
                    evidence, now, existing[0],
                ),
            )
            updated += 1
        else:
            c.execute(
                """INSERT OR IGNORE INTO organizations
                   (name, country_code, country_name, state_province, city,
                    registration_id, registration_type, description,
                    source, source_id,
                    framework_area, model_type, alignment_score,
                    status, date_added,
                    legibility, evidence_url, evidence_fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?)""",
                (
                    razao, 'BR', 'Brazil', state, city,
                    cnpj, 'BR_CNPJ', description,
                    'mapa_oscs_brazil', cnpj,
                    framework, model_type, score,
                    now,
                    'formal', evidence, now,
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
        f.write(f'\n# ingest_brazil_oscs run - {today}\n\n')
        for line in lines:
            f.write(line + '\n')


def main():
    ap = argparse.ArgumentParser(description='Brazil Mapa das OSCs ingest')
    ap.add_argument('--dry-run', action='store_true', help='Parse + count, no writes')
    ap.add_argument('--refresh', action='store_true', help='Ignore cache, re-download')
    ap.add_argument('--limit', type=int, default=0, help='Cap kept rows (0 = all)')
    ap.add_argument('--cnae-filter', type=str, default='',
                    help='Override default CNAE prefix list. Comma-separated.')
    args = ap.parse_args()

    cnae_prefixes = (
        [p.strip() for p in args.cnae_filter.split(',') if p.strip()]
        if args.cnae_filter else DEFAULT_CNAE_PREFIXES
    )
    print(f"{'[DRY RUN] ' if args.dry_run else ''}Ingesting Brazil OSCs from Mapa das OSCs (IPEA)")
    print(f'  CNAE prefix whitelist: {cnae_prefixes}')
    print(f'  Aligned legal forms: {sorted(LEGAL_FORM_WHITELIST.keys())}')

    csv_path = fetch_csv(MAPA_CSV_URL, refresh=args.refresh)
    if not csv_path:
        print('  FATAL: could not obtain Mapa OSCs CSV. Stopping.')
        sys.exit(1)

    print('  Parsing CSV (this scans ~860k rows; only kept rows are loaded)')
    kept_rows = list(parse_rows(csv_path, cnae_prefixes, limit=args.limit or None))
    print(f'  Kept after pre-filter: {len(kept_rows):,}')

    db = sqlite3.connect(DB_PATH)
    run_migration(db)
    inserted, updated = upsert(db, kept_rows, dry_run=args.dry_run)
    db.close()

    mode = '[DRY RUN] Would insert' if args.dry_run else 'Inserted'
    summary = [
        f"Mode: {'dry-run' if args.dry_run else 'real'}",
        f"Source CSV: {MAPA_CSV_URL}",
        f"Rows kept after pre-filter: {len(kept_rows)}",
        f"{mode}: {inserted}",
        f"Updated: {updated}",
        f"CNAE prefixes used: {','.join(cnae_prefixes)}",
        f"Legal forms used: {','.join(sorted(LEGAL_FORM_WHITELIST.keys()))}",
    ]
    print('\n' + '\n'.join(summary))
    write_log(summary)
    print(f'\nLog appended: {LOG_PATH}')


if __name__ == '__main__':
    main()
