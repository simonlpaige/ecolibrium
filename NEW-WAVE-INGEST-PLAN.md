# New Wave Ingest Plan

*Source: `commonweave org finder new wave.md` (Simon's desk, 2026-04-25). Written 2026-04-25 by Larry.*

## What the new wave doc actually is

Two things stitched together:

1. **A country-by-country atlas of national legal-entity registries** (~190 sovereign/state-like jurisdictions). Each row tells us: registrar name, URL when verified, languages, what entity types are covered (company / cooperative / nonprofit / charity / community-company), update frequency, access cost, and whether the search portal was confirmed reachable or just an "authority anchor."
2. **A second layer of thematic global directories** for the things national registries miss: cooperatives & solidarity economy, community land trusts, mutual aid, intentional communities, transition networks, indigenous and informal organizations, and regional umbrella networks (RIPESS, ASEC, RAESS, ICA-Africa, ASEC, ECLAC).

It explicitly maps these to the Commonweave field families: **legal form, purpose/activity code, governance/ownership, public-benefit status, community signals.** That mapping is the part we should keep — it's a screen we can build into our scorer.

## What we already have

Today's ingest universe (from `DATA.md` + `data/`):

| Layer | What's in | Coverage |
|---|---|---|
| **National registries** | IRS BMF (US), UK Charity Commission (E&W), Wikidata (global, structured-data subset) | 88% of rows are US/UK |
| **Thematic** | OFN, Wikidata unions/CLTs/housing co-ops, ITUC affiliates, Grounded Solutions, Habitat international, construction co-ops | ~1,400 rows total, all `legibility='formal'` |
| **Per-country research bots** | Researcher scripts for HN, BO, EC, GY, NG, PY, SR, VE | ~58 rows so far (rounding error vs. registries) |
| **Dispatcher** | `ingest_india.py` (TODO list of 10 India sources, only Wikidata-India wired up) | 0 rows from local-language registries |
| **Total** | 24,508 aligned orgs, 60 countries | 88% US/UK |

The new wave doc is essentially a **190-row TODO list** that, if even half-executed, breaks the US/UK skew that `DATA.md` flags as the #1 known issue.

## Gap analysis: new wave vs. current ingest

What the new wave gives us that we don't have:

1. **A complete country roster.** Today we have ad-hoc per-country researcher scripts for 7 Latin American countries. The new wave names every jurisdiction and tags whether a portal is verified or authority-only. That's a ready-made queue.
2. **Confirmed-reachable URLs for ~30 countries** (Algeria CNRC, Angola GUE, Botswana CIPA, Nigeria CAC, Zambia PACRA, Antigua ABIPCO, Dominica CIPO, Brunei ROCBN, Fiji businessNOW, Palau FIC, Solomon Islands Company Haus, Samoa BR, Vanuatu VFSC, Bulgaria, Estonia, Denmark CVR, Czech ARES, India MCA, Japan Corporate Number, Taiwan, Vietnam, etc.). These are immediately scriptable.
3. **Field-family mapping** — legal form, purpose text, governance, public-benefit, community signals. We currently score on keyword-in-description; the new wave tells us *which registry fields to look for* before scoring.
4. **The OHADA cluster** (15 francophone African countries sharing one RCCM registry architecture). One ingester pattern, 15 countries' worth of coverage.
5. **Mission-first national systems** explicitly in scope: Solomon Islands (community companies + charitable orgs), Dominica (non-profit companies), Vanuatu (charitable associations), Antigua (charities + societies), Palau (nonprofit corps), Bulgaria NPO register, Moldova NPO register, Australia ACNC, NZ Charities Services, Israel GuideStar, Brazil Mapa das OSCs.
6. **Thematic networks we haven't touched.** Find.coop, Data Commons Cooperative, ICA Cooperatives Connect, .coop directory, NEC, RIPESS LAC, RAESS, ASEC, SUSY Map, Mutual Aid Wiki, Intentional Communities Directory, Transition Network maps, CLT World Map, CPRI (Common Property Resource Institutions) — all missing today.
7. **Indigenous + informal coverage** — explicitly the layer that registries miss. PIAALC, IRI, OD Mekong Datahub, Aboriginal co-ops Canada, BC Indigenous services, Jawun, Waste Pickers (WAW). Today we have zero rows from this layer.

What we have that the new wave doesn't really cover:
- Bulk machine-readable IRS / UK Charity Commission ingest at scale.
- Wikidata SPARQL pulls (the new wave names Wikidata once; we already lean on it heavily).
- ProPublica enrichment for US.

So the two are complementary. The new wave is mostly **net-new sources outside the US/UK lens**.

## The plan

Three waves, sized so each one ships in days, not months. Squash mode.

---

### Wave A — Mission-first national registries (highest signal-to-noise, ~2 weeks)

These are the registries the new wave doc explicitly calls out as having a public-benefit / nonprofit / community-entity tier searchable. They give us aligned orgs by *legal form*, no keyword scoring required.

**Targets, with verified URLs:**

| Country | Registry | URL | Why first |
|---|---|---|---|
| Bulgaria | Commercial Register + Register of NPOs | `portal` (NPO register integrated) | Native nonprofit register |
| Moldova | State Register of Nonprofit Organizations | authority | Native nonprofit register |
| Australia | ACNC Charity Register | `acnc.gov.au` | National charity API + bulk CSV |
| New Zealand | Charities Services | `charities.govt.nz` | National charity API |
| Israel | GuideStar Israel | `guidestar.org.il` | National nonprofit directory |
| Brazil | Mapa das OSCs + Receita Federal CNPJ | `mapaosc.ipea.gov.br` | OSC tags by purpose, plus CNPJ for legal-form |
| Solomon Islands | Company Haus | `solomonbusinessregistry.gov.sb` | Charitable orgs + community companies in scope |
| Dominica | CIPO | `cipo.gov.dm` | Non-profit companies as a registration class |
| Antigua & Barbuda | ABIPCO | `abipco.gov.ag/searchtheregister/` | Charities + societies searchable |
| Vanuatu | VFSC entity search | `vfsc.vu/entity-search/` | Charitable associations searchable |
| Palau | FIC Corporations Registry | `palauregistries.pw` | Nonprofit corps explicit |
| Samoa | Samoa BR | `businessregistries.gov.ws/samoa-br-companies/` | Director/shareholder data |
| Philippines | SEC non-stock corporation search | `sec.gov.ph` | Non-stock = nonprofit form |
| India | MCA Section-8 / CSR companies | `mca.gov.in` | Section-8 = nonprofit |
| Poland | KRS (associations + foundations) | `ekrs.ms.gov.pl` | Associations / foundations visible inside KRS |
| Ukraine | NGO register | authority | National NGO register |
| Saudi Arabia | National nonprofit regulator | authority | Charities/associations split out |

**Pattern:** one ingester per registry, written to mirror `ingest_grounded_solutions.py`. Each:
- Caches raw HTML/JSON/CSV at `data/sources/<source>-cache/`
- Writes rows with `source='<country_code>_<registry>'`, `legibility='formal'`, `source_id=<official ID>`
- Idempotent on `source_id`
- Honors `--dry-run` and `--refresh`
- Logs to `data/ingest-<source>-run.log`

**Estimated yield:** 50,000–150,000 new aligned rows once Brazil's Mapa das OSCs and India's MCA Section-8 land. That's a 2–6x bump on current 24,508.

---

### Wave B — Thematic global networks (moderate effort, big mission-fit, ~1 week)

These are mission-first by definition. Smaller row counts but every row is high-alignment.

**Targets:**

1. **Find.coop** — North American cooperative directory. `findcoop.com`. Stone-soup directory; check for an export endpoint.
2. **Data Commons Cooperative** — member-owned, may need a partnership ask (good outreach hook for `@alphaworm`).
3. **ICA Cooperatives Connect** — global cooperative directory by ICA. `coopsconnect.coop`. Check for API.
4. **.coop global directory** — every org with a `.coop` domain. There is a published list.
5. **SUSY Map** — 1,200+ EU social/solidarity economy initiatives. Geocoded. Should be scrapeable.
6. **New Economy Coalition** — 200+ member orgs, US/Canada. Member directory on the site.
7. **RIPESS** + **RIPESS LAC** + **RAESS** + **ASEC** — umbrella networks. Each has a member list. Smaller but high-signal.
8. **Mutual Aid Wiki** — crowd-sourced GitHub dataset. Already structured. Easy ingest, marks `legibility='informal'`.
9. **Intentional Communities Directory** — 1,200+ communities globally (`ic.org`). Has search/JSON.
10. **Transition Network** — local groups map. Geocoded.
11. **CLT World Map + Directory** (Schumacher Center) — 600+ CLTs globally. Filterable by use type.
12. **CPRI (Common Property Resource Institutions)** — 138 indigenous resource-management cases, 20+ countries. Honey Bee Network / SRISTI.

**Pattern:** mostly web-scrape with caching. Several have JSON or CSV exports already. Each gets one ingester, same conventions as Wave A.

**Estimated yield:** ~5,000–10,000 high-alignment rows, heavily concentrated outside US/UK. This is where the legibility tags `hybrid` and `informal` start showing up.

---

### Wave C — The long tail: country atlas + indigenous/informal (rolling, indefinite)

For the ~140 countries the new wave lists where the registry is "authority-anchor only" or behind logins, we extend the existing per-country research-bot pattern (`run_researcher_*.py`) instead of building one ingester per country.

**Approach:**

1. **Convert the new wave's country atlas into a queue file**: `data/QUEUE-new-wave.txt` with one line per (country, registry, URL, languages, registry-type, verified?, notes). Researcher bot reads this instead of the old QUEUE.txt.
2. **Generalize `run_next_country.py`** so it dispatches to:
   - A dedicated ingester if Wave A or B added one
   - The web-research bot otherwise (existing pattern)
   - An "opaque-jurisdiction" stub that just records the registrar authority page and moves on (for North Korea, Vatican, Turkmenistan, etc. — explicitly opaque per the new wave)
3. **Indigenous / informal layer** gets its own queue: `data/QUEUE-informal.txt`. Pulls from PIAALC, IRI, Aboriginal co-ops Canada, BC Indigenous services, Jawun, Waste Pickers WAW. These rows always tag `legibility='informal'` or `'hybrid'` and never auto-archive (the staleness check already protects them).
4. **OHADA cluster** is one ingester for 15 countries. Worth doing in this wave because the architecture is shared.

**Estimated yield:** unknown but slow — a few hundred rows per country, with strong geographic balance. The point of Wave C is closing the US/UK skew, not raw row count.

---

## Method changes (cross-cutting)

Three pipeline upgrades the new wave forces us to make:

1. **Field-family scorer.** Right now `phase2_filter.py` scores on description keywords. Add a second axis: **legal-form score**. If `legal_form ∈ {cooperative, community_company, non_profit_company, charitable_organization, association, foundation, social_enterprise, CIC, section_8_company, OSC, benefit_corp}`, that's a +3 alignment bump independent of description. This lets non-English registries score high even with thin descriptions.
2. **Verified-URL registry.** Add `data/sources/REGISTRIES.yaml` cataloging every country's registrar with: name, URL, language, auth required, update frequency, last-checked date, what entity classes are exposed. Sourced from the new wave doc, then maintained by the weekly auditor. This becomes the canonical "what we know about each country's drawer" file. Replaces the scattered notes in ingester docstrings.
3. **Legibility ladder gets used in the map.** Today legibility is stored but the public map doesn't show it. Add a filter so visitors can choose "formal only" / "include hybrid" / "include informal." This is the public-facing piece that makes Wave C politically defensible — informal/indigenous orgs are visible without being hidden in the "registered" pile.

---

## Sequencing & first concrete steps

This is a **plan, not a commit**. Simon's call on whether to start.

If yes:

1. **Today (1 hour):** I write `data/sources/REGISTRIES.yaml` from the new wave doc. Pure transcription; no code.
2. **Wave A first three (3–5 days):** Bulgaria NPO + Australia ACNC + Brazil Mapa das OSCs. Highest yield, all have public APIs or bulk downloads, all have native nonprofit registers. Confirms the pattern works on three different continents.
3. **Then iterate:** add 2–3 Wave A ingesters per week, alternating with one Wave B ingester per week. Each one ships independently to the directory.
4. **Field-family scorer + map legibility filter** can ship in parallel with Wave A — they're not blocking.
5. **Wave C queue + OHADA ingester** after Wave A is ~80% done.

## Estimated total impact

If Waves A+B fully ship: directory grows from **24,508 → ~80,000–180,000 aligned orgs**, US/UK share drops from **88% → ~50–60%**, and Energy & Digital Commons (currently 40 rows) gains a real seed via cooperative networks.

The bigger win is **methodological**: we stop being "an English-language nonprofit list with some thematic add-ons" and start being "a global directory with explicit legibility labels and a transparent registry catalog." That's the version of Commonweave that survives the next round of red-teaming.

---

## Open questions for Simon

1. **Wave A first three** — are Bulgaria NPO + Australia ACNC + Brazil Mapa das OSCs the right opening, or do you want a different mix? (E.g., Solomon Islands or Vanuatu would be smaller-yield but more on-thesis for "community-companies as a legal form.")
2. **Indigenous/informal layer** — comfortable shipping a public map filter that surfaces these with `legibility='informal'` tags, or do you want to gate that behind a separate page until we've curated harder?
3. **Outreach overlap** — Data Commons Cooperative and Find.coop might be partnership conversations, not scrape targets. Worth routing through `tools/mycelial-outreach/` (@alphaworm) before scraping?
4. **Pace** — squash-mode default would be one Wave A ingester every 2–3 days. Faster (one a day) or slower (weekly)?

No code written yet. This is the plan; tell me which wave to start, or which ingester to prototype first.
