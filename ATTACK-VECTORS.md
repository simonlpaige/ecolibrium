# Attack Vectors

> How could Commonweave be captured, degraded, abused, or made dangerous?
>
> A project that can't name its own failure modes can't defend against them. This file is the running list. Add to it.

This file is a partner to [`THREAT-MODEL.md`](THREAT-MODEL.md). Threat-model.md is about the framework's adversaries; this file is about the *project*'s adversaries — including itself.

---

## Format

Each attack vector includes:

1. **Threat** — what could happen
2. **Who benefits** — the adversary's incentive
3. **Who is harmed** — the people exposed by the failure
4. **Early warning signs** — what to watch for
5. **Countermeasures** — how to resist
6. **Open questions** — what we don't know yet

---

## External capture

### AV-EXT-1. Corporate greenwashing

**Threat:** Large corporations or industry groups submit aligned-looking entries to the directory (e.g. "EcoTech Solutions" with vaguely cooperative language) to legitimize themselves, improve search rankings, or appear in a "100 organizations building the post-labor economy" list they didn't deserve.

**Who benefits:** Greenwashing actors — corporate ESG departments, astroturf nonprofits, foundations laundering reputation.

**Who is harmed:** Real cooperatives crowded out of attention. Researchers who treat the directory as authoritative. Public trust in the framework.

**Early warning signs:**
- Submissions from PR/marketing email domains.
- Sudden batch submissions of similarly-worded organizations.
- Submissions for organizations with >500 employees and conventional ownership.
- Pressure from foundations to include their grantee networks wholesale.

**Countermeasures:**
- Source-quality requirement on all PRs (cited registry, news, or peer-reviewed reference).
- Tier B / Tier D distinction in the schema (registry-backed vs candidate).
- `legibility` column that surfaces *how* the org was found.
- Public review window for batch submissions.
- Reject PRs that don't include source URLs.

**Open questions:**
- How do we score alignment for ambiguous organizations (genuine co-op subsidiary of a conventional parent)?
- Should we maintain a "rejected for greenwashing" list for transparency?

---

### AV-EXT-2. State surveillance and targeting

**Threat:** A state actor scrapes the directory to identify and target organizers, mutual aid networks, labor groups, migrant support, or abolitionist work — especially in countries with legal or paramilitary repression of these groups.

**Who benefits:** Authoritarian states, hostile police, ICE-equivalents, anti-union employers, anti-abortion regimes.

**Who is harmed:** Vulnerable organizers and the communities they serve. Could include physical harm, legal harm, deportation, or loss of livelihood.

**Early warning signs:**
- Bulk scraping traffic patterns.
- Inquiries for "comprehensive lists" of organizations in specific repressive contexts.
- Reports from organizations that they were targeted after being added.

**Countermeasures:**
- **Hard rule:** never expose informal/vulnerable groups without explicit self-description and consent (see AGENTS.md safety rule).
- Default `legibility=unknown` until verified.
- Country-level exclusion list for high-risk contexts.
- No street-level addresses for sensitive groups — country/region only.
- Robots.txt / rate-limit aggressive scrapers.
- Honor takedown requests within 48 hours, no questions asked, when the requester is from the affected organization.

**Open questions:**
- Is hosting the directory on commonweave.earth or GitHub mirrors enough to put vulnerable groups at risk regardless of safeguards?
- Should we offer a "researchers-only" sub-corpus for high-risk regions?
- What's our policy on requests from law enforcement?

---

### AV-EXT-3. Foundation dependency

**Threat:** A funder offers significant resources contingent on shaping the framework, the directory's inclusion criteria, or the project's governance — and Commonweave drifts to match the funder's preferences.

**Who benefits:** The funder. Sometimes the project (in the short term).

**Who is harmed:** Communities the project was supposed to serve. Trust in the framework's independence.

**Early warning signs:**
- Funder requests editorial say.
- Funder pushes for inclusion of their grantees regardless of fit.
- Project starts using funder's preferred language.
- Project removes critique of funder-aligned approaches.

**Countermeasures:**
- Funding policy in `GOVERNANCE.md` requiring all funder relationships to be public.
- No editorial veto for any funder.
- Multiple small funders preferred over one large one.
- Hard rule: framework critique cannot be removed because it is uncomfortable to a funder.

**Open questions:**
- Is there a funding model that doesn't create capture risk?
- Do we accept anonymous funding?

---

### AV-EXT-4. Political astroturfing

**Threat:** Coordinated submissions push a particular ideological frame (left, right, ecomodernist, primitivist, libertarian) into the directory or into framework documents through volume rather than evidence.

**Who benefits:** Political operators trying to capture the legitimacy of "commons" framing.

**Who is harmed:** The framework's analytical clarity. Real organizations whose work doesn't fit the captured frame.

**Early warning signs:**
- Sudden volume of similar submissions or PRs.
- Coordinated language across submissions.
- Pressure to add or remove framework concepts based on political fashion rather than evidence.

**Countermeasures:**
- All framework changes go through PR with cited evidence.
- Steelman alternatives file (`STEELMAN-ALTERNATIVES.md`) keeps competing theories visible.
- Critique-first culture in CRITIQUE.md.
- Slow-down rules: framework-touching PRs need a comment-aging period before merge.

**Open questions:**
- How do we tell good-faith disagreement from coordinated capture?

---

### AV-EXT-5. Data extraction by platforms

**Threat:** AI training pipelines or LLM agent platforms scrape the entire directory and framework to enrich proprietary datasets, without contributing back.

**Who benefits:** Commercial AI labs.

**Who is harmed:** Contributors whose work is laundered into closed systems. The commons framing is inverted (we built a commons; they enclosed it).

