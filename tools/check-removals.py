"""Check what post_ingest.py would remove, broken down by reason type and source."""
import sqlite3, re, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data'))
from post_ingest import TRUST_SOURCES, SCORE_CUTLINES, EXCLUDE_NAME_PATTERNS, EXCLUDE_DESC_PATTERNS, matches_any, get_cutline

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'commonweave_directory.db')
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT id, name, source, alignment_score, description, framework_area FROM organizations WHERE status='active'")
orgs = list(c.fetchall())
conn.close()

removals = {'name_pattern': [], 'desc_pattern': [], 'score_below_cutline': []}
for o in orgs:
    name   = o['name'] or ''
    source = o['source'] or ''
    score  = o['alignment_score'] if o['alignment_score'] is not None else 0
    desc   = o['description'] or ''
    reason = None
    pat = matches_any(name, EXCLUDE_NAME_PATTERNS)
    if pat: reason = ('name_pattern', pat)
    if not reason:
        pat = matches_any(desc, EXCLUDE_DESC_PATTERNS)
        if pat: reason = ('desc_pattern', pat)
    if not reason and source not in TRUST_SOURCES:
        cutline = get_cutline(source)
        if score < cutline: reason = ('score_below_cutline', f'score={score} cutline={cutline}')
    if reason:
        removals[reason[0]].append({'name': name, 'source': source, 'score': score,
                                    'area': o['framework_area'], 'desc': str(desc)[:100], 'why': reason[1]})

for rtype, items in removals.items():
    print(f'\n=== {rtype}: {len(items)} ===')
    for item in items[:15]:
        print(f'  [{item["source"]}] score={item["score"]} area={item["area"]} | {item["name"][:55]}')
        print(f'    why: {item["why"]}')
        if item["desc"]: print(f'    desc: {item["desc"][:80]}')
