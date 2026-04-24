# Commonweave Threat Model

**Version:** 2026-04-23
**Review cadence:** Quarterly. Simon Paige signs off. Review logged in git as a commit to this file with the date and reviewer.
**Next scheduled review:** 2026-07-23

---

> This document tries to be honest about who would want to damage or subvert Commonweave, how they would do it, and what we have or don't have as countermeasures. If you are reading this because you want to attack the project, you are welcome. We'd rather you attacked us directly than discovered a gap we missed. If you find something we haven't addressed, file an issue or PR.

---

## 1. Assets

What does Commonweave have that is worth protecting?

| Asset | Description | Value |
|---|---|---|
| Directory integrity | 26,022 orgs filtered by alignment criteria; quality matters more than quantity | If orgs are fake, misclassified, or gamed in, the directory loses the property that makes it useful |
| Framework credibility | The theory of change is only as good as its intellectual honesty | Credibility is slow to build, fast to lose |
| Contributor trust | People putting their names (or pseudonyms) on contributions, often from politically exposed contexts | Trust is the actual resource; we don't have funding or staff to compensate for it |
| Simon's time and attention | One person currently drives most of the work | Attention is the binding constraint; anything that wastes it is a real cost |
| Larry's analytical output | AI-assisted research and writing shapes what gets into the framework | Subtle drift here degrades the framework without anyone noticing |
| Pipeline reproducibility | `data/commonweave_directory.db` + audit trail in `data/trim_audit/` | If we can't explain why an org is in or out, the directory is not auditable |

---

## 2. Accepted Tradeoffs

These are threats we have explicitly decided not to defend against, because the cost of defense is worse than the threat.

**State surveillance.** Open coordination makes it trivial for hostile governments to monitor and map the network. We accept this. A movement that requires secrecy to function is fragile; a movement that functions in plain sight and still works is resilient. Contributors in repressive contexts should use whatever operational security they personally need. The network supports that without judgment. We do not attempt to hide the network's existence or structure.

**Metadata leakage.** Every commit, issue, PR, and discussion exposes contributor activity patterns, locations (via IP/timezone inference), and social graphs. We accept this. The alternative is closed coordination, which creates hidden power and destroys accountability. Contributors who need to protect their metadata should use Tor or a VPN -- that's a personal choice, not a network requirement.

**Public contributor targeting.** Visible participation in a political project can attract harassment, professional consequences, or worse in some jurisdictions. We accept that this risk exists and cannot be eliminated. Countermeasures: pseudonymous contribution is explicitly supported and technically straightforward; the governance process treats pseudonymous contributors identically to named ones. We do not pressure anyone to be publicly identified.

---

## 3. External Adversaries

People or organizations outside the project who might try to damage it.

### 3.1 Grifters

**Profile:** Individuals or groups who want to extract value from the project's reputation or contributor network for personal or commercial gain. Common vectors: selling "Commonweave consulting," using the directory in commercial products without attribution, claiming affiliation to raise money.

**Countermeasure:** CC BY-SA 4.0 license requires attribution and share-alike. This is imperfect but creates legal ground. Alignment criteria in the directory are specific enough that "we use the Commonweave framework" without meeting them is falsifiable. Note in the obvious places that this project has no commercial affiliates and no authorized consultants.

**Residual risk:** Moderate. Licensing enforcement requires legal resources we don't have. Reputational damage from false affiliation claims is the most realistic harm.

### 3.2 Greenwashers

**Profile:** Corporations or institutions that want to list themselves in the directory to claim social legitimacy without meeting alignment criteria. Also includes organizations that meet criteria today but drift after inclusion.

**Countermeasure:** `pipeline_auditor.py` generates weekly proposals flagging orgs that may no longer meet alignment criteria. `staleness_check.py` flags orgs with stale data. Alignment score >= 5 filter provides a higher bar. Tier system makes data quality visible.

**Residual risk:** High. We don't have capacity for ongoing manual verification of all 26,022 orgs. The legibility column (formal/hybrid/informal/unknown) will help when backfilled -- it's designed to catch formal-sector actors claiming community legitimacy they don't have. Currently all 26,022 read 'unknown'; backfill is the gap.

### 3.3 Entryists

