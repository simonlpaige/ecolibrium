# Open Problem: What Happens When the Framework Is Used Against Itself?

**Category: Security / Threat Modeling | Difficulty: Hard | Status: Mostly unaddressed**

---

The framework currently says: "Co-option is hard when everything is visible. Infiltration is meaningless when there is nothing hidden to discover. The openness *is* the security model."

We've come to think this is half right and half wishful thinking. This post is our attempt to be more honest about the threat surface.

## What transparency does protect against

Transparency genuinely does make some attacks harder:

- It's difficult to secretly redirect a project's goals when every decision is public and archived.
- It's difficult to claim false authority when the contribution history is visible.
- It reduces certain kinds of insider fraud (no hidden fund movements, no secret deals).

These are real benefits, and we're not abandoning the commitment to openness.

## What transparency does not protect against

**Flooding.** An open project can be overwhelmed with noise - low-quality contributions, bad-faith issues, coordinated "concern trolling" that consumes maintainer time without producing insight. The signal-to-noise ratio collapses. The original contributors burn out. Wikipedia, Stack Overflow, and every major open-source project has faced versions of this. Transparency doesn't prevent it.

**Strategic co-option.** A foundation or corporation can publicly endorse a project, offer funding, propose governance changes "for sustainability," and gradually redirect it toward industry-friendly goals - all in the open. Greenwashing of environmental movements happens in public. This is a pattern, not a hypothetical.

**Doxxing and harassment.** Open participation means visible participation. In adversarial environments - which includes any context where the framework's goals threaten concentrated wealth or political power - contributor visibility is a security liability. We can say "use pseudonyms if you need to," but that's individual operational security, not a project-level security design.

**State surveillance.** Open coordination makes it trivial to map a movement's structure, identify key contributors, and preemptively disrupt organizing. This isn't paranoia - it's the documented history of COINTELPRO, the surveillance of Standing Rock organizers, the pre-emptive arrests before the 2004 Republican National Convention protests. If Ecolibrium ever becomes consequential enough to threaten significant power, open coordination is a liability in ways that the current document doesn't acknowledge.

**The specific problem in our context.** The framework's Mycelial Strategy describes building alternative systems to the point where the old systems become optional. If that ever works, it directly threatens entities with enormous resources and legal authority. The moment it works is precisely the moment the threat model becomes most serious - and the moment the current "transparency is security" model is least adequate.

## The historical cases we need to reckon with

**COINTELPRO (1956-1971).** The FBI's domestic surveillance program infiltrated, disrupted, and discredited civil rights organizations, the Socialist Workers Party, and the American Indian Movement - primarily through legal tools: informants, forged letters, leaks to employers, smear campaigns. The organizations targeted were largely nonviolent. Openness didn't protect them because the attack vectors didn't require secrecy.

**The Standing Rock Surveillance.** Internal TigerSwan documents (published by The Intercept in 2017) showed private security contractors and law enforcement treating pipeline protesters as "insurgents" and running coordinated intelligence operations against an entirely peaceful movement. Open coordination made mapping the movement straightforward.

**Corporate co-option of sustainability.** The history of corporate capture of environmental certification systems (LEED, FSC, Rainforest Alliance) is a case study in how open, well-intentioned governance processes can be redirected through sustained institutional pressure - all in public.

## What we don't know how to solve

We don't have a clean answer here. Some honest tradeoffs:

If the project is fully open, it's surveyable and disruptable by adversaries with resources. If the project has operational security, it looks like the sock puppet operations and intelligence fronts it wants to distinguish itself from. There's no clean resolution.

Some approaches worth exploring:

- **Tiered participation.** Public-facing work is fully open. Contributor identity protections are available for those in adversarial contexts. The project distinguishes "open decisions" from "protected contributors."
- **Threat modeling by phase.** The security requirements for a small open-source project are different from those of an organization with political significance. Build in security review triggers.
- **Learning from other movements.** How did the early labor movement handle infiltration? How do contemporary mutual aid networks balance openness with operational security? There's accumulated knowledge here we haven't drawn on.

## What we're asking for

- Has anyone done serious security design for a political/economic transition project that isn't a state actor? Not corporate information security - the specific challenge of a distributed, open, politically consequential project.
- What does the history of social movements tell us about the point at which operational security becomes necessary vs. counterproductive? There's a version of this where excessive security posture is itself the attack (making the movement appear dangerous, reducing participation).
- The IRS, FBI, and corporate intelligence services have tools specifically designed for open-source intelligence on civil society organizations. What do we actually know about those capabilities, and what does designing against them look like without becoming a closed cell?
- Is there a "safety valve" design - where the project can operate openly in low-risk contexts and shift posture if the threat environment changes, without losing its character?

We're asking because we genuinely don't know. The current document's answer - "openness is the security model" - was written by someone (us) who had been thinking about software security, not movement security. These are different problems.

---

*Ecolibrium is an open design document for a post-labor economy. [Repository](https://github.com/simonlpaige/ecolibrium). Author: Simon L. Paige.*
