import json
from datetime import datetime

path = r'C:\Users\simon\.openclaw\workspace\commonweave\data\country_research_state.json'

with open(path, encoding='utf-8') as f:
    state = json.load(f)

state['CN']['completed'] = True
state['CN']['completed_at'] = datetime.utcnow().isoformat() + 'Z'
state['CN']['note'] = 'Marked complete after 32 failed attempts; 0 orgs found (CN scraping blocked)'

with open(path, 'w', encoding='utf-8') as f:
    json.dump(state, f, indent=2, sort_keys=True)

print('CN marked as completed.')
print(json.dumps(state['CN'], indent=2))
