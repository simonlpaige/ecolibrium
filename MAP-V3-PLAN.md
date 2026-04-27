# MAP-V3-PLAN.md

Plan for the v3 Commonweave map. Research and planning only. No code changes in this pass.

Voice: plain language, no marketing-speak, no em dashes. Author: Claude, 2026-04-25, in response to MAP-V3-BRIEF.md.

---

## 1. Current state audit

### 1.1 What actually exists today

The current map is a single file, `map.html`, about 60KB. It is not a "pin map." It is a hybrid D3 visualisation with two view modes and edge rendering already wired in.

What `map.html` does today:

- **Stack:** D3 v7 + topojson-client v3 from unpkg. **No MapLibre, no deck.gl, no Leaflet.** It draws to a single `<canvas>` element, with the world basemap pulled at runtime from `world-atlas@2/countries-110m.json`.
- **Two view modes:** `network` (force-directed simulation with section cluster centres at fixed simulation coordinates) and `geo` (equirectangular projection of `lo, la`).
- **Loads two files at startup:** `data/search/map_points_v2.json` (~4.5MB, ~12.5K points) and `data/search/map_edges.json` (~100KB, ~2.7K edges).
- **Default filter is already Tier A+B.** Line 513 of `map.html`: `let activeTiers = new Set(['A', 'B']);` with the comment "Default: high-confidence only (Tier A + B). Tier C toggled off until user enables." Good. The brief asks for a "high-confidence only" toggle and it is half-done already.
- **Edges already render.** `drawEdges()` exists at line 967. The edges are read from `map_edges.json`, endpoint coords are matched back to nodes via a `coordHash` that rounds to 4 decimals.
- **Tier labels in code:** `{ A: 'Curated', B: 'Verified', C: 'Inferred' }`. These differ from the README, which calls Tier B "Matched" and Tier C "Inferred". Drift.
- **Detail panel exists** but it is filled at click time from JS rather than driven by a separate template.
- **No URL state.** No `location.hash`, no `URLSearchParams`. Filters reset on reload.
- **No tier legend visible in DOM.** Tier filter buttons exist; a legend explaining what A/B/C mean does not.
- **Section filters, country filters, search box all exist** in the sidebar (`.sb-stats`, `#filters`, `#tier-filter`, `#regions`).
- **System completeness dots exist as a static visual** in `.sb-health`. They are not yet driven by viewport state.

What `data/build_map_v2.py` does today:

- Assigns tiers in SQL: A (reviewed + description + website), B (reviewed/sourced with public detail), C (passed keyword scorer), D (everything else active).
- Exports Tier A/B/C points only to `map_points_v2.json`. Tier D is excluded from the map by design.
- Generates edges between Tier A+B points only. Spatial grid index, 50km max distance, max 5 edges per org, deduped by ordered id pair. Two edge categories:
  - `same_section`: same `framework_area` within 50km
  - `complementary`: from a hardcoded set of 11 cross-section pairs (food+housing_land, food+cooperatives, food+ecology, housing_land+cooperatives, housing_land+democracy, healthcare+education, healthcare+conflict, energy_digital+cooperatives, energy_digital+democracy, education+democracy, ecology+food).
- Edge weight: `1.0 - (distance / 50)`, floored at 0.1.
- Edge file already includes `edge_type, confidence, explanation, created_at, source_script`. **Not present:** `evidence` array, edge `id`, source/target as ids (currently coords), and the brief's wider taxonomy of edge types (verified_relationship, federation_membership, attestation, shared_resource, user_need_match).
- Builds country and US-state aggregates with a "completeness" score: `section_coverage * (0.5 + 0.5 * quality_ratio) * 100`. Already wired through to the map UI's framework dots, partially.

What `data/build_map_points.py` does today:

- Older, superseded. Outputs `map_points.json` (4.6MB, 23,779 points) and `map_meta.json`. **Still on disk and still updated by something** (timestamps on `map_meta.json` are recent). No tier field, no edges, no aggregates. Recommendation later: retire it once the v3 pipeline takes over.

### 1.2 The count drift

This is the headline mess. Five different "truths" coexist.

