import sqlite3, json, os

db_path = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db'
db = sqlite3.connect(db_path)
c = db.cursor()

c.execute("SELECT COUNT(*) FROM organizations WHERE status != 'removed'")
active = c.fetchone()[0]

c.execute("SELECT COUNT(DISTINCT country_code) FROM organizations WHERE status != 'removed'")
countries_done = c.fetchone()[0]

c.execute("SELECT DISTINCT country_code FROM organizations WHERE status != 'removed' ORDER BY country_code")
done_codes = [r[0] for r in c.fetchall() if r[0]]

# Check queue
queue_path = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\country_queue.json'
if os.path.exists(queue_path):
    with open(queue_path) as f:
        queue = json.load(f)
    remaining = [c for c in queue if c not in done_codes]
    print(f"Queue total: {len(queue)}")
    print(f"Remaining in queue: {len(remaining)}")
    print(f"Next 10: {remaining[:10]}")
else:
    print("No country_queue.json found")

print(f"\nActive orgs: {active:,}")
print(f"Countries completed: {countries_done}")
print(f"Country codes done: {done_codes}")

# Framework areas
c.execute("SELECT framework_area, COUNT(*) FROM organizations WHERE status != 'removed' AND framework_area IS NOT NULL GROUP BY framework_area ORDER BY COUNT(*) DESC")
print("\nBy section:")
for area, cnt in c.fetchall():
    print(f"  {area}: {cnt:,}")

db.close()
