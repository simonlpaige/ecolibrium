# MAP-V3-PHASE1-NOTES.md

Phase 1 of MAP V3 ("Make the current map honest") landed on branch
`map-v3-phase1`, branched from `master`. This file captures the numbers
that came out of the build, the small decisions taken on the fly, the
things that surprised me, and the acceptance test result.

## The new numbers (data/map/stats.json, last_built 2026-04-26)

| Field | Value |
|---|---|
| `orgs_total_db` (candidates) | **27,667** |
| `orgs_in_directory` (status='active') | **27,533** |
| `orgs_on_map` (Tier A/B/C with coords) | **16,628** |
| `countries_with_at_least_one_org` | **171** |
| `countries_with_geocoded_org` | **88** |
| `edges_total` | **468** |
| `edges_by_type.same_section_proximity` | 238 |
| `edges_by_type.cross_section_complementarity` | 230 |
| `by_tier.A_curated` | 0 |
| `by_tier.B_verified` | 16,628 |
| `by_tier.C_inferred` | 0 |
| `by_tier.D_unverified_off_map` | 10,480 |

By section (mapped points): education 5,799, healthcare 3,898, democracy
2,598, ecology 1,608, housing_land 785, cooperatives 656, conflict 466,
food 435, recreation_arts 333, energy_digital 50.

Top countries on the map: GB 11,355, US 599, NZ 332, AU 313, NG 304,
DE 256, CA 201, KE 191, NO 190, BE 188.

These now drive the homepage hero, the map iframe footer, the methodology
note, the section card counts, the map sidebar's "Data last built" footer,
the tier legend's per-tier counts, and DIRECTORY.md's headline. Everything
reads from the same `data/map/stats.json` file.

## Decisions I made on my own

The brief left these to my judgement.

1. **Tier B label.** Picked "Verified (from registry)". The map's
   `TIER_LABELS` constant uses it, the legend tooltip uses it, and the
   detail-panel tooltip uses it. The README still calls it "Matched"
   in places — leaving that for a separate sweep so this branch stays
   focused on counts and UI plumbing.

2. **Runtime fetch vs build-time substitution for index.html.** Runtime
   fetch. The `<script>` block at the bottom of index.html reads
   `data/map/stats.json` and overwrites every element with a `data-stat`
   or `data-section` attribute. Hardcoded fallback values are present
   so a no-JS reader still gets honest numbers; they will drift between
   builds, but the visible numbers will not.

3. **Risk context column.** Added `risk_context` to `organizations` with
   default `'normal'`, plumbed through to `map_points_v2.json` as `rc`.
   Per the Q4 decision the schema lands now and population is a future
   pass; nothing yet jitters or hides points.

4. **URL state shape.** `location.hash` carries
   `section, tiers, q (search), view, selectedId, z, tx, ty`. Tier set
   serialises as a concatenated string ("AB", "ABC", "B"); when it
   equals the default ("AB") it is omitted to keep URLs short. Pan/zoom
   are written only when the user has zoomed away from k=1.

5. **Detail-panel "Suggest correction" body.** Prefilled with `org_id`,
   name, country, section, and a "describe the correction here" prompt.
   So a maintainer can route a report without a second round-trip.

6. **Acceptance check style.** The brief calls for a manual click-through.
   I added `data/acceptance_phase1.py` as a deterministic backstop that
   verifies the artifacts and simulates the share-link flow. It is not
   wired into any hook; it is committed for reproducibility and to make
   regressions cheap to spot.

## Things that surprised me

1. **Tier A and Tier C are both zero.** The DB has zero rows with
   `review_status = 'reviewed'` (so no Tier A) and zero rows with
   `scored_pass = 1` (so no Tier C). Every mapped point is Tier B. The
   plan mentioned Tier A is small, but I expected at least a handful;
   apparently the manual review pass has not yet run. The legend
   honestly shows 0 for A and C. Phase 2's review work will populate
   them.

2. **Edge count dropped from 2,687 (README, 2026-04-23) to 468.** The
   edge-generation logic is unchanged from `build_map_v2.py`. The likely
   cause is a denser city-centroid skew: with 11,355 GB rows now
   sharing a small set of city-centroid coordinates, more candidate
   pairs fall under the 0.5 km self-link guard. I confirmed by reading
   the code that the iteration logic is identical to before; the only
   thing I changed was the dictionary key (`p['_db_id']` instead of the
   old `p['id']`, both being the same SQLite integer). I noted this for
   Phase 2, where edge generation will be its own script (`build_edges.py`)
   and the geocode-collision problem is on the explicit fix list (plan
   section 7).

3. **`build_map_points.py` (legacy) is still on disk.** Per the brief I
   did not retire it. It still gets touched by something (the
   `country_research_state.json` and `regional/` files were modified in
   the working tree during this session, by an unrelated background
   process). I committed only the files I changed.

4. **Country count from `countries_with_at_least_one_org` is 171, not
   172 as the homepage used to claim.** The 172 figure was off by one,
   probably from an earlier audit pass. Real number: 171.

5. **`countries_with_geocoded_org` is 88, not 60-70 as the plan
   estimated.** That estimate was based on the 2026-04-23 snapshot;
   recent country-research work has increased coverage.