| Source | Org count | Country count | Edge count | Reading |
|---|---|---|---|---|
| `index.html` hero stat | **27.3K** | **172** | not shown | Marketing copy. Hardcoded in HTML. |
| `index.html` meta description | 27,300+ | 172 | not shown | Hardcoded. Used by search engines and social cards. |
| `index.html` map iframe footer | 27,300 | 172 | not shown | Hardcoded. |
| `index.html` section cards (sum) | **27,330** | not shown | not shown | Sum of 10 hardcoded section counts: 6,460 + 5,835 + 2,975 + 4,299 + 2,674 + 2,370 + 912 + 1,335 + 350 + 70. |
| `README.md` honest section | **26,022 candidates** | **61** | **2,687** | Updated 2026-04-23. Calls out the drift explicitly. |
| `README.md` further breakdown | 11,991 geocoded; 15,854 Tier B+; 10,032 Tier D; 136 untiered | 61 | 2,687 | Same source. |
| `DATA.md` honest numbers | **24,508** post-trim | not shown | not shown | "Smaller than the 26,022 candidate count" because of subsequent trim. |
| `data/search/map_meta.json` | **23,779** total | top 30 listed | not shown | Output of `build_map_points.py` (legacy). |
| `data/search/map_points_v2.json` | **~12,478** Tier A/B/C | implicit | not shown | Output of `build_map_v2.py`. What the live map actually loads. |
| `data/search/map_aggregates.json` | `total_points: 12,478`; `total_edges: 2,687` | counts in `countries` dict | 2,687 | Same source as map. |

So the public-facing "27,300 orgs / 172 countries" is **roughly 2x** what is in the database after trimming, and the map shows even less than that (12K points, because Tier D is excluded). The "172 countries" claim is the most misleading; the actual non-empty country count from `map_meta.json` is closer to 60-70 and from `aggregates.json`'s `countries` dict probably similar.

The 27.3K figure looks like it traces back to an older "post-filter, pre-trim" candidate count that has since been further reduced by audit passes. No one updated the homepage when the trims happened.

### 1.3 Edge audit

Edges that exist today (~2,687):

- All are derived. **Zero verified relationships, zero federations, zero attestations.** The `verified_relationship`, `federation_membership`, `shared_resource`, and `attestation` types from the brief are unimplemented.
- Both extant edge types (`same_section`, `complementary` -> stored as `geographic_nearby`) are pure proximity-plus-section heuristics. The "explanation" string is generated from a template ("Both are in the X section and within Y km of each other"). It is honest about what it is, but it is also all the map currently has.
- **Provenance fields present:** `edge_type, confidence, explanation, created_at, source_script`.
- **Provenance fields missing:** `evidence` (the brief asks for a list of `{type, value}` pairs pointing at URLs, registries, or manual notes). Also missing: `id`, stable `source_id` and `target_id` (currently coordinate-keyed), and a `weight` distinct from `confidence` (the brief lists both; the script uses one number for both).

### 1.4 Things that look broken or close to it

- **`build_map_points.py` (legacy) still runs.** `map_meta.json` is updated by it on a recent timestamp but the file's `total: 23779` no longer matches anything else. Either retire it or make it a thin alias for the v2 output.
- **`map.html` reads `map_meta.json`?** Quick grep says no, only `map_points_v2.json` and `map_edges.json`. So the legacy file is dead weight on the live map. But the search/directory pages may use the per-country files in `data/search/<CC>.json`, which are produced by `build_search_index.py`. Worth confirming before deletion.
- **Country code default fallback** in `build_map_v2.py` is `'US'`. So an org with `country_code = NULL` becomes a US point. This is a small bias source.
- **Edge endpoint resolution by rounded coords** in `map.html` line 530: `coordKey(p.lo, p.la)` rounds to 4 decimals. If two orgs share rounded coords (city centroid geocode collisions are common), edges get attached to whichever index landed in the hash last. Counts of orphaned edges should be checked before Phase 2.
- **Index.html hardcoded section cards sum to 27,330** but `map_meta.json` says only 11,481 are actually in GB and 6,682 in US. The section totals shown publicly are not even the 10K-org subset that is geocoded. They look like they came from an early registry intake count.

---

## 2. Target architecture

The brief lays this out well; this section restates it briefly with a few concrete choices.

