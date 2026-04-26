# Task: Add one serious falsifier

**ID:** `cw-framework-falsifier-001`
**Type:** research
**Difficulty:** hard
**Rubric:** [`../rubrics/research_quality.md`](../rubrics/research_quality.md)

## Goal

Pick one claim in `README.md` or `DEEP-DIVE.md`. Add it to `CLAIMS.md` (if not already there). Define what evidence would weaken or falsify it, and add the falsifier to `FALSIFIERS.md`.

## Why this matters

A claim that cannot be falsified is not a claim. Commonweave's credibility depends on being able to say what would change its mind. Right now, `CLAIMS.md` and `FALSIFIERS.md` are seeded but thin.

## Files

- `CLAIMS.md` (claim ledger format).
- `FALSIFIERS.md` (falsifier format).
- `README.md` or `DEEP-DIVE.md` (source of the claim).

## Process

1. Read `README.md` and `DEEP-DIVE.md`. Find a claim that is:
   - specific enough to test,
   - load-bearing for the framework,
   - not yet captured in `CLAIMS.md`.

2. Add the claim to `CLAIMS.md` using the existing format. Set status, confidence, evidence, and link to the source location in the repo.

3. Add a falsifier to `FALSIFIERS.md`. The falsifier must be:
   - **concrete** (specific test or observation),
   - **observable** (a third party could check it),
   - **tied to the claim** (cite the C-number),
   - **change-inducing** (state what would happen to the framework if the falsifier triggered).

4. Submit a PR.

## Acceptance criteria

- [ ] Claim is quoted or referenced precisely (file + section).
- [ ] Falsifier is concrete and observable.
- [ ] At least one source or real-world case is cited.
- [ ] PR explains whether the claim should be kept, weakened, or marked unresolved.
- [ ] Both `CLAIMS.md` and `FALSIFIERS.md` updated coherently.

## Examples of good falsifiers

- "If a longitudinal study of >=50 community energy projects shows >50% revert to private/state ownership within 10 years, the commons-based-distribution claim is fragile."
- "If a blind expert audit of 100 randomly sampled `alignment_score >= 5` records produces <70% agreement with directory classifications, alignment scoring is unreliable."

## Examples of bad falsifiers

- "If the framework feels wrong." (Vibes, not test.)
- "If something better comes along." (Not specific.)
- "If the project fails." (Tautological.)

## Related

- `CLAIMS.md` (existing claim ledger).
- `FALSIFIERS.md` (existing falsifiers).
- `STEELMAN-ALTERNATIVES.md` (competing theories that may already imply falsifiers).
