# Commonweave PR Scoring

This directory holds simple, transparent rubrics for scoring contributions. Scores are **informational only** and **do not block merges**.

The scoring system is intentionally boring at first. It exists to:

1. Make rubrics public so contributors know what we value.
2. Surface low-quality patterns (unsourced changes, false positives, exposed vulnerable groups).
3. Build the dataset that a more sophisticated benchmark (`benchmarks/`) can use later.

## Files

- [`score_pr.py`](score_pr.py) — top-level dispatch. Reads PR metadata, classifies the contribution type, and routes to the type-specific scorer.
- [`score_data_quality.py`](score_data_quality.py) — scores directory contributions.
- [`score_map_quality.py`](score_map_quality.py) — scores map/code contributions.
- [`score_research_quality.py`](score_research_quality.py) — scores research/citation contributions.

## Running

```bash
python evals/score_pr.py --pr <pr_number>     # uses gh CLI to fetch PR
python evals/score_pr.py --diff <diff_file>   # score from a local diff file
python evals/score_pr.py --files <file1> <file2> ...  # score specific changed files
```

Output is human-readable plus a JSON summary on stdout for CI parsing.

## Rubrics

### Data contribution (100 points)

| Dimension | Weight |
|-----------|--------|
| Source quality (cited, verifiable) | 25 |
| Correct country / geography | 15 |
| Framework relevance | 15 |
| False-positive reduction (broken sites fixed, misclassified orgs corrected) | 15 |
| Vulnerable-group safety (legibility honesty, conservative detail) | 15 |
| Reproducibility note in PR | 10 |
| Leaves a next task | 5 |

### Map / code contribution (100 points)

| Dimension | Weight |
|-----------|--------|
| Feature works as described | 25 |
| Does not break existing map/UI | 20 |
| Improves user comprehension | 20 |
| Preserves provenance (edge metadata, source attribution) | 15 |
| Mobile / accessibility improvement | 10 |
| Leaves a next task | 10 |

### Research contribution (100 points)

| Dimension | Weight |
|-----------|--------|
| Claim specificity (precise, citable) | 20 |
| Source quality | 20 |
| Falsifiability (concrete falsifier proposed) | 20 |
| Counterargument strength | 15 |
| Framework integration (ties to README, CLAIMS, FALSIFIERS) | 15 |
| Leaves a next task | 10 |

## Honest limits

These rubrics are heuristic. They will produce false confidence on novel contributions. They are not a substitute for human review.

When the scorer flags a PR low, that's a signal to look more carefully — not a verdict.

When the scorer flags a PR high, that's a signal it touched the right things — not proof it was right.