### 2.1 Data model: three files in `data/map/`

```
data/map/orgs.geojson      # FeatureCollection of org points and (optional) coverage polygons
data/map/edges.json        # Array of edge objects with id, source_id, target_id, type, confidence, evidence
data/map/regions.geojson   # FeatureCollection of country and region polygons with aggregate counts baked in
```

Plus three derived/sidecar files:

```
data/map/stats.json        # Single source of truth for ALL public counts (orgs, countries, sections, edges, by_tier, by_source, last_built)
data/map/schema.org.json   # JSON Schema for an org Feature
data/map/schema.edge.json  # JSON Schema for an edge
```

Org node: as in brief section 2. Stable string id (`org_<sqliteid>`), slug, primary section, secondary sections, description, website, contact (with `contact_url` always allowed even when email/phone are null), location (point + city + region + country + `geocode_precision`), coverage (scope + optional geometry + precision + radius), quality (tier + score + source + last_verified + verified_by), resources, offers, needs, privacy.

Edge: as in brief section 2. Stable id (`edge_<source>_<target>` or hash), source_id and target_id as strings, edge_type from the seven-type enum, confidence enum (high/medium/low) **and** numeric weight (the brief implies both; keep both), `derived: bool`, explanation, created_at, source_script, evidence array.

### 2.2 Edge types and scoring

Use the brief's seven types. Default visibility, in order:

1. `verified_relationship` - solid line, always visible on selection
2. `federation_membership` - solid line, always visible on selection or when federation overlay is on
3. `attestation` - solid line, visible when attestor or attestee is selected
4. `same_section_proximity` - dashed, visible only at high zoom or on selection
5. `cross_section_complementarity` - dashed, visible in Need Pathway mode and on selection
6. `shared_resource` - dotted, optional toggle
7. `user_need_match` - bright temporary highlight, only after a query

Derived edge score (from the brief):

```
edge_score =
   0.30 * section_similarity
 + 0.25 * geographic_proximity
 + 0.20 * complementary_function
 + 0.15 * data_quality
 + 0.10 * shared_resources_or_keywords
```

Suppress edges below 0.55 unless user toggles "show weak/inferred links."

### 2.3 Four modes

| Mode | What it answers | Layers on |
|---|---|---|
| Geographic | Who is where? | Points, coverage polygons, density hexbins at low zoom |
| Network | Who is connected? | Force-directed network of selected subset, no basemap |
| Need Pathway | Who should I talk to for X? | Points filtered + ranked + `user_need_match` edges |
| System Health | What is missing here? | Region polygons coloured by completeness, gap callouts |

The current `map.html` already has Network and Geo modes. They need to be re-grounded on the new data model and stack.

---

## 3. Stack decision

**Confirm the brief's stack: MapLibre GL JS + deck.gl + Turf.js + PMTiles, with D3 force kept for Network mode only.**

Why I am not pushing back:

- **MapLibre GL JS** is genuinely free, vector-tile native, and has built-in clustering and feature-state. It does not require a paid token. Pairs with **OpenFreeMap** (free hosted vector tiles) or **Protomaps** + a self-hosted PMTiles file (also free, single static file, fits GitHub Pages perfectly). Either one keeps the static-first constraint intact.
- **deck.gl** at 12K points is overkill but cheap to add. It buys ScatterplotLayer (GPU-accelerated dot rendering at zoom transitions), ArcLayer (great for federation arcs), and HeatmapLayer/HexagonLayer (System Health overlays) without rewriting the basemap. Loads as one CDN script.
- **Turf.js** is the right tool for buffers, hulls, viewport spatial joins, and section coverage calculations.
- **PMTiles** is the right format for region polygons. World countries fit in roughly 2-5MB as a single PMTiles file served from `/data/map/`, with HTTP range requests (which GitHub Pages supports). For ~12K points right now, a plain `orgs.geojson` works fine; revisit PMTiles for points only if/when the count crosses ~50K.

What I would not do yet:

- Do not move points to PMTiles in Phase 1. A 4.5MB GeoJSON parses fast enough; the bottleneck on slow phones is render, not parse. Defer to Phase 5.
- Do not adopt Supercluster yet. MapLibre's built-in cluster is good enough for MVP.

