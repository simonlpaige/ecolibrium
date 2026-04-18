# Open.coop, PLANET, and the First Person Project: Research Brief for Ecolibrium

> Created 2026-04-17. Researched at Simon's request after the Open.coop relaunch announcement.
>
> **TL;DR:** The Open Co-op is relaunching around a project called PLANET, a member-owned "cooperating system" for the regenerative economy. PLANET depends on a trust-infrastructure layer being built by the First Person Project under the Linux Foundation Decentralized Trust initiative. If the trust layer ships, it solves a problem Ecolibrium has not yet addressed: **verifiable identity and reputation across commons-based networks without central-platform capture**. Ecolibrium should (1) follow this closely, (2) adopt the verifiable-credentials pattern for directory-entry provenance, and (3) list Open.coop + PLANET in the directory once it is operational.

## Sources

1. The Open Co-op, "Relaunching The Open Co-op: Preparing for a Trust-Based Internet," 2026-03-20. <https://open.coop/2026/03/20/relaunching-the-open-co-op-preparing-for-a-trust-based-internet/>
2. First Person Project homepage. <https://www.firstperson.network/>
3. Linux Foundation Decentralized Trust. "Decentralized Trust Infrastructure at LF: A Progress Report." Cited in source 1. <https://www.lfdecentralizedtrust.org/blog/decentralized-trust-infrastructure-at-lf-a-progress-report>
4. ZDNet. "Linux kernel maintainers' new way of authenticating developers and code." Cited in source 1. <https://www.zdnet.com/article/linux-kernel-maintainers-new-way-of-authenticating-developers-and-code/>
5. Open.coop collaboration portal. <https://collab.open.coop/>

Trust statistics quoted from source 1 (verification left for future work):
- OECD 2023: 15% of people trust social media
- Pew 2024: 22% of people trust governments
- Gallup 2023: 27% of people trust banks
- OECD 2023: 32% of people trust news media

## What The Open Co-op is saying

Paraphrased from source 1, with direct quotes flagged.

The Open Co-op has worked for twenty-plus years toward "a cooperative, regenerative economy - one that is owned and governed by its participants, and designed to serve people and planet over profit."

They argue the internet has always lacked "a way to know who and what you can trust," and that for the first time this is being solved at infrastructure level. They are relaunching to ship **PLANET**, described as "a member-owned co-operating system to support collaboration at scale" and "a cooperating system for the collaborative regenerative economy."

The trust layer PLANET rides on is being built by the **First Person Project** in collaboration with **Linux Foundation Decentralized Trust** and "a global consortium of other projects."

Key evidence that the trust layer is serious: the Linux kernel community is itself exploring this infrastructure to harden its code-contribution chain after the 2024 XZ Utils backdoor. If it is being evaluated by kernel maintainers, it is more than cooperative-movement wishful thinking.

The value proposition of the trust layer, in their words:

> "By enabling verifiable identity, cryptographic proof of authorship, and transparent trust relationships, it becomes possible to know not just what code is being contributed, but who is behind it, how they are trusted, and how that trust was established."

Extended to communities:

> "An internet where identity and trust based relationships can be owned by individuals and communities. Where reputation travels with you. Where cooperation can scale without central control."

## What this means for Ecolibrium

### 1. It fills a hole in our framework we have not named

Ecolibrium's BLUEPRINT specifies Transparency by Default and Common Ownership of the Commons, but does not answer: **in a federated, leaderless, commons-based network, how do participants know which other participants to trust?**

The prior self-critique (CRITIQUE.md section 3) hit the "leaderless" problem from the governance side. The trust-infrastructure side is a different dimension:
- How do we know an org listed in the directory is who it claims to be?
- How do a bioregional cooperative and a digital commons project in another country federate without a central platform brokering trust?
- How do we prevent the Sybil attack (one actor, many fake identities) that kills most decentralized systems?

"Verifiable identity + cryptographic proof + transparent trust relationships" is a direct answer. If the First Person Project ships a working protocol, it becomes a tool Ecolibrium can use rather than invent.

### 2. PLANET is a peer, not a competitor

Ecolibrium's directory and PLANET's cooperating system solve different layers:
- **Directory (Ecolibrium):** Who exists, what they claim, and where. Optimized for discovery.
- **Cooperating system (PLANET):** How discovered entities collaborate, govern, share resources, and surface reputation. Optimized for operation.

A mature Ecolibrium directory is a great input for PLANET (here are the aligned entities to federate with). A mature PLANET generates trust signals that Ecolibrium can use as relevance inputs (this org has sustained high-trust collaboration with five other aligned orgs over three years).

Action: list Open.coop and PLANET in DIRECTORY once PLANET is operational, under a new or expanded category for digital commons / cooperating infrastructure.

### 3. The verifiable-credential pattern is directly adoptable

