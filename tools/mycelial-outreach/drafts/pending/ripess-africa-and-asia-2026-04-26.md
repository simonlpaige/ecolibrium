# RIPESS Africa (RAESS) and RIPESS Asia (ASEC) — outreach + data revival

Status: pending. Created 2026-04-26 by Wave B ingest job.

## Why this is outreach, not scraping

The brief told us to ingest member rosters from raess.org (RIPESS Africa,
also called RAESS) and asec.coop (RIPESS Asia, ASEC). When we tried,
both domains failed DNS lookups; neither server is reachable in
April 2026. Same goes for riless.org's older content (the domain still
resolves but has been bought by an unrelated Australian housing blog).

So there is nothing to scrape. The work that exists has to come through
a conversation with the regional networks instead.

What we did manage to ingest from this family lives in
data/ingest_ripess_family.py: 9 umbrella entries seeded from the RIPESS
member directory, plus members of RIPESS Europe (45), RIPESS LAC (20),
and RIPESS NA (3) pulled through the socioeco.org mirror. About 80
rows, all formal.

## What we want

In rough priority order:

1. A working contact at RIPESS Africa (RAESS) and RIPESS Asia (ASEC).
   The RIPESS umbrella's contact email is info@ripess.org; that is the
   first place to ask.
2. A data-sharing arrangement so we can mirror their member rosters in
   the directory. Even a one-page CSV of "country, name, website,
   contact" per region would close the gap for thousands of orgs we
   currently have no path to.
3. If they would prefer not to share data directly, ask whether they
   would be open to publishing the rosters anywhere a directory bot
   could crawl: a static page, a Google Sheet with view permission,
   an Airtable view, a downloaded XLS - the format does not matter as
   long as it is a stable URL.

## Why this matters for Commonweave

RIPESS members are by definition mission-aligned. Every row that comes
out of this conversation is a row we do not have to keyword-score. They
are also concentrated in the Global South, which is where Wave A's
national-registry coverage is thinnest.

## Tracking

- Owner: @alphaworm
- Next action: email info@ripess.org introducing Commonweave and asking
  for a warm handoff to RAESS and ASEC.
- Follow-up cadence: two weeks.
- Mark this entry done once we have either a yes / no / not-yet from
  each region, or a working alternative.
