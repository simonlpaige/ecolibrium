# NeighborhoodOS Deep Dive and Red Team, 2026-04-21

Scope: `commonweave/neighborhood-os/` plus `commonweave/civic-identity/`. The reviewer read the vision, theory of change, README, and every source and schema file listed in the assignment, built a mental map of the whole thing, hunted for bugs and weaknesses, applied the safe fixes directly, and wrote down the rest here.

No em dashes were used. No files outside code and schema were touched. No server was started, no API was called, no git operations ran.

---

## 1. Executive summary

Eight to ten bullets, brutal honesty, in the voice of a friend telling you the thing you need to hear before you show this to anyone.

- **This is a solid v1 skeleton.** The separation into a data plane (connectors plus ingest), an identity plane (trust levels and sessions), a governance plane (proposals and voting), and a federation plane is clean. The three files most other projects screw up (schema, voting, federation) are all reasonable.
- **There are real bugs that would have stopped it from starting on a fresh box.** `index.js` had a CommonJS `require()` inside an ESM module. `api.js` used `readFileSync` without importing it. `legistar.js` used `crypto.randomUUID` without importing `crypto`. `social.js` used `require('fs')` inside ESM. All four of those were broken on day one and are now fixed.
- **The admin story is dangerous by default.** `ADMIN_TOKEN` being unset meant every admin route was open. On a Raspberry Pi exposed to a LAN or tunnel, someone could add federation peers and pull bundles. Fixed: admin routes now fail closed unless the operator explicitly sets `ALLOW_OPEN_ADMIN=1` for dev.
- **Voting authorization was missing in two places.** Any authenticated user could open a draft proposal they didn't author, and any authenticated user could close any open proposal. Both paths now require the author or a trust-4+ coordinator.
- **Federation has a replay hole.** Signatures cover only `bundle.data`, so a captured bundle could be re-submitted forever with the same or shifted envelope. Fixed: signatures now cover the full envelope (source, target, timestamp, data), receivers reject stale bundles (default 24h skew), and repeats of the exact same signature are blocked.
- **The "body_hash + salt in the same column" trick is a real smell.** It works but destroys the promise that `body_hash` detects retroactive edits. If you want the edit check back, store the salt separately. Not fixed, flagged below.
- **The liquid democracy delegation resolver is subtly wrong.** It mixes raw user IDs with blinded IDs. As written the cross-salt resolution in `tallyLiquid` cannot correctly follow A delegates to B delegates to C. Not fully fixed (needs a design call), but flagged high-severity.
- **Privacy posture is mostly good but has one slip.** The social connector is careful to discard author info, which is excellent. But the identity schema tells operators to log IP or device hints in `sessions.hint`. For a civic trust tool, "audit by IP" is surveillance by default. Recommend removing the field.
- **Hardcoded geography.** Street names, neighborhood slugs, and bounds are hardcoded to West Waldo in code. Fine for a pilot, painful for node two. Needs a per-node config file before federation is meaningful.
- **No rate limiting, no abuse controls, no audit log.** Signup, vote, federation receive, all wide open. Not fatal for a single trusted Pi, fatal the moment the URL leaks.

Bottom line: the shape is right. About a dozen concrete hardening and correctness items away from something a neighborhood association could actually use without eating a silent failure.

---

## 2. What exists today (the mental map)

### 2.1 Data plane

```
connectors/
  kc-open-data.js   Socrata puller for 311, permits, crime, violations,
                    dangerous buildings, budgets, vendor payments, zoning,
                    business licenses. Incremental by date cursor, stored in
                    a raw_records table keyed by dataset + content hash.
  legistar.js       KC city legislative record via public Legistar OData API.
                    Syncs recent matters (ordinances) and events (meetings).
                    Also owns the commitment tracker: overdue promises from
                    meetings that residents can nag about.
  social.js         Nextdoor and Facebook. Nextdoor is mostly login-gated, so
                    this file is honest about it and provides both the legal
                    API path (after agency approval) and a manual-export path.
                    Posts are stored stripped of any author metadata.
  commonweave-directory.js
                    Read-only bridge to the parent commonweave directory DB.
                    Maps neighborhood topic tags to commonweave taxonomy
                    categories and answers "who is already working on this
                    near me?"
ingest/
  sync.js           The cron entry point. Pulls everything, prints overdue
                    commitments, prints a terse status view.
```

