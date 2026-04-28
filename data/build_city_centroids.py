"""
Build a small city centroids file for the front-end need-pathway parser.

For each (country, region, city) with >= 3 geocoded Tier A/B/C orgs, emit a
record with the median lat/lon and the org count. Front-end search.js looks
up location strings against this file before falling back to country bounds.

Output: data/map/city_centroids.json
"""
import json
import os
import sqlite3
import statistics
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(ROOT, 'data', 'commonweave_directory.db')
OUT_PATH = os.path.join(ROOT, 'data', 'map', 'city_centroids.json')

MIN_ORGS = 3


def main():
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    c.execute("""
        SELECT city, state_province, country_code, lat, lon
        FROM organizations
        WHERE status='active' AND lat IS NOT NULL AND lon IS NOT NULL
          AND quality_tier IN ('tier_a','tier_b','tier_c')
          AND city IS NOT NULL AND city != ''
    """)
    buckets = defaultdict(list)
    for city, state, cc, lat, lon in c.fetchall():
        key = (cc or '', state or '', city.strip())
        buckets[key].append((lat, lon))
    db.close()

    centroids = []
    for (cc, state, city), pts in buckets.items():
        if len(pts) < MIN_ORGS:
            continue
        med_lat = statistics.median(p[0] for p in pts)
        med_lon = statistics.median(p[1] for p in pts)
        centroids.append({
            'city': city,
            'region': state,
            'country': cc,
            'lat': round(med_lat, 4),
            'lon': round(med_lon, 4),
            'count': len(pts),
        })

    centroids.sort(key=lambda r: -r['count'])

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump({'centroids': centroids, 'min_orgs': MIN_ORGS}, f, separators=(',', ':'))
    print(f"Wrote {len(centroids):,} city centroids -> {OUT_PATH} ({os.path.getsize(OUT_PATH) / 1024:.1f} KB)")
    print("Top 20:")
    for c in centroids[:20]:
        print(f"  {c['city']}, {c['region']}, {c['country']}: {c['count']} orgs")


if __name__ == '__main__':
    main()
