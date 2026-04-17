# Ecolibrium: Directory and Framework for the Post-Labor Economy

> **Skeptics start here:** [CRITIQUE.md](CRITIQUE.md) is a section-by-section honest audit of where this framework is weak, magical, or incomplete. It's linked first on purpose. If you're looking for the case against this project, it's already written, and we'd rather you sharpened it than discovered it.

---

## The Idea

Ecolibrium is two things: (1) an open directory of the existing transition network across 60 countries, and (2) a working framework explaining why that network matters and how it composes into a post-labor economy.

The directory is the concrete deliverable. The framework is the argument for it.

Here is a thing that is true and that almost no one talks about clearly: the machines are going to do most of the work. Not eventually -- now, and accelerating. The interesting question isn't whether that happens. It's who benefits when it does.

Right now the answer is: whoever owns the machines. That's a design choice, not a law of nature. You could design it differently.

The directory catalogs who is already designing it differently: cooperatives, community land trusts, mutual aid networks, open-source health platforms, participatory governance experiments, community energy grids -- 24,508 aligned organizations across 60 countries, filtered from ~760K public registry records through multi-pass keyword scoring against the framework's mechanisms. The framework maps how those pieces fit together and what's still missing.

It's not a manifesto. It's more like an engineering problem with a lot of political and historical constraints. The goal is to figure out what needs to be true for people to have food, shelter, healthcare, and a say in their own lives -- and then figure out how to make those things true.

### Selective Abundance, Not Post-Scarcity

This framework does not assume post-scarcity arrives as a binary switch. Some goods are becoming radically cheaper to produce: information, energy, basic nutrition, digital services. Other goods remain genuinely scarce: land, fresh water, skilled human care, rare materials, attention. The honest framing is *selective abundance* -- a world where the challenge is distributing what's abundant while governing what's scarce.

Different categories of goods require different governance mechanisms:
- **Trending toward abundance** (energy, information, basic food production): commons-based distribution, universal access
- **Persistently scarce** (land, water, rare minerals, skilled care): democratic allocation, stewardship models, Ostrom-style commons governance with monitoring and graduated sanctions
- **Attention and meaning** (the scarcities automation creates): these require cultural and institutional responses, not just economic ones

The framework is designed to work under conditions of *partial* abundance and *persistent* scarcity -- not to wait for a threshold that may never fully arrive.

Some of this is worked out in detail. A lot of it isn't. The parts that aren't worked out are listed as open questions, which is honest. If you know something we don't, that's what the pull requests are for.

---

## What Exists Today

This section matches ambition to evidence. Here is the concrete state of the project as of April 2026.

### The Directory

The primary deliverable is a searchable database of organizations working in the framework's 10 areas. Numbers from `data/ecolibrium_directory.db` after the April 2026 alignment trim:

- **24,508 aligned organizations** across **60 countries**
- **8,412 geocoded points** visible on the interactive map, with **2,687 network edges** connecting related organizations
- **Sources:** UK Charity Commission (11,537), IRS Exempt Organizations BMF (9,402), Wikidata (2,894), ProPublica (604), web research (58), manual curation (13)
- **Search interface:** per-country JSON index at `data/search/`, browsable at `directory.html`
- **Interactive map:** network visualization at `map.html`
- **Framework area breakdown:** healthcare (6,369), education (5,694), food (2,955), democracy (2,863), housing & land (2,406), ecology (2,346), conflict resolution (910), cooperatives (656), recreation & arts (269), energy & digital (40)

Honest breakdown of what 24,508 records means:

- **11,737 entries (48%)** have a real description (>50 characters)
- **10,262 entries (42%)** have a website
- **10,067 entries (41%)** are verified (Tier A or B)
- **2,805 entries (11%)** score >=5 on framework alignment -- the strongest keyword matches (community land trust, worker cooperative, mutual aid, food sovereignty, restorative justice)
- **Geographic skew:** 88% of records come from US and UK open registries (21,559). The remaining 58 countries hold 2,949 organizations between them. Closing that gap is the main enrichment target.

The earlier 738K figure counted every non-removed row including 431K entries flagged as excluded by prior audit passes. The current 24,508 reflects what actually passed alignment scoring. The excluded rows are preserved as CSVs in `data/trim_audit/` for transparency and reversibility.

### The Framework

This README is the framework document. Its current maturity:

- **Draft.** The core thesis, three-phase structure, and Mycelial Strategy are written and internally consistent. Core tensions are documented. Open questions are flagged as open.
- **Critique-first.** [CRITIQUE.md](CRITIQUE.md) is a section-by-section honest audit of where the framework is weak or incomplete. It exists because the failure modes should be on the table before anyone commits to this.
- **Open.** Every claim is either citable or flagged as speculative. Pull requests are the revision mechanism.

### What Does Not Exist Yet

To be specific:

- **No running pilots under the Ecolibrium banner.** Organizations in the directory operate independently. None are affiliated with or funded by this project.
- **No collaboration agreements with Tier 1 allied projects.** The outreach plan is in [OUTREACH.md](OUTREACH.md). The conversations have not happened yet.
- **No named legal entity.** There is no Ecolibrium Foundation, LLC, or unincorporated association. This is a repository and a framework document.
- **No staff.** This is an open-source project.

---

## Core Principles

These are the load-bearing walls. Everything else is details.

