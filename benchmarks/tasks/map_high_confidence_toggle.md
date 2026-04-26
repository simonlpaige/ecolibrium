# Task: Add high-confidence-only map toggle

**ID:** `cw-map-high-confidence-toggle-001`
**Type:** code
**Difficulty:** medium
**Rubric:** [`../rubrics/map_quality.md`](../rubrics/map_quality.md)

## Goal

Add a toggle to `map.html` that filters the map to only show Tier B organizations with `alignment_score >= 5`. This will display roughly 3,657 of the current 11,991 visible points — the strongest framework matches.

## Context

The current map shows all geocoded organizations regardless of tier or alignment. A user looking for "the strongest examples of the framework in action" has no way to filter to those.

Tier B = registry-backed (UK Charity Commission, IRS BMF, Wikidata, ProPublica, etc.). `alignment_score >= 5` = strongest keyword matches against framework mechanisms.

## Files

- `map.html` (primary)
- Optional: a small helper to recompute the cache of high-confidence point IDs at build time, if performance matters.

## Acceptance criteria

- [ ] Toggle is visible on desktop and mobile.
- [ ] Default map behavior is unchanged when the toggle is off.
- [ ] Filtered mode includes a 1-2 sentence explanation of what "high-confidence" means and what it excludes.
- [ ] Map still loads without console errors.
- [ ] No visible performance regression on first load.

## Safety considerations

- Excluding lower-confidence records is fine; mention in the explanation that absence is *not* evidence of low quality, only of less data.

## Related

- README: "What Exists Today" section describes Tier A/B/D and `alignment_score`.
- Data: `data/commonweave_directory.db` has the relevant fields.
- Future task: once the toggle exists, consider adding a filter for `legibility=formal` once that backfill is done.
