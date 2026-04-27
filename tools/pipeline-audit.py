import sqlite3, os
conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'commonweave_directory.db'))
c = conn.cursor()

print('=== Score dist: wikidata_subregion (should all be filtered) ===')
c.execute("SELECT alignment_score, COUNT(*) as n FROM organizations WHERE source='wikidata_subregion' AND status='active' GROUP BY alignment_score ORDER BY alignment_score")
for r in c.fetchall(): print(f'  score {r[0]}: {r[1]}')

print('\n=== Score dist: wikidata India (status=active) ===')
c.execute("SELECT alignment_score, COUNT(*) as n FROM organizations WHERE source='wikidata' AND status='active' AND country_code='IN' GROUP BY alignment_score ORDER BY alignment_score")
for r in c.fetchall(): print(f'  score {r[0]}: {r[1]}')

print('\n=== Score=0 active orgs -- how many per source? ===')
c.execute("SELECT source, COUNT(*) as n FROM organizations WHERE alignment_score=0 AND status='active' GROUP BY source ORDER BY n DESC")
for r in c.fetchall(): print(f'  {r[0]:<35} {r[1]}')

print('\n=== Avg score by source (ascending -- worst first) ===')
c.execute("SELECT source, MIN(alignment_score), MAX(alignment_score), ROUND(AVG(alignment_score),1), COUNT(*) FROM organizations WHERE status='active' GROUP BY source ORDER BY AVG(alignment_score)")
for r in c.fetchall(): print(f'  {r[0]:<35} min={r[1]} max={r[2]} avg={r[3]} n={r[4]}')

print('\n=== Do ingesters call phase2_filter? Check for phase2 invocations in ingest scripts ===')
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
for fname in sorted(os.listdir(data_dir)):
    if not fname.startswith('ingest_'): continue
    txt = open(os.path.join(data_dir, fname), encoding='utf-8', errors='ignore').read()
    has_phase2 = 'phase2' in txt.lower() or 'alignment_score' in txt
    has_audit  = 'audit_pass' in txt.lower() or 'audit_quality' in txt.lower()
    has_cutline = 'score' in txt and ('< 3' in txt or '<3' in txt or 'MIN_SCORE' in txt or 'cutline' in txt.lower())
    print(f'  {fname:<45} phase2={has_phase2} audit={has_audit} cutline={has_cutline}')

conn.close()
