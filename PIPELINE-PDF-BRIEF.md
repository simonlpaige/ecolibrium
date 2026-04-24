# Brief: Pipeline Flow Diagram PDF

You are Claude Code. This brief is the source of truth. Read it once, then execute.

## Mission

Produce a **beautiful, polished PDF** titled something like **"How Commonweave Finds and Grades Organizations"** that explains — with a clean logic-flow diagram — the full pipeline that fills the Commonweave directory (currently 25,837 orgs across 61 countries).

Audience: humans first (founders, journalists, skeptics, potential contributors), but also AI agents reading it. Plain language (Richard Feynman "Curious Explainer" voice — simple words, vivid analogies, no AI-speak, no em dashes, no marketing filler). Someone non-technical should be able to read it and understand the whole flow. An AI agent should be able to read it and know how to add a new ingest source without reading the code.

## Hard rules

1. **No em dashes.** Use regular dashes or reword.
2. **Feynman voice.** Kitchen-table language. No "leverage", "empower", "unlock".
3. **Human AND AI friendly.** After the PDF, also write a parallel Markdown version at `commonweave/PIPELINE.md` that mirrors the PDF content 1:1. The PDF is pretty; the MD is grep-able.
4. **Be accurate.** If you're not sure what a script does, read it. Don't invent.
5. **Cite the scripts.** Each stage of the flow should name the actual Python file that does the work (e.g. `ingest_wikidata_bulk.py`) so anyone can jump from the diagram to the code.
6. **Keep it to ~6-10 pages.** Not a book. Not a pamphlet. One full walkthrough, one full diagram, a "how to add a source" appendix.

## What to read before writing

These are the canonical files. Read them, then explain what they do.

