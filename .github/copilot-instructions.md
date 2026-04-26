# GitHub Copilot Instructions for Commonweave

You are working in the Commonweave repository — a public directory and framework for cooperative, commons-based, democratic, ecological, and post-labor infrastructure.

## Read these first

1. [`AGENTS.md`](../AGENTS.md) — full agent instructions and hard rules
2. [`README.md`](../README.md) — project overview
3. [`CRITIQUE.md`](../CRITIQUE.md) — known weaknesses (read this; it tells you where the work is)
4. [`AGENT-TASKS.json`](../AGENT-TASKS.json) — bounded tasks to pick from

## What we want

- One concrete improvement per PR.
- Source-cited changes (registry, news, peer-reviewed, or directly from the repo).
- Reduce uncertainty: verify a record, fix a false positive, add provenance, weaken an overconfident claim.

## What we don't want

- Generic praise or summaries.
- Unsourced organizations or invented citations.
- Manifesto language ("we will," "we must," "the future demands").
- Removal of critique because it is uncomfortable.

## Hard rules

- **Never invent sources.** If you don't have a real URL, don't add one.
- **Never expose vulnerable groups.** Default `legibility=unknown` for informal/sensitive orgs unless they publicly self-describe.
- **Cite everything** that touches the directory, the framework, or claims.
- **Leave the next task better defined** before finishing.

## Workflow

- Pick exactly one task from `AGENT-TASKS.json` or a GitHub issue with the `agent-ready` label.
- Make the smallest useful change.
- Use the PR template (`.github/PULL_REQUEST_TEMPLATE.md`) — fill in every section honestly.
- Run validation scripts in `data/` if your change touches the directory.

## File-specific guidance

- `data/*.py` — Python 3, sqlite3, no external DB calls, idempotent where possible.
- `data/search/*.json` — keep formatting consistent; add a top-level note when you correct entries.
- `map.html` — vanilla JS; no build step; preserve existing structure.
- Markdown docs — plain markdown, no admonition extensions; relative links; keep tone factual.
- `CLAIMS.md`, `FALSIFIERS.md`, `ATTACK-VECTORS.md` — follow the format at the top of each file.

When in doubt, ask in the PR description rather than guessing.
