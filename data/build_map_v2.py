"""
Map V2 data pipeline:
1. Assign quality tiers (A/B/C/D) to all orgs
2. Generate derived network edges (same-section proximity)
3. Pre-compute country aggregates for choropleth
4. Compute System Completeness scores per region
5. Output: map_points_v2.json, map_edges.json, map_aggregates.json,
           data/map/stats.json (single source of truth for public counts)
"""
import sqlite3
import json
import os
import math
from collections import defaultdict, Counter
from datetime import datetime, timezone

DB_PATH = r'C:\Users\simon\.openclaw\workspace\commonweave\data\commonweave_directory.db'
SEARCH_DIR = r'C:\Users\simon\.openclaw\workspace\commonweave\data\search'
MAP_DIR = r'C:\Users\simon\.openclaw\workspace\commonweave\data\map'

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


def ensure_risk_context_column(db):
    """Add risk_context column with default 'normal' if missing.

    The column lets us flag rows in repressive contexts (anti-eviction networks,
    Indigenous land defenders) so we can later jitter or hide their precise
    coordinates. Phase 1 only adds the field; populating sensitive flags is a
    future pass.
    """
    c = db.cursor()
    c.execute("PRAGMA table_info(organizations)")
    cols = {row[1] for row in c.fetchall()}
    if 'risk_context' not in cols:
        # Older SQLite refuses non-constant defaults. 'normal' is constant.
        c.execute("ALTER TABLE organizations ADD COLUMN risk_context TEXT DEFAULT 'normal'")
        c.execute("UPDATE organizations SET risk_context = 'normal' WHERE risk_context IS NULL")
        db.commit()
        print("Added risk_context column (all rows -> 'normal').")
    else:
        c.execute("UPDATE organizations SET risk_context = 'normal' WHERE risk_context IS NULL")
        db.commit()


