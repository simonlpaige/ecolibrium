"""
build_regions.py: produce data/map/regions.geojson, world-country polygons
with per-country aggregates baked into properties.

Inputs:
  - data/map/_src/countries-50m.topojson  (Natural Earth 1:50m, world-atlas v2)
  - data/commonweave_directory.db         (for the per-country counts)

Output:
  - data/map/regions.geojson  (FeatureCollection of countries with
                                aggregates in properties)

The output drives Phase 4's System Health choropleth and the viewport health
bar. Each feature carries:
  properties.iso_a2        # 'US', 'GB', 'KE', ...
  properties.name          # human-readable country name
  properties.org_count     # Tier A/B/C orgs in this country
  properties.sections      # { democracy: 12, food: 5, ... }
  properties.completeness  # 0..100, brief's section_coverage * quality
  properties.section_count # how many of 10 sections are present
"""
import json
import os
import sqlite3
from collections import defaultdict, Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(ROOT, 'data', 'commonweave_directory.db')
SRC_TOPO = os.path.join(ROOT, 'data', 'map', '_src', 'countries-50m.topojson')
OUT_PATH = os.path.join(ROOT, 'data', 'map', 'regions.geojson')

SECTIONS = ['democracy', 'cooperatives', 'healthcare', 'food', 'education',
            'housing_land', 'conflict', 'energy_digital', 'recreation_arts', 'ecology']

# ISO numeric -> alpha-2. Hand-curated subset that covers every code with
# >= 1 active org in the directory (verified against data/map/stats.json).
# When a country shows up in the TopoJSON but not here, we just skip the
# join and the polygon shows zero counts.
NUMERIC_TO_ALPHA2 = {
    '004': 'AF', '008': 'AL', '012': 'DZ', '016': 'AS', '020': 'AD', '024': 'AO',
    '028': 'AG', '031': 'AZ', '032': 'AR', '036': 'AU', '040': 'AT', '044': 'BS',
    '048': 'BH', '050': 'BD', '051': 'AM', '052': 'BB', '056': 'BE', '060': 'BM',
    '064': 'BT', '068': 'BO', '070': 'BA', '072': 'BW', '076': 'BR', '084': 'BZ',
    '090': 'SB', '096': 'BN', '100': 'BG', '104': 'MM', '108': 'BI', '112': 'BY',
    '116': 'KH', '120': 'CM', '124': 'CA', '132': 'CV', '136': 'KY', '140': 'CF',
    '144': 'LK', '148': 'TD', '152': 'CL', '156': 'CN', '158': 'TW', '170': 'CO',
    '174': 'KM', '178': 'CG', '180': 'CD', '188': 'CR', '191': 'HR', '192': 'CU',
    '196': 'CY', '203': 'CZ', '204': 'BJ', '208': 'DK', '212': 'DM', '214': 'DO',
    '218': 'EC', '222': 'SV', '226': 'GQ', '231': 'ET', '232': 'ER', '233': 'EE',
    '242': 'FJ', '246': 'FI', '250': 'FR', '254': 'GF', '258': 'PF', '262': 'DJ',
    '266': 'GA', '268': 'GE', '270': 'GM', '275': 'PS', '276': 'DE', '288': 'GH',
    '296': 'KI', '300': 'GR', '304': 'GL', '308': 'GD', '312': 'GP', '316': 'GU',
    '320': 'GT', '324': 'GN', '328': 'GY', '332': 'HT', '340': 'HN', '344': 'HK',
    '348': 'HU', '352': 'IS', '356': 'IN', '360': 'ID', '364': 'IR', '368': 'IQ',
    '372': 'IE', '376': 'IL', '380': 'IT', '384': 'CI', '388': 'JM', '392': 'JP',
    '398': 'KZ', '400': 'JO', '404': 'KE', '408': 'KP', '410': 'KR', '414': 'KW',
    '417': 'KG', '418': 'LA', '422': 'LB', '426': 'LS', '428': 'LV', '430': 'LR',
    '434': 'LY', '438': 'LI', '440': 'LT', '442': 'LU', '450': 'MG', '454': 'MW',
    '458': 'MY', '462': 'MV', '466': 'ML', '470': 'MT', '478': 'MR', '480': 'MU',
    '484': 'MX', '492': 'MC', '496': 'MN', '498': 'MD', '499': 'ME', '504': 'MA',
    '508': 'MZ', '512': 'OM', '516': 'NA', '520': 'NR', '524': 'NP', '528': 'NL',
    '540': 'NC', '548': 'VU', '554': 'NZ', '558': 'NI', '562': 'NE', '566': 'NG',
    '578': 'NO', '583': 'FM', '584': 'MH', '585': 'PW', '586': 'PK', '591': 'PA',
    '598': 'PG', '600': 'PY', '604': 'PE', '608': 'PH', '616': 'PL', '620': 'PT',
    '624': 'GW', '626': 'TL', '630': 'PR', '634': 'QA', '642': 'RO', '643': 'RU',
    '646': 'RW', '659': 'KN', '662': 'LC', '670': 'VC', '682': 'SA', '686': 'SN',
    '688': 'RS', '690': 'SC', '694': 'SL', '702': 'SG', '703': 'SK', '704': 'VN',
    '705': 'SI', '706': 'SO', '710': 'ZA', '716': 'ZW', '724': 'ES', '728': 'SS',
    '729': 'SD', '740': 'SR', '748': 'SZ', '752': 'SE', '756': 'CH', '760': 'SY',
    '762': 'TJ', '764': 'TH', '768': 'TG', '772': 'TK', '776': 'TO', '780': 'TT',
    '784': 'AE', '788': 'TN', '792': 'TR', '795': 'TM', '798': 'TV', '800': 'UG',
    '804': 'UA', '807': 'MK', '818': 'EG', '826': 'GB', '834': 'TZ', '840': 'US',
    '854': 'BF', '858': 'UY', '860': 'UZ', '862': 'VE', '882': 'WS', '887': 'YE',
    '894': 'ZM',
}


