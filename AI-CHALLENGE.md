# The Commonweave Agent Challenge

Commonweave is a public, falsifiable directory and framework for the post-labor economy. We need help from humans and AI-assisted contributors to make it more accurate, more navigable, and harder to fool.

The challenge is simple: **make one concrete improvement** to a real commons-oriented project.

Do not submit:

- generic praise,
- vague strategy,
- unsourced manifesto language,
- "here's what Commonweave should do" essays without a PR attached.

Do submit:

- one verified country gap closed,
- one map feature shipped,
- one weak claim weakened,
- one missing source added,
- one falsifier proposed,
- one attack vector documented.

## Tracks

### 1. Global Directory Track

Find, verify, or correct organizations in underrepresented countries. The directory is currently ~83% US/UK records (21,559 of 26,022). Closing that gap is the single most valuable thing a contributor can do.

Examples:
- Pick one country with <50 records. Verify or correct 10. PR.
- Add 5 organizations from a country missing from the directory.
- Backfill `legibility` (formal/hybrid/informal/unknown) for one country.

### 2. Map Intelligence Track

Make the map more useful, legible, filterable, and honest about uncertainty.

Examples:
- High-confidence-only toggle (Tier B + `alignment_score >= 5`).
- Better mobile UX (touch-friendly filters, better popups, clustering).
- Edge inspection: show *why* two organizations are connected.

### 3. Edge Provenance Track

Explain why organizations are connected. Add `edge_type`, `confidence`, `explanation`, `created_at`, `source_script` to generated edges in `data/build_map_v2.py`.

### 4. Falsification Track

Find claims that are weak, overconfident, or wrong. Add them to [`CLAIMS.md`](CLAIMS.md) with status, confidence, evidence, and a concrete falsifier.

### 5. Governance Stress-Test Track

Show how the project could be captured, centralized, spammed, surveilled, or made unsafe. Document the threat, who benefits, who is harmed, early warning signs, and countermeasures. Add to [`ATTACK-VECTORS.md`](ATTACK-VECTORS.md).

---

## What makes a great PR

The best PRs:

- improve something **measurable**,
- **cite sources**,
- **reduce uncertainty** (don't increase word count),
- **preserve vulnerable-group safety** (see [`AGENTS.md`](AGENTS.md) safety rule),
- and **leave a better task** for the next contributor.

---

## Where to start

1. Read [`AGENTS.md`](AGENTS.md).
2. Read [`CRITIQUE.md`](CRITIQUE.md) — it tells you where the work actually is.
3. Pick one task from [`AGENT-TASKS.json`](AGENT-TASKS.json) or from GitHub issues labeled `agent-ready`.
4. Submit a PR using [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).

---

## What this challenge is not

This is not a benchmark for general intelligence. It does not score reasoning or eloquence. It scores whether a contributor can improve a real project without making it less trustworthy.

There are no prizes, no tokens, no leaderboard rewards beyond credit in [`AGENT-LEADERBOARD.md`](AGENT-LEADERBOARD.md) and on the PR itself. The point is the work.

If you want a benchmark to test against: [`benchmarks/README.md`](benchmarks/README.md) describes Weaver Bench, the internal eval harness.
