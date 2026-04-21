"""
ECO-1: Download and ingest IRS EO BMF data into ecolibrium_directory.db
Runs directly as Python - bypasses Gemma/Paperclip heartbeat issues.
"""

import sqlite3
import csv
import urllib.request
import io
import os
import json
import time
import sys

DB_PATH = r"C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db"
DATA_DIR = r"C:\Users\simon\.openclaw\workspace\ecolibrium\data"

UNIQ_SOURCE_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uniq_org_source
ON organizations(source, source_id)
WHERE source_id IS NOT NULL AND TRIM(source_id) != ''
"""

UNIQ_REGISTRATION_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uniq_org_registration
ON organizations(country_code, registration_type, registration_id)
WHERE registration_id IS NOT NULL AND TRIM(registration_id) != ''
"""

# NTEE to framework area mapping
NTEE_MAP = {
    'R': 'democracy', 'S': 'democracy', 'U': 'democracy', 'V': 'democracy',
    'W': 'democracy',  # W20-W99 = democracy; W itself = cooperatives overlap
    'J': 'cooperatives', 'Y': 'cooperatives',
    'E': 'healthcare', 'F': 'healthcare', 'G': 'healthcare', 'H': 'healthcare',
    'K': 'food',
    'B': 'education',
    'L': 'housing_land',
    'I': 'conflict',
    'C': 'ecology', 'D': 'ecology',
    'A': 'recreation_arts',
}

# Real IRS EO BMF URLs - per state CSV files
# Source: https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf
BMF_BASE_URL = "https://www.irs.gov/pub/irs-soi/eo_{state}.csv"

STATE_CODES = [
    'al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'dc', 'fl',
    'ga', 'hi', 'id', 'il', 'in', 'ia', 'ks', 'ky', 'la', 'me',
    'md', 'ma', 'mi', 'mn', 'ms', 'mo', 'mt', 'ne', 'nv', 'nh',
    'nj', 'nm', 'ny', 'nc', 'nd', 'oh', 'ok', 'or', 'pa', 'ri',
    'sc', 'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv', 'wi',
    'wy', 'pr', 'xx'  # xx = international
]

