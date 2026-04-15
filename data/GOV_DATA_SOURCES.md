# Ecolibrium Government Data Sources Master List

Priority-ranked by data quality, bulk download availability, and record count.

## TIER 1: Bulk Download Available (highest priority - ingest first)

| CC | Country | Source | URL | Format | Est Records | Auth | Notes |
|---|---|---|---|---|---|---|---|
| US | United States | IRS Business Master File (BMF) | https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf | CSV | ~1.8M | No | **Already ingested but needs NTEE filtering.** Filter by NTEE codes C,E,F,I,J,K,L,O,P,Q,R,S,W only. |
| GB | England & Wales | Charity Commission | https://ccewuksprdoneregsadata1.blob.core.windows.net/data/json/publicextract.charity.zip | JSON/TSV | ~170,000 | No | Daily extract. Multiple tables: charity, trustees, finances, area of operation. |
| GB | Scotland | OSCR | https://www.oscr.org.uk/about-charities/search-the-register/download-the-scottish-charity-register/ | CSV | ~25,000 | No | Daily updated. |
| GB | Northern Ireland | CCNI | https://www.charitycommissionni.org.uk/charity-search/ | CSV | ~7,500 | No | Open data section. |
| FR | France | RNA (Repertoire National des Associations) via data.gouv.fr | https://www.data.gouv.fr/en/datasets/repertoire-national-des-associations/ | CSV | ~1.8M | No | **Massive.** All registered associations. Needs alignment filtering. |
| JP | Japan | Cabinet Office NPO Portal | https://www.npo-homepage.go.jp/npoportal/ | CSV bulk | ~50,000 | No | Bulk download by prefecture. |
| AU | Australia | ACNC Charity Register | https://www.acnc.gov.au/charity/charities | CSV | ~60,000 | No | Australian Charities and Not-for-profits Commission. |
| NZ | New Zealand | Charities Register | https://www.charities.govt.nz/charities-in-new-zealand/the-charities-register/ | CSV | ~28,000 | No | Full register download available. |
| RU | Russia | FNS EGRUL | https://www.nalog.gov.ru/opendata/7707329152-egrul/ | XML (50GB) | ~550,000 NCOs | No | Filter by ОПФ code for NCO types. Geo-blocked, may need VPN. |
| UA | Ukraine | Unified State Register (EDR) | https://data.gov.ua/ | XML/ZIP | ~80,000 NGOs | No | Addresses redacted for security. Filter by org type. |
| TW | Taiwan | data.gov.tw | https://data.gov.tw/ | CSV/JSON | ~50,000 | No | Search 公益/財團法人/社會團體. |
| PL | Poland | KRS (Krajowy Rejestr Sądowy) | https://prs.ms.gov.pl/ | CSV | ~100,000 | No | National Court Register for associations and foundations. |
| MX | Mexico | SAT Padron via datos.gob.mx | https://datos.gob.mx/ | CSV | ~7,000 | No | Tax-exempt civil organizations. |
| CZ | Czechia | Public Register (Veřejný rejstřík) | https://or.justice.cz/ | CSV/XML | ~80,000 | No | Associations, foundations, institutes. |

## TIER 2: API or Registration Required

