# Brief: Wave C — Long-Tail Country Atlas + OHADA + Indigenous/Informal

You are Claude Code. This brief is the source of truth. Read it once, then execute one slice at a time.

## What Wave C is (different from A and B)

Wave A and B were one-shot ingest sprints. **Wave C is a rolling weekly cadence.** Each weekly run does ONE of these slices and then stops:

1. Pull one country off the queue and run a country-specific researcher script
2. Build the OHADA cluster ingester (one-time, 15 francophone African countries via shared RCCM architecture)
3. Add one indigenous/informal source (PIAALC, IRI, Aboriginal co-ops Canada, BC Indigenous services, Jawun, Waste Pickers WAW, etc.)
4. Refresh `data/sources/REGISTRIES.yaml` with newly-verified URLs

The point is **steady geographic balance over time**, not a sprint.

## Pre-flight (every run)

```
cd C:\Users\simon\.openclaw\workspace\commonweave
git log --oneline -10
cat data/QUEUE-new-wave.txt | head -20
```

If `data/QUEUE-new-wave.txt` doesn't exist, you're on the **first run**. Bootstrap it:

1. Read `commonweave/NEW-WAVE-RESEARCH-SOURCE.md` country atlas tables.
2. For each country NOT already covered by Wave A or Wave B, write one line to `data/QUEUE-new-wave.txt`:
   ```
   <country_code>|<registrar_name>|<url_or_AUTHORITY>|<languages>|<entity_classes>|<priority>
   ```
   Priority levels: `1` = mission-first (community/nonprofit registry exists), `2` = general company register with object-clause search, `3` = authority-anchor only.
3. Sort by priority then country_code.
4. Commit the queue file with message "wave-c: bootstrap country queue from new wave atlas."

If the queue exists, pick the **next priority-1 line that hasn't been processed** (track state in `data/wave_c_state.json`).

## Slice-of-the-week logic

Each run picks ONE of these in this order of preference:

### A. OHADA cluster (only on the first run after bootstrap)
- 15 countries share one RCCM architecture: Benin, Burkina Faso, Cameroon, CAR, Chad, Comoros, Congo (Brazzaville), Cote d'Ivoire, DRC, Equatorial Guinea, Gabon, Guinea, Guinea-Bissau, Mali, Niger, Senegal, Togo. (17 OHADA member states actually; verify current list.)
- Build `data/ingest_ohada.py` once, run for all 17 in one sweep.
- Source: shared OHADA RCCM portal — search `ohada.org` for the unified register or country-specific RCCM portals.
- Per-country fallback: if RCCM doesn't expose searchable entity types, write a stub row with `legibility='unknown'` and a note for human review.
- `legibility='formal'` for confirmed RCCM rows.
- Mark all 17 OHADA countries as **processed** in `wave_c_state.json` after the sweep.

### B. Country-of-the-week
- Pop next priority-1 country off the queue.
- If it has a Wave A-style mission-first registry, build one ingester (model on `ingest_acnc.py` or `ingest_grounded_solutions.py`).
- If it only has a general company register with object-clause search, build a **lightweight researcher script** at `data/run_researcher_<CC>.py` modeled on `run_researcher_NG.py`. This bot does targeted Brave/web searches in the local language and writes a regional markdown file under `data/regional/<country_code>.md`, then ingests rows from that markdown.
- Mark country as **processed** with date.

### C. Indigenous/informal source-of-the-week (every 4th week)
- One source per run. Targets in priority order:
  1. PIAALC (Plataforma Indígena de las Américas) — `piaalc.org`
  2. Indigenous Resilience Initiative — `iri.org` or similar
  3. Aboriginal Co-operatives in Canada (NACCA) — `nacca.ca` member directory
  4. BC Indigenous Business Listing — BC government open data
  5. Jawun (Australian Indigenous corporate partnership) — `jawun.org.au`
  6. Waste Pickers Without Frontiers (WAW) — `globalrec.org`
  7. CPRI (Common Property Resource Institutions) — Honey Bee Network / SRISTI dataset
- All rows: `legibility='informal'` or `'hybrid'`.
- These rows are **protected from staleness auto-archive** by `staleness_check.py` (already configured).

### D. Registry catalog refresh (every 4th week, alternating with C)
- Visit 5 entries in `data/sources/REGISTRIES.yaml` where `last_checked` is older than 90 days.
- Update `last_checked`, fix dead URLs, update `update_frequency` notes.
- This is non-ingest housekeeping; no new rows expected.

## Hard rules

Same as Wave A. Plus:

- **One slice per run, then stop.** No sprinting through multiple countries in one session.
- **Always update `data/wave_c_state.json`** at the end of every run, even if the slice failed (record the failure with reason).
- **Indigenous/informal rows go through human-review queue first.** Don't auto-publish to the public directory in the same run. Add the rows with `status='pending_review'` and let Simon promote them via the existing review flow.

## Done criteria (per weekly run)

- [ ] One slice picked and executed (or a documented "no work" reason)
- [ ] `wave_c_state.json` updated
- [ ] Any new rows are idempotent and tagged with correct legibility
- [ ] One commit per slice, Feynman voice
- [ ] System event fired with weekly summary

## When you finish (per run)

```
openclaw system event --text "Wave C week-<n>: slice=<slice_name>, +<n> rows. Country distribution: US/UK <n>%, RoW <n>%." --mode now
```

If the queue is empty, send: "Wave C queue empty — atlas fully covered. Recommend graduation to monthly maintenance cadence."