def create_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS organizations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        country_code TEXT,
        country_name TEXT,
        state_province TEXT,
        city TEXT,
        registration_id TEXT,
        registration_type TEXT,
        description TEXT,
        website TEXT,
        email TEXT,
        framework_area TEXT,
        ntee_code TEXT,
        source TEXT,
        source_id TEXT,
        last_filing_year INTEGER,
        annual_revenue REAL,
        status TEXT DEFAULT 'active',
        date_added TEXT DEFAULT CURRENT_TIMESTAMP,
        verified INTEGER DEFAULT 0
    )''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_source_id ON organizations(source, source_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_country ON organizations(country_code)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_framework ON organizations(framework_area)')
    c.execute(UNIQ_SOURCE_SQL)
    c.execute(UNIQ_REGISTRATION_SQL)
    conn.commit()
    return conn

def get_framework_area(ntee_code):
    if not ntee_code:
        return None
    letter = ntee_code[0].upper()
    if letter in NTEE_MAP:
        # Special case: W20-W99 = democracy, W10-W19 = cooperatives/general
        if letter == 'W':
            try:
                num = int(ntee_code[1:3]) if len(ntee_code) >= 3 else 0
                if num >= 20:
                    return 'democracy'
                else:
                    return 'cooperatives'
            except:
                return 'democracy'
        # Special case: R20-R30 = conflict
        if letter == 'R':
            try:
                num = int(ntee_code[1:3]) if len(ntee_code) >= 3 else 0
                if 20 <= num <= 30:
                    return 'conflict'
            except:
                pass
        return NTEE_MAP[letter]
    return None

def process_bmf_row(row):
    """Extract relevant fields from IRS BMF CSV row."""
    # IRS BMF columns vary by file format. Common columns:
    # EIN, NAME, ICO, STREET, CITY, STATE, ZIP, GROUP, SUBSECTION, AFFILIATION,
    # CLASSIFICATION, RULING, DEDUCTIBILITY, FOUNDATION, ACTIVITY, ORGANIZATION,
    # STATUS, TAX_PERIOD, ASSET_CD, INCOME_CD, FILING_REQ_CD, PF_FILING_REQ_CD,
    # ACCT_PD, ASSET_AMT, INCOME_AMT, REVENUE_AMT, NTEE_CD, SORT_NAME
    
    ntee = row.get('NTEE_CD', '').strip()
    framework_area = get_framework_area(ntee)
    
    if not framework_area:
        return None  # Skip irrelevant orgs
    
    name = row.get('NAME', '').strip() or row.get('SORT_NAME', '').strip()
    if not name:
        return None
    
    ein = row.get('EIN', '').strip()
    state = row.get('STATE', '').strip()
    city = row.get('CITY', '').strip()
    
    try:
        revenue = float(row.get('REVENUE_AMT', 0) or 0)
    except:
        revenue = 0.0
    
    try:
        tax_period = str(row.get('TAX_PERIOD', ''))
        filing_year = int(tax_period[:4]) if len(tax_period) >= 4 else None
    except:
        filing_year = None
    
    return {
        'name': name,
        'country_code': 'US',
        'country_name': 'United States',
        'state_province': state,
        'city': city,
        'registration_id': ein,
        'registration_type': 'IRS_EIN',
        'framework_area': framework_area,
        'ntee_code': ntee,
        'source': 'IRS_EO_BMF',
        'source_id': ein,
        'last_filing_year': filing_year,
        'annual_revenue': revenue,
        'status': 'active',
        'verified': 0,
    }

def download_and_ingest_state(conn, state_code, progress):
    """Download and ingest one state's BMF file."""
    url = BMF_BASE_URL.format(state=state_code)
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read().decode('latin-1', errors='replace')
    except Exception as e:
        print(f"  SKIP {state_code}: {e}", flush=True)
        return 0, 0, 0
    
    reader = csv.DictReader(io.StringIO(content))
    
    rows_read = 0
    rows_inserted = 0
    rows_skipped = 0
    
    batch = []
    c = conn.cursor()
    
    for row in reader:
        rows_read += 1
        org = process_bmf_row(row)
        if org is None:
            rows_skipped += 1
            continue
        
        batch.append((
            org['name'], org['country_code'], org['country_name'],
            org['state_province'], org['city'], org['registration_id'],
            org['registration_type'], None, None, None,
            org['framework_area'], org['ntee_code'],
            org['source'], org['source_id'],
            org['last_filing_year'], org['annual_revenue'],
            'active', 0
        ))
        
        if len(batch) >= 1000:
            c.executemany('''
                INSERT INTO organizations
                (name, country_code, country_name, state_province, city,
                 registration_id, registration_type, description, website, email,
                 framework_area, ntee_code, source, source_id,
                 last_filing_year, annual_revenue, status, verified)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(source, source_id)
                WHERE source_id IS NOT NULL AND TRIM(source_id) != ''
                DO UPDATE SET
                    name=excluded.name,
                    country_code=excluded.country_code,
                    country_name=excluded.country_name,
                    state_province=excluded.state_province,
                    city=excluded.city,
                    registration_id=excluded.registration_id,
                    registration_type=excluded.registration_type,
                    framework_area=excluded.framework_area,
                    ntee_code=excluded.ntee_code,
                    last_filing_year=excluded.last_filing_year,
                    annual_revenue=excluded.annual_revenue,
                    status=excluded.status,
                    verified=excluded.verified
                ON CONFLICT(country_code, registration_type, registration_id)
                WHERE registration_id IS NOT NULL AND TRIM(registration_id) != ''
                DO UPDATE SET
                    name=excluded.name,
                    country_name=excluded.country_name,
                    state_province=excluded.state_province,
                    city=excluded.city,
                    framework_area=excluded.framework_area,
                    ntee_code=excluded.ntee_code,
                    source=excluded.source,
                    source_id=excluded.source_id,
                    last_filing_year=excluded.last_filing_year,
                    annual_revenue=excluded.annual_revenue,
                    status=excluded.status,
                    verified=excluded.verified
            ''', batch)
            rows_inserted += c.rowcount
            conn.commit()
            batch = []
    
    if batch:
        c.executemany('''
            INSERT INTO organizations
            (name, country_code, country_name, state_province, city,
             registration_id, registration_type, description, website, email,
             framework_area, ntee_code, source, source_id,
             last_filing_year, annual_revenue, status, verified)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(source, source_id)
            WHERE source_id IS NOT NULL AND TRIM(source_id) != ''
            DO UPDATE SET
                name=excluded.name,
                country_code=excluded.country_code,
                country_name=excluded.country_name,
                state_province=excluded.state_province,
                city=excluded.city,
                registration_id=excluded.registration_id,
                registration_type=excluded.registration_type,
                framework_area=excluded.framework_area,
                ntee_code=excluded.ntee_code,
                last_filing_year=excluded.last_filing_year,
                annual_revenue=excluded.annual_revenue,
                status=excluded.status,
                verified=excluded.verified
            ON CONFLICT(country_code, registration_type, registration_id)
            WHERE registration_id IS NOT NULL AND TRIM(registration_id) != ''
            DO UPDATE SET
                name=excluded.name,
                country_name=excluded.country_name,
                state_province=excluded.state_province,
                city=excluded.city,
                framework_area=excluded.framework_area,
                ntee_code=excluded.ntee_code,
                source=excluded.source,
                source_id=excluded.source_id,
                last_filing_year=excluded.last_filing_year,
                annual_revenue=excluded.annual_revenue,
                status=excluded.status,
                verified=excluded.verified
        ''', batch)
        rows_inserted += c.rowcount
        conn.commit()
    
    progress['total_read'] += rows_read
    progress['total_inserted'] += rows_inserted
    progress['total_skipped'] += rows_skipped
    
    db_count = conn.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]
    print(f"  {state_code.upper()}: read={rows_read} inserted={rows_inserted} skipped={rows_skipped} | DB total: {db_count:,}", flush=True)
    return rows_read, rows_inserted, rows_skipped

