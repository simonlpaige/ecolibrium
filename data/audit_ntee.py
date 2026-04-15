import sqlite3
db = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db')
c = db.cursor()

# NTEE code distribution for active US orgs
c.execute("""
    SELECT SUBSTR(ntee_code, 1, 1) as major, COUNT(*) 
    FROM organizations 
    WHERE status NOT IN ('removed', 'excluded_audit_p1', 'excluded_audit_p2')
    AND country_code = 'US'
    GROUP BY major ORDER BY COUNT(*) DESC
""")

# NTEE major categories reference:
# A = Arts, Culture, Humanities
# B = Education
# C = Environment
# D = Animal-Related
# E = Health Care
# F = Mental Health / Crisis
# G = Diseases, Disorders
# H = Medical Research
# I = Crime, Legal Related
# J = Employment
# K = Food, Agriculture, Nutrition
# L = Housing, Shelter
# M = Public Safety
# N = Recreation, Sports, Leisure
# O = Youth Development
# P = Human Services
# Q = International
# R = Civil Rights, Social Action, Advocacy
# S = Community Improvement
# T = Philanthropy, Voluntarism
# U = Science & Technology
# V = Social Science
# W = Public, Society Benefit
# X = Religion-Related
# Y = Mutual/Membership Benefit
# Z = Unknown

ECOLIBRIUM_RELEVANT = {
    'C': 'Environment',
    'E': 'Health Care',
    'F': 'Mental Health',
    'I': 'Crime/Legal/Justice',
    'J': 'Employment/Jobs',
    'K': 'Food/Agriculture',
    'L': 'Housing/Shelter',
    'O': 'Youth Development',
    'P': 'Human Services',
    'Q': 'International',
    'R': 'Civil Rights/Advocacy',
    'S': 'Community Improvement',
    'W': 'Public/Society Benefit',
}

EXCLUDE_NTEE = {
    'A': 'Arts/Culture (too broad)',
    'B': 'Education (too broad)',
    'D': 'Animal-Related (not mission)',
    'G': 'Diseases/Disorders (medical research)',
    'H': 'Medical Research',
    'M': 'Public Safety (fire depts etc)',
    'N': 'Recreation/Sports (too broad)',
    'T': 'Philanthropy/Voluntarism (meta)',
    'U': 'Science/Technology (too broad)',
    'V': 'Social Science (academic)',
    'X': 'Religion-Related',
    'Y': 'Mutual/Membership Benefit',
    'Z': 'Unknown',
}

print(f"{'Code':<6} {'Category':<35} {'Count':>10} {'Verdict'}")
print("-" * 70)
keep_total = 0
exclude_total = 0
for major, count in c.fetchall():
    if major in ECOLIBRIUM_RELEVANT:
        verdict = f"KEEP - {ECOLIBRIUM_RELEVANT[major]}"
        keep_total += count
    elif major in EXCLUDE_NTEE:
        verdict = f"EXCLUDE - {EXCLUDE_NTEE[major]}"
        exclude_total += count
    else:
        verdict = "REVIEW"
    print(f"{major or '?':<6} {'':35} {count:>10,}  {verdict}")

null_count_q = c.execute("""
    SELECT COUNT(*) FROM organizations 
    WHERE status NOT IN ('removed', 'excluded_audit_p1', 'excluded_audit_p2')
    AND country_code = 'US' AND (ntee_code IS NULL OR ntee_code = '')
""")
null_count = null_count_q.fetchone()[0]
print(f"\n{'NULL':<6} {'No NTEE code':35} {null_count:>10,}  REVIEW")

print(f"\nKeep (by NTEE):     {keep_total:>10,}")
print(f"Exclude (by NTEE):  {exclude_total:>10,}")
print(f"No NTEE code:       {null_count:>10,}")
print(f"Potential removal:  {exclude_total + null_count:>10,} ({(exclude_total+null_count)/638877*100:.1f}% of US orgs)")

db.close()
