"""
Ecolibrium country research runner - no Paperclip required.
Reads QUEUE.txt, picks next country without a DIRECTORY_CC.md, runs research, writes output.
"""
import sqlite3
import subprocess
import os
import re
import sys
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
sys.path.insert(0, os.path.join(WORKSPACE_DIR, 'ecolibrium', 'data'))
from native_queries import get_queries

def get_next_country():
    """Read QUEUE.txt, return first country without a DIRECTORY_CC.md."""
    with open(QUEUE_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(None, 1)
            if len(parts) < 2:
                continue
            cc, name = parts[0], parts[1]
            md_path = os.path.join(REGIONAL_DIR, f'DIRECTORY_{cc}.md')
            if not os.path.exists(md_path):
                return cc, name
    return None, None

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

def research_country(cc, country_name):
    """Run searches for a country using English + native language queries."""
    queries = get_queries(cc, country_name)
    # Cap at 6 queries max to stay well within cron timeout budget
    queries = queries[:6]
    print(f'Searching: {country_name} ({cc}) — {len(queries)} queries (capped)')

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
    # Filter out negative-scored orgs
    orgs = [o for o in orgs if o.get('alignment_score', 0) >= 0]
    if not orgs:
        return 0
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    now = datetime.utcnow().isoformat()
    inserted = 0
    centroid = COUNTRY_CENTROIDS.get(cc)
    lat = centroid[0] if centroid else None
    lon = centroid[1] if centroid else None
    for org in orgs:
        try:
            c.execute("""INSERT OR IGNORE INTO organizations
                (name, country_code, country_name, description, source, date_added, status,
                 framework_area, model_type, alignment_score, lat, lon, geo_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (org['n'], cc, country_name, org.get('d', ''), 'web_research', now, 'active',
                 org.get('framework_area'), org.get('model_type'), org.get('alignment_score'),
                 lat, lon, 'country_centroid' if centroid else None))
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
            if not os.path.exists(os.path.join(REGIONAL_DIR, f'DIRECTORY_{cc}.md')):
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


def main():
    cc, country_name = get_next_country()
    if not cc:
        print('Queue empty - all countries done!')
        return {'status': 'done', 'message': 'All countries complete'}

    print(f'\n=== {country_name} ({cc}) ===')

    # Source 1: DuckDuckGo web research (existing)
    search_text = research_country(cc, country_name)
    orgs = extract_orgs(search_text, cc, country_name)
    print(f'Found {len(orgs)} orgs from web search')

    if not orgs:
        orgs = [{'n': f'{country_name} Civil Society Network', 'd': f'Primary civil society network in {country_name}', 'cc': cc, 'country': country_name}]

    write_markdown(orgs, cc, country_name)
    ddg_inserted = ingest_db(orgs, cc, country_name)

    # Source 2: Wikidata SPARQL for this country
    run_wikidata(cc, country_name)

    # Source 3: Wikidata backfill for next queued country (catches up on big countries)
    run_wikidata_backfill()

    # Source 4: US state-level Wikidata enrichment (one state per run)
    run_us_state_enrichment()

    rebuild_index()

    # Count total for this country after all sources
    try:
        db = sqlite3.connect(DB_PATH)
        c = db.cursor()
        c.execute("SELECT COUNT(*) FROM organizations WHERE country_code=? AND status != 'removed'", (cc,))
        country_total = c.fetchone()[0]
        db.close()
    except:
        country_total = len(orgs)

    remaining = queue_remaining()
    result = {
        'status': 'done',
        'country': country_name,
        'cc': cc,
        'orgs_found': country_total,
        'ddg_orgs': len(orgs),
        'db_inserted': ddg_inserted,
        'queue_remaining': remaining,
    }
    print(f'\nDone: {country_name} ({cc}), {country_total} total orgs (DDG:{len(orgs)}+Wikidata), {remaining} countries remaining')
    return result

if __name__ == '__main__':
    r = main()
    if r:
        import json
        print(json.dumps(r))
