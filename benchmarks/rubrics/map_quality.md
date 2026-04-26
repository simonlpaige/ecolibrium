# Rubric: Map / Code Quality

> 100 points total. Score is informational.
> Implemented in [`../../evals/score_map_quality.py`](../../evals/score_map_quality.py).

## Dimensions

### Feature works (25 pts)

- 25: Feature is shipped and demonstrably works in a manual smoke test.
- 0: Feature is broken, partial, or doesn't load.

The scorer awards this by default on any code change because it cannot run a manual smoke test from CI alone. Human review confirms.

### No regression (20 pts)

- 20: Existing functionality (default map, directory search, mobile rendering) continues to work.
- 0: PR breaks an existing surface.

The scorer awards this by default; CI/visual review confirms.

### User comprehension (20 pts)

- 20: PR adds tooltips, labels, help text, or filter explanations that make the change legible to someone landing on the page cold.
- 10: PR adds a feature without explaining it.
- 0: PR removes existing affordances that explain behavior.

### Preserves provenance (15 pts)

- 15: Edge metadata, source attribution, or generation timestamps are preserved or extended (`edge_type`, `confidence`, `explanation`, `created_at`, `source_script`).
- 0: PR strips provenance or hides where data came from.

### Mobile / accessibility (10 pts)

- 10: PR includes media queries, touch targets, ARIA labels, or other improvements measurable on a small screen.
- 0: Desktop-only.

### Next task (10 pts)

- 10: PR leaves a TODO/FIXME comment, extends `AGENT-TASKS.json`, or files an issue for follow-up.
- 0: No next-task signal.

## How to read the score

The scorer is heuristic on this track because most evidence requires runtime. Rely on human review for "feature works" and "no regression"; rely on the scorer for the structural signals.
