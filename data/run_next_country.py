"""
Ecolibrium country research runner - no Paperclip required.
Reads QUEUE.txt, picks next country without a DIRECTORY_CC.md, runs research, writes output.
"""
import sqlite3
import subprocess
import os
import re
import sys
import json
from datetime import datetime

COUNTRY_CENTROIDS = {
    'NG':(9.08,8.67),'KE':(-1.29,36.82),'ZA':(-30.56,22.94),
    'VE':(6.42,-66.59),'HN':(15.2,-86.24),'BO':(-16.29,-63.59),
    'EC':(-1.83,-78.18),'GY':(4.86,-58.93),'PY':(-23.44,-58.44),
    'SR':(3.92,-56.03),'BR':(-14.24,-51.93),'IN':(20.59,78.96),
    'PH':(12.88,121.77),'ID':(-0.79,113.92),'VN':(14.06,108.28),
    'TH':(15.87,100.99),'MM':(21.91,95.96),'KH':(12.57,104.99),
    'MY':(4.21,101.98),'CN':(35.86,104.19),'JP':(36.2,138.25),
    'KR':(35.91,127.77),'TW':(23.69,120.96),'DE':(51.17,10.45),
    'FR':(46.23,2.21),'GB':(55.38,-3.44),'IT':(41.87,12.57),
    'ES':(40.46,-3.75),'PL':(51.92,19.15),'UA':(48.38,31.17),
    'TR':(38.96,35.24),'EG':(26.82,30.80),'MA':(31.79,-7.09),
    'GH':(7.95,-1.02),'ET':(9.14,40.49),'TZ':(-6.37,34.89),
    'UG':(1.37,32.29),'RW':(-1.94,29.87),'MZ':(-18.67,35.53),
    'ZM':(-13.13,27.85),'CA':(56.13,-106.35),'AU':(-25.27,133.78),
    'NZ':(-40.90,174.89),'MX':(23.63,-102.55),'CO':(4.57,-74.30),
    'AR':(-38.42,-63.62),'PE':(-9.19,-75.02),'CL':(-35.68,-71.54),
    'GT':(15.78,-90.23),'CU':(21.52,-77.78),'SN':(14.50,-14.45),
    'CI':(7.54,-5.55),'CM':(3.85,11.50),'MG':(-18.77,46.87),
    'TN':(33.89,9.54),'JO':(30.59,36.24),'LB':(33.85,35.86),
    'PK':(30.38,69.35),'BD':(23.68,90.35),'NP':(28.39,84.12),
    'LK':(7.87,80.77),'KZ':(48.02,66.92),'UZ':(41.38,64.59),
    'GE':(42.32,43.36),'AM':(40.07,45.04),'RO':(45.94,24.97),
    'HU':(47.16,19.50),'RS':(44.02,21.01),'BG':(42.73,25.49),
    'GR':(39.07,21.82),'PT':(39.40,-8.22),'NL':(52.13,5.29),
    'BE':(50.50,4.47),'SE':(60.13,18.64),'NO':(60.47,8.47),
    'DK':(56.26,9.50),'FI':(61.92,25.75),'CH':(46.82,8.23),
    'AT':(47.52,14.55),'IE':(53.41,-8.24),'FJ':(-17.71,178.07),
    'PG':(-6.31,143.96),'DO':(18.74,-70.16),'JM':(18.11,-77.30),
    'TT':(10.69,-61.22),'HT':(18.97,-72.29),'NI':(12.87,-85.21),
    'CR':(9.75,-83.75),'PA':(8.54,-80.78),'UY':(-32.52,-55.77),
}

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

STRONG_POS_LOCAL = ['cooperative','co-op','mutual aid','indigenous','agroecol','solidarity','restorative']
MODERATE_POS_LOCAL = ['community','environmental','health','education','housing','food','energy','justice','rights']
NEGATIVE_LOCAL = ['church','parish','fraternal','golf','country club','hoa','booster','cemetery']