Even before the First Person protocol ships, Ecolibrium can adopt the pattern for directory-entry provenance:
- Each directory entry has a declared source (government registry, Wikidata, researcher bot, self-submission).
- Each entry could eventually carry cryptographically signed attestations: "verified by [federation X] on [date]," "co-signed by [member org Y]."
- Attestations degrade the reliance on keyword scoring as the only relevance signal. Instead, trust is earned through a web of other verified entities vouching for an entry.

This is the **web-of-trust** idea (Zimmermann, 1991) re-expressed for the commons era. The concrete W3C spec to watch: Verifiable Credentials Data Model 2.0 (<https://www.w3.org/TR/vc-data-model-2.0/>). Decentralized Identifiers (DIDs): <https://www.w3.org/TR/did-core/>.

### 4. Digital Commons needs a first-class taxonomy category

MULTILINGUAL-TERMS.md section 7 flags this. Currently the pipeline buries digital commons / open source / platform cooperativism inside broader categories. DeepSeek R1 noted only ~40 entries end up in "Energy & Digital Commons" despite this being a fast-growing globally-networked sector.

Concrete: split the existing category into "Energy Commons" and "Digital Commons," and add explicit keywords:
- platform cooperative, platform co-op, data trust, commons-based peer production, federated, fediverse, ActivityPub, Matrix protocol, peer-to-peer, self-sovereign identity, verifiable credentials, DID, decentralized trust, solidarity cloud, cooperatively-owned infrastructure

### 5. Ideas worth lifting directly into Ecolibrium framing

From source 1, rewritten as framework additions:

- **"Reputation travels with you."** Ecolibrium's directory entries should carry portable reputation artifacts that can move with an org if it leaves the directory or federates into a PLANET-style network.
- **"Cooperation can scale without central control."** Re-centers the federation problem in BLUEPRINT Phase 1. Add a "federation readiness" subsection describing what technical and governance primitives must exist before Ecolibrium can claim to be federation-ready.
- **"Outsourced trust to the big tech giants."** Frame the directory's independence as a trust-re-insourcing project. The directory is not just a list; it is a community asset that refuses to route trust through Google, Meta, LinkedIn, or X.
- **"Building the social layer alongside the technical one."** Useful language for arguing against the techno-solutionist reading of Ecolibrium. Add to VISION or THEORY-OF-CHANGE.

## What to add to the project

### To GOVERNANCE.md (new section)
**Trust and Verification in a Commons-Based Directory**

Short section describing: (1) the Sybil and impersonation threats to any open directory; (2) verifiable-credentials / DID as the emerging standards; (3) the web-of-trust model as interim architecture; (4) the explicit plan to align with First Person / Linux Foundation Decentralized Trust primitives once stable. Cite sources 1-4.

### To DATA.md (new field)
Add an `attestations` JSON array field to each org record:
```
attestations: [
  { issuer: "wikidata", date: "2026-01-12", type: "existence", signature: null },
  { issuer: "us-irs-bmf", date: "2026-03-01", type: "legal-registration", signature: null },
  { issuer: "opencoop", date: "2026-04-10", type: "federation-member", signature: "..." }
]
```
Initially `signature` is null and attestations are trust-on-source. When the W3C VC-compatible tooling is ready, attestations become cryptographically verifiable without schema change.

### To MULTILINGUAL-TERMS.md (already added)
Section 7: Digital Commons, Platform Cooperativism. Needs expansion into non-English (Spanish "plataforma cooperativa", French "coopérative de plateforme", Italian "cooperativa di piattaforma", etc. - already seeded).

### To OUTREACH.md
Add Open.coop, First Person Project, and Linux Foundation Decentralized Trust to the outreach list under a new tier: **Infrastructure Peers**. Not targets for directory inclusion yet (Open.coop is a co-op; PLANET is pre-launch), but natural collaborators.

## Open questions

1. **When will First Person ship something usable?** Source 1 says "not yet fully ready" but "advancing quickly." We should monitor, not wait on it.
2. **Does PLANET compete with Fediverse/ActivityPub approaches?** Unclear from the announcement. Worth asking Open.coop directly.
3. **Is the trust protocol open-standard or Linux-Foundation-scoped only?** The announcement conflates the two. Verifiable credentials and DIDs are W3C; the LF Decentralized Trust project ships implementations. We should track both layers.
4. **Licensing of PLANET?** Not stated in the announcement. Will matter for adoption by Ecolibrium-aligned orgs.

## Recommendation

1. **Now:** Merge this brief into project docs. Add digital-commons keyword expansion to MULTILINGUAL-TERMS. Add the `attestations` field to the DATA schema (as spec, not yet required).
2. **This month:** Email Open.coop via <https://collab.open.coop/>. Offer to list them in the directory once PLANET launches, and ask for a reciprocal mention or any published federation interface they are designing.
3. **This quarter:** Watch the First Person Project for a public developer release. If it lands, prototype a VC-attestation on a small sample of directory entries (say, 50 hand-verified Kansas City orgs) as a pilot.
4. **Ongoing:** If PLANET ships, add it to the directory and use its federation protocol in place of anything Ecolibrium would otherwise build in-house. No reinventing here.
