# Ecolibrium Data: Sources, Schema, and Methodology

## Honest Numbers

As of April 2026, the directory contains **24,508 aligned organizations** across **60 countries**. This number is the result of a multi-pass alignment filter applied to a much larger raw import; both numbers matter and we keep the history.

### Where the numbers came from

1. We pulled ~760,000 records from three public registries (IRS BMF, UK Charity Commission, Wikidata) plus smaller ProPublica and hand-curated sets.
2. Three audit passes removed obvious non-fits (alumni associations, cemeteries, homeowner associations, corporate retirement trusts, country clubs, etc.). That eliminated ~406,000 rows.
3. The remaining rows were scored against a keyword list of framework mechanisms (community land trust, worker cooperative, mutual aid, food sovereignty, restorative justice, community health, open source, and so on). Rows scoring below 2 were removed.
4. What remains: 24,508 rows with real framework signal. CSVs of every removed row are preserved in `data/trim_audit/` for transparency.

### Current composition

| Source | Records | % of Total | What You Get |
|--------|---------|-----------|--------------|
| UK Charity Commission | 11,537 | 47.1% | Name, registration ID, description available for many. |
| IRS Exempt Organizations BMF | 9,402 | 38.4% | Name, EIN, state, city, NTEE code, filing year, revenue. |
| Wikidata | 2,894 | 11.8% | Name, country, often website/description. |
| ProPublica Nonprofit Explorer | 604 | 2.5% | US nonprofits with descriptions and financials. |
| Web research | 58 | 0.2% | Hand-researched entries with full profiles. |
| Manual curation | 13 | 0.1% | Individually verified and described entries. |

### Quality profile

- **11,737 entries (48%)** have a real description (>50 characters)
- **10,262 entries (42%)** have a website on file
- **10,067 entries (41%)** are verified (Tier A or B in the map)
- **2,805 entries (11%)** score >=5 on framework alignment -- the strongest keyword matches
- **US + UK: 21,559 entries (88%)** -- heavy English-language registry skew, with the remaining 58 countries holding 2,949 entries between them. Closing this gap is the main enrichment target.

The earlier 738K figure counted every non-removed row including rows already flagged as excluded by prior audits. The 24,508 figure is what actually passed the full filter chain. We keep both histories documented rather than silently deleting them.

## Data Schema

The directory is stored in a SQLite database (`data/ecolibrium_directory.db`, ~230MB, gitignored).

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
| framework_area | TEXT | Mapped Ecolibrium framework section (see below) |
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
