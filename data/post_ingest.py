"""
post_ingest.py -- Enforcement gate that runs after every ingest script.

What it does:
  1. Runs audit_pass1 name-pattern exclusions against newly ingested rows
     (or all active rows if --full-scan is passed).
  2. Applies a tiered score cutline per source type.
  3. Applies a Wikidata class blocklist (description-based).
  4. Logs every removal to trim_audit/post-ingest-YYYY-MM-DD.md.

This is the missing enforcement step. Previously, phase2_filter.py scored orgs
but nothing enforced the cutline -- every org went active regardless of score.

Usage:
  python data/post_ingest.py                   # scan recently added rows (24h)
  python data/post_ingest.py --source wikidata # scan a specific source
  python data/post_ingest.py --full-scan       # scan all active rows (slow)
  python data/post_ingest.py --dry-run         # report without writing
"""

import argparse, os, sqlite3, re, sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import DB_PATH, TRIM_AUDIT_DIR

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Trust sources: membership in these networks IS the alignment evidence.
# Never cut by score alone. Still apply name-pattern exclusions.
TRUST_SOURCES = {
    'ica_directory', 'ituc_affiliates', 'construction_coops', 'susy_map',
    'clt_world_map', 'nec_members', 'mutual_aid_hub', 'transition_network',
    'ripess_family', 'habitat_affiliates', 'grounded_solutions', 'manual_curation',
    'ic_directory', 'wikidata_land_trusts', 'wikidata_unions', 'web_research',
}

# Score cutlines per source type.
# Orgs scoring BELOW the cutline are moved to status='removed'.
SCORE_CUTLINES = {
    # Wikidata: high noise, hard cutline at 3
    # Avg score 0.4 -- almost everything below 3 is a library, historical society, or generic NGO
    'wikidata':           3,
    'wikidata_subregion': 3,
    # Bulgaria wikidata: slightly better signal, cut at 2
    'wikidata_bg_npo':    2,
    # National registries: DO NOT cut by score alone.
    # These are pre-filtered at ingest; low scores may reflect scoring gaps
    # (e.g. 'FREE CLINICS OF IOWA' scores 0 despite being framework-aligned).
    # Use name/desc pattern exclusions instead.
    'IRS_EO_BMF':            None,
    'uk_charity_commission': None,
    'acnc_charity_register': None,
    'mapa_oscs_brazil':      None,
    # Other sources: no cutline by default (trust the source filtering at ingest)
    '__default__': None,
}

# Name patterns that indicate off-mission orgs (mirrors audit_pass1.py patterns).
# These are checked against the org name (lowercased).
EXCLUDE_NAME_PATTERNS = [
    # Public/national libraries -- NOT seed libraries, community libraries, or library cooperatives
    # Match: 'national library service', 'public library', 'state library', 'national library of X'
    # Don't match: 'seed library', 'little free library', 'cooperative library'
    r'\b(national|public|state|county|municipal|regional) library\b',
    r'\blibrary service[s]?\b',
    r'\bbiblioteca nacional\b', r'\bbiblioth[eè]que nationale\b',
    r'\bnational bibliothek\b',
    # Fast food / commercial chains (specific brands only)
    r"\bmcdonald'?s?\b", r'\bkfc\b', r'\bburger king\b', r'\bstarbucks\b',
    r'\bdomino.?s pizza\b',
    # Country clubs / exclusive social clubs
    r'\bcountry club\b', r'\byacht club\b', r'\bgolf club\b', r'\bpolo club\b',
    # Cemeteries
    r'\bcemetery (association|inc|corp|district)\b', r'\bfuneral home\b',
    # HOAs
    r'\bhomeowners? association\b', r'\bcondo association\b',
    # Chamber of commerce (not cooperative trade bodies)
    r'\bchamber of commerce\b',
    # Pure religious worship congregations
    r'\bfirst (baptist|methodist|presbyterian|lutheran|evangelical) church\b',
    r'\bassembly of god\b', r'\bgospel (church|fellowship)\b',
    r'\bpentecostal (church|assembly)\b',
]

