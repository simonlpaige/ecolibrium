"""
Pass 2: Strict alignment re-scoring.
Orgs must have at least ONE strong positive signal to survive.
Zero-signal orgs are excluded as 'excluded_audit_p2'.
"""
import sqlite3

db = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db')
c = db.cursor()

c.execute("SELECT COUNT(*) FROM organizations WHERE status NOT IN ('removed', 'excluded_audit_p1')")
before = c.fetchone()[0]
print(f"Starting Pass 2 with {before:,} orgs\n")

# Strong positive signals - org MUST match at least one to stay
STRONG_POSITIVE = [
    # Cooperative / solidarity economy
    'cooperative', 'co-op', 'coop ', 'worker-owned', 'worker owned',
    'mutual aid', 'solidarity economy', 'solidarity fund',
    'credit union', 'social enterprise', 'fair trade',
    'microfinance', 'microcredit',
    
    # Land / housing justice
    'community land trust', 'land trust', 'affordable housing',
    'habitat for humanity', 'homeless', 'housing coalition',
    'housing authority', 'tenant', 'eviction prevention',
    
    # Food sovereignty
    'food bank', 'food pantry', 'food co-op', 'food cooperative',
    'community garden', 'community farm', 'food sovereignty',
    'agroecology', 'permaculture', 'seed library', 'seed bank',
    'farmers market', 'urban farm', 'soup kitchen',
    
    # Democracy / civic
    'civic engagement', 'voter registration', 'voting rights',
    'participatory budget', 'community organizing', 'grassroots',
    'civil liberties', 'civil rights', 'human rights',
    'aclu', 'naacp', 'league of women voters',
    'transparency', 'accountability', 'anti-corruption',
    'public interest', 'advocacy',
    
    # Environment / ecology
    'conservation', 'environmental justice', 'climate',
    'renewable energy', 'solar', 'wind energy',
    'watershed', 'wetland', 'forest', 'reforestation',
    'wildlife', 'biodiversity', 'ecology', 'ecological',
    'sustainability', 'sustainable', 'green',
    'nature conserv', 'land conserv', 'sierra club',
    'audubon', 'wilderness', 'clean water', 'clean air',
    
    # Health / community wellness
    'community health', 'public health', 'free clinic',
    'mental health', 'health center', 'health centre',
    'planned parenthood', 'reproductive', 'hiv', 'aids',
    'substance abuse', 'addiction', 'recovery',
    'disability', 'disabled', 'accessibility',
    
    # Education (community-serving)
    'literacy', 'adult education', 'community college',
    'head start', 'early childhood', 'after school',
    'afterschool', 'mentoring', 'tutoring',
    'scholarship fund', 'educational equity',
    'stem education', 'coding for', 'tech for',
    'library', 'free library',
    
    # Justice / conflict resolution
    'restorative justice', 'criminal justice reform',
    'prison reform', 'reentry', 're-entry',
    'legal aid', 'legal services', 'public defender',
    'mediation', 'conflict resolution', 'peacebuilding',
    'peace corps', 'amnesty', 'innocence project',
    
    # Refugee / immigrant
    'refugee', 'immigrant', 'immigration', 'asylum',
    'newcomer', 'resettlement', 'migrant',
    
    # Indigenous
    'indigenous', 'native american', 'tribal',
    'first nations', 'aboriginal',
    
    # Community development
    'community development', 'community foundation',
    'community action', 'united way', 'community chest',
    'neighborhood development', 'rural development',
    
    # Youth development
    'boys and girls club', 'boy scouts', 'girl scouts',
    'big brothers', 'big sisters', 'ymca', 'ywca',
    'youth development', 'youth services', 'youth empowerment',
    
    # Senior / aging
    'meals on wheels', 'senior center', 'senior services',
    'aging', 'elder care', 'eldercare',
    
    # Arts & culture (community-serving)
    'community theater', 'community theatre',
    'public art', 'community arts', 'folk arts',
    'cultural center', 'cultural centre', 'heritage',
    'museum', 'historical society',
    
    # Open source / digital commons
    'open source', 'open data', 'digital commons',
    'net neutrality', 'internet freedom', 'privacy rights',
    
    # International development
    'international development', 'global health',
    'world relief', 'oxfam', 'care international',
    'doctors without borders', 'red cross', 'red crescent',
]

# Count how many have at least one strong positive
print("Checking strong positive signals...")

# Build a massive OR condition
conditions = " OR ".join(
    [f"LOWER(name) LIKE '%{kw}%' OR LOWER(description) LIKE '%{kw}%'" for kw in STRONG_POSITIVE]
)

# Mark orgs that have NO strong positive signal
c.execute(f"""
    UPDATE organizations
    SET status = 'excluded_audit_p2'
    WHERE status NOT IN ('removed', 'excluded_audit_p1', 'excluded_audit_p2')
    AND NOT ({conditions})
""")
excluded_p2 = c.rowcount
db.commit()

c.execute("SELECT COUNT(*) FROM organizations WHERE status NOT IN ('removed', 'excluded_audit_p1', 'excluded_audit_p2')")
after = c.fetchone()[0]

print(f"\n=== PASS 2 RESULTS ===")
print(f"Before:     {before:>10,}")
print(f"Excluded:   {excluded_p2:>10,}")
print(f"Surviving:  {after:>10,}")
print(f"Removal:    {excluded_p2/before*100:.1f}%")
print(f"Total kept: {after/698220*100:.1f}% of original")

# Breakdown by section
print(f"\n=== SURVIVING ORGS BY SECTION ===")
c.execute("""
    SELECT framework_area, COUNT(*) FROM organizations 
    WHERE status NOT IN ('removed', 'excluded_audit_p1', 'excluded_audit_p2')
    GROUP BY framework_area ORDER BY COUNT(*) DESC
""")
for area, cnt in c.fetchall():
    print(f"  {area or 'unclassified':<25} {cnt:>8,}")

# Breakdown by country (top 20)
print(f"\n=== TOP 20 COUNTRIES (post-audit) ===")
c.execute("""
    SELECT country_code, COUNT(*) FROM organizations 
    WHERE status NOT IN ('removed', 'excluded_audit_p1', 'excluded_audit_p2')
    GROUP BY country_code ORDER BY COUNT(*) DESC LIMIT 20
""")
for cc, cnt in c.fetchall():
    print(f"  {cc:<4} {cnt:>8,}")

# Random sample of survivors
print(f"\n=== RANDOM SAMPLE OF SURVIVORS (20) ===")
c.execute("""
    SELECT name, country_code, framework_area FROM organizations 
    WHERE status NOT IN ('removed', 'excluded_audit_p1', 'excluded_audit_p2')
    ORDER BY RANDOM() LIMIT 20
""")
for name, cc, area in c.fetchall():
    print(f"  [{cc}] {area or '?':<20} {name[:80]}")

db.close()
