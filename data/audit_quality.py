"""
Audit the Ecolibrium database for off-mission organizations.
Sample random orgs and check alignment. Also scan for known bad patterns.
"""
import sqlite3
import random

db = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db')
c = db.cursor()

# Known patterns that should NOT be in the dataset
EXCLUDE_PATTERNS = [
    # Religious (unless social service arm)
    'church', 'parish', 'diocese', 'synagogue', 'mosque', 'temple',
    'chapel', 'congregation', 'ministry', 'baptist', 'methodist',
    'lutheran', 'presbyterian', 'pentecostal', 'evangelical',
    'catholic charities',  # keep this one actually
    'bible', 'gospel', 'worship',
    
    # Social clubs / recreation that isn't community infrastructure
    'golf club', 'country club', 'yacht club', 'polo club',
    'tennis club', 'swim club', 'garden club', 'bridge club',
    'rotary club', 'lions club', 'kiwanis', 'elks lodge',
    'moose lodge', 'eagles lodge', 'vfw post', 'american legion',
    'masonic', 'freemason', 'odd fellows', 'knights of columbus',
    'shriners', 'fraternal order',
    
    # HOAs and property
    'homeowners association', 'hoa', 'condo association',
    'property owners', 'neighborhood association',
    
    # Booster clubs and school parent orgs
    'booster club', 'boosters', 'pta', 'pto',
    'parent teacher', 'alumni association',
    
    # Cemetery
    'cemetery', 'funeral', 'memorial park', 'burial',
    
    # Pet/animal hobby (not conservation)
    'kennel club', 'cat club', 'dog club', 'breed club',
    'horse show', 'pony club', 'rodeo',
    
    # Professional associations (not civil society)
    'bar association', 'medical association', 'dental association',
    'real estate association', 'chamber of commerce',
    'trade association', 'industry association',
    
    # Political parties and PACs
    'republican party', 'democratic party', 'political action',
    'pac', 'super pac', 'campaign committee',
]

# Count matches for each pattern
print("=== CONTAMINATION SCAN ===\n")
total_contaminated = 0
pattern_counts = []

for pattern in EXCLUDE_PATTERNS:
    c.execute(
        "SELECT COUNT(*) FROM organizations WHERE status != 'removed' AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ?)",
        (f'%{pattern}%', f'%{pattern}%')
    )
    count = c.fetchone()[0]
    if count > 0:
        pattern_counts.append((pattern, count))
        total_contaminated += count

pattern_counts.sort(key=lambda x: x[1], reverse=True)
for pattern, count in pattern_counts[:30]:
    print(f"  {pattern:<35} {count:>8,}")

print(f"\n  TOTAL contaminated (with overlap): {total_contaminated:,}")

# Get total
c.execute("SELECT COUNT(*) FROM organizations WHERE status != 'removed'")
total = c.fetchone()[0]
print(f"  Total active orgs:                 {total:,}")
print(f"  Estimated contamination rate:      ~{total_contaminated/total*100:.1f}%")

# Random sample of 20 orgs to eyeball
print("\n=== RANDOM SAMPLE (20 orgs) ===\n")
c.execute("SELECT name, country_code, framework_area, alignment_score FROM organizations WHERE status != 'removed' ORDER BY RANDOM() LIMIT 20")
for name, cc, area, score in c.fetchall():
    flag = " *** SUSPECT" if score and score < 0 else ""
    print(f"  [{cc}] {area or '?':<20} score={score or 0:>2}  {name[:80]}{flag}")

# Alignment score distribution
print("\n=== ALIGNMENT SCORE DISTRIBUTION ===\n")
c.execute("""
    SELECT alignment_score, COUNT(*) 
    FROM organizations 
    WHERE status != 'removed' 
    GROUP BY alignment_score 
    ORDER BY alignment_score
""")
for score, count in c.fetchall():
    bar = '#' * min(50, count // 1000)
    print(f"  score={score or 0:>3}: {count:>8,}  {bar}")

db.close()
