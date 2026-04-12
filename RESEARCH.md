# Ecolibrium Research: Existing Work, Tools, and Allies

> *A deep dive into what already exists for each area of the framework. Nothing starts from zero.*

---

## 1. Democratic Infrastructure & Voting Systems

### What Already Exists

**Open-source voting technology is maturing rapidly.** Multiple projects are building verifiable, transparent election systems:

- **ElectionGuard** (github.com/Election-Tech-Initiative/electionguard) — Microsoft-backed open-source SDK using homomorphic encryption for end-to-end verifiable elections. Allows voters to confirm their votes were correctly counted while keeping ballots secret. MIT licensed.
- **VotingWorks** (votingworks.com) — Nonprofit building open-source voting machines. Already piloted in Mississippi and New Hampshire. Code publicly available on GitHub.
- **VoteSecure** — First open-source SDK for end-to-end encrypted mobile voting, released November 2025 by the Mobile Voting Foundation. Election vendors Sequent and Democracy Live committed to implementing it in 2026.
- **Belenios** (belenios.org) — French open-source online voting system providing vote privacy via encryption and public verifiability. Actively maintained through 2025.
- **VotoSocial** (votosocial.github.io) — Blockchain-based voting with no central servers, publicly traceable votes, and voter anonymity.
- **OSET Institute / TrustTheVote** (trustthevote.org) — Developing ElectOS, an open-source election technology platform for publicly owned innovation.

**Participatory democracy platforms are production-ready:**

- **Decidim** (github.com/decidim) — The most mature participatory democracy framework. Ruby on Rails. Used by Barcelona, Helsinki, and hundreds of organizations worldwide for proposals, debates, participatory budgeting, and assemblies.
- **Liquid Democracy e.V.** (github.com/liqd) — Berlin-based nonprofit. Their Adhocracy+ platform powers participation processes across Germany, including Berlin's meinBerlin platform.
- **OpenDemocracy AI** (github.com/AshmanRoonz/OpenDemocracy) — Open-source AI for participatory democracy, surfacing consensus while preserving minority views. Community-governed, no gatekeepers.
- **Consul** (consuldemocracy.org) — Open-source citizen participation tool used by Madrid and many other cities.
- **Loomio** (loomio.com) — Collaborative decision-making tool for groups of any size.
- **Democracy Earth** — Decentralized liquid democracy governance platform using blockchain.

**Key resources:**
- The Democracy Foundation maintains a comprehensive list of 50+ e-democracy projects: democracy.foundation/similar-projects

### Recommendations for Ecolibrium

1. Don't build new voting software — integrate with Decidim and ElectionGuard. They're battle-tested.
2. Focus the framework's contribution on the *governance design* layer: how liquid democracy, sortition, and recall mechanisms interoperate.
3. The Sophia Protocol on GitHub (integrating UBI with governance and Sybil resistance) is worth tracking.

---

## 2. Wealth Distribution & Universal Basic Income

### What Already Exists

**UBI has moved from theory to empirical evidence.** Over 100 pilots have run or are running worldwide:

- **Guaranteed Income Pilots Dashboard** (guaranteedincome.us) — Tracks all active and completed pilots in the US. Data updated through December 2025.
- **OpenResearch Unconditional Income Study** (2024) — The largest US study: 1,000 people received $1,000/month for 3 years. Results: participants took better jobs, went back to school, started businesses. No evidence of work stoppage.
- **Marshall Islands** (November 2025) — Introduced a national universal basic income scheme: quarterly payments of ~$200 to every resident citizen, funded by a $1.3B trust fund.
- **Catalonia** — Piloting €800/month for adults, €300/month for children under 18 across 5,000 participants.
- **Chicago Resilient Communities Pilot** — 5,000 households received $500/month for one year. UChicago evaluation showed improved financial stability, food security, and psychological wellness.
- **Minneapolis Fed study** — Found $500/month GBI improved financial stability and food security with no negative effects on labor supply.
- **GiveDirectly** — Long-running unconditional cash transfer program in Kenya, one of the most studied in the world.

**Cooperative and commons economics:**
- **Mondragon Corporation** (Basque Country) — World's largest worker-owned cooperative: 80,000+ worker-owners, €12B+ revenue. Proof that democratic enterprise works at scale.
- **Preston Model** (UK) — Municipal "community wealth building" using anchor institutions, local procurement, and cooperative development.
- **Evergreen Cooperatives** (Cleveland, OH) — Network of worker-owned, green businesses anchored by local institutions.
- **P2P Foundation** — Extensive research and policy proposals on commons-based economics and transition.

### Recommendations for Ecolibrium

1. Link to the Guaranteed Income Pilots Dashboard as a living evidence base.
2. Study the Preston Model as a concrete "Phase 1" pilot — it shows how existing local governments can begin redirecting wealth without national policy changes.
3. The Mondragon cooperative structure should be documented as a template for enterprise transition.

