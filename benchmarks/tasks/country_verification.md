# Task: Verify one underrepresented country

**ID:** `cw-data-global-gap-001`
**Type:** data
**Difficulty:** medium
**Rubric:** [`../rubrics/data_quality.md`](../rubrics/data_quality.md)

## Goal

Pick one country with fewer than 50 organizations in the directory. Verify or improve at least 10 records. Submit a PR with corrections, source citations, and a short methodology note.

## Why this matters

The directory is currently ~83% US/UK skewed. Closing that gap is the single most valuable kind of data contribution. A contributor with local knowledge of any non-US/UK country immediately has expertise the directory does not have.

## Files

- `data/search/<country>.json` (the per-country index used by `directory.html`).
- `data/CONTRIBUTING-DATA.md` (schema and safety rules).

## Process

1. Identify a target country. Run a quick check:
   ```bash
   python -c "import json, pathlib; p = pathlib.Path('data/search'); print({f.stem: len(json.loads(f.read_text(encoding='utf-8')).get('organizations', [])) for f in p.glob('*.json')})"
   ```
   Pick one with <50 records that you have local knowledge of.

2. Spot-check at least 10 records:
   - Does the website resolve?
   - Is the description accurate?
   - Is the country code right?
   - Is the framework area assignment plausible?
   - Should `legibility` be classified (formal / hybrid / informal / unknown)?

3. Edit the JSON in place. Add or update the `_notes` block at the top with the date, your handle, and a one-line summary.

4. Submit a PR using `.github/PULL_REQUEST_TEMPLATE.md`.

## Acceptance criteria

- [ ] At least 10 organizations checked.
- [ ] Broken or invalid URLs corrected or marked.
- [ ] Misclassified records corrected.
- [ ] No vulnerable group exposed unnecessarily (default `legibility=unknown` for any informal/sensitive group).
- [ ] PR includes a short methodology note (what was checked, how, with what sources).
- [ ] All cited sources actually resolve.

## Safety considerations

If your country has hostile political conditions for any of the framework's organizational types (labor, migrant support, abolitionist work, mutual aid in repressive contexts), default to **less detail, not more**. Country-level location only. No street addresses for sensitive groups. Read the safety rule in [`../../AGENTS.md`](../../AGENTS.md).

## Related

- `data/CONTRIBUTING-DATA.md` (schema).
- `ATTACK-VECTORS.md` AV-EXT-2 (state surveillance).
- `FALSIFIERS.md` F-PROJ-2 (parochial framework if non-Western coverage stays thin).
