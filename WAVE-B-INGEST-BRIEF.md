# Brief: Wave B — Thematic Global Networks Ingest

You are Claude Code. This brief is the source of truth. Read it once, then execute.

## Pre-flight

Before doing anything, run:
```
cd C:\Users\simon\.openclaw\workspace\commonweave
git log --oneline -10
python data/check_counts.py
```

If you don't see commits referencing `ingest_acnc`, `ingest_bulgaria_npo`, and `ingest_brazil_oscs` (or equivalents from Wave A), STOP. Send:
```
openclaw system event --text "Wave B blocked: Wave A not committed yet. Last commit: <hash>" --mode now
```

If Wave A is committed, proceed.

## Mission

Add **thematic global directory ingesters** for cooperative networks, solidarity economy umbrellas, mutual aid lists, and intentional community directories. These are smaller in row count than national registries but every row is high-alignment by definition (they're already mission-curated).

Target: ~5,000–10,000 new rows, geographically balanced.

## Why Wave B

Wave A added national-registry coverage. Wave B fills the gap that registries miss: the **thematic, mission-first networks** where alignment is the entry criterion. A row in RIPESS or Find.coop is high-alignment by virtue of membership, not by keyword luck.

Wave B also seeds the underrepresented framework areas — especially **Energy & Digital Commons** (only 40 rows today) and **Cooperatives & Solidarity** (656 rows).

## Hard rules

Same as Wave A's brief. Read `WAVE-A-INGEST-BRIEF.md` Hard Rules section. Plus:

- **Some sources may need partnership outreach instead of scraping.** If a directory's robots.txt forbids scraping or the ToS is restrictive (Find.coop, Data Commons Cooperative are likely candidates), do NOT scrape. Instead, log a TODO entry pointing at `tools/mycelial-outreach/` for @alphaworm to handle as an outreach conversation. Skip and continue.
- **Legibility tagging matters here.** Wave A is all `formal`. Wave B will be a mix:
  - Cooperative networks (RIPESS, ICA, Find.coop, .coop): `formal`
  - Mutual Aid Wiki, Transition Network local groups, IC Directory: `hybrid` (registered some places, informal others)
  - Always tag at ingest time. Don't default to formal.

## Targets, in priority order

### 1. `ingest_susy_map.py` — SUSY Map (EU social/solidarity economy)
- Source: `https://www.solidarityeconomy.eu/susy-map/` or `http://susy.ripess.eu/` — find the data endpoint. Likely a Leaflet/GeoJSON layer.
- ~1,200 EU initiatives, geocoded. Easy parse.
- `legibility='formal'`, `framework_area` mapped from category.

### 2. `ingest_transition_network.py` — Transition Network local groups
- Source: `https://transitionnetwork.org/transition-near-me/` — has a JSON map endpoint.
- ~1,000+ local groups globally.
- `legibility='hybrid'` (registered varies by country).

### 3. `ingest_ic_directory.py` — Intentional Communities Directory (ic.org)
- Source: `https://www.ic.org/directory/` — JSON/CSV export available to members; check for a public API.
- ~1,200 communities globally.
- `legibility='hybrid'`.

### 4. `ingest_clt_world_map.py` — Schumacher Center CLT World Map
- Source: `https://centerforneweconomics.org/apply/community-land-trust-program/cltwm/` — find the GeoJSON layer.
- ~600 CLTs globally. Many will already be in the directory from Grounded Solutions / Wikidata; idempotent upsert handles this. Cross-check against existing `framework_area='housing_land'` rows.

### 5. `ingest_mutual_aid_wiki.py` — Mutual Aid Wiki
- Source: GitHub repo of crowd-sourced mutual aid groups. Search github.com for "mutual-aid-hub" or "mutualaid.wiki" data dumps.
- Already structured (CSV or JSON in repo).
- `legibility='informal'` on every row.

### 6. `ingest_nec_members.py` — New Economy Coalition members
- Source: `https://neweconomy.net/members/` — scrape member directory.
- ~200 US/Canada orgs. Small but high-quality.
- `legibility='formal'`.

### 7. `ingest_ica_directory.py` — ICA Cooperatives Connect (global cooperative apex)
- Source: `https://www.ica.coop/en/cooperatives/our-members` — country list of national cooperative apex orgs.
- Apex orgs only (not individual co-ops). ~100 entries but each is a national federation.
- `legibility='formal'`.

### 8. `ingest_ripess.py` — RIPESS + RIPESS LAC + RAESS + ASEC
- Sources: `ripess.org`, `riless.org`, `raess.org`, `asec.coop` — scrape member rosters.
- ~300 orgs combined.
- `legibility='formal'`.

### 9. `ingest_findcoop.py` — Find.coop / Data Commons Cooperative
- **Outreach first.** Log a TODO at `tools/mycelial-outreach/drafts/pending/findcoop-partnership-2026-XX-XX.md` describing what we want (data sharing or directory mirror). Do not scrape until Simon confirms outreach result. Skip this for now; ship the others and announce.

## Cross-cutting

- All ingesters: same conventions as Wave A (cache, log, idempotent, `--dry-run`, `--refresh`).
- Update `data/sources/REGISTRIES.yaml` with thematic entries (use `country_code: GLOBAL` for borderless networks).
- After all ingesters run, re-run `python data/phase2_filter.py` to apply the legal-form scorer.
- Update `DATA.md` with new sources and counts.

## Done criteria

- [ ] At least 6 of the 8 thematic ingesters land cleanly (Find.coop is exempted; outreach pending)
- [ ] Each ingester is idempotent
- [ ] Legibility tagging is correct per source (mix of formal / hybrid / informal)
- [ ] DATA.md updated
- [ ] Energy & Digital Commons row count grows (currently 40)
- [ ] One commit per ingester, Feynman voice, no squashing

## When you finish

```
openclaw system event --text "Wave B done: <n> new rows across <m> thematic networks. Total directory: <n>. Energy & Digital Commons: <n> (was 40)." --mode now
```

If blocked: same pattern as Wave A.