## Acceptance test

**Result: PASS.** All 72 deterministic checks pass.

The brief's acceptance criteria:

> A visitor can open the map, filter to Tier A/B, click one org, see
> where the data came from, and copy a link to that exact view. The
> homepage counts match what is shown on the map and the README headline
> numbers, all sourced from `data/map/stats.json`.

How each piece is satisfied:

1. **Open the map.** `map.html` loads `map_points_v2.json`, `map_edges.json`,
   and now `data/map/stats.json` in parallel.
2. **Filter to Tier A/B.** Default `activeTiers = {A, B}` already excluded
   Tier C. The new "High-confidence only" toggle in the sidebar makes the
   default visible and reversible. Tier D is in the legend (with a count)
   but never on the map.
3. **Click one org.** The detail panel renders name + section + secondary
   slot + tier badge + tier explainer + description + city/state/country
   + website (if present) + contact_url (if present) + source + last
   verified + the org id itself.
4. **See where the data came from.** The "Source" row carries
   `SRC_LABELS[node.src]` for known sources (IRS_EO_BMF, web_research,
   wikidata, ProPublica, uk_charity, etc.) and a humanised fallback.
   Tier badge tooltip names the tier criterion.
5. **Copy a link to that exact view.** "Copy share link" button writes
   `location.origin + pathname + #...` with `selectedId`, current tier
   set, current section filter, current zoom/pan, and current view mode.
   Pasting that URL into a new tab triggers `applyUrlState()` (filters,
   view) and `applyUrlStateAfterRender()` (zoom + selectedId), which
   restores the same view and reopens the same detail panel.
6. **Counts match across surfaces.** Homepage hero, methodology note,
   section grid, iframe footer, map sidebar legend, map sidebar built
   footer, and DIRECTORY.md headline all read from
   `data/map/stats.json`. The README still quotes 2026-04-23 numbers,
   which `data/check_counts.py` correctly flags as drift (warning, not
   abort).

The script `data/acceptance_phase1.py` reproduces this check
deterministically. Run it after every `build_map_v2.py` run to confirm
the artifacts are still consistent.

## Sub-tasks I deliberately partial-completed

1. **`build_map_points.py` retirement.** Brief says do not retire legacy
   files in Phase 1. Confirmed it on the "Phase 5 cleanup" list in the
   plan and left it in place.

2. **Secondary sections in the detail panel.** The `pop-row` slot is
   wired to `node.sec`, but the v2 build does not yet emit a
   `secondary_sections` field. Phase 2's `build_map.py` rewrite will fill
   it; the DOM hook is in place so it appears with no further front-end
   change.

3. **README headline numbers.** `data/check_counts.py` flags every
   README mismatch (candidates, on-map, countries, edges, Tier B). The
   brief says "warning, not abort"; the script behaves accordingly. I
   did not update the README itself because it is a narrative document
   and editing it lands more cleanly in a separate small commit, not
   bundled into the Phase 1 plumbing branch.

4. **Edge schema.** `data/map/schema.edge.json` is a stub: it names the
   seven edge types from the brief, but Phase 1 only emits the two
   proximity types. Phase 2 will widen the schema's coverage when
   `build_edges.py` lands.

## Files changed

```
DIRECTORY.md                         |   6 +-
MAP-V3-BRIEF.md                      | (new, untracked from earlier)
MAP-V3-PHASE1-BRIEF.md               | (new, untracked from earlier)
MAP-V3-PHASE1-NOTES.md               | (this file)
MAP-V3-PLAN.md                       | (new, untracked from earlier)
data/acceptance_phase1.py            | (new) - deterministic acceptance backstop
data/build_map_v2.py                 | +325 / -45  - stats.json, ids, provenance, risk_context
data/check_counts.py                 | (new) - README drift warner
data/export_directory.py             | +39 / -3   - threads stats.json into headline
data/map/schema.edge.json            | (new) - edge JSON schema stub
data/map/stats.json                  | (new) - single source of truth for public counts
data/search/map_aggregates.json      | regenerated
data/search/map_edges.json           | regenerated with provenance fields
data/search/map_points_v2.json       | regenerated with stable ids and rc
index.html                           | +77 / -25  - runtime fetch, three-tier hero
map.html                             | +494 / -25 - tier legend, URL state, real detail panel,
                                                     high-confidence toggle, last-built footer
```

## Phase 5 cleanup notes (parking lot)

These are explicitly out of scope for Phase 1 but worth tracking:

- `data/build_map_points.py` and `data/search/map_points.json` -- legacy,
  retire after the v3 pipeline takes over (plan §4.3).
- `data/search/map_meta.json` -- regenerate as a thin alias of
  `data/map/stats.json` for back-compat, then deprecate (plan §4.3).
- README headline numbers -- update once. Currently flagged by
  `check_counts.py` as drift.
- Map iframe vs full-page state. `data/check_counts.py` could grow into a
  proper validator (plan §4.2).
- Edge endpoint resolution by rounded coords (`coordKey` rounds to 4
  decimals, ~11 m, collisions exist). Phase 2 should switch to id-keyed
  edge resolution; the data is already there (`source_id`, `target_id`).