Happy path for a neighborhood operator:

1. Start the API (`node ../civic-identity/api.js`) on the Pi.
2. Run `node ingest/sync.js` nightly from cron. The SQLite file grows, cursors advance, social posts accumulate.
3. Residents hit the web UI (not in this tree, wired over HTTP), sign up, get verified, vote.
4. Once a week, run an admin route to issue a federation bundle to peer nodes.

### 2.2 Identity plane

Trust ladder 0 to 5:

```
0  anonymous handle only
1  self-identified (email provided, not confirmed)
2  email-verified
3  neighbor-vouched (a trust-4+ resident vouched)
4  address-verified (a coordinator saw a utility bill or lease)
5  full resident (4 + one year of active participation; not automated anywhere)
```

All transitions are logged in `trust_events` with the actor, method, and a proof hash when applicable. Sessions are bearer tokens stored in `sessions`, 30-day expiry.

Happy path for a resident:

1. `POST /signup` with a handle. Gets session token. Trust 0.
2. `POST /verify-email` with an email. Gets a token (in prod would be emailed).
3. `POST /confirm-email` with that token. Trust 2.
4. Neighborhood coordinator runs `POST /vouch` from their own session. Trust 3.
5. Coordinator confirms address offline, then calls `verifyAddress` via admin path. Trust 4.
6. Trust 5 is declared but never promoted in code. Dead rung on the ladder.

### 2.3 Governance plane

Proposals support five voting methods: binary, approval, ranked (IRV), score, and liquid. Each proposal has a minimum trust level to vote, a category, a body hash for edit detection, and optional federation peer list.

Votes are stored with a blinded voter ID (HMAC of user + proposal + per-proposal salt). Individual vote-to-voter mapping is not recoverable from the blinded ID without the salt. Public tally is available; private vote is not.

Happy path for a proposal:

1. Author calls `POST /proposals` (draft).
2. Author (or a coordinator) calls `POST /proposals/:id/open`. Salt gets generated and pasted into `body_hash`.
3. Residents with sufficient trust call `POST /proposals/:id/vote`.
4. Author (or coordinator) calls `POST /proposals/:id/close`, which tallies and marks passed or failed.

### 2.4 Federation plane

Two neighborhoods agree to share. Each holds the other's public key. A bundle is built locally, signed, and sent. The receiver verifies the signature, timestamp, and peer status, then logs it in `federation_received`. Default share scope is `aggregated_votes` and `user_count`, both minimal and privacy-preserving.

Happy path for federation:

1. Admin on node A calls `POST /federation/peers` with node B's slug and pubkey. Status `pending_out`.
2. Out-of-band, node B admin adds A with status `pending_in`.
3. Both sides call `activatePeer` (there is no HTTP route for this yet, see red team).
4. Periodically, admin calls `GET /federation/bundle/:peer` and POSTs the result to the peer's `/federation/receive`.

### 2.5 Dead ends, TODOs, and stubs found in code

- `registerNeighborhoodNode` in `commonweave-directory.js` is a placeholder. Returns a message asking a human to open a GitHub issue.
- Trust level 5 exists in the ladder. No code path promotes anyone to it.
- `users.pubkey` is declared in schema but never set in `identity.js`. Vote signatures in `castVote` take `userPrivKey` from the caller, but since no keypair is ever minted for a user, that parameter is effectively dead.
- The commitment tracker has `addCommitment` and `getOverdueCommitments` but no API route. Commitments are only visible from a local CLI run.
- `activatePeer` exists in federation.js but has no HTTP route. Federation handshake is half-built.
- Nextdoor public page scrape returns "error: HTTP xxx" as a plain object, not thrown. Callers that assume thrown errors will silently ingest garbage.
- `dangerous_buildings` uses `casenumber` as its `dateField` and then special-cases that string. That is a string flag masquerading as a real field. Works, but load-bearing magic.

---

## 3. Bugs and fixes applied

All file paths relative to `commonweave/`.

