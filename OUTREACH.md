# Outreach & Collaboration Guide

> *How to connect with allied projects and invite collaboration. For any agent or contributor reaching out on behalf of Ecolibrium.*

---

## Principles of Outreach

1. **Lead with respect.** These projects have been doing this work for years. We are newcomers learning from them, not saviors arriving to coordinate them.
2. **Be specific.** Don't ask for vague "collaboration." Identify exactly what Ecolibrium can offer and what we'd like to learn or integrate.
3. **Be transparent.** Ecolibrium is authored by Simon Paige, open-source, and has no funding. Say this upfront. The honesty does more work than a pitch.
4. **No pressure.** An invitation is not an obligation. Respect no-responses and declinations gracefully.
5. **Credit everything.** When integrating ideas from other projects, cite them prominently. Attribution is non-negotiable.

---

## Outreach Template

> **Positioning note.** We are a new, small project reaching out to mature, battle-tested projects that have been doing this work for a decade or more. The message is *we learned from you, here is what we took, here is how Ecolibrium might be useful to you* — never *please slot into our framework*. If a draft message can be read as "come be part of our thing," rewrite it.

Use and adapt this template when reaching out via GitHub Issues, Discussions, or email:

---

**Subject:** Learning from [Project Name] — a new open-source transition directory

**Body:**

Hi [Project Name] team,

I'm reaching out from Ecolibrium — a small, early-stage open-source project that is cataloguing the existing network of commons-based, cooperative, and transition organisations and connecting it to a set of working notes on post-labor economic design. We are new. You are not. The point of this message is to learn from you, not to pitch you.

**What we took from your work.** We've been reading [specific artifact — e.g., "your Decidim governance model documentation" / "the Open Food Network federated-hub architecture" / "your Community Health Toolkit deployment case studies"] and it shaped our thinking on [specific section with link to the exact commit / line in our repo]. We cite you in RESEARCH.md and have tried to credit specifically rather than generically.

**Two things we would value, if you have bandwidth.**

- **Correction:** Is anything in our summary of your project wrong, stale, or misleading? We would rather learn it from you than ship it.
- **One question:** [A single, specific, answerable question tied to their actual expertise — e.g., "What surprised you most about production Decidim deployments that your docs don't cover?" Not: "Would you like to integrate with us?"]

**What we might offer, if useful.** We are building a directory of transition-aligned organisations across 60 countries (currently ~24,500 entries, filtered from a much larger registry import) with open data and a public search index. If that would be useful to your community (for example, as a way for practitioners in your network to discover adjacent work), we're happy to expose your projects' data the way you want it exposed, not the way we want to absorb it.

No response needed. If you are busy — which you are — a silent "noted" is a completely fine outcome.

Our repository: [link]
Our reference to your work: [link to specific section]

With respect,

— Simon Paige, Ecolibrium (simonlpaige/ecolibrium)

---

## Contact List: Priority Outreach Targets

### Tier 1: Core Infrastructure Projects (Reach out first)

> Columns renamed: *What we learned* = what shaped our thinking. *One question* = the single specific question we want to ask, never a request for integration or endorsement.

| Project | Platform | Contact Method | What we learned / One question |
|---------|----------|----------------|--------------------------------|
| **Decidim** | github.com/decidim | GitHub Discussions or Matrix chat | Their governance model informed our approach; ask what production deployments struggle with that isn't in the docs |
| **Open Food Network** | github.com/openfoodfoundation | GitHub or community forum | Their federated-hub model shaped our thinking on food distribution; ask what they'd correct in our summary |
| **Community Health Toolkit** | github.com/medic | GitHub or communityhealthtoolkit.org | Their deployment case studies shaped our healthcare section; ask which claims we should hedge |
| **OpenMRS** | github.com/openmrs | Talk forum (talk.openmrs.org) | Their 40+ country deployment experience informed our healthcare delivery notes; ask about integration pitfalls we should warn readers about |
| **ElectionGuard** | github.com/Election-Tech-Initiative | GitHub Discussions | Their end-to-end verifiability model informs our voting section; ask what assumptions in our summary are wrong |
| **Open Source Ecology** | github.com/OpenSourceEcology | Wiki or forum | GVCS informs our infrastructure notes; ask what they wish newcomers understood before referencing their work |

### Tier 2: Governance & Economics Projects