| CC | Country | Source | URL | Format | Est Records | Auth | Notes |
|---|---|---|---|---|---|---|---|
| IN | India | NGO Darpan (NITI Aayog) | https://ngodarpan.gov.in/ | JSON API | ~700,000-1.8M | Reg | API endpoint: ngodarpan.gov.in/index.php/ajaxcontroller/. State/district/sector filtering. **Top priority.** |
| IN | India | FCRA Online (MHA) | https://fcraonline.nic.in/ | Excel/Web | ~16,000 active | No | Foreign-funded NGOs. District-wise Excel lists downloadable. |
| IN | India | MCA21 Section 8 Companies | https://www.mca.gov.in/content/mca/global/en/mca/master-data-download.html | CSV | ~12,000 | No | Nonprofit companies. Filter by company type. |
| KR | South Korea | data.go.kr (비영리법인) | https://www.data.go.kr/ | CSV/API | ~100,000 | API key (free) | Search 비영리법인 or 사단법인. Free registration for API. |
| CN | China | MCA Social Org Registry | https://chinanpo.mca.gov.cn/ | Web only | ~910,000 | No | **No bulk download.** Search-only. Scraping needed. Geo-blocked overseas. |
| CN | China | China Foundation Center | http://foundationcenter.org.cn/ | Web | ~7,000 | No | Foundations only. Partial structured data. |
| PK | Pakistan | SECP Section 42 | https://www.secp.gov.pk/company-search/ | Web/API | ~12,000 | API key | Nonprofit companies. |
| PK | Pakistan | EAD NGO List | https://www.ead.gov.pk/ | PDF | ~5,000 | No | Foreign-funded NGOs. |
| PH | Philippines | SEC E-Filing | https://efiling.sec.gov.ph/ | Web | ~700,000 all | No | Includes nonprofits. No bulk export. |
| ID | Indonesia | Ormas Registry (Kemendagri) | https://ormas.kemendagri.go.id/ | Web | ~430,000 | No | No bulk download. Search only. |
| BD | Bangladesh | NGO Affairs Bureau | https://www.ngoab.gov.bd/ | Web/PDF | ~2,500 | No | Foreign-funded NGOs. Domestic orgs at district level (~300K). |
| NP | Nepal | Social Welfare Council | https://www.swc.org.np/ | Web | ~50,000 | No | No bulk download. |
| TH | Thailand | DOPA Association Registry | https://www.dopa.go.th/ | Web | ~45,000 | No | Search only. |
| MY | Malaysia | Registrar of Societies | https://www.ros.gov.my/ | Web | ~73,000 | No | Search by state. No bulk download. |
| VN | Vietnam | Ministry of Home Affairs | https://www.moha.gov.vn/ | Web | ~70,000 | No | No public bulk download. |

## TIER 3: Limited/Restricted (scraping or manual collection needed)

| CC | Country | Source | URL | Format | Est Records | Auth | Notes |
|---|---|---|---|---|---|---|---|
| DE | Germany | Handelsregister.de (Vereinsregister) | https://www.handelsregister.de | Web | ~600,000 e.V. | No | **No national bulk.** Split across 16 state courts. OpenCorporates has partial scrape. |
| IT | Italy | RUNTS (Registro Unico Terzo Settore) | https://servizi.lavoro.gov.it/runts/ | Web | ~115,000 | No | Launched 2022. Search only. |
| ES | Spain | RNA (Interior Ministry) | https://www.interior.gob.es/ | Web | ~300,000 | No | Plus autonomous community registers. No bulk. |
| NL | Netherlands | KvK (Kamer van Koophandel) | https://www.kvk.nl/ | Paid API | ~250,000 NPOs | Paid | Stichtings + Verenigings. ANBI register (tax-exempt) is free: ~43,000. |
| TR | Turkey | Dernekler Daire Başkanlığı | https://www.siviltoplum.gov.tr/ | Web | ~120,000 | No | Associations registry. Search only. |
| SA | Saudi Arabia | NCNP Registry | https://ncnp.org.sa/ | Web | ~3,000 | No | National Center for Non-Profit Sector. |
| EG | Egypt | Ministry of Social Solidarity | https://www.moss.gov.eg/ | Web | ~50,000 | No | NGO registry. Limited online. |
| BR | Brazil | Receita Federal CNPJ | https://dados.gov.br/ | CSV (large) | ~900,000 NPOs | No | Filter by natureza juridica for nonprofits. Massive dataset. |
| CO | Colombia | DIAN/Cámara de Comercio | https://www.datos.gov.co/ | CSV | ~25,000 | No | Tax-exempt entities. |
| AR | Argentina | CENOC | https://www.argentina.gob.ar/desarrollosocial/cenoc | Web | ~15,000 | No | National Center for Community Organizations. |
| ZA | South Africa | NPO Directorate | https://www.dsd.gov.za/npo/ | Web | ~250,000 | No | Search available. Bulk download unclear. |
| KE | Kenya | NGO Coordination Board | https://ngobureau.go.ke/ | Web | ~12,000 | No | Search only. |
| NG | Nigeria | CAC (Corporate Affairs Commission) | https://www.cac.gov.ng/ | Web | ~100,000+ NPOs | No | Search only. Part of broader business registry. |