| # | File:line | Fix | Why |
|---|-----------|-----|-----|
| 1 | `neighborhood-os/index.js` | Removed unused `import Database from 'better-sqlite3'`; converted the `getEcosystemRecommendations()` method from CommonJS `require` to `await import()` and marked it `async` | ESM modules cannot use `require`. Would throw on first call. |
| 2 | `neighborhood-os/connectors/legistar.js` top | Added `import crypto from 'crypto'` | `addCommitment` referenced `crypto.randomUUID` but `crypto` was never imported. ReferenceError on every call. |
| 3 | `neighborhood-os/connectors/legistar.js` searchMatters | Escape single quotes in `keyword` before interpolation into the OData `$filter` | Tiny SoQL/OData injection. A keyword with an apostrophe would either break the query or alter it. |
| 4 | `neighborhood-os/connectors/social.js` top | Added `import { readFileSync } from 'fs'` | `ingestFacebookExport` used `require('fs')` inside ESM. Would throw. |
| 5 | `neighborhood-os/connectors/social.js` ingestFacebookExport | Removed the in-function `require('fs')` | Cleaned up after fix 4. |
| 6 | `neighborhood-os/connectors/kc-open-data.js` bboxWhere | Coerce `bounds.north/south/east/west` to numbers, drop the quotes around numeric comparisons | Defense in depth against a poisoned bounds JSON, and SoQL is happier without the quotes around numeric fields. |
| 7 | `neighborhood-os/connectors/kc-open-data.js` syncDataset | Regex-validate the `since` cursor string before interpolating it into the OData filter | Stops a corrupted cursor from breaking out of the quoted literal. |
| 8 | `civic-identity/api.js` imports | Added `import { readFileSync } from 'fs'` | File was reading `NODE_PRIVKEY_PATH` without importing `readFileSync`. Top-of-file ReferenceError when `NODE_PRIVKEY_PATH` was set. |
| 9 | `civic-identity/api.js` config and `requireAdmin` | Admin routes now fail closed when `ADMIN_TOKEN` is unset, unless `ALLOW_OPEN_ADMIN=1`. Added a startup warning, a `CORS_ORIGIN` knob, and `Access-Control-Allow-Methods`. Token comparison uses `crypto.timingSafeEqual`. | The previous "no ADMIN_TOKEN means open" default was wildly unsafe on any non-loopback deployment. |
| 10 | `civic-identity/api.js` readBody | Capped body size at 64 KB (`MAX_BODY_BYTES`, overrideable). Destroys the socket on overflow | Prevents a single POST from swallowing all memory. |
| 11 | `civic-identity/api.js` /verify-email | Added `isValidEmail` shape check before calling `addEmail` | Stops obvious junk from being hashed and stored. |
| 12 | `civic-identity/api.js` /proposals | Cap title to 200 chars and body to 20,000 chars on create | Prevents a single proposal from bloating the DB. |
| 13 | `civic-identity/voting.js` openProposal | Require author or trust-4+ user to open a draft | Any signed-in anonymous account could open anyone's proposal before. |
| 14 | `civic-identity/voting.js` closeProposal | Accept an optional `actingUserId`; when supplied, require author or trust-4+ | Same issue for closing. Now enforced from the API with `session.userId`. |
| 15 | `civic-identity/voting.js` validateVoteValue | Type and length checks on option IDs; duplicate-option check for approval and ranked; score values bounded 0..10 | Before, a caller could submit arbitrary strings, nested objects, or absurd scores. |
| 16 | `civic-identity/voting.js` delegateVote | Verify the delegate user actually exists and is active | Before, you could delegate to a ghost. |
| 17 | `civic-identity/api.js` close route | Pass `session.userId` into `closeProposal` | So the new authz check in #14 is actually enforced. |
| 18 | `civic-identity/identity.js` addEmail | Validate email format, read the real current trust level for the audit event, invalidate prior pending tokens before issuing a new one | The previous version always logged `fromLevel: 0 toLevel: 1` regardless of the user's real trust level, and a user could accumulate many "pending" tokens all still valid. |
| 19 | `civic-identity/identity.js` verifyEmail | Mark the used pending event as `email_pending_used` so the token cannot be replayed | Before, the same token could be used to verify again and again. |
| 20 | `civic-identity/federation.js` buildShareBundle | Sign over the full envelope (source, target, `generatedAt`, data) instead of only `data` | Without this, a captured bundle could be re-sent with a different envelope since the signature did not cover it. |
| 21 | `civic-identity/federation.js` receiveBundle | Added envelope-scoped signature check, timestamp staleness window (24h default, overridable), 2 MB size cap, and a replay check via `federation_received` lookup by exact signature | Closes the bundle replay hole and puts a ceiling on what a misbehaving peer can push. |

