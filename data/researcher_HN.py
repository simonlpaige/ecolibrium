"""
ECO-71: Honduras (HN) Regional Research
Uses web search (DuckDuckGo) to find Honduran organizations.
Output: data/regional/DIRECTORY_HN.md
"""

import urllib.request
import urllib.parse
import json
import os
import time
import sys
import re

DATA_DIR = r"C:\Users\simon\.openclaw\workspace\ecolibrium\data"
OUTPUT_FILE = os.path.join(DATA_DIR, "regional", "DIRECTORY_HN.md")

# 15-search protocol for Honduras
SEARCHES = [
    "Honduras NGO directorio organizaciones sociedad civil lista",
    "Honduras cooperativas organizaciones campesinas agricultores",
    "Honduras soberania alimentaria agroecologia organizaciones comunidad",
    "Honduras organizaciones indigenas pueblos lenca maya chortí derechos",
    "Honduras organizaciones salud comunitaria salud primaria rural",
    "Honduras movimiento de mujeres organizaciones feministas derechos",
    "Honduras organizaciones ambientales conservacion biodiversidad",
    "Honduras organizaciones jovenes educacion popular",
    "Honduras economia solidaria redes mutual aid solidarity",
    "Honduras organizaciones vivienda tierra comunidad rural",
    "Honduras derechos humanos organizaciones defensa",
    "Honduras organizaciones LGBTQ comunidad diversidad",
    "Honduras organizaciones afrodescendientes garifuna derechos",
    "Honduras tecnologia civica organizaciones transparencia",
    "Honduras organizaciones mineria resistencia comunidades",
]

