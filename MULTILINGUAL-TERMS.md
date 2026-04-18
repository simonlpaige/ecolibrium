# Multilingual Relevance Terms for the Ecolibrium Pipeline

> Created 2026-04-17. Addresses false-negative problem in `data/phase2_filter.py` STRONG_POS and the researcher bot search-query templates.
>
> **The problem:** The pipeline searches and scores almost entirely in English, with a handful of tokens in Spanish, French, Indonesian, Arabic, and German. The Nigeria researcher (`run_researcher_ng.py`) searches in English + ethnic-group names, never in Hausa, Yoruba, or Igbo. Same pattern across every non-US/UK country script. Result: we cannot *find* the aligned orgs we cannot name.

This file is the source of truth for multilingual terms. It is organized by **concept**, not by language, so the same concept (e.g. "worker cooperative") can be expanded across many languages in one place.

Each concept block lists:
- The **Ecolibrium principle(s)** it supports (from BLUEPRINT.md)
- **Terms** in local languages with rough transliterations where relevant
- **Where to use**: `STRONG_POS` (score +3), `MODERATE_POS` (+1), or `SEARCH_QUERIES` (researcher bots)
- **Caveats** where the term is polysemous or co-optable

## Pipeline integration plan

1. `data/i18n_terms.py` - single Python module exports `STRONG_POS_MULTI`, `MODERATE_POS_MULTI`, `SEARCH_TERMS_BY_LANG`. `phase2_filter.py` imports it.
2. Researchers get a lightweight `build_local_queries(country, topic)` helper that pulls the right language set.
3. All terms are lowercase and UTF-8. Match is done with `term in combined.lower()` after NFC normalization.

---

## 1. Worker / Producer Cooperatives
**Principle:** Common Ownership, Voluntary Contribution, Democratic Sovereignty