---

## 4. Open issues not yet fixed, ranked by severity

### High

1. **Liquid democracy delegation is broken.** In `tallyLiquid`, when a user casts `delegate:<delegateId>`, the code stores the raw `delegateId` in the delegation map, then treats it as a `voter_blind_id` when following the chain. Since `voter_blind_id` is an HMAC and the raw `delegateId` is the plaintext user ID, they never match. Chains of length 2 or more do not resolve. The caller in `delegateVote` passes `userId: delegatorId` into `castVote`, which blinds the delegator but not the target. The right fix is to either (a) blind the target at delegation time using the same salt, or (b) store both delegator and delegate blinded IDs and resolve in the blind-space.
2. **`body_hash` no longer serves its stated purpose.** `openProposal` appends `:salt` to the column. The name of the column is `body_hash`, the schema comment says "prevents retroactive edits after votes are cast", but since the salt ruins the pure hash, you cannot verify the original body against the column anymore. Add a `voting_salt` column to `proposals` and keep `body_hash` pure.
3. **Vote signatures cannot be verified.** `castVote` takes a `userPrivKey` parameter, signs with it, and stores the signature, but `users.pubkey` is never populated. Any downstream audit that tries to verify the stored signature will fail for lack of a public key. Either generate an Ed25519 keypair at signup and store the pubkey, or drop the signature feature until you mean it.
4. **No HTTP route to accept an incoming federation request.** `addPeer` with status `pending_out` is exposed. `activatePeer` only runs inside the process. There is no `/federation/peers/:node/accept` endpoint. Federation handshake cannot complete without a shell on each node.
5. **Admin routes accept bearer tokens that are compared once against a single shared secret.** For a single-Pi deployment that is fine. For any multi-admin operation, you want per-admin tokens with revocation. Also, `ADMIN_TOKEN` has no length floor and no rotation path.

### Medium

6. **No rate limiting anywhere.** `/signup`, `/vote`, `/verify-email`, and `/federation/receive` are all unlimited. A friendly LAN makes this OK. A tunneled URL makes it a spam cannon. Recommend a simple sliding-window limiter in-process, keyed by IP and by user ID.
7. **Errors leak internal details.** `api.js` returns `err.message` directly. A SQLite error or a crypto error text is now visible to the caller. Wrap with a `toPublicError(err)` that maps to a short code plus a log line.
8. **No audit log.** Admin actions (add peer, activate peer, verify address, revoke vouch, close proposal) are not stored anywhere durable. `trust_events` covers trust changes only.
9. **CORS wildcard in dev is easy to leave in prod.** Added `CORS_ORIGIN` knob but defaulted to `*`. Flip the default to `http://localhost:<port>` once the web UI ships.
10. **`sessions.hint` is an IP log by design.** For a civic tool whose theory of change is explicitly anti-surveillance, logging IP by default is drift. Drop the column, or only populate it on explicit admin opt-in.
11. **No schema-versioning or migration path.** `ensureLegistarTables`, `ensureSocialTables`, and so on are all `CREATE TABLE IF NOT EXISTS`. That means you can add tables, but if you ever need to add a column or change a type, you are in ad-hoc migration land. Add a `schema_version` table and a tiny migrations runner. Do it before there are any live neighborhoods.
12. **The KC pagination advances by `page.length` but never records a per-record cursor.** If the dataset changes mid-sync, or the server paginates inconsistently, you can miss records. Record the last seen `dateField` as the cursor, not `new Date().toISOString()`.
13. **Nextdoor scrape is brittle and ToS-adjacent.** One class change and `memberMatch` returns null. The connector already notes this but the retry story is not written.
14. **`commonweave-directory.js` silently degrades when the directory DB is missing or the schema lacks a column.** Good for resilience, bad for operators who will not know the feature is off. Return a machine-readable `status: 'directory_unavailable'` so the UI can say why.
15. **`TOPIC_KEYWORDS.parks` includes "trolley track".** West Waldo specific. Move the topic dictionary to per-node JSON.
16. **`extractGeoHint` street patterns are hardcoded.** Same issue. Move to config.
17. **No cleanup of `trust_events` marked `email_pending_superseded`.** These accumulate forever. Add a purge job.

