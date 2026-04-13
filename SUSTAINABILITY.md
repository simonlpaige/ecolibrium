# Ecolibrium Sustainability

> *WiserEarth mapped 114,994 organizations across 243 countries. Then its funding ran out and it disappeared in 72 hours. On April 10, 2014, the site went dark.*
>
> *This document exists so Ecolibrium doesn't make the same mistake.*

---

## The Problem

WiserEarth is the direct predecessor to this project. It failed for one reason: it depended entirely on philanthropic grants flowing through a single organization (Natural Capital Institute). When the grants stopped, the infrastructure stopped. No federated copies. No endowment. No protocol. Just a server that went dark.

This is not a unique failure. It is the default failure mode of well-intentioned open infrastructure projects:

- **Centralized funding + decentralized mission = single point of collapse**
- **Volunteer labor + no compensation model = burnout and abandonment**
- **Open-source idealism + no revenue model = dependency on whoever writes the checks**

The framework cannot credibly propose a resilient, distributed, post-scarcity society if its own infrastructure is one grant cycle away from extinction.

---

## Design Principles for Sustainability

These are not aspirations. They are hard constraints that any infrastructure decision must satisfy:

**1. No single point of financial failure.**
The project cannot depend on any single funder, foundation, corporation, or individual for more than 20% of its operating costs. If one source disappears, operations continue.

**2. Infrastructure is federated, not hosted.**
Code, data, and documentation must be reproducible from public sources. If the primary repository disappears, any participant can reconstitute the project from their own copy. This means: public git mirrors, exportable datasets, no proprietary lock-in.

**3. Contributions are compensated where possible.**
"Voluntary contribution" cannot become a euphemism for unpaid labor. Sustainable projects find ways to compensate core contributors -- not necessarily with money, but with credit, access, reduced costs, or priority support. When money exists, it goes to contributors first.

**4. Costs are transparent.**
Operating costs are published. Anyone can see what the project costs to run, where the money comes from, and where it goes.

**5. The project is smaller than its network.**
Ecolibrium's infrastructure should be minimal. The value lives in the network of organizations, contributors, and allied projects -- not in central servers or staff. A project with 5 federated mirrors and 200 active contributors is more resilient than one with a $1M budget and a central office.

---

## Funding Models (In Priority Order)

These are not mutually exclusive. The goal is a portfolio that satisfies Principle 1.

### Tier 1: Protocol-Level Funding (No Strings)

**Quadratic Funding via Gitcoin or similar**
Gitcoin has distributed over $50M to open-source projects through quadratic funding -- a mechanism where small donations from many contributors are matched by a larger pool, weighted by the number of unique donors rather than the size of donations. This structurally favors projects with broad community support over projects with a few large donors. It is the closest thing to democratic fundraising for open infrastructure.

Target: quarterly Gitcoin rounds for any open-source tooling built under this project.

**Open Collective**
Open Collective provides transparent fiscal hosting -- all income and expenses are public, anyone can contribute, and funds are disbursed by project maintainers with full public visibility. Used by Babel, webpack, Open Food Network, and hundreds of other open-source projects. No nonprofit incorporation required to start.

Target: establish an Open Collective for Ecolibrium infrastructure costs (hosting, domains, tooling) as Phase 1.

### Tier 2: Federated Membership Dues

Once the network is active -- once organizations are using the directory, the taxonomy, and the coordination tools -- a federated membership model becomes viable.

**Model:** Organizations that use Ecolibrium infrastructure contribute based on capacity. Large organizations (annual budget >$1M) contribute more; small organizations and individuals contribute less or nothing. No minimum required for participation.

This mirrors the cooperative movement's own funding model: dues proportional to benefit and capacity. It also mirrors how successful federated networks like REScoop.eu (2,250+ European energy cooperatives) sustain themselves.

**What dues pay for:** Hosting, moderation, translation, accessibility improvements, and compensation for core contributor time.

**What dues never pay for:** Exclusivity. Paying members get no governance power that non-paying members don't. The Ecolibrium framework explicitly rejects pay-to-play governance.

### Tier 3: Grants (With Structural Constraints)

Grants are acceptable if and only if:

- No single grant exceeds 20% of annual operating budget (Principle 1)
- Grant terms do not restrict the project's direction, licensing, or governance
- The project would survive the grant ending without structural damage

**Priority grant sources:**
- **Prototype Fund** (Germany) -- funds open-source civic tech, no strings, up to €95K
- **NLnet Foundation** -- funds open internet and privacy infrastructure
- **Mozilla Foundation** -- funds open web and digital commons projects
- **Ford Foundation** -- funds civic infrastructure and democratic participation
- **Shuttleworth Foundation** -- funds open, collaborative approaches to social challenges
- **NDI / IRI Technology Grants** -- fund democracy and civic tech infrastructure

**What to avoid:**
- Grants from organizations with political agendas that conflict with the framework
- Grants that require proprietary deliverables or restricted licensing
- Grants that create dependency on continued funding for basic operations

### Tier 4: Earned Revenue (Long-Term)

As Ecolibrium grows, there are legitimate earned revenue models that don't compromise the commons:

**Premium support and consulting:** Organizations implementing Ecolibrium tools can pay for dedicated support, customization, and consulting. The software remains free. The expertise is compensable.

**Training and facilitation:** The deep-dive documents, governance templates, and taxonomy tools have value for organizations building commons infrastructure. Workshops and facilitation services are compensable.

**Data services:** Aggregated, anonymized data from the directory (not individual organizational data) may have value for researchers and policymakers. This requires careful governance to ensure it doesn't create perverse incentives.

---

## Infrastructure Requirements and Costs

### Minimum Viable Infrastructure

The project currently runs on GitHub Pages (free) with no operating costs. This is fine for Phase 0 (documentation and community building). It is not sufficient for Phase 1 (active directory, coordination tools, community platform).

**Estimated Phase 1 annual costs:**
- Hosting and CDN: $500-2,000/year (depending on traffic)
- Domain registration: $20/year
- Email infrastructure: $100-500/year
- Data backup and redundancy: $200-500/year
- **Total minimum: ~$1,000-3,000/year**

This is achievable through Open Collective from day one. It is not a funding problem; it is an organizational problem.

**Estimated Phase 2 annual costs (active community platform):**
- Hosting (Mastodon/Matrix/Nextcloud instance or similar): $2,000-10,000/year
- Moderation and community management (part-time): $15,000-30,000/year
- Core contributor compensation (1-2 part-time): $30,000-60,000/year
- **Total: $50,000-100,000/year**

This is achievable through a combination of federated membership dues and grants. It is not a large budget. The Wikimedia Foundation runs on $150M/year. The Free Software Foundation runs on ~$5M/year. This project at Phase 2 scale costs less than a mid-level developer salary at a tech company.

### Federation and Redundancy

**Git mirrors:** The repository is currently on GitHub. It should also be mirrored to:
- GitLab (automated mirror, free)
- Codeberg (community-owned, free)
- Self-hosted Gitea instance (optional, when community capacity exists)

**Data exports:** The `data/taxonomy.yaml` and `DIRECTORY.md` are already structured for export. Any participant can download and host copies. This is intentional. The data is CC0 -- it belongs to everyone.

**No lock-in:** No tools, platforms, or services should be used that cannot be replaced or migrated away from within 30 days. If a platform disappears or changes its terms, operations continue.

---

## What WiserEarth Teaches

Paul Hawken's vision was correct. The movement existed. The network was real. The database was valuable. What failed was the infrastructure model, not the idea.

Specific lessons:

**1. Philanthropic mono-funding is a time bomb.** NCI depended on a small number of large grants. When funders shifted priorities (as foundations do), there was no fallback.

**2. Centralized hosting is a single point of failure.** WiserEarth's data was not federated. When the servers went down, everything went down. No mirrors existed. The Wayback Machine has snapshots, but the structured data is gone.

**3. Community ownership was not structural.** WiserEarth had a community, but the community didn't own the infrastructure. There was no cooperative structure, no membership model, no mechanism for the community to sustain what it had built.

**4. Closure was not announced.** Users and partner organizations got no warning. A project with 114,994 registered organizations simply disappeared. This is not just a technical failure; it is a governance failure. Any responsible project should have a documented wind-down procedure that includes data export, community notification, and preservation.

---

## Wind-Down Procedure (Required)

Every responsible infrastructure project needs a documented procedure for what happens if it must close. This is not pessimism -- it is stewardship.

If Ecolibrium must wind down:

1. **90-day public notice** posted to all channels
2. **Full data export** of directory, taxonomy, and all community contributions made available as a single downloadable archive (CC0)
3. **Documentation archive** pushed to the Internet Archive (archive.org)
4. **Git mirrors** notified and given time to update final state
5. **Handoff offer** -- active maintainers have 90 days to find a successor organization to adopt the project before any infrastructure is decommissioned
6. **No deletion** -- the GitHub repository remains public indefinitely even if unmaintained

This procedure exists so that what happened to WiserEarth cannot happen to Ecolibrium. The data belongs to the commons. It stays in the commons.

---

## Immediate Actions

These can be done now, before any funding exists:

- [ ] Create an Open Collective for Ecolibrium (5 minutes, free)
- [ ] Add GitLab mirror (automated, free)
- [ ] Add Codeberg mirror (automated, free)
- [ ] Register the domain (ecolibrium.org or similar) before someone else does (~$20)
- [ ] Add this document to the README as a linked resource

---

## Further Reading

- **Gitcoin Grants** -- gitcoin.co/grants
- **Open Collective** -- opencollective.com
- **Prototype Fund** -- prototypefund.de (German open-source civic tech grants, English applications accepted)
- **NLnet Foundation** -- nlnet.nl
- **Elinor Ostrom, "Governing the Commons"** (1990) -- the empirical foundation for commons sustainability
- **"The Tyranny of Structurelessness"** -- Jo Freeman (1972) -- on why informal structures need formalization
- **WiserEarth archive** -- web.archive.org/web/20140411042711/http://wiser.org/

---

*This document was written in April 2026. If you are reading this and the project is still running, something went right. If you are reading this because the project is in trouble, start at the Wind-Down Procedure and work backwards.*
