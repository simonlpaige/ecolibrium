# Findcoop / Data Commons Cooperative — partnership outreach

Status: pending. Created 2026-04-26 by Wave B ingest job.

## Why this is outreach, not scraping

Wave B's brief says Find.coop is a "scrape last, ask first" source. Their
catalog is the labour of a coop-of-coops (Data Commons Cooperative) and they
explicitly frame the directory as a shared resource that members contribute
to. Pulling it without a conversation would be impolite even where ToS
technically allows it, and the goodwill from doing this right is worth more
than the few thousand rows we'd save by not asking.

So we don't scrape. We ask.

## What we want

In rough priority order:

1. A bulk-export feed (CSV, JSON, or a queryable API) of the Find.coop
   directory keyed on a stable identifier so we can re-pull idempotently.
2. Permission to mirror that feed inside Commonweave's directory with
   per-row attribution back to the Find.coop entry, refreshed on whatever
   cadence they're comfortable with.
3. A two-way arrangement where any cooperative we discover via national
   registry ingest (UK FCA mutuals, US co-ops, ACNC charities flagged as
   cooperatives, etc.) can be offered back to Find.coop as a candidate.

If they prefer a one-way "you can show our data, we'll show yours" link
exchange instead of a feed, that's also fine and we'll wire it to the
"powered by" footer pattern.

## What we can offer

- Co-branded entry in Commonweave's "global cooperative networks" rail.
- Engineering help on whatever export plumbing they need. The maintainers
  are busy and a working CSV endpoint on their side is more useful to us
  than a one-off scrape we'd have to maintain forever.
- Public credit on commonweave.earth/about, at the source level on each
  row, and in DATA.md.

## How to start the conversation

- Primary contact: the Data Commons Cooperative steward at
  https://datacommons.coop/contact (or whoever Find.coop currently lists
  on its colophon page).
- Secondary contact: any RIPESS NA / NEC member who already has a working
  relationship there. Ask before cold-emailing.
- Tone: short, specific, no salesy language. We are a cousin project, not
  a customer.

## Tracking

- Owner: @alphaworm
- Next action: send first email.
- Follow-up cadence: two weeks.
- File this entry under done once we have a yes / no / not-yet decision.