What I would push back on, mildly:

- The existing D3 + topojson code in `map.html` is non-trivial and, in places, well-tuned (the force simulation cluster centres, the coordinate hash, the dash animation on edges). Phase 1 should make the *current* D3 map honest before rewriting onto MapLibre. The MapLibre rewrite belongs in Phase 2 alongside the new edge layer. This avoids a four-week dead patch where neither map works.

---

## 4. File-by-file plan

For each file the brief proposes, I note the existing equivalent, what changes, and a complexity tag (S = a few hours, M = a day, L = a few days, XL = a week+).

### 4.1 Frontend

| File | Existing equivalent | What changes | Complexity |
|---|---|---|---|
| `/map.html` | `/map.html` (60KB monolith) | Strip inline CSS to `assets/css/map.css`. Strip JS to `assets/js/map/*.js` modules. Switch basemap to MapLibre GL JS. Keep D3 force for Network mode only. | L |
| `/assets/js/map/app.js` | none (everything is currently inline) | New entry point. Boots MapLibre, wires modes, registers state subscribers. | M |
| `/assets/js/map/layers.js` | none | deck.gl ScatterplotLayer for points, ArcLayer for federation/verified edges, LineLayer for inferred edges, HexagonLayer for density. | L |
| `/assets/js/map/state.js` | inline globals (`activeSection`, `activeTiers`, `selectedNode`) | Centralised store with subscribe/notify; reads/writes URL hash. | M |
| `/assets/js/map/search.js` | inline `searchTerm` filtering | Search box -> structured query parser -> filter+rank pipeline. Phase 3 work; stub in Phase 1. | M |
| `/assets/js/map/scoring.js` | none | Need-pathway scoring, viewport System Health calculation. Phase 3-4 work. | M |
| `/assets/js/map/detail-panel.js` | inline detail panel renderer | Component module. Adds "share link" copy, "suggest correction" GitHub issue link, edge explanations. | M |
| `/assets/css/map.css` | inline `<style>` in `map.html` | Extract; add tier legend, mobile bottom-sheet. | S |

### 4.2 Backend / data pipeline

| File | Existing equivalent | What changes | Complexity |
|---|---|---|---|
| `/data/build_map.py` | `build_map_v2.py` (385 lines) | Rename and rewrite. Outputs `data/map/orgs.geojson` and `data/map/stats.json`. New schema fields: stable ids, slug, secondary_sections, contact, coverage, privacy, quality block. Tier assignment kept. | L |
| `/data/build_edges.py` | edge logic in `build_map_v2.py` (lines 143-236) | Split into its own script. Add edge types beyond proximity: federation_membership (from a curated YAML of federations), attestation (placeholder until trust layer lands), verified_relationship (from manual `data/relationships.csv` if any). Add `evidence` array. Add edge `id`, source_id/target_id as stable strings. | L |
| `/data/build_regions.py` | partial: country + state aggregates inside `build_map_v2.py` | New script. Joins per-country aggregates onto Natural Earth country polygons; outputs `data/map/regions.geojson` with completeness baked in. | M |
| `/data/validate_map_data.py` | none | New script. Asserts schema conformance, count parity between `stats.json` and the GeoJSON files, and that every edge endpoint resolves. Run in CI on every commit that touches `data/map/`. | M |
| `/data/map/orgs.geojson` | `data/search/map_points_v2.json` (compact JSON) | Net-new format. ~5-7MB once descriptions and contacts are inlined. | (data) |
| `/data/map/edges.json` | `data/search/map_edges.json` | Net-new schema. Likely ~150-300KB once explanations and evidence are inlined for ~2.7K edges. | (data) |
| `/data/map/regions.geojson` | none | Net-new. Country polygons (Natural Earth 1:50m) plus an `aggregates` property dict per feature. ~3-5MB. | (data) |
| `/data/map/stats.json` | partial: `map_aggregates.json` | The single source of truth for all public counts. Homepage, README, map, directory all read from here. | S |
| `/data/map/schema.org.json` | none | JSON Schema. ~150 lines. | S |
| `/data/map/schema.edge.json` | none | JSON Schema. ~80 lines. | S |

### 4.3 Files to retire or alias once v3 ships