---

## 3. Healthcare

### What Already Exists

**Open-source healthcare infrastructure is surprisingly mature:**

- **OpenMRS** (openmrs.org) — The world's leading open-source medical records system. No license fees. Used across 40+ countries. Supports HIV, TB, maternal health, COVID, and more. Hundreds of developers contribute globally.
- **Community Health Toolkit** (communityhealthtoolkit.org) — Open-source digital tools for community health workers. Deployed in 15 countries across Africa and Asia. Supports 40,000+ health workers who have performed 85M+ caring activities since 2014. Offline-first, works on feature phones.
- **DHIS2** — Open-source health information system used by 100+ countries for disease surveillance, health program management, and pandemic response.
- **OpenEHR** — Open standard separating clinical information models from software, enabling interoperable health records across systems.
- **iHRIS** — Open-source human resources information system for healthcare workforce management, used in 20+ countries.

**Healthcare models to study:**
- **Cuba's Community Health Worker model** — Neighborhood-embedded family doctors. One of the world's most effective primary care systems despite limited resources.
- **Costa Rica's EBAIS system** — Community-based health teams providing universal coverage.
- **Kerala's public health system** — High health outcomes on low GDP through investment in primary care, education, and community health.
- **NHS (UK)** — Despite its challenges, remains the most comprehensive single-payer system in the developed world.

### Recommendations for Ecolibrium

1. The Community Health Toolkit is the single most deployment-ready piece of the framework. It already works offline in low-infrastructure environments.
2. Cuba's polyclinic model should be documented as a governance template for community-embedded healthcare.
3. Open-source medical research can build on existing movements like Open Access publishing and the Medicines Patent Pool.

---

## 4. Food Distribution & Sovereignty

### What Already Exists

**Open-source food systems infrastructure:**

- **Open Food Network** (openfoodnetwork.org, github.com/openfoodfoundation) — Open-source platform connecting 6,000+ farmers and 700+ local shops across 15 production instances on three continents. AGPL v3 licensed. Developing open standards for food system data exchange.
- **FarmHack** (farmhack.org) — Open-source community for farmer-developed tools and technologies.
- **Open Source Ecology GVCS** — Includes agricultural machines (tractor, combine, seed drill) in their 50-machine civilization construction set.

**Food sovereignty movements and models:**
- **La Via Campesina** — Global movement of 200 million peasant farmers across 81 countries advocating food sovereignty.
- **Community Supported Agriculture (CSA)** — Direct farmer-to-consumer relationships operating in thousands of communities worldwide.
- **Lumbee Tribe Food Sovereignty Initiative** — Comprehensive model combining food hubs, processing centers, commercial kitchens, and community markets.
- **Canobi AgTech** — Modular vertical farming systems deployed with First Nations communities in Canada. Combines indoor farming with food forests and small livestock for complete food sovereignty.

**Vertical farming and technology:**
- The European Agricultural Resilience Act (January 2026) provides subsidies for converting abandoned commercial real estate into vertical farms using closed-loop hydroponic systems.
- Saudi Arabia's NEOM project is piloting advanced aeroponics with solar microgrids for caloric sovereignty in arid environments.

### Recommendations for Ecolibrium

1. Open Food Network is the infrastructure layer for food distribution. It should be integrated directly.
2. Document La Via Campesina's principles of food sovereignty — they've been doing this work for 30 years.
3. The combination of vertical farming + regenerative agriculture + community food networks is the model. No single approach is sufficient.

---

## 5. Education

### What Already Exists

**Open education resources are vast:**

- **MIT OpenCourseWare** — Free access to virtually all MIT course materials.
- **Khan Academy** — Free education platform serving millions globally.
- **Wikipedia** — The largest collaboratively-built knowledge commons in history.
- **Creative Commons** — Legal infrastructure for sharing educational materials openly.
- **Open Education Global** — Network promoting open education policies and practices.
- **Moodle** (open-source) — Most widely used open-source learning management system globally.
- **Kolibri** (learningequality.org) — Offline-first open-source education platform designed for low-connectivity environments.

**Alternative education models:**
- **Finland's education system** — No standardized testing until age 16, emphasis on play, creativity, and well-being. Consistently top-ranked globally.
- **Reggio Emilia approach** (Italy) — Child-led, project-based, community-integrated education.
- **Paulo Freire's critical pedagogy** — Education as liberation, not domestication. Foundation of many progressive education movements globally.
- **Escuela Nueva** (Colombia) — Scalable model for rural, multi-grade, democratic education. Adopted in 16+ countries.
- **Democratic free schools** — Sudbury Valley, Summerhill, and hundreds of schools worldwide where students govern themselves.

### Recommendations for Ecolibrium

