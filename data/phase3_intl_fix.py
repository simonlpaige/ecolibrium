"""
Phase 3: Fix international orgs + delete P2 junk.
1. Delete all orgs where country_code='P2'
2. For all active web_research orgs where framework_area IS NULL:
   Assign framework_area from description+name keywords
"""
import sqlite3

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'

FRAMEWORK_KEYWORDS = {
    'healthcare': ['health','clinic','hospital','medical','medicine','nurse','doctor','hiv','aids','malaria','maternal'],
    'food': ['food','farm','agri','seed','nutrition','hunger','crop','livestock','agroecol','permaculture','harvest'],
    'education': ['education','school','learn','literacy','teach','curriculum','library','university','college','training'],
    'ecology': ['environment','ecology','conservation','climate','biodiversity','forest','ocean','watershed','rewild','wildlife','restoration'],
    'housing_land': ['housing','shelter','land trust','tenure','homeless','eviction','affordable housing','community land'],
    'democracy': ['democracy','civic','governance','participat','voting','election','transparency','accountability','human rights','civil liberties'],
    'cooperatives': ['cooperative','co-op','worker-owned','mutual','solidarity economy','credit union','social enterprise'],
    'energy_digital': ['energy','solar','wind','renewable','digital','open source','internet','data','technology'],
    'conflict': ['justice','conflict','mediation','reconciliation','peace','restorative','prison','abolition','transitional'],
    'recreation_arts': ['arts','culture','recreation','sport','music','theater','museum','heritage','creative'],
}


def assign_framework_area(name, desc):
    combined = ((name or '') + ' ' + (desc or '')).lower()
    best_area = None
    best_score = 0
    for area, keywords in FRAMEWORK_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > best_score:
            best_score = score
            best_area = area
    return best_area or 'democracy'


def run():
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    
    # 1. Delete P2 orgs
    c.execute("SELECT COUNT(*) FROM organizations WHERE country_code='P2'")
    p2_count = c.fetchone()[0]
    c.execute("DELETE FROM organizations WHERE country_code='P2'")
    db.commit()
    print(f'Deleted {p2_count} P2 orgs')
    
    # 2. Assign framework_area for active web_research orgs where it's NULL
    c.execute("""
        SELECT COUNT(*) FROM organizations 
        WHERE status='active' AND source='web_research' AND framework_area IS NULL
    """)
    null_count = c.fetchone()[0]
    print(f'Active web_research orgs with NULL framework_area: {null_count}')
    
    # Process in batches
    batch_size = 5000
    offset = 0
    total_assigned = 0
    area_counts = {}
    
    while True:
        c.execute("""
            SELECT id, name, description
            FROM organizations
            WHERE status='active' AND source='web_research' AND framework_area IS NULL
            ORDER BY id
            LIMIT ?
        """, (batch_size,))
        rows = c.fetchall()
        if not rows:
            break
        
        updates = []
        for row in rows:
            org_id, name, desc = row
            area = assign_framework_area(name, desc)
            updates.append((area, org_id))
            area_counts[area] = area_counts.get(area, 0) + 1
        
        c.executemany("UPDATE organizations SET framework_area=? WHERE id=?", updates)
        db.commit()
        total_assigned += len(updates)
        print(f'  Assigned framework_area to {total_assigned} orgs so far...')
    
    print(f'\n=== Phase 3 Complete ===')
    print(f'P2 orgs deleted: {p2_count}')
    print(f'framework_area assigned: {total_assigned}')
    print('\nFramework area distribution for assigned:')
    for area, cnt in sorted(area_counts.items(), key=lambda x: -x[1]):
        print(f'  {area}: {cnt}')
    
    # Final stats
    c.execute("SELECT COUNT(*) FROM organizations WHERE status='active'")
    active = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM organizations")
    total = c.fetchone()[0]
    print(f'\nDB totals: active={active:,}, total={total:,}')
    
    db.close()


if __name__ == '__main__':
    run()