**Profile:** People who join the contributor network with intent to redirect the framework toward a specific political faction's goals (accelerationist, electoralist, insurrectionist, any single-issue group that wants to commandeer the broader framework). This is the "concerned ally who keeps raising concerns about insufficient radicalism" pattern.

**Countermeasure:** "Rough consensus and running code" -- working implementations outweigh theoretical objections. Contribution quality standards. Decision deadlines. No single contributor has veto power. The framework is evaluated on outcomes, not ideology.

**Residual risk:** Medium. Small active communities are disproportionately affected by motivated actors who show up consistently. The Mycelial Strategy's "concern trolling" countermeasure is named but not operationally enforced -- there is no formal moderation process yet.

### 3.4 Spam and AI-generated fake org submissions

**Profile:** Automated or semi-automated submission of fake, duplicate, or low-quality organizations to inflate directory size, poison search results, or stress the pipeline.

**Countermeasure:** `dedup_merge.py` handles duplicate detection. Multi-pass keyword scoring means random submissions are unlikely to pass alignment filters without targeted effort. Tier system means unreviewed submissions are Tier D and don't appear in high-confidence views.

**Residual risk:** Low-moderate for naive spam; Medium for targeted fake-org campaigns where someone deliberately creates organizations that score well. No mechanism currently exists to verify that a listed organization actually operates as described.

### 3.5 Harassers

**Profile:** Bad actors who target individual contributors -- coordinated harassment campaigns, doxxing, pressure on contributors' employers.

**Countermeasure:** Pseudonymous contribution is supported. We do not require real names or contact information. GitHub account is the only identity requirement, and those can be created pseudonymously. We have no centralized contributor contact database to breach.

**Residual risk:** High. A named author (Simon Paige) is a permanent target. Pseudonymous contributors are partially protected. There is no current response protocol if a contributor is targeted -- this should be added to GOVERNANCE.md.

---

## 4. Internal Adversaries

This section is load-bearing. The most dangerous adversaries are not hostile outsiders -- they are patterns of failure that emerge from inside the project without anyone intending harm.

### 4.1 Maintainer drift

**What it is:** Simon's priorities shift with his attention, life circumstances, and what's interesting this week. Proposals from `pipeline_auditor.py` accumulate unreviewed. Issues sit open. The framework slowly ossifies into whatever happened to be worked on last, not what matters most.

**Evidence it has already happened:** The US/UK 88% geographic skew is partly a product of which registries were cheap and easy to scrape. That was a reasonable early decision. It became a structural bias when enrichment work concentrated on the same registries.

**Countermeasures:** `pipeline_auditor.py` generates weekly read-only proposals that Simon reviews; any proposal ignored for 30 days gets logged as deprioritized in `data/audit_log/`. The `[commonweave]` tag in Simon's daily memory creates a paper trail of what got deprioritized and why. Explicit retirement rule for proposals ignored past threshold.

**Residual risk:** High. One-person projects drift toward the maintainer's attention. This is documented, not solved.

### 4.2 Pipeline bias

**What it is:** The aggregator scripts absorb selection bias from which registries are cheap to scrape, which registries exist, and which keywords the scorer was trained to prefer. The directory reflects what's legible to English-language formal-sector data sources, not what actually exists.

**Evidence it has already happened:** ~83% of records come from US/UK registries. 26,022 orgs with `legibility='unknown'` because the column was added after the pipeline ran but before backfill. Healthcare and education dominate the framework area breakdown partly because those are the most common nonprofit categories in US/UK registries.

**Countermeasures:** `legibility` column (formal/hybrid/informal/unknown) was added 2026-04-22 specifically to flag this. When backfilled, it will surface whether the directory is overweighted toward formal-sector orgs at the expense of informal mutual aid and hybrid structures. `pipeline_auditor.py` tracks geographic distribution. Regional directory files (`data/regional/`) as enrichment targets for non-US/UK coverage.

**Residual risk:** High. Legibility backfill is pending. Geographic enrichment is manual and slow. This is the dominant data quality problem.

### 4.3 AI-assisted drift

**What it is:** Larry (the planning AI) writes text that Simon edits and ships. If Larry drifts from the project's register -- becomes more consensus-seeking, softer on hard questions, more likely to hedge -- the framework's credibility degrades without anyone noticing. The voice reads like a think-tank report rather than an honest engineering problem.

