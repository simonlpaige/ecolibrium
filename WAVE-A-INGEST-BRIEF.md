# Brief: Wave A — Mission-First National Registry Ingest

You are Claude Code. This brief is the source of truth. Read it once, then execute.

## Mission

Add three new national-registry ingesters to the Commonweave directory, following the existing pipeline conventions. Each one targets a country whose national registry has an explicit nonprofit / charity / public-benefit entity class — meaning we can pull aligned orgs by **legal form**, not just keyword scoring on descriptions.

The three openers, in priority order:

1. **Australia — ACNC Charity Register** (highest yield, cleanest API)
2. **Bulgaria — Register of Non-profit Legal Entities (NPO Register)**
3. **Brazil — Mapa das OSCs (IPEA)** + a thin CNPJ enrichment pass

Goal: ~50,000–80,000 new aligned rows, all `legibility='formal'`, all geographically outside the existing US/UK skew.

## Why we're doing this

Today's directory is 88% US/UK because IRS BMF + UK Charity Commission + Wikidata are the only big drawers we've opened. The "new wave" research doc names ~30 confirmed-reachable national registries with native nonprofit/charity classes — most outside the Anglosphere. Wave A picks three high-yield, three-different-continents openers to confirm the pattern works before scaling.

Australia (~70K registered charities), Bulgaria (~20K NPOs), and Brazil (~1M+ OSCs, of which we'll tag the aligned ones) cover Oceania, Eastern Europe, and Latin America in one wave.

The bigger win is methodological: this is the first ingest where we're scoring on **legal form** rather than English-keyword presence. See "Field-family scorer" below.

## Hard rules

1. **Read `commonweave/NEW-WAVE-INGEST-PLAN.md` first.** It's the full strategic context. This brief is the execution layer.
2. **Follow the existing pipeline.** Model new scripts on `ingest_grounded_solutions.py` and `ingest_unions.py`. Same conventions: `--dry-run`, `--refresh`, cache to `data/sources/<source>-cache/`, log to `data/ingest-<source>-run.log`, idempotent on `source_id`.
3. **`legibility='formal'` on every row.** All three sources are official registries.
4. **No em dashes.** Feynman voice in all comments and docs.
5. **Surgical.** No drive-by refactors of the existing pipeline. If you find a bug, log it in a comment and keep going.
6. **Polite scraping.** Real User-Agent, 1–2s sleep between requests, cache aggressively, honor robots.txt.
7. **Dedup is the existing pipeline's job.** Just ingest idempotently (upsert by `source_id`). `dedup_merge.py` runs separately and requires location agreement before merging.
8. **No commits before Simon reviews.** Stage everything. Push only after a smoke test on `--dry-run` for each ingester.

## What to read first

- `commonweave/NEW-WAVE-INGEST-PLAN.md` — strategic context
- `commonweave/data/_common.py` — DB helpers
- `commonweave/data/ingest_grounded_solutions.py` — best template (caching, fallbacks, idempotent upserts)
- `commonweave/data/ingest_unions.py` and `ingest_ituc.py` — multi-source pattern
- `commonweave/data/ingest_wikidata_bulk.py` — SPARQL pattern (Bulgaria fallback may use this)
- `commonweave/data/taxonomy.yaml`
- `commonweave/PIPELINE.md` — the field guide; especially Stages 2–4 and 7
- `commonweave/data/phase2_filter.py` — the scorer; you'll extend it (see below)
- `commonweave/data/migrate_legibility.py`

## Work items

### 0. Pre-flight: `data/sources/REGISTRIES.yaml`

Transcribe the country atlas from `commonweave org finder new wave.md` (on Simon's desktop — ask Larry to paste the contents into the workspace if you can't reach the desktop) into a single YAML catalog. Schema per entry:

```yaml
- country_code: AU
  country_name: Australia
  registrar: Australian Charities and Not-for-profits Commission
  registry_name: ACNC Charity Register
  url: https://www.acnc.gov.au/charity
  bulk_data_url: https://data.gov.au/dataset/acnc/resource/...   # if known
  languages: [en]
  entity_classes_in_scope: [registered_charity, public_benevolent_institution, religious_charity_secular_arms]
  api: true
  bulk_csv: true
  auth_required: false
  update_frequency: monthly
  last_checked: 2026-04-25
  notes: National charity register; excellent CSV download; size ~70k rows.
  wave_a_target: true
```

If a country in the new wave doc is "authority-anchor only" (no confirmed public search portal), still include the row with `url: null` and `notes` describing the situation. This file becomes the canonical "what we know about each country's drawer."

Don't try to do all ~190 countries today. Do the **17 Wave A countries** named in `NEW-WAVE-INGEST-PLAN.md`, plus any of the ~30 confirmed-reachable countries the new wave doc explicitly verified. Mark `wave_a_target: true` on the three this brief covers; mark the rest with `wave_a_target: false` (Wave B/C will pick them up later).

### 1. `commonweave/data/ingest_acnc.py` — Australia ACNC Charity Register

**Source order:**
1. Bulk CSV from data.gov.au — the ACNC publishes a quarterly/monthly dump of the full register. URL pattern: search `https://data.gov.au/dataset/acnc` for the most recent "Register of Charities" CSV resource. Cache the CSV.
2. If the bulk file is unavailable, fall back to the ACNC public API: `https://acnc-public-api.azure-api.net/v1/...` (search ACNC developer docs).
3. If both fail, scrape the public search at `https://www.acnc.gov.au/charity` paginated. Last resort.

**Mapping:**
- `name`: Charity name
- `country_code`: `AU`
- `country_name`: Australia
- `state_province`: state if available
- `city`: town/suburb
- `registration_id`: ABN
- `registration_type`: `ACNC_REGISTRATION`
- `description`: Charity purpose + activity description (concatenate)
- `website`: charity website if listed
- `framework_area`: classify via existing keyword map (re-use `phase2_filter.py` keyword bank); fallback to `unknown` and let the second-pass classifier handle it
- `source`: `acnc_charity_register`
- `source_id`: ABN (Australian Business Number — unique)
- `legibility`: `formal`
- `model_type`: `nonprofit` default; promote to `cooperative` or `foundation` if name/text hints

**Filters at ingest time:**
- Skip charities marked as **revoked** or **deregistered** (status field)
- Skip pure religious-only charities with no secular activity (use the ACNC sub-type classification — keep "Public Benevolent Institution," "Health Promotion Charity," charity types serving advancement of education / health / social welfare; drop charities whose ONLY sub-type is "Advancement of religion" with no secondary classification)

**Expected row count:** ~50,000–60,000 after filtering.

**Flags:** `--dry-run`, `--refresh`, `--limit N`.

### 2. `commonweave/data/ingest_bulgaria_npo.py` — Bulgaria NPO Register

**Source order:**
1. Bulgarian Registry Agency — Register of Non-profit Legal Entities. URL: search `https://portal.registryagency.bg/` for the NPO public search. Bulk export availability uncertain — check first. Cache HTML/JSON aggressively.
2. Fallback: Wikidata SPARQL for `instance of (P31) wdt:Q163740` (nonprofit organization) AND `country (P17) wdt:Q219` (Bulgaria). Mark these rows with `source='wikidata_bg_npo'` (separate source so we know provenance).
3. Last resort: scrape the public list at the registry's web portal with proper pagination and language headers (`bg`).

**Language note:** Bulgarian (Cyrillic). Keep the Bulgarian name in `name`; if a Latin transliteration is available, store it in `name_translit` (add the column via `_common.ensure_column` if it doesn't exist; otherwise concatenate in parens at end of `name`). The multilingual term bank in `i18n_terms.py` already handles Bulgarian alignment scoring.

**Mapping:**
- `country_code`: `BG`
- `registration_type`: `BG_NPO_REGISTER`
- `source`: `bg_npo_register` (or `wikidata_bg_npo` for the fallback)
- `source_id`: EIK (single-ID code) if available; else slug

**Expected row count:** ~10,000–20,000 if the bulk pull works; ~1,000 if Wikidata fallback only.

**Flags:** same.

### 3. `commonweave/data/ingest_brazil_oscs.py` — Brazil Mapa das OSCs

**Source order:**
1. Mapa das OSCs (IPEA) public API. URL base: `https://mapaosc.ipea.gov.br/` — find their JSON API endpoint (likely `/api/...`). The platform has ~860,000 OSCs catalogued with Brazilian government CNAE classification.
2. If the API requires registration, fall back to bulk CSV (Mapa publishes annual datasets — check the open data section).
3. Last resort: query Receita Federal CNPJ public bulk data and filter by legal form code `3220` (Associação Privada) and `3999` (Outras Fundações). This is a multi-GB download — only do this if Mapa's API is unreachable.

**Critical filter:** Brazil's Mapa is broad. Pre-filter rows by **purpose / CNAE activity code** to keep only:
- Health and social services (CNAE 86, 87, 88)
- Education (CNAE 85)
- Environmental protection (CNAE 81.30, 39.00)
- Cooperatives (legal form code 2143 — Cooperativa)
- Cultural/civic associations (CNAE 94)
- Food sovereignty / agriculture co-ops (CNAE 01.13.0, 01.62, 03)

This prevents pulling 800K rows of religious associations and HOAs. Aim for **~30,000–60,000** aligned rows.

**Mapping:**
- `country_code`: `BR`
- `registration_id`: CNPJ
- `registration_type`: `BR_CNPJ`
- `source`: `mapa_oscs_brazil`
- `source_id`: CNPJ
- `description`: combine "razão social," "objeto social" (purpose clause), and CNAE description
- Language: Portuguese; multilingual term bank in `i18n_terms.py` handles `pt-BR` already.

**Flags:** same. Add `--cnae-filter` flag to override the default activity filter list.

### 4. Cross-cutting: extend `phase2_filter.py` with a legal-form score axis

Today the filter scores on description keywords. Add a second signal:

```python
LEGAL_FORM_BUMPS = {
    'cooperative': 3,
    'community_land_trust': 4,
    'community_company': 3,
    'non_profit_company': 3,
    'charitable_organization': 2,
    'association': 2,
    'foundation': 2,
    'social_enterprise': 3,
    'community_interest_company': 3,
    'section_8_company': 3,           # India
    'osc': 2,                          # Brazil
    'public_benevolent_institution': 3, # Australia
    'benefit_corporation': 2,
}
```

Apply by inspecting `model_type` and `registration_type` columns. The bump stacks with the existing keyword score, capped at `alignment_score=5`. This is what lets a Bulgarian or Brazilian row score high without an English description.

Run the re-score after all three ingesters land.

### 5. Run order + verification

1. `python data/ingest_acnc.py --dry-run` — confirm row count and field mapping
2. `python data/ingest_acnc.py` — real run
3. Same for Bulgaria, then Brazil
4. `python data/phase2_filter.py` — re-score with new legal-form bumps
5. `python data/check_counts.py` — confirm directory size and country distribution shifted
6. Update `commonweave/DATA.md` with the new sources, row counts, and updated "Honest Numbers" table

## Done criteria

- [ ] `data/sources/REGISTRIES.yaml` exists with at least the 17 Wave A countries documented
- [ ] All three ingesters run cleanly on `--dry-run` and real
- [ ] Each ingester is idempotent (re-running adds zero new rows)
- [ ] Each ingester has a cache dir under `data/sources/`
- [ ] Each ingester logs to `data/ingest-<source>-run.log`
- [ ] `phase2_filter.py` extended with legal-form score bumps
- [ ] `DATA.md` updated with new source entries and current row count
- [ ] US/UK percentage drops below 80% (was 88%)
- [ ] No regressions: `python data/check_counts.py` shows expected growth, no orphaned rows
- [ ] All commits in Feynman voice. One commit per ingester. No squashing.

## When you finish

Send a system event with the summary:
```
openclaw system event --text "Wave A ingest done: AU=<n>, BG=<n>, BR=<n>. Total directory: <n>. US/UK now <n>%." --mode now
```

If you hit a hard blocker (registry offline, API requires paid auth Simon hasn't approved, etc.), STOP and announce:
```
openclaw system event --text "Wave A blocked at <step>: <reason>. Need decision." --mode now
```

Don't guess. Ask.
