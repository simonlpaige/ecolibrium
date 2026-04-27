# MAP-V3-BRIEF.md

Brief from Simon, 2026-04-25. The full prompt and design instructions for the new Commonweave map are pasted below. Your job in this pass is **research and planning only** — produce `MAP-V3-PLAN.md` in the repo root. Do NOT start implementation yet. Simon will review the plan and greenlight phases.

---

## What you should do in this pass

1. **Read the existing surface area first.** At minimum:
   - `map.html` (current map, ~60KB)
   - `MAP-BUILD-GUIDE.md` (the older guide; this brief supersedes parts of it but it has useful context)
   - `DATA.md` and `PIPELINE.md` (data model + pipeline)
   - `index.html` (homepage — counts shown there)
   - `README.md` (counts referenced here)
   - `data/build_map_v2.py` and `data/build_map_points.py` (current map data generation)
   - `data/search/map_points.json`, `map_points_v2.json`, `map_edges.json`, `map_meta.json`, `map_aggregates.json` (sample 50 lines each — they may be large)
   - `data/taxonomy.yaml` and `data/taxonomy-map.txt` (section names)

2. **Reconcile the count drift.** Public site says 27.3K orgs / 172 countries. README says 26,022 candidates / 11,991 geocoded / 2,687 edges. These should be one source of truth. Document the current numbers and the proposed reconciliation in your plan.

3. **Audit the current edge generation.** `data/build_map_v2.py` produces edges. Document:
   - What kinds of edges are currently created
   - What provenance metadata is missing (the brief calls out `edge_type`, `confidence`, `explanation`, `created_at`, `source_script`, `evidence`)
   - Whether the inferred edges currently dominate or whether real verified relationships exist

4. **Produce `MAP-V3-PLAN.md`** in the repo root with these sections:
   - **Current state audit** — what exists, what counts, what's broken, what's drifting
   - **Target architecture** — the data model, edge types, scoring, modes (Geographic / Network / Need Pathway / System Health)
   - **Stack decision** — confirm or push back on MapLibre + deck.gl + Turf + PMTiles. If you have a better suggestion for a static-first GitHub Pages-compatible site with ~12K geocoded points and growing, name it and justify.
   - **File-by-file plan** — for each new/modified file in the brief's section 12, note: existing equivalent if any, what changes, est. complexity (S/M/L/XL).
   - **Phase 1 detailed task list** — break Phase 1 ("Make the current map honest") into concrete checkboxes a coding agent can execute. Acceptance test included.
   - **Phase 2-5 high-level task lists** — less detail; just enough that someone can see the work.
   - **Risks and unknowns** — privacy (sensitive orgs), large-data perf on mobile, edge-spaghetti, count reconciliation, tile hosting.
   - **Open questions for Simon** — anything you can't decide without him.
   - **Estimated total effort** — rough ranges per phase in hours of focused dev time.

5. **Do not modify any other files.** Just write `MAP-V3-PLAN.md`. If you find something obviously broken (e.g. a script that crashes), note it in the plan but do not fix it in this pass.

6. **Keep it static-first.** No new backend services. No new paid map tokens. GitHub Pages must keep working.

7. **Voice.** Use Feynman "Curious Explainer" voice in the plan. Plain language. No AI marketing-speak. No em dashes.

---

## Original full brief from Simon (Sat 2026-04-25 21:29 CDT)

You want **an adaptive relationship map**, not a prettier pin map. Build it as a **multi-layer decision interface**: geography is the base, organizations are nodes, relationship logic creates edges, and user-defined needs decide which parts of the web appear.

Your public site says Commonweave is an open directory of roughly 27.3K aligned organizations across 172 countries, built from registry data and filtered through framework-alignment scoring. Your README currently says the repo has 26,022 candidate orgs, 11,991 geocoded map points, and 2,687 edges, with a known need to add edge provenance metadata. First task: **make the map pipeline the source of truth so the site, README, directory, and map always show the same counts.**

### Build instruction set for the Commonweave map

#### 1. Product definition

Build `/map.html` into four connected modes:

| Mode | Purpose | What it shows |
| ----------------- | ------------------------------------- | ----------------------------------------------------- |
| **Geographic** | "Who is where?" | Orgs, coverage areas, density, gaps |
| **Network** | "Who is connected?" | Mycelial edges between orgs |
| **Need Pathway** | "Who should I talk to for this goal?" | User-defined query → best orgs + useful relationships |
| **System Health** | "What is missing in this place?" | Coverage by framework section, gaps, weak spots |

Make the existing tier filters and guided views real, not decorative.

