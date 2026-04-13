"""
ECO-70: Venezuela (VE) Regional Research
Uses web search (DuckDuckGo) to find Venezuelan organizations.
Output: data/regional/DIRECTORY_VE.md
"""

import urllib.request
import urllib.parse
import json
import os
import time
import sys
import re

DATA_DIR = r"C:\Users\simon\.openclaw\workspace\ecolibrium\data"
OUTPUT_FILE = os.path.join(DATA_DIR, "regional", "DIRECTORY_VE.md")

# 15-search protocol for Venezuela
SEARCHES = [
    "Venezuela organizaciones sociedad civil ONG directorio",
    "Venezuela cooperativas trabajadores federacion nacional",
    "Venezuela soberania alimentaria agroecologia organizaciones campesinas",
    "Venezuela salud comunitaria organizaciones atencion primaria",
    "Venezuela democracia participacion ciudadana organizaciones",
    "Venezuela vivienda cooperativa tierra comunidad",
    "Venezuela economia solidaria ayuda mutua redes",
    "Venezuela pueblos indigenas organizaciones derechos Wayuu Yanomami",
    "Venezuela mujeres organizaciones cooperativa ayuda mutua",
    "Venezuela restorative justice justicia restaurativa paz",
    "Venezuela tecnologia civica software libre organizaciones",
    "Venezuela medio ambiente ecologia conservacion organizaciones Amazonia",
    "Venezuela educacion popular grassroots escuela comunitaria",
    "Venezuela energia renovable solar comunidad cooperativa",
    "Venezuela organizaciones humanitarias OCHA frontline civil society",
]

FRAMEWORK_KEYWORDS = {
    'democracy': ['civic', 'democracy', 'democracia', 'governance', 'community', 'citizen', 'rights', 'political', 'civil society', 'sociedad civil', 'ngo', 'ong'],
    'cooperatives': ['cooperative', 'cooperativa', 'co-op', 'worker', 'savings', 'credit union', 'thrift', 'mutual', 'ahorro', 'credito'],
    'healthcare': ['health', 'salud', 'medical', 'hospital', 'clinic', 'malaria', 'hiv', 'maternal', 'nurse', 'enfermeria', 'medico'],
    'food': ['food', 'alimento', 'agriculture', 'farming', 'nutrition', 'hunger', 'agroecology', 'smallholder', 'campesino', 'agricola'],
    'education': ['school', 'escuela', 'education', 'educacion', 'learn', 'literacy', 'university', 'training', 'youth', 'jovenes'],
    'housing_land': ['housing', 'vivienda', 'shelter', 'land', 'tierra', 'slum', 'urban', 'home', 'settlement'],
    'conflict': ['peace', 'paz', 'conflict', 'justice', 'justicia', 'violence', 'violencia', 'reconciliation', 'refugee', 'displaced', 'migrante'],
    'energy_digital': ['energy', 'energia', 'solar', 'electricity', 'electricidad', 'digital', 'tech', 'internet', 'connectivity', 'tecnologia'],
    'recreation_arts': ['arts', 'cultura', 'music', 'musica', 'dance', 'heritage', 'sport', 'recreation', 'arte', 'cultural'],
    'ecology': ['environment', 'ambiente', 'ecology', 'ecologia', 'conservation', 'conservacion', 'forest', 'bosque', 'water', 'agua', 'climate', 'clima'],
    'indigenous': ['indigena', 'indigenous', 'wayuu', 'yanomami', 'pemon', 'warao', 'tribal', 'aboriginal', 'native'],
}

def guess_framework(name, desc=''):
    text = (name + ' ' + desc).lower()
    best = None
    best_score = 0
    for area, kws in FRAMEWORK_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in text)
        if score > best_score:
            best_score = score
            best = area
    return best or 'democracy'

