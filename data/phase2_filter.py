"""
Phase 2: Second-pass alignment filter + model_type classification.
Scores every active org and sets alignment_score and model_type.

Multilingual coverage: STRONG_POS is unioned with STRONG_POS_MULTI from i18n_terms.py,
which provides around 350 alignment terms across ~30 languages. See MULTILINGUAL-TERMS.md.
"""
import os
import re
import sys
import sqlite3
import unicodedata

# Allow running from either the workspace root or the data/ dir.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)
from i18n_terms import STRONG_POS_MULTI  # noqa: E402

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'

# Original English-biased list. Preserved verbatim; multilingual expansion is
# merged below so reviewers can still see the original assumptions.
_STRONG_POS_ORIGINAL = [
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

# Merge original + multilingual bank, lowercase + dedup while preserving order.
def _dedup_keep_order(items):
    seen = set()
    out = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out

# English plural + hyphenated variants. Word-boundary matching treats each
# surface form as a distinct term, so we list them explicitly rather than
# writing morphological rules.
_ENGLISH_SURFACE_VARIANTS = [
    # Hyphenated (UK sector convention)
    'co-operative', 'co-operation', 'co-operatives',
    'worker co-operative', 'housing co-operative',
    # Plurals of alignment terms likely to appear in org names + descriptions
    'cooperatives', 'worker cooperatives', 'housing cooperatives',
    'producer cooperatives', 'credit unions', 'community land trusts',
    'community gardens', 'community health centers',
    'mutual aid networks', 'worker collectives',
]

STRONG_POS = _dedup_keep_order(
    [t.lower() for t in _STRONG_POS_ORIGINAL]
    + _ENGLISH_SURFACE_VARIANTS
    + list(STRONG_POS_MULTI)
)

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


def _normalize_for_match(text):
    # NFC first so composed/decomposed forms compare equal,
    # then lowercase. Keep Unicode intact, do not strip accents.
    return unicodedata.normalize('NFC', text or '').lower()


# Precompile a single regex for STRONG_POS that uses Unicode-aware word
# boundaries. This prevents false positives like 'owe' matching 'power',
# 'hima' matching 'himalaya', or 'cooperativa' matching something longer.
# The pattern alternates all terms, each wrapped with lookarounds that
# require non-word-char boundaries on both sides. re.UNICODE makes \w
# respect Unicode letter categories so Chinese, Arabic, Cyrillic etc.
# are treated as word chars too.
_WORD_BOUNDARY_LEFT = r'(?<![\w])'
_WORD_BOUNDARY_RIGHT = r'(?![\w])'


def _compile_boundary_regex(terms):
    if not terms:
        return None
    # Sort longest first so longer terms win over their prefixes during scan.
    escaped = [re.escape(t) for t in sorted(terms, key=len, reverse=True)]
    pattern = _WORD_BOUNDARY_LEFT + r'(?:' + '|'.join(escaped) + r')' + _WORD_BOUNDARY_RIGHT
    return re.compile(pattern, re.IGNORECASE | re.UNICODE)


# STRONG_POS needs word-boundary matching because it has short non-English
# terms like 'hima', 'mera', 'owe' that collide with English substrings.
_STRONG_POS_RE = _compile_boundary_regex(STRONG_POS)
# NEGATIVE is English-only proper-noun-ish words (church, chapel, club). We
# want 'church' to catch 'churches' too, so we use substring (the old behavior).
# MODERATE_POS is English stems (education, community, health) that must
# match morphological variants (educational, communities, healthcare), also
# substring.


def _count_unique_strong(text):
    if _STRONG_POS_RE is None:
        return 0
    return len(set(m.group(0).lower() for m in _STRONG_POS_RE.finditer(text)))


def _count_substring_hits(terms, text):
    return sum(1 for kw in terms if kw in text)


def score_org(name, desc):
    combined = _normalize_for_match((name or '') + ' ' + (desc or ''))
    score = 0
    score += 3 * _count_unique_strong(combined)
    score += 1 * _count_substring_hits(MODERATE_POS, combined)
    score -= 3 * _count_substring_hits(NEGATIVE, combined)
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
    last_id = 0
    processed = 0
    
    score_buckets = {}
    model_type_counts = {}
    removed_count = 0
    
    while True:
        c.execute("""
            SELECT id, name, description
            FROM organizations
            WHERE status='active' AND id > ?
            ORDER BY id
            LIMIT ?
        """, (last_id, batch_size))
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
        last_id = rows[-1][0]
        print(f'  Processed {processed:,}/{total:,}')

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
