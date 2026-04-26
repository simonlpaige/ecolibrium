# Wave B Known Issues

Tracked here so they don't block the Wave B push. Each item gets a Wave-D-priority TODO.

## 1. `state_province` regression: full-state-names alongside 2-letter codes

**Symptom:** `data/search/US_<full-name>.json` (e.g. `US_Alabama.json`, `US_New York.json`) appearing alongside the canonical `US_<XX>.json` files. The full-name files contain only ~5-15 orgs each (the new Wave B ingest rows). The 2-letter files still contain the legitimate IRS BMF + Wikidata rows.

**Root cause:** One or more Wave B ingesters (Mutual Aid Wiki, Mutual Aid Hub, IC Directory, CLT World Map, NEC, ICA, RIPESS, SUSY, Transition Network) write `state_province="Alabama"` instead of `state_province="AL"` for US rows. `build_search_index.py` then groups by whatever's in that column and emits a separate file per distinct value.

**Detected:** 2026-04-26 morning audit, immediately after Wave B landed.

**Impact:** Cosmetic on the public site (state filter UI may double-count or show duplicates). No DB integrity issue — every row still has the correct country_code. The duplicates are an artifact of the search-index build step, not the directory itself.

**Fix plan (Wave D priority 1):**
1. Audit the 9 Wave B ingesters for the line that writes `state_province`.
2. Add a `normalize_us_state(value)` helper to `data/sources/_common.py` (or wherever the shared utils live) that maps full names → 2-letter codes, and call it from every ingester before insert.
3. Run a one-shot DB migration: `UPDATE organizations SET state_province = <2-letter> WHERE country_code='US' AND length(state_province) > 2`.
4. Re-run `build_search_index.py`.
5. Delete the orphaned `data/search/US_<full-name>.json` files.

**Files to inspect first:**
- `data/ingest_mutual_aid_wiki.py`
- `data/ingest_mutual_aid_hub.py`
- `data/ingest_ic_directory.py`
- `data/ingest_clt_world_map.py`
- `data/ingest_new_economy_coalition.py`
- `data/ingest_ica_directory.py`
- `data/ingest_ripess_family.py`
- `data/ingest_susy_map.py`
- `data/ingest_transition_network.py`

## 2. Find.coop, RAESS, ASEC: skipped to outreach TODOs

Three Wave B targets weren't scrape-friendly (auth-walls or partnership-asks). They went to `tools/mycelial-outreach/drafts/pending/` instead. Track conversion when @alphaworm makes the asks. Wave D should not re-scrape these — wait for outreach outcomes.
