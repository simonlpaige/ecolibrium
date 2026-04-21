"""
ECO-184 / Phase 2: Download and ingest UK Charity Commission data
Source: https://register-of-charities.charitycommission.gov.uk/register/full-register-download
"""

import sqlite3
import csv
import urllib.request
import zipfile
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

# UK Charity Commission classification codes to framework areas
# CCEW uses "what" codes (classification of purposes)
# Key codes: 101=Education, 103=Health, 108=Religious (skip), 111=Environment,
# 113=Arts, 115=Sport, 116=Citizenship/Community, 117=Community dev,
# 118=Housing, 205=Poverty, 206=Overseas, 207=Relief of disaster
# NTEE-equivalent: map by purpose code

PURPOSE_TO_FRAMEWORK = {
    '101': 'education',       # Education/training
    '102': 'education',       # Arts/culture (sometimes)
    '103': 'healthcare',      # Health/disability
    '104': 'conflict',        # Saving lives
    '105': 'conflict',        # Overseas aid/famine
    '106': 'ecology',         # Environmental protection
    '107': 'ecology',         # Animal welfare
    '108': None,              # Religion - skip
    '109': 'conflict',        # Human rights/religion freedom
    '110': 'democracy',       # Community development
    '111': 'ecology',         # Environment
    '112': 'recreation_arts', # Recreation/leisure
    '113': 'recreation_arts', # Arts/culture
    '114': None,              # Sports (skip)
    '115': None,              # Sports
    '116': 'democracy',       # Citizenship/community
    '117': 'democracy',       # Community development
    '118': 'housing_land',    # Housing
    '119': 'education',       # Education
    '120': None,              # Economic/employment (often not a match)
    '121': 'healthcare',      # Disability
    '201': 'food',            # Food/poverty relief (poverty)
    '202': 'healthcare',      # Health
    '203': None,              # Religious activities
    '204': 'democracy',       # Political activities
    '205': 'food',            # Poverty/deprivation
    '206': 'democracy',       # Overseas/global justice
    '207': 'conflict',        # Disaster/emergency
    '208': 'democracy',       # Community
    '209': 'education',       # Education
    '210': 'healthcare',      # Medical research
    '211': 'ecology',         # Environmental
    '301': 'cooperatives',    # Mutual benefit
    '302': 'cooperatives',    # Members' benefit
}

UK_DOWNLOAD_URL = "https://ccewuksprododata.blob.core.windows.net/assets/zip/RegEntity.zip"
# Alt: try the bulk download endpoint
UK_ALT_URL = "https://register-of-charities.charitycommission.gov.uk/register/full-register-download"

def create_db_if_needed():
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
    c.execute(UNIQ_SOURCE_SQL)
    c.execute(UNIQ_REGISTRATION_SQL)
    conn.commit()
    return conn

def try_download(url, timeout=120):
    """Attempt to download from a URL, return bytes or None."""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; EcolibiumBot/1.0)',
            'Accept': 'application/zip,application/octet-stream,*/*'
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            size = resp.headers.get('Content-Length', 'unknown')
            print(f"  Downloading from {url} (size: {size} bytes)...", flush=True)
            data = resp.read()
            print(f"  Downloaded {len(data):,} bytes", flush=True)
            return data
    except Exception as e:
        print(f"  FAIL {url}: {e}", flush=True)
        return None

def get_framework_from_purposes(purposes_str):
    """Parse pipe-separated purpose codes and return first matching area."""
    if not purposes_str:
        return None
    codes = purposes_str.split('|') if '|' in purposes_str else [purposes_str.strip()]
    for code in codes:
        code = code.strip()
        area = PURPOSE_TO_FRAMEWORK.get(code)
        if area:
            return area
    return None

