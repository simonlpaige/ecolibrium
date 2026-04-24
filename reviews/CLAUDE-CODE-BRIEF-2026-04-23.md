# Claude Code execution brief — Commonweave README review fixes
**Date:** 2026-04-23
**Spec doc:** `commonweave/reviews/README-review-2026-04-23.md`
**Author of this brief:** Larry (for Simon's approval)

## Your task
Execute all 9 priority fixes from the review doc. Work carefully, one fix per commit if the change is substantive, grouped commits if cosmetic. Stop and ask Simon before:
- deleting any existing file
- truncating Phase 1/2/3 content (move, don't cut)
- changing any number that doesn't match the DB verification table below

## Authoritative data (use these, not the numbers currently in README)
Verified against `data/commonweave_directory.db` on 2026-04-23 by Larry.
Filter: `WHERE merged_into IS NULL`.

| Metric | Current README says | Actual DB value | Use in rewrite |
|---|---|---|---|
| Total active orgs | 24,508 | **26,022** | 26,022 |
| Countries | 60 | **61** | 61 |
| Geocoded points | 8,412 | **11,991** | 11,991 |
| Alignment score ≥5 | 2,805 | **3,657** | 3,657 |
| US/UK skew | 88% | **82.8%** (21,559 of 26,022) | ~83% |

### Tier schema gotcha — IMPORTANT
README says "Tier A/B verified" but DB only has:
- `tier_b`: 15,854
- `tier_d`: 10,032
- null: 136

**There is no tier_a row in the database.** Do not write "Tier A/B verified" in the rewrite. Use:
- "15,854 are registry-backed (Tier B)" OR
- "15,854 pass alignment scoring with registry-backed metadata"

If you want "Tier A" to mean something, that's a data-model change, not a README change. Flag it in a `data/TODO-tier-a.md` note but don't invent numbers.

### Legibility column gotcha — IMPORTANT
All 26,022 orgs currently have `legibility='unknown'`. The column exists (shipped 2026-04-22) but has not been backfilled. So:
- **Do not** claim in the README that legibility data is visible today
- **Do** note the column exists and backfill is a known gap
- **Do** reference it in THREAT-MODEL.md as the countermeasure for pipeline bias (intended purpose, backfill pending)

## Priority order (from review doc)
1. **Promote "What does not exist yet" to top of README** (~5 min)
2. **Confidence-aware phrasing on headline number** (~10 min) — use verified numbers above
3. **Good-first-contribution tasks** (~30 min) — add `## Good first contributions` section to README with Data / Research / Code / Design subsections exactly as drafted in review doc §9, including Larry's "Directory verification (45 minutes)" addition
4. **Shorten README into entry point** (2–3 hrs) — move Phase 1/2/3 detail to BLUEPRINT.md if not already duplicated there (check first). Preserve critique-first link at top. Preserve Mycelial Strategy failure-modes subsection (it's load-bearing). Keep README under ~2,000 words.
5. **Resource governance matrix** (2–4 hrs) — add table per review doc §2, **including the 5th column for real-world examples from the directory** (Larry's addition). For the examples column, pick orgs from DB with `alignment_score >= 5` in the matching framework area. If you can't find a good real example for a cell, write `[NEEDS EXAMPLE]` — do not invent.
6. **Map confidence defaults + edge types** (1 day) — modify `data/build_map_v2.py` to emit edges with schema per review doc (edge_type, confidence, explanation, created_at, source_script). Update `map.html` to default to "high-confidence only" view (alignment_score >= 5) and hide edges by default. Add narrative presets per review doc map problem 3. Keep the "Start with the skeptic view" preset (Larry's addition).
7. **Issue-linked open questions** (2 hrs) — convert Open Questions in README to table with columns: Question / Status / Needed expertise / Issue (if open) / Blocker. Do NOT file GitHub issues for every row — leave "Issue (if open)" empty where there isn't one. That's a Simon decision, not yours.
8. **THREAT-MODEL.md** (half day) — new file at `commonweave/THREAT-MODEL.md`. Follow structure in review doc §7:
    - Assets
    - **Accepted tradeoffs** (state surveillance, metadata leakage, public contributor targeting)
    - **External adversaries** (grifters, greenwashers, entryists, spam, harassers, AI-generated org spam, fake orgs gaming directory)
    - **Internal adversaries** (maintainer drift, pipeline bias, AI-assisted drift, founder capture) — THIS SECTION IS LOAD-BEARING, don't skimp
    - Attack surfaces
    - Controls (matrix: control → adversaries it defends → residual risk)
    - Review cadence (quarterly, signed off by Simon, logged in repo)
    Name specific existing tooling as countermeasures: `pipeline_auditor.py`, `staleness_check.py`, `dedup_merge.py`, `legibility` column (intended, backfill pending), `[commonweave]` daily-memory tag.
9. **Canonical domain line** (~5 min) — add `Official site: simonlpaige.com/commonweave/` near top of README. Do NOT register commonweave.earth — that's Simon's call. Note the recommendation in a comment or in the review doc's recommendations section.

## Style rules (hard requirements)
Pulled from `AGENTS.md` and `MEMORY.md`:
- **No em dashes.** Use regular dashes or reword. If you see an em dash in the existing README, leave it if it's Simon's (don't introduce new ones; don't bulk-rewrite existing ones without asking).
- **No AI-style language.** Richard Feynman "Curious Explainer" voice. Simple language, concrete examples.
- **Commit messages:** Feynman voice. First line = one sentence summary. Body (if needed) = why this was worth doing. See `docs/commit-style.md`.
- **No inventing stats.** All numbers must trace to DB or existing docs. If unknown, write `[NEEDS VERIFICATION]`.
- **Preserve existing good parts:**
  - Critique-first link at top of README
  - "What Does Not Exist Yet" section content (just relocating it)
  - Mycelial Strategy failure-modes list
  - All "Open problem:" callouts in Phase 1
  - `Economic Transition Mechanisms` scale disclaimers (UBI $4T math, CLT scale reality, etc.)

## Deliverables
1. Modified README.md
2. New `commonweave/THREAT-MODEL.md`
3. Modified `data/build_map_v2.py` (edge schema)
4. Modified `map.html` (confidence default + narrative presets + edge toggle)
5. (If content was moved from README to BLUEPRINT.md) a summary block in the final report of what moved
6. A short final report as `commonweave/reviews/EXECUTION-REPORT-2026-04-23.md` listing:
    - Files changed
    - Each fix # and status (done / partial / skipped with reason)
    - Any `[NEEDS VERIFICATION]` markers left in place
    - Any decisions that need Simon's sign-off before merging

## Working directory
`C:\Users\simon\.openclaw\workspace\commonweave`

## Git
Working on the commonweave repo. Commit each fix separately with a Feynman-voice message. Do NOT push — Simon reviews and pushes.

## If something is unclear
Write your question into the final report's "Questions for Simon" section and skip/partial that fix. Don't guess.