#### 2. Data model

Create three core files:

```
data/map/orgs.geojson
data/map/edges.json
data/map/regions.geojson
```

Each organization node should look like:

```json
{
  "id": "org_123",
  "name": "Example Cooperative",
  "slug": "example-cooperative",
  "section": "cooperatives_solidarity",
  "secondary_sections": ["land_housing", "food_sovereignty"],
  "description": "One or two sentence human-readable summary.",
  "website": "https://example.org",
  "contact": {
    "email": null,
    "phone": null,
    "contact_url": "https://example.org/contact"
  },
  "location": {
    "type": "Point",
    "coordinates": [-94.5786, 39.0997],
    "city": "Kansas City",
    "region": "Missouri",
    "country": "United States",
    "geocode_precision": "city_centroid"
  },
  "coverage": {
    "scope": "local|regional|national|global|unknown",
    "geometry": null,
    "coverage_precision": "declared|inferred|buffered|unknown",
    "service_radius_km": 50
  },
  "quality": {
    "tier": "A|B|C|D",
    "alignment_score": 7,
    "source": "manual|wikidata|irs|uk_charity|web_research",
    "last_verified": "2026-04-25",
    "verified_by": "script|human|unknown"
  },
  "resources": [
    {
      "label": "Toolkit",
      "url": "https://example.org/toolkit",
      "type": "guide|dataset|software|funding|training|other"
    }
  ],
  "offers": ["training", "mutual aid", "land stewardship"],
  "needs": ["funding", "volunteers", "legal support"],
  "privacy": {
    "show_contact": true,
    "risk_context": "normal|sensitive|repressive|unknown"
  }
}
```

Each edge should look like:

```json
{
  "id": "edge_123_456",
  "source_id": "org_123",
  "target_id": "org_456",
  "edge_type": "verified_relationship|federation_membership|same_section_proximity|cross_section_complementarity|shared_resource|attestation|user_need_match",
  "weight": 0.82,
  "confidence": "high|medium|low",
  "derived": true,
  "explanation": "Both are food sovereignty orgs within 50km and share agroecology/resource terms.",
  "created_at": "2026-04-25",
  "source_script": "data/build_edges.py",
  "evidence": [
    {
      "type": "url|registry|manual_note|wikidata|inference",
      "value": "https://example.org/partners"
    }
  ]
}
```

#### 3. Edge logic

Layered edges, not all-at-once:

| Edge type | Meaning | Visible by default? |
| ------------------------------- | --------------------------------------------------------------------- | ------------------------ |
| `verified_relationship` | Explicit collaboration, federation, partner page, manual confirmation | Yes |
| `federation_membership` | Org belongs to a known network/federation | Yes |
| `attestation` | Org vouches for another org | Yes, when available |
| `same_section_proximity` | Similar orgs near each other | Only when zoomed in |
| `cross_section_complementarity` | Different orgs that complete a local system | Yes in Need Pathway mode |
| `shared_resource` | Same toolkit, funder, platform, project, or dataset | Optional |
| `user_need_match` | Dynamically generated from user query | Only after query |

Derived edge scoring:

```
edge_score =
   0.30 * section_similarity
 + 0.25 * geographic_proximity
 + 0.20 * complementary_function
 + 0.15 * data_quality
 + 0.10 * shared_resources_or_keywords
```

Suppress below `0.55` unless user toggles "show weak/inferred links."

#### 4. User-defined needs model

Add a "What are you trying to do?" panel. User queries get represented as:

```json
{
  "goal": "find_collaborators",
  "location": {"lat": 39.0997, "lng": -94.5786, "radius_km": 250},
  "sections": ["land_housing", "food_sovereignty", "cooperatives_solidarity"],
  "needs": ["training", "legal support", "volunteers"],
  "offers": [],
  "quality_min": "B",
  "relationship_types": ["verified_relationship", "cross_section_complementarity"],
  "include_inferred": true
}
```

Output:
1. Best direct matches
2. Nearby complementary orgs
3. Existing verified relationships
4. Suggested bridge orgs
5. Gaps in the local system

#### 5. Visualization stack

| Layer | Tool |
| --------------------------- | -------------------------------------------------------------------------------- |
| Base map | MapLibre GL JS |
| Large point/edge rendering | deck.gl |
| Clustering | MapLibre clustering for MVP; Supercluster if you need custom cluster composition |
| Geographic analysis | Turf.js |
| Network-only layout | D3 force |
| Static hosting / no backend | GeoJSON first, PMTiles later |

#### 6. Zoom behavior

