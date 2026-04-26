# Falsifiers

> Commonweave should become **easier to disprove, not harder**. A project that cannot be falsified cannot be trusted.

A good falsifier is:

- **concrete** — names a measurable thing that could be observed,
- **observable** — could be checked by a third party,
- **tied to a specific claim** — references a CLAIMS.md entry,
- **not merely a vibe** — "if it feels wrong" is not a falsifier,
- **capable of changing the project** — if the falsifier triggered, something would actually have to change.

If a claim cannot be falsified, weaken it or remove it.

---

## Project-level falsifiers

These would weaken or invalidate Commonweave as a whole, not just a single claim.

### F-PROJ-1. The directory is a loose pile, not a network.

Tied to: C6
Test: Sample 50 edges from `map.html` after edge provenance lands. Independently verify whether the two organizations in each edge have any real-world connection (shared funding, shared members, shared strategy, public collaboration). If <40% are real, the edges are keyword artifacts and the network claim collapses.
What changes if falsified: Either rebuild edge generation from a different signal, or remove the network framing from the README.

### F-PROJ-2. Non-Western, informal, or hybrid groups are systematically missing at a scale that makes the framework parochial.

Tied to: C1
Test: After legibility backfill on at least 10 non-US/UK countries, if formal-registry records still account for >75% of high-alignment entries, the directory has not corrected for its origin bias.
What changes if falsified: Reframe Commonweave as a "registry-visible commons directory" rather than a global directory. Or commit to a non-registry ingest pipeline as a hard prerequisite for v2.

### F-PROJ-3. High-alignment organizations don't actually do what the framework predicts.

Tied to: C4
Test: Blind external review of 100 randomly sampled `alignment_score >= 5` records. If <70% of expert classifications agree with the directory's framework-area assignment, alignment scoring is unreliable.
What changes if falsified: Rebuild the scoring system, or reduce the directory's claim from "aligned organizations" to "keyword-matched candidates."

### F-PROJ-4. Users cannot find useful collaborators through the directory or map.

Tied to: C6
Test: Recruit 10 organizers, researchers, or co-op builders. Ask each to find 3 potentially useful collaborators using the directory and map alone. If <50% report at least one useful contact, the directory is not functioning as a coordination tool.
What changes if falsified: Refocus on the directory as a research artifact, not a coordination layer. Or rebuild discovery (search, filtering, recommendations).

### F-PROJ-5. Commonweave is read by humans but not improved by them.

Test: After 12 months of public visibility with a working PR template and agent-task pipeline, if the project has fewer than 10 external contributors with merged PRs, the contribution funnel is broken.
What changes if falsified: Reduce scope. Remove participation framing from the README. Either accept that Commonweave is a personal research artifact, or invest in real outreach and onboarding.

---

## Framework-level falsifiers

### F-FW-1. Commons-based distribution does not solve trending-toward-abundance goods.

Tied to: C2
Test: Longitudinal study of >=50 community energy or open-source-food projects over 10+ years. If >50% are captured, defunded, or revert to private/state distribution within 10 years, commons-based distribution is fragile in a way the framework does not currently acknowledge.
What changes if falsified: Add a "fragility" section to the framework. Identify what governance interventions are needed to make commons-based distribution survive.

### F-FW-2. Skilled care work cannot be sustained as voluntary surplus.

Tied to: C3
Test: A counterexample: a community health worker, midwife, or eldercare network that has operated at scale (>1,000 participants) for >10 years on volunteer labor without substantial wage compensation, and where worker burnout is not above non-volunteer baselines.
What changes if falsified: Weaken the wage-premium claim. Add the conditions under which volunteer care can scale.

### F-FW-3. Mycelial Strategy (cross-phase connective tissue) is necessary.

Tied to: C5
Test: At least one historical commons transition (Mondragon-style worker-cooperative federation, the Quaker network, Indian self-help group movements, etc.) that succeeded without explicit cross-phase connective infrastructure.
What changes if falsified: Reframe Mycelial Strategy as one viable connective approach among several, not a necessary feature.

### F-FW-4. Selective abundance is the honest framing.

Tied to: C7
Test: Evidence that all framework-relevant goods (including land, fresh water, skilled care, attention) become effectively non-rival within a near-term (25-year) horizon.
What changes if falsified: Move toward post-scarcity framing. Most current evidence runs the other direction (climate, demographics, attention economy), so this is unlikely — but the falsifier is on the table.

---

## Data-level falsifiers

### F-DATA-1. The 26,022 candidate count is inflated by duplicates or near-duplicates.

Test: Run `data/dedup_merge.py` against the current DB and report how many merges fire. If >5% of records merge, the headline count is misleading.
What changes if falsified: Update the README headline number. Annotate the difference between "rows in DB" and "distinct organizations."

### F-DATA-2. Geocoded points are concentrated in a few cities, not spread across countries.

Test: For each of the 61 countries, check what fraction of geocoded points fall within a single metro area. If >70% of countries have >50% of their points in one metro, the geographic-coverage claim is misleading at sub-country resolution.
What changes if falsified: Add a "geographic concentration" caveat to the directory description. Prioritize secondary-city ingest.

### F-DATA-3. Most "broken websites" are tracking-parameter false positives.

Test: For records flagged with broken websites, re-run liveness checks with stripped UTM/tracking parameters and a real browser User-Agent. If >40% pass after stripping, the broken-site signal is unreliable.
What changes if falsified: This was already partly addressed in lead-finder v2 (see workspace TOOLS.md). Mirror the same fix in directory liveness checks.

---

## Adding a falsifier

When adding a falsifier:

1. Tie it to a specific claim in `CLAIMS.md` (or a section of `README.md` if the claim is not yet captured).
2. Make the test concrete and reproducible.
3. State explicitly what would change if the falsifier triggered.
4. Mark it `F-PROJ-`, `F-FW-`, or `F-DATA-` and number sequentially within section.

A falsifier is a promise: if the test runs and fails, the project changes. If you wouldn't honor that promise, don't add the falsifier.
