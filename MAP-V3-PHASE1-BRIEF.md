# MAP-V3-PHASE1-BRIEF.md

Phase 1 build brief. Read this and `MAP-V3-PLAN.md` first. The plan's section 5 is your task list. Execute it.

## Decisions from Simon (2026-04-25 21:47 CDT)

- **Q1 homepage count framing: Option A.** Lead with full transparency. Use three numbers: "26,022 candidates / 11,991 mapped / 60+ countries" (or whatever the actual numbers are after stats.json is generated, three-tier framing kept). Pull all numbers from `data/map/stats.json` at runtime. Update homepage hero, meta description, og:description, the iframe footer, and the section card counts.
- **Q4 default `risk_context`: `'normal'`.** All currently unmarked orgs default to `'normal'`. Add the column/field but do not start jittering or hiding points yet. The schema and field plumbing land now; populating sensitive flags is a future pass.

Other Phase 1 decisions (you can make these):
- **Tier B label**: pick "Verified (from registry)" and use it everywhere. Update both code (`map.html` line 513 area) and any README references.
- **Runtime fetch vs build-time substitution for index.html counts**: use runtime fetch. Lower risk, no build pipeline change.
- **Use the existing repo, branch off `master`** into `map-v3-phase1`. Commit per task or per logical group, your call. Push the branch but do NOT merge or open a PR. Simon reviews before merge.

## Hard rules

1. **Static-first.** No new backend, no new paid services, GitHub Pages must keep working.
2. **No MapLibre rewrite in this phase.** Phase 1 keeps the existing D3 + topojson stack. Just make it honest.
3. **No deletions of legacy files yet.** `build_map_points.py` and `map_meta.json` stay where they are. Note them in a "Phase 5 cleanup" section in the plan; do not retire them now.
4. **Voice rules apply to commit messages and any new docs**: Feynman "Curious Explainer" voice. Plain language. No em dashes ever. No AI marketing-speak.
5. **No external network writes.** Do not post to GitHub Issues, do not send emails, do not run any deploy. Just code, commit, and push the branch.
6. **If you find something that needs Simon to decide, write it into a `MAP-V3-PHASE1-NOTES.md` file in the repo root.** Do not block on it. Pick a reasonable default, note the choice, keep going.

## Tasks (from `MAP-V3-PLAN.md` section 5)

Work through these in order. They are mostly independent but 1.1 and 1.9 must land before 1.2-1.6 are useful.

- [ ] 1.1 Single source of truth for counts via `data/map/stats.json`. Modify `data/build_map_v2.py` to also write this file. Run the script. Record numbers.
- [ ] 1.2 Reconcile `index.html` to fetch from `data/map/stats.json` at runtime. Replace all hardcoded "27.3K", "27,300+", "172 countries", and per-section counts. Update meta description and og:description (these can stay hardcoded but use the new honest numbers).
- [ ] 1.3 Add `data/check_counts.py` that reads `stats.json` and verifies the README's headline numbers match. Warning, not abort. Wire into the existing build process if there is a clear hook; otherwise document how to run it.
- [ ] 1.4 Tier legend in `map.html` sidebar. Visible block: "A Curated. B Verified (from registry). C Inferred. D Unverified, not on map." Counts pulled from stats.json.
- [ ] 1.5 URL-state filters via `location.hash` + URLSearchParams. Serialize `{section, tiers, country, search, selectedId, zoom}`. Restore on load. Debounced.
- [ ] 1.6 Real detail panel. Audit existing renderer. Show: name, primary + secondary sections, description, location, website, contact_url if present, source, tier badge, "Suggest correction" GitHub-issue prefilled link, "Copy share link" button.
- [ ] 1.7 High-confidence-only toggle. Promote the existing default to a single prominent switch with tooltip.
- [ ] 1.8 Edge provenance fields in `data/build_map_v2.py`. Add `id`, `source_id`, `target_id` (use stable org ids), `evidence: []`, `weight` separate from `confidence`, `derived: true`. Document in `data/map/schema.edge.json` (stub is fine).
- [ ] 1.9 Stable org ids on the wire. Add `id` field to `map_points_v2.json`. Either stop stripping at line ~348, or re-add a stable id (`org_<sqlite_id>`).
- [ ] 1.10 Visible "Data last built: YYYY-MM-DD" footer in map UI, pulled from stats.json.
- [ ] 1.11 Update DIRECTORY.md headline counts from stats.json (thread through `export_directory.py`).
- [ ] 1.12 Acceptance check (manual). Document the result in `MAP-V3-PHASE1-NOTES.md` with what passed and any issues.

## Acceptance test

A visitor can open the map, filter to Tier A/B, click one org, see where the data came from, and copy a link to that exact view. The homepage counts match what is shown on the map and the README headline numbers, all sourced from `data/map/stats.json`.

## Deliverables

When done:
1. Branch `map-v3-phase1` pushed to origin (NOT merged to master).
2. `MAP-V3-PHASE1-NOTES.md` in the repo root documenting:
   - Numbers from the new `stats.json`
   - Decisions you made on your own
   - Anything that surprised you
   - The acceptance test result
   - Any sub-task you skipped or partially completed and why
3. A short final terminal printout summarizing: branch name, commit count, files changed, and whether the acceptance test passed.

Do not open a PR. Do not merge. Stop after the branch is pushed.