### Low

18. **`nextdoor` scrape returns `{ error: ... }` instead of throwing.** The sync script already prints "error" status, but this is inconsistent with the other connectors that throw. Unify.
19. **`dangerous_buildings` magic `dateField = 'casenumber'`.** Rename to `null` and handle null in `syncDataset`. The special case reads as a typo.
20. **`addCommitment` handles the "no crypto.randomUUID" fallback.** With the import fix applied, this fallback is never reached. It is still fine to keep for older runtimes, but the code should pick one path.
21. **`syncDataset` updates the cursor to `new Date().toISOString()` on success.** That silently hides the last-seen date. Store both.
22. **`addEmail` re-hashes the new email every time, but does not clear `email_hash` if the caller wants to remove it.** No `removeEmail`. Fine for now, flag as a privacy-right-to-erasure gap.

---

## 5. Red team findings, grouped

### Security

- **Fail-open admin (fixed).** The single biggest security hole. Now fails closed.
- **Federation bundle replay (fixed).** Envelope-bound signatures plus staleness window plus signature-seen check.
- **No rate limits.** High priority before any public exposure.
- **Error leakage.** Medium. Map internal errors before returning them.
- **Bearer tokens are single shared secret for admin, long-lived for users (30 days).** Consider short-lived access tokens with refresh, or at minimum a `POST /logout-all` to invalidate all sessions for a user.
- **No CSRF worry in practice** (bearer in header, not cookie), **but** if the UI ever sets cookies for convenience, that blows up.
- **No TLS story documented.** The README says "each neighborhood runs its own node" but does not mention HTTPS. On a Pi behind a WaldoNet tunnel it is fine. On the public internet it is not.
- **SoQL / OData interpolation hardened** (fixed) but worth reviewing again when more connectors land.

### Privacy and civic-tech ethics

- **Social connector is exemplary.** Strips author, truncates body, stores only content plus tags plus optional geo hint. Keep doing this.
- **`sessions.hint` as IP log is a drift** from the "transparency applies to power and resources, not to people made vulnerable by visibility" principle in `VISION.md`. Recommend dropping.
- **Nextdoor scraping of public pages** is currently very shallow (member count only). If anyone extends it to scrape posts from logged-in sessions, that becomes surveillance of neighbors without their consent. Gate behind explicit per-neighborhood opt-in config.
- **No retention policy.** `raw_records`, `social_posts`, `federation_received` all grow forever. A civic tool should document what gets deleted and when. Default to 3 years of raw city data, 90 days of social posts, forever for trust events.
- **`users.email_hash` via bcrypt is good**, but note that bcrypt-of-email is only lightly protective: the space of real emails is small enough that a targeted attacker can bcrypt a wordlist and test for presence. Recommend upgrading the doc to say "presence-resistant, not disclosure-resistant".
- **Cross-node PII leak path.** `buildShareBundle` with `proposal_text` scope exports full proposal bodies, which residents wrote and might contain an address or a neighbor's name. Add a sanitization step or require explicit author opt-in per proposal before that scope serves its body.

### Governance correctness

