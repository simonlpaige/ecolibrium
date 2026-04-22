"""
Schema migration: add the legibility column.

Tracks HOW an org was found, so the directory can honestly show what slice
of the real solidarity economy is visible to us versus what we are missing.

Values:
  'formal'   - registered legal entity, found via a government registry,
               Wikidata, or an official NGO directory.
  'hybrid'   - registered BUT primarily operating informally (e.g. SHG
               federations, farmer producer organizations that exist on
               paper but live through village-level practice).
  'informal' - unregistered group: sangha, mutual aid network, forest or
               water commons, neighborhood collective.
  'unknown'  - we have not yet classified this org.

Default for existing rows is 'unknown'. Each ingester sets this explicitly
for new rows.

Run:
    python migrate_legibility.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import get_db, ensure_column


def main():
    db = get_db()
    ensure_column(db, 'organizations', 'legibility', "TEXT DEFAULT 'unknown'")
    db.execute(
        'CREATE INDEX IF NOT EXISTS idx_orgs_legibility '
        'ON organizations(legibility)'
    )
    db.commit()

    # Report current distribution
    cur = db.execute(
        'SELECT legibility, COUNT(*) FROM organizations '
        "WHERE status = 'active' GROUP BY legibility"
    )
    rows = cur.fetchall()
    print('\nLegibility distribution (active orgs):')
    if not rows:
        print('  (empty)')
    else:
        total = sum(r[1] for r in rows)
        for legibility, count in rows:
            pct = (count / total * 100) if total else 0
            print(f'  {legibility or "(null)":10s} {count:>8,}  {pct:5.1f}%')

    print('\nMigration complete.')
    db.close()


if __name__ == '__main__':
    main()
