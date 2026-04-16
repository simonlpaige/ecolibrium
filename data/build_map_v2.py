"""
Map V2 data pipeline:
1. Assign quality tiers (A/B/C/D) to all orgs
2. Generate derived network edges (same-section proximity)
3. Pre-compute country aggregates for choropleth
4. Compute System Completeness scores per region
5. Output: map_points_v2.json, map_edges.json, map_aggregates.json
"""
import sqlite3
import json
import os
import math
from collections import defaultdict, Counter

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'
SEARCH_DIR = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\search'

# Framework sections
SECTIONS = [
    'democracy', 'cooperatives', 'healthcare', 'food', 'education',
    'housing_land', 'conflict', 'energy_digital', 'recreation_arts', 'ecology'
]

# Complementary section pairs (cross-section edges)
COMPLEMENTARY = {
    ('food', 'housing_land'), ('food', 'cooperatives'), ('food', 'ecology'),
    ('housing_land', 'cooperatives'), ('housing_land', 'democracy'),
    ('healthcare', 'education'), ('healthcare', 'conflict'),
    ('energy_digital', 'cooperatives'), ('energy_digital', 'democracy'),
    ('education', 'democracy'), ('ecology', 'food'),
}

def haversine_km(lat1, lon1, lat2, lon2):
    """Fast haversine distance in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def assign_tiers(db):
    """Assign quality tiers based on data completeness."""
    c = db.cursor()
    
    # Tier A: verified=1 AND has description AND has website
    c.execute("""UPDATE organizations SET tags = 'tier_a' 
                 WHERE status='active' AND verified=1 
                 AND description IS NOT NULL AND description != ''
                 AND website IS NOT NULL AND website != ''""")
    tier_a = c.rowcount
    
    # Tier B: has description OR (verified AND has website) OR source in (web_research, manual_curation, ProPublica)
    c.execute("""UPDATE organizations SET tags = 'tier_b'
                 WHERE status='active' AND (tags IS NULL OR tags = '')
                 AND (
                     (description IS NOT NULL AND description != '')
                     OR (verified=1 AND website IS NOT NULL AND website != '')
                     OR source IN ('web_research', 'manual_curation', 'ProPublica')
                 )""")
    tier_b = c.rowcount
    
    # Tier C: alignment_score >= 3 (meaningful keyword match)
    c.execute("""UPDATE organizations SET tags = 'tier_c'
                 WHERE status='active' AND (tags IS NULL OR tags = '')
                 AND alignment_score >= 3""")
    tier_c = c.rowcount
    
    # Tier D: everything else that's active
    c.execute("""UPDATE organizations SET tags = 'tier_d'
                 WHERE status='active' AND (tags IS NULL OR tags = '')""")
    tier_d = c.rowcount
    
    db.commit()
    print(f"Tier A (curated):    {tier_a:>8,}")
    print(f"Tier B (matched):    {tier_b:>8,}")
    print(f"Tier C (inferred):   {tier_c:>8,}")
    print(f"Tier D (unverified): {tier_d:>8,}")
    return {'A': tier_a, 'B': tier_b, 'C': tier_c, 'D': tier_d}


def build_map_points(db):
    """Extract map-worthy points (Tier A, B, C only)."""
    c = db.cursor()
    
    # Get all Tier A/B/C orgs with coordinates
    c.execute("""
        SELECT id, name, lat, lon, framework_area, model_type, website, description,
               country_code, state_province, annual_revenue, source, tags, alignment_score
        FROM organizations
        WHERE status='active' AND lat IS NOT NULL AND lon IS NOT NULL
          AND tags IN ('tier_a', 'tier_b', 'tier_c')
        ORDER BY 
            CASE tags WHEN 'tier_a' THEN 0 WHEN 'tier_b' THEN 1 ELSE 2 END,
            annual_revenue DESC NULLS LAST
    """)
    
    points = []
    points_by_id = {}
    
    for row in c.fetchall():
        org_id, name, lat, lon, area, mtype, website, desc, cc, state, revenue, source, tier, align = row
        
        tier_letter = tier.replace('tier_', '').upper() if tier else 'D'
        
        # Truncate fields
        if website:
            website = website.replace('https://', '').replace('http://', '').rstrip('/')
            if len(website) > 60:
                website = website[:60]
        if desc and len(desc) > 150:
            desc = desc[:150].rsplit(' ', 1)[0] + '...'
        
        point = {
            'id': org_id,
            'n': (name or '')[:80],
            'la': round(lat, 4),
            'lo': round(lon, 4),
            'f': area or 'democracy',
            'm': mtype or 'nonprofit',
            't': tier_letter,
            'cc': cc or 'US',
        }
        if website: point['w'] = website
        if desc: point['d'] = desc
        if revenue and revenue > 0: point['r'] = int(revenue)
        if state: point['st'] = state
        if source: point['src'] = source
        
        points.append(point)
        points_by_id[org_id] = point
    
    print(f"\nMap points: {len(points):,}")
    tier_counts = Counter(p['t'] for p in points)
    for t in ['A', 'B', 'C']:
        print(f"  Tier {t}: {tier_counts.get(t, 0):,}")
    
    return points, points_by_id


def build_edges(points, max_distance_km=50, max_edges_per_org=5):
    """Generate derived proximity edges between nearby same-section and complementary-section orgs."""
    print(f"\nBuilding edges (max {max_distance_km}km, max {max_edges_per_org}/org)...")
    
    # Only use Tier A and B for edges (higher quality)
    tier_ab = [p for p in points if p['t'] in ('A', 'B')]
    print(f"  Using {len(tier_ab):,} Tier A/B points for edge computation")
    
    if len(tier_ab) > 15000:
        print(f"  WARNING: {len(tier_ab)} points - edge computation may be slow")
    
    # Spatial index: group by rough grid cell (~50km cells)
    CELL_SIZE = 0.5  # degrees, roughly 50km at mid-latitudes
    grid = defaultdict(list)
    for p in tier_ab:
        cell = (int(p['la'] / CELL_SIZE), int(p['lo'] / CELL_SIZE))
        grid[cell].append(p)
    
    edges = []
    edge_count_per_org = defaultdict(int)
    seen_pairs = set()
    
    for cell, cell_points in grid.items():
        # Check this cell and its 8 neighbors
        neighbor_points = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                ncell = (cell[0] + dx, cell[1] + dy)
                if ncell in grid:
                    neighbor_points.extend(grid[ncell])
        
        for p1 in cell_points:
            if edge_count_per_org[p1['id']] >= max_edges_per_org:
                continue
                
            candidates = []
            for p2 in neighbor_points:
                if p1['id'] >= p2['id']:
                    continue
                pair = (p1['id'], p2['id'])
                if pair in seen_pairs:
                    continue
                
                # Check section relationship
                same_section = p1['f'] == p2['f']
                complementary = (p1['f'], p2['f']) in COMPLEMENTARY or (p2['f'], p1['f']) in COMPLEMENTARY
                
                if not same_section and not complementary:
                    continue
                
                dist = haversine_km(p1['la'], p1['lo'], p2['la'], p2['lo'])
                if dist <= max_distance_km and dist > 0.5:  # min 500m to avoid self-links
                    edge_type = 'same_section' if same_section else 'complementary'
                    weight = max(0.1, 1.0 - (dist / max_distance_km))
                    candidates.append((dist, weight, p2, edge_type, pair))
            
            # Take top N closest
            candidates.sort(key=lambda x: x[0])
            for dist, weight, p2, edge_type, pair in candidates[:max_edges_per_org]:
                if edge_count_per_org[p1['id']] >= max_edges_per_org:
                    break
                if edge_count_per_org[p2['id']] >= max_edges_per_org:
                    continue
                    
                edges.append({
                    's': [p1['lo'], p1['la']],  # source [lng, lat]
                    't': [p2['lo'], p2['la']],  # target [lng, lat]
                    'e': edge_type[0],           # 's' or 'c'
                    'f': p1['f'],                # section (for coloring)
                    'w': round(weight, 2),
                })
                seen_pairs.add(pair)
                edge_count_per_org[p1['id']] += 1
                edge_count_per_org[p2['id']] += 1
    
    print(f"  Generated {len(edges):,} edges")
    type_counts = Counter(e['e'] for e in edges)
    print(f"    Same-section: {type_counts.get('s', 0):,}")
    print(f"    Complementary: {type_counts.get('c', 0):,}")
    
    return edges


def build_country_aggregates(db):
    """Pre-compute per-country stats for choropleth layer."""
    c = db.cursor()
    
    c.execute("""
        SELECT country_code, framework_area, COUNT(*), SUM(CASE WHEN verified=1 THEN 1 ELSE 0 END),
               SUM(CASE WHEN tags='tier_a' THEN 1 WHEN tags='tier_b' THEN 1 ELSE 0 END)
        FROM organizations
        WHERE status='active' AND framework_area IS NOT NULL
        GROUP BY country_code, framework_area
    """)
    
    countries = defaultdict(lambda: {
        'total': 0, 'verified': 0, 'quality': 0,
        'sections': defaultdict(int), 'completeness': 0
    })
    
    for cc, area, count, verified, quality in c.fetchall():
        if not cc:
            continue
        countries[cc]['total'] += count
        countries[cc]['verified'] += (verified or 0)
        countries[cc]['quality'] += (quality or 0)
        countries[cc]['sections'][area] = count
    
    # Compute System Completeness score (0-100)
    for cc, data in countries.items():
        sections_present = len([s for s in SECTIONS if data['sections'].get(s, 0) > 0])
        section_coverage = sections_present / len(SECTIONS)
        
        # Weight by quality ratio
        quality_ratio = data['quality'] / max(data['total'], 1)
        
        # Completeness = section coverage * (0.5 + 0.5 * quality_weight)
        data['completeness'] = round(section_coverage * (0.5 + 0.5 * quality_ratio) * 100, 1)
        data['sections_present'] = sections_present
        
        # Convert sections defaultdict to regular dict for JSON
        data['sections'] = dict(data['sections'])
    
    print(f"\nCountry aggregates: {len(countries)} countries")
    
    # Top 10 by completeness
    top = sorted(countries.items(), key=lambda x: -x[1]['completeness'])[:10]
    print("Top completeness:")
    for cc, data in top:
        print(f"  {cc}: {data['completeness']:.1f}% ({data['sections_present']}/{len(SECTIONS)} sections, {data['total']:,} orgs)")
    
    return dict(countries)


def build_state_aggregates(db):
    """Pre-compute per-US-state stats for regional completeness."""
    c = db.cursor()
    
    c.execute("""
        SELECT state_province, framework_area, COUNT(*)
        FROM organizations
        WHERE status='active' AND country_code='US' AND state_province IS NOT NULL
          AND framework_area IS NOT NULL AND tags IN ('tier_a', 'tier_b', 'tier_c')
        GROUP BY state_province, framework_area
    """)
    
    states = defaultdict(lambda: {'total': 0, 'sections': defaultdict(int)})
    
    for state, area, count in c.fetchall():
        states[state]['total'] += count
        states[state]['sections'][area] = count
    
    for state, data in states.items():
        sections_present = len([s for s in SECTIONS if data['sections'].get(s, 0) > 0])
        data['completeness'] = round((sections_present / len(SECTIONS)) * 100, 1)
        data['sections_present'] = sections_present
        data['sections'] = dict(data['sections'])
    
    return dict(states)


def main():
    os.makedirs(SEARCH_DIR, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    
    print("=" * 60)
    print("ECOLIBRIUM MAP V2 DATA PIPELINE")
    print("=" * 60)
    
    # Step 1: Assign tiers
    print("\n--- Step 1: Assigning quality tiers ---")
    tier_counts = assign_tiers(db)
    
    # Step 2: Build map points
    print("\n--- Step 2: Building map points ---")
    points, points_by_id = build_map_points(db)
    
    # Step 3: Build edges
    print("\n--- Step 3: Building network edges ---")
    edges = build_edges(points)
    
    # Step 4: Country aggregates
    print("\n--- Step 4: Building country aggregates ---")
    country_aggs = build_country_aggregates(db)
    
    # Step 5: State aggregates
    print("\n--- Step 5: Building US state aggregates ---")
    state_aggs = build_state_aggregates(db)
    
    db.close()
    
    # Strip internal IDs from points before export
    export_points = []
    for p in points:
        ep = {k: v for k, v in p.items() if k != 'id'}
        export_points.append(ep)
    
    # Write outputs
    print("\n--- Writing outputs ---")
    
    pts_path = os.path.join(SEARCH_DIR, 'map_points_v2.json')
    with open(pts_path, 'w') as f:
        json.dump(export_points, f, separators=(',', ':'))
    print(f"  map_points_v2.json: {os.path.getsize(pts_path)/1024:.0f} KB ({len(export_points):,} points)")
    
    edges_path = os.path.join(SEARCH_DIR, 'map_edges.json')
    with open(edges_path, 'w') as f:
        json.dump(edges, f, separators=(',', ':'))
    print(f"  map_edges.json: {os.path.getsize(edges_path)/1024:.0f} KB ({len(edges):,} edges)")
    
    aggs_path = os.path.join(SEARCH_DIR, 'map_aggregates.json')
    aggs = {
        'countries': country_aggs,
        'us_states': state_aggs,
        'tier_counts': tier_counts,
        'sections': SECTIONS,
        'total_points': len(export_points),
        'total_edges': len(edges),
    }
    with open(aggs_path, 'w') as f:
        json.dump(aggs, f, indent=2)
    print(f"  map_aggregates.json: {os.path.getsize(aggs_path)/1024:.0f} KB")
    
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == '__main__':
    main()