| Language | Term(s) | Notes |
|---|---|---|
| English | cooperative, co-op, worker-owned, employee-owned, worker cooperative | Already present |
| Spanish | cooperativa, sociedad cooperativa, cooperativa de trabajo, cooperativa obrera | "De trabajo asociado" = worker co-op in Argentina |
| Portuguese | cooperativa, cooperativa de trabalho, cooperativa popular | Brazil has massive cooperativa movement |
| French | coopérative, société coopérative, SCOP (société coopérative et participative), SCIC | SCOP = worker co-op in FR |
| Italian | cooperativa, cooperativa di lavoro, società cooperativa | Italy's Legacoop / Confcooperative federations |
| German | Genossenschaft, eG (eingetragene Genossenschaft), Produktivgenossenschaft | eG is the legal suffix |
| Dutch | coöperatie, coöperatieve vereniging | |
| Russian | кооператив (kooperativ), артель (artel), производственный кооператив | Artel = pre-Soviet + Soviet worker guild |
| Polish | spółdzielnia, spółdzielnia pracy | |
| Mandarin | 合作社 (hézuòshè), 生产合作社 (shēngchǎn hézuòshè), 工人合作社 | Widely state-linked; validate carefully |
| Japanese | 協同組合 (kyōdō kumiai), 労働者協同組合 (rōdōsha kyōdō kumiai) | 2022 Worker Cooperative Act passed |
| Korean | 협동조합 (hyeopdong johab), 노동자협동조합 | 2012 Framework Act on Cooperatives |
| Indonesian/Malay | koperasi, koperasi pekerja, koperasi produsen | |
| Tagalog | kooperatiba, kooperatibang manggagawa | |
| Vietnamese | hợp tác xã, hợp tác xã lao động | |
| Thai | สหกรณ์ (sahakon), สหกรณ์การผลิต | |
| Hindi | सहकारी समिति (sahkari samiti), श्रमिक सहकारी | |
| Bengali | সমবায় সমিতি (samabay samiti) | |
| Urdu | کوآپریٹو (cooperative), تعاونی سوسائٹی (taawuni society) | |
| Turkish | kooperatif, işçi kooperatifi, üretim kooperatifi | |
| Arabic | تعاونية (ta'awuniya), شركة تعاونية (sharika ta'awuniya), جمعية تعاونية | MSA; dialectal variants exist |
| Persian/Farsi | تعاونی (ta'avoni), شرکت تعاونی کارگری | |
| Swahili | ushirika, chama cha ushirika | Kenya/Tanzania |
| Hausa | kungiya ta hada-hadar tattalin arziki, kungiyar manoma | Northern Nigeria, Niger |
| Yoruba | egbe ajose, egbe agbe | Southwestern Nigeria |
| Igbo | otu nkwado, otu oru | Southeastern Nigeria |
| Amharic | የህብረት ስራ ማህበር (yehbret sera mahber) | Ethiopia |
| Zulu | inhlangano yokusebenzelana, i-cooperative | |
| Xhosa | umbutho wokusebenzisana | |
| Hebrew | קואופרטיב (ko'operativ), קיבוץ (kibbutz), מושב שיתופי (moshav shitufi) | Kibbutz has drifted; validate |

**Caveats:**
- "Cooperative" in many countries includes **corporate co-ops** (agribusiness, insurance, supermarket chains) that are not aligned. Use in combination with signals like member count vs revenue, legal form, and federation affiliation.
- In China and Vietnam, state-directed cooperatives are common. Ownership claim often differs from practice.
- Kibbutz: many have privatized. Filter by current governance, not historical name.

---

## 2. Mutual Aid / Solidarity Economy
**Principle:** Universal Sufficiency, Voluntary Contribution

| Language | Term(s) | Notes |
|---|---|---|
| English | mutual aid, solidarity economy, commons | Already partially present |
| Spanish | ayuda mutua, economía solidaria, economía social | Brazil/Argentina/Spain have formal "ES" sector |
| Portuguese | ajuda mútua, economia solidária, economia popular | Brazilian Secretaria Nacional de Economia Solidária existed until 2016 |
| French | entraide, économie solidaire, économie sociale et solidaire (ESS) | France has ESS law (2014) |
| Italian | mutuo soccorso, società di mutuo soccorso (SMS), economia solidale | SMS = 19th-century tradition, still exists |
| German | Solidarische Ökonomie, Genossenschaftsbewegung | |
| Russian | взаимопомощь (vzaimopomoshch), общество взаимопомощи | |
| Mandarin | 互助 (hùzhù), 团结经济 (tuánjié jīngjì) | |
| Japanese | 互助 (gojo), 連帯経済 (rentai keizai) | |
| Korean | 상호부조 (sanghobujo), 연대경제 (yeondae gyeongje) | |
| Indonesian | **gotong royong**, tolong menolong, koperasi solidaritas | Gotong royong is constitutional principle |
| Malay | gotong-royong, bantu-membantu | |
| Tagalog | bayanihan, damayan | Bayanihan = community cooperation tradition |
| Vietnamese | tương trợ, giúp đỡ lẫn nhau | |
| Thai | ช่วยเหลือเกื้อกูล (chuai lueu), น้ำใจ (nam jai) | Nam jai = mutual generosity, cultural concept |
| Hindi | परस्पर सहायता (paraspar sahayata), स्वयं सहायता समूह (SHG) | SHG = self-help group, huge in India |
| Bengali | স্বনির্ভর গোষ্ঠী (swanirbhar goshthi) | Self-help groups |
| Urdu | باہمی امداد (bahami imdad) | |
| Turkish | dayanışma, imece | Imece = traditional collective labor |
| Arabic | **waqf** (charitable endowment), تكافل (takaful), تعاون (ta'awun) | Takaful = Islamic mutual insurance |
| Swahili | msaada wa pande zote, harambee | Harambee = Kenyan self-help tradition |
| Hausa | gayya (communal labor tradition) | |
| Yoruba | owe (reciprocal labor exchange), esusu (rotating savings) | |
| Igbo | isusu (rotating savings), igba boyi | |
| Amharic | ድር (idir - burial society), equb (rotating savings) | |
| Zulu | ilima (collective labor), stokvel (rotating savings) | |
| Xhosa | ilima, umgalelo | |
| Quechua | ayni (reciprocal labor), **minga/minka** (collective work) | Andes: Peru, Bolivia, Ecuador |
| Aymara | ayni, mink'a | |
| Nahuatl | tequio | Mexico |

**Caveats:**
- Waqf in some modern contexts has been appropriated by states (Egypt, Saudi Arabia). Distinguish community waqf from state waqf.
- Harambee in Kenya has been politically captured at times. Check for political-patronage signals.
- Rotating savings (esusu, susu, tanda, hui, chama) are informal and usually invisible to digital registries. Include as SEARCH_TERMS, not scoring keywords.

---

## 3. Commons, Common Lands, Shared Resources
**Principle:** Common Ownership of the Commons, Ecological Equilibrium

| Language | Term(s) | Notes |
|---|---|---|
| English | commons, community land trust, common land, commoning | Already partially present |
| Spanish | **ejido**, comunidad agraria, bienes comunales, tierras comunales | Mexico: ejido = post-revolution land commons |
| Portuguese | quilombo, baldios, terras de uso comum, fundo de pasto | Quilombo = Afro-Brazilian maroon communities |
| French | biens communaux, terres communales, commun, communs | |
| Italian | usi civici, beni comuni, proprietà collettiva | Usi civici = medieval common-land tradition |
| German | Allmende, Gemeingut, Gemeinschaftsgut | |
| Russian | община (obshchina), общинное землевладение | Pre-Soviet peasant commune |
| Mandarin | 公地 (gōngdì), 集体土地 (jítǐ tǔdì) | State-collective, not same as commons |
| Japanese | 入会地 (iriai-chi), コモンズ (komonzu) | Iriai-chi = traditional village commons |
| Korean | 공유지 (gongyuji), 마을공동체 (maeul gongdongche) | |
| Indonesian | tanah ulayat, tanah adat | Customary land |
| Thai | ที่ดินสาธารณะ (tidin satharana), ป่าชุมชน (pa chumchon) | Community forest |
| Vietnamese | đất công, rừng cộng đồng | |
| Hindi | साझा भूमि (sajha bhoomi), गोचर (gochar) | Gochar = village grazing commons |
| Arabic | **hima** (protected commons), musha'a (shared land) | Hima = pre-Islamic + Islamic pastoral commons |
| Turkish | mera (pasture commons), orman köyleri | |
| Swahili | ardhi ya kijiji, ardhi ya jamii | |
| Zulu | umhlaba wesizwe, indlu yesizwe | |
| Quechua | ayllu (kinship-land unit) | |
| Maori | whenua (ancestral land), iwi (tribal land) | |
| Inuktitut | nunavut ("our land") | |

**Caveats:**
- Many of these are under active enclosure or formalization pressure from states. Current legal status varies. Include as SEARCH_TERMS; downstream verification is required.
- Chinese "集体土地" is collective in name, not in commons-governance practice. Do not auto-score.

---

## 4. Agroecology, Food Sovereignty, Seed Commons
**Principle:** Ecological Equilibrium, Universal Sufficiency

| Language | Term(s) | Notes |
|---|---|---|
| English | agroecology, food sovereignty, seed library, regenerative agriculture | Already partially present |
| Spanish | agroecología, soberanía alimentaria, semillas criollas, semillas nativas | La Vía Campesina origin |
| Portuguese | agroecologia, soberania alimentar, sementes crioulas | |
| French | agroécologie, souveraineté alimentaire, semences paysannes | |
| Italian | agroecologia, sovranità alimentare, sementi contadine | |
| German | Agrarökologie, Ernährungssouveränität, bäuerliches Saatgut | |
| Hindi | कृषि पारिस्थितिकी, खाद्य संप्रभुता, देसी बीज (desi beej) | |
| Tamil | உணவு இறையாண்மை | |
| Swahili | kilimo-ikolojia, uhuru wa chakula, mbegu asilia | |
| Arabic | زراعة بيئية (zira'a bi'iya), سيادة غذائية (siyada ghida'iya) | |
| Thai | เกษตรนิเวศ (kaset niwet), อธิปไตยทางอาหาร | |
| Indonesian | pertanian agroekologi, kedaulatan pangan | |
| Korean | 농생태학 (nongsaengtaehak), 식량주권 (sikryang jugwon) | |
| Japanese | アグロエコロジー, 食料主権 (shokuryō shuken) | |

---

## 5. Community Health, Care, Healing
**Principle:** Universal Sufficiency

| Language | Term(s) | Notes |
|---|---|---|
| English | community health, free clinic, community health worker | Already present |
| Spanish | salud comunitaria, promotor de salud, centro de salud comunitario | |
| Portuguese | saúde comunitária, agente comunitário de saúde | Brazil's ACS program = world-scale model |
| French | santé communautaire, maison de santé | |
| Arabic | صحة مجتمعية (sihha mujtama'iya) | |
| Swahili | afya ya jamii, kituo cha afya | |
| Hindi | सामुदायिक स्वास्थ्य, आशा कार्यकर्ता (ASHA worker) | ASHA = India's community health program |

---

## 6. Democratic / Participatory Governance
**Principle:** Democratic Sovereignty, Transparency

| Language | Term(s) | Notes |
|---|---|---|
| English | participatory budgeting, citizen assembly, commons governance | |
| Spanish | presupuesto participativo, asamblea ciudadana, consejo comunal | Porto Alegre origin |
| Portuguese | orçamento participativo, assembleia popular | |
| French | budget participatif, assemblée citoyenne, démocratie participative | |
| Italian | bilancio partecipativo, assemblea cittadina | |
| German | Bürgerhaushalt, Bürgerrat | |
| Mandarin | 参与式预算 (cānyù shì yùsuàn), 居民议事会 | |
| Japanese | 市民参加, 参加型予算 | |
| Arabic | الموازنة التشاركية (mawazana tasharukiya) | |

---

## 7. Digital Commons, Platform Cooperativism
**Principle:** Common Ownership, Democratic Sovereignty, Transparency

| Language | Term(s) | Notes |
|---|---|---|
| English | platform cooperative, platform co-op, open source, digital commons, data trust, commons-based peer production | Add these - only "open source" currently implied |
| Spanish | plataforma cooperativa, cooperativa de plataforma, bienes comunes digitales | |
| Portuguese | cooperativa de plataforma, bens comuns digitais | |
| French | coopérative de plateforme, communs numériques | |
| Italian | cooperativa di piattaforma, beni comuni digitali | |
| German | Plattformgenossenschaft, digitale Allmende | |

See **OPENCOOP-RESEARCH.md** for why this category needs its own first-class treatment.

---

## Researcher search-query template

Replace the flat English-only `SEARCHES` list in country researcher scripts with a language-aware template:

```python
def build_searches(country_code, iso_language_codes):
    """Generate searches in each relevant language for the country."""
    topics_by_lang = {
        'en': ['NGO directory', 'cooperative federation', 'mutual aid', ...],
        'es': ['cooperativas directorio', 'economía solidaria', 'ayuda mutua', ...],
        'pt': ['cooperativas diretório', 'economia solidária', ...],
        'fr': ['coopératives annuaire', 'économie solidaire', ...],
        'ar': ['تعاونيات دليل', 'اقتصاد تضامني', ...],
        # ... etc
    }
    out = []
    for lang in iso_language_codes:
        for topic in topics_by_lang.get(lang, []):
            out.append(f"{country_name_in_lang(country_code, lang)} {topic}")
    return out
```

Countries to language-mapping should live in `data/country_languages.json` and pull from the CLDR language-territory data, not be hand-maintained.

---

## What this file is NOT

- Not a finished implementation. See `MULTILINGUAL-IMPLEMENTATION-PLAN.md` for the code work.
- Not a guarantee of alignment. Every term here has been or can be co-opted. These are **recall tools**, not **relevance tools**. Precision still comes from downstream verification (website review, governance signals, embedding similarity against principle definitions).
- Not exhaustive. Missing: many African languages beyond the main 5, Bantu language family depth, Austronesian coverage, Turkic outside Turkey, Indigenous languages of the Americas beyond Quechua/Aymara/Nahuatl/Maori/Inuktitut. Community contributions welcome.
