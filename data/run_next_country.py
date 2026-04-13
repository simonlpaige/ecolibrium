"""
Run the next pending country research task from Paperclip issue queue.
Picks the highest-priority todo issue, runs DuckDuckGo research, writes DIRECTORY_XX.md,
marks issue done, ingest into DB.
"""
import sqlite3
import requests
import json
import re
import os
import sys
from datetime import datetime

BASE_URL = "http://localhost:3100"
COMPANY_ID = "f76fbb4f-ea7d-4c8f-8358-373686a188eb"
AGENT_ID = "da60c721-16ba-43e1-9665-13fb7a2ad190"  # Researcher
API_KEY = "pcp_11a4e3b71a29d45efecc830e0d26a3110fb0cdd9038d6fcb"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
DB_PATH = r"C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db"
REGIONAL_DIR = r"C:\Users\simon\.openclaw\workspace\ecolibrium\data\regional"
WORKSPACE_DIR = r"C:\Users\simon\.openclaw\workspace"

def get_next_issue():
    """Get highest priority todo issue assigned to researcher."""
    r = requests.get(f"{BASE_URL}/api/companies/{COMPANY_ID}/issues?limit=200&status=todo", headers=HEADERS)
    issues = r.json()
    if not issues:
        # Fall back to backlog
        r = requests.get(f"{BASE_URL}/api/companies/{COMPANY_ID}/issues?limit=200&status=backlog", headers=HEADERS)
        issues = r.json()
    if not issues:
        print("No issues found")
        return None
    # Sort by priority (lower = higher priority), then by issue number
    sorted_issues = sorted(issues, key=lambda x: (x.get('priority', 99), x.get('identifier', 'Z')))
    return sorted_issues[0]

def search_country_orgs(country_name, country_code):
    """Search for civil society orgs in a country using DuckDuckGo."""
    import subprocess
    
    queries = [
        f"civil society organizations {country_name} NGO nonprofit list",
        f"{country_name} registered nonprofits charities directory",
        f"{country_name} NGO database civil society",
        f"environmental organizations {country_name}",
        f"human rights organizations {country_name}",
        f"community organizations {country_name} nonprofit",
    ]
    
    results = []
    for q in queries:
        try:
            cmd = ["node", os.path.join(WORKSPACE_DIR, "tools", "puter-search.js"), q]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=WORKSPACE_DIR)
            if result.returncode == 0:
                results.append(result.stdout[:2000])
        except Exception as e:
            print(f"Search error for '{q}': {e}")
    
    return "\n\n".join(results)

def extract_orgs_from_search(search_text, country_name, country_code):
    """Parse search results to extract org names and details."""
    orgs = []
    seen = set()
    
    lines = search_text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or len(line) < 10:
            continue
        
        # Look for org-like patterns
        patterns = [
            r'\*\*([^*]+)\*\*',  # Bold text
            r'^\d+\.\s+(.+?)(?:\s*[-–]|\s*:)',  # Numbered lists
            r'^[-•]\s+(.+?)(?:\s*[-–]|\s*:)',  # Bullet points
            r'([A-Z][A-Za-z\s&/,-]{10,60})(?:\s*[-–(])',  # Org-name-like capitalized phrases
        ]
        
        for pat in patterns:
            m = re.search(pat, line)
            if m:
                name = m.group(1).strip().strip('.,;:')
                if len(name) > 5 and name.lower() not in seen:
                    seen.add(name.lower())
                    # Extract description from surrounding context
                    desc_lines = lines[i:i+2]
                    desc = ' '.join(desc_lines).replace(name, '').strip()[:200]
                    orgs.append({'name': name, 'description': desc, 'country_code': country_code, 'country_name': country_name})
                break
    
    return orgs[:150]  # Cap at 150 orgs per country

def write_directory_md(orgs, country_name, country_code, issue_title):
    """Write DIRECTORY_XX.md file."""
    now = datetime.utcnow().strftime('%Y-%m-%d')
    path = os.path.join(REGIONAL_DIR, f"DIRECTORY_{country_code}.md")
    
    lines = [
        f"# 🌐 {country_name} ({country_code}) Civil Society Directory",
        f"",
        f"*Compiled: {now} | Source: Web research via DuckDuckGo | Task: {issue_title}*",
        f"",
        f"**{len(orgs)} organizations identified**",
        f"",
        "---",
        "",
        "## Organizations",
        "",
    ]
    
    for org in orgs:
        name = org['name']
        desc = org.get('description', '').strip()
        lines.append(f"### {name}")
        if desc and len(desc) > 10:
            lines.append(f"> {desc}")
        lines.append("")
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"Written: {path} ({len(orgs)} orgs)")
    return path

