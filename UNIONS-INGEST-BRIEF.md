# Brief: Add labor unions to the Commonweave directory

You are Claude Code. This brief is the source of truth. Read it once, then execute.

## Mission

Add **labor unions** to the Commonweave directory as a new taxonomy branch. Target: federations and national-level unions first (~300-600 orgs), not locals. Cover two ingest paths: **Wikidata SPARQL** and **ITUC affiliates list**.

## Why we're doing this (so you frame it correctly in code comments + docs)

Labor unions are one of the oldest working examples of democratic ownership of a commons (collective labor power). They're principles 3 (Democratic Sovereignty) and 4 (Common Ownership) of the Commonweave framework expressed in the real world. Co-ops, mutual aid societies, and credit unions are already indexed. Unions are the missing sibling.

## Hard rules

1. **Follow the existing pipeline conventions.** Don't invent new patterns. Model `ingest_unions.py` on `commonweave/data/ingest_wikidata_bulk.py`.
2. **Federations + nationals only in v1.** No locals. Locals are a v2 conversation. A good filter: orgs whose `instance of` / `subclass of` in Wikidata is "trade union federation" (Q3395115), "national trade union center" (Q11038979), or "trade union" (Q178790) *and* that have "country" set and "headquarters location" set at the national level. ITUC affiliates are all federation-tier by definition.
3. **Mark legibility correctly.** ITUC affiliates and Wikidata-sourced national unions = `legibility=formal`. Works councils embedded in law (Germany, Austria, Netherlands) = `legibility=formal`. Informal worker solidarity networks without legal status = `legibility=informal` (skip for v1 unless already in Wikidata).
4. **No em dashes** in any user-visible text.
5. **Surgical.** Don't touch unrelated files. Don't refactor the pipeline.
6. **Don't run this yet if PIPELINE-PDF-BRIEF.md is still mid-flight.** If you see uncommitted changes related to `pipeline.pdf` / `PIPELINE.md` in the working tree, STOP and announce: the previous task isn't done. This brief runs *after* the PDF ships and is committed.

## What to read first

