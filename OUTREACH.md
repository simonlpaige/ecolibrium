# Outreach & Collaboration Guide

> *How to connect with allied projects and invite collaboration. For any agent or contributor reaching out on behalf of Ecolibrium.*

---

## Principles of Outreach

1. **Lead with respect.** These projects have been doing this work for years. We are newcomers learning from them, not saviors arriving to coordinate them.
2. **Be specific.** Don't ask for vague "collaboration." Identify exactly what Ecolibrium can offer and what we'd like to learn or integrate.
3. **Be transparent.** Ecolibrium is anonymous, open-source, and has no funding. Say this upfront. It's a strength, not a weakness.
4. **No pressure.** An invitation is not an obligation. Respect no-responses and declinations gracefully.
5. **Credit everything.** When integrating ideas from other projects, cite them prominently. Attribution is non-negotiable.

---

## Outreach Template

Use and adapt this template when reaching out via GitHub Issues, Discussions, or email:

---

**Subject:** Invitation to collaborate — Ecolibrium open-source transition framework

**Body:**

Hi [Project Name] team,

I'm reaching out from Ecolibrium, an open-source framework for peaceful societal transition toward post-scarcity, commons-based, ecologically sustainable systems. The project is anonymous by design — no founders, no leaders, no personality cult. Just the work.

We've been researching existing projects in this space, and [Project Name] stands out as [specific reason — e.g., "the most mature participatory democracy platform available" / "the pioneering model for commons-based land stewardship" / "a critical proof of concept for community-owned energy"].

We've referenced your work in our research document and would like to explore how we might collaborate. Specifically, we're interested in:

- [Specific ask #1 — e.g., "Integrating Decidim as the recommended governance platform in our framework"]
- [Specific ask #2 — e.g., "Learning from your deployment experience in [context]"]
- [Specific ask #3 — e.g., "Cross-referencing our framework with your policy proposals"]

We're not asking for endorsement or commitment — just a conversation about whether our work might be mutually useful.

Our repository: [link]
Our research on your project: [link to relevant section of RESEARCH.md]

Thank you for the work you do.

— Ecolibrium Contributors

---

## Contact List: Priority Outreach Targets

### Tier 1: Core Infrastructure Projects (Reach out first)

| Project | Platform | Contact Method | What We Want |
|---------|----------|----------------|--------------|
| **Decidim** | github.com/decidim | GitHub Discussions or Matrix chat | Adopt as recommended governance platform; learn from deployment |
| **Open Food Network** | github.com/openfoodfoundation | GitHub or community forum | Integrate as food distribution infrastructure |
| **Community Health Toolkit** | github.com/medic | GitHub or communityhealthtoolkit.org | Reference as healthcare delivery model |
| **OpenMRS** | github.com/openmrs | Talk forum (talk.openmrs.org) | Understand health records integration |
| **ElectionGuard** | github.com/Election-Tech-Initiative | GitHub Discussions | Integrate for verifiable voting |
| **Open Source Ecology** | github.com/OpenSourceEcology | Wiki or forum | Cross-reference GVCS with our infrastructure needs |

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

## Setting Up the Anonymous GitHub Account

### Step 1: Create a Pseudonymous Email
- Use ProtonMail (proton.me) — end-to-end encrypted, no personal info required.
- Choose a project-related address (e.g., ecolibrium@proton.me).

### Step 2: Create the GitHub Account
- Go to github.com and sign up with the ProtonMail address.
- Use a project name as the username (e.g., `ecolibrium-framework`).
- Do not add a profile photo, real name, or location.

### Step 3: Configure Git for Anonymity
Before making any commits, configure your local Git to use the pseudonym:
```bash
git config --global user.name "Ecolibrium"
git config --global user.email "ecolibrium@proton.me"
```

### Step 4: Create the Repository
```bash
# Initialize the repository
mkdir ecolibrium && cd ecolibrium
git init

# Add files
git add .
git commit -m "Initial framework: bones and details we can infer"

# Create the remote repository on GitHub (do this via the web interface first)
git remote add origin https://github.com/ecolibrium-framework/ecolibrium.git
git push -u origin main
```

### Step 5: Repository Settings
- **Visibility:** Start public (per the "open from the start" principle). If you need private first, set to Private and flip to Public when ready.
- **License:** CC BY-SA 4.0 (already specified in README).
- **Topics:** Add tags: `post-scarcity`, `commons`, `transition`, `democracy`, `sustainability`, `open-framework`.
- **Discussions:** Enable GitHub Discussions for community conversation.
- **Issues:** Enable and create issue templates for different contribution types.

### Step 6: Invite Collaborators
- Go to Settings → Collaborators → Add people.
- Invite trusted contributors by their GitHub username.
- For the public model: anyone can fork and submit pull requests. No invitation needed.

### Step 7: Security Considerations
- Never access the account from a network tied to your real identity if anonymity is critical.
- Consider using a VPN or Tor when managing the account.
- Do not link to any personal social media accounts.
- Remember: Git commit metadata (timestamps, etc.) can reveal timezone patterns. Be aware.

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
