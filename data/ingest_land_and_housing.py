"""
Land and housing ingest dispatcher.

Runs the four land-and-housing ingesters in order:
  1. ingest_land_trusts.py         - Wikidata SPARQL for community land
                                     trusts (Q3278937) and housing cooperatives
                                     (Q562166).
  2. ingest_grounded_solutions.py  - Grounded Solutions Network member-
                                     spotlight posts plus a curated seed list
                                     of US, UK, Canada, and Belgium CLTs.
  3. ingest_habitat.py             - Enriches existing IRS_EO_BMF Habitat
                                     rows and adds international Habitat
                                     country offices.
  4. ingest_construction_coops.py  - Wikidata SPARQL plus a seed list of
                                     Mondragon, SCOP, Italian, US, and UK
                                     construction cooperatives.

Mirrors ingest_labor.py. Forwards --dry-run to every child.

Usage:
    python ingest_land_and_housing.py              # real run
    python ingest_land_and_housing.py --dry-run    # all sources, no writes
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from _common import DATA_DIR  # noqa: F401


CHILDREN = [
    ('wikidata_land_trusts', 'ingest_land_trusts.py'),
    ('grounded_solutions',   'ingest_grounded_solutions.py'),
    ('habitat_affiliates',   'ingest_habitat.py'),
    ('construction_coops',   'ingest_construction_coops.py'),
]


def run_child(script, dry_run):
    path = os.path.join(os.path.dirname(__file__), script)
    args = [sys.executable, path]
    if dry_run:
        args.append('--dry-run')
    print(f'\n>> Running: {" ".join(args)}')
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=3600)
        if r.stdout:
            print(r.stdout)
        if r.returncode != 0:
            print(f'  exit {r.returncode}: {r.stderr[-800:]}')
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        print('  TIMEOUT after 60 minutes')
        return False


def main():
    ap = argparse.ArgumentParser(description='Land and housing ingest dispatcher')
    ap.add_argument('--dry-run', action='store_true',
                    help='Forward --dry-run to every child ingester')
    args = ap.parse_args()

    started = datetime.now(timezone.utc).isoformat()
    print(f'land-and-housing dispatcher started: {started}')

    results = []
    for name, script in CHILDREN:
        ok = run_child(script, args.dry_run)
        results.append((name, ok))

    print('\n--- summary ---')
    for name, ok in results:
        print(f'  {name:22s} {"ok" if ok else "FAILED"}')

    if any(not ok for _, ok in results):
        sys.exit(1)


if __name__ == '__main__':
    main()
