"""
Ecolibrium bulk ingestion runner - all non-US sources.
Runs phases in order, logs progress. Safe to re-run (INSERT OR IGNORE).
"""
import sqlite3, csv, urllib.request, urllib.parse, zipfile, io, json, os, time, sys, re

DB = r"C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db"
DATA = r"C:\Users\simon\.openclaw\workspace\ecolibrium\data"

FRAMEWORK_KEYWORDS = {
    'democracy': ['civic','democracy','governance','community','citizen','rights','political','vote','accountability','transparency','civil'],
    'cooperatives': ['cooperative','co-op','worker','savings','credit union','thrift','mutual benefit','solidarity','coop'],
    'healthcare': ['health','medical','hospital','clinic','malaria','hiv','maternal','nurse','disability','mental health','wellbeing'],
    'food': ['food','agriculture','farming','nutrition','hunger','agroecology','smallholder','seed','permaculture','food bank'],
    'education': ['school','education','learn','literacy','university','training','youth','library','curriculum'],
    'housing_land': ['housing','shelter','land','slum','urban','home','settlement','tenant','homeless','affordable'],
    'conflict': ['peace','conflict','justice','violence','reconciliation','refugee','displaced','restorative','mediation','abolition'],
    'energy_digital': ['energy','solar','electricity','digital','tech','internet','connectivity','open source','data rights','renewable'],
    'recreation_arts': ['arts','culture','music','dance','heritage','sport','recreation','theater','museum','creative'],
    'ecology': ['environment','ecology','conservation','forest','water','climate','nature','wildlife','biodiversity','restoration'],
}

def conn():
    c = sqlite3.connect(DB)
    c.execute('PRAGMA journal_mode=WAL')
    return c

