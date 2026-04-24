# Commonweave: Directory and Framework for the Post-Labor Economy

> **Skeptics start here:** [CRITIQUE.md](CRITIQUE.md) is a section-by-section honest audit of where this framework is weak, magical, or incomplete. It's linked first on purpose. If you're looking for the case against this project, it's already written, and we'd rather you sharpened it than discovered it.

---

## The Idea

Commonweave is two things: (1) an open directory of the existing transition network across 60 countries, and (2) a working framework explaining why that network matters and how it composes into a post-labor economy.

The directory is the concrete deliverable. The framework is the argument for it.

Here is a thing that is true and that almost no one talks about clearly: the machines are going to do most of the work. Not eventually -- now, and accelerating. The interesting question isn't whether that happens. It's who benefits when it does.

Right now the answer is: whoever owns the machines. That's a design choice, not a law of nature. You could design it differently.

The directory catalogs who is already designing it differently: cooperatives, community land trusts, mutual aid networks, open-source health platforms, participatory governance experiments, community energy grids -- 26,022 candidate organizations across 61 countries, filtered from ~760K public registry records through multi-pass keyword scoring against the framework's mechanisms. Of those, 3,657 score >=5 on framework alignment (the strongest matches); the rest are candidates awaiting review. The framework maps how those pieces fit together and what's still missing.

It's not a manifesto. It's more like an engineering problem with a lot of political and historical constraints. The goal is to figure out what needs to be true for people to have food, shelter, healthcare, and a say in their own lives -- and then figure out how to make those things true.

### Selective Abundance, Not Post-Scarcity

This framework does not assume post-scarcity arrives as a binary switch. Some goods are becoming radically cheaper to produce: information, energy, basic nutrition, digital services. Other goods remain genuinely scarce: land, fresh water, skilled human care, rare materials, attention. The honest framing is *selective abundance* -- a world where the challenge is distributing what's abundant while governing what's scarce.

Different resource categories require different governance mechanisms. The table below is the operative claim: if the framework is right, we should find organizations already governing each type correctly.

| Resource type | Examples | Constraint | Governance mode | Failure mode | Directory examples (score >=5) |
|---|---|---|---|---|---|
| Trending toward abundance (energy, information, basic food) | Solar power, open-source software, community gardens | Distribution access, not production cost | Commons-based distribution; universal access rights | Platform capture, artificial scarcity re-imposed by incumbents | Centre for Renewable Energy and Action on Climate Change [NG] |
| Persistently scarce (land, fresh water, rare minerals) | Urban land, aquifers, lithium | Physical limits; rival consumption | Democratic allocation; stewardship/usufruct models; Ostrom-style commons with monitoring and graduated sanctions | Enclosure; privatization of the governance body itself | ADDISON COURT HOUSING COOPERATIVE INC [US]; LANDWELL HOUSING COOPERATIVE [US] |
| Skilled care (healthcare, childcare, eldercare) | Community health workers, midwives, teachers | Human labor hours; training pipeline | Recognized as essential work; compensation premiums; community health worker networks | Burnout and wage suppression when treated as volunteer surplus | [NEEDS EXAMPLE] |
| Ecological systems (atmosphere, oceans, biodiversity) | Carbon cycle, ocean fisheries, pollinator networks | Non-rival but fragile; slow feedback loops | Scientific governance bodies with democratic accountability; use limits insulated from short-term majorities | Democratic override of ecological limits; regulatory capture | Environmental Monitoring Group (EMG) [ZA] |
| Attention and meaning | Culture, community, creative work | Cannot be manufactured or stockpiled | Cultural and institutional responses; time sovereignty | Commodification; algorithmic capture of attention for extraction | [NEEDS EXAMPLE] |
| Cooperative economics (worker ownership, mutual aid) | Worker co-ops, mutual aid networks, credit unions | Capital access; competition from non-cooperative firms | Solidarity economy networks; preferential sourcing between co-ops; policy support (Marcora Law model) | Scale pressure causes drift back to conventional employment (Mondragon precedent) | Mutual Aid Twin Cities Housing Cooperative [US]; PRAGYA [GB] |

The "Directory examples" column is the test. If the framework is falsifiable, then organizations with alignment_score >= 5 in matching areas should be doing what the framework predicts. Cells marked [NEEDS EXAMPLE] are gaps -- either the directory doesn't have good coverage there yet, or the framework's prediction is wrong. Both are worth investigating.