- **Double-vote prevention is real.** Unique `(proposal_id, voter_blind_id)` and per-proposal salt mean the same user cannot vote twice on the same proposal.
- **Trust-level spoofing at vote time** is prevented: `castVote` looks up the current `trust_level` from the DB, not from the session.
- **Vouch cycle detection:** a trust-4 resident can vouch for anyone including someone who later vouches for them. Fine, since the vouch only lifts to 3, not to 4. Still, worth documenting.
- **Ranked IRV tiebreak** arbitrary: `remaining.find(id => firstChoiceCounts[id] === lowestCount)` picks the first in array order. Document the tiebreak rule or add a deterministic tiebreak by option label hash.
- **Federation vote poisoning.** A bad node cannot forge votes into our DB (votes are never imported from peers, only aggregates). A bad node can inflate its own reported tally. There is no Byzantine resistance; the federation trusts the signatures of the peers you added. Document this clearly: federated results are the sum of what peers claim.
- **Federation-wide proposals are half-designed.** The schema has `federation_nodes` and `getFederationVoteSummary` computes a per-node summary, but there is no agreed tally combination rule. If node A has 500 trust-4 residents and node B has 50, a simple sum favors A. A population-weighted or capped rule should be specified before the first federation vote.

### Operational fragility

- **KC Open Data schema drift:** schema changes in the Socrata datasets will silently yield zero records (wrong field names) or broken queries. No schema check on each run. Recommend a "probe" at the start of each sync that SELECTs the expected fields and warns on failure.
- **Legistar rate limits:** no backoff, no retry. A transient 429 kills the sync for that run.
- **SQLite locking:** `journal_mode = WAL` is on. Good. Long-running admin queries during a sync will not block writes. But if two syncs overlap (cron and manual), they will contend. Add a simple PID lockfile.
- **Nextdoor blocking:** scrape will start returning HTML-less pages or 403. The connector swallows this as `{ error: ... }`. Operators will not know the feed is dead.
- **No retries on transient network errors.** Add exponential backoff, 3 attempts, on every `fetch` in the connectors.

### Alignment drift vs commonweave principles

- **Transparency by Default, with exceptions for people made vulnerable:** mostly respected. The one drift is `sessions.hint`. Remove it.
- **Common Ownership of the Commons:** the schema.sql is GPL-3.0 per package.json, which matches. Good.
- **Voluntary Contribution:** no coercion paths here. Good.
- **Non-Violence:** n/a.
- **Democratic Sovereignty:** the trust ladder does real work. The fact that trust-4 controls vouching AND address verification AND proposal opening/closing is, however, a concentration. One compromised coordinator can inflate trust at will. Consider requiring two trust-4+ signatures for address verification.

### Usability for a real neighborhood leader

Imagine a neighborhood association president who is not a developer.

- There is no web UI in this tree. They get an API and a CLI.
- There is no email digest. If they asked "who has overdue commitments?" they would need to SSH in and run `node ingest/sync.js`.
- There is no printable report. Everything is JSON.
- There is no SMS path. If the sewer just flooded on 79th, Nextdoor won't alert them.
- There is no mobile-friendly intake for residents to file issues.
- The commitment tracker is write-only at the moment. No API route to add or close commitments.
- Exporting a PDF of tonight's meeting agenda: not possible, though `EventAgendaFile` URLs exist in the Legistar data.

For a pilot with one technical operator, this is fine. For a real handoff, it is not. See recommendations below.

---

## 6. Recommendations to make the toolset more complete

Each item: problem, smallest fix, rough effort.

1. **Per-node config file.**
   - Problem: Neighborhood boundaries, topic dictionaries, geo hints, and slugs are hardcoded in JS. No way to stand up node two without forking code.
   - Smallest fix: a `node.config.json` loaded on startup, schema `{ slug, bounds, nextdoorSlug, facebookGroupId, topicKeywords, geoPatterns, contactEmail }`. Every connector and ingest script reads from this.
   - Effort: 3 to 4 hours.

2. **Schema-versioned migrations.**
   - Problem: Every "ensureX" function is `CREATE TABLE IF NOT EXISTS`. No way to evolve.
   - Smallest fix: add a `schema_version` table, a `migrations/` directory of numbered `.sql` files, and a 30-line runner that applies anything newer than the recorded version at startup.
   - Effort: 2 hours.

3. **Federation handshake HTTP routes.**
   - Problem: `activatePeer` has no route. Handshake cannot happen over HTTP.
   - Smallest fix: add `POST /federation/peers/:node/accept` (admin only) that flips status from `pending_in` to `active`. Add a `POST /federation/peers/request` that a peer can call to announce itself and be stored as `pending_in`.
   - Effort: 2 hours.

