# README.md Review — 2026-04-23

**Reviewer:** Billy (external)
**Respondent:** Larry
**Scope:** README.md only. Architecture / data-files pass to follow.

---

## Overall verdict

The README is unusually strong for an early-stage civilizational framework. It has already absorbed a lot of obvious criticism: it admits the directory is the concrete deliverable, distinguishes the framework from the database, names the current limits, says there are no pilots, no staff, no legal entity, and no current partnerships. That honesty is a major asset.

But it still has one big structural problem: the README is trying to be four documents at once — project landing page, political theory, data report, and contributor guide. That makes it impressive but hard to act on.

---

## Section-by-section

### 1. Opening is compelling but too broad too fast

**Billy's critique.** The strongest sentence is "The directory is the concrete deliverable. The framework is the argument for it." That distinction should be sharpened. Project has two audiences (directory users vs. theory debaters) that shouldn't be forced through the same door. Proposed fix: rewrite opening around a blunt product statement and split reader paths.

**Larry's response — partially agree.** The "too much in one door" diagnosis is right. But the proposed split (users vs. debaters) is the wrong axis, and would weaken the project.

The whole point of Commonweave is that the directory and framework are inseparable. Directory without framework = another NGO list (dozens exist). Framework without directory = another post-capitalist manifesto (hundreds exist). What makes Commonweave unusual is that the 24,508 orgs are filtered *by* the framework's mechanisms. Route "directory users" past the theory and you lose the thing that makes the directory worth using. You also lose what makes the theory falsifiable — the claim that these mechanisms already exist in the wild.

Real split isn't audience-by-intent. It's **entry-depth**:
- 60-second landing that states the product bluntly
- 5-minute overview that shows directory + framework as one thing
- Deep docs branching off for anyone who wants to keep going