The framework is designed to work under conditions of *partial* abundance and *persistent* scarcity -- not to wait for a threshold that may never fully arrive.

---

## What Exists Today

This section matches ambition to evidence. Here is the concrete state of the project as of April 2026.

### The Directory

The primary deliverable is a searchable database of organizations working in the framework's 10 areas. Numbers from `data/commonweave_directory.db`, verified 2026-04-23, filter: `WHERE merged_into IS NULL`:

- **26,022 candidate organizations** across **61 countries**
- **11,991 geocoded points** visible on the interactive map, with **2,687 network edges** connecting related organizations
- **Sources:** UK Charity Commission (11,537), IRS Exempt Organizations BMF (9,402), Wikidata (2,894), ProPublica (604), web research (58), manual curation (13)
- **Search interface:** per-country JSON index at `data/search/`, browsable at `directory.html`
- **Interactive map:** network visualization at `map.html`
- **Framework area breakdown:** healthcare (6,369), education (5,694), food (2,955), democracy (2,863), housing & land (2,406), ecology (2,346), conflict resolution (910), cooperatives (656), recreation & arts (269), energy & digital (40)

Honest breakdown of what 26,022 records means:

- **15,854 are registry-backed (Tier B)** - sourced from official charity registries or manually curated; 10,032 are unverified candidates (Tier D); 136 have no tier assigned
- **3,657 entries (14%)** score >=5 on framework alignment -- the strongest keyword matches (community land trust, worker cooperative, mutual aid, food sovereignty, restorative justice)
- **Geographic skew:** ~83% of records come from US and UK open registries (21,559 of 26,022). The remaining 59 countries hold 4,463 organizations between them. Closing that gap is the main enrichment target.
- **Legibility data:** a `legibility` column (formal / hybrid / informal / unknown) was added 2026-04-22 to flag self-reported-bias signals. All 26,022 records currently read `unknown` - the column exists, backfill is pending. This is the intended countermeasure for the US/UK formal-NGO skew problem; it is not yet operational.

The earlier 738K figure counted every non-removed row including 431K entries flagged as excluded by prior audit passes. The current 26,022 reflects what actually passed alignment scoring. The excluded rows are preserved as CSVs in `data/trim_audit/` for transparency and reversibility.

### The Framework

This README is the framework document. Its current maturity:

- **Draft.** The core thesis, three-phase structure, and Mycelial Strategy are written and internally consistent. Core tensions are documented. Open questions are flagged as open.
- **Critique-first.** [CRITIQUE.md](CRITIQUE.md) is a section-by-section honest audit of where the framework is weak or incomplete. It exists because the failure modes should be on the table before anyone commits to this.
- **Open.** Every claim is either citable or flagged as speculative. Pull requests are the revision mechanism.

### Related project: NeighborhoodOS

