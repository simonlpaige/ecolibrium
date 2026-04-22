# Civic Identity System

> Sign up as a neighbor. Earn trust. Vote on things that matter. Federate with other neighborhoods.

Part of NeighborhoodOS / Commonweave. Runs on neighborhood-owned hardware.

---

## What It Is

Three things in one system that grow together:

1. **Signup** - Get a handle. Start at zero trust. No data required.
2. **Trust Verification** - Earn higher trust levels by verifying your email, getting vouched by a neighbor, or having a coordinator verify your address.
3. **Federated Voting** - Propose things. Vote on them. Share results (not raw votes) with other neighborhoods.

---

## Trust Levels

| Level | Name | How to Get It | What It Unlocks |
|-------|------|---------------|-----------------|
| 0 | Anonymous | Just sign up with a handle | Read, comment on discussion |
| 1 | Self-identified | Provided email (not yet verified) | Nothing extra yet |
| 2 | Email-verified | Clicked the link | Surveys, advisory votes |
| 3 | Neighbor-vouched | A verified resident vouched for you | Full neighborhood votes |
| 4 | Address-verified | Coordinator checked a bill or lease | Can vouch for others |
| 5 | Full resident | Level 4 + 1 year of participation | Constitutional proposals |

**The floor for meaningful civic votes is level 3.** That means either:
- A neighbor at level 4+ vouches "I know this person lives here," or
- A coordinator checks your address.

Surveys and lightweight feedback work at level 2 (email verified).

---

## Voting Methods

| Method | Use Case | How It Works |
|--------|----------|--------------|
| `binary` | Yes/no decisions | Yes, no, or abstain. Simple majority. |
| `approval` | Pick your favorites | Select any options you support. Highest count wins. |
| `ranked` | Elections, priority lists | Rank options 1, 2, 3. Instant runoff. |
| `score` | Rate proposals 1-5 | Average score per option. Useful for budgets. |
| `liquid` | Delegation democracy | Vote yourself or delegate to a trusted neighbor. |

---

## Privacy Model

**The vote is yours. Who you voted for is not stored.**

- Your voter ID is **blinded** per-proposal using HMAC. Nobody can trace a vote back to you, even with DB access.
- You get a **receipt** after voting. You can verify your vote was counted.
- **Aggregate tallies** are public. Individual vote-to-voter mapping is not.
- Your email is stored as a **bcrypt hash**, not plaintext.
- Nothing is sold. Nothing feeds advertising. No engagement loops.

---

## Federation Model

Each neighborhood runs its own node. Federation is opt-in and bilateral.

**What gets shared (default):**
- User counts by trust level (how many verified residents)
- Aggregated vote tallies on closed proposals (yes: 34, no: 12 - not who voted what)

**What stays local forever:**
- Individual votes
- Email hashes
- Session tokens
- Raw user records

**What can be shared with explicit consent:**
- Full proposal text (so other neighborhoods can see what you decided)
- Detailed vote breakdowns

Federation lets neighborhoods ask: "Is the city doing this to us specifically, or to everyone?" and coordinate responses across district lines without surrendering autonomy.

---

## File Structure

```
civic-identity/
  schema.sql           - Base SQLite schema (users, votes, proposals, federation peers)
  migrations.js        - Tiny versioned migrations runner
  migrations/          - Numbered SQL migrations applied in order
  identity.js          - Registration, trust levels, vouching, sessions, Ed25519 keypair at signup
  voting.js            - Proposals, voting, tallying (binary, approval, ranked IRV, score, liquid)
  federation.js        - Peer management, envelope-signed bundles, replay+staleness guards
  audit.js             - Durable audit log for privileged actions (IPs hashed, not stored raw)
  rate-limit.js        - In-process sliding-window rate limiter
  issues.js            - Resident issue lifecycle (file, acknowledge, resolve)
  commitments.js       - Commitment tracker (who promised what, who kept what)
  retention.js         - Prune job for expired sessions, old social posts, rate-limit rows
  api.js               - HTTP API server (pure Node, no framework)
  smoke-test.js        - End-to-end sanity test for the main flows
  federation-smoke.js  - Federation handshake + replay + tamper tests
  README.md            - This file
```

