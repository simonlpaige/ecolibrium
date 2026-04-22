"""
Staleness check for Commonweave directory.

HEAD-checks org websites to find dead links. Flags unreachable orgs for
HUMAN REVIEW after 3 strikes. Never auto-archives a row.

Why the safeguards matter: a website-centric check, applied naively,
systematically prunes the most marginalized orgs (grassroots, informal,
non-Western, social-media-only). We do not want that. So we:

  * Skip the check entirely for orgs marked legibility='informal' or
    'hybrid'. These often have no web footprint by design.
  * Skip orgs whose description or notes contain a social platform URL
    (Facebook, WhatsApp, Telegram, Twitter/X, Instagram, YouTube). A
    social-first org is not dead just because its website is down or
    never existed.
  * Skip orgs added in the last 30 days. Let them settle first.
  * Skip orgs with no website. Their presence in the directory is not
    conditional on having one.
  * NEVER auto-transition to status='stale'. After 3 consecutive fails,
    the org gets staleness_flag='needs_review'. A human decides.

New columns (idempotent):
  last_verified_at TEXT
  staleness_flag TEXT        -- 'unreachable' or 'needs_review'
  staleness_count INTEGER DEFAULT 0

Usage:
    python staleness_check.py                  # batch of 500
    python staleness_check.py --limit 20       # small test batch
    python staleness_check.py --dry-run        # show what would be checked
    python staleness_check.py --country IN     # scope to one country
"""
import argparse
import os
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False

sys.path.insert(0, os.path.dirname(__file__))
from _common import DB_PATH, ensure_column, trim_audit_path


MAX_CONCURRENT = 30
BATCH_SIZE = 500
REQUEST_TIMEOUT = 10
BATCH_SLEEP = 0.5
STRIKES_BEFORE_REVIEW = 3
REVERIFY_DAYS = 180
NEW_ORG_GRACE_DAYS = 30
USER_AGENT = 'Commonweave/1.0 (+https://commonweave.earth)'

# Social platforms that count as legitimate primary presence.
# If an org's description/notes contain one of these, we do not treat
# website absence or 404 as a sign the org is dead.
SOCIAL_URL_PATTERNS = [
    r'facebook\.com', r'fb\.com', r'wa\.me', r'whatsapp\.com',
    r't\.me', r'telegram\.org', r'twitter\.com', r'x\.com',
    r'instagram\.com', r'youtube\.com', r'youtu\.be',
    r'tiktok\.com', r'linktr\.ee', r'mastodon\.',
]
SOCIAL_RE = re.compile('|'.join(SOCIAL_URL_PATTERNS), re.IGNORECASE)


def run_migration(db):
    ensure_column(db, 'organizations', 'last_verified_at', 'TEXT')
    ensure_column(db, 'organizations', 'staleness_flag', 'TEXT')
    ensure_column(db, 'organizations', 'staleness_count', 'INTEGER DEFAULT 0')


def get_domain(url):
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ''


def head_check(url):
    """HEAD (with GET fallback on 405) -> ('ok', code) or ('fail', reason)."""
    if not url or not url.startswith(('http://', 'https://')):
        return ('skip', 'no_url')
    try:
        if HAS_REQUESTS:
            resp = requests.head(
                url, timeout=REQUEST_TIMEOUT, allow_redirects=True,
                headers={'User-Agent': USER_AGENT}
            )
            if resp.status_code == 405:
                resp = requests.get(
                    url, timeout=REQUEST_TIMEOUT, allow_redirects=True,
                    headers={'User-Agent': USER_AGENT}
                )
            code = resp.status_code
            if 200 <= code < 400:
                return ('ok', code)
            return ('fail', code)
        else:
            req = urllib.request.Request(
                url, method='HEAD',
                headers={'User-Agent': USER_AGENT}
            )
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
                return ('ok', r.status)
    except Exception as e:
        return ('fail', str(e)[:80])


def row_has_social_presence(row):
    """True if the description/tags mention a social platform URL."""
    for field in ('description', 'tags'):
        val = row[field] if field in row.keys() else None
        if val and SOCIAL_RE.search(val):
            return True
    return False


def is_skippable(row, now):
    """
    Apply the red-team safeguards. Returns (skip: bool, reason: str).
    """
    legibility = row['legibility'] if 'legibility' in row.keys() else None
    if legibility in ('informal', 'hybrid'):
        return True, f'legibility={legibility}'

    if not row['website']:
        return True, 'no_website'

    if row_has_social_presence(row):
        return True, 'social_presence'

    # Grace period for recently added orgs
    added = row['date_added'] if 'date_added' in row.keys() else None
    if added:
        try:
            added_dt = datetime.fromisoformat(
                str(added).replace('Z', '+00:00')
            )
            if added_dt.tzinfo is None:
                added_dt = added_dt.replace(tzinfo=timezone.utc)
            if (now - added_dt).days < NEW_ORG_GRACE_DAYS:
                return True, 'too_new'
        except (ValueError, TypeError):
            pass

    return False, ''


def load_candidates(db, limit, country):
    """Load orgs that might be due for reverification."""
    c = db.cursor()
    cutoff_iso = (
        datetime.now(timezone.utc) - timedelta(days=REVERIFY_DAYS)
    ).isoformat()

    parts = ["status NOT IN ('removed', 'merged', 'stale')"]
    # Only pool orgs that actually have a website - no point loading
    # thousands of no-website rows only to skip them
    parts.append("website IS NOT NULL AND website != ''")
    parts.append(
        f"(last_verified_at IS NULL OR last_verified_at < '{cutoff_iso}')"
    )
    if country:
        parts.append(f"country_code = '{country.upper()}'")

    where = ' AND '.join(parts)
    # Oldest-due first: puts never-verified orgs and long-stale ones up front
    q = (
        "SELECT id, name, website, country_code, staleness_count, "
        "legibility, description, tags, date_added "
        f"FROM organizations WHERE {where} "
        "ORDER BY COALESCE(last_verified_at, '1970-01-01') ASC, "
        "date_added ASC "
        f"LIMIT {limit}"
    )
    c.execute(q)
    return c.fetchall()


