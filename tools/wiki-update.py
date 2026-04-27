"""
wiki-update.py -- Keep the Commonweave GitHub wiki in sync with the live DB.

Pulls stats from the SQLite DB, rewrites the dynamic sections of:
  - Home.md          (status table)
  - Data-and-Directory.md  (source table + summary numbers)

Then commits and pushes the wiki repo.

Usage:
  python tools/wiki-update.py [--dry-run] [--wiki-path <path>]

Wiki repo is expected at: C:/Users/simon/commonweave.wiki
Clone it first if it doesn't exist:
  git clone https://github.com/simonlpaige/commonweave.wiki.git C:/Users/simon/commonweave.wiki
"""

import subprocess, sys, os, re, datetime, sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'commonweave_directory.db')

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM organizations WHERE status='active'")
    active = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT country_code) FROM organizations WHERE status='active' AND country_code != ''")
    countries = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM organizations WHERE status='active' AND lat IS NOT NULL AND lon IS NOT NULL")
    geocoded = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM organizations WHERE status='active' AND alignment_score >= 5")
    score5 = c.fetchone()[0]
    c.execute("SELECT source, COUNT(*) as n FROM organizations WHERE status='active' GROUP BY source ORDER BY n DESC")
    sources = c.fetchall()
    conn.close()
    return dict(active=active, countries=countries, geocoded=geocoded, score5=score5, sources=sources)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

WIKI_PATH = os.environ.get('WIKI_PATH', r'C:\Users\simon\commonweave.wiki')

DRY_RUN = '--dry-run' in sys.argv
if '--wiki-path' in sys.argv:
    idx = sys.argv.index('--wiki-path')
    WIKI_PATH = sys.argv[idx + 1]

# Human-readable source name map
SOURCE_LABELS = {
    'mapa_oscs_brazil':      ('Mapa das OSCs (Brazil)',            'Public / IPEA'),
    'acnc_charity_register': ('ACNC Charity Register (Australia)', 'Open Government'),
    'uk_charity_commission': ('UK Charity Commission',             'Open Government Licence v3'),
    'IRS_EO_BMF':            ('IRS Exempt Organizations BMF',      'US Gov public domain'),
    'mutual_aid_wiki':       ('Mutual Aid Wiki',                   'CC BY-NC-SA'),
    'wikidata':              ('Wikidata',                          'CC0'),
    'wikidata_bg_npo':       ('Wikidata Bulgaria NPOs',            'CC0'),
    'ic_directory':          ('Foundation for Intentional Community', '-'),
    'transition_network':    ('Transition Network',                'ODbL'),
    'mutual_aid_hub':        ('Mutual Aid Hub',                    'PDDL-1.0'),
    'susy_map':              ('SUSY Map',                          'Public Domain'),
    'ProPublica':            ('ProPublica Nonprofit Explorer',     'Public (IRS)'),
    'wikidata_subregion':    ('Wikidata (subregion)',              'CC0'),
    'wikidata_land_trusts':  ('Wikidata (land trusts)',            'CC0'),
    'clt_world_map':         ('Schumacher CLT World Map',          '-'),
    'wikidata_unions':       ('Wikidata (labor unions)',           'CC0'),
    'ica_directory':         ('ICA member directory',              'Open'),
    'ituc_affiliates':       ('ITUC affiliates',                   '-'),
    'nec_members':           ('New Economy Coalition members',     '-'),
    'construction_coops':    ('Construction coops',                '-'),
    'ripess_family':         ('RIPESS family',                     '-'),
    'habitat_affiliates':    ('Habitat affiliates',                '-'),
    'web_research':          ('Web research',                      '-'),
    'grounded_solutions':    ('Grounded Solutions',                '-'),
    'manual_curation':       ('Manual curation',                   '-'),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def replace_block(text, start_marker, end_marker, new_block):
    """Replace content between start_marker and end_marker (inclusive)."""
    pattern = re.compile(
        re.escape(start_marker) + r'.*?' + re.escape(end_marker),
        re.DOTALL
    )
    replacement = start_marker + '\n' + new_block.strip() + '\n' + end_marker
    result, n = pattern.subn(replacement, text)
    if n == 0:
        # markers not found -- append
        result = text.rstrip() + '\n\n' + replacement + '\n'
    return result

def run(cmd, cwd=WIKI_PATH):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f'[error] {" ".join(cmd)}: {result.stderr.strip()}')
        sys.exit(1)
    return result.stdout.strip()

# ---------------------------------------------------------------------------
# Build blocks
# ---------------------------------------------------------------------------

