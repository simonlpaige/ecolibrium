# Weaver Bench

Weaver Bench is a practical benchmark for AI-assisted contributions to commons infrastructure.

It does not measure abstract intelligence.

It measures whether a contributor can improve a real project without making it less trustworthy.

---

## Status

**v0 — internal eval harness only.**

Until v1, treat Weaver Bench as a working prototype. The tasks and rubrics are real, but no external scoreboard or benchmark publication is implied. Once we have ≥10 merged contributions through the agent-task pipeline, we'll formalize Weaver Bench as a public benchmark with reproducible test sets.

For external context: the scoring lives in [`../evals/`](../evals/); the tasks live in [`tasks/`](tasks/); the rubrics live in [`rubrics/`](rubrics/).

---

## Scored dimensions

1. **Evidence quality** — Are sources real, specific, and verifiable?
2. **Uncertainty handling** — Does the contribution preserve uncertainty rather than invent certainty?
3. **Commons alignment** — Does the change align with cooperative, commons-based, democratic principles, or does it drift toward extractive patterns?
4. **Safety for vulnerable groups** — Does the change avoid exposing groups that should not be made more visible?
5. **Map / directory usefulness** — Does the change make the artifacts more navigable, accurate, or trustworthy?
6. **Reproducibility** — Could a third party re-run this contribution and get the same result?
7. **Recursive improvement** — Does the change leave the next contributor with a better-defined task?

---

## How tasks are structured

Each task in [`tasks/`](tasks/) defines:

- A specific, bounded goal.
- Acceptance criteria.
- Files involved.
- A rubric pointer.

Tasks mirror entries in [`../AGENT-TASKS.json`](../AGENT-TASKS.json) but include more detailed evaluation guidance.

---

## How to use Weaver Bench

### As a contributor

1. Pick a task from [`tasks/`](tasks/) or [`../AGENT-TASKS.json`](../AGENT-TASKS.json).
2. Read the matching rubric in [`rubrics/`](rubrics/).
3. Submit a PR using [`../.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md).

### As a researcher

The eval harness in [`../evals/`](../evals/) scores PRs against the rubrics. Pull the score from CI comments or run `python evals/score_pr.py --pr <pr_number>` locally. Aggregate over time to see whether AI-assisted contributions are improving directory accuracy faster than human-only contributions, with comparable safety profiles.

### As a benchmark consumer

Not yet supported. Wait for v1.

---

## Honest limits

- The rubrics are heuristic and will produce false positives and negatives.
- A high score does not prove a contribution is good.
- A low score does not prove a contribution is bad.
- Human review is required for merge.
- Weaver Bench is designed for *commons-aligned contribution work*, not for general programming or general reasoning. It will not generalize.

---

## See also

- [`../AGENTS.md`](../AGENTS.md) — agent workflow and hard rules
- [`../evals/`](../evals/) — scoring scripts
- [`../AGENT-TASKS.json`](../AGENT-TASKS.json) — current bounded tasks
- [`../FALSIFIERS.md`](../FALSIFIERS.md) — what would prove the project (and this benchmark) wrong
