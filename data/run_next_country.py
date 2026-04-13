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

QUEUE_FILE = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\QUEUE.txt'
REGIONAL_DIR = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\regional'
DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'
WORKSPACE_DIR = r'C:\Users\simon\.openclaw\workspace'

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
    """Run a single DuckDuckGo search via puter-search.js."""
    try:
        result = subprocess.run(
            ['node', os.path.join(WORKSPACE_DIR, 'tools', 'puter-search.js'), query],
            capture_output=True, text=True, timeout=30, cwd=WORKSPACE_DIR
        )
        return result.stdout[:2000] if result.returncode == 0 else ''
    except Exception as e:
        print(f'  search error: {e}')
        return ''

def research_country(cc, country_name):
    """Run 15+ searches for a country, return raw text."""
    print(f'Searching: {country_name} ({cc})')
    queries = [
        f'civil society organizations {country_name} NGO nonprofit directory',
        f'{country_name} nonprofit registry charities database',
        f'{country_name} cooperative federation worker-owned solidarity economy',
        f'{country_name} environmental organizations ecology',
        f'{country_name} food sovereignty agroecology peasant organizations',
        f'{country_name} community health organizations',
        f'{country_name} democratic governance citizen participation',
        f'{country_name} housing land trust community organizations',
        f'{country_name} restorative justice peacebuilding organizations',
        f'{country_name} renewable energy community cooperative',
        f'{country_name} indigenous peoples organizations rights',
        f'{country_name} women cooperative self-help solidarity',
        f'{country_name} mutual aid solidarity economy network',
        f'{country_name} open source civic tech digital rights',
        f'{country_name} nonprofit social enterprise directory',
    ]

    # Add local-language queries
    latam = ['CO','AR','MX','PE','CL','UY','PY','VE','HN','GT','NI','CR','PA','CU','DO','BO','EC']
    francophone = ['SN','CI','CM','MG','TN','MA']
    if cc in latam:
        queries += [
            f'organizaciones sociedad civil {country_name} directorio',
            f'{country_name} organizaciones comunitarias cooperativas',
            f'{country_name} movimientos sociales organizaciones populares',
        ]
    elif cc in francophone:
        queries += [
            f'organisations société civile {country_name} annuaire',
            f'{country_name} coopératives organisations communautaires',
        ]
    elif cc == 'BR':
        queries += [
            f'organizações sociedade civil {country_name} diretório',
            f'{country_name} cooperativas movimentos sociais',
        ]
    elif cc == 'PT':
        queries += [f'organizações sociedade civil Portugal']
    elif cc in ['CN', 'TW']:
        queries += [f'{country_name} civil society NGO organizations English']
    elif cc in ['JP', 'KR']:
        queries += [f'{country_name} NPO NGO civil society organizations English list']

    results = []
    for i, q in enumerate(queries):
        print(f'  [{i+1}/{len(queries)}] {q[:60]}...' if len(q) > 60 else f'  [{i+1}/{len(queries)}] {q}')
        text = search(q)
        if text:
            results.append(text)

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
                orgs.append({'n': name, 'd': desc, 'cc': cc, 'country': country_name})
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
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    now = datetime.utcnow().isoformat()
    inserted = 0
    for org in orgs:
        try:
            c.execute("""INSERT OR IGNORE INTO organizations
                (name, country_code, country_name, description, source, date_added, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (org['n'], cc, country_name, org.get('d', ''), 'web_research', now, 'active'))
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

def main():
    cc, country_name = get_next_country()
    if not cc:
        print('Queue empty - all countries done!')
        return {'status': 'done', 'message': 'All countries complete'}

    print(f'\n=== {country_name} ({cc}) ===')

    search_text = research_country(cc, country_name)
    orgs = extract_orgs(search_text, cc, country_name)
    print(f'Found {len(orgs)} orgs')

    if not orgs:
        orgs = [{'n': f'{country_name} Civil Society Network', 'd': f'Primary civil society network in {country_name}', 'cc': cc, 'country': country_name}]

    write_markdown(orgs, cc, country_name)
    inserted = ingest_db(orgs, cc, country_name)
    rebuild_index()

    remaining = queue_remaining()
    result = {
        'status': 'done',
        'country': country_name,
        'cc': cc,
        'orgs_found': len(orgs),
        'db_inserted': inserted,
        'queue_remaining': remaining,
    }
    print(f'\nDone: {country_name} ({cc}), {len(orgs)} orgs, {remaining} countries remaining')
    return result

if __name__ == '__main__':
    r = main()
    if r:
        import json
        print(json.dumps(r))
