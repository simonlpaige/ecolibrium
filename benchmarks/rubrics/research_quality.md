# Rubric: Research Quality

> 100 points total. Score is informational.
> Implemented in [`../../evals/score_research_quality.py`](../../evals/score_research_quality.py).

## Dimensions

### Claim specificity (20 pts)

- 20: PR adds a numbered, formatted claim/falsifier/vector (e.g. `C9.`, `F-PROJ-6.`, `AV-EXT-7.`) that is testable.
- 8: PR mentions a claim but doesn't follow the format or skips a falsifier.
- 0: PR adds prose without a specific claim.

### Source quality (20 pts)

- 20: 5+ external sources cited and resolving.
- 12: 2-4 sources.
- 6: 1 source.
- 0: No external sources.

Internal repo links don't count toward source quality (they count toward integration, below).

### Falsifiability (20 pts)

- 20: PR adds or references a concrete falsifier tied to a specific claim.
- 0: No falsifier proposed.

### Counterargument strength (15 pts)

- 15: PR steelmans an opposing position (touches `STEELMAN-ALTERNATIVES.md` or includes a "What it gets right" / counterargument section).
- 0: PR only argues one side.

### Framework integration (15 pts)

- 15: PR cross-references at least 3 of `README.md`, `CLAIMS.md`, `FALSIFIERS.md`, `ATTACK-VECTORS.md`, `CRITIQUE.md`, `GOVERNANCE.md`.
- 8: PR cross-references at least 1.
- 0: PR is isolated from the rest of the framework.

### Next task (10 pts)

- 10: PR includes a "Needed work:" line, a follow-up note, or extends a related file with an open question.
- 0: PR ends with no follow-up surfaced.

## How to read the score

Research-track scoring rewards specificity and falsifiability over volume. A 30-line PR adding one sharp claim with a concrete falsifier and a real source can score higher than a 300-line essay with no testable content.

If a research PR scores below 40, the most common gap is missing sources or missing falsifier — not low effort.