def search_ddg_html(query):
    """Scrape DuckDuckGo HTML results."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html'
        })
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        
        results = []
        title_pattern = re.compile(r'class="result__a"[^>]*>([^<]+)</a>', re.IGNORECASE)
        snippet_pattern = re.compile(r'class="result__snippet"[^>]*>(.*?)</(?:td|div|span)[^>]*>', re.IGNORECASE | re.DOTALL)
        url_pattern = re.compile(r'class="result__url"[^>]*>([^<]+)</[^>]+>', re.IGNORECASE)
        
        titles = title_pattern.findall(html)
        snippets = snippet_pattern.findall(html)
        urls_found = url_pattern.findall(html)
        
        for i, title in enumerate(titles[:10]):
            snippet = snippets[i] if i < len(snippets) else ''
            url_found = urls_found[i] if i < len(urls_found) else ''
            snippet = re.sub(r'<[^>]+>', ' ', snippet).strip()
            snippet = re.sub(r'\s+', ' ', snippet)
            results.append({'title': title.strip(), 'snippet': snippet[:250], 'url': url_found.strip()})
        
        return results
    except Exception as e:
        print(f"  DDG HTML error: {e}", flush=True)
        return []

def search_ddg_api(query):
    """Use DuckDuckGo instant answers API."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_redirect=1&skip_disambig=1"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = []
            if data.get('Abstract'):
                results.append({'title': data.get('Heading', query), 'snippet': data['Abstract'], 'url': data.get('AbstractURL', '')})
            for topic in data.get('RelatedTopics', [])[:5]:
                if isinstance(topic, dict) and topic.get('Text'):
                    results.append({'title': topic['Text'][:80], 'snippet': topic['Text'], 'url': topic.get('FirstURL', '')})
            return results
    except Exception as e:
        print(f"  API error: {e}", flush=True)
        return []

def extract_orgs_from_results(results, query):
    """Identify organization names from search results."""
    orgs = []
    
    for r in results:
        title = r.get('title', '').strip()
        snippet = r.get('snippet', '').strip()
        url = r.get('url', '').strip()
        
        if not title or len(title) < 5:
            continue
        
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Skip noise
        if any(x in title.lower() for x in ['wikipedia', 'pdf', 'page 1 of', '- amazon', 'youtube', 'twitter']):
            continue
        
        # Check if looks like org
        org_indicators = [
            'foundation', 'fundacion', 'trust', 'association', 'asociacion', 'network', 'red',
            'society', 'sociedad', 'union', 'sindicato', 'institute', 'instituto', 'centre', 'center',
            'centro', 'organization', 'organizacion', 'coalition', 'coalicion', 'alliance', 'alianza',
            'initiative', 'iniciativa', 'project', 'proyecto', 'community', 'comunidad',
            'cooperative', 'cooperativa', 'forum', 'foro', 'federation', 'federacion',
            'council', 'consejo', 'committee', 'comite', 'group', 'grupo', 'ngo', 'ong',
            'collective', 'colectivo', 'plataforma', 'platform', 'movimiento', 'movement',
            'humanitaria', 'humanitarian', 'civil', 'grassroots'
        ]
        
        title_lower = title.lower()
        is_org = any(ind in title_lower for ind in org_indicators)
        is_venezuela = '.ve' in url.lower() or 'venezuel' in (title + snippet).lower()
        
        if is_org or is_venezuela:
            framework = guess_framework(title, snippet)
            desc = snippet[:200] if snippet else f"Found via: {query[:80]}"
            orgs.append({
                'name': title,
                'location': 'Venezuela',
                'description': desc,
                'website': url if url.startswith('http') else '',
                'framework_area': framework,
                'source': f"Web search: {query[:50]}"
            })
    
    return orgs