def topojson_to_geojson(topo, object_name='countries'):
    """Decode TopoJSON to a list of GeoJSON Features. Inline, minimal: the
    repo does not need a full topojson lib for one bake."""
    arcs = topo['arcs']
    transform = topo.get('transform')
    if transform:
        scale = transform['scale']
        translate = transform['translate']

        def absolute(arc):
            x, y = 0, 0
            out = []
            for dx, dy in arc:
                x += dx
                y += dy
                out.append([x * scale[0] + translate[0], y * scale[1] + translate[1]])
            return out

        decoded_arcs = [absolute(a) for a in arcs]
    else:
        decoded_arcs = arcs

    def get_arc(i):
        if i < 0:
            return list(reversed(decoded_arcs[~i]))
        return decoded_arcs[i]

    def stitch(arc_indices):
        coords = []
        for i in arc_indices:
            seg = get_arc(i)
            if coords:
                coords.extend(seg[1:])
            else:
                coords.extend(seg)
        return coords

    def geom_to_geojson(geom):
        t = geom['type']
        if t == 'Polygon':
            return {'type': 'Polygon', 'coordinates': [stitch(ring) for ring in geom['arcs']]}
        if t == 'MultiPolygon':
            return {'type': 'MultiPolygon', 'coordinates': [
                [stitch(ring) for ring in poly] for poly in geom['arcs']
            ]}
        if t == 'LineString':
            return {'type': 'LineString', 'coordinates': stitch(geom['arcs'])}
        if t == 'Point':
            return {'type': 'Point', 'coordinates': geom['coordinates']}
        return None

    obj = topo['objects'][object_name]
    out = []
    for g in obj['geometries']:
        gj = geom_to_geojson(g)
        if gj is None:
            continue
        out.append({
            'type': 'Feature',
            'id': g.get('id'),
            'properties': dict(g.get('properties') or {}),
            'geometry': gj,
        })
    return out