So: keep README as the router (Billy's right about that), but split by depth, not by user type.

### 2. "Selective Abundance" governance matrix

**Billy's critique.** Section is rhetorically strong but under-operationalized. Names categories but doesn't turn them into a governance matrix. Proposed fix: add a table with resource type / examples / constraint / governance mode / failure mode.

**Larry's response — fully agree, with one addition.** This is the strongest suggestion in the review. "Selective abundance" is currently a rhetorical move that hasn't been turned into a tool. A table converts it from a clever framing into the spine of the framework.

Addition: add a 5th column for **current real-world examples** — actual orgs from the directory that govern that resource type. That's how you make the framework falsifiable and close the loop back to the directory. Otherwise the table is still theory.

### 3. Directory stats need stronger confidence disclaimers

**Billy's critique.** "24,508 aligned organizations" sounds more authoritative than the pipeline supports. Only 11% score ≥5, only 41% are Tier A/B. Fix: soften headline and add confidence legend.

**Larry's response — agree, with a tweak.** Go further than Billy suggests. Put the confidence tiers **in the opening directory sentence**, not as a separate section:

> The directory holds 24,508 candidate organizations across 60 countries. 10,067 are verified (Tier A/B), 2,805 are high-confidence framework matches (score ≥5), the rest are candidates awaiting review. All exclusions are preserved in trim audits.

One sentence, one number plus three qualifiers, no separate legend to skip. Confidence legend lives in DATA.md.

**Real miss Billy didn't catch:** the `legibility` column shipped last week (formal / hybrid / informal / unknown) doesn't appear in the README. This is exactly the self-reported-bias signal that preempts "your data is US/UK/formal-NGO-biased" attacks. Should be in the directory stats.

### 4. Framework is too large for README

**Billy's critique.** README is trying to be the canonical framework doc. Should summarize and link to BLUEPRINT / THEORY-OF-CHANGE / GOVERNANCE etc. Proposed structure: What this is / Try it / Current state / Data confidence / Why it matters / 90-sec framework / What is still weak / How to contribute / Key docs.

**Larry's response — agree with one change.** Move "What is still weak" *before* "Why it matters." Anti-hype first, then pitch. Current README does this correctly (critique-first link at top) — restructure must preserve that ordering or it loses the README's single best rhetorical move.

Caution on moving Phase 1/2/3 to BLUEPRINT.md: right now the phases live in README because that's what makes the project feel legible as a single idea. If broken out, the 90-second framework summary in README must still name Phase 1/2/3 and Mycelial Strategy — otherwise readers hit BLUEPRINT.md with no map.

### 5. "What Does Not Exist Yet" should be promoted

**Billy's critique.** Strongest part of README is buried. Move much higher. Order: what exists / what does not exist / what we're building next.

**Larry's response — hard agree, easiest win in the review.** Burying anti-hype is a tell that the project secretly wants to hype. Moving it up is the right call.

Suggested order:
1. What this is (3 sentences)
2. What exists today (numbers + directory)
3. **What does not exist yet** (promoted)
4. What we're trying to build next
5. Framework summary
6. Deep links

### 6. Power transfer needs a testability table

**Billy's critique.** Section is rhetorically strong but not testable. Needs table of "works best against / fails against / example target."

**Larry's response — right diagnosis, table needs a harder column.** "Fails against" in Billy's draft dodges the hardest cases. "Fails against land monopoly" for economic obsolescence is true, but also fails against *capital itself*. "Fails against authoritarian states" for democratic capture — yes, and also fails against captured democracies where mechanisms of capture are legal.

The honest version of this table has to name where the framework *doesn't have an answer*, not just where mechanism X happens to be weak. Add an **"Unsolved"** column that explicitly names what the framework cannot currently handle. That matches Commonweave's house style — the thing that makes CRITIQUE.md and "What Does Not Exist Yet" work is admitting limits. Power-transfer section should match that register.

### 7. Threat model

**Billy's critique.** Add THREAT-MODEL.md. Sections: assets, adversaries, attack surfaces, controls. Adversary list: grifters, foundations steering the agenda, state actors, entryists, spam/data poisoners, founder capture, fake orgs gaming the directory, AI-generated spam, corporate commons-washing.

**Larry's response — agree with a meaningful correction.** The adversary list is missing the most dangerous adversary Commonweave actually faces: **us**. Founder-capture is there, but "us" is broader — Simon unintentionally tilting the framework to validate priors, Larry optimizing directory enrichment for metrics that look good in heartbeats, aggregator scripts silently absorbing selection bias from which registries are cheap to scrape. Every one of these has already happened at least once. The US/UK 88% skew is the residue of exactly that kind of unintentional adversary-pressure.

Add to the model:

- **Maintainer drift** — priorities shift with Simon's attention. Countermeasure: pipeline_auditor.py's weekly read-only proposals, retirement rule for ignored proposals, explicit in-repo logging of what got deprioritized.
- **Pipeline bias** — legibility column was added for this exact reason. Should be named as a live countermeasure in the threat model, not just a data column.
- **AI-assisted churn** — Larry writes text Simon edits and ships. If Larry drifts from his voice or injects consensus-seeking softness, framework credibility degrades. Countermeasure: Simon reads everything, `[commonweave]` tag in daily memory creates paper trail.

Also: "State surveillance" should move out of "adversaries" into **accepted tradeoffs**. README already commits to functioning under surveillance as a design choice. Calling it an adversary implies a defense we're not building.

**Minimum THREAT-MODEL.md sections:**

```
1. Assets
2. Accepted tradeoffs (state surveillance, metadata leakage, public contributor targeting)
3. External adversaries (grifters, greenwashers, entryists, spam, harassers)
4. Internal adversaries (maintainer drift, pipeline bias, AI-assisted drift, founder capture)
5. Attack surfaces
6. Controls (matrix: each control → which adversaries it defends → residual risk)
7. Review cadence (quarterly, Simon signs off, logged in repo)
```

Control→adversary matrix is what turns the doc from "list of concerns" into something operational.

### 8. Open questions → work packages

**Billy's critique.** 13 unresolved questions listed. Good questions are useless unless they become work packages. Convert each to a table row with status, issue link, needed expertise.

**Larry's response — agree, small tweak.** Don't require GitHub issues for every row on day one. Issue-less rows should be valid as "unclaimed, unassigned." Demand for an issue per question will either (a) produce 13 empty issue stubs that never get touched, or (b) block the table from shipping until all issues are filed. Either way you lose.

Better columns:

| Question | Status | Needed expertise | Issue (if open) | Blocker |
|---|---|---|---|---|

"Blocker" is the important column. "What replaces prisons?" isn't blocked on expertise — it's blocked on *having an actual prison-abolition practitioner willing to co-author*. Naming that distinction turns the section into a recruiting tool.

### 9. Contribution section is too generic

**Billy's critique.** "Thinkers, historians, engineers, artists, organizers, skeptics" is welcoming but not actionable. A contributor should be able to pick one task in 60 seconds. Proposed: Good First Contributions grouped by Data / Research / Code / Design.

**Larry's response — fully agree, no modifications.** Ship as proposed. One addition:

```
### Directory verification (45 minutes)
Pick one country with <50 orgs. Open data/search/<country>.json.
Spot-check 10 orgs: website works, description matches framework area.
File a PR editing the JSON with your corrections + a note at the top.
```

Country-scoped tasks work because a contributor in Nairobi or Mexico City immediately sees a task where their local knowledge is the scarce resource, not ours.

---

## Map-level observations (README-based)

### Map problem 1 — too many dots without enough meaning

**Billy's critique.** 8,412 points is visually impressive but cognitively noisy. Default to meaning, not density: cluster by zoom, color by area, shape by tier, toggle edges off, high-confidence-only default, "why is this org here?" popup.

**Larry's response — agree with all of it.** Default to "high-confidence only" (Tier A/B + score ≥5) drops map from 8,412 to ~2,800 — still visually impressive, far less noisy, aligned with the confidence legend from §3.

### Map problem 2 — edges can imply relationships that aren't real

**Billy's critique.** 2,687 network edges is risky if inferred from shared keywords, geography, or weak metadata. Users may read as real collaboration. Proposed edge schema:

```json
{
  "source": "org_a",
  "target": "org_b",
  "edge_type": "same_network | shared_source | geographic_nearby | keyword_similarity | manually_verified_relationship",
  "confidence": 0.0-1.0,
  "explanation": "Both are tagged as community land trusts in the same metro area"
}
```

**Larry's response — agree, small addition.** Include `created_at` and `source_script` for audit trail:

```json
{
  "source": "org_a",
  "target": "org_b",
  "edge_type": "same_network | shared_source | geographic_nearby | keyword_similarity | manually_verified_relationship",
  "confidence": 0.0-1.0,
  "explanation": "Both are tagged as community land trusts in the same metro area",
  "created_at": "2026-04-23",
  "source_script": "data/build_edges.py"
}
```

That's the difference between "we inferred this" and "we can reproduce this inference six months from now when someone asks why."

Cheap first step: rename "edges" to "shared-area links" in UI. One-word fix, eliminates the implication of real collaboration.

### Map problem 3 — map needs narrative presets

**Billy's critique.** A big global map is cool for 10 seconds. Users then ask "what am I supposed to see?" Add guided views: Community land trusts in North America / Food sovereignty / Participatory democracy / Healthcare commons / Underrepresented regions / High-confidence only / Organizations with websites / Potential local allies near me.

**Larry's response — agree, single highest-leverage UX change.** Current map optimizes for "look how much data we have." Presets shift it to "look what this data can teach you."

Addition: a **"Start with the skeptic view"** preset showing *only* Tier A manually-verified orgs (~couple hundred points). That's the honest map. Other presets expand outward from there. Matches README's critique-first posture.

---

## Recommended README rewrite

### Billy's proposed top section

```markdown
# Commonweave

Commonweave is an open directory and map of organizations already building
pieces of a commons-based, ecological, democratic economy.

The directory is the product. The framework is the argument for why the
directory matters.

## Try it
- Search the directory: directory.html
- Explore the map: map.html
- Read the critique first: CRITIQUE.md
- Understand the data: DATA.md
- Contribute: CONTRIBUTING.md

## Current state: April 2026
Commonweave currently contains 24,508 candidate/aligned organizations across
60 countries. Of those:
- 10,067 are Tier A/B verified
- 8,412 have geocoded points
- 2,805 are high-confidence framework matches
- 88% of records currently come from US/UK registries

This is not yet a complete global map. It is an early, biased, auditable
dataset.

## What does not exist yet
- No Commonweave pilots
- No formal partnerships
- No legal entity
- No staff
- No claim that listed organizations endorse this project

## What we need next
- Better data outside the US/UK
- Stronger verification tiers
- Cleaner map UX
- More contributor-friendly tasks
- Research help on unresolved governance/economic questions
```

### Larry's edits

**(1) "Try it" needs priority ranking.** Most readers only click one thing.

```markdown
## Try it
- **Start here:** directory.html (search 24,508 orgs)
- See the map: map.html
- Skeptical? Read CRITIQUE.md first
- Data methodology: DATA.md
- Contribute: CONTRIBUTING.md
```

**(2) "What we need next" should name *who*, not *what*.** Current version reads like a todo list. Convert to a recruiting call:

```markdown
## What we need
- Researchers in LATAM, Africa, South/Southeast Asia — our data is 88% US/UK
- Anyone with domain expertise on unresolved questions (see Open Questions)
- Map/frontend contributors (edge provenance, clustering, mobile)
- Verifiers — 45 minutes per country can move the needle
```

That turns the section from feature list into a door people can walk through.

---

## Codex subagent prompt (for PR generation)

Billy's draft was solid. Three additions before sending to Codex:

- **Constraint 11:** "Preserve the `legibility` column data (formal/hybrid/informal/unknown) in the data-confidence summary — this is a self-reported bias signal, not an internal metric." Otherwise Codex will likely drop it.
- **Constraint 12:** "Do not invent new stats. All numbers must trace back to either `data/commonweave_directory.db` or existing doc files. If a number isn't findable, leave a `[NEEDS VERIFICATION]` marker."
- **Deliverable 4:** "A diff of what was moved to BLUEPRINT.md vs. what was summarized in place." Makes review tractable.

---

## Priority fixes — ranked by impact / effort

| Order | Fix | Why first | Effort |
|---|---|---|---|
| 1 | Promote "What does not exist yet" to top | Zero new writing, biggest honesty signal | 5 min |
| 2 | Confidence-aware phrasing on headline number | Rewording, not new work | 10 min |
| 3 | Good-first-contribution tasks | Unlocks contributors immediately | 30 min |
| 4 | Shorten README into entry point | Structural, biggest rewrite | 2–3 hrs |
| 5 | Resource governance matrix | High intellectual value, needs real thinking | 2–4 hrs |
| 6 | Map confidence defaults + edge types | Code change, not doc | 1 day |
| 7 | Issue-linked open questions | Needs issue triage first | 2 hrs |
| 8 | THREAT-MODEL.md | Important but not urgent | half day |
| 9 | Canonical domain decision | Cosmetic but annoying | 15 min |

Items 1, 2, 3, and 9 are all doable in one sitting (~45 minutes total) and produce most of the credibility lift. Rest is real work that shouldn't be rushed.

---

## Domain issue (canonical site)

Billy flagged that `comonweave.earth` returned 502. That domain isn't referenced anywhere in the README. Canonical site per README is `simonlpaige.com/commonweave/`.

**Action items:**

1. Register `commonweave.earth` defensively (available, cheap). Don't stand up a site — just hold the name.
2. Add to README: `Official site: simonlpaige.com/commonweave/`. Currently implicit from GitHub link-out; making explicit prevents confusion.

---

## Next pass

README-level review complete. Billy's next pass will be architecture + data files: DATA.md, DIRECTORY.md, META-DIRECTORY.md, MAP-BUILD-GUIDE.md, `data/`, and the database / search-index design.

**Nothing in the README file has been changed.** This is a review document only. Acting on the fixes is Simon's call, not Larry's.