def build_home_status_table(s):
    date_str = datetime.date.today().strftime('%B %Y')
    return f"""| Metric | Count |
|--------|-------|
| Active organizations | {s['active']:,} |
| Countries covered | {s['countries']} |
| Data sources | {len(s['sources'])} |
| Framework alignment score >= 5 | ~{s['score5']:,} |
| Geocoded entries | ~{s['geocoded']:,} |

*Last updated: {date_str}*"""

def build_source_table(s):
    header = "| Source | Records | License |\n|--------|--------:|---------|\n"
    rows = []
    for source_key, count in s['sources']:
        label, license_ = SOURCE_LABELS.get(source_key, (source_key, '-'))
        rows.append(f"| {label} | {count:,} | {license_} |")
    return header + '\n'.join(rows)

def build_data_summary(s):
    top = s['sources'][:3]
    top_str = ', '.join(
        f"{SOURCE_LABELS.get(k, (k,))[0]} ~{n:,}"
        for k, n in top
    )
    return (
        f"- **{s['active']:,} active organizations** across {s['countries']} countries\n"
        f"- Top sources: {top_str}\n"
        f"- **~{s['score5']:,}** score >= 5 on framework alignment (strongest matches)\n"
        f"- **~{s['geocoded']:,}** geocoded entries"
    )

# ---------------------------------------------------------------------------
# Update files
# ---------------------------------------------------------------------------

START_STATUS  = '<!-- wiki:status-table:start -->'
END_STATUS    = '<!-- wiki:status-table:end -->'
START_SOURCES = '<!-- wiki:source-table:start -->'
END_SOURCES   = '<!-- wiki:source-table:end -->'
START_SUMMARY = '<!-- wiki:data-summary:start -->'
END_SUMMARY   = '<!-- wiki:data-summary:end -->'

def update_home(s):
    path = os.path.join(WIKI_PATH, 'Home.md')
    text = open(path, encoding='utf-8').read()
    text = replace_block(text, START_STATUS, END_STATUS, build_home_status_table(s))
    if not DRY_RUN:
        open(path, 'w', encoding='utf-8').write(text)
    else:
        print('[dry-run] Home.md would be updated')

def update_data_page(s):
    path = os.path.join(WIKI_PATH, 'Data-and-Directory.md')
    text = open(path, encoding='utf-8').read()
    text = replace_block(text, START_SUMMARY, END_SUMMARY, build_data_summary(s))
    text = replace_block(text, START_SOURCES, END_SOURCES, build_source_table(s))
    if not DRY_RUN:
        open(path, 'w', encoding='utf-8').write(text)
    else:
        print('[dry-run] Data-and-Directory.md would be updated')

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def rebuild_map_stats():
    """Regenerate data/map/stats.json from the live DB."""
    script = os.path.join(SCRIPT_DIR, '..', 'data', 'build_map_v2.py')
    if not os.path.exists(script):
        print('[wiki-update] build_map_v2.py not found, skipping map stats rebuild')
        return
    print('[wiki-update] Rebuilding data/map/stats.json...')
    result = subprocess.run(
        ['python', script],
        cwd=os.path.join(SCRIPT_DIR, '..'),
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f'[wiki-update] map rebuild warning: {result.stderr.strip()[-200:]}')
    else:
        print('[wiki-update] map stats rebuilt')


def main():
    print('[wiki-update] Pulling stats from DB...')
    s = get_stats()
    print(f"  active={s['active']:,}  countries={s['countries']}  geocoded={s['geocoded']:,}  score5+={s['score5']:,}")

    if not os.path.isdir(WIKI_PATH):
        print(f'[error] Wiki path not found: {WIKI_PATH}')
        print('  Clone it first: git clone https://github.com/simonlpaige/commonweave.wiki.git')
        sys.exit(1)

    if not DRY_RUN:
        rebuild_map_stats()

    print('[wiki-update] Pulling latest wiki from GitHub...')
    if not DRY_RUN:
        run(['git', 'pull', '--rebase'])

    print('[wiki-update] Updating Home.md...')
    update_home(s)

    print('[wiki-update] Updating Data-and-Directory.md...')
    update_data_page(s)

    if DRY_RUN:
        print('[dry-run] Done. No files written, no git push.')
        return

    # Check if anything changed
    diff = run(['git', 'diff', '--stat'])
    if not diff:
        print('[wiki-update] No changes. Wiki already up to date.')
        return

    date_str = datetime.date.today().isoformat()
    msg = f'auto: wiki stats update {date_str} ({s["active"]:,} orgs / {s["countries"]} countries)'
    run(['git', 'add', 'Home.md', 'Data-and-Directory.md'])
    run(['git', 'commit', '-m', msg])
    run(['git', 'push'])
    print(f'[wiki-update] Pushed: {msg}')

if __name__ == '__main__':
    main()