**Evidence it has happened at least once:** Early framework drafts were softer on power transfer and more optimistic about voluntary participation. Simon corrected this; the correction is logged in daily memory.

**Countermeasures:** Simon reads everything before it ships. The `[commonweave]` tag in daily memory creates a paper trail. The framework's Feynman-voice requirement ("simple language, concrete examples, no jargon that obscures rather than clarifies") is a signal: if text sounds like it's performing rigor rather than practicing it, something has gone wrong.

**Residual risk:** Moderate. Gradual drift is hard to notice. The paper trail helps but doesn't fully solve it.

### 4.4 Founder capture

**What it is:** The framework gradually becomes a vehicle for Simon's specific views rather than a genuinely open project. This can happen without bad intent -- the maintainer's aesthetic, political instincts, and blind spots become the framework's unexamined defaults.

**Evidence it has happened at least once:** The framework's nonviolence commitment is stated without a comparative analysis of historical cases where nonviolence failed to achieve transition. That's a founder aesthetic choice being passed off as a principled conclusion.

**Countermeasures:** CRITIQUE.md is the primary countermeasure -- it invites external criticism before internal consensus hardens. Pull requests are the revision mechanism. The explicit invitation in README for skeptics to sharpen rather than discover the case against this project. Governance structure in GOVERNANCE.md (review in progress).

**Residual risk:** High. The maintainer still makes all final decisions. The governance structure that would distribute that is in GOVERNANCE.md but not operationally complete.

---

## 5. Attack Surfaces

Where would an adversary actually apply pressure?

| Surface | Description | Current state |
|---|---|---|
| Directory content | Submitting fake orgs; gaming alignment scores; poisoning the search index | Partially defended by pipeline filters and dedup; vulnerable to targeted attacks |
| GitHub repository | Issues, PRs, Discussions as vectors for entryism, spam, harassment | No formal moderation process; Simon is the only moderator |
| Framework text | PRs that subtly shift framework positions; edits that introduce policy capture | Simon reviews all changes; no secondary reviewer |
| Larry's outputs | AI-assisted text that drifts from project voice or positions | Daily memory paper trail; Simon reads everything |
| Simon's attention | Burnout, distraction, or loss of interest by the sole maintainer | Named risk; no succession plan yet |
| External reputation | False affiliation claims; grifters using the directory name | CC BY-SA gives some leverage; no enforcement capacity |

---

## 6. Controls

| Control | Adversaries it defends against | Residual risk |
|---|---|---|
| `pipeline_auditor.py` weekly read-only proposals | Greenwashers, pipeline bias, maintainer drift | Proposals still require human review; can be ignored |
| `staleness_check.py` | Greenwashers, drift in org status | Doesn't verify actual operations, only data freshness |
| `dedup_merge.py` | Spam, data poisoning | Targeted fake-org campaigns with unique names will bypass |
| `legibility` column (backfill pending) | Pipeline bias, greenwashers | Not operational until backfilled |
| Multi-pass keyword alignment scoring | Spam, AI-generated fake orgs | Sophisticated targeted submissions can score well |
| Tier system (A/B/C/D) | Greenwashers, spam | Tier D orgs still in the database; display filter only |
| CC BY-SA 4.0 license | Grifters, misattribution | No enforcement capacity |
| Pseudonymous contribution | Harassers | Doesn't protect named maintainer |
| CRITIQUE.md | Founder capture, framework drift | Countermeasure only works if critics actually engage |
| Simon reads all changes | AI-assisted drift, entryism | Single point of failure on maintainer attention |
| `[commonweave]` daily memory tag | Maintainer drift, AI-assisted drift | Paper trail, not a prevention mechanism |
| Pull request review process | Entryism, framework drift | Currently no secondary reviewer; informal |

---

## 7. Review Cadence

This document is reviewed quarterly. Simon Paige signs off on each review. Review is logged as a git commit to this file with the date, reviewer, and a brief note on what changed or was confirmed.

| Review date | Reviewer | Notes |
|---|---|---|
| 2026-04-23 | Simon Paige / Claude Sonnet 4.6 | Initial version |

**What a review covers:**
- Has anything in the threat landscape changed since last review?
- Have any controls lapsed or been superseded?
- Has the "Internal adversaries" section been honestly updated with any new evidence of drift?
- Are the residual risk ratings still accurate?
- Is the next review date logged?