FRAMEWORK_KEYWORDS = {
    'democracy': ['civic', 'democracy', 'governance', 'community', 'citizen', 'rights', 'political', 'vote', 'derechos', 'democracia', 'participacion', 'transparencia'],
    'cooperatives': ['cooperative', 'co-op', 'worker', 'savings', 'credit union', 'thrift', 'mutual', 'cooperativa', 'solidaridad'],
    'healthcare': ['health', 'medical', 'hospital', 'clinic', 'malaria', 'hiv', 'maternal', 'nurse', 'salud', 'clinica'],
    'food': ['food', 'agriculture', 'farming', 'nutrition', 'hunger', 'agroecology', 'smallholder', 'alimento', 'agricola', 'campesino'],
    'education': ['school', 'education', 'learn', 'literacy', 'university', 'training', 'youth', 'escuela', 'educacion', 'jovenes'],
    'housing_land': ['housing', 'shelter', 'land', 'slum', 'urban', 'home', 'settlement', 'vivienda', 'tierra', 'comunidad'],
    'conflict': ['peace', 'conflict', 'justice', 'violence', 'reconciliation', 'refugee', 'displaced', 'paz', 'justicia', 'derechos humanos'],
    'energy_digital': ['energy', 'solar', 'electricity', 'digital', 'tech', 'internet', 'connectivity', 'energia', 'tecnologia'],
    'recreation_arts': ['arts', 'culture', 'music', 'dance', 'heritage', 'sport', 'recreation', 'cultura', 'arte'],
    'ecology': ['environment', 'ecology', 'conservation', 'forest', 'water', 'climate', 'nature', 'ambiental', 'bosque', 'agua'],
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
        snippet_pattern = re.compile(r'class="result__snippet"[^>]*>(.*?)</[^>]+>', re.IGNORECASE | re.DOTALL)
        url_pattern = re.compile(r'class="result__url"[^>]*>([^<]+)</[^>]+>', re.IGNORECASE)
        
        titles = title_pattern.findall(html)
        snippets = snippet_pattern.findall(html)
        urls_found = url_pattern.findall(html)
        
        for i, title in enumerate(titles[:8]):
            snippet = snippets[i] if i < len(snippets) else ''
            url_found = urls_found[i] if i < len(urls_found) else ''
            snippet = re.sub(r'<[^>]+>', ' ', snippet).strip()
            results.append({'title': title.strip(), 'snippet': snippet[:200], 'url': url_found.strip()})
        
        return results
    except Exception as e:
        print(f"  DDG HTML error: {e}", flush=True)
        return []

def search_ddg_api(query):
    """DuckDuckGo instant answers API fallback."""
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
        print(f"  DDG API error: {e}", flush=True)
        return []

def extract_orgs_from_results(results, query):
    orgs = []
    
    for r in results:
        title = r.get('title', '')
        snippet = r.get('snippet', '')
        url = r.get('url', '')
        
        if not title or len(title) < 4:
            continue
        
        title = re.sub(r'\s+', ' ', title).strip()
        
        if any(x in title.lower() for x in ['wikipedia', 'facebook.com', 'twitter.com', 'pdf', 'page 1', 'login', 'sign in']):
            continue
        
        org_indicators = [
            'foundation', 'trust', 'association', 'network', 'society', 'union',
            'institute', 'centre', 'center', 'organization', 'coalition', 'alliance',
            'initiative', 'project', 'community', 'cooperative', 'forum', 'federation',
            'council', 'committee', 'group', 'ngo', 'cso', 'ong',
            # Spanish
            'fundacion', 'asociacion', 'red de', 'sociedad', 'cooperativa', 'federacion',
            'consejo', 'comite', 'movimiento', 'colectivo', 'coordinadora', 'central',
            'confederacion', 'plataforma', 'frente', 'comision', 'foro', 'alianza',
        ]
        
        title_lower = title.lower()
        is_org = any(ind in title_lower for ind in org_indicators)
        is_honduras = '.hn' in url.lower() or 'honduras' in title_lower or 'hondure' in title_lower
        
        if is_org or is_honduras:
            framework = guess_framework(title, snippet)
            orgs.append({
                'name': title,
                'description': snippet[:200] if snippet else f"Found via: {query[:80]}",
                'website': url if url.startswith('http') else '',
                'framework_area': framework,
                'source': f"DDG: {query[:60]}"
            })
    
    return orgs

def main():
    print("ECO-71: Honduras (HN) Regional Research", flush=True)
    os.makedirs(os.path.join(DATA_DIR, "regional"), exist_ok=True)
    
    all_orgs = []
    seen_names = set()
    
    for i, query in enumerate(SEARCHES):
        print(f"\n[{i+1}/{len(SEARCHES)}] Searching: {query[:70]}...", flush=True)
        
        results = search_ddg_html(query)
        print(f"  Got {len(results)} results", flush=True)
        
        if not results:
            results = search_ddg_api(query)
            print(f"  Fallback API: {len(results)} results", flush=True)
        
        orgs = extract_orgs_from_results(results, query)
        
        new_orgs = []
        for org in orgs:
            name_key = org['name'].lower()[:40]
            if name_key not in seen_names:
                seen_names.add(name_key)
                new_orgs.append(org)
        
        print(f"  Extracted {len(new_orgs)} new orgs", flush=True)
        all_orgs.extend(new_orgs)
        
        time.sleep(2.0)
    
    # Targeted known Honduran organizations
    print(f"\n[Bonus] Targeted searches for known Honduran orgs...", flush=True)
    known_queries = [
        ("COPINH Consejo Civico Organizaciones Populares Indigenas Honduras Berta Caceres", "conflict"),
        ("COFADEH Comite Familiares Detenidos Desaparecidos Honduras", "conflict"),
        ("CNTC Central Nacional Trabajadores Campo Honduras campesinos", "food"),
        ("Caritas Honduras organizacion iglesia social", "healthcare"),
        ("FIAN Honduras derecho alimentacion", "food"),
        ("CDM Centro Derechos Mujeres Honduras", "democracy"),
        ("ERIC Equipo Reflexion Investigacion Comunicacion Honduras", "democracy"),
        ("Asociacion Coordinadora Comunidades Indigenas Honduras ACICH", "democracy"),
        ("OFRANEH Organizacion Fraternal Negra Hondurena garifuna", "democracy"),
        ("Via Campesina Honduras organizaciones", "food"),
    ]
    
    for query, framework_hint in known_queries:
        results = search_ddg_html(query)
        for r in results[:3]:
            title = r.get('title', '')
            if title and len(title) > 5:
                name_key = title.lower()[:40]
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    all_orgs.append({
                        'name': title,
                        'description': r.get('snippet', '')[:200],
                        'website': r.get('url', ''),
                        'framework_area': framework_hint,
                        'source': f"Targeted: {query[:60]}"
                    })
        time.sleep(1.5)
    
    print(f"\nWriting {len(all_orgs)} organizations to {OUTPUT_FILE}", flush=True)
    
    by_area = {}
    for org in all_orgs:
        area = org['framework_area']
        if area not in by_area:
            by_area[area] = []
        by_area[area].append(org)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# Honduras (HN) -- Regional Directory\n\n")
        f.write(f"**Searches conducted:** {len(SEARCHES) + len(known_queries)}\n")
        f.write(f"**Organizations found:** {len(all_orgs)}\n")
        f.write(f"**Generated:** ECO-71 Researcher run\n\n")
        f.write(f"*Note: These orgs were found via web search and need verification. ")
        f.write(f"Honduras has a rich civil society -- indigenous, campesino, Garífuna, and women's movements. ")
        f.write(f"Treat as leads for human review.*\n\n")
        f.write(f"---\n\n")
        
        for area, orgs in sorted(by_area.items()):
            f.write(f"## {area.replace('_', ' ').title()} ({len(orgs)} orgs)\n\n")
            f.write(f"| Name | Location | Framework Area | Description | Website | Source |\n")
            f.write(f"|---|---|---|---|---|---|\n")
            for org in orgs:
                name = org['name'].replace('|', '-')[:80]
                desc = org['description'].replace('|', '-').replace('\n', ' ')[:120]
                web = org['website'][:60] if org['website'] else ''
                src = org['source'][:40]
                f.write(f"| {name} | Honduras | {area} | {desc} | {web} | {src} |\n")
            f.write(f"\n")
        
        f.write(f"---\n\n")
        f.write(f"## Coverage Assessment\n\n")
        f.write(f"- IRS BMF records for HN: 0 (expected -- US-only database)\n")
        f.write(f"- This research adds: {len(all_orgs)} Honduran organizations\n")
        f.write(f"- Framework coverage: {', '.join(f'{a}({len(o)})' for a,o in sorted(by_area.items()))}\n")
        f.write(f"- Recommended follow-up: Contact ASONOG (Asociacion de ONGs), FOPRIDEH for formal registry\n")
    
    print(f"\nECO-71 COMPLETE", flush=True)
    print(f"Total orgs: {len(all_orgs)}", flush=True)
    print(f"Output: {OUTPUT_FILE}", flush=True)
    
    return len(all_orgs)

if __name__ == '__main__':
    count = main()
    sys.exit(0 if count >= 0 else 1)
