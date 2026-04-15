# Ecolibrium Data Quality Audit Plan

## Problem
698K orgs, ~5.9% obviously contaminated (41K), ~78% have zero alignment signal (544K at score 0). The dataset is mostly noise from the IRS BMF bulk import.

## Three-Pass Audit

### Pass 1: Hard Exclusion (pattern-based, instant)
Remove orgs matching ANY of these patterns. No exceptions:
- **Religious worship**: church, parish, diocese, synagogue, mosque, temple, chapel, congregation, ministry, baptist, methodist, lutheran, presbyterian, pentecostal, evangelical, bible, gospel, worship (KEEP: faith-based social services like "Catholic Charities", "Lutheran Services", "Islamic Relief")
- **Social/fraternal clubs**: golf club, country club, yacht club, rotary, lions, kiwanis, elks, moose, eagles, VFW, american legion, masonic, freemason, odd fellows, knights of columbus, shriners, fraternal order
- **HOAs/property**: homeowners association, HOA, condo association, property owners
- **Booster/parent orgs**: booster club, boosters, PTA, PTO, PTSO, parent teacher
- **Cemetery/funeral**: cemetery, funeral, memorial park, burial
- **Pet hobby**: kennel club, cat club, dog club, breed club, horse show, pony club, rodeo
- **Professional guilds**: bar association, medical association, dental association, real estate association, trade association, industry association
- **Political**: republican party, democratic party, political action committee, PAC, campaign committee
- **Corporate/LLC**: LLC, Inc (alone isn't bad but LLC is)
- **Alumni**: alumni association (unless clearly serving community purpose)

Expected removal: ~50-60K orgs

### Pass 2: Alignment Scoring (enhanced classifier)
Re-score remaining orgs with a stricter classifier:

**STRONG POSITIVE (must have at least one to stay):**
- cooperative, co-op, mutual aid, indigenous, agroecology, solidarity economy, restorative justice, community land trust, worker-owned, participatory, civic tech, open source, renewable energy, food sovereignty, community health, affordable housing, environmental justice, human rights, refugee, asylum, community development, social enterprise, fair trade, microfinance, community organizing, grassroots, advocacy, public interest, civil liberties, community foundation

**MODERATE POSITIVE (helps but not sufficient alone):**
- community, environmental, health, education, housing, food, energy, justice, rights, youth, disability, senior, immigrant, nonprofit, foundation, volunteer, conservation, sustainability, resilience

**AUTOMATIC KEEP (high-value org types regardless of keywords):**
- Any org with "cooperative" or "co-op" in name
- Any org with "land trust" in name
- Any org with "mutual aid" in name
- Any org with "community development" in name/desc
- Any org with "credit union" in name
- Known frameworks: B-Corp, Community Interest Company, Social Enterprise

**Threshold**: Must have alignment_score >= 1 (at least one moderate positive keyword match) to survive Pass 2.

Expected removal: ~400-500K orgs (the bulk of zero-signal noise)

### Pass 3: ML Classifier (XGBoost on labeled data)
Train a binary classifier on a hand-labeled sample:
1. Randomly sample 1000 orgs
2. Hand-label each as KEEP or REMOVE
3. Features: name tokens, description tokens, framework_area, country, source, org type keywords
4. Train XGBoost (the same model stack we use for cryptobot)
5. Apply to all remaining orgs
6. Remove orgs with P(keep) < 0.5
7. Flag orgs with 0.5 < P(keep) < 0.7 for manual review

### Post-Audit Validation
- Random sample 100 orgs from survivors: manual check, target <5% false positive rate
- Random sample 100 from removed: manual check, target <5% false negative rate
- If either rate exceeds 5%, refine and re-run

## Implementation Order
1. Pass 1 NOW (5 minutes, pure SQL)
2. Pass 2 TODAY (re-run classifier with stricter rules)
3. Pass 3 THIS WEEK (needs labeled data + training)

## Ongoing Quality Gate
Every new country ingest must pass through all 3 filters before orgs enter the active dataset. No more bulk-insert-then-hope.