4. **Commitment tracker API routes.**
   - Problem: `addCommitment` and `getOverdueCommitments` exist but no route.
   - Smallest fix: `GET /commitments?status=overdue`, `POST /commitments` (trust-3+), `POST /commitments/:id/resolve` (trust-4+). Add a `follow_through_score` per committed_by person that ticks down when due dates are missed and up when kept.
   - Effort: 3 hours.

5. **Email digest via plain SMTP.**
   - Problem: Neighborhood leader wants a weekly summary, not to log into an admin panel.
   - Smallest fix: a `tools/email-digest.js` that renders markdown from the last seven days of overdue commitments, new legistar matters, top social topics, and any open proposals, then sends via `nodemailer` or local `sendmail`. Triggered by cron.
   - Effort: 4 to 5 hours.

6. **Printable meeting packet.**
   - Problem: Legistar exposes `EventAgendaFile`. Nobody links it.
   - Smallest fix: `GET /meetings/:eventId/packet` streams the concatenated agenda PDF plus minutes PDF, so the association can print one document for the board.
   - Effort: 3 hours (use `pdf-lib` to concatenate).

7. **Per-person follow-through tracker.**
   - Problem: Commitment tracker tracks promises, not people.
   - Smallest fix: `commitment_tracker_people` view that rolls `committed_by` to a promises-made, promises-kept, and rolling 12-month percentage. Expose in the digest.
   - Effort: 2 hours.

8. **Rate limiter.**
   - Problem: None.
   - Smallest fix: an in-memory sliding-window limiter keyed by IP plus session, 20 requests per minute default, applied as middleware in `api.js`. Specific limits: `/signup` 5 per hour per IP; `/vote` 60 per minute per user; `/federation/receive` 10 per minute per peer.
   - Effort: 2 hours.

9. **Audit log table.**
   - Problem: No durable record of admin action.
   - Smallest fix: add an `audit_log` table (`id, actor_user_id, actor_ip_hash, action, target_type, target_id, payload_json, created_at`). Wrap every admin route so it writes one row. Hash IPs, do not store them in plaintext.
   - Effort: 2 hours.

10. **Fix liquid delegation resolution.**
    - Problem: See Open issue 1 in section 4.
    - Smallest fix: at `delegateVote` time, compute the delegate's blind ID with the same per-proposal salt and store the delegation in blind-space. Then `tallyLiquid` can walk the chain correctly.
    - Effort: 4 hours including a decent test harness.

11. **Separate the voting salt from `body_hash`.**
    - Problem: Column abuse.
    - Smallest fix: add a `voting_salt TEXT` column via a migration. Move salt there. Leave `body_hash` pure. Add a verify-body route that recomputes the hash and checks.
    - Effort: 1.5 hours.

12. **Resident issue lifecycle table.**
    - Problem: The README mentions "resident issue reports via the Resident Voice API" but the API does not exist.
    - Smallest fix: `resident_issues (id, reporter_blind_id, category, body, geo_hint, status, created_at, acknowledged_at, resolved_at)`. Routes: `POST /issues`, `GET /issues`, `POST /issues/:id/ack`, `POST /issues/:id/resolve`. Link to `legistar_commitments` via `origin_issue_id`.
    - Effort: 3 hours.

13. **SMS alerts (optional, gated).**
    - Problem: No push channel for urgent events.
    - Smallest fix: a `sms_subscribers` table keyed by phone hash, with explicit double-opt-in. Pluggable backend (Twilio or a local Asterisk). Emit on trigger list: a trust-4+ coordinator calls `POST /broadcast` with a short message; the server fans out.
    - Effort: 6 to 8 hours. Defer until the pilot neighborhood asks.

14. **Retention policies.**
    - Problem: Nothing ever deletes.
    - Smallest fix: a `cron/retention.js` that deletes `social_posts` older than 90 days (configurable), `federation_received` older than 1 year, and expired sessions daily.
    - Effort: 1.5 hours.

