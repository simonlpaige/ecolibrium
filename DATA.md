# Commonweave Data: Sources, Schema, and Methodology

## Honest Numbers

As of late April 2026, after Wave A and Wave B of the new-wave ingest, the directory contains **173,106 aligned organizations**. Wave A added the three national-registry ingesters (Australia, Bulgaria, Brazil) that broke the 88% US/UK skew. Wave B layered on **9,115 thematic-network rows**: cooperative federations, mutual-aid neighborhood networks, intentional communities, transition initiatives, community land trusts, and the RIPESS solidarity-economy family. Every Wave B row is high-alignment by definition; the source itself is the alignment evidence.

### Where the numbers came from

1. We pulled raw records from a growing list of public registries (IRS BMF, UK Charity Commission, Wikidata, ACNC for Australia, Mapa das OSCs for Brazil, Wikidata-Bulgaria for Bulgarian NPOs) plus thematic sources for labor, land, and housing.
2. Pre-filters at each ingest step drop obvious non-fits before they hit the database. Mapa OSCs is the loudest example: about 672,000 active Brazilian OSCs exist, of which 226,000 are pure religious orgs and another 18,000 are pure professional/employer associations. Both groups are skipped at ingest. The remaining ~85,000 are kept on a combination of IPEA area flags (saude, educacao, etc.) plus the brief's CNAE prefix whitelist.
3. The audit and quality passes (`audit_pass1`, `audit_pass2`, `audit_pass3_ntee`, `audit_quality`) keep doing their job on top.
4. `phase2_filter.py` re-scores everything with a combined keyword + legal-form score axis. The legal-form axis (added 2026-04-25) is the methodological win Wave A was about: a Bulgarian or Brazilian row whose description is in the local language can still score high because its `model_type` and `registration_type` columns encode the legal form directly.
5. CSVs of every removed row are still preserved in `data/trim_audit/`.

### Current composition

| Source | Records | What You Get |
|--------|--------:|--------------|
| Mapa das OSCs (Brazil) | ~85,438 | CNPJ, IPEA area flags (saude, educacao, assistencia social, etc.), natureza juridica, CNAE primary, address, lat/lng. Filtered to skip pure-religion and pure-patronal rows; kept on IPEA-area or CNAE-prefix match. |
| ACNC Charity Register (Australia) | ~48,542 | ABN, charitable purpose flags, beneficiary flags, address, website, PBI/HPC tags. Pure-religious-only rows dropped. |
| UK Charity Commission | 11,396 | Name, registration ID, description available for many. |
| IRS Exempt Organizations BMF | 9,392 | Name, EIN, state, city, NTEE code, filing year, revenue. |
| Mutual Aid Wiki | 4,251 | Crowd-sourced UK-heavy mutual aid groups; CC BY-NC-SA. Pulled from the canonical groups.json on the Covid-Mutual-Aid GitHub repo (live API offline). Tagged informal. |
| Wikidata | 4,124 | Name, country, often website/description. |
| Wikidata Bulgaria NPOs | ~2,528 | Bulgarian Cyrillic names of nonprofits, associations, foundations, and chitalishte (community cultural centers). Wikidata-side fallback because the Registry Agency portal is SSO-gated. |
| Foundation for Intentional Community | ~1,098 | ic.org's full directory of intentional communities, ecovillages, and cohousing groups, parsed from /wp-json/v1/directory/entries/. Tagged hybrid. |
| Transition Network | 995 (+18 hubs) | Local Transition initiatives globally, pulled from the documented public REST API at maps.transitionnetwork.org/wp-json/cds/v1/. Licence ODbL; tagged hybrid. |
| Mutual Aid Hub | ~898 | US-focused crowd-curated mutual aid networks, pulled from Town Hall Project's public Firestore document collection. Licence PDDL-1.0; tagged informal. |
| SUSY Map | 887 | EU social and solidarity economy initiatives from the 2018 SUSY project, ingested as a frozen GeoJSON snapshot kept on the TransforMap viewer's gh-pages branch. Public Domain. |
| ProPublica Nonprofit Explorer | 602 | US nonprofits with descriptions and financials. |
| Wikidata (subregion) | 560 | Subnational Wikidata pulls. |
| Wikidata (land trusts) | 444 | Community land trusts (Q3278937) and housing cooperatives (Q562166); subclasses via P279*. |
| Schumacher CLT World Map | ~406 | Global community-land-trust directory; Toolset Views table walked across 44 paginated pages. Tagged formal. |
| Wikidata (labor unions) | 405 | Trade union federations, national unions, works councils (Q3395115, Q11038979, Q178790, Q1141395). |
| ICA member directory | 322 | International Cooperative Alliance member orgs, pulled as a flat CSV from data.digitalcommons.coop/ica/standard.csv (mirror of the lod.coop linked-open-data dataset). Tagged formal. |
| ITUC affiliates | 297 | ITUC-affiliated national trade union centers, parsed from the Wikipedia mirror when ituc-csi.org blocks automated requests. |
| New Economy Coalition members | 181 | US/Canada solidarity-economy orgs, parsed from the JavaScript variable on neweconomy.net/member-directory plus per-org og:description from each member profile. Tagged formal. |
| Construction coops | 81 | Worker-owned construction and trades firms. Wikidata plus seed list. |
| RIPESS family | 78 | RIPESS umbrella plus continental affiliates (apex seed) plus RIPESS EU/LAC/NA members from the socioeco.org GeoJSON mirror. RIPESS Africa (RAESS) and RIPESS Asia (ASEC) skipped: domains DNS-dead, outreach TODO logged. |
| Habitat affiliates | 66 | Habitat for Humanity international country offices; ~355 US affiliates enriched in place. |
| Web research | 58 | Hand-researched entries with full profiles. |
| Grounded Solutions | 38 | Curated seed list of US, UK, Canadian, and Belgian CLTs. |
| Manual curation | 13 | Individually verified and described entries. |

