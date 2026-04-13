"""
Phase 1b: Geocode all organizations in the DB.
- US orgs: try city exact match, fall back to state centroid
- International: use country centroid
"""
import sqlite3
import urllib.request
import csv
import io
import os

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'
CACHE_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\us_cities_cache.csv'

STATE_CENTROIDS = {
    'AL':(32.8,-86.8),'AK':(64.2,-153.4),'AZ':(34.3,-111.1),'AR':(34.8,-92.2),
    'CA':(36.8,-119.4),'CO':(39.0,-105.5),'CT':(41.6,-72.7),'DE':(39.0,-75.5),
    'FL':(27.8,-81.6),'GA':(32.2,-83.4),'HI':(19.9,-155.6),'ID':(44.2,-114.5),
    'IL':(40.0,-89.2),'IN':(39.8,-86.1),'IA':(42.0,-93.2),'KS':(38.5,-98.4),
    'KY':(37.7,-84.9),'LA':(30.8,-92.0),'ME':(44.7,-69.4),'MD':(39.1,-76.8),
    'MA':(42.2,-71.5),'MI':(44.4,-85.4),'MN':(46.4,-93.1),'MS':(32.7,-89.7),
    'MO':(38.3,-92.6),'MT':(47.0,-110.4),'NE':(41.5,-99.9),'NV':(39.3,-116.6),
    'NH':(43.7,-71.6),'NJ':(40.1,-74.5),'NM':(34.8,-106.2),'NY':(42.2,-74.9),
    'NC':(35.6,-79.8),'ND':(47.5,-100.5),'OH':(40.2,-82.8),'OK':(35.6,-96.9),
    'OR':(44.6,-122.1),'PA':(40.6,-77.2),'RI':(41.7,-71.5),'SC':(33.9,-80.9),
    'SD':(44.5,-100.4),'TN':(35.7,-86.7),'TX':(31.1,-97.6),'UT':(39.3,-111.1),
    'VT':(44.1,-72.7),'VA':(37.5,-78.5),'WA':(47.4,-120.5),'WV':(38.6,-80.6),
    'WI':(43.8,-89.7),'WY':(43.0,-107.6),'DC':(38.9,-77.0),'PR':(18.2,-66.6),
    'GU':(13.44,144.79),'VI':(18.34,-64.90),'AS':(-14.27,-170.13),'MP':(15.19,145.75),
}

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


def load_city_lookup():
    """Load US city -> (lat, lon) dict from CSV (cached locally or downloaded)."""
    city_lookup = {}
    
    # Try loading from cache
    if os.path.exists(CACHE_PATH):
        print(f'Loading US cities from cache: {CACHE_PATH}')
        try:
            with open(CACHE_PATH, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        city = row.get('city', row.get('CITY', '')).upper().strip()
                        state = row.get('state_id', row.get('STATE_CODE', row.get('state', ''))).upper().strip()
                        lat = float(row.get('lat', row.get('LAT', 0)))
                        lng = float(row.get('lng', row.get('LON', row.get('lon', 0))))
                        if city and state and lat and lng:
                            key = (city, state)
                            if key not in city_lookup:
                                city_lookup[key] = (lat, lng)
                    except (ValueError, KeyError):
                        pass
            if city_lookup:
                print(f'Loaded {len(city_lookup):,} cities from cache')
                return city_lookup
        except Exception as e:
            print(f'Cache load error: {e}')
    
    # Try downloading
    urls = [
        'https://raw.githubusercontent.com/kelvins/US-Cities-Database/main/csv/us_cities.csv',
        'https://raw.githubusercontent.com/grammakov/USA-cities-and-states/master/us_cities_states_counties.csv',
    ]
    
    for url in urls:
        try:
            print(f'Downloading city data from: {url}')
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read().decode('utf-8', errors='replace')
            
            # Save cache
            with open(CACHE_PATH, 'w', encoding='utf-8') as f:
                f.write(data)
            
            reader = csv.DictReader(io.StringIO(data))
            fieldnames = reader.fieldnames or []
            print(f'  Columns: {fieldnames[:10]}')
            
            for row in reader:
                try:
                    city = (row.get('city') or row.get('CITY') or row.get('CITY_NAME') or '').upper().strip()
                    state = (row.get('state_id') or row.get('STATE_CODE') or row.get('STATE') or '').upper().strip()
                    lat = float(row.get('lat') or row.get('LAT') or row.get('LATITUDE') or 0)
                    lng = float(row.get('lng') or row.get('LON') or row.get('LONGITUDE') or 0)
                    if city and state and lat and lng:
                        key = (city, state)
                        if key not in city_lookup:
                            city_lookup[key] = (lat, lng)
                except (ValueError, KeyError):
                    pass
            
            if city_lookup:
                print(f'Downloaded {len(city_lookup):,} cities')
                return city_lookup
                
        except Exception as e:
            print(f'  Failed: {e}')
    
    print('All downloads failed, using state centroids only')
    return {}


def geocode_all():
    city_lookup = load_city_lookup()
    
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    
    # Get total count
    c.execute('SELECT COUNT(*) FROM organizations')
    total = c.fetchone()[0]
    print(f'Total orgs: {total:,}')
    
    batch_size = 20000
    offset = 0
    stats = {'city_exact': 0, 'state_centroid': 0, 'country_centroid': 0, 'no_geo': 0}
    processed = 0
    
    while True:
        c.execute('''
            SELECT id, country_code, state_province, city 
            FROM organizations 
            ORDER BY id 
            LIMIT ? OFFSET ?
        ''', (batch_size, offset))
        rows = c.fetchall()
        if not rows:
            break
        
        updates = []
        for row in rows:
            org_id, cc, state, city = row
            lat, lon, geo_source = None, None, None
            
            if cc == 'US':
                # Try city exact match
                if city and state:
                    city_upper = city.upper().strip()
                    state_upper = state.upper().strip()
                    if (city_upper, state_upper) in city_lookup:
                        lat, lon = city_lookup[(city_upper, state_upper)]
                        geo_source = 'city_exact'
                
                # Fall back to state centroid
                if lat is None and state:
                    state_upper = state.upper().strip()
                    if state_upper in STATE_CENTROIDS:
                        lat, lon = STATE_CENTROIDS[state_upper]
                        geo_source = 'state_centroid'
            
            elif cc and cc in COUNTRY_CENTROIDS:
                lat, lon = COUNTRY_CENTROIDS[cc]
                geo_source = 'country_centroid'
            
            if lat is not None:
                updates.append((lat, lon, geo_source, org_id))
                stats[geo_source] = stats.get(geo_source, 0) + 1
            else:
                stats['no_geo'] += 1
        
        if updates:
            c.executemany('UPDATE organizations SET lat=?, lon=?, geo_source=? WHERE id=?', updates)
            db.commit()
        
        processed += len(rows)
        print(f'  Processed {processed:,}/{total:,} ({len(updates)} geocoded in batch)')
        offset += batch_size
    
    db.close()
    
    print('\n=== Geocoding Complete ===')
    print(f'city_exact: {stats["city_exact"]:,}')
    print(f'state_centroid: {stats["state_centroid"]:,}')
    print(f'country_centroid: {stats["country_centroid"]:,}')
    print(f'no_geo: {stats["no_geo"]:,}')
    total_geo = stats['city_exact'] + stats['state_centroid'] + stats['country_centroid']
    print(f'Total geocoded: {total_geo:,} / {total:,}')


if __name__ == '__main__':
    geocode_all()
