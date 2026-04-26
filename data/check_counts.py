"""
check_counts.py: warn (not abort) when README headline numbers drift away
from data/map/stats.json.

Phase 1 task 1.3. Run after `data/build_map_v2.py`. The script reads the
freshly built stats file, scans the README for the headline numbers it
quotes, and prints a one-line OK or a warning per mismatch. Exit code is
always zero so this can be wired into the build without breaking it.

The patterns we look for are loose on purpose. The README rephrases the
numbers in different sentences; we want to flag drift, not to be a strict
parser.
"""
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
STATS = os.path.join(REPO, 'data', 'map', 'stats.json')
README = os.path.join(REPO, 'README.md')


def _fmt(n):
    return f"{n:,}"


def find_numbers(text, regex):
    """Return integers matched by a single capturing group, comma-stripped."""
    out = []
    for m in re.finditer(regex, text, flags=re.IGNORECASE):
        try:
            out.append(int(m.group(1).replace(',', '')))
        except ValueError:
            pass
    return out


def check(label, expected, found, tol=0):
    """Compare a list of found numbers against the expected one."""
    if not found:
        return f"  [skip] {label}: no candidate number in README (pattern did not match)"
    bad = [n for n in found if abs(n - expected) > tol]
    if not bad:
        return f"  [ok]   {label}: README has {_fmt(found[0])} matching stats {_fmt(expected)}"
    return (f"  [warn] {label}: README mentions {', '.join(_fmt(n) for n in bad)} "
            f"but stats.json says {_fmt(expected)}")


def main():
    if not os.path.exists(STATS):
        print(f"check_counts: {STATS} missing. Run data/build_map_v2.py first.")
        return 0
    with open(STATS, 'r', encoding='utf-8') as f:
        stats = json.load(f)

    if not os.path.exists(README):
        print(f"check_counts: {README} missing. Nothing to check.")
        return 0
    with open(README, 'r', encoding='utf-8') as f:
        readme = f.read()

    print("check_counts: comparing README headline numbers against data/map/stats.json")
    print(f"  stats last built: {stats.get('last_built_date', '?')}")

    # 1. Candidates: "X candidate organizations" or "X candidates"
    cand = find_numbers(readme, r'([\d,]+)\s*candidate organi[sz]ations?')
    cand += find_numbers(readme, r'([\d,]+)\s+candidate[s]?\b')
    print(check('candidates', stats['orgs_total_db'], cand, tol=200))

    # 2. Geocoded points: "X geocoded points" or "X mapped"
    geo = find_numbers(readme, r'([\d,]+)\s*geocoded\s*points?')
    geo += find_numbers(readme, r'([\d,]+)\s*mapped\s+(?:organi[sz]ations|points)')
    print(check('orgs_on_map', stats['orgs_on_map'], geo, tol=200))

    # 3. Countries: "across N countries"
    countries = find_numbers(readme, r'across\s+([\d,]+)\s+countries')
    # The README's headline uses the broad-country count, not just on-map.
    print(check('countries (any)', stats['countries_with_at_least_one_org'], countries, tol=5))

    # 4. Edges: "X network edges" or "X edges"
    edges = find_numbers(readme, r'([\d,]+)\s*network\s+edges')
    edges += find_numbers(readme, r'([\d,]+)\s+edges\b')
    print(check('edges_total', stats['edges_total'], edges, tol=50))

    # 5. Tier B count: "X are registry-backed (Tier B)"
    tier_b = find_numbers(readme, r'([\d,]+)\s+are registry-backed')
    tier_b += find_numbers(readme, r'([\d,]+)\s+\(Tier B\)')
    print(check('tier_b_full', stats['by_tier_full']['B'], tier_b, tol=200))

    print("check_counts: done. Warnings above do not fail the build.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