def main():
    print("ECO-70: Venezuela (VE) Regional Research", flush=True)
    os.makedirs(os.path.join(DATA_DIR, "regional"), exist_ok=True)
    
    all_orgs = []
    seen_names = set()
    search_log = []
    
    for i, query in enumerate(SEARCHES):
        print(f"\n[{i+1}/{len(SEARCHES)}] Searching: {query[:70]}...", flush=True)
        
        results = search_ddg_html(query)
        print(f"  Got {len(results)} HTML results", flush=True)
        
        if not results:
            results = search_ddg_api(query)
            print(f"  Fallback API: {len(results)} results", flush=True)
        
        orgs = extract_orgs_from_results(results, query)
        
        new_orgs = []
        for org in orgs:
            name_key = org['name'].lower()[:50]
            if name_key not in seen_names:
                seen_names.add(name_key)
                new_orgs.append(org)
        
        print(f"  Extracted {len(new_orgs)} new orgs", flush=True)
        all_orgs.extend(new_orgs)
        search_log.append(f"Search {i+1}: '{query[:60]}' -> {len(new_orgs)} new orgs")
        
        time.sleep(2)
    
    # Targeted searches for known Venezuelan orgs
    print(f"\n[Targeted] Known Venezuelan organizations...", flush=True)
    known_targets = [
        ("PROVEA Venezuela derechos humanos organizacion", "democracy"),
        ("Espacio Publico Venezuela libertad expresion", "democracy"),
        ("Transparencia Venezuela organizacion anticorrupcion", "democracy"),
        ("CONVITE Venezuela inclusion social discapacidad", "democracy"),
        ("Fundaredes Venezuela fronteras comunidades", "conflict"),
        ("Accion Solidaria Venezuela VIH salud", "healthcare"),
        ("Cepaz Venezuela paz justicia", "conflict"),
        ("Civilis Venezuela derechos humanos", "democracy"),
        ("Venezuela Wayuu cooperativa indigena", "indigenous"),
        ("REDNOPV Venezuela organizaciones pueblos", "indigenous"),
        ("ACCSI Venezuela VIH SIDA salud", "healthcare"),
        ("Sinergia Venezuela redes organizaciones", "democracy"),
        ("Superatec Venezuela tecnologia empleo", "energy_digital"),
        ("Venezuela Sin Limites fundacion ONG", "democracy"),
        ("PAHNAL Venezuela humanitaria plataforma", "conflict"),
    ]
    
    for query, framework_hint in known_targets:
        results = search_ddg_html(query)
        if not results:
            results = search_ddg_api(query)
        for r in results[:4]:
            title = r.get('title', '').strip()
            if title and len(title) > 5:
                name_key = title.lower()[:50]
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    framework = guess_framework(title, r.get('snippet',''))
                    # Use hint if no better match
                    if framework == 'democracy' and framework_hint != 'democracy':
                        framework = framework_hint
                    all_orgs.append({
                        'name': title,
                        'location': 'Venezuela',
                        'description': r.get('snippet', '')[:200],
                        'website': r.get('url', ''),
                        'framework_area': framework,
                        'source': f"Targeted: {query[:50]}"
                    })
        time.sleep(1.5)
    
    # Write output markdown in standard format
    print(f"\nWriting {len(all_orgs)} organizations to {OUTPUT_FILE}", flush=True)
    
    by_area = {}
    for org in all_orgs:
        area = org['framework_area']
        if area not in by_area:
            by_area[area] = []
        by_area[area].append(org)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# Venezuela (VE) -- Regional Directory\n\n")
        f.write(f"**Searches conducted:** {len(SEARCHES) + len(known_targets)}\n")
        f.write(f"**Organizations found:** {len(all_orgs)}\n")
        f.write(f"**Generated:** ECO-70 Researcher run (2026-04-13)\n\n")
        f.write(f"*Note: These orgs were found via web search and need verification. ")
        f.write(f"Most are NOT in the IRS bulk data (Venezuela is non-US). ")
        f.write(f"Quality varies -- treat as leads for human review.*\n\n")
        f.write(f"---\n\n")
        
        for area in sorted(by_area.keys()):
            orgs = by_area[area]
            area_label = area.replace('_', ' ').title()
            f.write(f"## {area_label} ({len(orgs)} orgs)\n\n")
            f.write(f"| Name | Location | Framework Area | Description | Website | Source |\n")
            f.write(f"|---|---|---|---|---|---|\n")
            for org in orgs:
                name = org['name'].replace('|', '-').replace('\n',' ')[:80]
                loc = org.get('location','Venezuela')
                area_col = area
                desc = org['description'].replace('|', '-').replace('\n', ' ')[:120]
                web = org['website'][:80] if org['website'] else ' '
                src = org['source'][:50]
                f.write(f"| {name} | {loc} | {area_col} | {desc} | {web} | {src} |\n")
            f.write(f"\n")
        
        f.write(f"---\n\n")
        f.write(f"## Coverage Assessment\n\n")
        f.write(f"- IRS BMF records for VE: 0 (expected -- US-only database)\n")
        f.write(f"- This research adds: {len(all_orgs)} Venezuelan organizations\n")
        f.write(f"- Framework coverage: {', '.join(f'{a}({len(o)})' for a,o in sorted(by_area.items()))}\n")
        f.write(f"- Key areas: Human rights orgs (operating under repression), humanitarian orgs, indigenous (Wayuu, Yanomami, Pemon, Warao)\n")
        f.write(f"- Key gaps: Informal mutual aid networks, non-registered community orgs, Margarita/Maracaibo local orgs\n")
        
        f.write(f"\n## Search Log\n\n")
        for entry in search_log:
            f.write(f"- {entry}\n")
    
    print(f"\nECO-70 COMPLETE", flush=True)
    print(f"Total orgs: {len(all_orgs)}", flush=True)
    print(f"Output: {OUTPUT_FILE}", flush=True)
    
    return len(all_orgs)

if __name__ == '__main__':
    count = main()
    sys.exit(0 if count >= 0 else 1)