---

## Quick Start

```bash
# Install deps
npm install better-sqlite3 bcrypt

# Start the API
NODE_SLUG="westwaldo@waldonet.local" \
PORT=4242 \
DB_PATH=./civic-identity.db \
node api.js
```

**Register a user:**
```bash
curl -X POST http://localhost:4242/signup \
  -H "Content-Type: application/json" \
  -d '{"handle":"neighbor42"}'
# Returns: {"user": {...}, "token": "..."}
```

**Create a proposal:**
```bash
curl -X POST http://localhost:4242/proposals \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Install traffic calming on 75th Street",
    "body": "Proposal to request the city install speed humps on 75th between Wornall and Holmes...",
    "category": "policy",
    "voteMethod": "binary",
    "minTrust": 3
  }'
```

**Vote:**
```bash
curl -X POST http://localhost:4242/proposals/<id>/vote \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"value": "yes"}'
# Returns a receipt with your blinded voter ID
```

---

## Running the Smoke Tests

```bash
# Install deps first (in neighborhood-os/, which hosts node_modules)
cd ../neighborhood-os && npm install && cd ../civic-identity

node smoke-test.js            # end-to-end identity + voting + audit + retention
node federation-smoke.js      # federation bundle build/receive/replay/tamper
```

Both tests use temp SQLite files and clean up after themselves.

## Hardening Features (post 2026-04-21 deep dive)

- **Fail-closed admin.** Admin routes refuse to serve unless `ADMIN_TOKEN` is set. `ALLOW_OPEN_ADMIN=1` opens them for local dev only.
- **Ed25519 keypair at signup.** Private key is returned once at signup and never stored. Public key lives on the user row; vote signatures are verified on cast.
- **Separated voting salt.** `body_hash` stays a pure hash; the per-proposal salt lives in `voting_salt`. `GET /proposals/:id/verify-body` surfaces tampering.
- **Liquid delegation in blind-space.** Delegation chains resolve across multiple hops and never leak raw user ids.
- **Federation replay + tamper guard.** Envelope-signed bundles, 24h staleness window, and signature-seen check.
- **Rate limiter.** Sliding-window limits on signup, vote, email, federation receive, and a generic per-IP cap.
- **Audit log.** Every admin and trust-changing action is recorded; IPs are HMAC-hashed with a node-local salt.
- **Issues + commitments API.** Residents can file issues; coordinators (trust 4+) close them out. Commitments link back to originating issues.
- **Connector health probe.** `ingest/sync.js` probes each dataset before pulling; status is in `connector_status`.
- **Versioned migrations.** Schema evolves via numbered `migrations/*.sql` files, tracked in `schema_version`.

## Roadmap

- [ ] **Email sending** - currently returns the token directly (dev mode). Wire up Resend.
- [ ] **Address verification UI** - admin screen for coordinators to review and approve
- [ ] **Liquid democracy UI** - show delegation chain, let users see who they delegated to
- [ ] **Federation sync cron** - periodic bundle exchange with active peers
- [ ] **Whisper integration** - auto-extract commitments from meeting transcripts
- [ ] **Election-grade audit** - generate Belenios-compatible audit log for high-stakes votes
- [ ] **Mobile-friendly web UI** - static HTML, works offline, designed for neighborhood meetings

---

## Connection to Commonweave

This is Commonweave's "Democratic Infrastructure" layer made concrete.

From `BLUEPRINT.md`:
> "Verifiable, tamper-resistant voting at local scale" ✓ (this)
> "Liquid democracy options" ✓ (this)
> "Mandatory inclusion for marginalized voices" → vouching system + low barrier entry
> "Recall and accountability mechanisms" → recall category in proposals

And from NeighborhoodOS:
> The Layer 4 (Resident Voice) + Layer 5 (Federation) infrastructure is this system.

---

*Larry (AlphaWorm AI) + Simon L. Paige, April 2026*