def process_charity_csv(content, conn, progress):
    """Process the main charity CSV file."""
    # UK Charity Commission CSV format varies. Key columns typically:
    # regno, subno, name, orgtype, gd, aob, aob_defined, nhs, ha_no, 
    # corr, add1-5, phone, fax, email, web, fax_n, phone_n, 
    # income_band, fyend, phone2, email2

    reader = csv.DictReader(io.StringIO(content))
    fieldnames = reader.fieldnames
    print(f"  CSV columns: {fieldnames[:10] if fieldnames else 'unknown'}", flush=True)

    batch = []
    c = conn.cursor()
    rows_read = 0
    rows_inserted = 0
    rows_skipped = 0

    for row in reader:
        rows_read += 1
        
        # Try to get name
        name = (row.get('name') or row.get('charity_name') or 
                row.get('NAME') or row.get('CHARITY_NAME') or '').strip()
        if not name:
            rows_skipped += 1
            continue
        
        # Registration number
        regno = (row.get('regno') or row.get('charity_number') or 
                 row.get('REGNO') or '').strip()
        
        # Status - skip removed charities
        status_val = (row.get('removed') or row.get('status') or '').strip().lower()
        if status_val in ('y', 'yes', '1', 'removed', 'deregistered'):
            rows_skipped += 1
            continue
        
        # Purpose/classification codes - try various column names
        purposes = (row.get('gd') or row.get('purposes') or row.get('classification') or
                   row.get('GD') or '').strip()
        
        framework_area = get_framework_from_purposes(purposes)
        
        # If no purpose code match, try to infer from name keywords
        if not framework_area:
            name_lower = name.lower()
            if any(w in name_lower for w in ['school', 'college', 'university', 'education', 'learn']):
                framework_area = 'education'
            elif any(w in name_lower for w in ['health', 'hospice', 'medical', 'hospital', 'care home']):
                framework_area = 'healthcare'
            elif any(w in name_lower for w in ['housing', 'homeles', 'shelter']):
                framework_area = 'housing_land'
            elif any(w in name_lower for w in ['food bank', 'foodbank', 'food aid']):
                framework_area = 'food'
            elif any(w in name_lower for w in ['environment', 'ecology', 'conservation', 'wildlife']):
                framework_area = 'ecology'
            elif any(w in name_lower for w in ['community', 'civic', 'democracy', 'citizen']):
                framework_area = 'democracy'
            else:
                rows_skipped += 1
                continue
        
        city = (row.get('add4') or row.get('city') or row.get('CITY') or '').strip()
        postcode = (row.get('postcode') or row.get('add5') or '').strip()
        website = (row.get('web') or row.get('website') or '').strip()
        email = (row.get('email') or '').strip()
        
        try:
            income = float(row.get('income') or row.get('latest_income') or 0)
        except:
            income = 0.0
        
        batch.append((
            name, 'GB', 'United Kingdom',
            None, city, regno,
            'UK_CHARITY_NUMBER', None, website, email,
            framework_area, purposes[:50] if purposes else None,
            'UK_CHARITY_COMMISSION', regno,
            None, income, 'active', 0
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
                    website=excluded.website,
                    email=excluded.email,
                    framework_area=excluded.framework_area,
                    ntee_code=excluded.ntee_code,
                    annual_revenue=excluded.annual_revenue,
                    status=excluded.status,
                    verified=excluded.verified
                ON CONFLICT(country_code, registration_type, registration_id)
                WHERE registration_id IS NOT NULL AND TRIM(registration_id) != ''
                DO UPDATE SET
                    name=excluded.name,
                    country_name=excluded.country_name,
                    city=excluded.city,
                    website=excluded.website,
                    email=excluded.email,
                    framework_area=excluded.framework_area,
                    ntee_code=excluded.ntee_code,
                    source=excluded.source,
                    source_id=excluded.source_id,
                    annual_revenue=excluded.annual_revenue,
                    status=excluded.status,
                    verified=excluded.verified
            ''', batch)
            rows_inserted += c.rowcount
            conn.commit()
            batch = []
            db_count = conn.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]
            print(f"  Progress: {rows_read:,} read, {rows_inserted:,} inserted | DB total: {db_count:,}", flush=True)
    
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
                website=excluded.website,
                email=excluded.email,
                framework_area=excluded.framework_area,
                ntee_code=excluded.ntee_code,
                annual_revenue=excluded.annual_revenue,
                status=excluded.status,
                verified=excluded.verified
            ON CONFLICT(country_code, registration_type, registration_id)
            WHERE registration_id IS NOT NULL AND TRIM(registration_id) != ''
            DO UPDATE SET
                name=excluded.name,
                country_name=excluded.country_name,
                city=excluded.city,
                website=excluded.website,
                email=excluded.email,
                framework_area=excluded.framework_area,
                ntee_code=excluded.ntee_code,
                source=excluded.source,
                source_id=excluded.source_id,
                annual_revenue=excluded.annual_revenue,
                status=excluded.status,
                verified=excluded.verified
        ''', batch)
        rows_inserted += c.rowcount
        conn.commit()
    
    progress['total_read'] += rows_read
    progress['total_inserted'] += rows_inserted
    progress['total_skipped'] += rows_skipped
    return rows_read, rows_inserted

def main():
    print("ECO-184 / Phase 2: UK Charity Commission Ingestion", flush=True)
    conn = create_db_if_needed()
    
    existing = conn.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]
    print(f"Existing DB records: {existing:,}", flush=True)
    
    progress = {'total_read': 0, 'total_inserted': 0, 'total_skipped': 0}
    
    # Try download URLs
    urls_to_try = [
        "https://ccewuksprododata.blob.core.windows.net/assets/zip/RegEntity.zip",
        "https://ccewuksprododata.blob.core.windows.net/assets/zip/RegEntity.zip",
    ]
    
    data = None
    for url in urls_to_try:
        data = try_download(url, timeout=180)
        if data:
            break
    
    if not data:
        print("Failed to download UK data. Trying alternative approach...", flush=True)
        # Try the direct CSV endpoint
        alt_urls = [
            "https://ccewuksprododata.blob.core.windows.net/assets/zip/RegEntity.zip",
            "https://apps.charitycommission.gov.uk/Showcharity/API/SearchCharitiesV1/Searchcharities?search=&SearchFields=CharityName&StatusGroup=Registered&SubsidaryGroup=&CharityRegulator=CCEW&pageCount=100&SortOrder=CharityName&CurrentPage=0&format=CSV",
        ]
        for url in alt_urls:
            data = try_download(url, timeout=180)
            if data:
                break
    
    if not data:
        print("ERROR: Could not download UK charity data.", flush=True)
        conn.close()
        return 0
    
    # Process as ZIP
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            files = zf.namelist()
            print(f"ZIP contents: {files}", flush=True)
            
            for fname in files:
                if fname.lower().endswith('.csv'):
                    print(f"Processing {fname}...", flush=True)
                    with zf.open(fname) as f:
                        content = f.read().decode('utf-8', errors='replace')
                    process_charity_csv(content, conn, progress)
    except zipfile.BadZipFile:
        # Try as direct CSV
        print("Not a ZIP, treating as CSV...", flush=True)
        content = data.decode('utf-8', errors='replace')
        process_charity_csv(content, conn, progress)
    
    final_count = conn.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]
    uk_count = conn.execute("SELECT COUNT(*) FROM organizations WHERE country_code='GB'").fetchone()[0]
    
    print(f"\n{'='*50}", flush=True)
    print(f"ECO-184 COMPLETE", flush=True)
    print(f"Total read: {progress['total_read']:,}", flush=True)
    print(f"Total inserted: {progress['total_inserted']:,}", flush=True)
    print(f"UK records: {uk_count:,}", flush=True)
    print(f"DB total: {final_count:,}", flush=True)
    
    conn.close()
    return progress['total_inserted']

if __name__ == '__main__':
    count = main()
    sys.exit(0 if count >= 0 else 1)