def apply_results(db, results, dry_run, log_lines):
    c = db.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    ok_count = 0
    fail_count = 0
    needs_review = 0

    for row_id, name, url, outcome, reason in results:
        if outcome in ('skip', 'skipped'):
            continue
        if outcome == 'ok':
            ok_count += 1
            if not dry_run:
                c.execute(
                    "UPDATE organizations "
                    "SET last_verified_at=?, staleness_count=0, "
                    "    staleness_flag=NULL "
                    "WHERE id=?",
                    (now_iso, row_id)
                )
        else:
            fail_count += 1
            log_lines.append(f"  FAIL [{reason}] id={row_id} '{name}' {url}")
            if not dry_run:
                c.execute(
                    "UPDATE organizations "
                    "SET staleness_flag='unreachable', "
                    "    staleness_count=COALESCE(staleness_count,0)+1, "
                    "    last_verified_at=? "
                    "WHERE id=?",
                    (now_iso, row_id)
                )
                c.execute(
                    "SELECT staleness_count FROM organizations WHERE id=?",
                    (row_id,)
                )
                row = c.fetchone()
                if row and row[0] and row[0] >= STRIKES_BEFORE_REVIEW:
                    c.execute(
                        "UPDATE organizations "
                        "SET staleness_flag='needs_review' "
                        "WHERE id=?",
                        (row_id,)
                    )
                    needs_review += 1
                    log_lines.append(
                        f'    -> FLAGGED needs_review after '
                        f'{row[0]} strikes (human decides)'
                    )

    if not dry_run:
        db.commit()
    return ok_count, fail_count, needs_review


def main():
    ap = argparse.ArgumentParser(
        description='Grassroots-safe website staleness checker'
    )
    ap.add_argument('--limit', type=int, default=BATCH_SIZE,
                    help='Max orgs to check per run')
    ap.add_argument('--dry-run', action='store_true',
                    help='Show what would be checked, no writes')
    ap.add_argument('--country', help='Scope to one country code')
    args = ap.parse_args()

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    run_migration(db)

    pool_candidates = load_candidates(db, args.limit * 5, args.country)
    print(f'Pool considered: {len(pool_candidates)}')

    # Apply safeguards
    now = datetime.now(timezone.utc)
    to_check = []
    skipped_by_reason = {}
    for row in pool_candidates:
        skip, reason = is_skippable(row, now)
        if skip:
            skipped_by_reason[reason] = skipped_by_reason.get(reason, 0) + 1
        else:
            to_check.append(row)
        if len(to_check) >= args.limit:
            break

    print(f'Skipped (safeguards): '
          f'{sum(skipped_by_reason.values())} '
          f'[{", ".join(f"{k}={v}" for k,v in skipped_by_reason.items())}]')
    print(f'Will check: {len(to_check)}')

    if args.dry_run:
        for row in to_check[:20]:
            print(f'  [{row["country_code"]}] '
                  f'{row["name"]} -> {row["website"]}')
        if len(to_check) > 20:
            print(f'  ... and {len(to_check) - 20} more')
        db.close()
        print(f'[DRY RUN] Would check {len(to_check)} URLs.')
        return

    log_lines = []
    all_results = []

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as pool:
        futures = {}
        for row in to_check:
            futures[pool.submit(head_check, row['website'])] = (
                row['id'], row['name'], row['website']
            )

        done = 0
        for fut in as_completed(futures):
            row_id, name, url = futures[fut]
            outcome, reason = fut.result()
            all_results.append((row_id, name, url, outcome, reason))
            done += 1
            if done % 50 == 0:
                print(f'  Checked {done}/{len(to_check)}...')
            time.sleep(BATCH_SLEEP / MAX_CONCURRENT)

    ok, fail, review = apply_results(
        db, all_results, args.dry_run, log_lines
    )
    db.close()

    print(f'Results: {ok} ok, {fail} unreachable, '
          f'{review} flagged needs_review')

    # Write audit log + review-needed list
    log_path = trim_audit_path('staleness')
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(f'# Staleness Check - {today}\n\n')
        f.write('Safeguards active: informal/hybrid orgs skipped, '
                'social-first orgs skipped, orgs under 30 days old '
                'skipped, no-website orgs skipped. Orgs are NEVER '
                'auto-archived. After 3 strikes an org gets '
                'staleness_flag=needs_review and a human decides.\n\n')
        f.write('| Metric | Value |\n|---|---|\n')
        f.write(f'| Pool considered | {len(pool_candidates)} |\n')
        f.write(f'| Skipped by safeguards | '
                f'{sum(skipped_by_reason.values())} |\n')
        for reason, count in sorted(
            skipped_by_reason.items(), key=lambda x: -x[1]
        ):
            f.write(f'|   - {reason} | {count} |\n')
        f.write(f'| Checked | {len(to_check)} |\n')
        f.write(f'| OK (2xx/3xx) | {ok} |\n')
        f.write(f'| Unreachable | {fail} |\n')
        f.write(f'| Flagged needs_review | {review} |\n\n')
        if log_lines:
            f.write('## Failure log (first 300)\n\n```\n')
            for line in log_lines[:300]:
                f.write(line + '\n')
            if len(log_lines) > 300:
                f.write(f'... and {len(log_lines) - 300} more\n')
            f.write('```\n')

    print(f'Log: {log_path}')


if __name__ == '__main__':
    main()