- `commonweave/data/_common.py` (shared helpers, DB connection)
- `commonweave/data/ingest_wikidata_bulk.py` (model your script on this)
- `commonweave/data/migrate_legibility.py` (so you understand the legibility column)
- `commonweave/data/taxonomy.yaml` (so you know where to add the new branch — don't dump it in your output, just know the shape)
- `commonweave/PIPELINE.md` (should exist from the previous task — confirms the pipeline contract)
- `commonweave/data/dedup_merge.py` (so you understand dedup rules — name+country isn't enough, needs location match)

## Work items

### 1. Taxonomy additions

Add a new top-level branch to `commonweave/data/taxonomy.yaml`:

```yaml
labor:
  description: Worker power and democratic labor organizations
  subtypes:
    union_federation:
      description: National or international federations of unions (AFL-CIO, ITUC, IG Metall)
      wikidata_ids: [Q3395115, Q11038979]
    national_union:
      description: National-level trade unions
      wikidata_ids: [Q178790]
    worker_cooperative_federation:
      description: Federations of worker cooperatives (distinct from individual worker co-ops)
      wikidata_ids: [Q4539]   # cooperative federation; filter by "worker" subtype in code
    works_council_system:
      description: Legally-mandated worker representation bodies (German Betriebsrat, Dutch OR, etc.)
      wikidata_ids: [Q1141395]
    labor_education_org:
      description: Worker education, labor colleges, union training institutes
      wikidata_ids: []   # manual curation or Wikidata text search
```

If the YAML structure in the existing file differs, match the existing pattern. Don't break the file.

### 2. `commonweave/data/ingest_unions.py`

Model on `ingest_wikidata_bulk.py`. Structure:

- Wikidata SPARQL query for each taxonomy subtype above (filter by country-level, skip locals by requiring HQ set + excluding subclasses like "local union chapter" if those exist as Wikidata classes).
- For each org: insert with `legibility=formal`, category=`labor/<subtype>`, source=`wikidata_unions`, evidence URL = Wikidata item URL.
- Dedup against existing rows using the same rules as `dedup_merge.py` (name + country + location proximity). Do NOT run dedup yourself — just insert, and let the existing dedup pipeline catch overlaps on the next run.
- Log runs to `commonweave/data/ingest-unions-run.log`.
- Be idempotent: re-running should update existing rows (by Wikidata ID), not create duplicates.
- Print a summary at the end: total queried, total inserted, total updated, total skipped (and why).

### 3. `commonweave/data/ingest_ituc.py`

Separate script for ITUC (International Trade Union Confederation) affiliates.

- Source: https://www.ituc-csi.org/list-of-affiliated-organisations (public listing). If the listing URL has moved, find the current one. If no clean page exists, fall back to Wikipedia's "List of trade unions" by country pages — document the fallback in the script header.
- Parse the affiliate list: name, country, acronym, website, member count if listed.
- Insert with `legibility=formal`, category=`labor/union_federation` or `labor/national_union`, source=`ituc_affiliates`.
- Be polite to the server: `time.sleep(1)` between requests, proper User-Agent, respect robots.txt.
- Cache HTML responses to `commonweave/data/sources/ituc-cache/` so re-runs don't re-hit the server.

### 4. Dispatcher

Add a `ingest_labor.py` dispatcher that runs both scripts in order (Wikidata first, then ITUC). Mirrors the `ingest_india.py` pattern.

### 5. Documentation

- Append a "Labor unions" section to `commonweave/PIPELINE.md` explaining the new ingest branch. Match the voice and formatting of the rest of the file.
- Add a row to `commonweave/DATA.md` (if the file documents sources in a list/table) for `ituc_affiliates` and `wikidata_unions`.
- Update the PDF? **No, skip re-rendering the PDF for this pass.** Simon can re-render on the next big update. Note the omission in your final commit message so he knows.

### 6. Do a dry run

Run `python commonweave/data/ingest_unions.py --dry-run` (add a `--dry-run` flag that queries Wikidata but doesn't write to the DB). Print the count of orgs that would be inserted, broken down by subtype. This is your verifier — if it returns 0 or some absurd number like 50,000, something's wrong with the SPARQL query.

Target range for dry-run insert count: **200-800 orgs** across all subtypes combined. If outside that range, inspect the query and fix before doing a real run.

### 7. Actually run it

After the dry-run looks sane, run both scripts for real:

```bash
python commonweave/data/ingest_unions.py
python commonweave/data/ingest_ituc.py
```

Capture the output. If the real run diverges wildly from the dry-run estimate, stop and flag it rather than committing a bad batch.

### 8. Rebuild frontend artifacts

After ingest, the map + search index are stale. Run:

```bash
python commonweave/data/build_map_v2.py
python commonweave/data/build_search_index.py
python commonweave/data/export_directory.py
```

This updates the files that the live site uses. Then copy any changed artifacts from `commonweave/data/` to `simonlpaige.github.io/commonweave/data/` (follow whatever pattern the existing cron `commonweave-frontend-update` uses — look at its payload in the gateway config, or just mirror the files that differ).

### 9. Commit + push

Workspace repo (`C:\Users\simon\.openclaw\workspace\commonweave\`, branch `master`):
- Commit message first line: `Add labor unions to the directory (Wikidata + ITUC)`.
- Body: one short paragraph, Feynman voice, no em dashes. What you added, how many orgs it brought in, the legibility decisions you made, the note that the PDF wasn't re-rendered.

Live-site repo (`C:\Users\simon\.openclaw\workspace\simonlpaige.github.io\`, branch `main`):
- Commit message first line: `Update directory data: labor unions added`.
- Body: one short paragraph. What changed on the public-facing side (map points, search index, directory export).

Push both.

## Done = all of these

- [ ] `taxonomy.yaml` has a `labor` branch with subtypes
- [ ] `ingest_unions.py` exists, has `--dry-run`, runs cleanly
- [ ] `ingest_ituc.py` exists, caches HTML, runs cleanly
- [ ] `ingest_labor.py` dispatcher exists
- [ ] Dry-run printed a sane count (200-800 orgs)
- [ ] Real run completed, summary captured
- [ ] `PIPELINE.md` has a "Labor unions" section
- [ ] Map + search index + directory export rebuilt
- [ ] Live-site data files synced
- [ ] Workspace repo committed + pushed
- [ ] Live-site repo committed + pushed
- [ ] At end, run: `openclaw system event --text "Done: Labor unions added to Commonweave. N orgs inserted. Ready for Codex red-team." --mode now` (replace N with actual count)

## If you get stuck

- Wikidata SPARQL endpoint rate-limits? Add `time.sleep(2)` between queries and set User-Agent.
- ITUC site structure has changed? Document the fallback source, implement that, move on.
- Dry-run count is way off? Don't force it. Stop, write what you found to `commonweave/data/ingest-unions-run.log`, and announce: `openclaw system event --text "ingest_unions dry-run returned X (expected 200-800). Need Simon's input on SPARQL query." --mode now`.

## Follow Karpathy rules

1. State assumptions. Ask when confused.
2. Minimum code. No speculative abstractions.
3. Touch only what the task requires.
4. The "Done" checklist is your verifier.
