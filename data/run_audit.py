"""
Ecolibrium Audit Agent
Two jobs per run:
  1. FILTER: Remove orgs that don't align with Ecolibrium's framework areas
  2. ENRICH: Fill missing fields (website, description) for remaining orgs via web search

Runs in batches - safe to interrupt and resume. Tracks progress in audit_state.json.
"""
import sqlite3
import subprocess
import json
import os
import re
import sys
from datetime import datetime

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'
STATE_FILE = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\audit_state.json'
WORKSPACE_DIR = r'C:\Users\simon\.openclaw\workspace'

# ── What belongs in Ecolibrium ────────────────────────────────────────────────
# NTEE codes that are IN scope
NTEE_IN = {
    'A',  # Arts, Culture & Humanities - recreation/arts section
    'B',  # Education
    'C',  # Environment - ecology, energy
    'D',  # Animal-Related - ecology adjacent
    'E',  # Health Care
    'F',  # Mental Health
    'G',  # Disease Research - healthcare
    'H',  # Medical Research - healthcare
    'I',  # Crime & Legal - conflict/restorative justice
    'J',  # Employment - cooperatives/work
    'K',  # Food, Agriculture & Nutrition
    'L',  # Housing & Shelter
    'N',  # Recreation & Sports - rec/arts section
    'O',  # Youth Development
    'P',  # Human Services
    'Q',  # International & Foreign Affairs
    'R',  # Civil Rights & Advocacy - democracy
    'S',  # Community Improvement - democracy, cooperatives
    'T',  # Philanthropy & Voluntarism
    'U',  # Science & Technology - digital commons
    'V',  # Social Science
    'W',  # Public & Societal Benefit
    'Y',  # Mutual & Membership Benefit - cooperatives
}

# NTEE codes that are OUT of scope
NTEE_OUT = {
    'X',  # Religion (unless social justice subcodes)
    'M',  # Public Safety/Military - out unless restorative
}

# NTEE subcodes that ARE in scope even within out-of-scope letters
NTEE_EXCEPTIONS_IN = {
    'X20', 'X30',  # Religious orgs with strong social justice mission
}

# Name/description patterns that indicate OUT of scope
EXCLUDE_PATTERNS = [
    r'\bchurch\b', r'\bchurches\b', r'\bchapel\b', r'\bcathedral\b',
    r'\bparish\b', r'\bdiocese\b', r'\bsynod\b', r'\bministr(y|ies)\b',
    r'\bcongregation\b', r'\btemple\b', r'\bmosque\b', r'\bsynagogue\b',
    r'\bfraternal order\b', r'\blodge\b', r'\bvfw post\b', r'\blegion post\b',
    r'\bhomeowners association\b', r'\bhoa\b',
    r'\bgolf club\b', r'\bcountry club\b',
    r'\bpolitical (party|committee|action)\b', r'\bpac\b',
    r'\bbooster club\b',
]
EXCLUDE_RE = re.compile('|'.join(EXCLUDE_PATTERNS), re.IGNORECASE)

# Name patterns that strongly indicate IN scope
INCLUDE_SIGNALS = [
    'cooperative', 'co-op', 'coop', 'mutual aid', 'community land',
    'worker', 'solidarity', 'indigenous', 'agroecolog', 'food bank',
    'habitat for', 'restorative', 'civic', 'democracy', 'participat',
    'environmental', 'ecology', 'renewable', 'solar', 'wind energy',
    'community health', 'free clinic', 'legal aid', 'civil rights',
    'housing trust', 'tenant', 'refugee', 'asylum', 'immigrant',
]

BATCH_SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 500


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        'filter_last_id': 0,
        'enrich_last_id': 0,
        'filter_done': False,
        'enrich_done': False,
        'filtered_out': 0,
        'enriched': 0,
        'last_run': None,
    }


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def is_in_scope(name, ntee, description=''):
    """Return True if org belongs in Ecolibrium directory."""
    ntee = (ntee or '').strip().upper()
    name_lower = (name or '').lower()
    desc_lower = (description or '').lower()
    combined = name_lower + ' ' + desc_lower

    # Explicit NTEE exclusion
    if ntee and ntee[0] in NTEE_OUT:
        # Check exceptions
        if ntee[:3] not in NTEE_EXCEPTIONS_IN:
            # But still keep if name/desc has strong inclusion signal
            if not any(s in combined for s in INCLUDE_SIGNALS):
                return False

    # Name/description exclusion patterns
    if EXCLUDE_RE.search(combined):
        # Override if strong inclusion signal
        if not any(s in combined for s in INCLUDE_SIGNALS):
            return False

    return True


def search(query):
    try:
        result = subprocess.run(
            ['node', os.path.join(WORKSPACE_DIR, 'tools', 'puter-search.js'), query],
            capture_output=True, text=True, timeout=25, cwd=WORKSPACE_DIR
        )
        return result.stdout[:1500] if result.returncode == 0 else ''
    except Exception:
        return ''


def extract_website(text, org_name):
    """Try to find a website URL in search results."""
    # Look for URLs near the org name
    patterns = [
        r'https?://(?:www\.)?([a-zA-Z0-9\-]+\.(?:org|net|coop|ngo|int|edu))[^\s]*',
        r'(?:www\.)?([a-zA-Z0-9\-]+\.(?:org|net|coop|ngo))[^\s]*',
    ]
    for pat in patterns:
        matches = re.findall(pat, text)
        if matches:
            # Prefer .org/.coop/.ngo
            for m in matches:
                if any(m.endswith(ext) for ext in ['.org', '.coop', '.ngo', '.int']):
                    return 'https://' + m if not m.startswith('http') else m
            return 'https://' + matches[0]
    return ''


