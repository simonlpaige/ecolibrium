# New payload.message for cron job: ecolibrium-frontend-update
# ID: ced4d951-8f81-4231-a8c4-d490699f8e44
#
# Changes from old payload:
#   - SQL uses status='active' (not status != 'removed')
#   - 10 sections (not 12) — Allied Projects and Networks & Federations removed
#   - ecology maps to "Ecological Restoration" (not "Wellbeing Economics")
#   - Cooperatives section name updated to "Cooperatives & Solidarity"
#   - All DB stat references updated to post-trim schema
#
# Paste everything between the --- markers as the new payload.message value.
# DO NOT include the markers themselves.
# ---

Update the Ecolibrium website frontend with current DB numbers. Do NOT message anyone.

**Step 1: Get current stats**
Run this Python script and capture the output:
```
python -c "
import sqlite3
db = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db')
c = db.cursor()
c.execute(\"SELECT COUNT(*) FROM organizations WHERE status = 'active'\")
active = c.fetchone()[0]
c.execute(\"SELECT COUNT(DISTINCT country_code) FROM organizations WHERE status = 'active'\")
countries = c.fetchone()[0]
print(f'ACTIVE={active}')
print(f'COUNTRIES={countries}')
c.execute(\"SELECT framework_area, COUNT(*) FROM organizations WHERE status = 'active' AND framework_area IS NOT NULL GROUP BY framework_area ORDER BY framework_area\")
for area, cnt in c.fetchall():
    print(f'SECTION_{area}={cnt}')
db.close()
"
```

**Step 2: Update ecolibrium/index.html**
Update ALL dynamic numbers on the homepage to match current DB:
- Organizations mapped stat (e.g. '24.5K' -> current rounded to nearest 100)
- Countries represented stat number
- The hero subtitle mentioning org count
- The map footer org count and country count
- The sections heading org count (e.g. '10 sections — 24,500 aligned organizations')
- The og:description meta tag
- **IMPORTANT: Update EVERY section card's org count** in the sec-meta divs. Map framework_area values to section cards:
  - democracy -> Democratic Infrastructure
  - cooperatives -> Cooperatives & Solidarity
  - healthcare -> Healthcare
  - food -> Food Sovereignty
  - education -> Education
  - housing_land -> Land & Housing
  - conflict -> Conflict Resolution
  - energy_digital -> Energy & Digital Commons
  - recreation_arts -> Recreation & Arts
  - ecology -> Ecological Restoration
  Format large numbers nicely: under 1000 show exact, 1K-10K show like '2,847', over 10K show like '12.4K'

**Step 3: Rebuild map + search data**
`python C:\Users\simon\.openclaw\workspace\ecolibrium\data\build_search_index.py`
`python C:\Users\simon\.openclaw\workspace\ecolibrium\data\build_map_points.py`

**Step 4: Sync to GitHub Pages repo**
`Copy-Item C:\Users\simon\.openclaw\workspace\ecolibrium\index.html C:\Users\simon\.openclaw\workspace\simonlpaige.github.io\ecolibrium\index.html -Force`
`Copy-Item C:\Users\simon\.openclaw\workspace\ecolibrium\data\search\* C:\Users\simon\.openclaw\workspace\simonlpaige.github.io\ecolibrium\data\search\ -Force`
`Copy-Item C:\Users\simon\.openclaw\workspace\ecolibrium\map.html C:\Users\simon\.openclaw\workspace\simonlpaige.github.io\ecolibrium\map.html -Force`
`Copy-Item C:\Users\simon\.openclaw\workspace\ecolibrium\directory.html C:\Users\simon\.openclaw\workspace\simonlpaige.github.io\ecolibrium\directory.html -Force`

**Step 5: Push both repos**
`git -C C:\Users\simon\.openclaw\workspace\ecolibrium add -A && git -C C:\Users\simon\.openclaw\workspace\ecolibrium commit -m 'auto: frontend stats update' && git -C C:\Users\simon\.openclaw\workspace\ecolibrium push`
`git -C C:\Users\simon\.openclaw\workspace\simonlpaige.github.io add ecolibrium/ && git -C C:\Users\simon\.openclaw\workspace\simonlpaige.github.io commit -m 'auto: ecolibrium frontend update' && git -C C:\Users\simon\.openclaw\workspace\simonlpaige.github.io push`

Silent - no messages to anyone.

# ---
