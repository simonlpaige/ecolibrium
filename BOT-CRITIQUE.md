# Ecolibrium Bot Pipeline Critique (DeepSeek R1)

> Generated 2026-04-17. Focus: directory-building bots - relevance, false positives, false negatives, anti-greenwashing.
> Bundle fed to R1: VISION, BLUEPRINT, GOVERNANCE, DATA + bot pipeline code (taxonomy, filters, researchers, audit, wikidata).
> Prior CRITIQUE.md was summarized (section titles only) to avoid rehash.

---

## 1. What the bots are actually doing (R1's summary)

The pipeline operates as follows:

1. **Source ingestion**: Pulls from government registries (IRS BMF, UK Charity Commission), Wikidata, and ProPublica. Researchers (`researcher_HN.py`, `run_researcher_ng.py`) scrape web searches for specific countries.
2. **Taxonomy tagging**: Uses `taxonomy.yaml` and keyword matching to assign a `framework_area` from 10 categories. For US orgs, maps NTEE codes to framework areas; for others, uses keywords in names/descriptions.
3. **Alignment scoring**: `phase2_filter.py` scores orgs using three keyword lists: `STRONG_POS` (+3), `MODERATE_POS` (+1), and `NEGATIVE` (-3). Scores range -10 to 10. `alignment_score >= 2` passes.
4. **Audit/trim**: Three audit passes (`audit_pass1.py`-`audit_pass3_ntee.py`) exclude patterns (churches, clubs, HOAs), require ≥1 strong positive keyword, and filter US NTEE codes. `trim_to_aligned.py` deletes everything not `status='active' AND alignment_score >= 2`.
5. **Wikidata ingest**: `wikidata_ingest.py` queries Wikidata SPARQL for orgs by country/type, scores them with the same keyword system, inserts if `score >= 2`.
6. **Final directory**: ~24,500 orgs in SQLite, mapped to framework areas, heavy US/UK skew.

**Guesses required**: The exact mapping from NTEE to framework_area isn't shown in code—presumably a manual table. How `taxonomy.yaml` influences classification beyond keyword mapping is unclear. The `model_type` assignment in `phase2_filter.py` uses simple substring matching, but the logic for choosing "cooperative" vs "mutual_aid" isn't detailed.

## 2. Where the bots are WRONG or WEAK for relevance