def main():
    print("ECO-1: IRS EO BMF Ingestion", flush=True)
    print(f"DB: {DB_PATH}", flush=True)
    
    conn = create_db()
    
    # Check existing count
    existing = conn.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]
    print(f"Existing records: {existing:,}", flush=True)
    
    progress = {'total_read': 0, 'total_inserted': 0, 'total_skipped': 0}
    
    # Also try the full zip file first - it may be more reliable
    # Try per-state CSV files
    print(f"\nDownloading {len(STATE_CODES)} state files...", flush=True)
    
    for i, state in enumerate(STATE_CODES):
        print(f"[{i+1}/{len(STATE_CODES)}] Processing {state.upper()}...", flush=True)
        download_and_ingest_state(conn, state, progress)
        time.sleep(0.5)  # Be polite
    
    final_count = conn.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]
    
    # Framework area breakdown
    breakdown = conn.execute(
        'SELECT framework_area, COUNT(*) FROM organizations GROUP BY framework_area ORDER BY COUNT(*) DESC'
    ).fetchall()
    
    print(f"\n{'='*50}", flush=True)
    print(f"ECO-1 COMPLETE", flush=True)
    print(f"Total read: {progress['total_read']:,}", flush=True)
    print(f"Total inserted: {progress['total_inserted']:,}", flush=True)
    print(f"Total skipped (no NTEE match): {progress['total_skipped']:,}", flush=True)
    print(f"Final DB count: {final_count:,}", flush=True)
    print(f"\nFramework breakdown:", flush=True)
    for area, count in breakdown:
        print(f"  {area}: {count:,}", flush=True)
    
    # Sample 10 random records
    samples = conn.execute(
        'SELECT name, state_province, framework_area, ntee_code FROM organizations ORDER BY RANDOM() LIMIT 10'
    ).fetchall()
    print(f"\nSample records:", flush=True)
    for s in samples:
        print(f"  {s[0]} ({s[1]}) [{s[2]}] NTEE:{s[3]}", flush=True)
    
    conn.close()
    
    # Save report
    report = {
        'source': 'IRS_EO_BMF',
        'total_read': progress['total_read'],
        'total_inserted': progress['total_inserted'],
        'total_skipped': progress['total_skipped'],
        'final_db_count': final_count,
        'framework_breakdown': dict(breakdown)
    }
    with open(os.path.join(DATA_DIR, 'eco1_report.json'), 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nReport saved to eco1_report.json", flush=True)
    return final_count

if __name__ == '__main__':
    count = main()
    sys.exit(0 if count > 0 else 1)
