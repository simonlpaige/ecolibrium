import json, os
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'trim_audit', 'audit-sample-2026-04-27.json')
d = json.load(open(path, encoding='utf-8'))

def show(label, orgs, limit=12):
    print('\n=== ' + label + ' (' + str(len(orgs)) + ' orgs) ===')
    for o in orgs[:limit]:
        cc   = o.get('country_code') or '?'
        name = (o.get('name') or '')[:52]
        src  = (o.get('source') or '')[:20]
        area = (o.get('framework_area') or '')[:14]
        score= str(o.get('alignment_score', '?'))
        leg  = str(o.get('legibility') or '?')
        desc = str(o.get('description') or '')[:80]
        print('  [' + cc + '] ' + name)
        print('       src=' + src + ' area=' + area + ' score=' + score + ' leg=' + leg)
        if desc and desc != 'None':
            print('       desc: ' + desc)

show('USA', d['usa']['orgs'])
show('India', d['india']['orgs'])
show('LatAm stratified (2 per country)', d['latam_stratified']['orgs'])
