# Ecolibrium Map: Multi-Disciplinary Critique & Build Guide

**For the maintainer and designer of simonlpaige.com/ecolibrium**

Four perspectives. One goal: make the map the most useful artifact in the project.

---

## Part 1 — What Exists Now (Audit)

### Current State

The map at `/map.html` is a full-screen JavaScript application that renders organization dots on a world map. Based on the extracted content, it shows:

- A header bar with title "ECOLIBRIUM — mapping the networks of change"
- Four stat counters: Organizations, Countries, Visible, Networks
- A search box labeled "Networks"
- An "Explore Regions" prompt
- Interaction hint: "scroll to zoom · click clusters to expand · click orgs for details"
- The page is entirely JavaScript-rendered — fetching returns only the shell

The homepage's embedded mini-map describes: "Filter by section · hover any dot for details · scroll to zoom · drag to pan."

### What's Missing (the critique begins here)

The map currently does **none** of what the project claims to be about. The project's core metaphor is *mycelial* — a network of interconnected organizations forming a living web. But the map shows **dots on a surface**. No connections. No network edges. No relationships. No flows. It is a pin map, not a network map. That's the foundational problem everything else flows from.

---

## Part 2 — The Critique, By Expert

### 🎨 Web Designer — Interface & Experience

**First impression is a dead screen.** The map loads as a JavaScript app with no server-side rendering. Search engines, link previews, assistive technology, and slow connections all get an empty shell. For a project about transparency and openness, the primary visualization is invisible to most of the web.

**The stat counters are decoration, not information.** "739K+ Organizations" and "99 Countries" sit in the header bar but don't connect to anything interactive. They don't update as you filter. They don't link to the data. They're marketing numbers in an engineering project.