1. **Universal Sufficiency** -- Every person has an unconditional right to food, shelter, healthcare, education, and meaningful participation in society.
2. **Ecological Equilibrium** -- No economic activity may degrade the systems that sustain life. The economy operates within planetary boundaries.
3. **Democratic Sovereignty** -- Power flows from people, not capital. Decisions are made by those affected by them.
4. **Common Ownership of the Commons** -- Land, water, air, energy, data, and infrastructure belong to everyone. They cannot be privately hoarded.
5. **Voluntary Contribution** -- Work is not coerced. People contribute because they find meaning, not because survival depends on it.
6. **Non-Violence** -- The transition happens through preparation, legitimacy, and collective action -- not force.
7. **Transparency by Default** -- Systems of governance and resource allocation operate in the open. "By default" does work here, and the exceptions matter: individual medical records, whistleblower and dissident protection, survivors of domestic violence, children's data, and contributors operating under authoritarian regimes. Transparency applies to *power and resources*, not to *people made vulnerable by visibility*. The failure mode of "radical transparency" is surveillance dressed as accountability; the framework rejects that trade. See the Mycelial Strategy's failure-mode subsection for operational detail.

These principles are in tension with each other. That's not a bug. See [Tensions and Tradeoffs](#tensions-and-tradeoffs) below.

---

## The Framework

### A Note on Sequencing

The framework below is organized as Phase 1/2/3 for readability, but this is misleading if read as a strict timeline. Many Phase 1 prerequisites (land transition, cooperative economics) depend on Phase 3 outcomes (values transformation). The phases are better understood as *parallel tracks with dependencies* that co-evolve, not a linear sequence. Systems-building, power transfer, and cultural change happen simultaneously at different speeds in different places.

The Mycelial Strategy (below) is not a phase - it is the connective tissue that operates across all phases at all times.

### Phase 1: Pre-Transfer -- Systems That Must Exist Before the Transition

The transfer of power to a better system can only happen if a better system is ready to receive it. History is full of examples of what happens when the old system collapses before the new one is operational. It's not pretty.

So: before the transfer, these systems need to exist and be demonstrably working, even if only at small scale. Think of it as load testing before launch.

#### 1.1 Democratic Infrastructure

- [ ] **Uncompromising voting systems** - local, regional, and worldwide
  - Verifiable, transparent, tamper-resistant (not just electronic - auditable)
  - Liquid democracy options: direct vote or delegate to trusted representatives per issue
  - Constitutional protections against tyranny of the majority
  - Mandatory inclusion mechanisms for marginalized voices
  - Recall and accountability mechanisms built into every elected role
- [ ] **Removal of cults of personality from politics**
  - Structural limits on individual political power (term limits, rotation, sortition)
  - Ban on political advertising and personal branding in governance
  - Decision-making by council and consensus, not charismatic authority
  - Separation of celebrity and governance - cooling-off periods between high-profile fame-driven roles and elected office, with the specific period, definition of "public figure," and enforcement mechanism delegated to constitutional design rather than asserted here. (Open problem: this clause has obvious free-speech and definitional risks; it belongs in a constitutional-safeguards working group, not a principles list.)
- [ ] **Conflict resolution systems**
  - Restorative justice replacing punitive justice
  - Community mediation infrastructure
  - International arbitration frameworks

#### 1.2 Resource Distribution Systems

- [ ] **Food distribution**
  - Local and regional food sovereignty - communities control their food supply
  - Vertical farming, permaculture, and regenerative agriculture at scale
  - Elimination of food waste through smart logistics and community kitchens
  - Universal free access to nutritious food
  - Preservation of food cultures and culinary traditions
- [ ] **Healthcare**
  - Universal, free-at-point-of-use healthcare for all
  - Preventive care prioritized over reactive treatment
  - Mental health fully integrated - not an afterthought
  - Community health workers embedded in every neighborhood
  - Open-source medical research - no patents on life-saving treatments
  - Care work (childcare, eldercare, disability support) recognized and valued as essential
- [ ] **Education**
  - Lifelong, free, universally accessible education
  - Not job training - genuine cultivation of critical thinking, creativity, and civic participation
  - Decentralized: community-led, culturally responsive, multilingual
  - Emphasis on ecological literacy, systems thinking, and emotional intelligence
  - Open-source curricula, collaboratively developed
- [ ] **Housing**
  - Shelter as a right, not a commodity
  - Transition from private land ownership to stewardship models (community land trusts, usufruct)
  - Ecological building standards - every structure contributes to the ecosystem
  - No homelessness. Period.

#### 1.3 Economic Transition Mechanisms

> *Each proposal below must be evaluated on three dimensions: cost at scale, funding mechanism, and who bears the transition cost. Without those numbers, this is a wish list. Some numbers are included here; full analysis belongs in a dedicated ECONOMICS.md.*