def classify_org(org):
    name = (org.get('n','') or '').lower()
    desc = (org.get('d','') or '').lower()
    combined = name + ' ' + desc

    # framework_area
    best_area = None
    best_score = 0
    for area, keywords in FRAMEWORK_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > best_score:
            best_score = score
            best_area = area
    org['framework_area'] = best_area or 'democracy'

    # alignment_score
    score = 0
    for kw in STRONG_POS_LOCAL:
        if kw in combined: score += 3
    for kw in MODERATE_POS_LOCAL:
        if kw in combined: score += 1
    for kw in NEGATIVE_LOCAL:
        if kw in combined: score -= 3
    org['alignment_score'] = max(-5, min(5, score))

    # model_type
    if any(x in name for x in ['cooperative','co-op','coop']): org['model_type'] = 'cooperative'
    elif 'mutual aid' in name: org['model_type'] = 'mutual_aid'
    elif 'foundation' in name: org['model_type'] = 'foundation'
    elif any(x in name for x in ['institute','research','center']): org['model_type'] = 'research'
    elif any(x in name for x in ['federation','alliance','coalition','network']): org['model_type'] = 'federation'
    else: org['model_type'] = 'nonprofit'

    return org

QUEUE_FILE = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\QUEUE.txt'
REGIONAL_DIR = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\regional'
DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'
WORKSPACE_DIR = r'C:\Users\simon\.openclaw\workspace'
COUNTRY_STATE_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\country_research_state.json'
sys.path.insert(0, os.path.join(WORKSPACE_DIR, 'ecolibrium', 'data'))
from native_queries import get_queries


def load_country_state():
    try:
        with open(COUNTRY_STATE_PATH, encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f'  state load error: {e}')
    return {}


def save_country_state(state):
    os.makedirs(os.path.dirname(COUNTRY_STATE_PATH), exist_ok=True)
    with open(COUNTRY_STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, sort_keys=True)


def is_country_completed(state, cc):
    record = state.get(cc) or {}
    return bool(record.get('completed'))


def update_country_state(cc, country_name, completed, org_count, markdown_path=None):
    state = load_country_state()
    state[cc] = {
        'country_name': country_name,
        'completed': bool(completed),
        'org_count': int(org_count or 0),
        'last_attempted_at': datetime.utcnow().isoformat() + 'Z',
        'markdown_path': markdown_path,
    }
    if completed:
        state[cc]['completed_at'] = datetime.utcnow().isoformat() + 'Z'
    save_country_state(state)