[NeighborhoodOS](https://neighborhoodos.org) is a sibling project — an open-source operating system for neighborhoods that want to solve their own problems, starting with one sharp "wedge" at a time. It was originally developed inside Commonweave as a ground-level implementation layer; in April 2026 it was split out into its own project so each can move at its own pace.

The two projects stay loosely connected: NeighborhoodOS can optionally consume the Commonweave directory to answer "who's already working on this near me?" when a wedge calls for it. But each project has its own repo, roadmap, and governance.

Current NeighborhoodOS wedge: home maintenance in West Waldo, Kansas City (owner-occupied only).

- Site: [neighborhoodos.org](https://neighborhoodos.org)
- Code: [GitHub](https://github.com/simonlpaige/neighborhoodos) / [Codeberg](https://codeberg.org/AlphaWorm/neighborhoodos)

---

## What Does Not Exist Yet

To be specific:

- **No running pilots under the Commonweave banner.** Organizations in the directory operate independently. None are affiliated with or funded by this project.
- **No collaboration agreements with Tier 1 allied projects.** The outreach plan is in [OUTREACH.md](OUTREACH.md). The conversations have not happened yet.
- **No named legal entity.** There is no Commonweave Foundation, LLC, or unincorporated association. This is a repository and a framework document.
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

## The Framework in 90 Seconds

Three phases, one connective tissue. The phases are parallel tracks that co-evolve, not a linear sequence -- Phase 1 prerequisites depend on Phase 3 outcomes and vice versa.

**Phase 1 -- Pre-transfer:** Build the alternatives before anything collapses. Democratic infrastructure, food/healthcare/housing/energy systems designed for sufficiency rather than profit, cooperative economics. These need to be working at small scale before any transfer is realistic -- think of it as load testing before launch. Full specification: [BLUEPRINT.md](BLUEPRINT.md).

**Phase 2 -- The transfer:** Not a revolution, a migration with resistance. The prepared alternatives scale up, institutions transform from within and under pressure, the old economy loses its revenue base. Full analysis of mechanisms and historical cases: [THEORY-OF-CHANGE.md](THEORY-OF-CHANGE.md).

**Phase 3 -- Maintenance:** The hard part isn't building the good world, it's keeping it from sliding back. Anti-backsliding mechanisms, beyond-GDP measurement, nested governance, ecological restoration. Phase 3 is the immune system. [THEORY-OF-CHANGE.md](THEORY-OF-CHANGE.md).

### The Mycelial Strategy

The connective tissue across all phases: a distributed network of people and organizations building working alternatives -- not arguing about theory, but running pilots, writing code, keeping books, growing food, running clinics. When conditions are right, the network doesn't seize power. It just already has the replacement ready.

In 2007, Paul Hawken published *Blessed Unrest* arguing the world's largest social movement already existed -- millions of organizations with no name and no central organization. He and colleagues catalogued 114,994 of them on WiserEarth. Then the funding ran out and the whole thing disappeared in a weekend. That was 2014.

The lesson isn't that the idea was wrong. It's about infrastructure -- both technical (don't depend on a single server) and social (don't depend on everyone running their own). The realistic model is decentralized in *governance* but may be centralized in *operations* -- like the Wikimedia Foundation or the Apache Foundation. Not ideologically pure, but actually works.

The framework protects itself primarily through transparency. Co-option is harder when everything is visible. But openness has known failure modes that must be actively managed:

- **Flooding and noise:** Bad actors can overwhelm discussion to dilute signal. *Countermeasure: moderation policies, contribution quality standards, rough consensus decision-making with clear timelines.*
- **Concern trolling:** Using the open process to slow-walk decisions to death. *Countermeasure: decision deadlines, "rough consensus and running code" -- working implementations outweigh theoretical objections.*
- **Strategic co-option:** Aligning publicly with the movement while redirecting its resources toward industry-friendly goals (see: corporate greenwashing). *Countermeasure: clear alignment criteria, willingness to refuse partnerships that don't meet them, outcome-based evaluation.*
- **Harassment of contributors:** Visible participation makes contributors targets. *Countermeasure: contributor pseudonymity is supported as protection, not ideology. People may contribute under any identity.*
- **State surveillance:** Open coordination makes it trivial for hostile governments to monitor and map the network. *The framework accepts this tradeoff.* A movement that requires secrecy to function is fragile. A movement that functions in plain sight and still works is resilient. Contributors in repressive contexts should use whatever operational security they need, and the network supports that without judgment.

Network governance, accountability structures, named leadership: [GOVERNANCE.md](GOVERNANCE.md).

### Theory of Power Transfer

The framework requires an honest answer to the hardest question: *why would those with power give it up?*

Most won't. Not voluntarily. Power does not become "irrelevant" because better alternatives exist. The history of fossil fuels, tobacco, feudal land tenure, and colonial governance shows that entrenched power fights to preserve itself long after superior alternatives are available.

The framework relies on five mechanisms, in order of realism:

1. **Economic obsolescence.** Some power structures erode when technology changes -- newspaper classified ad revenue, taxi medallions, music label distribution monopolies. The framework identifies which current power structures are vulnerable to technological displacement and builds alternatives there first.
2. **Democratic capture in reverse.** Electing people committed to commons-based policy into existing structures. Already happening: participatory budgeting in 7,000+ cities, community wealth building in Preston and Cleveland, state-level cooperative development legislation. Slow, boring, effective.
3. **Coalition pressure.** Labor movements, consumer boycotts, shareholder activism, divestment campaigns. The anti-apartheid movement, marriage equality, the tobacco settlement -- none waited for the powerful to see the light.
4. **Parallel institution-building.** Email didn't ask the postal service for permission. Wikipedia didn't negotiate with Encyclopaedia Britannica. When commons-based alternatives are demonstrably better, migration happens.
5. **Nonviolent non-cooperation.** When power refuses to yield: strikes, tax resistance, civil disobedience. The framework is nonviolent. It is not passive.

**What the framework does NOT assume:** That power holders will voluntarily step aside. That the transition will be smooth or painless. Some power will have to be taken, even if the taking is nonviolent. Full engagement with historical cases: [THEORY-OF-CHANGE.md](THEORY-OF-CHANGE.md).

---

## Tensions and Tradeoffs

The core principles are in tension with each other. These are not bugs -- they are the hardest design problems. They do not have clean answers.

**Democratic Sovereignty vs. Ecological Equilibrium:** What happens when a democratic majority votes to allow resource extraction that violates planetary boundaries? The framework's position: ecological limits function like constitutional rights -- not subject to majority override. A majority vote cannot strip future generations of a livable planet. Planetary boundaries are pre-political. **Open problem:** Who defines them, and who enforces them when democratic institutions disagree? No such body currently exists at adequate scale. (See Issue #35)

**Voluntary Contribution vs. Universal Sufficiency:** If contribution is truly voluntary, who does the unglamorous work? Sewage treatment, garbage collection, elder care at 3 AM. Every commune and cooperative in history has confronted this. The framework's position: voluntary contribution means work is not performed under threat of starvation. Mechanisms in order of preference: automation first, then rotation, then compensation premiums, then genuine voluntarism. **Open problem:** Free-rider dynamics are documented in every commons. Ostrom's design principles are the best available framework but require enforcement mechanisms not yet fully specified here. (See Issue #35)

**Common Ownership vs. Cultural Adaptation:** Local communities may govern *how* resources are distributed. They may not govern *whether* a person is entitled to food, shelter, healthcare, or safety. **Open problem:** Who decides when a community has crossed from adaptation into exclusion? This is the federalism problem in its oldest form. (See Issue #35)

The framework does not assume humans are angels. It assumes systems designed for the full range of human behavior -- free-riding, status competition, in-group formation, apathy -- will produce better outcomes than systems that punish people for surviving under coercive conditions. See [RESEARCH.md](RESEARCH.md).

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

### Good First Contributions

A contributor should be able to pick one task in 60 seconds. Here are tasks by type:

**Data**
- Pick a country with fewer than 50 orgs in the directory. Open `data/search/<country>.json`. Find organizations that are missing, misclassified, or have broken websites. File a PR with corrections and a one-line note at the top explaining what you checked.
- **Directory verification (45 minutes).** Pick one country with <50 orgs. Open `data/search/<country>.json`. Spot-check 10 orgs: website works, description matches framework area. File a PR editing the JSON with your corrections + a note at the top. Country-scoped tasks work because a contributor in Nairobi or Mexico City immediately has local knowledge we don't have.

**Research**
- Pick one Open Question from the table below and find at least one peer-reviewed source or documented real-world experiment that speaks to it. File a PR adding the source and a 2-sentence summary to RESEARCH.md.
- Find a working cooperative, land trust, or mutual aid network in your country or city not yet in the directory. Document it in a PR following the format in `data/CONTRIBUTING-DATA.md`.

**Code**
- The map defaults to showing all tiers. A "high-confidence only" filter (Tier B + score>=5) would show ~3,657 orgs instead of ~11,991. Implement it as a toggle in `map.html`.
- `data/build_map_v2.py` generates edges without provenance metadata. The edge schema should include `edge_type`, `confidence`, `explanation`, `created_at`, and `source_script`. Add these fields.
- Mobile experience on `map.html` is basic. Clustering, better popups, or a touch-friendly filter panel would help.

**Design / Writing**
- The governance matrix in the Selective Abundance section has several `[NEEDS EXAMPLE]` cells. Find a real organization from the directory that fits and fill one in with a PR.
- Draft a 3-sentence plain-language explanation of one framework mechanism (community land trust, participatory budgeting, mutual aid) for someone who has never heard of it. Submit to GLOSSARY.md (create it if it doesn't exist).

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
- **HumanityOS** - Free, public-domain (CC0) cooperative platform + game engine for ending poverty through capability. Self-custody identity, federated, local-first, peer marketplace, offline-first. The Humanity Accord is a model constitution with strong alignment to Commonweave's principles. (united-humanity.us, github.com/Shaostoul/Humanity)
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