- [ ] **Wealth distribution**
  - Gradual wealth caps and redistribution schedules
    - *Scale challenge: Enforcement requires international coordination to prevent capital flight. Existing precedents: Norway's sovereign wealth fund, Switzerland's wealth tax. No country has implemented hard caps.*
  - Universal Basic Income (UBI) as a bridge mechanism during transition
    - *Scale: US at $1,000/month = ~$4 trillion/year (roughly the entire federal budget). Proposed funding mechanisms that partially close the gap: land value tax (~$1.7T potential), carbon tax (~$200B), financial transaction tax (~$75B), automation dividend, sovereign wealth funds. This does not fully add up at current scale - UBI requires selective abundance to reduce costs simultaneously. See 100+ pilot results at guaranteedincome.us.*
  - Cooperative and mutual ownership replacing corporate structures
    - *Existing models: Mondragon (80,000 worker-owners, $12B+ revenue - but also Fagor's 2013 bankruptcy and increasing reliance on non-member temps). Italy's Marcora Law provides low-interest loans for worker buyouts. These work at specific scales; the transition path for a 100,000-employee global supply chain is unsolved.*
  - Community wealth funds - regional pools of shared resources
  - Debt jubilee - cancellation of unjust debts (medical, student, developing-nation)
    - *Scale: US student debt ~$1.7T, medical debt ~$220B, developing-nation debt ~$300B. Jubilee cost falls on whoever holds the debt as an asset - including pension funds, retirement accounts, and banks with depositors. A jubilee without a plan for downstream losses is a wealth transfer from some regular people to other regular people. Requires careful sequencing.*
- [ ] **Disassembly of private land ownership**
  - Phased transition: private ownership → long-term stewardship leases → full commons
    - *Scale: US residential real estate alone is worth ~$45 trillion. "Inviting" transition requires either compensation at market value (requires a funding source that doesn't exist) or a values transformation that makes land ownership feel unnecessary (Phase 3, creating a circular dependency with Phase 1). Honest path: start with public/abandoned/tax-delinquent land, scale CLTs, build proof over decades.*
  - Community Land Trusts as the primary mechanism
    - *Current reality: ~300 CLTs in the US managing a tiny fraction of total land. Real, working, and growing - but scaling from "affordable housing tool" to "all land is commons" is a civilizational transformation, not an incremental step. The framework should be honest about this timeline.*
  - Indigenous land return as a foundational act of justice
  - Ecological land-use planning replaces market-driven development
- [ ] **Deletion of unjust power**
  - Corporate charters revoked for entities acting against the public interest
  - Lobbying and political bribery criminalized
  - Monopolies dissolved - especially in energy, media, tech, and agriculture
  - Tax havens and offshore wealth structures dismantled through international cooperation
    - *Reality check: Tax havens exist because nation-states benefit from them. Dismantling requires the cooperation of the very states that profit from the status quo. Incremental progress: OECD global minimum tax (15%), automatic information exchange agreements. Full dismantlement requires political leverage that doesn't currently exist.*
  - Transparent asset registries - no hidden wealth

#### 1.4 Energy and Infrastructure

- [ ] **Energy sovereignty**
  - 100% renewable, community-owned energy grids
  - Decentralized generation (solar, wind, geothermal at household and community scale)
  - Energy as a public utility, not a commodity
- [ ] **Digital commons**
  - Internet as a public utility - free, universal access
  - Data sovereignty - personal data belongs to individuals, collective data to communities
  - Open-source everything: software, hardware designs, research
  - AI governance - algorithms that affect lives are publicly auditable
- [ ] **Transportation**
  - Free public transit
  - Shared vehicle networks replacing private car ownership
  - Walkable, bikeable communities by design

---

### The Network of Trust -- The Mycelial Strategy

In 2007, a researcher named Paul Hawken published a book arguing that the world's largest social movement already existed -- millions of organizations working on environmental sustainability, social justice, and indigenous rights -- and that nobody had noticed because it had no name, no leader, and no central organization. He called it "blessed unrest." Then he and his colleagues built a website called WiserEarth and catalogued 114,994 of those organizations across 243 countries.

Then the funding ran out and the whole thing disappeared in a weekend. That was 2014.

The lesson isn't that the idea was wrong. The lesson is about infrastructure. But the deeper lesson is one the framework must be honest about: **most people don't want to run infrastructure.** WiserEarth's code was released as open source when it shut down. Nobody self-hosted it. Every federated protocol - email, XMPP, ActivityPub - eventually concentrates around a few large nodes because running your own server is hard and most people don't care enough to do it.

The strategy here is similar to Hawken's original idea, with both infrastructure problems taken seriously: the technical one (don't depend on a single server) and the social one (don't depend on everyone running their own). The realistic model is decentralized in *governance* but may be centralized in *operations* - like the Wikimedia Foundation (one organization, one infrastructure, community governance) or the Apache Foundation (umbrella organization, multiple projects, shared infrastructure). These aren't as ideologically pure as full federation, but they actually work.

The approach is **mycelial**: a distributed network of people and organizations building working alternatives to the systems that don't work -- not arguing about theory, but running pilots, writing code, keeping books, growing food, running clinics. When the conditions are right, the network doesn't seize power. It just already has the replacement ready.

#### How the Network Works

- **Distributed, not leaderless.** The network is a web of trust, not a hierarchy. No single node can be removed to collapse it. But "leaderless" is a myth - Jo Freeman documented in 1972 that refusing to formalize leadership just creates informal leadership without accountability. The network has leaders: they are the people doing the work, making decisions, and maintaining systems. The goal is to make that leadership visible, accountable, and replaceable - not to pretend it doesn't exist. See [GOVERNANCE.md](GOVERNANCE.md).
- **Trust is built through contribution.** You join by doing the work -- building systems, running pilots, sharing knowledge. Trust is earned, not granted.
- **Radical transparency.** This is not a conspiracy. The framework is open-source. The pilots are public. The strategy is visible. Anyone, including opponents, can read every word. If the idea can't survive being seen, it doesn't deserve to succeed.
- **Named author, pseudonymous contributors welcome.** This project is authored and maintained by Simon Paige (simonlpaige/ecolibrium on GitHub). Earlier drafts experimented with framing the project as "anonymous by design." That framing was a mistake: established organizations will not collaborate with anonymous accounts - it looks indistinguishable from a troll or sock puppet - and pretending otherwise while the repository sits under a named account is worse than either choice. The correction: the author is named, the reasoning is on record, contributors may still work under any pseudonym they want as personal protection. The governance process is transparent either way. See [GOVERNANCE.md](GOVERNANCE.md) for the current accountability structure.
- **Operate inside and outside institutions simultaneously.** Some contributors work within governments, hospitals, universities, and corporations -- not to subvert them, but to understand them and prepare them for transformation. Others build parallel structures outside. All of this happens in the open.
- **Demonstrate, don't argue.** The network's primary pre-transfer activity is running proof-of-concept systems at local scale: community energy grids, cooperative businesses, participatory budgets, mutual aid networks, open-source health clinics. When the moment arrives, scaling up is not a leap of faith -- it's expanding what already works.

#### Principles of Network Growth

1. **Invite, never recruit.** People join because they see the work and want to contribute. Persuasion is unnecessary when the results speak.
2. **Open by default.** All coordination, planning, and strategy happens in the open. No inner circles. No secret channels. If someone needs to whisper, something has gone wrong.
3. **Cultural adaptation.** The framework is universal but its expression is local. A community in Kerala and a community in Detroit will implement differently -- and that's the point.
4. **No purity tests.** People arrive from different political traditions, spiritual backgrounds, and life experiences. The framework is evaluated on outcomes, not ideology.
5. **Resilience through redundancy -- where realistic.** Critical functions should not have single points of failure. Where full federation is feasible (knowledge, training materials, local governance), pursue it. Where it isn't (complex infrastructure, databases, hosting), use community-governed shared infrastructure with transparent operations and contingency plans. Ideological purity about decentralization is less important than systems that actually survive.
6. **The framework protects itself primarily through transparency -- but transparency is not a complete security model.** Co-option is harder when everything is visible. Infiltration is less effective when there is nothing hidden to discover. But openness has known failure modes that must be actively managed:
   - **Flooding and noise:** Bad actors can overwhelm discussion to dilute signal. *Countermeasure: moderation policies, contribution quality standards, rough consensus decision-making with clear timelines.*
   - **Concern trolling:** Using the open process to slow-walk decisions to death. *Countermeasure: decision deadlines, "rough consensus and running code" -- working implementations outweigh theoretical objections.*
   - **Strategic co-option:** Aligning publicly with the movement while redirecting its resources toward industry-friendly goals (see: corporate greenwashing). *Countermeasure: clear alignment criteria, willingness to refuse partnerships that don't meet them, outcome-based evaluation.*
   - **Harassment of contributors:** Visible participation makes contributors targets. *Countermeasure: contributor pseudonymity is supported as protection, not ideology. People may contribute under any identity.*
   - **State surveillance:** Open coordination makes it trivial for hostile governments to monitor and map the network. *The framework accepts this tradeoff.* A movement that requires secrecy to function is fragile. A movement that functions in plain sight and still works is resilient. But contributors operating in repressive contexts should use whatever operational security they need, and the network should support that without judgment.

#### What the Network Builds Before the Transfer

- Working prototypes of every Phase 1 system (even at small scale)
- Relationships of trust across borders, cultures, and institutions
- A shared technical infrastructure (open-source, federated, encrypted)
- Training and education programs that anyone can access
- A body of evidence: data showing the systems work

---

### Theory of Power Transfer

The framework requires an honest answer to the hardest question: *why would those with power give it up?*

The honest answer is: most won't. Not voluntarily. Power does not become "irrelevant" because better alternatives exist. The history of fossil fuels, tobacco, feudal land tenure, and colonial governance shows that entrenched power fights to preserve itself long after superior alternatives are available. A billionaire is not going to voluntarily become a regular participant in a commons because you offered them dignity.

So the framework relies on multiple mechanisms, in order of realism:

1. **Economic obsolescence.** Some forms of power genuinely do erode when technology changes. Newspaper classified ad revenue, taxi medallions, music label distribution monopolies -- these were power bases that technology made irrelevant whether the holders liked it or not. The framework identifies which current power structures are vulnerable to technological displacement and prioritizes building alternatives there first.

2. **Democratic capture in reverse.** Electing people committed to commons-based policy into existing democratic structures. This is already happening: participatory budgeting in 7,000+ cities worldwide, community wealth building in Preston and Cleveland, state-level cooperative development legislation. Slow, boring, effective.

3. **Coalition pressure.** Labor movements, consumer boycotts, shareholder activism, divestment campaigns -- actual mechanisms of power redistribution that have worked historically. The anti-apartheid divestment movement, the marriage equality campaign, the tobacco settlement -- none of these waited for the powerful to see the light. They applied pressure until the cost of resistance exceeded the cost of change.

4. **Parallel institution-building.** When the alternative is good enough, migration happens. Email didn't ask the postal service for permission. Wikipedia didn't negotiate with Encyclopaedia Britannica. When commons-based alternatives are demonstrably better, people switch -- and the old system's revenue base erodes whether it consents or not.

5. **Nonviolent non-cooperation.** When power refuses to yield despite all of the above, the framework explicitly supports strikes, tax resistance, non-cooperation, and civil disobedience. The framework is nonviolent. It is not passive.

**What the framework does NOT assume:** That power holders will voluntarily step aside. That dignity of exit will be sufficient motivation. That the transition will be smooth or painless. Some power will have to be taken, even if the taking is nonviolent. The framework must be honest about that.

---

### Phase 2: The Transfer

Not a revolution -- a migration. But a migration that some will resist.

The transfer is not a single event. It is a phase shift. The conditions accumulate gradually and the transformation appears sudden -- which is how most phase transitions work. You heat water for a long time and then it boils.

1. **Selective abundance crosses key thresholds.** Automation, AI, and renewable energy make specific necessities dramatically cheaper -- not universally free, but cheap enough that the old economy's logic starts breaking in visible ways. Energy, information, and basic food production lead. Housing, care, and land follow on different timelines.
2. **The network activates.** Prepared systems go live at scale. What was a local pilot becomes regional infrastructure. What was a prototype becomes the default.
3. **Institutions transform from within and under pressure.** People inside governments, corporations, hospitals, and schools -- who have been part of the network or who simply see that the new way works -- begin redirecting their institutions toward the new systems. Where institutions resist, coalition pressure, democratic processes, and nonviolent non-cooperation provide the force that goodwill alone cannot.
4. **The old system loses its base.** Some structures become unnecessary and are absorbed into new democratic frameworks. Others are actively dismantled through democratic processes. Others resist and are bypassed. Not all transitions are graceful.

#### What Makes Peaceful Transfer Possible

- The new systems are already working and visibly better -- proof, not promises
- A critical mass of people understand and support the transition
- Multiple pressure mechanisms operate simultaneously: economic, democratic, social, cultural
- International solidarity prevents external sabotage -- the network is worldwide
- No one loses access to necessities during the transition -- the old and new systems overlap
- Those who held power are offered dignified reintegration -- but the transition does not depend on their acceptance

---

### Phase 3: Post-Transfer - Governance Maintenance

> *Phase 3 is not "what the good world looks like" - everyone can imagine that. Phase 3 is "what prevents the good world from sliding back into the bad one." History shows that every democratic gain, every commons, every cooperative structure is under constant pressure from power reconcentration, democratic backsliding, ecological overshoot, and free-rider erosion. Phase 3 is the immune system.*

#### 3.1 Measurement Infrastructure - What Replaces GDP

You can't maintain what you can't measure. The transition from growth-based metrics to wellbeing-based metrics is not aspirational - it's already happening, and the framework should treat existing implementations as Phase 1 pilots to scale.

- [ ] **Beyond-GDP national accounting** (operational precedents exist)
  - *Bhutan's GNH Commission* has screened all policy proposals against 9 domains of happiness metrics since 2008. Population 780K, top-down introduction by the king - genuine experiment, uncertain replicability to large diverse democracies.
  - *New Zealand's Wellbeing Budget* (2019) - first national budget organized around wellbeing outcomes rather than GDP growth. Uses 12 domains of wellbeing from the NZ Treasury's Living Standards Framework. This is the most replicable model.
  - *WEGo partnership* (Scotland, Iceland, New Zealand, Wales, Finland, Canada) - six governments formally committed to moving beyond GDP. The OECD Better Life Index provides comparative data across 40 countries.
  - *Doughnut Economics* (Kate Raworth / Amsterdam, 2020) - city-level framework balancing social foundation (12 minimum standards) against ecological ceiling (9 planetary boundaries). Amsterdam adopted it as official policy framework.
  - **The framework's position:** Wellbeing measurement is not a Phase 3 aspiration. It is a Phase 1 deployment. Adopt the NZ/WEGo model at every governance level the network touches. Measure: life satisfaction, health outcomes, educational access, social connection, ecological footprint, housing security, democratic participation, time sovereignty (hours not spent in coerced labor).
  - **Open problem:** Who controls the measurement apparatus? Metrics shape behavior. If the wellbeing index is designed by economists, it will reflect economic assumptions. If designed by psychologists, psychological ones. The design of the measurement system is itself a governance problem requiring democratic input.

#### 3.2 Anti-Backsliding Mechanisms - Democratic Immune System

Every post-revolutionary, post-transition, and post-reform society faces the same threat: power reconcentration. The wealthy find new ways to accumulate. Politicians find new ways to entrench. Corporations find new ways to capture regulators. The framework needs specific countermeasures, not just "safeguards against re-concentration of power."

- [ ] **Constitutional sunset and renewal**
  - *Ireland's Citizens' Assembly model* - periodic assemblies of randomly selected citizens review constitutional provisions and recommend changes. Ireland used this to resolve abortion and marriage equality - issues that elected politicians couldn't touch. The mechanism is: sortition (random selection), structured deliberation, expert testimony, binding referendum.
  - **Proposed mechanism:** Constitutional review assemblies every 10 years, with mandatory review of: wealth distribution trends, ecological boundary compliance, democratic participation rates, and power concentration metrics. If any metric has deteriorated beyond a defined threshold, the assembly has binding authority to propose corrective constitutional amendments.
  - **Open problem:** Constitutional stability vs. adaptability. Too-frequent revision creates uncertainty. Too-infrequent revision allows drift. 10 years is a guess.

- [ ] **Power concentration detection**
  - Real-time monitoring of wealth concentration (Gini coefficient, wealth share of top 1%/0.1%), corporate consolidation (HHI index by sector), media ownership concentration, political donation patterns, and revolving-door metrics (officials moving to industries they regulated).
  - **Proposed mechanism:** An independent statistical authority (modeled on central bank independence but for inequality data) that publishes quarterly power concentration reports. When any metric crosses a predefined threshold, it triggers automatic democratic review - not automatic action, but mandatory public deliberation.
  - *Precedent: Estonia's e-governance* - transparent digital infrastructure that makes government operations auditable in real time. If you can make tax collection transparent, you can make power concentration transparent.

- [ ] **Anti-capture mechanisms**
  - Cooling-off periods between public office and private sector (minimum 5 years)
  - Asset transparency requirements for all governance participants
  - Sortition for oversight bodies - randomly selected citizens are harder to capture than elected officials who need campaign funding
  - *Precedent: Uruguay's electoral system* - considered one of the most robust in the Americas, with mandatory voting, independent electoral court, and strong party finance regulations. Democratic backsliding has not occurred despite regional trends.

#### 3.3 Adaptive Governance - How the Framework Changes Itself

The most dangerous thing a framework can become is sacred. The moment people defend the framework because it's *the framework* rather than because it's *working*, it has become the rigid ideology it sought to replace.

- [ ] **Built-in self-revision**
  - The framework must contain explicit mechanisms for its own modification, including modification of its core principles.
  - **Proposed mechanism:** Any core principle can be amended through a three-stage process: (1) public proposal with evidence that the principle is producing harmful outcomes, (2) citizens' assembly deliberation with structured pro/con testimony, (3) supermajority ratification (67%+). This is deliberately hard but deliberately possible.
  - **Open problem:** Who decides what counts as "harmful outcomes"? This is recursive - the measurement infrastructure (3.1) and the governance system are evaluating each other. There is no neutral ground. The best available answer is: make the evaluation criteria themselves subject to democratic revision.

- [ ] **Multi-horizon governance**
  - *Short-term (1-5 years):* Elected/sortition-selected bodies handle operational governance. Standard democratic accountability.
  - *Medium-term (5-50 years):* Dedicated futures bodies (modeled on Finland's Parliamentary Committee for the Future or Wales's Future Generations Commissioner) with legal authority to block policies that sacrifice long-term wellbeing for short-term gain.
  - *Long-term (50-500+ years):* Ecological governance. Planetary boundaries are not subject to democratic override (see Tensions and Tradeoffs below). Scientific bodies with democratic accountability but insulation from electoral pressure monitor and enforce ecological limits.
  - *Precedent: The Iroquois Confederacy's* seventh-generation principle - decisions evaluated for their impact seven generations out (~175 years). This is often cited as aspirational; the operational question is how to institutionalize it.

- [ ] **Nested governance at scale (Ostrom's Principle 8)**
  - Local communities govern local resources with full autonomy within shared principles.
  - Regional federations coordinate between communities, manage shared infrastructure, resolve inter-community disputes.
  - Global coordination handles planetary-scale commons (atmosphere, oceans, biodiversity, AI governance) through democratic bodies with representation from all levels.
  - *Precedent: The cooperative movement's federated structure* - local co-ops -> regional federations -> national bodies -> International Cooperative Alliance (ICA). Over 3 million cooperatives worldwide, 1 billion+ members. This is the largest existing example of nested democratic governance at global scale.
  - **Open problem:** How do you prevent the upper layers from accumulating power over the lower layers? Subsidiarity (decisions made at the lowest competent level) is the principle. Enforcement of subsidiarity is the unsolved problem. The EU struggles with this constantly.

#### 3.4 Ecological Restoration

Ecological restoration is technically achievable at large scale. The constraint is political will and sustained investment, not technical knowledge.

- [ ] **Demonstrated precedents for restoration at scale**
  - *China's Loess Plateau:* 35,000 km2 of degraded land transformed into productive landscape over 15 years (World Bank funded, community-implemented).
  - *Costa Rica:* Forest cover reversed from 21% (1987) to 60% (2025) through payments for ecosystem services, land-use planning, and ecotourism incentives.
  - *Great Green Wall of Africa:* 8,000 km reforestation project across the Sahel. Partial progress (15% complete as of 2025), demonstrating both feasibility and the challenge of sustained multi-decade commitment.
- [ ] **Regenerative agriculture** as the default, not the exception. Existing models: Savory Institute holistic management, Rodale Institute organic no-till, System of Rice Intensification (SRI) producing higher yields with less water in 60+ countries.
- [ ] **Ocean and freshwater governance** - the largest ungoverned commons. The High Seas Treaty (2023) is a start. Freshwater governance (Colorado River Compact, Murray-Darling Basin Plan) provides both positive and cautionary precedents.

**Open problem: Population.** Global population is projected to peak around 10.4 billion in the 2080s. Resource consumption = population x per-capita consumption. The framework addresses per-capita consumption but is silent on population dynamics. This is not a call for coercive population control - it's an acknowledgment that every ecological restoration plan must account for how many people are consuming what. Demographic transitions (declining fertility correlated with women's education, healthcare access, and economic security) are the ethical and effective mechanism. The framework's Phase 1 priorities (education, healthcare, economic sufficiency) are themselves the best population policy.

---

## Tensions and Tradeoffs

> *The core principles are in tension with each other. Pretending otherwise would be dishonest. These tensions are not bugs - they are the hardest design problems. They do not have clean answers.*

### Democratic Sovereignty vs. Ecological Equilibrium

What happens when a democratic majority votes to allow resource extraction that violates planetary boundaries? This is not hypothetical - it is the story of every coal-dependent community that votes to keep mines open, every fishing village that votes against catch limits.

**The framework's position:** Ecological limits function like constitutional rights - they are not subject to majority override. Just as a majority vote cannot legally strip a minority of civil rights in a constitutional democracy, a majority vote cannot strip future generations of a livable planet. Planetary boundaries are pre-political: they exist whether or not anyone votes for them.

This means democratic sovereignty is real but bounded. You may govern how you live within the limits of what the earth can sustain. You may not vote to exceed those limits.

**Open problem:** Who defines the planetary boundaries, and who enforces them when democratic institutions disagree? This requires a body of scientific governance that is itself democratically accountable but insulated from short-term political pressure. No such body currently exists at adequate scale. (See Issue #35)

---

### Voluntary Contribution vs. Universal Sufficiency

If contribution is truly voluntary, who does the unglamorous work? Sewage treatment. Garbage collection. Elder care at 3 AM. Slaughterhouse labor. Psychiatric emergency response.

Every intentional community, commune, and cooperative in history has confronted this. The kibbutz movement developed elaborate systems for task rotation, compensation differentials, and eventually re-introduced wage labor for roles voluntarism couldn't reliably fill.

**The framework's position:** Voluntary contribution means work is not performed under threat of starvation. It does not mean all work is equally pleasant. Mechanisms for necessary-but-unpleasant work, in order of preference:
1. **Automation** - priority target. If a task is necessary and undesirable, automate it first.
2. **Rotation** - shared burden distributed on a schedule.
3. **Compensation premiums** - additional resources for roles that remain undesirable after automation.
4. **Genuine voluntarism** - some people find meaning in work others find unpleasant. This is real.

**Open problem:** Free-rider dynamics are documented in every commons. Ostrom's design principles (monitoring, graduated sanctions, conflict resolution) are the best available framework but require enforcement mechanisms not yet fully specified here. (See Issue #35)

---

### Common Ownership vs. Cultural Adaptation

The framework says the commons belongs to everyone and that local implementation is culturally adapted. These conflict the moment a community uses "cultural adaptation" to exclude someone from the commons.

**The framework's position:** Local communities may govern *how* resources are distributed and *what* governance processes look like. They may not govern *whether* a person is entitled to food, shelter, healthcare, or safety. Cultural adaptation is permitted within the commons. Using cultural adaptation to deny commons access is not.

**Open problem:** Who decides when a local community has crossed from adaptation into exclusion, and with what enforcement authority? This is the federalism problem in its oldest form. (See Issue #35)

---

### On Human Nature

The framework does not assume humans are angels. It assumes systems designed for the full range of human behavior - including free-riding, status competition, in-group formation, and apathy - will produce better outcomes than systems that punish people for surviving under coercive conditions.

Ostrom's design principles for commons governance are the most empirically grounded framework for managing realistic human behavior: clear boundaries, proportional rules, collective choice, monitoring, graduated sanctions, conflict resolution, external recognition. Not idealistic - operational. See RESEARCH.md.

---

## Open Questions

> *These are unresolved. They need many minds.*

1. How do you transition a globalized economy without leaving developing nations worse off?
2. What role do existing nation-states play? Do they dissolve, federate, or transform?
3. How do you prevent a post-transfer power vacuum from being filled by authoritarians?
4. What does justice look like for historical wrongs (colonialism, slavery, ecological destruction) without creating new cycles of resentment?
5. How do you handle people who genuinely don't want to participate in collective governance?
6. What replaces prisons? What does accountability look like without punishment?
7. How do you govern AI development during and after the transition?
8. How do you maintain cultural and individual diversity in a system designed for collective wellbeing?
9. What is the role of spirituality, religion, and personal belief systems?
10. How do you keep this framework from becoming the very kind of rigid ideology it seeks to replace?
11. How does a fully open, leaderless network coordinate action at global scale without becoming either chaotic or quietly hierarchical?
12. If transparency is the security model, what are its failure modes? When - if ever - is openness genuinely dangerous?
13. What happens if the technological tipping point arrives before the network is ready?

---

## How to Contribute

This framework belongs to no one - and to everyone.

### What We Need

- **Thinkers** - Challenge assumptions, find blind spots, propose alternatives
- **Historians** - What has been tried? What worked? What failed and why?
- **Engineers** - Design the systems (voting, distribution, energy, digital infrastructure)
- **Artists** - Make this vision tangible, emotional, real
- **Organizers** - Connect this to existing movements and communities
- **Skeptics** - Break it. Find the failure modes. Make it stronger.

### How to Contribute

1. Fork this repository
2. Create a branch for your contribution
3. Submit a pull request with a clear description of what you're adding or changing
4. Engage in discussion on Issues - this is where the real work happens

### Guiding Rules for Contribution

- No single person owns this. No cult of personality. Leadership is transparent and accountable (see [GOVERNANCE.md](GOVERNANCE.md)).
- Ideas are evaluated on merit, not on who proposed them.
- Disagree constructively. We are building, not debating.
- Everything happens in the open. No private channels, no backroom coordination.
- Specificity is valued. "We should fix healthcare" is a starting point. "Here is a model for community health worker networks based on Cuba's system" is a contribution.
- Cite your sources. Build on what already exists.

---

## Influences and Prior Art

> *We are not starting from zero. Many have thought deeply about these problems.*

### Thinkers and Theorists
- **Paul Hawken** - *Blessed Unrest* (2007): the largest movement in the world already exists, leaderless, without ideology, and no one has seen it. WiserEarth was the mirror he built so it could.
- **Murray Bookchin** - Social ecology, libertarian municipalism
- **Elinor Ostrom** - Governing the commons without privatization or state control
- **André Gorz** - Post-work society, reclaiming time from capital
- **Kate Raworth** - Doughnut Economics: thriving within planetary boundaries
- **Paulo Freire** - Education as liberation, critical pedagogy
- **Ursula K. Le Guin** - *The Dispossessed*: a fictional blueprint for an anarchist society
- **Danielle Sered** - *Until We Reckon*: restorative justice for violent harm

### Living Models
- **Mondragon Cooperative** - 80,000+ worker-owners, €12B+ revenue (Basque Country)
- **Kerala Model** - High human development on low GDP (India)
- **Zapatista Autonomous Municipalities** - Indigenous self-governance (Mexico)
- **Bhutan's Gross National Happiness** - Alternative metrics for societal success
- **Preston Model** - Community wealth building through anchor institutions (UK)
- **Community Land Trusts** - 300+ in the US, 250+ in England/Wales, growing globally
- **Rural Electric Cooperatives** - 900+ member-owned utilities serving 42M Americans
- **Common Justice** - Restorative justice for violent felonies (New York City)
- **Barcelona Superblocks** - Reclaiming streets for people, play, and community

### Historical Precedents
- **WiserEarth / Wiser.org** (2007-2014) - The first large-scale civil society coordination network. 114,994 NGOs in 243 countries, 79,651 members, 3,273 groups, 381 sub-issue taxonomy. Leaderless, open-source, ad-free, women-led. Direct precedent for the Mycelial Strategy. Closed 2014 due to centralized funding failure -- the key cautionary lesson. See [WISEREARTH.md](WISEREARTH.md) for full analysis. (Paul Hawken / Natural Capital Institute)

### Allied Open-Source Projects
- **Decidim** - Participatory democracy framework (github.com/decidim)
- **Open Food Network** - Food sovereignty platform, 6,000+ farmers (github.com/openfoodfoundation)
- **Community Health Toolkit** - Digital tools for 40,000+ community health workers (communityhealthtoolkit.org)
- **OpenMRS** - Open-source medical records, 40+ countries (openmrs.org)
- **ElectionGuard** - End-to-end verifiable elections (github.com/Election-Tech-Initiative)
- **Open Source Ecology** - 50 open-source industrial machines (github.com/OpenSourceEcology)
- **Liquid Democracy e.V.** - Participatory governance tools (github.com/liqd)
- **OpenDemocracy AI** - AI-powered participatory democracy (github.com/AshmanRoonz/OpenDemocracy)
- **HumanityOS** - Free, public-domain (CC0) cooperative platform + game engine for ending poverty through capability. Self-custody identity, federated, local-first, peer marketplace, offline-first. The Humanity Accord is a model constitution with strong alignment to Ecolibrium's principles. (united-humanity.us, github.com/Shaostoul/Humanity)
- **Kolibri** - Offline-first education platform (learningequality.org)
- **Belenios** - Verifiable online voting system (belenios.org)

### Policy Frameworks
- **The Commons Transition Plan** - P2P Foundation (commonstransition.org)
- **Doughnut Economics Action Lab** - Economics within planetary boundaries (doughnuteconomics.org)
- **Wellbeing Economy Alliance** - Governments moving beyond GDP (weall.org)
- **Guaranteed Income Pilots Dashboard** - 100+ UBI pilots tracked (guaranteedincome.us)

> For a comprehensive deep dive into existing work in each framework area, see **[RESEARCH.md](RESEARCH.md)**. Evidence quality varies: some cited projects are proven at scale (Mondragon, CLTs), some are promising experiments (UBI pilots), and some are theoretical. RESEARCH.md should be read with that gradient in mind.
> For the collaboration outreach plan, see **[OUTREACH.md](OUTREACH.md)**.
> For explicit governance, decision-making, and accountability structures, see **[GOVERNANCE.md](GOVERNANCE.md)**.
> For the honest section-by-section critique of this framework, see **[CRITIQUE.md](CRITIQUE.md)**.

---

## License

This work is released under [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/).

You are free to share, adapt, and build upon this work - even commercially - as long as you give credit and share your contributions under the same license.

---

*"Another world is not only possible, she is on her way. On a quiet day, I can hear her breathing."*
- Arundhati Roy

---

## Project Status

🌱 **Seedling** - This framework is in its earliest stage. Everything is open for discussion, revision, and expansion.