## INDIA STATE-LEVEL REGISTRIES

| State | Source | URL | Est Records | Notes |
|---|---|---|---|---|
| Maharashtra | Charity Commissioner | https://charity.maharashtra.gov.in/ | ~500,000 | Public Trust/Society registry. Search only. |
| Uttar Pradesh | e-Society Portal | https://etsociety.upsdc.gov.in/ | ~300,000 | Search available. |
| Gujarat | GARVI | https://garvi.gujarat.gov.in/ | ~200,000 | e-Registration portal. |
| West Bengal | Registration Portal | https://wbregistration.gov.in/ | ~200,000 | Societies registration. |
| Tamil Nadu | TN RegNet | https://tnreginet.gov.in/ | ~150,000 | Societies + Trusts. |
| Karnataka | Dharmadhikari | https://dharmadhikari.kar.nic.in/ | ~100,000 | State charity commissioner. |
| Rajasthan | Pehchan | https://pehchan.raj.nic.in/ | ~100,000 | Society/Trust registration. |
| Madhya Pradesh | MP e-District | https://mpedistrict.gov.in/ | ~100,000 | Includes societies. |
| Andhra Pradesh | CARD | https://registration.ap.gov.in/ | ~90,000 | Society registration module. |
| Telangana | TS Registration | https://tsregistration.gov.in/ | ~80,000 | Registration & Stamps. |
| Kerala | ICDS | https://www.icds.kerala.gov.in/ | ~80,000 | Social Justice dept. |
| Punjab | Societies Registration | https://registrationsocietiespunjab.gov.in/ | ~60,000 | Dedicated portal. |
| Odisha | Revenue Dept | https://revenueodisha.gov.in/ | ~60,000 | Trust registration. |
| Bihar | State Portal | https://state.bihar.gov.in/ | ~50,000 | Limited online. |
| Assam | Registration Dept | https://registration.assam.gov.in/ | ~40,000 | Registration department. |

## AUSTRALIA STATE-LEVEL

| State | Source | Notes |
|---|---|---|
| National | ACNC (Tier 1 above) | ~60,000 charities. Primary source. |
| NSW | Fair Trading | Incorporated associations. |
| VIC | Consumer Affairs Victoria | Incorporated associations registry. |
| QLD | Office of Fair Trading | Incorporated associations. |
| WA | Dept of Mines (Associations) | Associations register. |

## REGIONAL AGGREGATORS

| Source | URL | Coverage | Notes |
|---|---|---|---|
| UN DESA Civil Society | https://esango.un.org/civilsociety/ | ~30,000 global | UN ECOSOC-associated NGOs. |
| CIVICUS Monitor | https://monitor.civicus.org/data/download/ | 198 countries | Civic space ratings, not org lists. |
| Candid/GuideStar | https://candid.org/ | 700,000+ global | Paid API for bulk. |
| OpenCorporates | https://opencorporates.com/ | 140+ jurisdictions | API (free tier). Filter by nonprofit type. |
| EU Transparency Register | https://ec.europa.eu/transparencyregister/public/opendata/ | ~12,000 | EU-level lobbying NGOs. CSV/XML. |
| ReliefWeb Organizations | https://reliefweb.int/organizations | ~10,000 | Humanitarian orgs. API available. |
| UN OCHA HDX | https://data.humdata.org/ | Per-country | Humanitarian datasets. |
| GLEIF | https://www.gleif.org/ | ~2.5M globally | Legal Entity Identifiers. |

## AMERICAS - ADDITIONAL SOURCES

