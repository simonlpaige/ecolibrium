# Wave D — Improvement Loop (the second pass)

*Drafted 2026-04-26 by Larry. Status: spec, not yet built.*

## What Wave D is

Wave A built the mission-first registry pipeline (~30 sources, big yield). Wave B added thematic global networks (~9k rows). Wave C is the rolling country-atlas + indigenous-informal cadence.

Wave D is **the engine that makes Waves A-C better in a second pass.** It's not a new ingest sprint — it's the auditor + queue-rewriter that catches what we missed.

The shape Simon described 2026-04-26: *"finish the loop once, then go back through to pick up things we haven't found and improve the ingest and network edge finding."*

## When Wave D triggers

Two preconditions, both required:

1. Wave A is ≥80% done (Brazil + India + Bulgaria + Australia + NZ + 5 more landed)
2. Wave C has cleared 50+ countries from `data/QUEUE-new-wave.txt`

Until then, Wave D is just this spec. Don't build prematurely.

## What Wave D actually does

Five passes. Each writes evidence, never auto-mutates the DB. Simon decides what to act on.

### Pass 1 — Coverage gap audit

For each country with active orgs in our DB:

- Compare our active count to known-population baselines (charity-density estimates from OECD, World Giving Index, registered-NPO counts where the registrar publishes a top-line number).
- Flag countries where our count is **<10% of the published baseline**. That's a registry we're either not pulling correctly or didn't ingest.
- For each flagged country, run a one-shot Brave search for "<country> nonprofit register" and "<country> public benefit organization registry" to find sources we missed.
- Output: `data/trim_audit/coverage-gaps-<date>.md` with country-by-country gap table + new-source candidates.

### Pass 2 — Per-source quality audit

For each `source` value in `organizations`:

- Stale-rate: % of rows in this source that haven't been re-verified in 90+ days.
- Match-rate: % of rows that successfully merged with another source via dedup. High match-rate means the source confirms what we already had (good for trust); low match-rate means either novel-coverage (great) or junk (bad).
- Field-fill-rate: % of rows missing description / website / location / legal_form.
- Output: `data/trim_audit/source-quality-<date>.md`. Each source gets a one-line scorecard.

This is where the `state_province` regression from Wave B would have surfaced automatically: 9 ingesters all show "field-fill-rate=100% but 40% of values are non-postal-code strings." Worth designing the audit so this kind of malformed-but-non-empty data is caught.

### Pass 3 — Network edge discovery (the big one)

This is the "network edge finding" Simon called out. We currently store orgs as nodes in `organizations` but barely connect them. Edges that exist already:

- `parent_org_id` (filled <5% of rows)
- `affiliation_network` (filled <2%, mostly ITUC + ICA hand-coded)

What's missing: most orgs in the same town/sector probably know each other. Most CLTs in the same state probably share a backbone. Most mutual-aid groups in the same metro probably overlap.

Wave D Pass 3 mines the corpus we already have for *implicit* edges:

- **Co-mention edges**: when two orgs are named on the same source page (e.g. CLT World Map's per-state list, ICA's per-country list), draw an edge.
- **Shared-website-domain edges**: orgs with the same root domain are part of one entity (chapters, programs).
- **Shared-address edges**: orgs at the same address are co-located, often share governance.
- **Affiliate-mention edges**: scrape org websites for "we're a member of X" / "affiliated with Y" mentions; resolve those to existing org rows where possible.
- **Grant-flow edges (stretch)**: ProPublica + UK Charity Commission publish grant data. Donor-org → grantee-org is a real edge type. Heaviest lift.

Output: `data/edges/` directory with one CSV per edge type. Map UI gets a toggle to render any edge layer on top of the node map. (The `build_map_v2.py` script already emits `map_edges.json` — Pass 3 fills it.)

### Pass 4 — Re-ingest opportunity scoring

For each source we already ingested, score whether re-ingesting in 6 months would be worth it:

- **Stale + high-volume sources** (IRS BMF, UK CC) — yes, refresh quarterly.
- **Stable + small** (Schumacher CLT World Map, IC Directory) — re-check annually.
- **One-shot frozen exports** (SUSY Map GeoJSON) — only re-check when source publishes a new version. Add a `last_known_publish` field per source and ping the source URL monthly to detect changes.
- Output: `data/sources/REGISTRIES.yaml` gets a `re_ingest_cadence` field per row.

### Pass 5 — OpenBrain feedback ingestion

The Track-3 piece. By the time Wave D runs, OpenBrain has months of `commonweave/*` thoughts captured: proposals, audit reports, action items, snapshot deltas. Pass 5 queries OB1 for thoughts tagged `commonweave + action` that are 14+ days old and **never executed** (no daily memory entry referencing the action). Those become Wave D's TODO list — actions that surfaced in evidence and got buried.

Output: `data/trim_audit/buried-actions-<date>.md`. Each row is one OB1 action, age, source, and a one-liner suggestion for whether to revive, kill, or refile.

## Cadence

Wave D runs **monthly** (first Saturday of each month, 8am CT) once preconditions are met. Each pass is independent — Pass 3 (edges) is the heaviest and could run quarterly while the others run monthly. We can split the cron later if needed.

## Outputs go where Simon already looks

All Wave D artifacts go to `commonweave/data/trim_audit/`. The OpenBrain weekly capture cron picks them up automatically — they get ingested as evidence, OB1 extracts action items, and the cycle keeps tightening.

## What Wave D does NOT do

- Does not auto-archive orgs (staleness already does that, with safeguards).
- Does not auto-merge edges (Simon reviews the new edge files before they're committed to the directory).
- Does not run any new external scrapes during the audit pass — uses cached data and existing source URLs.
- Does not fix Wave B's `state_province` regression. That's a Wave B QA task that comes first (see WAVE-B-KNOWN-ISSUES.md).

## Build order when preconditions hit

1. Pass 1 first — fastest, highest signal, validates the framework.
2. Pass 2 — catches data-quality regressions early.
3. Pass 5 — wires in the OpenBrain side; small lift, high payoff.
4. Pass 4 — paperwork pass on REGISTRIES.yaml.
5. Pass 3 last — biggest design lift, has the most novel value.

## Estimated effort when we get there

- Passes 1, 2, 4, 5: one to two days each.
- Pass 3 (edges): one to two weeks. The map integration is the slow part.

## Open questions for Simon (whenever Wave D triggers)

1. **Public visibility of edges** — render Pass 3 edges on commonweave.earth/map, or keep them in admin-only view until Simon validates a sample?
2. **Re-ingest budget** — Wave D Pass 4 will recommend cadences. Some (IRS BMF) will burn API quota. Set a monthly token/API cap so re-ingest doesn't surprise us?
3. **OB1 action revival** — Pass 5 will surface buried action items. Want them auto-filed as `DAILY_TODO.md` rows, or always-manual?
