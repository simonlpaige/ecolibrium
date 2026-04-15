"""
Prep re-run: delete DIRECTORY_CC.md files for undercounted countries
so run_next_country.py will re-process them.
Existing DB entries are kept - the runner will ADD to them.
"""
import os

REGIONAL_DIR = r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\regional'

# Countries that need re-running (got <50% of expected results)
RERUN_COUNTRIES = [
    'CN', 'IN', 'RU', 'KR', 'PK', 'BD', 'TR', 'VN', 'PL', 'UA',
    'DE', 'FR', 'GB', 'JP', 'IT', 'ES', 'ID', 'BR', 'MX', 'PH'
]

deleted = 0
for cc in RERUN_COUNTRIES:
    md_path = os.path.join(REGIONAL_DIR, f'DIRECTORY_{cc}.md')
    if os.path.exists(md_path):
        os.remove(md_path)
        print(f'  Deleted {md_path}')
        deleted += 1
    else:
        print(f'  No file for {cc} (already absent)')

print(f'\nDeleted {deleted} DIRECTORY files. These countries will re-run on next cron cycle.')