# Description patterns that are near-certain false positives regardless of score.
# IMPORTANT: only use patterns that unambiguously identify a WRONG org type.
# Generic Wikidata placeholders like "non-governmental organization" or
# "nonprofit organization from India" are NOT exclusion signals -- the org may
# be real and aligned. Use score cutline for those instead.
EXCLUDE_DESC_PATTERNS = [
    r'fast food restaurant',
    r'fast food chain',
    r'accessibility technology company',
    r'\bstate private university\b',
    r'\bcommercial bank\b',
    r'insurance company',
    r'real estate (company|firm|developer)',
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_cutline(source):
    return SCORE_CUTLINES.get(source, SCORE_CUTLINES['__default__'])

def matches_any(text, patterns):
    if not text:
        return None
    low = text.lower().strip()
    for pat in patterns:
        if re.search(pat, low):
            return pat
    return None

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(source_filter=None, full_scan=False, dry_run=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Build query
    if full_scan:
        c.execute("SELECT id, name, source, alignment_score, description, status FROM organizations WHERE status='active'")
    elif source_filter:
        c.execute("SELECT id, name, source, alignment_score, description, status FROM organizations WHERE status='active' AND source=?", [source_filter])
    else:
        # Default: rows added in the last 36 hours
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=36)).isoformat()
        c.execute("SELECT id, name, source, alignment_score, description, status FROM organizations WHERE status='active' AND date_added >= ?", [cutoff])

    orgs = list(c.fetchall())
    print(f'[post_ingest] Checking {len(orgs):,} orgs (dry_run={dry_run})')

    removals = []
    for o in orgs:
        oid    = o['id']
        name   = o['name'] or ''
        source = o['source'] or ''
        score  = o['alignment_score'] if o['alignment_score'] is not None else 0
        desc   = o['description'] or ''
        reason = None

        # 1. Name pattern exclusion (applies to all sources including trust)
        # Exception: if the name also contains 'cooperative', 'mutual', or 'solidarity',
        # a library/university reference may be a cooperative org operating in that space.
        name_lower = name.lower()
        coop_exception = any(kw in name_lower for kw in ('cooperative','co-op','coop','mutual','solidarity','credit union'))
        if not coop_exception:
            pat = matches_any(name, EXCLUDE_NAME_PATTERNS)
            if pat:
                reason = f'name_pattern: {pat}'

        # 2. Description pattern exclusion (trust sources exempt)
        if not reason and source not in TRUST_SOURCES:
            pat = matches_any(desc, EXCLUDE_DESC_PATTERNS)
            if pat:
                reason = f'desc_pattern: {pat}'

        # 3. Score cutline (skip trust sources and sources with None cutline)
        if not reason and source not in TRUST_SOURCES:
            cutline = get_cutline(source)
            if cutline is not None and score < cutline:
                reason = f'score_below_cutline: {score} < {cutline} (source={source})'

        if reason:
            removals.append({'id': oid, 'name': name, 'source': source, 'score': score, 'reason': reason})

    print(f'[post_ingest] {len(removals):,} orgs flagged for removal')

    # Apply removals
    if not dry_run and removals:
        ids = [r['id'] for r in removals]
        # Batch update in chunks of 500
        for i in range(0, len(ids), 500):
            chunk = ids[i:i+500]
            ph = ','.join(['?'] * len(chunk))
            conn.execute(f"UPDATE organizations SET status='removed' WHERE id IN ({ph})", chunk)
        conn.commit()
        print(f'[post_ingest] {len(removals):,} orgs marked status=removed')

    # Write log
    os.makedirs(TRIM_AUDIT_DIR, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    log_path = os.path.join(TRIM_AUDIT_DIR, f'post-ingest-{date_str}.md')

    mode = 'a' if os.path.exists(log_path) else 'w'
    with open(log_path, mode, encoding='utf-8') as f:
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        scope = source_filter or ('full-scan' if full_scan else 'recent-36h')
        f.write(f'\n## Run {now} | scope={scope} | dry_run={dry_run}\n')
        f.write(f'Checked {len(orgs):,} orgs, removed {len(removals):,}\n\n')
        by_reason = {}
        for r in removals:
            key = r['reason'].split(':')[0]
            by_reason.setdefault(key, []).append(r)
        for reason_type, items in sorted(by_reason.items()):
            f.write(f'### {reason_type} ({len(items)})\n')
            for item in items[:20]:
                f.write(f'- [{item["source"]}] score={item["score"]} | {item["name"][:80]}\n')
                if len(items) > 20 and item == items[19]:
                    f.write(f'- ... and {len(items)-20} more\n')
            f.write('\n')

    print(f'[post_ingest] Log written to {log_path}')
    conn.close()
    return len(removals)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default=None)
    parser.add_argument('--full-scan', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    removed = run(source_filter=args.source, full_scan=args.full_scan, dry_run=args.dry_run)
    print(f'[post_ingest] Done. {removed} orgs {"would be" if args.dry_run else "were"} removed.')
