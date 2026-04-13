"""
Ingest Open Food Network instances into Ecolibrium DB.
Each national/regional OFN instance is a food sovereignty cooperative platform.
"""
import sqlite3
from datetime import datetime

DB_PATH = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'

COUNTRY_CENTROIDS = {
    'AU': (-25.27, 133.78), 'GB': (55.38, -3.44), 'FR': (46.23, 2.21),
    'ES': (40.46, -3.75), 'CA': (56.13, -106.35), 'US': (37.09, -95.71),
    'BE': (50.50, 4.47), 'DE': (51.17, 10.45), 'BR': (-14.24, -51.93),
    'NZ': (-40.90, 174.89), 'IE': (53.41, -8.24), 'RU': (61.52, 105.32),
    'GR': (39.07, 21.82), 'CH': (46.82, 8.23), 'IN': (20.59, 78.96),
    'HU': (47.16, 19.50), 'NO': (60.47, 8.47), 'TR': (38.96, 35.24),
}

OFN_INSTANCES = [
    {
        'name': 'Open Food Network Australia',
        'country_code': 'AU', 'country_name': 'Australia',
        'city': 'Melbourne',
        'website': 'https://www.openfoodnetwork.org.au/',
        'description': 'Founding instance (2012) of the Open Food Network platform; supports local food enterprises and sector development across Australia.',
        'founded': 2012,
    },
    {
        'name': 'Open Food Network UK',
        'country_code': 'GB', 'country_name': 'United Kingdom',
        'city': 'London',
        'website': 'https://www.openfoodnetwork.org.uk/',
        'description': 'Launched 2014; connects food hubs, farmers, and buyers across the UK using open-source food distribution software.',
        'founded': 2014,
    },
    {
        'name': 'Open Food France',
        'country_code': 'FR', 'country_name': 'France',
        'city': 'Paris',
        'website': 'https://www.openfoodfrance.org/',
        'description': 'Deployed 2015; becoming a cooperative to run the platform, provide trainings and consulting, and support local food enterprises in France.',
        'founded': 2015,
    },
    {
        'name': 'Katuma (Open Food Network Spain)',
        'country_code': 'ES', 'country_name': 'Spain',
        'city': 'Barcelona',
        'website': 'https://app.katuma.org/',
        'description': 'Born 2012 in Barcelona, joined OFN in 2017. Catalan cooperative with presence across the Iberian Peninsula supporting local food networks.',
        'founded': 2012,
    },
    {
        'name': 'Open Food Network Canada',
        'country_code': 'CA', 'country_name': 'Canada',
        'city': 'Ontario',
        'website': 'https://openfoodnetwork.ca/',
        'description': 'Launched 2017; most active in Ontario, building capacity to deploy food sovereignty infrastructure broadly across Canada.',
        'founded': 2017,
    },
    {
        'name': 'Open Food Network USA',
        'country_code': 'US', 'country_name': 'United States',
        'city': None,
        'website': 'https://openfoodnetwork.net/',
        'description': 'Launched 2018 as a cooperative; growing network of member producers and food hubs stretching coast to coast.',
        'founded': 2018,
    },
    {
        'name': 'Open Food Network Belgium',
        'country_code': 'BE', 'country_name': 'Belgium',
        'city': 'Brussels',
        'website': None,
        'description': 'Deployed November 2018; community managed by Oxfam-Magasins du monde, supporting local food access in Belgium.',
        'founded': 2018,
    },
    {
        'name': 'Open Food Network Germany',
        'country_code': 'DE', 'country_name': 'Germany',
        'city': None,
        'website': None,
        'description': 'Launched 2019; supports food access throughout village centres across Germany, developing new cooperative governance structures.',
        'founded': 2019,
    },
    {
        'name': 'Open Food Network Brazil',
        'country_code': 'BR', 'country_name': 'Brazil',
        'city': None,
        'website': 'https://openfoodbrasil.com.br/',
        'description': 'Launched 2019; brings open-source food sovereignty infrastructure to Brazilian food hubs, farmers, and cooperatives.',
        'founded': 2019,
    },
    {
        'name': 'Open Food Network New Zealand',
        'country_code': 'NZ', 'country_name': 'New Zealand',
        'city': None,
        'website': 'https://openfoodnetwork.org.nz/',
        'description': 'Launched 2019; developing hubs that provide local people opportunities to buy directly from local food producers.',
        'founded': 2019,
    },
    {
        'name': 'Open Food Network Ireland',
        'country_code': 'IE', 'country_name': 'Ireland',
        'city': 'Dublin',
        'website': 'https://openfoodnetwork.ie',
        'description': 'Launched 2020; connecting Irish food producers, food hubs, and consumers through open-source food distribution infrastructure.',
        'founded': 2020,
    },
    {
        'name': 'Open Food Network Russia',
        'country_code': 'RU', 'country_name': 'Russia',
        'city': None,
        'website': 'https://openfoodnetwork.ru/',
        'description': 'Launched 2020; applies open food network model to support local food sovereignty and producer-consumer connections in Russia.',
        'founded': 2020,
    },
    {
        'name': 'Open Food Network Greece',
        'country_code': 'GR', 'country_name': 'Greece',
        'city': 'Athens',
        'website': 'https://www.openfoodnetwork.gr/',
        'description': 'Launched 2021; supports local food producers and cooperative food distribution across Greece.',
        'founded': 2021,
    },
    {
        'name': 'Open Food Network Switzerland',
        'country_code': 'CH', 'country_name': 'Switzerland',
        'city': None,
        'website': 'https://www.openfoodswitzerland.ch/',
        'description': 'Launched 2022; bringing open-source food network infrastructure to Swiss food hubs and local food enterprises.',
        'founded': 2022,
    },
    {
        'name': 'Open Food Network India',
        'country_code': 'IN', 'country_name': 'India',
        'city': None,
        'website': 'https://openfoodnetwork.in/',
        'description': 'Emerging instance connecting Indian food producers and cooperatives through open food distribution infrastructure.',
        'founded': None,
    },
    {
        'name': 'Open Food Network Hungary',
        'country_code': 'HU', 'country_name': 'Hungary',
        'city': 'Budapest',
        'website': 'https://openfood.hu/',
        'description': 'Emerging instance applying the Open Food Network model to support local food sovereignty and producer-consumer connections in Hungary.',
        'founded': None,
    },
    # In development
    {
        'name': 'Open Food Network Norway',
        'country_code': 'NO', 'country_name': 'Norway',
        'city': None,
        'website': 'https://www.openfoodnetwork.no/',
        'description': 'In development; bringing open food network infrastructure to Norwegian food producers and cooperatives.',
        'founded': None,
    },
    {
        'name': 'Acik Gida (Open Food Network Turkey)',
        'country_code': 'TR', 'country_name': 'Turkey',
        'city': None,
        'website': 'https://www.acikgida.com/',
        'description': 'In development; open food network instance for Turkey supporting local food sovereignty and producer-consumer connections.',
        'founded': None,
    },
]