def extract_description(text, org_name):
    """Extract a 1-sentence description from search results."""
    name_lower = org_name.lower()
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if len(line) < 20 or len(line) > 300:
            continue
        if name_lower[:10] in line.lower() or any(w in line.lower() for w in ['nonprofit', 'organization', 'founded', 'mission', 'works to', 'dedicated']):
            # Clean it up
            desc = re.sub(r'\s+', ' ', line).strip()
            if len(desc) > 15:
                return desc[:250]
    return ''


def run_filter(db, state):
    """Pass 1: remove out-of-scope orgs in batches."""
    if state['filter_done']:
        print('Filter: already complete')
        return state

    c = db.cursor()
    c.execute('SELECT COUNT(*) FROM organizations WHERE status != "removed"')
    total = c.fetchone()[0]

    last_id = state.get('filter_last_id', 0)
    print(f'Filter pass: last_id={last_id}, active orgs={total:,}')

    c.execute('''
        SELECT id, name, ntee_code, description
        FROM organizations
        WHERE status != "removed" AND id > ?
        ORDER BY id
        LIMIT ?
    ''', (last_id, BATCH_SIZE))
    rows = c.fetchall()

    if not rows:
        state['filter_done'] = True
        print(f'Filter complete. Total removed: {state["filtered_out"]:,}')
        return state

    to_remove = []
    for row_id, name, ntee, desc in rows:
        if not is_in_scope(name, ntee, desc):
            to_remove.append(row_id)

    if to_remove:
        db.execute(f'''
            UPDATE organizations SET status="removed", description=
            COALESCE(description,"") || " [FILTERED: out of scope]"
            WHERE id IN ({",".join("?" * len(to_remove))})
        ''', to_remove)
        db.commit()
        state['filtered_out'] += len(to_remove)

    state['filter_last_id'] = rows[-1][0]
    pct = min(100, int((state['filter_last_id']) / max(total, 1) * 100))
    print(f'  Processed through id {state["filter_last_id"]:,} (~{pct}%) - removed {len(to_remove)} this batch, {state["filtered_out"]:,} total')

    return state


def run_enrich(db, state):
    """Pass 2: fill missing website/description via web search."""
    if state['enrich_done']:
        print('Enrich: already complete')
        return state

    c = db.cursor()
    # Only enrich research orgs (not IRS bulk - those rarely have websites to find)
    c.execute('''
        SELECT COUNT(*) FROM organizations
        WHERE status = "active"
        AND source = "web_research"
        AND (website IS NULL OR website = "")
    ''')
    total = c.fetchone()[0]

    last_id = state.get('enrich_last_id', 0)
    print(f'Enrich pass: last_id={last_id}, orgs needing enrichment={total:,}')

    c.execute('''
        SELECT id, name, country_name, description
        FROM organizations
        WHERE status = "active"
        AND source = "web_research"
        AND (website IS NULL OR website = "")
        AND id > ?
        ORDER BY id
        LIMIT ?
    ''', (last_id, min(BATCH_SIZE, 50)))  # cap enrich at 50/run (search is slow)
    rows = c.fetchall()

    if not rows:
        state['enrich_done'] = True
        print(f'Enrich complete. Total enriched: {state["enriched"]:,}')
        return state

    enriched = 0
    for row_id, name, country, desc in rows:
        query = f'"{name}" {country} organization'
        text = search(query)
        if not text:
            continue
        website = extract_website(text, name)
        new_desc = desc or extract_description(text, name)
        if website or (new_desc and not desc):
            db.execute('''
                UPDATE organizations SET website=?, description=?
                WHERE id=?
            ''', (website or None, new_desc or desc, row_id))
            enriched += 1

    db.commit()
    state['enrich_last_id'] = rows[-1][0]
    state['enriched'] += enriched
    print(f'  Enriched {enriched}/{len(rows)} orgs this batch, {state["enriched"]:,} total')

    return state


def main():
    state = load_state()
    state['last_run'] = datetime.utcnow().isoformat()

    db = sqlite3.connect(DB_PATH)

    # Run filter pass
    state = run_filter(db, state)
    save_state(state)

    # Run enrich pass (only if filter is done for this batch)
    state = run_enrich(db, state)
    save_state(state)

    # Summary
    c = db.cursor()
    c.execute('SELECT COUNT(*) FROM organizations WHERE status="active"')
    active = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM organizations WHERE status="removed"')
    removed = c.fetchone()[0]
    db.close()

    print(f'\n=== Audit batch complete ===')
    print(f'Active orgs: {active:,}')
    print(f'Removed (out of scope): {removed:,}')
    print(f'Enriched total: {state["enriched"]:,}')
    fp = 'done' if state['filter_done'] else f'last_id={state.get("filter_last_id", 0):,}'
    ep = 'done' if state['enrich_done'] else f'last_id={state.get("enrich_last_id", 0):,}'
    print(f'Filter progress: {fp}')
    print(f'Enrich progress: {ep}')

    return {
        'active': active,
        'removed': removed,
        'enriched': state['enriched'],
        'filter_done': state['filter_done'],
        'enrich_done': state['enrich_done'],
    }


if __name__ == '__main__':
    r = main()
    print(json.dumps(r))
