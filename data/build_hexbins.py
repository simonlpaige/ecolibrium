"""
build_hexbins.py: pre-aggregate map points into a coarse grid for low-zoom
rendering on phones. The output is far smaller than the full point file and
lets the front-end show a meaningful density layer at world / continent zoom
without painting every dot.

Output: data/map/hexbins.json
  {
    "cell_size_deg": 2.0,
    "max_zoom": 6,
    "bins": [
      { "cx": 10.5, "cy": 30.5, "n": 137,
        "sections": {"food": 22, "cooperatives": 14, ...},
        "verified_ratio": 0.42 }
    ]
  }
"""
import json
import os
from collections import defaultdict, Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PTS_PATH = os.path.join(ROOT, 'data', 'search', 'map_points_v2.json')
OUT_PATH = os.path.join(ROOT, 'data', 'map', 'hexbins.json')

CELL_SIZE = 2.0  # degrees: ~220km at the equator. Coarse but good enough for zoom 0-6.


def main():
    with open(PTS_PATH, 'r', encoding='utf-8') as f:
        pts = json.load(f)
    bins = defaultdict(lambda: {'n': 0, 'verified': 0, 'sections': Counter()})
    for p in pts:
        lo, la = p.get('lo'), p.get('la')
        if lo is None or la is None:
            continue
        cx = round((lo // CELL_SIZE) * CELL_SIZE + CELL_SIZE / 2, 4)
        cy = round((la // CELL_SIZE) * CELL_SIZE + CELL_SIZE / 2, 4)
        b = bins[(cx, cy)]
        b['n'] += 1
        if p.get('t') in ('A', 'B'):
            b['verified'] += 1
        b['sections'][p.get('f') or 'unknown'] += 1
    out_bins = []
    for (cx, cy), b in bins.items():
        out_bins.append({
            'cx': cx,
            'cy': cy,
            'n': b['n'],
            'verified_ratio': round(b['verified'] / b['n'], 3) if b['n'] else 0,
            'sections': dict(b['sections']),
        })
    out_bins.sort(key=lambda r: -r['n'])

    out = {
        'cell_size_deg': CELL_SIZE,
        'max_zoom': 6,
        'bins': out_bins,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, separators=(',', ':'))
    print(f"Wrote {len(out_bins):,} hexbins -> {OUT_PATH} ({os.path.getsize(OUT_PATH) / 1024:.1f} KB)")
    print("Top 10 cells by org count:")
    for b in out_bins[:10]:
        top_sec = max(b['sections'], key=lambda k: b['sections'][k])
        print(f"  ({b['cx']:.1f}, {b['cy']:.1f}): {b['n']} orgs, top section {top_sec}")


if __name__ == '__main__':
    main()
