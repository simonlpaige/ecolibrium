"""
Labor ingest dispatcher.

Runs the two labor-union ingesters in order:
  1. ingest_unions.py  - Wikidata SPARQL for federations, nationals, works councils.
  2. ingest_ituc.py    - ITUC affiliate list (with Wikipedia fallback when the
                         ITUC site blocks automated requests).

Mirrors the pattern in ingest_india.py. Passes --dry-run through to both
children so the dispatcher is a safe no-op in dry-run mode.

Usage:
    python ingest_labor.py              # real run, both sources
    python ingest_labor.py --dry-run    # both sources, no writes
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from _common import DATA_DIR


CHILDREN = [
    ('wikidata_unions', 'ingest_unions.py'),
    ('ituc_affiliates', 'ingest_ituc.py'),
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
    ap = argparse.ArgumentParser(description='Labor ingest dispatcher')
    ap.add_argument('--dry-run', action='store_true',
                    help='Forward --dry-run to every child ingester')
    args = ap.parse_args()

    started = datetime.now(timezone.utc).isoformat()
    print(f'labor dispatcher started: {started}')

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