| Project | Platform | Contact Method | What We Want |
|---------|----------|----------------|--------------|
| **Liquid Democracy e.V.** | github.com/liqd | Email via liqd.net | Learn from Adhocracy+ deployments |
| **OpenDemocracy AI** | github.com/AshmanRoonz/OpenDemocracy | GitHub Issues | Explore AI governance integration |
| **Doughnut Economics Action Lab** | doughnuteconomics.org | Contact form | Adopt Doughnut framework for economic measurement |
| **Wellbeing Economy Alliance** | weall.org | Contact form | Align with WEAll network and policy agenda |
| **P2P Foundation** | wiki.p2pfoundation.net | Wiki or email | Integrate Commons Transition Plan insights |

### Tier 3: Movement & Knowledge Projects

| Project | Platform | Contact Method | What We Want |
|---------|----------|----------------|--------------|
| **International Center for CLTs** | cltweb.org | Email | Document CLT model as land transition template |
| **Grounded Solutions Network** | groundedsolutions.org | Contact form | Access CLT implementation resources |
| **GiveDirectly** | givedirectly.org | Contact form | Reference UBI evidence base |
| **Guaranteed Income Pilots Dashboard** | guaranteedincome.us | Contact form | Link to as living evidence base |
| **Impact Justice RJ Project** | impactjustice.org | Email | Document restorative justice models |
| **Common Justice** | commonjustice.org | Email | Reference as violent felony ATI model |
| **Vera Institute** | vera.org | Email | Access criminal justice reform research |

### Tier 4: Technical Infrastructure

| Project | Platform | Contact Method | What We Want |
|---------|----------|----------------|--------------|
| **Kolibri / Learning Equality** | github.com/learningequality | GitHub | Recommend as offline education platform |
| **Belenios** | belenios.org | Email | Evaluate as voting system option |
| **VoteSecure / Mobile Voting Foundation** | GitHub | GitHub Issues | Track mobile voting development |
| **Sophia Protocol** | GitHub | GitHub Issues | Explore governance + UBI integration |

---

## Outreach Workflow

### Step 1: Prepare
- Read the project's documentation, contribution guidelines, and code of conduct.
- Identify the appropriate channel (some projects prefer GitHub Issues, others have forums or mailing lists).
- Draft a message using the template above, customized with specific references to their work.

### Step 2: Reach Out
- Post on the appropriate channel.
- Keep the message concise — under 300 words.
- Include a link to our repository and the relevant section of RESEARCH.md.

### Step 3: Follow Up
- If no response in 2 weeks, send one polite follow-up.
- If still no response, move on. Respect silence.
- If they respond positively, open a GitHub Issue in our repository documenting the conversation and any agreed collaboration.

### Step 4: Document
- Record all outreach attempts in the `outreach-log.md` file (see template below).
- Update RESEARCH.md with any new information or corrections they provide.
- Credit collaborations prominently in the README.

---

## Outreach Log Template

Create a file called `outreach-log.md` and track all contact:

```markdown
# Outreach Log

## [Project Name]
- **Date:** YYYY-MM-DD
- **Channel:** GitHub Issues / Email / Forum
- **Message sent:** [link or summary]
- **Response:** Pending / Positive / Declined / No response
- **Follow-up:** [date and notes]
- **Outcome:** [what was agreed, integrated, or learned]
```

---

## Contributor Identity Guidance

Ecolibrium is authored under Simon Paige's real name. Contributors are not required to follow suit.

- **If you want to use your real name:** great. Commit under your own identity, show up in Discussions, take credit for your work.
- **If you need to stay pseudonymous:** also fine. Work under a handle, use a ProtonMail address, keep your timezone metadata clean if that matters to your situation. This is framed as *contributor protection*, not project mystique. At-risk contributors, people inside hostile institutions, and anyone whose employment or safety would be threatened by public participation should use whatever operational security they need. The maintainers will not ask you to unmask.
- **What the project will not do:** the project will not pretend to be "anonymous by design" while a named maintainer exists. That contradiction was a credibility bug and has been retired.

---

## Repository Structure

```
ecolibrium/
├── README.md              # The framework (main document)
├── RESEARCH.md            # Deep dive research on each area
├── OUTREACH.md            # This document
├── CONTRIBUTING.md        # How to contribute (create this next)
├── CODE_OF_CONDUCT.md     # Community standards (create this next)
├── LICENSE                # CC BY-SA 4.0
├── outreach-log.md        # Track all outreach attempts
└── areas/                 # Deep-dive folders for each framework area
    ├── voting/
    ├── healthcare/
    ├── food/
    ├── education/
    ├── land/
    ├── energy/
    ├── justice/
    ├── economics/
    └── digital-commons/
```

---

## Final Note

The goal of outreach is not to build a coalition under the Ecolibrium banner. It is to connect existing work into a coherent whole — and to make sure the people who have been doing this work for years know that someone is trying to weave their efforts together.

The framework succeeds when it becomes unnecessary — when the systems it describes are simply how the world works.