15. **Drop `sessions.hint`.**
    - Problem: IP logging by default clashes with the anti-surveillance stance.
    - Smallest fix: schema migration that drops the column. Any logging that operators want should go to a separate, off-by-default file.
    - Effort: 30 minutes plus a migration.

16. **Two-operator address verification.**
    - Problem: One captured coordinator can inflate trust to level 4.
    - Smallest fix: require two distinct trust-4+ approvals before the promotion to level 4 commits. Record both in `trust_events`.
    - Effort: 2 hours.

17. **User keypair at signup.**
    - Problem: `users.pubkey` is never set, `castVote` signature path is dead.
    - Smallest fix: on `registerAnonymous`, generate an Ed25519 keypair. Store the pubkey. Optionally return the private key once to the client so they can save it. Or drop the signature field entirely until you mean it.
    - Effort: 3 hours.

18. **Connector health probe.**
    - Problem: A Socrata schema change silently returns zero.
    - Smallest fix: `probeDataset(db, key)` fetches one record with `$limit=1` and checks for expected fields. Run as the first step of each connector in `sync.js`. On failure, set a `connector_status` row and write the diff to a log file.
    - Effort: 2 hours.

19. **Federation vote aggregation rule.**
    - Problem: No rule on how to combine per-node tallies.
    - Smallest fix: write `federation/aggregate.md` that specifies two modes: one-person-one-vote sum across nodes (default), and one-node-one-vote caucus mode. Code a `combineFederationResults(results, mode)` util. Refuse to report a federation result unless every listed node has reported or timed out.
    - Effort: 3 hours and a writeup.

20. **Printable proposal ballot.**
    - Problem: Not every resident is online.
    - Smallest fix: `GET /proposals/:id/ballot.pdf` that emits a paper ballot with a QR code that encodes the proposal ID. Residents mark it at the coordinator's table and the coordinator keys in the votes from the paper.
    - Effort: 4 hours.

---

## 7. What is strong and should not change

- **The vision-to-code alignment.** The schema says "we blind voter IDs", and the voting code actually blinds them. A lot of civic-tech projects declare things and then quietly store PII. This one does not.
- **The social connector's privacy posture.** Aggressively strips author info, caps content length, and explicitly says "we never store individual user profiles from social platforms". Keep doing exactly that.
- **`openDB` pragmas.** `journal_mode = WAL` and `foreign_keys = ON` at startup. Both are right. A lot of projects forget the second one.
- **The trust ladder as an explicit table, not a boolean.** Lets the community set `min_trust` per proposal category. Surveys at 2, board votes at 4. Good.
- **Connectors each expose an `ensureXTables` function.** The node can come up from a blank SQLite file in seconds. Good for the Raspberry Pi story.
- **`commonweave-directory.js` opens the directory DB read-only.** Small detail, correct decision. The neighborhood node cannot accidentally corrupt the global directory.
- **The voter receipt** `{ blindId, proposalId, value, signature, castAt }` is exactly the right shape. A voter can prove to themselves that they voted, without being able to prove to anyone else how they voted. Keep it.
- **Federation default scope is minimal.** `aggregated_votes` and `user_count` only. Richer scopes require explicit opt-in. Keep this default.
- **The README calls social "signal, not ground truth".** This framing should be preserved in every new doc. It is what keeps the whole thing from drifting into a surveillance engine for residents.
- **Voice in the README and this project.** Plain language, opinions audible, no marketing adjectives. This is Commonweave's voice. Hold that line.

---

## Files touched in this review

- `commonweave/neighborhood-os/index.js` (fixed)
- `commonweave/neighborhood-os/connectors/legistar.js` (fixed)
- `commonweave/neighborhood-os/connectors/social.js` (fixed)
- `commonweave/neighborhood-os/connectors/kc-open-data.js` (fixed)
- `commonweave/civic-identity/api.js` (fixed)
- `commonweave/civic-identity/voting.js` (fixed)
- `commonweave/civic-identity/identity.js` (fixed)
- `commonweave/civic-identity/federation.js` (fixed)

No philosophical, governance, or vision docs were modified. No files were deleted. No git operations ran. No server was started. No external APIs were called.