**The control vocabulary is confusing.** The UI shows a search box labeled "Networks" alongside a button labeled "Explore Regions" — but nowhere does it explain what a "network" means in this context versus a "section" (the framework's 12 categories) versus a "region." These three taxonomy axes compete for the user's attention without a clear hierarchy.

**There's no progressive disclosure.** A first-time visitor gets 739K dots at once with no guidance on what to look at first. There's no curated starting view, no "story" that walks you through the data, no featured organizations or highlighted patterns. The cognitive load is maximum from the first frame.

**Mobile is likely broken.** "Hover any dot for details" doesn't work on touch devices. If hover is the only mechanism for info discovery, the majority of web users (mobile) get a degraded experience.

**Specific UI failures:**
- No legend explaining what dot colors/sizes mean
- No visible filter controls on the map page itself (the homepage mentions "filter by section" but the map page doesn't surface this)
- No breadcrumbs or state indicators — the user doesn't know what they're currently viewing
- No way to share a specific map view (no URL state encoding)
- The "Explore Regions" button's behavior is unclear — is it a dropdown? A zoom action? A filter?


### 📊 Data Scientist — Data Integrity & Visualization Logic

**The 739K number is the elephant in the room.** The GitHub repo has a `data/` directory with YAML files. The directory page has filters for country, state, and category. But nowhere is it documented: where do 739,000 records come from? If this is aggregated from IRS 990 data, GuideStar, or similar bulk nonprofit databases, the methodology needs to be stated and the limitations acknowledged. Bulk nonprofit data is noisy — it includes defunct organizations, shell entities, and misclassified records. Claiming these as "mapped" organizations implies curation that may not exist.

**No visible data quality indicators.** When you click a dot, what do you see? Is there a confidence score? A "last verified" date? A data source attribution? Without these, the user has no way to distinguish a hand-curated entry from a bulk-imported row with a geocoded zip code centroid.

**The clustering algorithm is opaque.** "Click clusters to expand" implies some form of marker clustering (likely Leaflet.markercluster or Supercluster). But clustering 739K points naively hides the actual distribution. At world zoom, a cluster of 200,000 points in the US and a cluster of 50 points in Malawi look the same if the visual encoding is just a circle with a number. The clustering should communicate *density* and *composition* at every zoom level.

**No statistical aggregation views.** The map offers only one visual mode: dots. For 739K organizations across 12 framework sections, you need multiple aggregation levels:
- **Choropleth** (country/region level): organization density per capita, section coverage gaps
- **Hexbin/H3**: continuous density surfaces that don't follow arbitrary political boundaries
- **Proportional symbols**: aggregated by metro area or administrative region
- **Heatmap**: for seeing concentration patterns at continental scale

**The "12 sections" distribution is wildly uneven and this isn't surfaced.** From the homepage: Education has 195K organizations, Energy & Digital Commons has 246, Allied Projects has 10, Networks & Federations has 8. This 24,000x range means the map is dominated by a few categories. Without normalization or per-section views, the smaller sections are invisible noise.

**No temporal dimension.** When were these organizations founded? Are they active? The map is a static snapshot with no time slider, no indication of growth or decline, no way to see the movement's trajectory.


### 💰 Economist — What the Data Should *Mean*

**The map tells you where organizations *are* but not what they *do* to each other.** The entire framework is built on the idea that these organizations are parts of a larger system — the "mycelial network." But the map shows atoms, not molecules. An economist looking at this map wants to answer questions like:
- Where are the resource flows? (funding, knowledge, people)
- Which regions have coverage gaps in which framework sections?
- What's the relationship between organization density and outcome metrics (HDI, Gini coefficient, ecological footprint)?
- Are there clusters of complementary organizations (e.g., a food sovereignty org near a community land trust near an energy cooperative)?

**The framework's 12 sections are treated as flat categories, not as a system.** In reality, these sections have dependencies. Democratic infrastructure enables wealth redistribution, which enables healthcare, which enables education. The map should visualize these interdependencies — showing where the *system* is strong (multiple sections represented) versus where it's thin (only one type present).

**No economic metadata is surfaced.** The directory page has a "Sort: Revenue ↓" option, suggesting revenue data exists. But the map doesn't encode this. A $50B cooperative and a 3-person food garden collective appear as identical dots. Economic scale matters for understanding real-world impact versus aspiration.

**The map doesn't connect to the framework's "Phase 1 readiness" concept.** The README describes systems that "must exist before the transition." The map could powerfully show: for each geographic region, which Phase 1 systems exist and which are missing. That gap analysis is the map's highest-value use case, and it's completely absent.


### 🗺️ Cartographer — Spatial Design & Geographic Communication

**The basemap choice matters and isn't discussed.** A dark basemap (common in tech projects) emphasizes luminous dots but suppresses geographic context. For a project about place-based organizations, the user needs to see terrain, administrative boundaries, and population centers. A light, muted basemap with clear political boundaries would serve this data better.

**Projection is likely Web Mercator, which distorts the story.** Web Mercator inflates high-latitude landmasses, making the US, Europe, and Russia appear disproportionately large. For a project that explicitly values the Global South, this is a political and analytical problem. At minimum, the map should note this distortion. Ideally, continental views should use equal-area projections.

**There's no geographic hierarchy to the data.** 739K organizations can't all be shown at once — but the zoom transitions should communicate the hierarchy:
- **World view (zoom 0–3):** Continental patterns. Choropleth or proportional symbols by country. Network arcs between major hubs.
- **Continental view (zoom 4–6):** Sub-national patterns. Clusters resolve into metro-area aggregates. Section composition becomes visible per cluster.
- **Regional view (zoom 7–9):** Individual organizations begin to appear. Network connections between nearby organizations become visible.
- **Local view (zoom 10+):** Full detail. Individual pins with names, section colors, and connection lines to collaborators.

**No network lines exist.** This is the single biggest cartographic failure. The project's metaphor is a network — and networks require edges, not just nodes. Even if relationship data is incomplete, the framework's 12 sections define implicit connections: organizations in the same section within the same region are likely collaborators. Organizations in complementary sections (food + land + energy) within geographic proximity form potential system clusters. These can be drawn as proximity-based edges even without explicit partnership data.

**Scale bar and geographic context are probably absent.** Users need to orient themselves. A scale bar, a minimap inset showing the current viewport location, and clear labeling of major cities/countries at each zoom level are standard cartographic requirements.

**No inset maps for non-contiguous territories or dense areas.** If the data is US-heavy (likely, given IRS data availability), Alaska, Hawaii, Puerto Rico, and Pacific territories need inset treatment. Similarly, dense urban areas (NYC, London, Delhi) may need popup detail views.

---

## Part 3 — The Build Guide

### Architecture Decision: What to Build On

**Recommended stack:**

| Layer | Tool | Why |
|-------|------|-----|
| Map renderer | **MapLibre GL JS** | Open-source Mapbox fork. Free, no token required. Vector tiles. WebGL performance. |
| Large-scale points | **deck.gl** (ScatterplotLayer, HexagonLayer, ArcLayer) | GPU-accelerated. Handles 1M+ points. Composable layers. |
| Clustering | **Supercluster** | Fast point clustering with customizable aggregation. Returns cluster composition. |
| Network edges | **deck.gl ArcLayer + LineLayer** | GPU-rendered arcs between connected nodes. Supports color/width encoding. |
| Data format | **GeoJSON → FlatGeobuf or PMTiles** | Efficient binary format for large spatial datasets. Stream on demand. |
| UI framework | **Vanilla JS or lightweight (Preact/Svelte)** | Keep bundle small. Map is the app — the UI is filters and panels. |

**Do not use Leaflet for this.** Leaflet is DOM-based and chokes above ~50K markers even with clustering. At 739K, you need WebGL.


### Phase 1: Data Foundation (Week 1–2)

**Goal:** Clean data pipeline, documented schema, verifiable counts.

**1.1 — Audit and document the data.**

Create a `DATA-METHODOLOGY.md` in the repo that answers:
- What are the data sources? (IRS 990, GuideStar, NCCS, manual curation, other)
- How were organizations geocoded? (Address-level, zip centroid, city centroid, country centroid)
- What is the geocoding precision distribution? (What percentage are address-level vs. approximated?)
- How were organizations assigned to framework sections? (Keyword matching, NTEE codes, manual?)
- What is the false positive rate? (How many "organizations" are actually defunct, duplicates, or misclassified?)
- When was the data last refreshed?

**1.2 — Build a data quality tier system.**

Assign every record a confidence tier:

| Tier | Description | Visual treatment |
|------|-------------|-----------------|
| **A — Curated** | Hand-verified, active, confirmed section assignment | Full-opacity, full-size dot |
| **B — Matched** | Bulk-imported, algorithmically classified, geocoded to address | Medium opacity |
| **C — Inferred** | Bulk-imported, geocoded to zip/city centroid, section inferred from NTEE code | Low opacity, smaller |
| **D — Unverified** | Present in source data but not validated | Only visible when explicitly toggled on |

This lets you honestly say "739K organizations in our database, of which X are curated and Y are verified."

**1.3 — Design the data schema for network edges.**

Even without explicit partnership data, you can derive edges from:
- **Shared section + proximity** (organizations within 50km in the same section)
- **Shared section + same country** (national-level affinity)
- **Cross-section complementarity + proximity** (food + land + energy within a region = system cluster)
- **Explicit memberships** (if an org belongs to a federation in the "Networks & Federations" section, draw edges to members)
- **Shared funding sources** (if available from IRS data)

Schema for edges:
```
{
  "source_id": "org_123",
  "target_id": "org_456",
  "edge_type": "same_section_proximity" | "cross_section_complementarity" | "federation_membership" | "shared_funding",
  "weight": 0.0–1.0,
  "derived": true/false
}
```

**1.4 — Build a pre-processing pipeline.**

Write a script (Python or Node) that:
1. Reads raw data sources
2. Geocodes missing coordinates (batch geocoding with Nominatim or Pelias)
3. Assigns quality tiers
4. Generates derived edges
5. Outputs: `organizations.fgb` (FlatGeobuf), `edges.fgb`, `aggregates.json` (pre-computed country/region stats)
6. Outputs: a `data-stats.json` with verified counts per section, per country, per tier


### Phase 2: Map Rebuild — Multi-Scale Visualization (Week 2–4)

**Goal:** A map that communicates different things at different zoom levels, with network edges visible.

**2.1 — Implement the four-zoom-level design.**

| Zoom | What the user sees | Layers active | Key insight delivered |
|------|--------------------|---------------|---------------------|
| **0–3 (World)** | Choropleth by country: org density per capita. Proportional circles on capitals showing section breakdown (pie chart or stacked bar). Great-circle arcs connecting countries with shared federation memberships. | Choropleth, PropSymbol, ArcLayer | "Where is the movement strong? Where are the gaps?" |
| **4–6 (Continental)** | Hexbin aggregation (H3 resolution 3–4). Each hex colored by dominant section, sized by count. Inter-hex arcs for cross-section proximity edges. | HexagonLayer, ArcLayer | "What does the network fabric look like in this region?" |
| **7–9 (Regional)** | Clusters resolve into metro-level groups. Individual organizations start appearing (Tier A and B only). Section-colored dots. Proximity edges drawn as thin lines between nearby complementary orgs. | ScatterplotLayer (filtered), LineLayer | "What organizations are near me? What sections are they in?" |
| **10+ (Local)** | All organizations visible (with tier filtering). Full detail on click. Network connections from selected org drawn as highlighted arcs. | ScatterplotLayer (full), ArcLayer (interactive) | "Who is this organization? Who are they connected to?" |

**2.2 — Implement network edge rendering.**

Use deck.gl's `ArcLayer` for long-distance connections and `LineLayer` for proximity edges:

```javascript
// Proximity edges (same section, <50km)
new LineLayer({
  id: 'proximity-edges',
  data: proximityEdges,
  getSourcePosition: d => d.sourceCoords,
  getTargetPosition: d => d.targetCoords,
  getColor: d => sectionColors[d.section],
  getWidth: 1,
  opacity: 0.15,
  visible: zoom >= 7
})

// Federation arcs (long-distance memberships)
new ArcLayer({
  id: 'federation-arcs',
  data: federationEdges,
  getSourcePosition: d => d.sourceCoords,
  getTargetPosition: d => d.targetCoords,
  getSourceColor: [255, 200, 0, 80],
  getTargetColor: [255, 200, 0, 80],
  getWidth: 2,
  visible: zoom <= 6
})
```

**2.3 — Color system for the 12 framework sections.**

Design a 12-color palette that is:
- Colorblind-safe (test with Coblis or Viz Palette)
- Perceptually distinct at small sizes (dots must be distinguishable at 4–6px)
- Semantically meaningful where possible (green for ecology, blue for water/digital, etc.)

Suggested approach: use ColorBrewer's 12-class qualitative palette as a starting point, then adjust for your dark/light basemap.

Each section should have:
- A primary color (for dots)
- A lighter tint (for choropleth fills)
- A darker shade (for active/selected states)
- An icon (for legend and popups)

**2.4 — Basemap design.**

Use MapLibre GL JS with a custom style:
- Light, desaturated land in neutral warm gray
- Subtle country borders in medium gray, prominent at zoom 0–6, fading at higher zooms
- No distracting terrain or satellite imagery
- Ocean in a muted off-white or very light blue
- City labels appearing at zoom 5+, country labels always visible
- Dark mode toggle available but not default (light mode is better for data overlay legibility)

Consider using Protomaps or OpenMapTiles for self-hosted vector tiles to avoid dependency on commercial tile services.


### Phase 3: Interaction Design (Week 3–5)

**Goal:** Make it intuitive for a first-time visitor to extract value within 30 seconds.

**3.1 — First-visit guided experience.**

On first load, show a 3-step inline tour (not a modal — overlaid on the live map):

1. **"739K organizations across 12 areas of change."** (World view, all layers active, 3 seconds)
2. **"Zoom into any region to see the network."** (Auto-zoom to a visually interesting cluster — e.g., Western Europe or East Africa — showing hexbin + arc transitions, 3 seconds)
3. **"Click any organization to explore its connections."** (Auto-select a well-connected Tier A org, show its edges highlighted, 3 seconds)

Then dismiss and let the user explore. Persist a "Skip tour" preference.

**3.2 — Filter panel (left sidebar, collapsible).**

Sections:
- **Framework sections** (12 toggleable chips, color-coded, with counts)
- **Data quality** (Tier A/B/C/D toggle — default: A+B visible)
- **Edge types** (proximity / federation / cross-section — toggleable)
- **Country / region** (searchable dropdown or click-on-map)
- **Search** (by organization name — highlights and zooms)

Filter state should be encoded in the URL hash so views are shareable:
```
/map.html#sections=1,3,5&tier=A,B&zoom=7&lat=48.85&lng=2.35
```

**3.3 — Organization detail panel (right sidebar or bottom sheet on mobile).**

When a user clicks an organization:
- **Name** (linked to website if available)
- **Section** (color chip + label)
- **Location** (city, country)
- **Data tier** (A/B/C/D with explanation tooltip)
- **Revenue** (if available, formatted with scale indicator)
- **Description** (1–2 sentences)
- **Network connections** (list of connected orgs, grouped by edge type)
- **Data source** (where this record came from)
- **"Suggest correction"** (link to GitHub issue template)

On mobile, this should be a bottom sheet that slides up over the map, not a sidebar.

**3.4 — System health dashboard.**

Add a collapsible bottom bar or overlay panel that shows, for the current map viewport:
- Section coverage: a small 12-segment bar showing which sections are present and in what proportion
- Gap analysis: "This region has strong Education and Healthcare coverage but no Energy & Digital Commons organizations"
- Comparison: "Org density here is 3.2x the national average" or "0.4x the global median"

This transforms the map from "look at dots" to "understand systems."

**3.5 — Mobile-specific design.**

- Replace hover with tap
- Use a bottom sheet for org details (standard mobile pattern)
- Collapse the filter panel into a floating filter button
- Show section chips as horizontally scrollable pills at the top
- Ensure touch targets are minimum 44x44px
- Disable map rotation on mobile (confusing without a mouse)


### Phase 4: Performance at Scale (Week 4–6)

**Goal:** Smooth interaction with 739K points.

**4.1 — Data loading strategy.**

Do NOT load 739K points as a single GeoJSON on page load. Instead:

- **Level 0–6:** Load pre-computed country aggregates and federation arcs (~5KB JSON)
- **Level 7–9:** Load hex-aggregated tiles (PMTiles or vector tiles) for the viewport
- **Level 10+:** Load individual points for the viewport via spatial index query

Use FlatGeobuf with HTTP range requests for streaming only the data in the current viewport:
```javascript
import { deserialize } from 'flatgeobuf/lib/mjs/geojson.js'

async function loadViewport(bbox) {
  const iter = flatgeobuf.deserialize('data/organizations.fgb', bbox)
  const features = []
  for await (const feature of iter) {
    features.push(feature)
  }
  return features
}
```

**4.2 — Clustering with composition metadata.**

Use Supercluster with custom `map` and `reduce` functions to aggregate section composition:

```javascript
const index = new Supercluster({
  radius: 60,
  maxZoom: 12,
  map: (props) => ({
    sectionCounts: { [props.section]: 1 },
    totalRevenue: props.revenue || 0,
    maxTier: props.tier
  }),
  reduce: (accumulated, props) => {
    for (const [section, count] of Object.entries(props.sectionCounts)) {
      accumulated.sectionCounts[section] = (accumulated.sectionCounts[section] || 0) + count
    }
    accumulated.totalRevenue += props.totalRevenue
  }
})
```

This lets each cluster show its section composition as a mini pie chart, not just a number.

**4.3 — Web Workers for data processing.**

Move geocomputation off the main thread:
- Clustering calculations in a dedicated Worker
- Edge generation (proximity calculations) in a Worker
- Search indexing (Fuse.js or similar) in a Worker


### Phase 5: Network Intelligence (Week 5–8)

**Goal:** Move from "dots on a map" to "network intelligence."

**5.1 — Implement a "System Completeness" score per region.**

For each geographic unit (country, admin-1 region, or H3 hex):
- Count how many of the 12 framework sections are represented
- Weight by data quality tier (Tier A counts more)
- Weight by economic scale (revenue as proxy)
- Normalize to 0–100

Display as a choropleth overlay toggleable from the filter panel. This directly answers the framework's core question: "Where are the systems ready?"

**5.2 — Identify and highlight "system clusters."**

A system cluster is a geographic area where 4+ different framework sections have organizations within proximity. These are the "mycelial nodes" — places where the network is densest and most interdependent.

Run a spatial analysis:
1. For each Tier A/B organization, find all Tier A/B organizations within 50km
2. Count distinct sections represented in each neighborhood
3. Where section diversity ≥ 4, mark as a system cluster
4. Visualize these as highlighted regions on the map (convex hull or H3 hex fill)

**5.3 — "Explore connections from here" interaction.**

When a user clicks any point on the map (not just an organization), show:
- Nearest organizations by section
- System completeness score for the area
- Gaps: "No Conflict Resolution organizations within 100km"
- Suggested connections: "The nearest Energy cooperative is [name], 47km away in [city]"

**5.4 — Data export and embed.**

Let users:
- Export the current filtered view as GeoJSON or CSV
- Generate an embed `<iframe>` for a specific map view
- Share a permalink with full filter/zoom state

---

## Part 4 — Priority Triage

If you can only do five things, do these:

1. **Document the data methodology** (DATA-METHODOLOGY.md). This is non-negotiable. Until people know where 739K comes from, the map has a credibility problem.

2. **Implement the multi-zoom-level design** with pre-computed aggregates at low zoom. Country-level choropleth at world view, hex aggregation at continental view, individual dots at regional view. This alone transforms the experience.

3. **Add derived network edges** (same-section proximity). Even without explicit partnership data, showing connections between nearby organizations in the same framework section makes the "mycelial" metaphor visible for the first time.

4. **Build the section filter panel** with color-coded chips and URL state encoding. This makes the map useful for answering questions ("Where are the food sovereignty organizations in Southeast Asia?") instead of just browsing.

5. **Implement the "System Completeness" choropleth.** This is the map's killer feature — the thing no other platform shows. "Where is the movement complete?" is the question the framework exists to answer.

---

## Part 5 — What Not to Do

- **Don't add 3D extrusion.** It looks impressive in demos but makes spatial comparison harder and kills mobile performance.
- **Don't add a globe view.** Web Mercator has political problems but globe projections make interaction awkward and clustering impossible.
- **Don't gamify it.** No achievement badges, no "organizations discovered" counters. The data is serious; treat it that way.
- **Don't build a custom basemap.** Use MapLibre + an existing style (Positron, Protomaps Light) and customize colors. Basemap design is a 6-month project by itself.
- **Don't animate everything.** One transition animation (zoom level changes) is useful. Constant pulsing dots, floating particles, or animated arcs are distracting and burn battery.
- **Don't over-design the UI.** The map IS the UI. Filter panel, detail panel, and a legend. That's it. Every pixel of chrome is a pixel not showing data.

---

*This document is CC0. Use it, fork it, argue with it in a pull request.*
