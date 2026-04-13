"""
Phase 4: Build map_points.json and map_meta.json for the live map.
"""
import sqlite3
import json
import os
from collections import defaultdict

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'
SEARCH_DIR = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\search'
MAP_POINTS_PATH = os.path.join(SEARCH_DIR, 'map_points.json')
MAP_META_PATH = os.path.join(SEARCH_DIR, 'map_meta.json')

MAX_PER_STATE = 3000


def run():
    os.makedirs(SEARCH_DIR, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    c = db.cursor()
    
    points = []
    state_counts = defaultdict(int)
    area_counts = defaultdict(int)
    country_counts = defaultdict(int)
    
    # US orgs: sample up to MAX_PER_STATE per state
    # For IRS_EO_BMF source: only include if alignment_score >= 2
    # For all other sources: include all active with lat
    print('Processing US orgs...')
    
    # Get distinct states
    c.execute("SELECT DISTINCT state_province FROM organizations WHERE country_code='US' AND lat IS NOT NULL AND status='active'")
    states = [r[0] for r in c.fetchall() if r[0]]
    print(f'  States: {len(states)}')
    
    for state in states:
        # Non-IRS sources: all active with lat
        c.execute("""
            SELECT name, lat, lon, framework_area, model_type, website, description, country_code, annual_revenue, source
            FROM organizations
            WHERE country_code='US' AND state_province=? AND lat IS NOT NULL AND status='active'
              AND (source != 'IRS_EO_BMF' OR alignment_score >= 2)
            ORDER BY annual_revenue DESC NULLS LAST, name ASC
            LIMIT ?
        """, (state, MAX_PER_STATE))
        rows = c.fetchall()
        
        for row in rows:
            name, lat, lon, area, mtype, website, desc, cc, revenue, source = row
            if lat is None or lon is None:
                continue
            
            # Clean website
            if website:
                website = website.replace('https://', '').replace('http://', '').rstrip('/')
                if len(website) > 60:
                    website = website[:60]
            
            # Truncate description
            if desc and len(desc) > 150:
                desc = desc[:150].rsplit(' ', 1)[0] + '...'
            
            point = {
                'n': name[:80] if name else '',
                'la': round(lat, 4),
                'lo': round(lon, 4),
                'f': area or 'democracy',
                'm': mtype or 'nonprofit',
            }
            if website:
                point['w'] = website
            if desc:
                point['d'] = desc
            if cc != 'US':
                point['cc'] = cc
            if revenue:
                point['r'] = int(revenue)
            
            points.append(point)
            state_counts[state] += 1
            area_counts[area or 'democracy'] += 1
            country_counts['US'] += 1
    
    print(f'  US points: {sum(state_counts.values()):,}')
    
    # International orgs: include all active with lat (any source)
    print('Processing international orgs...')
    c.execute("""
        SELECT name, lat, lon, framework_area, model_type, website, description, country_code, annual_revenue
        FROM organizations
        WHERE country_code != 'US' AND lat IS NOT NULL AND status='active'
        ORDER BY country_code, name
    """)
    rows = c.fetchall()
    
    intl_count = 0
    for row in rows:
        name, lat, lon, area, mtype, website, desc, cc, revenue = row
        if lat is None or lon is None:
            continue
        
        if website:
            website = website.replace('https://', '').replace('http://', '').rstrip('/')
            if len(website) > 60:
                website = website[:60]
        
        if desc and len(desc) > 150:
            desc = desc[:150].rsplit(' ', 1)[0] + '...'
        
        point = {
            'n': name[:80] if name else '',
            'la': round(lat, 4),
            'lo': round(lon, 4),
            'f': area or 'democracy',
            'm': mtype or 'nonprofit',
            'cc': cc or '',
        }
        if website:
            point['w'] = website
        if desc:
            point['d'] = desc
        if revenue:
            point['r'] = int(revenue)
        
        points.append(point)
        area_counts[area or 'democracy'] += 1
        country_counts[cc or 'unknown'] += 1
        intl_count += 1
    
    print(f'  International points: {intl_count:,}')
    print(f'  Total points: {len(points):,}')
    
    db.close()
    
    # Write map_points.json
    with open(MAP_POINTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(points, f, separators=(',', ':'))
    
    file_size = os.path.getsize(MAP_POINTS_PATH)
    print(f'\nWrote map_points.json: {file_size/1024/1024:.1f} MB ({len(points):,} points)')
    
    # Build meta
    meta = {
        'total': len(points),
        'us_count': country_counts.get('US', 0),
        'intl_count': intl_count,
        'by_area': dict(sorted(area_counts.items(), key=lambda x: -x[1])),
        'by_country': dict(sorted(country_counts.items(), key=lambda x: -x[1])[:30]),
        'by_state': dict(sorted(state_counts.items(), key=lambda x: -x[1])[:10]),
    }
    
    with open(MAP_META_PATH, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    
    meta_size = os.path.getsize(MAP_META_PATH)
    print(f'Wrote map_meta.json: {meta_size} bytes')
    
    print('\nBy framework area:')
    for area, cnt in sorted(area_counts.items(), key=lambda x: -x[1]):
        print(f'  {area}: {cnt:,}')
    
    print('\nTop countries:')
    for cc, cnt in sorted(country_counts.items(), key=lambda x: -x[1])[:10]:
        print(f'  {cc}: {cnt:,}')


if __name__ == '__main__':
    run()
