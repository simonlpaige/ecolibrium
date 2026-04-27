# Commonweave UI Components

> Reference doc for the UI overhaul. Every component, its file, its CSS tokens, and its data dependencies. Keep this updated as the overhaul proceeds.

---

## Design System

### Color Tokens (`:root` in index.html and map.html)

| Token | Value | Role |
|-------|-------|------|
| `--bg` | `#0d1a0d` | Page background (deep forest) |
| `--surface` | `#132013` | Card / surface background |
| `--s2` | `#192819` | Elevated surface (nav hover) |
| `--s3` | `#1f321f` | Even more elevated |
| `--border` | `#253825` | Default border |
| `--border2` | `#30483a` | Brighter border |
| `--text` | `#cce8b0` | Primary text |
| `--muted` | `#5e8a52` | Muted / secondary text |
| `--dim` | `#3d5e35` | Dimmed text |
| `--accent` | `#78c87a` | Primary green accent (links, highlights) |
| `--a2` | `#56a85a` | Secondary accent |
| `--warm` | `#a8c87e` | Warm hover state |
| `--teal` | `#4fc4b0` | Focus rings, special highlights |
| `--earth` | `#c4a55d` | Earth tone accent |

**Map-only additions:** `--bg-deep`, `--bg-elevated`, `--border-bright`, `--text-primary`, `--text-dim`, `--text-muted`, `--accent-glow`, `--sidebar-w: 300px`

### Typography

- Font stack: system-ui / sans-serif
- Nav logo: lowercase, accent color, no underline
- Stat numbers: 34px, 800 weight, accent color, tight letter-spacing
- Section labels: 9-11px, uppercase, wide letter-spacing, muted

### Shared Patterns

- Focus outline: `2px solid var(--teal)` on interactive elements
- Skip link: `.skip-link` -- visually hidden until focused
- `role`, `aria-label`, `aria-live` on all dynamic regions

---

## Pages

### `index.html` -- Home / Landing

**Purpose:** Hero, live stats, embedded map iframe, framework sections grid.

**Layout (top to bottom):**
1. `<nav>` -- site nav with `.nav-logo` + `.nav-links` + `.nav-cta` (Directory button)
2. `<main id="main-content">` wrapping everything
3. `.hero` section -- heading, lead copy, CTA buttons (Explore Map / Browse Directory / GitHub)
4. `.stats` strip -- 6 stat tiles with `data-stat` attributes
5. `.methodology-wrap` -- two `.methodology-note` blocks (data explanation + multilingual pipeline)
6. `#map .map-wrap` -- embedded `map.html` in an iframe, plus `.map-footer` with live counts
7. `#sections .sections-wrap` -- 10 `.sec-card` tiles (one per framework section)
8. Framework doc text (long-form, inline)
9. Wave A/B ingest note

**Dynamic stat attributes (updated from `data/map/stats.json` on load):**

| `data-stat` key | Current value | Source field |
|-----------------|--------------|--------------|
| `orgs_in_directory` | 173,106 | `orgs_in_directory` |
| `orgs_on_map` | 33,364 | `orgs_on_map` |
| `countries_geocoded` | 102 | `countries_with_geocoded_org` |
| `countries_any` | 183 | `countries_with_at_least_one_org` |

**Section cards (`.sec-card`) -- 10 framework sections:**

| Section | `data-section` | Card color |
|---------|---------------|------------|
| Healthcare | `healthcare` | `#7ec88a` |
| Education | `education` | - |
| Food | `food` | - |
| Democracy | `democracy` | - |
| Housing/Land | `housing_land` | - |
| Ecology | `ecology` | - |
| Conflict | `conflict` | - |
| Cooperatives | `cooperatives` | - |
| Recreation/Arts | `recreation_arts` | - |
| Energy/Digital | `energy_digital` | - |

**Hardcoded fallback values** (HTML defaults before JS loads): Update these in index.html whenever stats change. `wiki-update.py` does NOT touch these -- they require a manual or scripted HTML edit. TODO: make them dynamic too.

---

### `directory.html` -- Full Directory Browser

**Purpose:** Search, filter, and browse all 173K orgs.

**Layout:**
1. `<nav>` -- same nav component as index.html (active state on "Directory")
2. PDF link row -- 2 PDF guides (pipeline explainer + labor-for-housing field guide)
3. `#stats-bar` -- 3 live stat tiles (`#stat-total`, `#stat-countries`, `#stat-loaded`)
4. `.search-row` -- `#search-input` + `#clear-btn`
5. `.filter-row` -- dropdowns: `#country-select`, `#state-select` (hidden unless US), `#ntee-select` (hidden unless relevant), `#sort-select`
6. `#content` -- main results area, dynamic. States: loading, error, featured grid, country grid, org card list

**Data source:** `data/search/index.json` (183 countries, 173,106 orgs, loaded on init), then per-country/state files from `data/search/<CC>.json` or `data/search/US_<ST>.json`

**Org card components:**
- `.org-card` (grid item): name (link), description, tags (`.tag.tag-source`)
- `.featured-card`: larger variant shown on homepage state
- `.country-card`: country selector buttons on the landing state

