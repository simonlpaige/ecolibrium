"""
geocode-batch.py -- Fill organizations.lat / lon / geo_source from OpenStreetMap Nominatim.

Targets active orgs that have a city + country_code but no coordinates yet.
Uses Nominatim (free, no key). Rate-limited to 1 request per second per Nominatim policy.

Resumable: stores last processed id in data/geocode-batch-state.json.

Usage:
  python tools/geocode-batch.py                  # process up to 500 orgs
  python tools/geocode-batch.py --limit 200      # process up to 200
  python tools/geocode-batch.py --dry-run        # do not write to DB
  python tools/geocode-batch.py --reset          # forget last id, start over
"""
import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.parse
import urllib.request


HERE       = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
ROOT       = os.path.abspath(os.path.join(HERE, '..'))
DB         = os.path.abspath(os.path.join(ROOT, 'data', 'commonweave_directory.db'))
STATE_PATH = os.path.abspath(os.path.join(ROOT, 'data', 'geocode-batch-state.json'))

# Nominatim asks every client to identify itself. This must be a real project
# identifier with a contact path. Update if the project moves.
USER_AGENT = 'Commonweave-Directory/1.0 (+https://commonweave.org; contact: simon@commonweave.org)'
NOMINATIM  = 'https://nominatim.openstreetmap.org/search'
SLEEP_SEC  = 1.05  # slightly above 1s to stay safely under the rate limit


def load_state():
    if not os.path.exists(STATE_PATH):
        return {'last_id': 0, 'total_geocoded': 0, 'total_misses': 0}
    try:
        with open(STATE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'last_id': 0, 'total_geocoded': 0, 'total_misses': 0}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def nominatim_lookup(city, country_code):
    """Query Nominatim for (city, countrycodes). Return (lat, lon) or None."""
    params = {
        'city':         city,
        'countrycodes': (country_code or '').lower(),
        'format':       'json',
        'limit':        '1',
    }
    # Drop empty country code entirely so global fallback still works for orgs
    # missing one. (Most callers will have one because of our WHERE filter.)
    if not params['countrycodes']:
        del params['countrycodes']
    url = NOMINATIM + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        'User-Agent':       USER_AGENT,
        'Accept':           'application/json',
        'Accept-Language':  'en',
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print('  [error] ' + type(e).__name__ + ': ' + str(e))
        return None
    if not data:
        return None
    try:
        lat = float(data[0]['lat'])
        lon = float(data[0]['lon'])
        return (lat, lon)
    except (KeyError, ValueError, TypeError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=500,
                    help='Max orgs to process this run. Default 500.')
    ap.add_argument('--dry-run', action='store_true',
                    help='Do not write to DB or update resume state.')
    ap.add_argument('--reset', action='store_true',
                    help='Reset resume cursor (last_id) to 0 before starting.')
    ap.add_argument('--db', default=DB)
    args = ap.parse_args()

    state = load_state()
    if args.reset:
        print('Resetting last_id from ' + str(state.get('last_id', 0)) + ' to 0.')
        state['last_id'] = 0

    last_id = int(state.get('last_id', 0))
    print('Resuming from last_id=' + str(last_id) + ', limit=' + str(args.limit) + '.')
    if args.dry_run:
        print('[dry-run] no DB writes, no state updates.')

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT id, name, city, state_province, country_code "
        "FROM organizations "
        "WHERE status='active' AND lat IS NULL AND city IS NOT NULL AND city != '' "
        "AND id > ? ORDER BY id LIMIT ?",
        (last_id, args.limit),
    )
    rows = c.fetchall()
    print('Fetched ' + str(len(rows)) + ' candidate orgs.')

    found = 0
    misses = 0
    processed = 0

    for row in rows:
        processed += 1
        org_id = row['id']
        name   = row['name'] or ''
        city   = (row['city'] or '').strip()
        cc     = (row['country_code'] or '').strip()

        prefix = '[' + str(processed) + '/' + str(len(rows)) + '] id=' + str(org_id)
        print(prefix + ' ' + (name[:60] or '?') + ' -- ' + city + ', ' + cc)

        coords = nominatim_lookup(city, cc)
        if coords:
            lat, lon = coords
            print('  -> ' + str(round(lat, 4)) + ', ' + str(round(lon, 4)))
            found += 1
            if not args.dry_run:
                c.execute(
                    "UPDATE organizations SET lat=?, lon=?, geo_source='nominatim_city' "
                    "WHERE id=?",
                    (lat, lon, org_id),
                )
        else:
            print('  -> not found')
            misses += 1

        # Always advance the resume cursor so that a city we cannot geocode does
        # not get retried forever on the next run. Save state every 10 ops in
        # case the run is killed mid-way.
        last_id = org_id
        if not args.dry_run:
            if processed % 10 == 0:
                conn.commit()
                state['last_id'] = last_id
                state['total_geocoded'] = state.get('total_geocoded', 0) + 0  # snapshot only
                save_state(state)

        time.sleep(SLEEP_SEC)

    if not args.dry_run:
        conn.commit()
        state['last_id']         = last_id
        state['total_geocoded']  = int(state.get('total_geocoded', 0)) + found
        state['total_misses']    = int(state.get('total_misses', 0)) + misses
        save_state(state)

    conn.close()

    print('')
    print('=' * 60)
    print('SUMMARY')
    print('=' * 60)
    print('Processed this run: ' + str(processed))
    print('Found:              ' + str(found))
    print('Not found:          ' + str(misses))
    print('Last id (cursor):   ' + str(last_id))
    if not args.dry_run:
        print('Total geocoded all-time: ' + str(state.get('total_geocoded', 0)))
        print('Total misses all-time:   ' + str(state.get('total_misses', 0)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
