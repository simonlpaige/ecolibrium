"""
Phase 2: Second-pass alignment filter + model_type classification.
Scores every active org and sets alignment_score and model_type.
"""
import sqlite3

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'

STRONG_POS = [
    'cooperative','co-op','coop','worker-owned','community land trust',
    'mutual aid','food bank','food pantry','food shelf','habitat for humanity',
    'legal aid','civil rights','indigenous','agroecol','solidarity economy',
    'restorative justice','renewable energy','community health center',
    'free clinic','community health','environmental justice',
    'tenant rights','affordable housing','community garden',
    'seed library','food sovereignty','participatory','civic tech',
    'worker cooperative','credit union','housing cooperative',
    # non-western + semantic expansion 2026-04-17
    'ejido','cooperativa','coopérative','solidaridad',
    'gotong-royong','gotong royong','waqf','minga','genossenschaft',
    "sharikat ta'awuniya",'sociedad cooperativa','société coopérative',
    'collective','employee-owned',
]

MODERATE_POS = [
    'community','environmental','ecology','conservation','health','education',
    'housing','food','energy','justice','rights','youth','women','refugee',
    'immigrant','disability','mental health','arts','culture','literacy',
    'workforce development','job training','urban farm','garden','watershed',
    'climate','biodiversity','human rights','social justice','public interest',
]

NEGATIVE = [
    'church','chapel','cathedral','parish','diocese','synagogue','mosque',
    'temple','ministry','congregation','fraternal order','golf club',
    'country club','homeowners association',' hoa ','booster club',' pta ',
    'vfw post','american legion','rotary club','lions club','kiwanis',
    'elks lodge','moose lodge','political action committee',' pac ',
    'cemetery','mausoleum','prep school','preparatory academy',
    'country day school','athletic association','sports association',
]

MODEL_TYPE_SIGNALS = {
    'cooperative': ['cooperative','co-op','coop','worker-owned','worker owned'],
    'mutual_aid': ['mutual aid','mutual benefit','mutual insurance'],
    'foundation': ['foundation','endowment','charitable trust'],
    'research': ['institute','research','center for','centre for','studies','laboratory'],
    'federation': ['federation','alliance','coalition','network','association of','league of','council of'],
    'education_inst': ['university','college','school','academy','polytechnic'],
    'government': ['authority','district','department of','bureau of','commission'],
}


def score_org(name, desc):
    combined = ((name or '') + ' ' + (desc or '')).lower()
    score = 0
    for kw in STRONG_POS:
        if kw in combined:
            score += 3
    for kw in MODERATE_POS:
        if kw in combined:
            score += 1
    for kw in NEGATIVE:
        if kw in combined:
            score -= 3
    return max(-10, min(10, score))


def get_model_type(name):
    name_lower = (name or '').lower()
    for mtype, signals in MODEL_TYPE_SIGNALS.items():
        for sig in signals:
            if sig in name_lower:
                return mtype
    return 'nonprofit'


def run():
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    
    c.execute("SELECT COUNT(*) FROM organizations WHERE status='active'")
    total = c.fetchone()[0]
    print(f'Active orgs to process: {total:,}')
    
    batch_size = 20000
    offset = 0
    processed = 0
    
    score_buckets = {}
    model_type_counts = {}
    removed_count = 0
    
    while True:
        c.execute("""
            SELECT id, name, description
            FROM organizations
            WHERE status='active'
            ORDER BY id
            LIMIT ? OFFSET ?
        """, (batch_size, offset))
        rows = c.fetchall()
        if not rows:
            break
        
        updates_active = []
        updates_downgrade = []
        updates_remove = []
        
        for row in rows:
            org_id, name, desc = row
            score = score_org(name, desc)
            mtype = get_model_type(name)
            
            score_buckets[score] = score_buckets.get(score, 0) + 1
            model_type_counts[mtype] = model_type_counts.get(mtype, 0) + 1
            
            if score >= 2:
                updates_active.append((score, mtype, org_id))
            elif score >= 0:
                updates_downgrade.append((score, mtype, org_id))
            else:
                updates_remove.append((score, mtype, org_id))
                removed_count += 1
        
        if updates_active:
            c.executemany(
                "UPDATE organizations SET alignment_score=?, model_type=?, status='active', verified=1 WHERE id=?",
                updates_active
            )
        if updates_downgrade:
            c.executemany(
                "UPDATE organizations SET alignment_score=?, model_type=?, status='active', verified=0 WHERE id=?",
                updates_downgrade
            )
        if updates_remove:
            c.executemany(
                "UPDATE organizations SET alignment_score=?, model_type=?, status='removed' WHERE id=?",
                updates_remove
            )
        
        db.commit()
        processed += len(rows)
        print(f'  Processed {processed:,}/{total:,}')
        offset += batch_size
    
    db.close()
    
    print('\n=== Phase 2 Complete ===')
    print(f'Removed: {removed_count:,}')
    
    print('\nScore distribution (top ranges):')
    for score in sorted(score_buckets.keys(), reverse=True):
        print(f'  score {score:3d}: {score_buckets[score]:,}')
    
    print('\nModel type distribution:')
    for mtype, cnt in sorted(model_type_counts.items(), key=lambda x: -x[1]):
        print(f'  {mtype}: {cnt:,}')


if __name__ == '__main__':
    run()