1. Don't reinvent educational content — build on existing open educational resources.
2. Focus the framework on *governance* of education: who decides what's taught, how communities control their schools, and how education connects to the broader commons.
3. Kolibri (offline-first education) is a critical tool for Phase 1 pilots in underserved areas.

---

## 6. Disassembly of Private Land Ownership

### What Already Exists

**Community Land Trusts are a proven, growing global movement:**

- **300+ CLTs now operate in the US** (up from 289 in 2021), spanning 48 states plus DC and Puerto Rico.
- **International Center for Community Land Trusts** (cltweb.org) — Coordinates the global CLT movement. Hosting a 2026 Global Virtual Summit.
- **Community Land Scotland** — Members collectively own or manage over 500,000 acres (2,000 km²), home to 25,000+ residents. Scotland's land reform legislation actively promotes community ownership.
- **Caño Martín Peña CLT** (Puerto Rico) — Created through community legislation to protect 2,000+ families from displacement, pioneering the CLT model in the Global South.
- **250+ CLTs in England and Wales** with thousands of members and hundreds of completed homes.
- The model has spread to Australia, Belgium, France, Brazil, Kenya, and other nations.

**Historical and theoretical foundations:**
- The CLT model grew directly from the US civil rights movement (New Communities Inc., 1969, founded by Black sharecroppers and activists in Georgia).
- Inspired by India's Bhoodan (Land Gift) Movement, Israel's moshav communities, and English Garden Cities.
- Elinor Ostrom's commons governance theory provides the intellectual framework.
- **Agrarian Trust** — Applying CLT principles specifically to agricultural land stewardship.

### Recommendations for Ecolibrium

1. Community Land Trusts are the single most proven mechanism for transitioning from private to commons-based land tenure. The framework should adopt the CLT model as its primary land transition strategy.
2. The tripartite governance structure (leaseholders, community residents, public interest) is a proven template for democratic land governance.
3. Scotland's experience shows this can work at national policy scale, not just community scale.

---

## 7. Conflict Resolution & Restorative Justice

### What Already Exists

**Restorative justice is moving from margins to mainstream:**

- **Common Justice** (New York City) — The first alternative-to-incarceration and victim-service program in the US focusing on violent felonies in adult courts. Research shows participants are 41.5% less likely to be rearrested than those processed through the traditional criminal legal system.
- **Impact Justice Restorative Justice Project** — The only national technical assistance and training project partnering with communities for pre-charge restorative justice diversion programs.
- **Vera Institute of Justice** — Leading research and advocacy on alternatives to incarceration, with comprehensive evaluations of ATI programs.
- **Dignity & Power Now** — Transformative justice, community healing, and abolition organization in Los Angeles.
- **Prison Policy Initiative** — Published "Winnable Criminal Justice Reforms in 2025" with 34 high-impact policy ideas.

**International models:**
- **New Zealand's family group conferences** — Restorative justice embedded in the youth justice system since 1989.
- **Rwanda's Gacaca courts** — Community-based justice system for post-genocide reconciliation.
- **Norway's and Finland's prison systems** — Focused on rehabilitation and reintegration, with among the lowest recidivism rates in the world.

### Recommendations for Ecolibrium

1. Common Justice's model proves restorative justice works for violent felonies, not just minor offenses. This is critical evidence.
2. The framework should advocate for restorative justice as the *default*, with incarceration as the rare exception — the inverse of current systems.
3. Build on existing abolitionist organizations' work rather than creating parallel structures.

---

## 8. Energy & Digital Commons

### What Already Exists

**Community energy is growing globally:**
- **Community Energy England** — 300+ community energy organizations generating renewable energy.
- **Energy Democracy** movement — Growing network of community-owned renewable energy projects.
- **Rural Electric Cooperatives** (US) — 900+ member-owned electric utilities already serving 42 million Americans. Proof that energy cooperatives work at scale.

**Digital commons and data sovereignty:**
- **IPFS (InterPlanetary File System)** — Decentralized file sharing protocol, bypassing centralized servers.
- **Mastodon / ActivityPub / Fediverse** — Federated, open-source social media replacing centralized platforms.
- **Signal** — Open-source encrypted messaging.
- **Mozilla** — Nonprofit steward of open internet values.
- **MyData Global** — Movement for human-centered personal data management.
- **Solid** (Tim Berners-Lee) — Protocol for decentralized data ownership.

### Recommendations for Ecolibrium

1. The 900+ rural electric cooperatives in the US are an existing proof of concept for community energy sovereignty.
2. The Fediverse / ActivityPub protocol is the model for decentralized digital infrastructure.
3. The framework should explicitly advocate for IPFS-based document and data storage.

---

## 9. Recreation, Art & Humanities

### What Already Exists

