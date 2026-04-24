# TODO: Tier A definition

**Logged:** 2026-04-23
**Context:** README review (CLAUDE-CODE-BRIEF-2026-04-23.md)

## The problem

The README previously said "Tier A/B verified." The database does not have a `tier_a` row. As of 2026-04-23, the actual tier distribution is:

- `tier_b`: 15,854
- `tier_d`: 10,032
- null: 136
- `tier_a`: 0

`build_map_v2.py` defines Tier A as "reviewed rows with both description and website" but the UPDATE query produces 0 rows because no orgs in the DB have `review_status='reviewed'`. The tier_a code path exists but is dead.

## Decision needed

1. **Option A:** Accept that there is no Tier A in the current data. Call Tier B "registry-backed" (which it is) and leave Tier A as a future tier for manually reviewed orgs. This is what the current README says.

2. **Option B:** Define Tier A by a different criterion that orgs actually meet -- e.g., has both a website and alignment_score >= 5. This would produce some Tier A orgs and make the tier system more useful.

3. **Option C:** Rename the tiers entirely. Tier B becomes "Registry-backed," Tier C becomes "Keyword-inferred," Tier D becomes "Unverified." Drop the A/B/C/D letters entirely in favor of names.

## Who decides

Simon. This is a data model change, not a README change.

## Current state

README and THREAT-MODEL.md use "registry-backed (Tier B)" to avoid claiming Tier A exists. The `build_map_v2.py` code still contains the Tier A logic but it produces 0 rows. If Option B or C is chosen, both the script and the docs need to update together.
