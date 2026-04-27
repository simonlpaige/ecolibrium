"""Quick stats dump from the Commonweave DB. Used by wiki-update.py."""
import sqlite3, json, sys, os

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'commonweave_directory.db')

def get_stats():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM organizations WHERE status='active'")
    active = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT country_code) FROM organizations WHERE status='active' AND country_code != ''")
    countries = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM organizations WHERE status='active' AND lat IS NOT NULL AND lon IS NOT NULL")
    geocoded = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM organizations WHERE status='active' AND alignment_score >= 5")
    score5 = c.fetchone()[0]

    c.execute("SELECT source, COUNT(*) as n FROM organizations WHERE status='active' GROUP BY source ORDER BY n DESC")
    sources = c.fetchall()

    conn.close()
    return dict(active=active, countries=countries, geocoded=geocoded, score5=score5, sources=sources)

if __name__ == '__main__':
    print(json.dumps(get_stats(), indent=2, default=str))
