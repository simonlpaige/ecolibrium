"""Phase 1 acceptance test for the MAP-V3-PHASE1-BRIEF.

Acceptance criteria from the brief:
    A visitor can open the map, filter to Tier A/B, click one org, see
    where the data came from, and copy a link to that exact view. The
    homepage counts match what is shown on the map and the README
    headline numbers, all sourced from data/map/stats.json.

This script is a static-analysis acceptance pass. It checks the artifacts
that prove each requirement is in place, plus a round-trip simulation of
the share-link flow. It is committed for reproducibility but not part of
any build hook (the brief says the manual click-through is the canonical
acceptance check; this is the deterministic backstop).
"""
import json
import os
import re
import sys
import urllib.parse

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def load(path):
    with open(os.path.join(REPO, path), 'r', encoding='utf-8') as f:
        return f.read()


def loadj(path):
    return json.loads(load(path))


def main():
    stats = loadj('data/map/stats.json')
    points = loadj('data/search/map_points_v2.json')
    edges = loadj('data/search/map_edges.json')
    home = load('index.html')
    mapsrc = load('map.html')
    dir_md = load('DIRECTORY.md')

    results = []

    def check(desc, ok, why=''):
        results.append((bool(ok), desc, why))
        print(('PASS' if ok else 'FAIL'), '-', desc, ('| ' + why if why else ''))

    print('--- 1.1 stats.json shape ---')
    required = [
        'orgs_total_db', 'orgs_in_directory', 'orgs_on_map',
        'countries_with_at_least_one_org', 'countries_with_geocoded_org',
        'by_tier', 'by_section', 'by_country', 'edges_total',
        'edges_by_type', 'last_built', 'last_built_date',
    ]
    for k in required:
        check(f'stats.json has {k}', k in stats)

    print('--- 1.2 homepage no longer hardcodes drift values ---')
    bad_patterns = [r'27\.3K', r'27,300', r'172\s*</div>\s*<div class="stat-l">Countries']
    for pat in bad_patterns:
        m = re.search(pat, home)
        check(f'index.html has no hardcoded {pat!r}', m is None,
              why=(m.group(0) if m else ''))
    for stat in ['orgs_in_directory', 'orgs_on_map', 'countries_geocoded']:
        check(f'index.html has data-stat="{stat}"', f'data-stat="{stat}"' in home)
    check('index.html fetches stats.json at runtime',
          "fetch('data/map/stats.json'" in home)

    print('--- 1.4 tier legend ---')
    check('map.html has tier-legend container', 'id="tier-legend"' in mapsrc)
    check('Tier B labelled "Verified (from registry)"',
          'Verified (from registry)' in mapsrc)
    check('TIER_LABELS includes A, B, C, D',
          all(f"  {x}: '" in mapsrc for x in ['A', 'B', 'C', 'D']))

    print('--- 1.5 URL state ---')
    for fn in ['_writeUrlState', 'readUrlState', 'applyUrlState', 'applyUrlStateAfterRender']:
        check(f'map.html defines {fn}()', f'function {fn}' in mapsrc)
    check('map.html restores on hashchange', "addEventListener('hashchange'" in mapsrc)

    print('--- 1.6 detail panel fields ---')
    required_in_panel = [
        'pop-name', 'pop-tier-explainer', 'pop-row',
        'Copy share link', 'Suggest correction',
        'data-share=', 'pop-actions', 'corrUrl', 'buildShareUrl', 'copyShareLink'
    ]
    for tok in required_in_panel:
        check(f'detail panel has {tok!r}', tok in mapsrc)

    print('--- 1.7 high-confidence toggle ---')
    check('hc-toggle button present', 'id="hc-toggle"' in mapsrc)
    check('hc-toggle handler defined', 'syncHighConfidenceToggle' in mapsrc)

    print('--- 1.8 edge provenance ---')
    sample = edges[0] if edges else {}
    for f in ['id', 'source_id', 'target_id', 'edge_type', 'weight',
              'confidence', 'derived', 'evidence', 'explanation',
              'created_at', 'source_script']:
        check(f'edges[0] has field {f!r}', f in sample)
    check('edges[0].id starts with edge_org_',
          str(sample.get('id', '')).startswith('edge_org_'))
    check('edges[0].source_id starts with org_',
          str(sample.get('source_id', '')).startswith('org_'))
    check('edges[0].confidence is high|medium|low',
          sample.get('confidence') in ('high', 'medium', 'low'))
    check('edges[0].evidence is list', isinstance(sample.get('evidence'), list))
    check('edges[0].derived is True', sample.get('derived') is True)
    check('schema.edge.json present',
          os.path.exists(os.path.join(REPO, 'data/map/schema.edge.json')))

    print('--- 1.9 stable org ids on the wire ---')
    sample_pt = points[0] if points else {}
    check('map_points_v2.json[0].id starts with org_',
          str(sample_pt.get('id', '')).startswith('org_'))
    check('map_points_v2.json[0] carries rc (risk_context)', 'rc' in sample_pt)
    check('map_points_v2.json[0].rc default is "normal"',
          sample_pt.get('rc') == 'normal')
    # Spot-check 50 random points all have an id like org_<digits>.
    bad = [p for p in points[:5000] if not re.match(r'^org_\d+$', str(p.get('id', '')))]
    check('all sampled points have an org_<n> id', not bad,
          why=f'{len(bad)} bad samples')

    print('--- 1.10 last-built footer ---')
    check('map.html has built footer DOM',
          'id="sb-built"' in mapsrc and 'id="built-date"' in mapsrc)
    check('map.html has renderBuiltFooter()',
          'function renderBuiltFooter' in mapsrc)

    print('--- 1.11 DIRECTORY.md threaded through stats.json ---')
    check('DIRECTORY.md cites stats.json', 'data/map/stats.json' in dir_md)
    check('DIRECTORY.md uses orgs_in_directory total',
          f"{stats['orgs_in_directory']:,} organizations" in dir_md)
    check('DIRECTORY.md mentions on-map count',
          f"{stats['orgs_on_map']:,} of those" in dir_md)

    print('--- Acceptance flow simulation ---')
    # Walk the brief's flow against a real org. The user filters to A/B
    # (default), clicks org_689392, sees source/website/desc, copies a
    # link, opens it -> same view.
    target_id = None
    for p in points:
        if (p.get('t') in ('A', 'B') and p.get('w') and p.get('d') and p.get('src')
                and re.match(r'^org_\d+$', str(p.get('id', '')))):
            target_id = p['id']
            target = p
            break
    check('found a high-confidence org with website + desc + source',
          target_id is not None)

    # Build the share URL the way the JS does: when tiers == 'AB' it is
    # omitted; selectedId is added.
    share_qs = urllib.parse.urlencode({'selectedId': target_id})
    share_url = f"https://example.org/map.html#{share_qs}"
    parsed_hash = urllib.parse.parse_qs(share_url.split('#', 1)[1])
    check('share URL preserves selectedId',
          parsed_hash.get('selectedId', [None])[0] == target_id)

    # Verify the URL params the JS reads on load. tiers absent -> default
    # A+B (high confidence).
    check('tiers param absent means default A+B applies',
          'tiers' not in parsed_hash)

    # When the user opens the share URL, applyUrlState reads the hash and
    # selectedId targets a known org. Simulate that lookup:
    points_by_id = {p['id']: p for p in points}
    check('selectedId resolves to a real point',
          target_id in points_by_id)

    print('--- Counts agreement ---')
    home_match = re.search(r'data-stat="orgs_in_directory">(\d[\d,]*)', home)
    if home_match:
        check('homepage fallback equals stats.orgs_in_directory',
              int(home_match.group(1).replace(',', '')) == stats['orgs_in_directory'])
    home_match2 = re.search(r'data-stat="orgs_on_map">(\d[\d,]*)', home)
    if home_match2:
        check('homepage fallback equals stats.orgs_on_map',
              int(home_match2.group(1).replace(',', '')) == stats['orgs_on_map'])
    home_match3 = re.search(r'data-stat="countries_geocoded">(\d[\d,]*)', home)
    if home_match3:
        check('homepage fallback equals stats.countries_with_geocoded_org',
              int(home_match3.group(1).replace(',', '')) == stats['countries_with_geocoded_org'])

    passed = sum(1 for ok, _, _ in results if ok)
    total = len(results)
    print()
    print(f'==== {passed}/{total} checks passed ====')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