**Early warning signs:**
- Bulk crawler traffic.
- AI-generated content using directory data without attribution.
- Inquiries for direct data dumps under non-CC licenses.

**Countermeasures:**
- CC BY-SA 4.0 license — anything built on this must share back.
- `llms.txt` is **opt-in** for what we want indexed; the rest is licensed.
- Public takedown record for license violators.
- Refuse offers for proprietary licensing of the corpus.

**Open questions:**
- Is CC BY-SA enforceable against AI training in practice?
- Should we add a "no AI training without share-back" clause beyond CC BY-SA?

---

## Internal decay

### AV-INT-1. Founder bottleneck

**Threat:** The project depends on Simon to make every editorial decision, and either burns him out or stalls when he steps back.

**Who benefits:** No one.

**Who is harmed:** The project, contributors, communities counting on it.

**Early warning signs:**
- PRs sit unreviewed for >2 weeks.
- All major decisions go through one person.
- No documented decision-making process.

**Countermeasures:**
- `GOVERNANCE.md` documents decision-making.
- Agent-task pipeline pre-bounds work so contributors don't need permission.
- `AGENTS.md` empowers AI-assisted contributors to act without waiting for review on agent-ready tasks.
- Recruit at least 2 trusted reviewers before the project is dependent on them.

**Open questions:**
- At what contributor count should governance shift?

---

### AV-INT-2. Hidden hierarchy

**Threat:** The project performs openness while real decisions happen in private channels (Discord DMs, email, etc.).

**Who benefits:** Insiders.

**Who is harmed:** External contributors who don't know the actual decision rules.

**Early warning signs:**
- "We discussed this offline" appears in PR threads.
- Decisions appear in commits without prior public discussion.
- Outsiders' PRs get treated differently than insiders'.

**Countermeasures:**
- All non-trivial decisions documented in public (issue, PR, or `discussions/`).
- No private project channels for editorial decisions.
- New contributors get the same review treatment as old ones.

**Open questions:**
- How do we handle private safety reports (e.g. for AV-EXT-2 takedown requests) without creating a private decision channel?

---

### AV-INT-3. Endless critique without implementation

**Threat:** The project becomes a place for talking about commons rather than building one. CRITIQUE.md grows; the directory doesn't.

**Who benefits:** No one. (Sometimes contributors who enjoy the discourse without doing the work.)

**Who is harmed:** Communities counting on the directory to be useful.

**Early warning signs:**
- More words written about the framework than rows added to the directory.
- More PRs touching framework docs than data files.
- Open Questions stay open for >6 months without research notes.

**Countermeasures:**
- Agent-task pipeline biases toward concrete deliverables.
- Quarterly "directory delta" report — what changed in the data, not the framework.
- Hard ratio: at least 3 data PRs for every framework-doc PR.

**Open questions:**
- Is the 3:1 ratio right? Should it be enforced or just monitored?

---

### AV-INT-4. Sloppy data accumulation

**Threat:** Volume becomes the metric. Records get added without verification. The directory inflates and trustworthiness collapses.

**Who benefits:** Contributors who want their PR merged. Sometimes the project's appearance of growth.

**Who is harmed:** Researchers and organizers who treat the directory as reliable.

**Early warning signs:**
- Records added without sources.
- Tier D candidate count grows faster than Tier B verified count.
- `[NEEDS REVIEW]` rows accumulate without being reviewed.

**Countermeasures:**
- Source-quality is required, not optional.
- Tier B / Tier D distinction visible in all directory views.
- Agent-task scoring weights `false_positive_reduction` heavily.
- Periodic audits via `data/audit_pass*.py`.

**Open questions:**
- Should we cap candidate-tier growth until verified-tier catches up?

---

### AV-INT-5. Ideological hardening

**Threat:** The framework ossifies around its current claims. Counterexamples are dismissed instead of incorporated. The project becomes evangelism instead of inquiry.

**Who benefits:** No one.

**Who is harmed:** Anyone who would have benefited from a more accurate framework.

**Early warning signs:**
- New evidence is rejected without engagement.
- `STEELMAN-ALTERNATIVES.md` stops being updated.
- CRITIQUE.md is treated as historical rather than active.
- Manifesto language ("we will," "we must") creeps into framework docs.

**Countermeasures:**
- CRITIQUE.md is required reading and stays first-linked from the README.
- `STEELMAN-ALTERNATIVES.md` is maintained and visible.
- AGENTS.md hard rule: don't add manifesto language.
- Falsifiers are required for new claims.

**Open questions:**
- How do we surface incorporated changes (so contributors see that critique actually shifts the framework)?

---

### AV-INT-6. Safety-blind radical transparency

**Threat:** The project's commitment to openness collides with vulnerable-group safety, and the openness wins by default.

**Who benefits:** No one (it just feels principled).

**Who is harmed:** The exposed groups.

**Early warning signs:**
- Pressure to publish complete records for vulnerable orgs in the name of transparency.
- Resistance to `legibility=unknown` defaults.
- Takedown requests treated as censorship.

**Countermeasures:**
- Safety rule in AGENTS.md is non-negotiable.
- Default to less detail when in doubt.
- Takedown requests from affected orgs honored without bureaucracy.
- Country-level exclusion list for high-risk contexts.

**Open questions:**
- Where is the line between transparency and safety in cases where the org publicly self-describes but the political context shifts?

---

## Adding a vector

When adding an attack vector:

1. Mark it `AV-EXT-` (external) or `AV-INT-` (internal) and number sequentially within section.
2. Include all six fields: threat, who benefits, who is harmed, early warning signs, countermeasures, open questions.
3. Be specific about the threat. "Bad people might do bad things" is not a vector.
4. Propose at least one countermeasure that's actually implementable.

A vector without countermeasures is a complaint. A vector with countermeasures is project work.