### False positives (wrongly included):
- **Corporate "cooperatives"**: Any org with "co-op" in name gets +3 in `phase2_filter.py`, but many are corporate co-ops (e.g., "Farmers Cooperative Association" that's a fertilizer seller).
- **Charity ≠ alignment**: NTEE codes like E (healthcare) auto-include many conventional hospitals that don't practice community health or democratic governance.
- **Greenwashing**: Environmental keywords like "conservation" trigger +1, but many are top-down NGOs with no commons governance.
- **Faith-based social services**: Whitelisted in `audit_pass1.py` (e.g., "Catholic Charities"), but may violate principles on LGBTQ+ rights or reproductive justice.
- **Professional associations**: NTEE code S (community improvement) includes trade groups masquerading as community development.

### False negatives (wrongly excluded):
- **Indigenous governance models**: "ejidos", "waqf", "gotong-royong" not in keyword lists. `taxonomy.yaml` has "Indigenous Lands" but no keywords in scoring.
- **Informal mutual aid**: No web presence → not in registries. Researcher scripts only find web-searchable orgs.
- **Worker co-ops without "co-op"**: Use "collective", "employee-owned", "société coopérative".
- **Global South orgs with non-English descriptions**: Keyword lists are English-only. Spanish "solidaridad" or French "coopérative" may not match.
- **Digital commons projects**: Only 40 entries in "Energy & Digital Commons" because keywords like "open source" are buried in broader categories.

### Why:
- **Keyword-based**: `phase2_filter.py` uses substring matching, not semantics. "Community development" matches corporate developers.
- **NTEE bias**: US-centric, nonprofit-biased. Ignores cooperatives (which are often tax-exempt under different codes).
- **Wikidata gaps**: `wikidata_ingest.py` filters out sports clubs, but coverage in Global South is sparse.
- **Alignment definition**: Scoring measures keyword presence, not actual adherence to principles (e.g., democratic governance, common ownership).

## 3. Taxonomy / scoring improvements

### Replace keyword scoring with embeddings:
- **Change**: In `phase2_filter.py`, replace `score_org` with sentence-transformers (`all-MiniLM-L6-v2`) to compute cosine similarity between org description and principle definitions from VISION.md.
- **Why**: "Cooperative" in name ≠ worker ownership. Embeddings capture semantic similarity.
- **Implement**: For each principle, create an embedding; compute max similarity; threshold at 0.3.

### Add principle-specific evidence field:
- **Change**: Add `principle_evidence` JSON column. Require at least one quoted sentence from org's website/description supporting each claimed principle.
- **Why**: Forces explicit grounding. Greenwashers won't have quotes about democratic sovereignty.
- **Implement**: Use LLM extraction or pattern matching during researcher runs.

### Fix NTEE mappings:
- **Change**: In `audit_pass3_ntee.py`, NTEE code Y (mutual benefit) should be **excluded**, not kept. Y includes fraternal orders, not cooperatives.
- **Why**: Currently Y42 (fraternal orgs) sneaks in as "cooperatives".
- **Implement**: Remove 'Y' from `KEEP_NTEE`.

### Expand keyword lists with non-Western terms:
- **Change**: Add to `STRONG_POS` in `phase2_filter.py`: "ejido", "waqf", "gotong-royong", "minga", "solidaridad", "coopérative", "genossenschaft".
- **Why**: Captures non-Anglophone models.
- **Implement**: Add array `NON_WESTERN_TERMS` with +3 weight.

### Model type classification overhaul:
- **Change**: Replace `get_model_type` with a rule-based classifier using multiple signals: legal structure (from registries), keywords, and revenue patterns.
- **Why**: "Foundation" currently catches anything with "foundation" in name, even if it's a community foundation.
- **Implement**: Use `registration_type` field (IRS_EO_BMF → nonprofit) plus keywords.

## 4. Source expansion for better recall

### Priority sources (from `GOV_DATA_SOURCES.md`):
- **India NGO Darpan**: ~700K NGOs via API. Needs registration but highest yield.
- **Brazil CNPJ**: ~900K nonprofits, filter by `natureza juridica`. CSV available.
- **France RNA**: 1.8M associations. Heavy filtering required but massive.
- **South Korea data.go.kr**: 100K nonprofits, free API key.
- **Poland KRS**: 100K associations, CSV.

### Regional aggregators missing:
- **International Cooperative Alliance (ICA) member directories**: 3M co-ops worldwide.
- **Fair Trade International registries**: Producer co-ops.
- **Open Source Initiative (OSI) members**: Digital commons.
- **Community Land Trust Network directories**: 300+ CLTs.
- **Rural Electric Cooperative directories**: 900+ US, plus international.

### Language/region gaps:
- **Arabic**: No sources for MENA except Turkey. Add `sharikat tʿāwunīya` (cooperative).
- **Francophone Africa**: No bulk data for Senegal, Côte d'Ivoire. Scrape national registries.
- **Chinese**: MCA registry scrapable but geo-blocked. Partner with China Foundation Center.

## 5. Anti-greenwashing / co-option detection

### Signals to detect:
- **Corporate funding disclosure**: If >20% revenue from fossil fuels/mining → flag.
- **Board composition**: Executives from extractive industries → demote.
- **Keyword contradiction**: "Sustainable" + "oil/gas/mining" in same description → reject.
- **Legal structure**: For-profit B-Corps claiming "cooperative" status → verify worker ownership.
- **Revenue concentration**: >80% from single government/corporate contract → possible front.
- **Website transparency**: No financials, no board names → lower score.

### Implement heuristics:
- Add `greenwashing_score` in `phase2_filter.py` based on above signals.
- Cross-reference with corporate watchdog databases (LittleSis, Corporate Europe Observatory).
- Check for membership in industry associations (e.g., "American Petroleum Institute").

## 6. Cheapest next experiments (squash mode)

1. **Hypothesis**: Adding non-Western cooperative terms will capture 100+ new aligned orgs in Latin America.
   - **Change**: Add "ejido", "cooperativa", "solidaridad" to `STRONG_POS` in `phase2_filter.py`.
   - **Test**: Run on existing Latin American data (Mexico, Brazil), count new orgs with score ≥2.

2. **Hypothesis**: Excluding NTEE Y (mutual benefit) removes 500+ false positives.
   - **Change**: Remove 'Y' from `KEEP_NTEE` in `audit_pass3_ntee.py`.
   - **Test**: Compare pre/post counts, manually verify 50 removed orgs are fraternal orders.

3. **Hypothesis**: Requiring a website reduces false positives by 30%.
   - **Change**: In `trim_to_aligned.py`, add `AND website IS NOT NULL` to keep condition.
   - **Test**: Sample 100 orgs without websites; how many are defunct/misclassified?

4. **Hypothesis**: Simple greenwashing rule catches corporate fronts.
   - **Change**: In `phase2_filter.py`, subtract 5 points if name contains "foundation" and description contains "corporation" or "inc".
   - **Test**: Manually check 20 orgs that drop below threshold.

## 7. One blind spot

**The pipeline assumes alignment is static.** Organizations evolve: co-ops get corporatized, nonprofits lose democratic governance, green orgs take dirty money. There's no mechanism to re-score orgs over time or detect mission drift. A greenwashing org could get in during a progressive phase, then pivot to extraction.

**High-leverage fix**: Implement a temporal scoring system that:
1. Rescores orgs quarterly using updated web data.
2. Flags significant drops in alignment score.
3. Uses Wayback Machine to track mission statement changes.
4. Incorporates user feedback (e.g., "this org now works with Monsanto").

The current pipeline is a one-time filter, not a living directory. The **decay problem** is the biggest unseen risk - the directory will become less relevant each year without continuous evaluation.
