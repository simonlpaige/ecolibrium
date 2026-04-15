"""
Pass 1: Hard exclusion of obviously off-mission organizations.
Marks them as status='excluded_audit_p1' rather than deleting.
"""
import sqlite3

db = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db')
c = db.cursor()

# Get pre-count
c.execute("SELECT COUNT(*) FROM organizations WHERE status != 'removed'")
before = c.fetchone()[0]

EXCLUDE_PATTERNS = [
    # Religious worship (NOT faith-based social services)
    'church of', 'first church', 'baptist church', 'methodist church',
    'lutheran church', 'presbyterian church', 'pentecostal',
    'parish of', 'diocese of', 'synagogue', 'temple of',
    'chapel of', 'congregation of', 'bible fellowship',
    'gospel mission', 'worship center', 'worship centre',
    'evangelical church', 'assembly of god',
    
    # Fraternal / social clubs
    'golf club', 'country club', 'yacht club', 'polo club',
    'tennis association', 'swim club',
    'rotary club', 'lions club', 'kiwanis',
    'elks lodge', 'moose lodge', 'eagles lodge',
    'vfw post', 'american legion post',
    'masonic lodge', 'masonic temple', 'freemasons',
    'odd fellows', 'knights of columbus',
    'shriners', 'fraternal order of',
    
    # HOA / property
    'homeowners association', 'homeowner association',
    'condo association', 'condominium association',
    'property owners association', 'townhouse association',
    
    # Booster / parent school orgs
    'booster club', 'boosters inc', 'athletic boosters',
    'music boosters', 'band boosters', 'choir boosters',
    ' pta', ' pto', ' ptso', 'parent teacher',
    
    # Cemetery / funeral
    'cemetery association', 'cemetery inc', 'cemetery corp',
    'funeral home', 'memorial park association', 'burial',
    
    # Pet / hobby animal (not conservation)
    'kennel club', 'cat fanciers', 'dog fanciers',
    'breed club', 'horse show association',
    'pony club', 'rodeo association', 'rodeo club',
    
    # Professional guilds (not civil society)
    'bar association', 'medical association', 'dental association',
    'real estate association', 'realtors association',
    'trade association', 'industry association',
    'chamber of commerce',
    
    # Political
    'republican party', 'republican committee',
    'democratic party', 'democratic committee',
    'political action committee',
    
    # Alumni (generic, not community-serving)
    'alumni association', 'alumni club', 'alumni chapter',
    
    # Corporate entities that slipped in
    ' llc',
]

# Faith-based social services to KEEP (whitelist)
KEEP_PATTERNS = [
    'catholic charities', 'lutheran services', 'lutheran social',
    'islamic relief', 'jewish community', 'jewish family',
    'salvation army', 'habitat for humanity',
    'world vision', 'compassion international',
    'samaritan', 'community ministry', 'community ministries',
    'food pantry', 'food bank', 'soup kitchen', 'shelter',
    'refugee', 'immigrant services', 'social services',
]

total_excluded = 0
for pattern in EXCLUDE_PATTERNS:
    # Build whitelist check
    whitelist_conditions = " AND ".join(
        [f"LOWER(name) NOT LIKE '%{kp}%'" for kp in KEEP_PATTERNS]
    )
    
    query = f"""
        UPDATE organizations 
        SET status = 'excluded_audit_p1'
        WHERE status NOT IN ('removed', 'excluded_audit_p1')
        AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ?)
        AND {whitelist_conditions}
    """
    c.execute(query, (f'%{pattern}%', f'%{pattern}%'))
    affected = c.rowcount
    if affected > 0:
        total_excluded += affected
        print(f"  {pattern:<40} {affected:>6,} excluded")

db.commit()

# Post-count
c.execute("SELECT COUNT(*) FROM organizations WHERE status NOT IN ('removed', 'excluded_audit_p1')")
after = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM organizations WHERE status = 'excluded_audit_p1'")
excluded_total = c.fetchone()[0]

print(f"\n=== PASS 1 RESULTS ===")
print(f"Before:   {before:>10,}")
print(f"Excluded: {excluded_total:>10,}")
print(f"After:    {after:>10,}")
print(f"Removal:  {(before-after)/before*100:.1f}%")

# Show what's left by framework area
print(f"\n=== SURVIVING ORGS BY SECTION ===")
c.execute("""
    SELECT framework_area, COUNT(*) FROM organizations 
    WHERE status NOT IN ('removed', 'excluded_audit_p1')
    GROUP BY framework_area ORDER BY COUNT(*) DESC
""")
for area, cnt in c.fetchall():
    print(f"  {area or 'unclassified':<25} {cnt:>8,}")

db.close()