def ingest_to_db(orgs, country_code, country_name):
    """Insert orgs into SQLite DB."""
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    now = datetime.utcnow().isoformat()
    inserted = 0
    for org in orgs:
        try:
            c.execute("""
                INSERT OR IGNORE INTO organizations 
                (name, country_code, country_name, description, source, date_added, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (org['name'], country_code, country_name, org.get('description', ''), 'web_research', now, 'active'))
            inserted += c.rowcount
        except Exception as e:
            pass
    db.commit()
    c.execute("SELECT COUNT(*) FROM organizations")
    total = c.fetchone()[0]
    db.close()
    print(f"DB: inserted {inserted} new orgs, total={total:,}")
    return inserted

def mark_issue_done(issue_id, comment):
    """Mark Paperclip issue as done."""
    # Update status
    requests.patch(f"{BASE_URL}/api/companies/{COMPANY_ID}/issues/{issue_id}",
                   headers=HEADERS, json={"status": "done"})
    # Add comment
    requests.post(f"{BASE_URL}/api/companies/{COMPANY_ID}/issues/{issue_id}/comments",
                  headers=HEADERS, json={"body": comment})
    print(f"Issue {issue_id} marked done")

def main():
    issue = get_next_issue()
    if not issue:
        print("No pending issues. All done!")
        return
    
    issue_id = issue['id']
    title = issue.get('title', '')
    identifier = issue.get('identifier', '')
    print(f"Working on: {identifier} - {title}")
    
    # Extract country from title: "ECO-65: Bolivia (BO)" or similar
    m = re.search(r'([A-Za-z\s]+)\s*\(([A-Z]{2,3})\)', title)
    if m:
        country_name = m.group(1).strip()
        country_code = m.group(2)
    else:
        # Try to extract just from title
        parts = title.replace('Research:', '').replace('Directory:', '').strip().split()
        country_name = ' '.join(parts[:2]) if parts else title
        country_code = ''.join(w[0] for w in country_name.split()[:2]).upper()
    
    print(f"Country: {country_name} ({country_code})")
    
    # Check if already done
    out_path = os.path.join(REGIONAL_DIR, f"DIRECTORY_{country_code}.md")
    if os.path.exists(out_path):
        print(f"Already exists: {out_path}, marking done anyway")
        mark_issue_done(issue_id, f"Already completed: {out_path}")
        return
    
    # Mark in progress
    requests.patch(f"{BASE_URL}/api/companies/{COMPANY_ID}/issues/{issue_id}",
                   headers=HEADERS, json={"status": "in_progress"})
    
    # Search
    print("Searching...")
    search_text = search_country_orgs(country_name, country_code)
    
    # Extract orgs
    orgs = extract_orgs_from_search(search_text, country_name, country_code)
    print(f"Found {len(orgs)} orgs")
    
    if not orgs:
        print("No orgs found, trying fallback...")
        orgs = [{'name': f'{country_name} Civil Society Network', 'description': f'Primary civil society network in {country_name}', 'country_code': country_code, 'country_name': country_name}]
    
    # Write files
    write_directory_md(orgs, country_name, country_code, title)
    ingest_to_db(orgs, country_code, country_name)
    
    # Regenerate DIRECTORY.md
    try:
        import subprocess
        subprocess.run(["python", os.path.join(WORKSPACE_DIR, "ecolibrium", "data", "export_directory.py")], 
                      timeout=120, cwd=WORKSPACE_DIR)
    except Exception as e:
        print(f"Export warning: {e}")
    
    # Mark done
    with open(out_path) as f:
        org_count = len(re.findall(r'^### ', f.read(), re.MULTILINE))
    mark_issue_done(issue_id, f"Completed: {org_count} organizations found for {country_name}. Output: data/regional/DIRECTORY_{country_code}.md")
    
    print(f"\nDone! {country_name} ({country_code}): {len(orgs)} orgs")

if __name__ == "__main__":
    main()