db = sqlite3.connect(DB_PATH)
c = db.cursor()
now = datetime.utcnow().isoformat()
inserted = 0
skipped = 0

for org in OFN_INSTANCES:
    cc = org['country_code']
    coords = COUNTRY_CENTROIDS.get(cc, (0, 0))
    lat, lon = coords

    # Check for duplicate by name
    c.execute("SELECT id FROM organizations WHERE name=? AND country_code=?", (org['name'], cc))
    if c.fetchone():
        print(f"  SKIP (exists): {org['name']}")
        skipped += 1
        continue

    c.execute("""
        INSERT INTO organizations
        (name, country_code, country_name, city, website, description,
         framework_area, model_type, source, source_id, status,
         alignment_score, lat, lon, geo_source, date_added, verified, last_filing_year)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        org['name'],
        cc,
        org['country_name'],
        org.get('city'),
        org.get('website'),
        org['description'],
        'food',
        'cooperative',
        'manual_curation',
        f"OFN_{cc}",
        'active',
        5,  # alignment_score: max - these are flagship food sovereignty orgs
        lat,
        lon,
        'country_centroid',
        now,
        1,   # verified = true
        org.get('founded'),
    ))
    inserted += 1
    print(f"  +{org['name']} ({cc})")

db.commit()

# Final count
c.execute("SELECT COUNT(*) FROM organizations WHERE source='manual_curation'")
total_curated = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM organizations")
total = c.fetchone()[0]
db.close()

print(f"\nDone: {inserted} inserted, {skipped} skipped")
print(f"Manual curation total: {total_curated}")
print(f"DB total: {total:,}")