def guess_area(text):
    text = text.lower()
    scores = {a: sum(1 for kw in kws if kw in text) for a, kws in FRAMEWORK_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None

def insert_batch(db, batch):
    db.executemany('''INSERT OR IGNORE INTO organizations
        (name,country_code,country_name,state_province,city,registration_id,registration_type,
         description,website,email,framework_area,ntee_code,icnpo_code,source,source_id,
         last_filing_year,annual_revenue,status,verified)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', batch)
    db.commit()
    return db.execute('SELECT changes()').fetchone()[0]

def fetch(url, timeout=120):
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 EcolibiumBot/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f"  FETCH FAIL {url}: {e}", flush=True)
        return None

def log_source(db, name, count, coverage, notes):
    db.execute('''INSERT OR REPLACE INTO sources (name,org_count,coverage,last_pulled,notes)
        VALUES (?,?,?,date('now'),?)''', (name, count, coverage, notes))
    db.commit()

# ─── PHASE: ACNC Australia ────────────────────────────────────────────────────
def run_acnc():
    print("\n=== PHASE: ACNC Australia ===", flush=True)
    db = conn()
    existing = db.execute("SELECT COUNT(*) FROM organizations WHERE country_code='AU'").fetchone()[0]
    print(f"  Existing AU records: {existing:,}", flush=True)

    # ACNC provides a bulk CSV download
    url = "https://www.acnc.gov.au/tools/data-explorer"
    # Direct data URL - try multiple
    data_urls = [
        "https://data.gov.au/data/dataset/b050b242-4487-4d04-89e2-3dccf9c25d63/resource/5a930977-8f5e-4a74-80cf-8cca01de3cd6/download/acncregister.csv",
        "https://acnc.gov.au/sites/default/files/2024-01/ACNC-Registered-Charities-1-January-2024.csv",
    ]

    data = None
    for u in data_urls:
        data = fetch(u, timeout=180)
        if data:
            print(f"  Downloaded {len(data):,} bytes from {u}", flush=True)
            break

    if not data:
        print("  ACNC direct download failed. Trying data.gov.au search...", flush=True)
        search = fetch("https://data.gov.au/api/3/action/package_search?q=acnc+charities&rows=5")
        if search:
            results = json.loads(search)
            for pkg in results.get('result',{}).get('results',[]):
                for res in pkg.get('resources',[]):
                    if res.get('format','').upper() in ('CSV','ZIP'):
                        data = fetch(res['url'], timeout=240)
                        if data:
                            print(f"  Got data from data.gov.au: {len(data):,} bytes", flush=True)
                            break
                if data:
                    break

    if not data:
        print("  ACNC: Could not download. Skipping.", flush=True)
        return 0

    # Try as ZIP first
    content = None
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for fname in zf.namelist():
                if fname.lower().endswith('.csv'):
                    content = zf.open(fname).read().decode('utf-8', errors='replace')
                    print(f"  Extracted {fname} from ZIP", flush=True)
                    break
    except:
        content = data.decode('utf-8', errors='replace')

    if not content:
        print("  Could not parse ACNC data.", flush=True)
        return 0

    reader = csv.DictReader(io.StringIO(content))
    print(f"  Columns: {list(reader.fieldnames or [])[:8]}", flush=True)

    batch = []
    inserted = skipped = read = 0

    for row in reader:
        read += 1
        name = (row.get('Charity_Legal_Name') or row.get('charity_legal_name') or
                row.get('Name') or row.get('name') or '').strip()
        if not name:
            skipped += 1
            continue

        purposes = (row.get('Charity_Activities') or row.get('charity_activities') or
                   row.get('Main_Activity') or row.get('main_activity') or '').strip()
        area = guess_area(name + ' ' + purposes)
        if not area:
            skipped += 1
            continue

        abn = (row.get('ABN') or row.get('abn') or '').strip()
        city = (row.get('Town_City') or row.get('town_city') or row.get('City') or '').strip()
        state = (row.get('State') or row.get('state') or '').strip()
        website = (row.get('Website') or row.get('website') or '').strip()

        batch.append((name,'AU','Australia',state,city,abn,'ACNC_ABN',
                      purposes[:200] if purposes else None,website,None,
                      area,None,None,'ACNC',abn,None,0.0,'active',0))

        if len(batch) >= 1000:
            inserted += insert_batch(db, batch)
            batch = []
            total = db.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]
            print(f"  Progress: {read:,} read | {inserted:,} inserted | DB: {total:,}", flush=True)

    if batch:
        inserted += insert_batch(db, batch)

    log_source(db, 'ACNC', inserted, 'Australia', f'read={read} skipped={skipped}')
    total = db.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]
    print(f"  ACNC complete: {inserted:,} inserted | DB total: {total:,}", flush=True)
    db.close()
    return inserted

# ─── PHASE: ProPublica API enrichment ─────────────────────────────────────────
def run_propublica():
    print("\n=== PHASE: ProPublica Nonprofit Explorer (enrichment) ===", flush=True)
    db = conn()
    existing = db.execute("SELECT COUNT(*) FROM organizations WHERE source='ProPublica'").fetchone()[0]
    print(f"  Existing ProPublica records: {existing:,}", flush=True)

    queries = [
        ('cooperative','cooperatives'), ('food sovereignty','food'), ('community land trust','housing_land'),
        ('restorative justice','conflict'), ('renewable energy cooperative','energy_digital'),
        ('civic technology','democracy'), ('agroecology','food'), ('mutual aid','cooperatives'),
        ('environmental justice','ecology'), ('community health center','healthcare'),
        ('indigenous rights','democracy'), ('worker cooperative','cooperatives'),
        ('housing cooperative','housing_land'), ('community development finance','cooperatives'),
        ('open source technology','energy_digital'),
    ]

    inserted = total_read = 0
    for query, area_hint in queries:
        page = 0
        while page < 5:  # max 5 pages per query
            url = f"https://projects.propublica.org/nonprofits/api/v2/search.json?q={urllib.parse.quote(query)}&page={page}"
            data = fetch(url, timeout=30)
            if not data:
                break
            try:
                results = json.loads(data)
                orgs = results.get('organizations', [])
                if not orgs:
                    break
                batch = []
                for o in orgs:
                    name = (o.get('name') or '').strip()
                    if not name:
                        continue
                    ein = str(o.get('ein') or '')
                    state = (o.get('state') or '').strip()
                    city = (o.get('city') or '').strip()
                    ntee = (o.get('ntee_code') or '').strip()
                    revenue = float(o.get('revenue_amount') or 0)
                    year = o.get('tax_prd_yr')
                    total_read += 1
                    batch.append((name,'US','United States',state,city,ein,'IRS_EIN',
                                  None,None,None,area_hint,ntee,None,'ProPublica',ein,
                                  year,revenue,'active',0))
                if batch:
                    inserted += insert_batch(db, batch)
                page += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"  Parse error: {e}", flush=True)
                break

        time.sleep(0.5)

    log_source(db, 'ProPublica', inserted, 'USA enrichment', f'queries={len(queries)} read={total_read}')
    total = db.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]
    print(f"  ProPublica complete: {inserted:,} new | DB total: {total:,}", flush=True)
    db.close()
    return inserted

# ─── PHASE: Canada CRA ────────────────────────────────────────────────────────
def run_canada():
    print("\n=== PHASE: Canada CRA Charities ===", flush=True)
    db = conn()
    existing = db.execute("SELECT COUNT(*) FROM organizations WHERE country_code='CA'").fetchone()[0]
    print(f"  Existing CA records: {existing:,}", flush=True)

    # CRA provides a downloadable list
    urls = [
        "https://apps.cra-arc.gc.ca/ebci/hacc/srch/pub/fileDownload?fileId=t3010ListingEn",
        "https://www.canada.ca/content/dam/cra-arc/prog-policy/charities/registered-charity-information-return/t3010-listing.zip",
    ]
    data = None
    for u in urls:
        data = fetch(u, timeout=180)
        if data:
            print(f"  Downloaded {len(data):,} bytes", flush=True)
            break

    if not data:
        print("  Canada CRA: Download failed. Skipping.", flush=True)
        return 0

    content = None
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for fname in zf.namelist():
                if fname.lower().endswith('.csv') or fname.lower().endswith('.txt'):
                    content = zf.open(fname).read().decode('utf-8', errors='replace')
                    print(f"  Extracted {fname}", flush=True)
                    break
    except:
        content = data.decode('utf-8', errors='replace')

    if not content:
        return 0

    reader = csv.DictReader(io.StringIO(content))
    print(f"  Columns: {list(reader.fieldnames or [])[:8]}", flush=True)

    batch = []
    inserted = skipped = read = 0
    for row in reader:
        read += 1
        name = (row.get('Organization legal name') or row.get('Charity Name') or
                row.get('name') or '').strip()
        if not name:
            skipped += 1
            continue
        area = guess_area(name)
        if not area:
            skipped += 1
            continue
        reg = (row.get('Registration number') or row.get('BN') or '').strip()
        city = (row.get('City') or '').strip()
        prov = (row.get('Province') or row.get('State') or '').strip()
        website = (row.get('Website') or '').strip()

        batch.append((name,'CA','Canada',prov,city,reg,'CRA_BN',None,website,None,
                      area,None,None,'CRA_Canada',reg,None,0.0,'active',0))

        if len(batch) >= 1000:
            inserted += insert_batch(db, batch)
            batch = []

    if batch:
        inserted += insert_batch(db, batch)

    log_source(db, 'CRA_Canada', inserted, 'Canada', f'read={read} skipped={skipped}')
    total = db.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]
    print(f"  Canada complete: {inserted:,} inserted | DB total: {total:,}", flush=True)
    db.close()
    return inserted

# ─── PHASE: New Zealand Charities Register ────────────────────────────────────
def run_nz():
    print("\n=== PHASE: New Zealand Charities Register ===", flush=True)
    db = conn()
    # NZ provides a downloadable CSV
    urls = [
        "https://www.charities.govt.nz/assets/Charities-Register.csv",
        "https://charities.govt.nz/charities-in-new-zealand/the-charities-register/open-data/",
    ]
    data = None
    for u in urls:
        data = fetch(u, timeout=120)
        if data and b',' in data[:100]:
            print(f"  Got NZ data: {len(data):,} bytes", flush=True)
            break

    if not data:
        print("  NZ: Download failed. Skipping.", flush=True)
        return 0

    content = data.decode('utf-8', errors='replace')
    reader = csv.DictReader(io.StringIO(content))
    print(f"  Columns: {list(reader.fieldnames or [])[:8]}", flush=True)

    batch = []
    inserted = skipped = read = 0
    for row in reader:
        read += 1
        name = (row.get('Charity Name') or row.get('Name') or '').strip()
        if not name:
            skipped += 1
            continue
        purposes = (row.get('Purposes') or row.get('Activities') or row.get('Description') or '').strip()
        area = guess_area(name + ' ' + purposes)
        if not area:
            skipped += 1
            continue
        reg = (row.get('Charity Number') or row.get('Registration Number') or '').strip()
        city = (row.get('City') or row.get('Town') or '').strip()
        website = (row.get('Website') or '').strip()

        batch.append((name,'NZ','New Zealand',None,city,reg,'NZ_CHARITY_NUM',
                      purposes[:200] if purposes else None,website,None,
                      area,None,None,'NZ_Charities',reg,None,0.0,'active',0))

        if len(batch) >= 500:
            inserted += insert_batch(db, batch)
            batch = []

    if batch:
        inserted += insert_batch(db, batch)

    log_source(db, 'NZ_Charities', inserted, 'New Zealand', f'read={read}')
    total = db.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]
    print(f"  NZ complete: {inserted:,} inserted | DB total: {total:,}", flush=True)
    db.close()
    return inserted

if __name__ == '__main__':
    print("Ecolibrium Bulk Ingestion - International Sources", flush=True)
    db = sqlite3.connect(DB)
    start = db.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]
    print(f"Starting DB count: {start:,}", flush=True)
    db.close()

    results = {}
    results['propublica'] = run_propublica()
    results['acnc'] = run_acnc()
    results['canada'] = run_canada()
    results['nz'] = run_nz()

    db = sqlite3.connect(DB)
    final = db.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]
    print(f"\n{'='*50}")
    print(f"All phases complete. DB: {start:,} -> {final:,} (+{final-start:,})")
    print(f"Results: {results}")
    breakdown = db.execute('SELECT framework_area,COUNT(*) FROM organizations GROUP BY framework_area ORDER BY COUNT(*) DESC').fetchall()
    print("\nFramework breakdown:")
    for a, c in breakdown:
        print(f"  {a}: {c:,}")
    db.close()