### Quality profile (after Wave A + Wave B)

- **173,106 entries** total active, up from 163,984.
- **Wave B added 9,115 rows** across 9 thematic global directories. Each row is mission-aligned at ingest by virtue of source membership.
- **Energy & Digital Commons** grew from 40 -> 123 (+83 net after phase2 re-classification). The bump is mostly Transition Network energy-coop tags and SUSY Map fablab/hackerspace entries.
- **Cooperatives & Solidarity** grew from 2,264 -> 2,802 (+538). ICA, RIPESS, and NEC members account for the bulk.
- **Legibility split**: 140,067 formal (Wave A's national registries plus the formal half of Wave B) + 5,149 informal (mutual aid networks) + 2,093 hybrid (Transition Network groups, IC Directory communities) + 25,797 unknown (older Wave A imports awaiting re-tag).

The earlier 24,508 number is preserved in the git history. We keep that history documented rather than silently deleting it.

### Wave B: thematic global directories (added 2026-04-26)

Wave B is "the membership *is* the alignment evidence" wave. Every row comes from a network whose entry criterion is mission, not country. So we tag rows by source legibility instead of trying to keyword-score them, and we trust the sources' own classifications.

The Wave B sources, by legibility tier:
- **Formal** (registered legal entity by definition): SUSY Map, NEC members, Schumacher CLT World Map, ICA member directory, RIPESS family.
- **Hybrid** (legibility varies by country and by individual group): Transition Network groups+hubs, IC Directory.
- **Informal** (mostly unincorporated neighborhood networks): Mutual Aid Wiki, Mutual Aid Hub.

Two Wave B sources were skipped on purpose:
- **Find.coop / Data Commons Cooperative**: outreach first, scrape later. The directory is a labour-of-love by a coop-of-coops; we ask before we take. TODO at `tools/mycelial-outreach/drafts/pending/findcoop-partnership-2026-04-26.md`.
- **RIPESS Africa (RAESS) and RIPESS Asia (ASEC)**: both raess.org and asec.coop fail DNS as of April 2026. TODO at `tools/mycelial-outreach/drafts/pending/ripess-africa-and-asia-2026-04-26.md` to chase through info@ripess.org.

### Wave A registry catalog

The `data/sources/REGISTRIES.yaml` file (added 2026-04-25) is the canonical "what we know about each country's drawer." It documents the 17 Wave A target countries plus ~10 other confirmed-reachable national portals from the new wave research. Each entry records the registrar, the URL, the languages the portal speaks, the entity classes in scope, whether bulk data is published, and the last-checked date. New ingesters should update the `last_checked` field when they run.

## Data Schema

The directory is stored in a SQLite database (`data/commonweave_directory.db`, ~230MB, gitignored).

### organizations table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | TEXT | Organization name |
| country_code | TEXT | ISO 3166-1 alpha-2 country code |
| country_name | TEXT | Human-readable country name |
| state_province | TEXT | State/province code (primarily US) |
| city | TEXT | City name |
| registration_id | TEXT | Official registration number (EIN, charity number, etc.) |
| registration_type | TEXT | Type of registration (IRS_EIN, UK_CHARITY, etc.) |
| description | TEXT | Organization description (often NULL for registry imports) |
| website | TEXT | Organization website URL |
| email | TEXT | Contact email |
| framework_area | TEXT | Mapped Commonweave framework section (see below) |
| ntee_code | TEXT | NTEE classification code (US nonprofits) |
| source | TEXT | Data source identifier |
| source_id | TEXT | ID in the source system |
| last_filing_year | INTEGER | Most recent tax filing year |
| annual_revenue | REAL | Annual revenue in USD |
| status | TEXT | Record status: active, removed, excluded_audit_p3 |
| date_added | TEXT | ISO timestamp when record was added |
| verified | INTEGER | 0 = unverified, 1 = verified |
| phone | TEXT | Contact phone |
| icnpo_code | TEXT | International Classification of Nonprofit Organizations code |
| employee_count | INTEGER | Number of employees |
| lat | REAL | Latitude (geocoded) |
| lon | REAL | Longitude (geocoded) |
| geo_source | TEXT | How coordinates were determined (city_exact, zip_centroid, etc.) |
| model_type | TEXT | Organization type (nonprofit, cooperative, government, etc.) |
| contact_url | TEXT | Contact page URL |
| tags | TEXT | Comma-separated tags |
| alignment_score | INTEGER | Framework alignment score (-3 to 5) |

### Framework Areas

Organizations are classified into one of 10 framework sections. Counts reflect the post-trim April 2026 snapshot:

| framework_area | Section Name | Count |
|----------------|-------------|-------|
| healthcare | Healthcare | 6,369 |
| education | Education | 5,694 |
| food | Food Sovereignty | 2,955 |
| democracy | Democratic Infrastructure | 2,863 |
| housing_land | Land & Housing | 2,406 |
| ecology | Ecological Restoration | 2,346 |
| conflict | Conflict Resolution | 910 |
| cooperatives | Cooperatives & Solidarity | 656 |
| recreation_arts | Recreation & Arts | 269 |
| energy_digital | Energy & Digital Commons | 40 |

**Classification method:** US nonprofits are mapped from NTEE codes to framework areas using a manually curated mapping table. Non-US organizations are classified using keyword matching on names and descriptions, or by ICNPO codes where available. This classification is approximate -- a motorcycle club categorized as "cooperatives" because it has NTEE code Y42 (fraternal organizations) is a known artifact of automated classification.

## Data Sources

### IRS Exempt Organizations Business Master File (BMF)
- **URL:** https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf
- **License:** US Government public domain
- **Coverage:** ~1.8M tax-exempt organizations in the US; we filter to active organizations and exclude obvious non-fits
- **Update frequency:** Monthly from IRS

### UK Charity Commission
- **URL:** https://register-of-charities.charitycommission.gov.uk/
- **License:** Open Government Licence v3.0
- **Coverage:** All registered charities in England and Wales

### Wikidata
- **URL:** https://www.wikidata.org/
- **License:** CC0
- **Coverage:** Structured data on organizations worldwide; quality varies significantly

### ProPublica Nonprofit Explorer
- **URL:** https://projects.propublica.org/nonprofits/
- **License:** Data is public (from IRS filings); enriched with descriptions
- **Coverage:** Major US nonprofits with detailed financials

### Web Research
- Organizations found through targeted web research for specific framework areas
- Each entry includes source URLs and research date
- These are the highest-quality entries in the directory

### Wikidata (labor unions) — source=`wikidata_unions`
- **Classes queried:** Q3395115 (trade union federation), Q11038979 (national trade union center), Q178790 (trade union, filtered to orgs with P17 country and P159 HQ set so locals are excluded), Q1141395 (works council).
- **Legibility:** `formal` on every row (Wikidata-notable = registered and documented).
- **Evidence:** Wikidata item URL stored on each row.
- **Script:** `data/ingest_unions.py` (supports `--dry-run`). Idempotent on `source_id` (the QID).

### ITUC affiliates — source=`ituc_affiliates`
- **Source order:** `https://www.ituc-csi.org/list-of-affiliated-organisations` (returns HTTP 403 to non-browser clients as of 2026-04-24), with documented fallback to Wikipedia's `International Trade Union Confederation` article.
- **Legibility:** `formal` on every row (federation-tier by ITUC definition).
- **Cache:** wikitext and HTML attempts cached at `data/sources/ituc-cache/`.
- **Script:** `data/ingest_ituc.py` (supports `--dry-run` and `--refresh`). Idempotent on Wikipedia article slug.

### Wikidata (land trusts and housing coops) — source=`wikidata_land_trusts`
- **Classes queried:** Q3278937 (community land trust), Q562166 (housing cooperative). Subclasses included via `wdt:P279*`.
- **Legibility:** `formal` on every row.
- **Evidence:** Wikidata item URL on each row.
- **Script:** `data/ingest_land_trusts.py` (supports `--dry-run` and `--limit`). Idempotent on QID.

### Grounded Solutions Network (and seed CLTs) — source=`grounded_solutions`
- **Source order:** `https://groundedsolutions.org/tools-for-success/resource-library/us-clt-directory` (HTTP 404 as of 2026-04-24, no Wayback snapshot). Fallback uses the WordPress REST API on the Member Profile and Member Spotlight categories, plus a curated seed list of 35 well-documented CLTs.
- **Legibility:** `formal` on every row.
- **Cache:** `data/sources/grounded-solutions-cache/`.
- **Script:** `data/ingest_grounded_solutions.py` (supports `--dry-run` and `--refresh`). Idempotent on WP post id or seed slug.

### Habitat for Humanity — source=`habitat_affiliates` (international) plus in-place enrichment of existing IRS rows
- **Source order:** `https://www.habitat.org/where-we-work` (HTML shell only; affiliate list is rendered client-side). The ingester therefore enriches the ~355 US Habitat rows already in IRS_EO_BMF and inserts a hand-maintained list of ~65 international Habitat country offices.
- **Legibility:** `formal` on every row.
- **Cache:** `data/sources/habitat-cache/`.
- **Script:** `data/ingest_habitat.py` (supports `--dry-run` and `--refresh`). Idempotent on `<cc>:<name-slug>` for country offices; existing IRS rows update in place on re-run.

### Construction cooperatives — source=`construction_coops`
- **Source order:** Wikidata SPARQL for cooperatives whose label contains a construction- or trades-specific token (construction, building, trades, Bau), plus a seed list of about 45 worker-owned construction firms from Mondragon, Italian cooperative federations, French SCOPs, and US/UK worker co-ops.
- **Legibility:** `formal` on every row.
- **Notes:** Rows land in `framework_area='cooperatives'` (not `housing_land`) because construction co-ops are fundamentally worker co-ops whose industry happens to be construction.
- **Script:** `data/ingest_construction_coops.py` (supports `--dry-run` and `--limit`). Idempotent on QID for Wikidata rows and on `seed:<slug>` for seed rows.

## How to Add Data

### Adding a single organization
1. Fork the repository
2. Add a row to the appropriate country search JSON in `data/search/`
3. Include at minimum: name, country_code, framework_area, and ideally description + website
4. Submit a pull request

### Bulk data sources
If you know of a public registry or dataset that could be imported:
1. Open an issue describing the data source, its license, and approximate size
2. Include a sample of what the data looks like
3. We'll build an import pipeline if the source is appropriate

### Verifying existing entries
The most valuable contribution is verifying that existing entries still have working websites, accurate descriptions, and correct framework classifications. Start with organizations that have `verified=0`.

## Known Issues

1. **Framework classification is still noisy** even after trimming. Auto-mapping NTEE codes to framework areas is approximate. We've removed the worst artifacts; some remain.
2. **Geographic coverage is heavily US/UK skewed.** 88% of entries are from US and UK registries. The remaining 58 countries hold 2,949 entries between them. This reflects what registries are publicly accessible, not where the work actually lives.
3. **Energy & Digital Commons has only 40 entries** despite thousands of community energy cooperatives existing globally. This section needs dedicated sourcing, not general-registry imports.
4. **Revenue data is US-centric** and comes from tax filings, which may be years old.
5. **The 2,805 strong-score entries are the defensible core.** The other 21,703 entries have framework alignment signal but would benefit from human review. Start there if you want to contribute.