def build_country_aggregates(db):
    """Per-country aggregates joined to ISO alpha-2 country codes."""
    c = db.cursor()
    c.execute("""
        SELECT country_code, framework_area, COUNT(*),
               SUM(CASE WHEN quality_tier IN ('tier_a','tier_b') THEN 1 ELSE 0 END)
        FROM organizations
        WHERE status='active' AND framework_area IS NOT NULL
          AND quality_tier IN ('tier_a','tier_b','tier_c')
        GROUP BY country_code, framework_area
    """)
    countries = defaultdict(lambda: {
        'org_count': 0, 'verified_count': 0, 'sections': defaultdict(int),
    })
    for cc, area, count, verified in c.fetchall():
        if not cc:
            continue
        countries[cc]['org_count'] += count
        countries[cc]['verified_count'] += (verified or 0)
        countries[cc]['sections'][area] += count

    # Completeness: section_coverage * (0.5 + 0.5 * quality_ratio).
    for cc, data in countries.items():
        section_count = sum(1 for s in SECTIONS if data['sections'].get(s, 0) > 0)
        section_coverage = section_count / len(SECTIONS)
        quality_ratio = (data['verified_count'] / data['org_count']) if data['org_count'] else 0
        data['completeness'] = round(section_coverage * (0.5 + 0.5 * quality_ratio) * 100, 1)
        data['section_count'] = section_count
        data['sections'] = dict(data['sections'])
    return dict(countries)


def main():
    if not os.path.exists(SRC_TOPO):
        raise SystemExit(f"Missing {SRC_TOPO}. Download world-atlas@2 countries-50m.json first.")
    print("Loading TopoJSON...")
    with open(SRC_TOPO, 'r', encoding='utf-8') as f:
        topo = json.load(f)
    features = topojson_to_geojson(topo, object_name='countries')
    print(f"  decoded {len(features)} country features")

    print("Loading aggregates from DB...")
    db = sqlite3.connect(DB_PATH)
    aggs = build_country_aggregates(db)
    db.close()
    print(f"  {len(aggs)} countries with at least one Tier A/B/C org")

    matched = 0
    skipped = 0
    for f in features:
        nid = str(f.get('id') or '').zfill(3)
        a2 = NUMERIC_TO_ALPHA2.get(nid)
        if not a2:
            skipped += 1
            f['properties']['iso_a2'] = None
            f['properties']['org_count'] = 0
            f['properties']['section_count'] = 0
            f['properties']['completeness'] = 0
            f['properties']['sections'] = {}
            continue
        f['properties']['iso_a2'] = a2
        if a2 in aggs:
            d = aggs[a2]
            f['properties']['org_count'] = d['org_count']
            f['properties']['verified_count'] = d['verified_count']
            f['properties']['section_count'] = d['section_count']
            f['properties']['completeness'] = d['completeness']
            f['properties']['sections'] = d['sections']
            matched += 1
        else:
            f['properties']['org_count'] = 0
            f['properties']['section_count'] = 0
            f['properties']['completeness'] = 0
            f['properties']['sections'] = {}
    print(f"  matched {matched} polygons to aggregates, {skipped} unmapped numeric ids")

    fc = {'type': 'FeatureCollection', 'features': features}
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(fc, f, separators=(',', ':'))
    print(f"Wrote {OUT_PATH} ({os.path.getsize(OUT_PATH) / 1024:.0f} KB)")

    # Top 10 by completeness, for sanity.
    ranked = sorted(features, key=lambda f: -f['properties'].get('completeness', 0))[:10]
    print("Top completeness:")
    for f in ranked:
        p = f['properties']
        print(f"  {p.get('iso_a2') or '??'} {p.get('name', ''):<30} "
              f"{p.get('completeness', 0):>5.1f}% "
              f"{p.get('section_count', 0)}/10 sections "
              f"{p.get('org_count', 0):>6,} orgs")


if __name__ == '__main__':
    main()