def get_next_country():
    """Read QUEUE.txt, return first country without a completed state flag."""
    state = load_country_state()
    with open(QUEUE_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(None, 1)
            if len(parts) < 2:
                continue
            cc, name = parts[0], parts[1]
            if not is_country_completed(state, cc):
                return cc, name
    return None, None


# Thresholds for thoroughness pass
THIN_ORG_THRESHOLD = 100  # countries with < this many orgs are "thin" and get priority re-runs
THIN_REVISIT_MIN_HOURS = 6  # even thin countries wait at least this long between re-runs


def _country_name_map():
    name_map = {}
    try:
        with open(QUEUE_FILE, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(None, 1)
                if len(parts) == 2:
                    name_map[parts[0]] = parts[1]
    except Exception:
        pass
    # Backstop names for centroids not in QUEUE.txt
    backstop = {
        'US': 'United States', 'GB': 'United Kingdom', 'CA': 'Canada',
        'AU': 'Australia', 'NZ': 'New Zealand', 'DE': 'Germany', 'FR': 'France',
        'IT': 'Italy', 'ES': 'Spain', 'PT': 'Portugal', 'NL': 'Netherlands',
        'BE': 'Belgium', 'CH': 'Switzerland', 'AT': 'Austria', 'IE': 'Ireland',
        'SE': 'Sweden', 'NO': 'Norway', 'DK': 'Denmark', 'FI': 'Finland',
        'GR': 'Greece', 'PL': 'Poland', 'HU': 'Hungary', 'RO': 'Romania',
        'BG': 'Bulgaria', 'RS': 'Serbia', 'UA': 'Ukraine', 'TR': 'Turkey',
        'RU': 'Russia', 'JP': 'Japan', 'KR': 'South Korea', 'CN': 'China',
        'IN': 'India', 'PK': 'Pakistan', 'BD': 'Bangladesh', 'LK': 'Sri Lanka',
        'NP': 'Nepal', 'VN': 'Vietnam', 'TH': 'Thailand', 'MY': 'Malaysia',
        'ID': 'Indonesia', 'PH': 'Philippines', 'MM': 'Myanmar', 'KH': 'Cambodia',
        'TW': 'Taiwan', 'KZ': 'Kazakhstan', 'UZ': 'Uzbekistan', 'TM': 'Turkmenistan',
        'GE': 'Georgia', 'AM': 'Armenia', 'JO': 'Jordan', 'LB': 'Lebanon',
        'EG': 'Egypt', 'MA': 'Morocco', 'TN': 'Tunisia', 'GH': 'Ghana',
        'NG': 'Nigeria', 'KE': 'Kenya', 'UG': 'Uganda', 'TZ': 'Tanzania',
        'RW': 'Rwanda', 'ET': 'Ethiopia', 'ZA': 'South Africa', 'ZM': 'Zambia',
        'MZ': 'Mozambique', 'MG': 'Madagascar', 'CM': 'Cameroon', 'SN': 'Senegal',
        'CI': "Cote d'Ivoire", 'MX': 'Mexico', 'GT': 'Guatemala', 'CU': 'Cuba',
        'DO': 'Dominican Republic', 'HT': 'Haiti', 'JM': 'Jamaica', 'TT': 'Trinidad and Tobago',
        'NI': 'Nicaragua', 'HN': 'Honduras', 'CR': 'Costa Rica', 'PA': 'Panama',
        'CO': 'Colombia', 'VE': 'Venezuela', 'EC': 'Ecuador', 'PE': 'Peru',
        'BR': 'Brazil', 'BO': 'Bolivia', 'PY': 'Paraguay', 'UY': 'Uruguay',
        'AR': 'Argentina', 'CL': 'Chile', 'GY': 'Guyana', 'SR': 'Suriname',
        'FJ': 'Fiji', 'PG': 'Papua New Guinea',
    }
    for cc, n in backstop.items():
        name_map.setdefault(cc, n)
    return name_map


def _country_org_counts():
    """Return dict of cc -> active org count for all centroid countries."""
    counts = {}
    try:
        db = sqlite3.connect(DB_PATH)
        c = db.cursor()
        c.execute("SELECT country_code, COUNT(*) FROM organizations WHERE status != 'removed' GROUP BY country_code")
        for cc, n in c.fetchall():
            counts[cc] = n
        db.close()
    except Exception:
        pass
    return counts


def get_oldest_revisit_country(staleness_days=14):
    """Pick the next country to revisit.

    Priority order:
      1. Thin countries (<THIN_ORG_THRESHOLD orgs) with oldest mtime, minimum
         THIN_REVISIT_MIN_HOURS old.
      2. Any country older than staleness_days.
    Returns (None, None) and prints a skip message if nothing is due.
    """
    import time
    now = time.time()
    thin_cutoff = now - THIN_REVISIT_MIN_HOURS * 3600
    stale_cutoff = now - staleness_days * 86400

    name_map = _country_name_map()
    counts = _country_org_counts()

    # Pass 1: thin countries (under-covered) - hit these hardest.
    thin_candidates = []
    for cc in COUNTRY_CENTROIDS:
        md_path = os.path.join(REGIONAL_DIR, f'DIRECTORY_{cc}.md')
        if not os.path.exists(md_path):
            continue
        n_orgs = counts.get(cc, 0)
        if n_orgs >= THIN_ORG_THRESHOLD:
            continue
        mtime = os.path.getmtime(md_path)
        if mtime >= thin_cutoff:
            continue  # hit too recently, let DDG cool off
        thin_candidates.append((mtime, cc, n_orgs))
    if thin_candidates:
        thin_candidates.sort()  # oldest mtime first
        mtime, cc, n_orgs = thin_candidates[0]
        age_hours = int((now - mtime) / 3600)
        country_name = name_map.get(cc, cc)
        print(f'MODE=thin cc={cc} orgs={n_orgs} age={age_hours}h (thin-coverage priority)')
        return cc, country_name

    # Pass 2: standard staleness sweep over all centroid countries.
    oldest_cc = None
    oldest_mtime = float('inf')
    for cc in COUNTRY_CENTROIDS:
        md_path = os.path.join(REGIONAL_DIR, f'DIRECTORY_{cc}.md')
        if not os.path.exists(md_path):
            continue
        mtime = os.path.getmtime(md_path)
        if mtime < oldest_mtime:
            oldest_mtime = mtime
            oldest_cc = cc

    if oldest_cc is None:
        return None, None

    if oldest_mtime >= stale_cutoff:
        print(f'All countries recently scanned (within {staleness_days}d and no thin-country due), skipping this cycle')
        return None, None

    age_days = int((now - oldest_mtime) / 86400)
    country_name = name_map.get(oldest_cc, oldest_cc)
    print(f'MODE=revisit cc={oldest_cc} age={age_days}d')
    return oldest_cc, country_name

def search(query):
    """Run a single DuckDuckGo search via ddg-search.js (free, no API key)."""
    try:
        result = subprocess.run(
            ['node', os.path.join(WORKSPACE_DIR, 'tools', 'ddg-search.js'), query],
            capture_output=True, text=True, timeout=12, cwd=WORKSPACE_DIR,
            encoding='utf-8', errors='replace'
        )
        return result.stdout[:3000] if result.returncode == 0 else ''
    except subprocess.TimeoutExpired:
        print(f'  search timeout (DDG rate-limited?), skipping')
        return ''
    except Exception as e:
        print(f'  search error: {e}')
        return ''

DDG_CONSECUTIVE_TIMEOUT_LIMIT = 3  # bail on DDG if this many consecutive timeouts

def research_country(cc, country_name, deep=False):
    """Run searches for a country using English + native language queries.
    deep=True raises the cap for thin/undercovered countries."""
    queries = get_queries(cc, country_name)
    cap = 12 if deep else 6
    queries = queries[:cap]
    label = 'DEEP' if deep else 'capped'
    print(f'Searching: {country_name} ({cc}) — {len(queries)} queries ({label})')

    results = []
    consecutive_timeouts = 0
    for i, q in enumerate(queries):
        print(f'  [{i+1}/{len(queries)}] {q[:60]}...' if len(q) > 60 else f'  [{i+1}/{len(queries)}] {q}')
        text = search(q)
        if text:
            results.append(text)
            consecutive_timeouts = 0
        else:
            consecutive_timeouts += 1
            if consecutive_timeouts >= DDG_CONSECUTIVE_TIMEOUT_LIMIT:
                print(f'  DDG appears rate-limited ({consecutive_timeouts} consecutive failures), skipping remaining queries')
                break

    return '\n\n'.join(results)

def extract_orgs(search_text, cc, country_name):
    """Parse search results to extract organization names and descriptions."""
    orgs = []
    seen = set()

    lines = search_text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or len(line) < 8:
            continue

        patterns = [
            r'^## (.{5,100})$',
            r'\*\*([^*]{5,80})\*\*',
            r'^\d+\.\s+([A-Z][^.\n]{5,80}?)(?:\s*[-–—:]|\s*$)',
            r'^[-•·]\s+([A-Z][^.\n]{5,80}?)(?:\s*[-–—:]|\s*$)',
            r'([A-Z][A-Za-z\s&/,\'-]{8,60})(?:\s+is\s|\s+was\s|\s*[-–(])',
        ]

        for pat in patterns:
            m = re.search(pat, line)
            if m:
                name = m.group(1).strip().rstrip('.,;:-')
                # Filter junk
                if len(name) < 5 or len(name) > 80:
                    continue
                if any(w in name.lower() for w in ['http', 'www.', 'click', 'search', 'result', 'page', 'found via']):
                    continue
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                # Grab description from next non-empty line
                desc = ''
                for j in range(i+1, min(i+3, len(lines))):
                    candidate = lines[j].strip()
                    if candidate and not candidate.startswith(('http', '**', '-', '•')):
                        desc = candidate[:200]
                        break
                org = {'n': name, 'd': desc, 'cc': cc, 'country': country_name}
                classify_org(org)
                orgs.append(org)
                break

    return orgs[:150]

def write_markdown(orgs, cc, country_name):
    """Write DIRECTORY_CC.md."""
    os.makedirs(REGIONAL_DIR, exist_ok=True)
    path = os.path.join(REGIONAL_DIR, f'DIRECTORY_{cc}.md')
    now = datetime.utcnow().strftime('%Y-%m-%d')
    lines = [
        f'# 🌐 {country_name} ({cc}) Civil Society Directory',
        f'',
        f'*Compiled: {now} | Source: Web research | Organizations: {len(orgs)}*',
        f'',
        '---',
        '',
        '## Organizations',
        '',
    ]
    for org in orgs:
        lines.append(f"### {org['n']}")
        if org.get('framework_area'):
            lines.append(f"Framework: {org['framework_area']}")
        if org.get('model_type'):
            lines.append(f"Model: {org['model_type']}")
        if org.get('d') and len(org['d']) > 10:
            lines.append(f"> {org['d']}")
        lines.append('')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'Written: {path} ({len(orgs)} orgs)')
    return path

def ingest_db(orgs, cc, country_name):
    """Insert orgs into SQLite."""
    if not orgs:
        return 0
    # Filter out low-signal orgs (score < 2 matches the aggressive alignment trim)
    before = len(orgs)
    orgs = [o for o in orgs if o.get('alignment_score', 0) >= 2]
    rejected = before - len(orgs)
    if rejected:
        print(f'Rejected {rejected} low-signal orgs before DB insert')
    if not orgs:
        return 0
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    now = datetime.utcnow().isoformat()
    inserted = 0
    centroid = COUNTRY_CENTROIDS.get(cc)
    lat = centroid[0] if centroid else None
    lon = centroid[1] if centroid else None
    import json as _json
    today = now[:10]
    for org in orgs:
        try:
            attestation = _json.dumps([{
                'issuer': 'web_research',
                'date': today,
                'type': 'ingest-provenance',
                'signature': None,
                'scope': cc,
            }])
            c.execute("""INSERT OR IGNORE INTO organizations
                (name, country_code, country_name, description, source, date_added, status,
                 framework_area, model_type, alignment_score, lat, lon, geo_source, attestations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (org['n'], cc, country_name, org.get('d', ''), 'web_research', now, 'active',
                 org.get('framework_area'), org.get('model_type'), org.get('alignment_score'),
                 lat, lon, 'country_centroid' if centroid else None, attestation))
            inserted += c.rowcount
        except Exception:
            pass
    db.commit()
    c.execute('SELECT COUNT(*) FROM organizations')
    total = c.fetchone()[0]
    db.close()
    print(f'DB: +{inserted} new, total={total:,}')
    return inserted

def rebuild_index():
    """Regenerate search JSON indexes and DIRECTORY.md."""
    for script in ['build_search_index.py', 'export_directory.py']:
        path = os.path.join(WORKSPACE_DIR, 'ecolibrium', 'data', script)
        if os.path.exists(path):
            subprocess.run(['python', path], timeout=120, cwd=WORKSPACE_DIR)

def queue_remaining():
    """Count countries left in queue."""
    state = load_country_state()
    remaining = 0
    with open(QUEUE_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(None, 1)
            if len(parts) < 2:
                continue
            cc = parts[0]
            if not is_country_completed(state, cc):
                remaining += 1
    return remaining

def run_wikidata(cc, country_name):
    """Pull structured org data from Wikidata SPARQL."""
    try:
        wikidata_script = os.path.join(WORKSPACE_DIR, 'ecolibrium', 'data', 'sources', 'wikidata_ingest.py')
        if os.path.exists(wikidata_script):
            print(f'\n--- Wikidata SPARQL ingest for {cc} ---')
            result = subprocess.run(
                ['python', wikidata_script, cc, country_name],
                capture_output=True, text=True, timeout=45,
                encoding='utf-8', errors='replace'
            )
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
            if result.stderr:
                errs = [l for l in result.stderr.split('\n') if 'Error' in l or 'error' in l.lower()]
                if errs:
                    print('  Wikidata errors:', '\n'.join(errs[:3]))
            return True
        else:
            print('  Wikidata ingest script not found, skipping')
            return False
    except subprocess.TimeoutExpired:
        print('  Wikidata ingest timed out')
        return False
    except Exception as e:
        print(f'  Wikidata error: {e}')
        return False


def run_wikidata_backfill():
    """Run Wikidata backfill for one queued country (separate from current DDG country)."""
    try:
        backfill_script = os.path.join(WORKSPACE_DIR, 'ecolibrium', 'data', 'sources', 'run_next_wikidata.py')
        if os.path.exists(backfill_script):
            print(f'\n--- Wikidata backfill (next queued country) ---')
            result = subprocess.run(
                ['python', backfill_script],
                capture_output=True, text=True, timeout=45,
                encoding='utf-8', errors='replace'
            )
            for line in result.stdout.split('\n'):
                if line.strip():
                    print(f'  {line.strip()}')
            return True
    except Exception as e:
        print(f'  Wikidata backfill error: {e}')
    return False


def run_us_state_enrichment():
    """Run Wikidata enrichment for one US state (adds notable orgs with descriptions/coords)."""
    try:
        state_script = os.path.join(WORKSPACE_DIR, 'ecolibrium', 'data', 'sources', 'us_state_wikidata.py')
        if os.path.exists(state_script):
            print(f'\n--- US state Wikidata enrichment ---')
            result = subprocess.run(
                ['python', state_script],
                capture_output=True, text=True, timeout=45,
                encoding='utf-8', errors='replace'
            )
            for line in result.stdout.split('\n'):
                if line.strip():
                    print(f'  {line.strip()}')
            return True
    except Exception as e:
        print(f'  US state enrichment error: {e}')
    return False


def run_subregion_enrichment():
    """Run generic subregion-level Wikidata ingest for one international subregion.
    Covers CA provinces, DE Laender, BR/IN/MX states, ES autonomous communities, etc."""
    try:
        script = os.path.join(WORKSPACE_DIR, 'ecolibrium', 'data', 'sources', 'subregion_wikidata.py')
        if os.path.exists(script):
            print(f'\n--- Subregion Wikidata enrichment ---')
            result = subprocess.run(
                ['python', script],
                capture_output=True, text=True, timeout=90,
                encoding='utf-8', errors='replace'
            )
            for line in result.stdout.split('\n'):
                if line.strip():
                    print(f'  {line.strip()}')
            return True
    except Exception as e:
        print(f'  Subregion enrichment error: {e}')
    return False


THIN_BATCH_SIZE = 5  # countries per run when in thin-only revisit mode


def _process_one(cc, country_name, deep):
    """Run one country through web search + wikidata + write. Return insert stats."""
    print(f'\n=== {country_name} ({cc}) {"[deep]" if deep else ""} ===')
    search_text = research_country(cc, country_name, deep=deep)
    orgs = extract_orgs(search_text, cc, country_name)
    print(f'Found {len(orgs)} orgs from web search')
    markdown_path = write_markdown(orgs, cc, country_name)
    ddg_inserted = ingest_db(orgs, cc, country_name)
    run_wikidata(cc, country_name)
    try:
        db = sqlite3.connect(DB_PATH)
        c = db.cursor()
        c.execute("SELECT COUNT(*) FROM organizations WHERE country_code=? AND status != 'removed'", (cc,))
        country_total = c.fetchone()[0]
        db.close()
    except Exception:
        country_total = len(orgs)
    completed = country_total > 0
    update_country_state(cc, country_name, completed, country_total, markdown_path)
    if not completed:
        print(f'No real organizations found for {country_name} ({cc}); leaving it uncompleted for a later retry')
    print(f'Done: {country_name} ({cc}) -> {country_total} total orgs ({ddg_inserted} new from web)')
    return {'cc': cc, 'country': country_name, 'orgs_found': country_total, 'ddg_orgs': len(orgs), 'db_inserted': ddg_inserted, 'deep': deep}


def main():
    mode = 'fresh'
    cc, country_name = get_next_country()
    if cc:
        print(f'MODE=fresh cc={cc}')
        deep = False
        try:
            counts = _country_org_counts()
            if counts.get(cc, 0) < THIN_ORG_THRESHOLD:
                deep = True
        except Exception:
            pass
        results = [_process_one(cc, country_name, deep)]

        # Fresh run still does housekeeping
        run_wikidata_backfill()
        run_us_state_enrichment()
        run_subregion_enrichment()
        rebuild_index()
        remaining = queue_remaining()
        results[0]['mode'] = 'fresh'
        results[0]['queue_remaining'] = remaining
        print(f'\nFresh done. {remaining} countries remaining in queue.')
        return {'status': 'done', 'mode': 'fresh', 'results': results, 'queue_remaining': remaining}

    print('Queue exhausted - thin-coverage batch mode (up to ' + str(THIN_BATCH_SIZE) + ' countries this run)...')
    mode = 'revisit'
    results = []
    seen = set()
    for i in range(THIN_BATCH_SIZE):
        cc, country_name = get_oldest_revisit_country(14)
        if not cc or cc in seen:
            break
        seen.add(cc)
        try:
            counts = _country_org_counts()
            deep = counts.get(cc, 0) < THIN_ORG_THRESHOLD
        except Exception:
            deep = True
        results.append(_process_one(cc, country_name, deep))

    if not results:
        return {'status': 'idle', 'message': 'No thin or stale countries due, skipping cycle'}

    # Housekeeping once per run
    run_wikidata_backfill()
    run_us_state_enrichment()
    run_subregion_enrichment()
    rebuild_index()

    print(f'\nBatch done: {len(results)} countries processed this run (thin priority).')
    return {'status': 'done', 'mode': 'revisit-batch', 'results': results}

if __name__ == '__main__':
    r = main()
    if r:
        import json
        print(json.dumps(r))