- `data/build_map_points.py` -> retire after Phase 1.
- `data/search/map_points.json` -> delete after Phase 1.
- `data/search/map_meta.json` -> regenerate as a thin alias of `data/map/stats.json` for back-compat, then deprecate.

---

## 5. Phase 1 detailed task list: "Make the current map honest"

This phase keeps the existing D3 stack. It fixes the lies, adds the legend, adds URL state, adds the missing edge provenance fields, and makes the public counts match reality. No MapLibre rewrite yet.

Acceptance test (from brief): a visitor can open the map, filter to Tier A/B, click one org, see where the data came from, and copy a link to that exact view.

Tasks:

- [ ] **1.1 Single source of truth for counts.** Modify `data/build_map_v2.py` to also write `data/map/stats.json` containing: `orgs_total_db`, `orgs_in_directory` (post-trim, `status='active'`), `orgs_on_map` (Tier A/B/C with coords), `countries_with_at_least_one_org`, `countries_with_geocoded_org`, `by_tier` dict, `by_section` dict, `by_country` dict, `edges_total`, `edges_by_type` dict, `last_built` ISO timestamp. Run it. Record numbers.
- [ ] **1.2 Reconcile homepage.** Edit `index.html` to replace all hardcoded "27.3K", "27,300+", "172 countries", and the per-section counts with values pulled from `data/map/stats.json` at build time. If a build-time templater is too much for Phase 1, replace them with values fetched at page-load via `fetch('data/map/stats.json')`. Update meta description and og:description too.
- [ ] **1.3 Reconcile README.** Add a small Python script `data/check_counts.py` that reads `data/map/stats.json` and verifies the README's headline numbers match. Run it as part of the build. Failing to match should print a warning, not abort.
- [ ] **1.4 Tier legend.** Add a visible legend block in the sidebar of `map.html` explaining: "A Curated (manually verified). B Verified (from registry, has description and website). C Inferred (passed scoring, not yet reviewed). D Unverified (not shown on map by default)." Show counts next to each tier, pulled from `stats.json`. Reconcile the in-code TIER_LABELS (`B: 'Verified'`) with the README (`B: 'Matched'`); pick one and use it everywhere.
- [ ] **1.5 URL-state filters.** In `map.html`, serialize `{section, tiers, country, search, selectedId, zoom}` to `location.hash` on every state change (debounced). On page load, read the hash and restore. Use `URLSearchParams` for the hash payload. Add a "Copy link" button on the detail panel that copies `location.href`.
- [ ] **1.6 Real detail panel.** Audit the existing detail panel renderer. Make sure it shows: name, primary and secondary sections, description, location (city + region + country), website, contact_url if present, source (the `src` field), tier badge with the legend tooltip, "Suggest correction" link that opens a prefilled GitHub issue (`https://github.com/simonlpaige/commonweave/issues/new?title=...&body=...`). Add a "Copy share link" button that uses 1.5.
- [ ] **1.7 High-confidence-only toggle.** Already half-done (default is A+B). Promote the toggle to a single, prominent "High confidence only" switch with a tooltip explaining what it does. When off, allow Tier C; when on, hide C.
- [ ] **1.8 Edge provenance fields.** In `data/build_map_v2.py`, add `id` (`edge_<a>_<b>` with sorted stable ids), `source_id`, `target_id` (use the org's sqlite id stringified, e.g. `org_12345`), and `evidence: []` (empty array for now; populated in Phase 2). Keep the existing `edge_type, confidence, explanation, created_at, source_script`. Add the brief's `weight` field as a separate numeric (currently aliased with `confidence`). Add `derived: true`. Document fields in `data/map/schema.edge.json` (a stub schema is fine for Phase 1).
- [ ] **1.9 Stable org ids on the wire.** Add an `id` field to `map_points_v2.json` so the URL can reference `selectedId=org_12345`. The current pipeline strips ids on export (line 348). Either stop stripping, or re-add a stable hashed id.
- [ ] **1.10 Visible "last updated" date.** Add a small footer in the map UI: "Data last built: 2026-04-25" pulled from `stats.json`. This makes the freshness honest and surfaces drift early.
- [ ] **1.11 Update DIRECTORY.md count.** Once `stats.json` exists, regenerate DIRECTORY.md's headline counts from it (the existing `export_directory.py` already runs in Stage 9; thread `stats.json` through).
- [ ] **1.12 Acceptance check.** Open the map. Toggle "High confidence only" on. Click a Tier A org. Confirm: tier badge, source, description, website, "Suggest correction" link, "Copy share link" button. Paste the link in a new tab. Confirm the same view loads with the same org selected.

Phase 1 is mostly fixes plus one new file (`stats.json`). No new map library. No new schema. No edge logic changes other than adding fields.

---

## 6. Phases 2-5 high-level task lists

### Phase 2: Mycelial edge layer

Acceptance: clicking an org shows no more than 25 most relevant connections, each with an explanation.

- Switch basemap to MapLibre GL JS with OpenFreeMap or Protomaps tiles.
- Add deck.gl overlay; render points as ScatterplotLayer, edges as LineLayer (proximity) and ArcLayer (federation).
- Build `data/build_edges.py`. Add `federation_membership` edges from a curated `data/federations.yaml` (e.g. ICA, US Federation of Worker Co-ops, Via Campesina, Habitat for Humanity affiliates).
- Add `verified_relationship` edges from `data/relationships.csv` (manual, starts with maybe 50-100 entries from web research).
- Implement the brief's score formula (`0.30 * section_similarity + ...`), suppress < 0.55.
- On selection, render no more than 25 edges, ranked by score. Show explanations on hover.
- Migrate Network mode to D3 force on the deck.gl + MapLibre canvas (deck.gl ScatterplotLayer with x,y from a force simulation, MapLibre map locked).

### Phase 3: User-defined need pathways

Acceptance: searching "housing co-ops near Kansas City that need volunteers" returns a ranked local web, not just keyword matches.

- Search box parser: extract location ("Kansas City"), section keywords ("housing co-ops"), needs ("volunteers"). Use a dictionary lookup against `data/taxonomy.yaml` plus a geocoder (Nominatim, rate-limited; or a precomputed city centroids file shipped statically).
- Need scoring: rank candidate orgs by combined section match + proximity + needs/offers overlap.
- Render the result: best matches, complementary nearby orgs, suggested bridge orgs, listed gaps.
- Add `user_need_match` edges as a transient layer.

### Phase 4: Coverage and System Health

Acceptance: zooming into a region tells the user what kinds of transition infrastructure exist there and what is missing.

- Add `coverage` block to org records; backfill from coordinates plus declared scope.
- Render coverage polygons as transparent fills.
- Compute viewport-level System Health on every moveend: section counts, missing sections, verified ratio, suggested bridges.
- Render a System Health bottom bar that updates with the viewport.

### Phase 5: Performance hardening

Acceptance: map loads under 3 seconds on midrange phone with all public orgs.

- Move regions to PMTiles (single binary file, range requests).
- Move points to PMTiles only if the dataset doubles. At 12K, GeoJSON works fine.
- Lazy-load edges: only fetch the edges relevant to the visible viewport or the selected org.
- Precompute hex-bin clusters for low-zoom System Health choropleth.
- Mobile: full-screen map, bottom sheet for filters and details, larger tap targets.

---

## 7. Risks and unknowns

- **Privacy.** The org schema already includes `privacy: { show_contact, risk_context }`. The pipeline does not yet write these fields. For Tier A/B orgs in repressive contexts (anti-eviction networks, Indigenous land defenders, sex worker collectives) the precise lat/lon is a liability. Phase 1 should add a column to the database (`risk_context`, defaulting to `'normal'`) and a CLI flag to mark a row sensitive. Sensitive rows: jitter location, hide exact coords, region-only on the map. Without this, the v3 map is a more visible target than v2.
- **Mobile performance on big GeoJSON.** 4.5MB JSON parses in ~200ms on a fast laptop, ~1-2s on a midrange phone. Acceptable for now. If `orgs.geojson` grows past 8MB or the count crosses 30K, switch to PMTiles or chunked-by-bbox loading earlier than Phase 5.
- **Edge spaghetti.** At ~12K points and ~2.7K edges, drawing every edge at world zoom is unreadable. The default rule from the brief ("only edges connected to selected node, selected cluster, or selected need") is correct. Phase 1 should not draw edges by default at world zoom; only at zoom 7+ or on selection.
- **Count reconciliation lag.** Once `stats.json` is the source of truth, the homepage's hardcoded numbers will drift again unless the build process rewrites `index.html` (or fetches at runtime). Pick one and stick with it. Recommend: runtime fetch in Phase 1 (zero risk to GitHub Pages), build-time substitution in Phase 2.
- **Tile hosting.** OpenFreeMap and Protomaps are free, but both are single-org dependencies. Mitigation: ship a fallback `style.json` with an OpenStreetMap raster basemap as a second stage, in case the primary vector tile host disappears. PMTiles for region polygons removes one of the two dependencies because that file lives in the repo.
- **Unverified edges dominate.** All ~2.7K current edges are derived. A user looking at "verified relationships" will see nothing in Phase 1. The legend must be honest about this. Phase 2's manual `relationships.csv` is the way out; budget ~4-8 hours to seed it from existing knowledge (Mondragon, Equal Exchange, ICA member co-ops, Habitat affiliates, ITUC unions).
- **Geocode collisions on rounded coords.** `coordKey` rounds to 4 decimals (~11m). Multiple orgs at the same city centroid collide. Edge attachment is correct only by accident in those cases. Switch to id-keyed edges in Phase 1 (task 1.8) to fix this.
- **Country count claim.** "172 countries" is almost certainly wrong; the database has ~60-70 countries with at least one entry. Worst-case headline. Fix in 1.2.

---

## 8. Open questions for Simon

1. **Public count target.** Should the homepage say "26K candidates / 12K mapped / 60+ countries" (honest) or "12K curated organisations / 60+ countries" (cleaner)? The first is more transparent; the second is what the map actually shows. My recommendation: lead with the second, link to the first.
2. **What counts as a "country"?** Currently `country_code` from registries. Should we count countries with at least one org, or countries with at least one Tier A/B org? Affects the headline number. Recommend: countries with at least one mapped (A/B/C) org.
3. **Relationships.csv seed.** Want me to seed a manual `data/relationships.csv` with maybe 100 verified relationships in Phase 2, or wait for community contributions? Manual seed is faster and gives the map something real to show; community seed is more sustainable.
4. **Risk context defaults.** What is the default `risk_context` for an unmarked org? `'unknown'` (treat as sensitive until verified safe) or `'normal'` (treat as public until marked sensitive)? Default-deny is safer; default-allow is what the current data supports.
5. **MapLibre tile provider.** OpenFreeMap, Protomaps demo, or self-host PMTiles for the basemap? Self-hosted PMTiles is the most resilient but adds ~50-100MB to the repo (or to a Releases attachment). My recommendation: OpenFreeMap for Phase 2 MVP, Protomaps PMTiles for Phase 5.
6. **Tier B label.** Code says "Verified," README says "Matched." Pick one. Recommend "Verified (from registry)" because it explains what the verification is.
7. **Scope of v3 launch.** Ship Phase 1 alone first (a week), or hold v3 until Phase 2 lands (three weeks)? My recommendation: ship Phase 1 alone. The honesty fix is independent of the network rebuild.
8. **Federations source.** Where is the canonical list of federations come from? Wikidata has many; the brief implies a curated YAML. Want me to extract from Wikidata in Phase 2 or curate by hand?

---

## 9. Estimated total effort

Rough hours of focused dev time. Add 30-50% for review, testing, and surprise.

| Phase | Best case | Likely | Worst case |
|---|---|---|---|
| Phase 1: Make the current map honest | 12 | **18** | 28 |
| Phase 2: Mycelial edge layer + MapLibre rewrite | 30 | **45** | 70 |
| Phase 3: Need pathways | 16 | **24** | 40 |
| Phase 4: Coverage and System Health | 16 | **24** | 36 |
| Phase 5: Performance hardening | 10 | **16** | 28 |
| **Total** | **84** | **127** | **202** |

Phase 1 is the smallest and the most disproportionately valuable. It buys honesty across the entire site for less than two days of work, and it can be merged independently. Recommend doing Phase 1 first and reviewing before Phase 2 starts.

---

*End of plan. Awaiting greenlight on Phase 1 and answers to section 8.*