**Top-level Commonweave context:**
- `commonweave/README.md`
- `commonweave/BLUEPRINT.md` (if relevant sections exist)
- `commonweave/DATA.md`
- `commonweave/DIRECTORY.md` (first ~200 lines to understand scope; don't ingest all 25k orgs)
- `commonweave/META-DIRECTORY.md`

**Pipeline scripts (the meat):**
- `commonweave/data/_common.py` (shared helpers)
- `commonweave/data/ingest_wikidata_bulk.py` (bulk SPARQL pull, Wikidata)
- `commonweave/data/ingest_gov_registry.py` (government registry ingest)
- `commonweave/data/ingest_ofn.py` (Open Food Network)
- `commonweave/data/ingest_india.py` (India dispatcher + notes)
- `commonweave/data/researcher_HN.py` and any `run_researcher_*.py` (per-country researcher pattern)
- `commonweave/data/run_next_country.py` (country-runner orchestrator)
- `commonweave/data/analyze_alignment.py` (alignment scoring)
- `commonweave/data/audit_pass1.py`, `audit_pass2.py`, `audit_pass3_ntee.py`, `audit_ntee.py`, `audit_quality.py`, `run_audit.py` (grading / quality audits)
- `commonweave/data/dedup_merge.py` (deduplication with location matching)
- `commonweave/data/staleness_check.py` (never-auto-archive staleness flow)
- `commonweave/data/pipeline_auditor.py` (weekly self-improvement loop)
- `commonweave/data/phase1_geocode.py`, `phase2_filter.py`, `phase3_intl_fix.py` (geocoding / filtering / intl)
- `commonweave/data/build_map_v2.py`, `build_search_index.py`, `export_directory.py` (frontend build)
- `commonweave/data/trim_to_aligned.py`
- `commonweave/data/migrate_legibility.py` (the legibility column — this matters)

Also skim, then mention briefly:
- `commonweave/data/i18n_terms.py`
- `commonweave/data/native_queries.py`
- `commonweave/data/taxonomy.yaml` (high-level taxonomy, don't dump it)

**Module context for philosophy (so the intro has the right framing):**
- `modules/commonweave/CONTEXT.md`

## PDF structure (suggested; deviate if a better structure emerges)

1. **Cover page** — title, subtitle ("A field guide to how we find aligned organizations, grade them, and keep the list honest"), date, single-line tagline, minimal design.
2. **One-sentence summary** — what the pipeline does, in one line.
3. **The big picture diagram** — a full-page or near-full-page logic flow. Sources → ingest → analyze/grade → dedup → geocode → staleness → audit → publish (map, directory, search). Each node labels the script(s) that do the work. Use a real diagramming tool (Mermaid rendered to SVG/PNG via mmdc, or Graphviz, or pure SVG hand-drawn — whichever yields the cleanest result).
4. **Stage-by-stage walkthrough** — one short section per stage. For each stage: what it does in plain language, what the inputs/outputs are, which script(s), one interesting design choice (e.g. dedup requires matching location, not just name+country; staleness never auto-archives).
5. **The grading ladder** — explain the `legibility` column (formal / hybrid / informal / unknown) and how alignment scoring works. This is the honesty layer.
6. **The self-improvement loop** — `pipeline_auditor.py`. Weekly read-only pass, writes evidence-cited proposals, retires ignored proposals after 3 weeks. Mention it sharpens the pipeline without Simon having to nag it.
7. **Appendix A: "How to add a new source"** — numbered steps an AI agent or human can follow. Which file to model after, which DB columns to populate, how to mark legibility, where to log the run.
8. **Appendix B: "How to audit the list yourself"** — one paragraph on reading `trim_audit/proposals-*.md` and the weekly diff reports.
9. **Back page / footer** — link to the repo, the directory, the map. Say "this document describes how the list is made; the list itself lives at commonweave.earth/directory".

## Build approach

**Source file**: write it as Markdown first (`commonweave/PIPELINE.md`), render to PDF second. Pick ONE rendering path that works cleanly on Windows:

- Preferred: **Pandoc + wkhtmltopdf** or **Pandoc + LaTeX (xelatex)**. If neither is installed, try `npm i -g md-to-pdf` and use that.
- Diagram: **Mermaid** rendered via `@mermaid-js/mermaid-cli` (`mmdc`) to SVG, then embed in the Markdown as an image reference. If Mermaid CLI isn't installed, install it via `npm i -g @mermaid-js/mermaid-cli`.
- If Mermaid proves too simple for the big diagram, **Graphviz** (`dot`) is acceptable.

Put the built artifact at:
- `C:\Users\simon\.openclaw\workspace\commonweave\pipeline.pdf`
- `C:\Users\simon\.openclaw\workspace\simonlpaige.github.io\commonweave\pipeline.pdf` (copy)

Put the diagram source (`.mmd` or `.dot`) at:
- `C:\Users\simon\.openclaw\workspace\commonweave\assets\pipeline-diagram.mmd` (or `.dot`)

Put the rendered SVG + PNG at:
- `C:\Users\simon\.openclaw\workspace\commonweave\assets\pipeline-diagram.svg`
- `C:\Users\simon\.openclaw\workspace\commonweave\assets\pipeline-diagram.png`

## Frontend linking

Add a prominent, non-ugly link to `pipeline.pdf` on both:

- `C:\Users\simon\.openclaw\workspace\commonweave\directory.html`
- `C:\Users\simon\.openclaw\workspace\commonweave\map.html`

Match the existing visual style (open the files, don't guess). A "How we find organizations (PDF)" link near the top of the content area is good. Do not add a big banner.

Mirror the edits to the live-site copies at:

- `C:\Users\simon\.openclaw\workspace\simonlpaige.github.io\commonweave\directory.html`
- `C:\Users\simon\.openclaw\workspace\simonlpaige.github.io\commonweave\map.html`

## Pending frontend sync

After your main work, sync any other drift from workspace → live. Known drift as of 2026-04-24:

- `commonweave/doc.html` in workspace (Apr 21, 21927 bytes) is newer than live (Apr 15, 21826 bytes). Copy workspace → live.

Verify by diffing all `*.html` in both dirs and copying workspace → live for any file whose workspace version is newer. Do not overwrite live-only files that don't exist in workspace.

## Commits and pushes

Two repos. Both get commits.

**Workspace repo** (`C:\Users\simon\.openclaw\workspace\commonweave\`):
- Branch: whatever is current (likely `master` based on git status output).
- Commit message style: Feynman "Curious Explainer" voice. Plain language. No em dashes. See `C:\Users\simon\.openclaw\workspace\docs\commit-style.md` if it exists. Example first line: `Add a PDF that explains how the directory gets built`.

**Live-site repo** (`C:\Users\simon\.openclaw\workspace\simonlpaige.github.io\`):
- Branch: `main`.
- Same commit message style.

Push both to their remotes when done. If the workspace repo has unrelated dirty files (DIRECTORY.md, search/index.json, etc.), leave them alone — only commit files you changed for this task.

## Done = all of these

- [ ] `commonweave/PIPELINE.md` exists and reads well
- [ ] `commonweave/pipeline.pdf` exists, looks polished, has the diagram embedded
- [ ] Diagram sources saved in `commonweave/assets/`
- [ ] `pipeline.pdf` copied to live-site repo
- [ ] `directory.html` and `map.html` link to `pipeline.pdf` in both repos
- [ ] `doc.html` drift (and any other drift) synced workspace → live
- [ ] Workspace repo committed + pushed
- [ ] Live-site repo committed + pushed
- [ ] At end, run: `openclaw system event --text "Done: Commonweave pipeline PDF shipped. Awaiting Codex red-team." --mode now`

## If you get stuck

- Missing binary (pandoc, mmdc, wkhtmltopdf)? Try `winget install` or `npm i -g`. If both fail, fall back to a different rendering path.
- Can't figure out what a script does? Read the file, then write your best plain-language explanation. Flag the ones you're unsure about in `PIPELINE.md` with `[unsure: ...]` so Codex can red-team them.
- Scope creep? Stop. This is PDF + link + sync + commit. Not a pipeline rewrite.

## Follow these rules (Karpathy)

1. State assumptions explicitly. Ask when confused.
2. Minimum code that solves the problem. No speculative abstractions.
3. Touch only what the task requires. No drive-by refactors.
4. Verifiable goals. The "Done" checklist above is your verifier.
