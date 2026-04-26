# AGENTS.md — Commonweave Agent Instructions

Commonweave is a directory and framework for mapping organizations building cooperative, commons-based, democratic, ecological, mutual-aid, and post-labor infrastructure.

Your job is not to praise or summarize the project.

Your job is to make one concrete improvement.

---

## Required first reads

1. [`README.md`](README.md) — what this project is and what state it's in
2. [`CRITIQUE.md`](CRITIQUE.md) — the section-by-section honest audit of weaknesses (read this; it tells you where the work actually is)
3. [`data/CONTRIBUTING-DATA.md`](data/CONTRIBUTING-DATA.md) — directory schema and how to add or correct an organization
4. [`AGENT-TASKS.json`](AGENT-TASKS.json) — machine-readable task list
5. [`FALSIFIERS.md`](FALSIFIERS.md) — what would prove this project wrong

If a file you need is missing, that itself is a worthwhile thing to flag in a PR.

---

## Default workflow

1. Pick exactly **one** task labeled `agent-ready` (in [`AGENT-TASKS.json`](AGENT-TASKS.json) or in GitHub issues with the `agent-ready` label).
2. Make the smallest useful change.
3. Preserve uncertainty instead of inventing certainty.
4. Run any relevant validation script in `data/` if your change touches the directory.
5. Submit a PR using [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md), which asks for:
   - what changed,
   - why it matters,
   - sources used,
   - validation performed,
   - known uncertainty,
   - one suggested next task.

---

## High-value contribution types

### Data
- Verify organizations in countries with fewer than 50 records (still many; the long tail past Brazil/Australia/UK/US/Bulgaria thins out fast).
- Audit the recent Wave A ingest (Brazil mapa_oscs, Australia ACNC, Bulgaria Wikidata NPO) for false positives and misclassifications.
- Add missing source URLs to `data/commonweave_directory.db` rows (or to `data/search/<country>.json`).
- Correct misclassified organizations.
- Backfill or audit the `legibility` field (`formal` / `hybrid` / `informal` / `unknown`). As of 2026-04-25, ~25,980 records still read `unknown`, and ~138,803 read `formal` from auto-classification at ingest time -- the latter is worth spot-auditing too.

### Map
- Add a high-confidence-only toggle to `map.html` (Tier B + `alignment_score >= 5`).
- Improve mobile map UX.
- Add clustering or filter panels.
- Show *why* nodes are connected (edge explanations).
- Add edge provenance metadata (`edge_type`, `confidence`, `explanation`, `created_at`, `source_script`).

### Research
- Turn open questions in `README.md` into cited research notes under `RESEARCH.md`.
- Fill `[NEEDS EXAMPLE]` cells in the governance matrix in `README.md`.
- Add falsifiers to weak claims in `CLAIMS.md`.
- Add counterexamples.
- Strengthen or weaken claims based on evidence.

### Framework critique
- Break the argument constructively.
- Identify hidden assumptions.
- Add historical counterexamples.
- Propose safer governance mechanisms.
- Flag claims that sound ideological, vague, or overconfident — and say what evidence would change them.

---

## Hard rules

Never:

- invent sources (don't make up URLs, citations, or org names),
- add unsourced organizations to the directory,
- expose vulnerable informal groups (see safety rule below),
- treat visibility as legitimacy,
- treat state registration as the only valid form of organization,
- add manifesto language ("we will," "we must," "the future demands"),
- remove critique because it is uncomfortable,
- optimize for quantity over trust.

A PR that adds 200 unsourced rows is worse than a PR that fixes 5 and explains the method.

---

## Safety rule for vulnerable groups

Some organizations should not be made more visible without care.

If a group is informal, operating under repression, protecting survivors, organizing labor, supporting migrants, doing abolitionist work, or operating in a hostile political context, prefer `legibility=unknown` or minimal metadata unless the group **publicly self-describes and clearly wants discoverability**.

When in doubt: less detail, not more. Note the uncertainty in your PR.

---

## Reduce uncertainty, don't add words

Every contribution should reduce uncertainty. The single test for a good PR is:

> Does this PR make Commonweave more accurate, more falsifiable, more navigable, or safer than it was?

If the answer is "it's longer now," that's not a contribution.

Good contributions:

- verify a record,
- remove a false positive,
- add source metadata,
- explain an edge,
- weaken an overconfident claim,
- improve a filter,
- document a risk,
- give the next contributor a clearer task.

---

## Recursive improvement clause

Before finishing, leave one thing better for the next contributor:

- add a task to [`AGENT-TASKS.json`](AGENT-TASKS.json),
- clarify an acceptance criterion,
- document a blocker you hit,
- add a missing source you wished was there,
- or improve an instruction in this file.

Every PR should leave the repo more legible for the next human or agent.

---

## See also

- [`AI-CHALLENGE.md`](AI-CHALLENGE.md) — the public challenge framing and contribution tracks
- [`CLAIMS.md`](CLAIMS.md) — the claim ledger
- [`FALSIFIERS.md`](FALSIFIERS.md) — falsifiers tied to claims
- [`ATTACK-VECTORS.md`](ATTACK-VECTORS.md) — how this project could be captured, abused, or decay
- [`STEELMAN-ALTERNATIVES.md`](STEELMAN-ALTERNATIVES.md) — the strongest competing theories
- [`benchmarks/README.md`](benchmarks/README.md) — Weaver Bench, the internal eval harness
