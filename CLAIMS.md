# Commonweave Claims Ledger

> A claim is something Commonweave says is true about the world or about itself. Each claim should be specific, cited where possible, and falsifiable.
>
> If a claim cannot be falsified, either weaken it or remove it.

This file is a working document. Add claims, weaken claims, contest claims. Status moves from `draft` to `supported`, `disputed`, or `unresolved` as evidence accumulates.

---

## Format

```
C<n>. <Claim, in one sentence>

Status: draft / supported / disputed / unresolved
Confidence: low / medium / high
Evidence: <what backs this up; cite sources>
Falsifiers: <what would prove this wrong>
Related files: <where the claim lives in the repo>
Needed work: <what would resolve this>
```

---

## Active Claims

### C1. The directory is skewed toward formal registry-visible organizations.

Status: weakened
Confidence: high (on the formal-skew framing); medium (on the geographic-skew framing as of 2026-04-25)
Evidence: As of 2026-04-25 (verified directly against `data/commonweave_directory.db`), the directory holds 164,783 records across 172 countries. US+UK now account for ~13.2% (21,697 records). Brazil, Australia, and Bulgaria became the top non-US/UK sources after the April 2026 ingest waves (mapa_oscs_brazil, acnc_charity_register, wikidata_bg_npo). The geographic-skew claim that drove this entry has been substantially weakened by the new ingest. The *formal-registry-skew* claim is unchanged: ~138,803 records (~84%) carry `legibility=formal`, almost all from registries (Brazil mapa_oscs, Australia ACNC, UK Charity Commission, IRS BMF, Wikidata NPO classes). Informal and hybrid coverage remains thin.
Falsifiers: A data audit showing comparable depth of *informal* and *hybrid* coverage (e.g. >5,000 records each, with `legibility` honestly classified, from non-registry sources -- mutual aid networks, community-list curation, indigenous/caste-community networks where appropriate to make visible).
Related files: README.md (What Exists Today), data/commonweave_directory.db, data/search/, data/ingest_acnc.py, data/ingest_brazil_oscs.py, data/ingest_bulgaria_npo.py
Needed work: Audit the auto-classified `legibility=formal` records for accuracy. Continue informal/hybrid source expansion (mutual aid, indigenous community networks, hybrid forms in countries where formal registries don't capture commons work). Re-evaluate this claim quarterly.

### C2. The governance mode for trending-toward-abundance goods is commons-based distribution.

Status: draft
Confidence: medium
Evidence: README "Selective Abundance" governance matrix names solar, open-source software, community gardens with commons-based distribution as the operative governance mode. Real-world examples cited (Centre for Renewable Energy and Action on Climate Change [NG]).
Falsifiers: A persistent pattern where commons-based distribution of these goods leads to under-provision or capture more often than market or state distribution does. A study of 50 community energy projects showing >50% revert to private/state ownership within 10 years would meaningfully weaken this.
Related files: README.md (Selective Abundance section)
Needed work: Cite at least 3 longitudinal studies of commons-based distribution outcomes for energy, software, or food. Add to RESEARCH.md.

### C3. Skilled care work is a persistent scarcity that requires recognition and compensation premiums.

Status: draft
Confidence: medium
Evidence: README "Selective Abundance" governance matrix. No directory examples currently filled in (cell marked [NEEDS EXAMPLE]).
Falsifiers: Evidence that automation or AI substitutes substantially reduce demand for human caregivers (community health workers, midwives, eldercare) within a 10-year horizon. Or evidence that volunteer-only models scale sustainably.
Related files: README.md (Selective Abundance section)
Needed work: Fill the [NEEDS EXAMPLE] cell (cw-needs-example-fill-001). Cite community health worker compensation studies.

### C4. Directory entries with alignment_score >= 5 reflect organizations actually doing what the framework predicts.

Status: draft
Confidence: low
Evidence: Alignment scoring is a multi-pass keyword scoring against framework mechanisms. 3,657 entries score >=5. Spot-checked manually during initial filtering, but no systematic external validation.
Falsifiers: A blind audit where domain experts review a random sample of 100 high-alignment records and find that <70% actually match the framework area's predicted behavior. Or a finding that alignment_score correlates poorly with independent expert classification.
Related files: data/commonweave_directory.db, data/audit_pass*.py
Needed work: Run a blind external validation on a random sample. Document the precision/recall of the alignment scoring.

### C5. Mycelial Strategy (connective tissue across phases) is necessary for the framework to function.

Status: draft
Confidence: low
Evidence: Asserted in framework. No empirical test in the directory yet.
Falsifiers: Historical case studies where commons-based transitions succeeded without explicit cross-phase connective infrastructure. Or evidence that connective infrastructure failed to prevent capture or fragmentation.
Related files: README.md (The Framework in 90 Seconds), DEEP-DIVE.md
Needed work: Identify 5+ historical commons transitions and assess whether they had Mycelial-equivalent infrastructure and whether it correlates with outcome.

### C6. The directory can reveal a real transition network rather than a loose pile of NGOs.

Status: unresolved
Confidence: low
Evidence: Network edges (2,687) exist between organizations, but edges currently lack provenance — they may be keyword artifacts rather than real-world relationships.
Falsifiers:
  - High-scoring organizations do not actually share mechanisms, relationships, or strategy.
  - Most edges are keyword artifacts rather than real relationships.
  - Non-Western, informal, or hybrid groups are systematically missing.
  - Users cannot find useful collaborators through the map.
Related files: data/build_map_v2.py, map.html
Needed work: Add edge provenance (cw-edge-provenance-001), then sample 50 edges and verify whether the connection is real-world or keyword-only.

### C7. Selective abundance (not post-scarcity) is the honest framing for this transition.

Status: supported
Confidence: medium
Evidence: README explicitly distinguishes goods trending cheap (energy, info, food) from persistently scarce (land, water, care, attention). Backed by Doughnut Economics framing and Ostrom's commons work.
Falsifiers: Evidence that all framework-relevant goods become non-rival within a near-term horizon (no longer requiring governance for scarcity). This is unlikely on physical-resource grounds but should be re-examined as automation advances.
Related files: README.md (Selective Abundance section)
Needed work: Add a 5-year and 25-year scarcity forecast for each goods category, with cited sources.

### C8. Visibility is not legitimacy: a registered organization is not necessarily aligned, and an unregistered group is not necessarily fringe.

Status: supported
Confidence: high
Evidence: The CRITIQUE.md and the legibility column design explicitly acknowledge this. Directory holds candidate (Tier D) and registry-backed (Tier B) records separately.
Falsifiers: Evidence that registry-backed orgs match framework behavior at a rate indistinguishable from informal groups (would suggest the legibility distinction is not informative).
Related files: README.md, CRITIQUE.md, data/commonweave_directory.db (legibility column)
Needed work: Once legibility backfill is done, compare framework-fit rates across formal/hybrid/informal groups.

---

## Adding a claim

When you add a claim:

1. Number it sequentially.
2. Quote or precisely reference the source location in the repo.
3. Set confidence honestly. Default to `low` if unsure.
4. Provide at least one concrete falsifier. If you can't, the claim is too vague.
5. Identify what work would resolve the claim's status.

A claim with no falsifier is not a claim. It's a vibe.