**Filter state machine:**
- Start: featured grid + country grid
- Country selected: load `<CC>.json`, show org list
- US selected: show state dropdown, load `US_<ST>.json`
- Search query: client-side filter on loaded set

---

### `map.html` -- Interactive Network Map

**Purpose:** D3 force-directed graph of geocoded orgs, embedded as iframe in index.html. Also accessible standalone.

**Layout:**
1. `#loading` overlay -- animated mycelium SVG (hyphae paths + spore circles), title, progress bar
2. `#layout` -- full-screen two-panel layout
   - `#sidebar` (300px, left) -- fixed panel
   - `#canvas-container` (fills remaining width) -- D3 canvas

**Sidebar sections (inside `#sidebar`):**
- `.sb-header` -- "COMMONWEAVE" title + "mapping the networks of change" subtitle
- `.sb-stats` -- live org/country counts
- `.sb-search` -- search input
- `#filters` -- section filter buttons (`.filter-btn`) with colored dot (`.filter-dot`) and active state (left accent bar in section color)
- `.sb-label` -- section group labels
- Legend / info panel (detail view when org is clicked)

**Map canvas (D3):**
- Nodes: dots per org, colored by `framework_area`, sized by some weight
- Edges: `data/map/map_edges.json` -- same-section proximity + cross-section complementarity (5,027 edges total)
- Node data: `data/map/map_points_v2.json`
- Aggregates: `data/map/map_aggregates.json`
- Stats: `data/map/stats.json`

**Loading animation:** SVG mycelium with `.hypha.hp` (primary), `.hypha.hs` (secondary), `.hypha.ht` (tertiary) paths + `.spore` circles. CSS-animated draw on `stroke-dasharray`.

**Standalone URL:** `/commonweave/map.html`

---

### `doc.html` -- Framework Document Reader

**Purpose:** Renders Markdown framework docs (README, RESEARCH, CRITIQUE, etc.) as styled HTML with a table of contents sidebar.

**Layout:**
1. Skip link
2. `<nav>` -- same site nav
3. `.breadcrumb` nav -- `#breadcrumb-current`
4. `.doc-layout` -- two-column
   - `<aside id="toc">` -- auto-generated TOC (`#toc-list`) from headings
   - `<main id="main-content">` -- `#loading` placeholder, `<article id="content">`, `#doc-nav` prev/next
5. `<footer>` -- site footer

**Data:** Fetches Markdown files, parses and renders client-side. File determined by URL query param or default.

---

## Data Files (Frontend-Facing)

| File | Size | Updated by | Used by |
|------|------|-----------|---------|
| `data/map/stats.json` | 2.6 KB | `build_map_v2.py` (via `wiki-update.py`) | index.html (JS), map.html |
| `data/map/map_points_v2.json` | ~5 MB | `build_map_v2.py` | map.html (D3) |
| `data/map/map_edges.json` | - | `build_map_v2.py` | map.html (D3) |
| `data/map/map_aggregates.json` | 78 KB | `build_map_v2.py` | map.html |
| `data/search/index.json` | ~35 MB | `build_search_index.py` | directory.html |
| `data/search/<CC>.json` | varies | `build_search_index.py` | directory.html (on demand) |
| `data/search/US_<ST>.json` | varies | `build_search_index.py` | directory.html (on demand) |

---

## Nav Component (shared across all pages)

```html
<nav role="navigation" aria-label="Site navigation">
  <a href="/commonweave/" class="nav-logo">commonweave</a>
  <div class="nav-links" role="list">
    <!-- links, class="active" on current page -->
    <a href="directory.html" class="nav-cta">Directory →</a>
  </div>
</nav>
```

Note: `index.html` uses relative href `/commonweave/`; `doc.html` uses same. Keep consistent during overhaul.

---

## Known Issues / Pre-Overhaul Tech Debt

1. **Hardcoded stat fallbacks in index.html** -- `data-stat` elements have hardcoded fallback values that go stale. JS overwrites them on load but not before paint. Options: SSG, server-side template, or accept flash-of-stale-content.
2. **Methodology note is factually stale** -- still says "we started with three registries." Now 25+. Needs prose update.
3. **`directory.html` nav links** use relative paths; `index.html` uses absolute-relative. Inconsistent -- pick one during overhaul.
4. **No shared CSS file** -- each page has its own `<style>` block. Design tokens are duplicated. Overhaul should extract to `commonweave.css`.
5. **map.html sidebar width** hardcoded at 300px, not responsive. Collapses on mobile (iframe is 340-540px tall on index.html).
6. **`doc.html` TOC** generated client-side from heading scan -- no anchor IDs in static HTML. Fine for now, but breaks deep-linking.
7. **`countries_any` stat** in index.html hero text still shows hardcoded `171` in one spot (the `<span data-stat="countries_any">` -- check JS updates this correctly).

---

## Overhaul Checklist (fill in as you go)

- [ ] Extract shared CSS design tokens to `commonweave.css`
- [ ] Make stat fallbacks data-driven (not hardcoded HTML)
- [ ] Update methodology note prose (25+ sources, not 3)
- [ ] Responsive map sidebar
- [ ] Nav consistency across pages
- [ ] Decide: dark-only or add light mode toggle
- [ ] Check `countries_any` stat renders correctly in hero
