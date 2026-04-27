import sqlite3, os
conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'commonweave_directory.db'))
c = conn.cursor()
TRUST = ('ica_directory','ituc_affiliates','construction_coops','susy_map',
         'clt_world_map','nec_members','mutual_aid_hub','transition_network',
         'ripess_family','habitat_affiliates','grounded_solutions','manual_curation',
         'ic_directory','wikidata_land_trusts','wikidata_unions')
ph = ','.join(['?' for _ in TRUST])
c.execute(f"SELECT COUNT(*) FROM organizations WHERE status='active' AND alignment_score < 3 AND source NOT IN ({ph})", TRUST)
print('Would be removed by score<3 cutline (non-trust sources):', c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM organizations WHERE status='active' AND alignment_score = 0")
print('Score=0 active total:', c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM organizations WHERE status='active'")
print('Total active:', c.fetchone()[0])
conn.close()