| Zoom | Display |
| ------------------- | ------------------------------------------------------------------- |
| 0–3 World | Country-level coverage, density, top hubs, missing-section warnings |
| 4–6 Continental | Hexbins / regional clusters, section composition, major arcs |
| 7–9 Regional | Clusters, top orgs, nearby complementary edges |
| 10+ Local | Individual orgs, contact/resources, selected-org relationship web |

#### 7. Geographic coverage

Every org needs **two spatial concepts**: headquarters point + coverage area.

| Known data | Geometry |
| ------------------------ | ---------------------------------------------------------------- |
| Exact service boundary | Use polygon |
| Multiple known locations | Use concave hull |
| Only point + radius | Use buffer |
| National org | Use country polygon |
| Global network | "global scope" badge + arcs, no giant polygon |

#### 8. Interface layout

Desktop: filters left, map center, detail right.
Mobile: top search, full-screen map, bottom sheet for filters/details.

#### 9. Detail panel requirements

When a user clicks an org: name, sections, description, location + coverage, website, contact, resources, quality tier + source, last_verified, known relationships, suggested complements, "suggest correction" GitHub issue link, "copy share link". Do NOT hide data quality.

#### 10. "System Health" overlay

For current viewport, calculate:

```json
{
  "viewport_org_count": 184,
  "sections_present": 7,
  "sections_missing": ["energy_digital_commons", "conflict_resolution"],
  "strongest_sections": ["education", "healthcare"],
  "weakest_sections": ["land_housing"],
  "verified_ratio": 0.42,
  "suggested_bridges": ["org_123", "org_789"]
}
```

#### 11. Visual rules

| Thing | Visual treatment |
| ------------------------ | ------------------------------------------------------- |
| Verified org | Solid dot |
| Inferred org | Smaller, translucent dot |
| Selected org | Larger dot + halo |
| Verified edge | Solid line |
| Inferred edge | Dashed / low-opacity line |
| User-generated need edge | Highlighted temporary line |
| Coverage area | Transparent polygon |
| Missing section | Warning badge, not red panic color |
| Sensitive org | Do not expose precise point; jitter or show region only |

Default rule:
```
Show all nodes appropriate to zoom.
Show only edges connected to selected node, selected cluster, selected need, or verified major network.
```

#### 12. Files to add or change

```
/map.html
/assets/js/map/app.js
/assets/js/map/layers.js
/assets/js/map/state.js
/assets/js/map/search.js
/assets/js/map/scoring.js
/assets/js/map/detail-panel.js
/assets/css/map.css

/data/build_map.py
/data/build_edges.py
/data/build_regions.py
/data/validate_map_data.py

/data/map/orgs.geojson
/data/map/edges.json
/data/map/regions.geojson
/data/map/stats.json
/data/map/schema.org.json
/data/map/schema.edge.json
```

Static-first. Python scripts generate data, GitHub Pages serves static files.

#### 13. Build phases

**Phase 1 — Make the current map honest**
- Sync counts across homepage, README, map, directory
- Add visible tier legend
- Add URL-state filters
- Add real detail panel
- Add "high-confidence only" toggle
- Add edge provenance fields

Acceptance: visitor can open the map, filter to Tier A/B, click one org, see where the data came from, and copy a link to that exact view.

**Phase 2 — Build the mycelial edge layer**
- Generate verified and inferred edges
- Show edges only on selection or need mode
- Add edge explanations
- Add edge confidence
- Add edge type filters

Acceptance: clicking an org shows no more than 25 most relevant connections, each with an explanation.

**Phase 3 — Add user-defined need pathways**
- Search box (natural-language-ish)
- Structured filters behind it
- Need scoring
- Best matches, bridge orgs, missing pieces

Acceptance: searching "housing co-ops near Kansas City that need volunteers" returns a ranked local web, not just keyword matches.

**Phase 4 — Add coverage and system health**
- Coverage polygons/radii
- Viewport section coverage
- Gap analysis
- Local system completeness score

Acceptance: zooming into a region tells the user what kinds of transition infrastructure exist there and what is missing.

**Phase 5 — Performance hardening**
- Move to PMTiles or tiled GeoJSON if load slow
- Lazy-load edges
- Precompute clusters/regions
- Mobile bottom sheet

Acceptance: map loads under 3 seconds on midrange phone with all public orgs.

### The core design principle

Commonweave should not say: "Here are 27,000 dots."

It should say: **"Tell me what you're trying to build, and I'll show you the nearest living network, the strongest bridges, and the missing pieces."**

---

## Output

Produce `MAP-V3-PLAN.md` only. No code changes in this pass.