def assign_tiers(db):
    """Assign quality tiers based on data completeness."""
    c = db.cursor()

    c.execute("UPDATE organizations SET quality_tier = NULL WHERE status='active'")

    # Tier A: reviewed rows with both description and website
    c.execute("""UPDATE organizations SET quality_tier = 'tier_a'
                 WHERE status='active' AND review_status='reviewed'
                 AND description IS NOT NULL AND description != ''
                 AND website IS NOT NULL AND website != ''""")
    tier_a = c.rowcount

    # Tier B: sourced rows with enough public detail to show on the map
    c.execute("""UPDATE organizations SET quality_tier = 'tier_b'
                 WHERE status='active' AND quality_tier IS NULL
                 AND (
                      (description IS NOT NULL AND description != '')
                      OR (review_status='reviewed' AND website IS NOT NULL AND website != '')
                      OR source IN ('web_research', 'manual_curation', 'ProPublica')
                  )""")
    tier_b = c.rowcount

    # Tier C: passed the keyword scorer but has not been reviewed
    c.execute("""UPDATE organizations SET quality_tier = 'tier_c'
                 WHERE status='active' AND quality_tier IS NULL
                 AND scored_pass = 1""")
    tier_c = c.rowcount

    # Tier D: everything else that's active
    c.execute("""UPDATE organizations SET quality_tier = 'tier_d'
                 WHERE status='active' AND quality_tier IS NULL""")
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
               country_code, state_province, annual_revenue, source, quality_tier, alignment_score,
               city, contact_url, risk_context, last_verified_at
        FROM organizations
        WHERE status='active' AND lat IS NOT NULL AND lon IS NOT NULL
          AND quality_tier IN ('tier_a', 'tier_b', 'tier_c')
        ORDER BY
            CASE quality_tier WHEN 'tier_a' THEN 0 WHEN 'tier_b' THEN 1 ELSE 2 END,
            annual_revenue DESC NULLS LAST
    """)

    points = []
    points_by_id = {}

    for row in c.fetchall():
        (org_id, name, lat, lon, area, mtype, website, desc, cc, state, revenue,
         source, tier, align, city, contact_url, risk_context, last_verified) = row

        tier_letter = tier.replace('tier_', '').upper() if tier else 'D'

        # Truncate fields
        if website:
            website = website.replace('https://', '').replace('http://', '').rstrip('/')
            if len(website) > 60:
                website = website[:60]
        if desc and len(desc) > 150:
            desc = desc[:150].rsplit(' ', 1)[0] + '...'

        point = {
            # Stable id on the wire so URL state can reference an org. Used by
            # selectedId in the map's URL hash and by edge source_id/target_id.
            'id': f'org_{org_id}',
            '_db_id': org_id,  # internal only, stripped before export
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
        if city: point['ci'] = city
        if source: point['src'] = source
        if contact_url: point['cu'] = contact_url
        if last_verified: point['lv'] = last_verified
        # Always include risk_context so the renderer can decide later whether
        # to jitter or hide. Default 'normal' makes the field cheap to ship.
        point['rc'] = risk_context or 'normal'

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
    today_iso = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    def confidence_band(w):
        # Bucket the numeric weight into the brief's enum: high/medium/low.
        if w >= 0.66:
            return 'high'
        if w >= 0.33:
            return 'medium'
        return 'low'

    for cell, cell_points in grid.items():
        # Check this cell and its 8 neighbors
        neighbor_points = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                ncell = (cell[0] + dx, cell[1] + dy)
                if ncell in grid:
                    neighbor_points.extend(grid[ncell])

        for p1 in cell_points:
            if edge_count_per_org[p1['_db_id']] >= max_edges_per_org:
                continue

            candidates = []
            for p2 in neighbor_points:
                if p1['_db_id'] >= p2['_db_id']:
                    continue
                pair = (p1['_db_id'], p2['_db_id'])
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
                if edge_count_per_org[p1['_db_id']] >= max_edges_per_org:
                    break
                if edge_count_per_org[p2['_db_id']] >= max_edges_per_org:
                    continue

                # Build human-readable explanation
                if edge_type == 'same_section':
                    explanation = f"Both are in the {p1['f']} section and within {round(dist, 1)} km of each other"
                else:
                    explanation = f"Complementary sections ({p1['f']} + {p2['f']}) within {round(dist, 1)} km"

                # Phase 1 brief task 1.8: stable edge id, source_id/target_id,
                # explicit numeric weight separate from confidence band, evidence
                # array (empty until Phase 2 wires real verified relationships),
                # derived flag.
                a_id, b_id = sorted([p1['_db_id'], p2['_db_id']])
                edge_id = f'edge_org_{a_id}_org_{b_id}'
                source_id = f'org_{p1["_db_id"]}'
                target_id = f'org_{p2["_db_id"]}'
                wnum = round(weight, 3)

                edges.append({
                    'id': edge_id,
                    'source_id': source_id,
                    'target_id': target_id,
                    # Source/target coords are kept so the existing D3 renderer
                    # can resolve endpoints by coord hash. Phase 2 will switch
                    # the renderer to id-keyed lookups and drop these.
                    's': [p1['lo'], p1['la']],
                    't': [p2['lo'], p2['la']],
                    'edge_type': 'same_section_proximity' if edge_type == 'same_section' else 'cross_section_complementarity',
                    'weight': wnum,
                    'confidence': confidence_band(wnum),
                    'derived': True,
                    'evidence': [],
                    'explanation': explanation,
                    'created_at': today_iso,
                    'source_script': 'data/build_map_v2.py',
                    # Compact display fields the renderer already uses:
                    'e': edge_type[0],   # 's' (same) or 'c' (complementary)
                    'f': p1['f'],        # section, drives stroke colour
                    'w': wnum,           # legacy alias of weight; renderer reads .w
                })
                seen_pairs.add(pair)
                edge_count_per_org[p1['_db_id']] += 1
                edge_count_per_org[p2['_db_id']] += 1

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
               SUM(CASE WHEN quality_tier='tier_a' THEN 1 WHEN quality_tier='tier_b' THEN 1 ELSE 0 END)
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
          AND framework_area IS NOT NULL AND quality_tier IN ('tier_a', 'tier_b', 'tier_c')
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


def compute_db_totals(db):
    """Counts that describe the database, not just the map."""
    c = db.cursor()

    # orgs_total_db: every row that has not been merged away. This is the
    # "candidates" number quoted on the homepage.
    c.execute("SELECT COUNT(*) FROM organizations WHERE merged_into IS NULL")
    orgs_total_db = c.fetchone()[0]

    # orgs_in_directory: post-trim active rows. A subset of total_db.
    c.execute("SELECT COUNT(*) FROM organizations WHERE status='active'")
    orgs_in_directory = c.fetchone()[0]

    # countries_with_at_least_one_org: every distinct active country code.
    c.execute("""SELECT COUNT(DISTINCT country_code)
                 FROM organizations
                 WHERE status='active' AND country_code IS NOT NULL AND country_code != ''""")
    countries_with_at_least_one_org = c.fetchone()[0]

    # countries_with_geocoded_org: distinct country codes among Tier A/B/C
    # rows that actually have lat/lon. This is the headline country count.
    c.execute("""SELECT COUNT(DISTINCT country_code)
                 FROM organizations
                 WHERE status='active' AND lat IS NOT NULL AND lon IS NOT NULL
                   AND quality_tier IN ('tier_a','tier_b','tier_c')
                   AND country_code IS NOT NULL AND country_code != ''""")
    countries_with_geocoded_org = c.fetchone()[0]

    return {
        'orgs_total_db': orgs_total_db,
        'orgs_in_directory': orgs_in_directory,
        'countries_with_at_least_one_org': countries_with_at_least_one_org,
        'countries_with_geocoded_org': countries_with_geocoded_org,
    }


def write_edge_schema(path):
    """Stub JSON Schema for an edge object. Phase 2 will fill in detail."""
    schema = {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': 'https://commonweave.earth/data/map/schema.edge.json',
        'title': 'Commonweave Map Edge',
        'description': 'A single relationship between two organizations on the Commonweave map. Phase 1 stub.',
        'type': 'object',
        'required': ['id', 'source_id', 'target_id', 'edge_type', 'weight', 'confidence', 'derived', 'created_at', 'source_script'],
        'properties': {
            'id': {'type': 'string', 'description': 'Stable edge id, typically edge_<source>_<target> with the lexicographically smaller id first.'},
            'source_id': {'type': 'string', 'description': 'Stable id of one endpoint, e.g. org_12345.'},
            'target_id': {'type': 'string', 'description': 'Stable id of the other endpoint.'},
            'edge_type': {
                'type': 'string',
                'enum': [
                    'verified_relationship',
                    'federation_membership',
                    'attestation',
                    'same_section_proximity',
                    'cross_section_complementarity',
                    'shared_resource',
                    'user_need_match',
                ],
                'description': 'The kind of connection. Phase 1 only emits the two proximity types; Phase 2 adds the rest.',
            },
            'weight': {'type': 'number', 'minimum': 0, 'maximum': 1, 'description': 'Numeric strength of the connection in [0,1].'},
            'confidence': {'type': 'string', 'enum': ['high', 'medium', 'low']},
            'derived': {'type': 'boolean', 'description': 'True if generated by an algorithm, false if a human asserted the relationship.'},
            'evidence': {
                'type': 'array',
                'description': 'Pointers to the data that supports this edge. Empty for derived edges in Phase 1.',
                'items': {
                    'type': 'object',
                    'required': ['type', 'value'],
                    'properties': {
                        'type': {'type': 'string', 'enum': ['url', 'registry', 'manual_note', 'wikidata', 'inference']},
                        'value': {'type': 'string'},
                    },
                },
            },
            'explanation': {'type': 'string', 'description': 'Plain-language description of why this edge exists.'},
            'created_at': {'type': 'string', 'format': 'date'},
            'source_script': {'type': 'string', 'description': 'Path to the script that produced this edge.'},
        },
        'additionalProperties': True,
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2)


def main():
    os.makedirs(SEARCH_DIR, exist_ok=True)
    os.makedirs(MAP_DIR, exist_ok=True)
    db = sqlite3.connect(DB_PATH)

    print("=" * 60)
    print("COMMONWEAVE MAP V2 DATA PIPELINE")
    print("=" * 60)

    # Step 0: Make sure the risk_context column exists. Cheap and idempotent.
    ensure_risk_context_column(db)

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

    # Step 6: DB-level totals for the public-facing stats.json.
    print("\n--- Step 6: Computing DB totals ---")
    db_totals = compute_db_totals(db)
    for k, v in db_totals.items():
        print(f"  {k}: {v:,}")

    db.close()

    # Strip internal _db_id from points before export. Keep the stable string
    # id so the URL hash and the new detail-panel "share link" can target it.
    export_points = []
    for p in points:
        ep = {k: v for k, v in p.items() if k != '_db_id'}
        export_points.append(ep)

    # Per-section and per-country counts on the map (the visible data).
    section_counts = Counter(p['f'] for p in export_points)
    country_counts_on_map = Counter(p['cc'] for p in export_points)
    map_tier_counts = Counter(p['t'] for p in export_points)
    edge_type_counts = Counter(e['edge_type'] for e in edges)

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

    # Single source of truth for ALL public counts (homepage hero, README,
    # map UI footer, DIRECTORY.md). Anything that wants to print "X orgs in
    # Y countries" reads this file.
    stats = {
        'orgs_total_db': db_totals['orgs_total_db'],
        'orgs_in_directory': db_totals['orgs_in_directory'],
        'orgs_on_map': len(export_points),
        'countries_with_at_least_one_org': db_totals['countries_with_at_least_one_org'],
        'countries_with_geocoded_org': db_totals['countries_with_geocoded_org'],
        'by_tier': {
            'A_curated': map_tier_counts.get('A', 0),
            'B_verified': map_tier_counts.get('B', 0),
            'C_inferred': map_tier_counts.get('C', 0),
            'D_unverified_off_map': tier_counts.get('D', 0),
        },
        # Whole-DB tier counts so consumers can show on-map vs off-map at once.
        'by_tier_full': {
            'A': tier_counts.get('A', 0),
            'B': tier_counts.get('B', 0),
            'C': tier_counts.get('C', 0),
            'D': tier_counts.get('D', 0),
        },
        'by_section': dict(sorted(section_counts.items(), key=lambda kv: -kv[1])),
        'by_country': dict(sorted(country_counts_on_map.items(), key=lambda kv: -kv[1])),
        'edges_total': len(edges),
        'edges_by_type': dict(edge_type_counts),
        'sections': SECTIONS,
        'last_built': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'last_built_date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'source_script': 'data/build_map_v2.py',
    }
    stats_path = os.path.join(MAP_DIR, 'stats.json')
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)
    print(f"  data/map/stats.json: {os.path.getsize(stats_path)/1024:.1f} KB")

    # Edge schema stub. Phase 2 will replace this with a real schema and add
    # the corresponding org schema.
    schema_path = os.path.join(MAP_DIR, 'schema.edge.json')
    write_edge_schema(schema_path)
    print(f"  data/map/schema.edge.json: {os.path.getsize(schema_path)/1024:.1f} KB")

    print("\n--- Public-facing numbers ---")
    print(f"  Candidates in DB:     {stats['orgs_total_db']:>8,}")
    print(f"  In directory:         {stats['orgs_in_directory']:>8,}")
    print(f"  On the map:           {stats['orgs_on_map']:>8,}")
    print(f"  Countries (any):      {stats['countries_with_at_least_one_org']:>8,}")
    print(f"  Countries (mapped):   {stats['countries_with_geocoded_org']:>8,}")
    print(f"  Edges:                {stats['edges_total']:>8,}")

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == '__main__':
    main()