| CC | Country | Source | URL | Format | Est Records | Auth | Notes |
|---|---|---|---|---|---|---|---|
| CA | Canada | CRA Charities List | https://open.canada.ca/data/en/dataset/7d5e0324-7f69-4607-a4a4-21c3e04adf78 | CSV | ~86,000 | No | T3010 filer data. Bulk CSV download on open.canada.ca. |
| CA | Canada | CRA T3010 Financial Data | https://open.canada.ca/data/en/dataset/d19db62e-3fd0-11e3-9da6-000c29e9c1dc | CSV | ~86,000 | No | Financial returns data for registered charities. |
| PE | Peru | SUNAT Consulta RUC | https://e-consultaruc.sunat.gob.pe/ | Web | ~20,000 NPOs | No | Filter by tipo persona juridica. No bulk download. |
| CL | Chile | SII Registro Contribuyentes | https://www.sii.cl/ | Web | ~15,000 NPOs | No | Tax authority. Search only. |
| EC | Ecuador | SEPS Cooperatives | https://www.seps.gob.ec/ | Web/PDF | ~12,000 | No | Popular and Solidarity Economy registry. |
| CR | Costa Rica | Registro Nacional | https://www.rnpdigital.com/ | Web | ~8,000 | No | Associations registry. |

## AFRICA - ADDITIONAL SOURCES

| CC | Country | Source | URL | Format | Est Records | Auth | Notes |
|---|---|---|---|---|---|---|---|
| ZA | South Africa | NPO Directorate (DSD) | https://www.dsd.gov.za/npo/ | Web/PDF | ~250,000 | No | Department of Social Development. Search available. Bulk unclear. |
| GH | Ghana | Registrar General Dept | https://rgd.gov.gh/ | Web | ~15,000 NPOs | No | Business + NGO registration. Search only. |
| RW | Rwanda | RGB (Rwanda Governance Board) | https://www.rgb.rw/ | Web/PDF | ~3,000 | No | Civil society oversight. Lists available. |
| TZ | Tanzania | BRELA + NGO Board | https://www.brela.go.tz/ | Web | ~10,000 | No | Business Registrations and Licensing Agency. |
| UG | Uganda | NGO Bureau | https://ngobureau.go.ug/ | Web | ~14,000 | No | National Bureau for NGOs. Search available. |
| ET | Ethiopia | ACSO (Authority for Civil Society Orgs) | https://www.acso.gov.et/ | Web | ~4,000 | No | Replaced CHSA in 2019. Registry search. |
| SN | Senegal | MCAS (Ministère de la Coopération) | Portal varies | Web | ~5,000 | No | NGO coordination ministry. |
| TN | Tunisia | IFEDA | http://www.ifeda.org.tn/ | Web | ~23,000 | No | Instance de Formation et d'Appui aux Associations. |
| MA | Morocco | SGG (Secrétariat Général du Gouvernement) | https://www.sgg.gov.ma/ | Web | ~200,000 | No | Association registry. Massive but no bulk download. |

## US STATE-LEVEL SOURCES

| State | Source | URL | Notes |
|---|---|---|---|
| National | IRS BMF (Tier 1 above) | irs.gov | Primary source. ~1.8M records. |
| National | ProPublica Nonprofit Explorer | https://projects.propublica.org/nonprofits/api | JSON API, no auth, ~1.6M orgs. Good for enrichment. |
| CA | CA Attorney General Registry | https://rct.doj.ca.gov/Verification/Web/Search.aspx | ~100K charities. Search only. |
| NY | NY Attorney General Charities Bureau | https://www.charitiesnys.com/search_charities.html | ~80K. Search only. |
| TX | TX Secretary of State | https://www.sos.state.tx.us/corp/sosda/index.shtml | Bulk data available. |

## INGESTION PRIORITY ORDER

1. **UK** (Charity Commission + OSCR + CCNI) - ~202K orgs, bulk CSV/JSON, no auth. Easy win.
2. **France RNA** - 1.8M associations, CSV, no auth. Needs heavy filtering.
3. **Japan NPO Portal** - 50K, CSV bulk, no auth.
4. **Australia ACNC** - 60K, CSV, no auth.
5. **New Zealand** - 28K, CSV, no auth.
6. **India NGO Darpan API** - 700K+, JSON, needs registration.
7. **Brazil CNPJ** - 900K NPOs, CSV, no auth. Needs filtering by natureza juridica.
8. **South Korea data.go.kr** - 100K, CSV/API, free key.
9. **Taiwan data.gov.tw** - 50K, CSV, no auth.
10. **Poland KRS** - 100K, CSV, no auth.
11. **Ukraine EDR** - 80K, XML, no auth.
12. **Russia EGRUL** - 550K NCOs in 50GB XML. Heavy lift but massive dataset.