- **Bhutan's Gross National Happiness** — The only country that officially measures national success by happiness rather than GDP.
- **Creative Commons** — Legal infrastructure enabling free sharing of creative works. Over 2 billion CC-licensed works exist.
- **Arts Council England, NEA (US)** — Public arts funding bodies (though chronically underfunded).
- **UBI for artists** — Ireland launched a Basic Income for the Arts pilot in 2022, providing €325/week to 2,000 artists.
- **Barcelona's Superblocks** — Reclaiming streets from cars for public recreation, play, and community gathering.
- **Public libraries** — The original commons institution, providing free access to knowledge, gathering space, and community services.

### Recommendations for Ecolibrium

1. Ireland's Basic Income for Artists is a concrete model to document.
2. Barcelona's Superblocks demonstrate how physical space can be reclaimed for recreation and community.
3. The framework should position public libraries as the institutional template for commons-based community infrastructure.

---

## 10. Values Transformation & Removing Cults of Personality

### What Already Exists

- **Doughnut Economics Action Lab** (DEAL) — Kate Raworth's framework for thriving within planetary boundaries. Adopted by Amsterdam, Brussels, and other cities as a governance framework.
- **Wellbeing Economy Alliance (WEAll)** — Network of organizations, governments, and movements working toward economies that deliver human and ecological wellbeing. Includes governments of Scotland, Iceland, New Zealand, Wales, Finland, and Canada.
- **Wellbeing Economy Governments (WEGo)** — Formal partnership of national governments committed to moving beyond GDP.
- **Gross National Happiness Commission** (Bhutan) — Operational since 2008, screens all policy proposals against happiness metrics.
- **Sortition / Citizens' Assemblies** — France's Convention Citoyenne pour le Climat (2019-2020), Ireland's Citizens' Assembly (led to marriage equality and abortion reform), and many others demonstrate that randomly selected citizens can make better policy than elected politicians without cults of personality.

### Recommendations for Ecolibrium

1. The Wellbeing Economy Alliance is the most aligned existing network. Direct collaboration is essential.
2. Citizens' Assemblies via sortition are the most proven mechanism for removing personality from politics.
3. The Doughnut Economics framework should be integrated as the economic measurement system.

---

## Connected Projects: Key Ideas to Integrate

### From Open Source Ecology
- **Modular, open-source industrial machines** — The GVCS approach of breaking civilization into 50 buildable machines is a powerful model. Ecolibrium should reference OSE's work for the physical infrastructure layer.
- **Distributed manufacturing** — The principle that any community should be able to fabricate what it needs locally.
- **Source:** opensourceecology.org, github.com/OpenSourceEcology

### From the P2P Foundation / Commons Transition
- **The Commons Transition Plan** — Originally developed for Ecuador (FLOK project, 2014), this is the most comprehensive existing policy framework for transitioning to a commons-centric economy. Key insight: the transition requires simultaneous transformation of civil society, the market, and the state.
- **Cosmo-local production** — Design global, manufacture local. Knowledge shared freely, physical production happens where it's needed.
- **P2P Accounting for Planetary Survival** — Framework for commons-based accounting systems.
- **Source:** commonstransition.org, wiki.p2pfoundation.net

### From Decidim
- **Modular participation architecture** — Decidim's approach of composable participation modules (proposals, debates, budgets, assemblies) is a governance design pattern Ecolibrium should adopt.
- **Source:** github.com/decidim

### From Solve Everything
- **The "New Abundance Contract"** — Floors (guaranteed access to basic services), Freedom (compute allowances), Feedback (real-time fairness dashboards).
- **Two-Source Rule** — Two independent AIs confirm critical decisions.
- **Data Fiduciaries** — Neutral trusts preventing data monopolies.
- **Source:** solveeverything.org

### From OpenDemocracy AI
- **AI as neutral integrator** — Not a ruler, not an oracle, but a shared reflective layer that surfaces consensus while preserving minority views.
- **Source:** github.com/AshmanRoonz/OpenDemocracy

### From Community Land Trust Movement
- **Tripartite governance** — Board structure balancing leaseholders, community residents, and public interest representatives. Applicable beyond land to all commons governance.
- **Permanent affordability through ground leases** — Legal mechanism preventing re-commodification.
- **Source:** cltweb.org, groundedsolutions.org

### From Doughnut Economics
- **Planetary boundaries as hard limits** — The economy operates within ecological ceilings and above social foundations.
- **The Doughnut framework** — A visual and conceptual tool for replacing GDP.
- **Source:** doughnuteconomics.org

---

## Sources & Credits

All projects, organizations, and models referenced in this document are credited to their respective creators and communities. Ecolibrium does not claim ownership of any of these ideas — it seeks to weave them together into a coherent transition framework.

This research was compiled in April 2026 and represents a snapshot. The landscape is evolving rapidly. Contributors are encouraged to update and expand this document as new projects emerge.
