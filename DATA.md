# Ecolibrium Data: Sources, Schema, and Methodology

## Honest Numbers

As of April 2026, the directory contains **738,613 active records** across **99 countries**. Here's what that actually means:

| Source | Records | % of Total | What You Get |
|--------|---------|-----------|--------------|
| IRS Exempt Organizations BMF | 665,312 | 90.1% | Name, EIN, state, city, NTEE code, filing year, revenue. No descriptions, rarely websites. |
| UK Charity Commission | 40,619 | 5.5% | Name, registration ID, some descriptions. |
| Wikidata | 31,467 | 4.3% | Name, country, sometimes website/description. Scraped from structured data. |
| ProPublica Nonprofit Explorer | 741 | 0.1% | Enriched US nonprofits with descriptions and financials. |
| Web research | 456 | 0.06% | Hand-researched organizations with full profiles. |
| Manual curation | 18 | <0.01% | Individually verified and described entries. |

**What this means in practice:**
- **672,857 entries** (91%) have no description and no website -- they're just registry entries with a name and an ID
- **Only 13,798 entries** (1.9%) have been verified
- **144,032 entries** (19.5%) have a positive alignment score with the framework

This is not 738K "organizations mapped" in the sense that someone reviewed each one. It's 738K organizations *indexed* from public registries and auto-classified using NTEE codes and keyword matching. The project is transparent about this because honesty is more credible than inflated claims.

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

Organizations are classified into one of 12 framework sections:

| framework_area | Section Name | Count |
|----------------|-------------|-------|
| democracy | Democratic Infrastructure | 145,156 |
| education | Education | 194,978 |
| recreation_arts | Recreation & Arts | 117,202 |
| healthcare | Healthcare | 101,332 |
| ecology | Wellbeing Economics | 71,666 |
| cooperatives | Wealth & Cooperatives | 36,555 |
| housing_land | Land & Housing | 30,835 |
| food | Food Sovereignty | 20,499 |
| conflict | Conflict Resolution | 20,046 |
| energy_digital | Energy & Digital Commons | 247 |

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

1. **Framework classification is noisy.** Auto-mapping NTEE codes to framework areas produces many misclassifications. A cemetery is not a cooperative. We know.
2. **Geographic coverage is heavily US/UK skewed.** 96% of entries are from countries with English-language public registries.
3. **Energy & Digital Commons has only 247 entries** despite thousands of community energy cooperatives existing globally. This reflects data source limitations, not reality.
4. **"Allied Projects" and "Networks & Federations" have <20 entries each.** These categories need dedicated research, not registry imports.
5. **Revenue data is US-centric** and comes from tax filings, which may be years old.
