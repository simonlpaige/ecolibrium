# Rubric: Data Quality

> 100 points total. Score is informational, not a merge gate.
> Implemented in [`../../evals/score_data_quality.py`](../../evals/score_data_quality.py).

## Dimensions

### Source quality (25 pts)

- 25: Every added/changed record has a verified source URL from a recognized registry, news outlet, or peer-reviewed reference.
- 15: At least 2 sources are cited and resolve.
- 8: At least 1 source is cited.
- 0: No source URLs detected.

### Geography correctness (15 pts)

- 15: Country code is ISO 3166-1 alpha-2 and matches the org.
- 0: Mismatched, missing, or invented country code.

### Framework relevance (15 pts)

- 15: Framework areas are correctly assigned and align with the org's actual work.
- 8: Framework areas are present but plausibly mismatched.
- 0: Missing or invented framework areas.

### False-positive reduction (15 pts)

- 15: PR removes or corrects at least 3 broken or misclassified records.
- 8: PR removes or corrects at least 1.
- 0: PR adds records without correcting any existing errors.

### Vulnerable-group safety (15 pts)

- 15: Legibility classified honestly; sensitive groups handled with `unknown` or minimal detail; no street-level locations for at-risk orgs.
- 8: Legibility classified but inconsistent.
- 0: PR exposes sensitive groups, or defaults to `formal` without evidence.

### Reproducibility (10 pts)

- 10: Changes made via an ingest script that can be re-run.
- 7: Changes made to JSON with a clear diff and methodology note.
- 0: Direct DB edits or missing notes.

### Next task (5 pts)

- 5: PR adds a TODO, follow-up, or `_notes` entry pointing the next contributor at related work.
- 0: PR ends without surfacing next steps.

## How to read the score

A score of 90+ is rare and means the contributor met every dimension well.

A score in the 60s means the contribution helped but had clear gaps.

A score below 40 is usually a signal that the PR description or the changes themselves are incomplete — not necessarily that the work is bad. Look at the `notes` field in the scorer output for what was missing.

A score is never a substitute for human review.
