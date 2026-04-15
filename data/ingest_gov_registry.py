"""
Ecolibrium Government Registry Ingestion Pipeline
Tier 1 bulk downloads with multi-language support and audit filtering.

Usage:
    python ingest_gov_registry.py --source uk
    python ingest_gov_registry.py --source france
    python ingest_gov_registry.py --source japan
    python ingest_gov_registry.py --source australia
    python ingest_gov_registry.py --source nz
    python ingest_gov_registry.py --source all
"""
import sqlite3
import os
import sys
import json
import csv
import io
csv.field_size_limit(10**7)  # Handle very large charity description fields
import zipfile
import requests
import time
import re
import argparse
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'ecolibrium_directory.db')

# ============================================================
# MULTI-LANGUAGE ALIGNMENT KEYWORDS
# Each language maps keywords to framework areas
# ============================================================

ALIGNMENT_KEYWORDS = {
    'en': {
        'strong_positive': [
            'cooperative', 'co-op', 'mutual aid', 'community land trust',
            'affordable housing', 'food bank', 'food pantry', 'community garden',
            'civic engagement', 'human rights', 'civil liberties', 'environmental justice',
            'community health', 'mental health', 'legal aid', 'restorative justice',
            'refugee', 'immigrant', 'indigenous', 'community development',
            'youth development', 'worker-owned', 'solidarity', 'grassroots',
            'advocacy', 'public interest', 'conservation', 'renewable energy',
            'social enterprise', 'fair trade', 'microfinance', 'credit union',
            'community organizing', 'participatory', 'transparency',
            'disability', 'homelessness', 'shelter', 'literacy',
        ],
        'exclude': [
            'church', 'parish', 'mosque', 'synagogue', 'temple',
            'golf club', 'country club', 'yacht club', 'polo club',
            'rotary club', 'lions club', 'kiwanis', 'masonic',
            'fraternal order', 'homeowners association', 'hoa',
            'booster club', 'alumni association', 'cemetery',
            'kennel club', 'rodeo', 'bar association',
            'chamber of commerce', 'political action committee',
        ],
    },
    'fr': {
        'strong_positive': [
            'cooperative', 'coop', 'mutuelle', 'aide mutuelle',
            'logement social', 'banque alimentaire', 'jardin communautaire',
            'droits humains', 'droits civiques', 'justice environnementale',
            'sante communautaire', 'sante mentale', 'aide juridique',
            'refugie', 'immigrant', 'autochtone', 'developpement communautaire',
            'economie sociale', 'economie solidaire', 'commerce equitable',
            'microfinance', 'insertion', 'reinsertion', 'alphabetisation',
            'handicap', 'sans-abri', 'hebergement', 'solidarite',
            'action sociale', 'protection environnement', 'energie renouvelable',
            'agriculture biologique', 'permaculture', 'agroecologie',
            'democratie participative', 'transparence', 'citoyennete',
            'education populaire', 'mediation', 'prevention',
        ],
        'exclude': [
            'eglise', 'paroisse', 'mosquee', 'synagogue',
            'club de golf', 'club nautique', 'franc-maconnerie',
            'association de proprietaires', 'copropriete',
            'association anciens eleves', 'cimetiere',
            'club canin', 'chambre de commerce',
            'ordre professionnel', 'syndicat patronal',
        ],
    },
    'ja': {
        'strong_positive': [
            'NPO', 'NGO', '協同組合', '生活協同組合', '生協',
            '社会福祉', '福祉法人', '地域福祉', 'ボランティア',
            '市民活動', '環境保全', '環境保護', '自然保護',
            '人権', '障害者', '高齢者', '子育て支援',
            '国際協力', '国際交流', '地域づくり', 'まちづくり',
            '食料支援', 'フードバンク', '居住支援',
            '消費者', '平和', '難民支援', '多文化共生',
            '再生可能エネルギー', '有機農業',
        ],
        'exclude': [
            '宗教法人', '神社', '寺院', '教会',
            'ゴルフ', 'カントリークラブ', 'ヨットクラブ',
            '同窓会', '墓地', 'ペット', '犬',
            '商工会議所', '業界団体',
        ],
    },
    'pt': {
        'strong_positive': [
            'cooperativa', 'associacao comunitaria', 'economia solidaria',
            'direitos humanos', 'justica social', 'meio ambiente',
            'saude comunitaria', 'saude mental', 'assistencia juridica',
            'refugiado', 'imigrante', 'indigena', 'quilombola',
            'desenvolvimento comunitario', 'agricultura familiar',
            'agroecologia', 'permacultura', 'banco comunitario',
            'microfinanca', 'economia popular', 'comercio justo',
            'energia renovavel', 'habitacao social', 'sem-teto',
            'alfabetizacao', 'inclusao', 'acessibilidade',
            'transparencia', 'participacao social', 'controle social',
        ],
        'exclude': [
            'igreja', 'paroquia', 'mesquita', 'sinagoga',
            'clube de golfe', 'iate clube', 'maconaria',
            'associacao de moradores', 'condominio',
            'associacao de ex-alunos', 'cemiterio',
            'canil', 'camara de comercio', 'ordem profissional',
        ],
    },
    'es': {
        'strong_positive': [
            'cooperativa', 'ayuda mutua', 'economia solidaria',
            'derechos humanos', 'justicia social', 'medio ambiente',
            'salud comunitaria', 'salud mental', 'asistencia legal',
            'refugiado', 'inmigrante', 'indigena', 'campesino',
            'desarrollo comunitario', 'agricultura familiar',
            'agroecologia', 'permacultura', 'comercio justo',
            'microfinanzas', 'vivienda social', 'sin hogar',
            'alfabetizacion', 'inclusion', 'accesibilidad',
            'transparencia', 'participacion ciudadana',
            'energia renovable', 'soberania alimentaria',
        ],
        'exclude': [
            'iglesia', 'parroquia', 'mezquita', 'sinagoga',
            'club de golf', 'club nautico', 'masoneria',
            'asociacion de propietarios', 'cementerio',
            'camara de comercio', 'colegio profesional',
        ],
    },
    'de': {
        'strong_positive': [
            'genossenschaft', 'selbsthilfe', 'solidarische',
            'menschenrechte', 'soziale gerechtigkeit', 'umweltschutz',
            'gemeinwohl', 'gemeinnuetzig', 'wohlfahrt',
            'fluechtling', 'migration', 'inklusion', 'barrierefreiheit',
            'gemeinschaftsgarten', 'erneuerbare energie', 'klimaschutz',
            'nachhaltig', 'oekologisch', 'bio', 'fairtrade',
            'sozialunternehmen', 'buergerinitiative', 'partizipation',
            'transparenz', 'ehrenamt', 'freiwillig',
            'jugendhilfe', 'altenhilfe', 'behindertenhilfe',
            'obdachlos', 'wohnungsnot', 'tafel',
        ],
        'exclude': [
            'kirche', 'gemeinde', 'moschee', 'synagoge',
            'golfclub', 'yachtclub', 'schuetzenverein',
            'freimaurerloge', 'eigentuemergemeinschaft',
            'friedhof', 'hundeverein', 'industrie und handelskammer',
            'berufsverband', 'standesorganisation',
        ],
    },
    'ko': {
        'strong_positive': [
            '협동조합', '사회적기업', '마을기업', '자활',
            '시민단체', '인권', '환경', '복지',
            '자원봉사', '지역사회', '사회적경제',
            '공정무역', '친환경', '재생에너지',
            '장애인', '노인', '아동', '청소년',
            '난민', '이주민', '다문화',
        ],
        'exclude': [
            '교회', '성당', '사찰', '모스크',
            '골프', '요트', '동문회', '묘지',
            '상공회의소',
        ],
    },
}

# Framework area classification keywords (multi-language)
FRAMEWORK_KEYWORDS_ML = {
    'healthcare': {
        'en': ['health', 'clinic', 'hospital', 'medical', 'mental health', 'disability', 'hiv', 'aids', 'maternal'],
        'fr': ['sante', 'clinique', 'hopital', 'medical', 'handicap', 'vih', 'sida', 'maternite'],
        'ja': ['健康', '医療', '福祉', '障害', '介護', '看護'],
        'pt': ['saude', 'clinica', 'hospital', 'medico', 'deficiencia'],
        'es': ['salud', 'clinica', 'hospital', 'medico', 'discapacidad'],
        'de': ['gesundheit', 'klinik', 'krankenhaus', 'medizin', 'behinderung', 'pflege'],
        'ko': ['건강', '의료', '복지', '장애', '간호'],
    },
    'food': {
        'en': ['food', 'farm', 'agriculture', 'nutrition', 'hunger', 'seed', 'crop', 'permaculture'],
        'fr': ['alimentaire', 'ferme', 'agriculture', 'nutrition', 'faim', 'semence', 'permaculture'],
        'ja': ['食料', '農業', '食品', '飢餓', '有機'],
        'pt': ['alimentacao', 'agricultura', 'nutricao', 'fome', 'semente', 'permacultura'],
        'es': ['alimentacion', 'agricultura', 'nutricion', 'hambre', 'semilla', 'permacultura'],
        'de': ['ernaehrung', 'landwirtschaft', 'lebensmittel', 'hunger', 'saatgut', 'permakultur'],
        'ko': ['식량', '농업', '영양', '식품'],
    },
    'education': {
        'en': ['education', 'school', 'literacy', 'learning', 'training', 'library'],
        'fr': ['education', 'ecole', 'alphabetisation', 'formation', 'bibliotheque'],
        'ja': ['教育', '学校', '学習', '図書館', '研修'],
        'pt': ['educacao', 'escola', 'alfabetizacao', 'formacao', 'biblioteca'],
        'es': ['educacion', 'escuela', 'alfabetizacion', 'formacion', 'biblioteca'],
        'de': ['bildung', 'schule', 'alphabetisierung', 'ausbildung', 'bibliothek'],
        'ko': ['교육', '학교', '학습', '도서관'],
    },
    'ecology': {
        'en': ['environment', 'ecology', 'conservation', 'climate', 'biodiversity', 'forest', 'wildlife', 'renewable'],
        'fr': ['environnement', 'ecologie', 'conservation', 'climat', 'biodiversite', 'foret', 'renouvelable'],
        'ja': ['環境', '生態', '保全', '気候', '生物多様性', '森林', '再生可能'],
        'pt': ['meio ambiente', 'ecologia', 'conservacao', 'clima', 'biodiversidade', 'floresta', 'renovavel'],
        'es': ['medio ambiente', 'ecologia', 'conservacion', 'clima', 'biodiversidad', 'bosque', 'renovable'],
        'de': ['umwelt', 'oekologie', 'naturschutz', 'klima', 'biodiversitaet', 'wald', 'erneuerbar'],
        'ko': ['환경', '생태', '보전', '기후', '생물다양성', '산림', '재생'],
    },
    'housing_land': {
        'en': ['housing', 'shelter', 'land trust', 'homeless', 'eviction', 'affordable housing', 'tenant'],
        'fr': ['logement', 'hebergement', 'foncier', 'sans-abri', 'expulsion', 'locataire'],
        'ja': ['住宅', '住居', '居住支援', 'ホームレス'],
        'pt': ['habitacao', 'moradia', 'sem-teto', 'fundiario', 'inquilino'],
        'es': ['vivienda', 'albergue', 'sin hogar', 'desahucio', 'inquilino'],
        'de': ['wohnen', 'obdachlos', 'grundstueck', 'mieter', 'sozialwohnung'],
        'ko': ['주거', '주택', '노숙', '세입자'],
    },
    'democracy': {
        'en': ['democracy', 'civic', 'governance', 'voting', 'transparency', 'accountability', 'human rights', 'civil liberties'],
        'fr': ['democratie', 'civique', 'gouvernance', 'vote', 'transparence', 'droits humains', 'libertes civiles'],
        'ja': ['民主主義', '市民', 'ガバナンス', '投票', '透明性', '人権'],
        'pt': ['democracia', 'civico', 'governanca', 'voto', 'transparencia', 'direitos humanos'],
        'es': ['democracia', 'civico', 'gobernanza', 'voto', 'transparencia', 'derechos humanos'],
        'de': ['demokratie', 'buergerlich', 'governance', 'wahl', 'transparenz', 'menschenrechte'],
        'ko': ['민주주의', '시민', '거버넌스', '투표', '투명성', '인권'],
    },
    'cooperatives': {
        'en': ['cooperative', 'co-op', 'worker-owned', 'mutual', 'solidarity economy', 'credit union', 'social enterprise'],
        'fr': ['cooperative', 'mutuelle', 'economie solidaire', 'caisse populaire', 'entreprise sociale'],
        'ja': ['協同組合', '生協', '共済', '社会的企業'],
        'pt': ['cooperativa', 'economia solidaria', 'cooperativa de credito', 'empresa social'],
        'es': ['cooperativa', 'economia solidaria', 'cooperativa de credito', 'empresa social'],
        'de': ['genossenschaft', 'selbsthilfe', 'solidarische oekonomie', 'sozialunternehmen'],
        'ko': ['협동조합', '사회적기업', '사회적경제'],
    },
    'conflict': {
        'en': ['justice', 'conflict', 'mediation', 'peace', 'restorative', 'prison', 'legal aid', 'refugee'],
        'fr': ['justice', 'conflit', 'mediation', 'paix', 'restauratif', 'prison', 'aide juridique', 'refugie'],
        'ja': ['正義', '紛争', '調停', '平和', '修復的', '難民'],
        'pt': ['justica', 'conflito', 'mediacao', 'paz', 'restaurativo', 'prisao', 'refugiado'],
        'es': ['justicia', 'conflicto', 'mediacion', 'paz', 'restaurativo', 'prision', 'refugiado'],
        'de': ['justiz', 'konflikt', 'mediation', 'frieden', 'restorative', 'gefaengnis', 'fluechtling'],
        'ko': ['정의', '분쟁', '중재', '평화', '회복', '난민'],
    },
    'recreation_arts': {
        'en': ['community arts', 'cultural center', 'heritage', 'museum', 'community theater', 'folk arts'],
        'fr': ['arts communautaires', 'centre culturel', 'patrimoine', 'musee', 'theatre communautaire'],
        'ja': ['文化', '芸術', '博物館', '伝統', '地域文化'],
        'pt': ['artes comunitarias', 'centro cultural', 'patrimonio', 'museu'],
        'es': ['artes comunitarias', 'centro cultural', 'patrimonio', 'museo'],
        'de': ['gemeinschaftskunst', 'kulturzentrum', 'kulturerbe', 'museum'],
        'ko': ['문화', '예술', '박물관', '전통', '지역문화'],
    },
}


def detect_language(text):
    """Simple language detection based on character ranges and common words."""
    if not text:
        return 'en'
    # Japanese (contains CJK + Hiragana/Katakana)
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
        return 'ja'
    # Korean (Hangul)
    if re.search(r'[\uAC00-\uD7AF\u1100-\u11FF]', text):
        return 'ko'
    # Chinese (CJK without Japanese kana)
    if re.search(r'[\u4E00-\u9FFF]', text) and not re.search(r'[\u3040-\u30FF]', text):
        return 'zh'
    # French indicators
    if any(w in text.lower() for w in ['association', 'fondation', "l'", 'des ', 'les ', 'pour ']):
        return 'fr'
    # Portuguese indicators
    if any(w in text.lower() for w in ['associacao', 'cooperativa de', 'fundacao', 'instituto']):
        return 'pt'
    # Spanish indicators
    if any(w in text.lower() for w in ['asociacion', 'cooperativa de', 'fundacion']):
        return 'es'
    # German indicators
    if any(w in text.lower() for w in ['verein', 'stiftung', 'genossenschaft', 'e.v.']):
        return 'de'
    return 'en'


def classify_org_ml(name, description='', country_code=''):
    """Classify an org using multi-language keywords. Returns (framework_area, alignment_score, should_exclude)."""
    lang = detect_language(name + ' ' + (description or ''))
    combined = (name + ' ' + (description or '')).lower()
    
    # Normalize accented chars for matching
    import unicodedata
    combined_norm = unicodedata.normalize('NFD', combined)
    combined_norm = ''.join(c for c in combined_norm if unicodedata.category(c) != 'Mn')
    combined_check = combined + ' ' + combined_norm
    
    # Check exclusions (any language)
    for check_lang in ALIGNMENT_KEYWORDS:
        for pattern in ALIGNMENT_KEYWORDS[check_lang].get('exclude', []):
            if pattern in combined_check:
                return None, -1, True
    
    # Score alignment
    score = 0
    for check_lang in ALIGNMENT_KEYWORDS:
        for kw in ALIGNMENT_KEYWORDS[check_lang].get('strong_positive', []):
            if kw in combined_check:
                score += 2
    
    # Classify framework area
    best_area = None
    best_score = 0
    for area, lang_keywords in FRAMEWORK_KEYWORDS_ML.items():
        area_score = 0
        for kw_lang, keywords in lang_keywords.items():
            for kw in keywords:
                if kw.lower() in combined_check:
                    area_score += 1
        if area_score > best_score:
            best_score = area_score
            best_area = area
    
    return best_area or 'democracy', min(score, 10), False


def ingest_org(cursor, org_data):
    """Insert or update an org, applying audit filter. Returns True if kept, False if excluded."""
    name = org_data.get('name', '').strip()
    if not name:
        return False
    
    desc = org_data.get('description', '') or ''
    cc = org_data.get('country_code', '')
    
    framework_area, alignment_score, should_exclude = classify_org_ml(name, desc, cc)
    
    if should_exclude:
        return False
    
    # Must have at least some positive signal
    if alignment_score < 1 and not any(kw in name.lower() for kw in [
        'foundation', 'trust', 'charity', 'ngo', 'npo',
        'fondation', 'fondazione', 'fundacion', 'fundacao', 'stiftung',
        'verein', 'forening', 'vereniging', 'stichting',
    ]):
        return False
    
    cursor.execute("""
        INSERT OR IGNORE INTO organizations 
        (name, country_code, country_name, state_province, city,
         registration_id, registration_type, description, website, email,
         framework_area, source, source_id, status, alignment_score, lat, lon)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
    """, (
        name,
        org_data.get('country_code', ''),
        org_data.get('country_name', ''),
        org_data.get('state_province', ''),
        org_data.get('city', ''),
        org_data.get('registration_id', ''),
        org_data.get('registration_type', ''),
        desc,
        org_data.get('website', ''),
        org_data.get('email', ''),
        framework_area,
        org_data.get('source', ''),
        org_data.get('source_id', ''),
        alignment_score,
        org_data.get('lat'),
        org_data.get('lon'),
    ))
    return cursor.rowcount > 0


# ============================================================
# SOURCE-SPECIFIC INGESTORS
# ============================================================

def ingest_uk(db):
    """UK Charity Commission for England & Wales + OSCR (Scotland)."""
    c = db.cursor()
    added = 0
    skipped = 0
    
    # England & Wales
    print("[UK] Downloading Charity Commission data...")
    url = "https://ccewuksprdoneregsadata1.blob.core.windows.net/data/txt/publicextract.charity.zip"
    try:
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            # Find the charity file
            charity_files = [f for f in zf.namelist() if 'charity' in f.lower() and f.endswith('.txt')]
            if not charity_files:
                print(f"  Warning: no charity file found in zip. Files: {zf.namelist()}")
                return
            
            print(f"  Found files: {zf.namelist()}")
            # Use the main charity file
            main_file = charity_files[0]
            print(f"  Processing {main_file}...")
            
            with zf.open(main_file) as f:
                text = f.read().decode('utf-8-sig', errors='replace')
                reader = csv.DictReader(io.StringIO(text), delimiter='\t')
                
                for row in reader:
                    name = row.get('charity_name', '') or row.get('name', '')
                    if not name:
                        continue
                    
                    reg_status = row.get('charity_registration_status', '')
                    if reg_status and 'removed' in reg_status.lower():
                        continue
                    
                    kept = ingest_org(c, {
                        'name': name,
                        'country_code': 'GB',
                        'country_name': 'United Kingdom',
                        'registration_id': row.get('registered_charity_number', ''),
                        'registration_type': 'charity_commission_ew',
                        'description': row.get('charity_activities', '') or row.get('charitable_objects', ''),
                        'website': row.get('charity_contact_web', ''),
                        'email': row.get('charity_contact_email', ''),
                        'source': 'uk_charity_commission',
                        'source_id': row.get('registered_charity_number', ''),
                    })
                    if kept:
                        added += 1
                    else:
                        skipped += 1
                    
                    if (added + skipped) % 10000 == 0:
                        print(f"  Processed {added + skipped:,} (kept {added:,}, skipped {skipped:,})")
                        db.commit()
        
        db.commit()
        print(f"  [UK-EW] Done: {added:,} added, {skipped:,} filtered out")
    except Exception as e:
        print(f"  [UK-EW] Error: {e}")
    
    # Scotland (OSCR)
    print("[UK] Downloading OSCR Scottish Charity Register...")
    oscr_url = "https://www.oscr.org.uk/umbraco/Surface/FormsSurface/CharityRegisterDownload"
    try:
        resp = requests.get(oscr_url, timeout=60, headers={'User-Agent': 'Ecolibrium/1.0'})
        if resp.status_code == 200 and len(resp.content) > 1000:
            text = resp.content.decode('utf-8-sig', errors='replace')
            reader = csv.DictReader(io.StringIO(text))
            scot_added = 0
            scot_skipped = 0
            for row in reader:
                name = row.get('Charity Name', '')
                if not name:
                    continue
                kept = ingest_org(c, {
                    'name': name,
                    'country_code': 'GB',
                    'country_name': 'United Kingdom',
                    'state_province': 'Scotland',
                    'registration_id': row.get('Charity Number', ''),
                    'registration_type': 'oscr_scotland',
                    'description': row.get('Purposes', '') or row.get('Activities', ''),
                    'website': row.get('Website', ''),
                    'source': 'oscr_scotland',
                    'source_id': row.get('Charity Number', ''),
                })
                if kept:
                    scot_added += 1
                else:
                    scot_skipped += 1
            db.commit()
            print(f"  [UK-SCT] Done: {scot_added:,} added, {scot_skipped:,} filtered")
            added += scot_added
        else:
            print(f"  [UK-SCT] Download failed (status {resp.status_code})")
    except Exception as e:
        print(f"  [UK-SCT] Error: {e}")
    
    return added


def ingest_france(db):
    """France RNA from data.gouv.fr."""
    c = db.cursor()
    added = 0
    skipped = 0
    
    print("[FR] Downloading RNA from data.gouv.fr...")
    # The RNA dataset page - we need to find the actual CSV URL
    dataset_url = "https://www.data.gouv.fr/fr/datasets/repertoire-national-des-associations/"
    
    try:
        # Try direct RNA download
        rna_url = "https://static.data.gouv.fr/resources/repertoire-national-des-associations/20241001-063527/rna-waldec-20241001.csv.gz"
        print(f"  Trying RNA CSV download...")
        resp = requests.get(rna_url, timeout=120, stream=True)
        
        if resp.status_code != 200:
            # Try alternate URL pattern
            print(f"  Direct URL failed ({resp.status_code}), trying dataset page...")
            page_resp = requests.get(dataset_url, timeout=30)
            # Look for CSV download links
            csv_links = re.findall(r'https://[^"]+rna[^"]*\.csv[^"]*', page_resp.text)
            if csv_links:
                rna_url = csv_links[0]
                print(f"  Found: {rna_url}")
                resp = requests.get(rna_url, timeout=120, stream=True)
            else:
                print(f"  Could not find RNA CSV URL on dataset page")
                return 0
        
        import gzip
        try:
            content = gzip.decompress(resp.content)
        except Exception:
            content = resp.content
        
        text = content.decode('utf-8', errors='replace')
        reader = csv.DictReader(io.StringIO(text), delimiter=';')
        
        for row in reader:
            name = row.get('titre', '') or row.get('titre_court', '')
            if not name:
                continue
            
            # Skip dissolved associations
            if row.get('date_dissolution') or row.get('nature') == 'D':
                continue
            
            objet = row.get('objet', '') or ''
            
            kept = ingest_org(c, {
                'name': name,
                'country_code': 'FR',
                'country_name': 'France',
                'state_province': row.get('libelle_commune', ''),
                'city': row.get('libelle_commune', ''),
                'registration_id': row.get('id', '') or row.get('id_assoc', ''),
                'registration_type': 'rna_france',
                'description': objet,
                'website': row.get('siteweb', ''),
                'source': 'rna_france',
                'source_id': row.get('id', ''),
            })
            if kept:
                added += 1
            else:
                skipped += 1
            
            if (added + skipped) % 50000 == 0:
                print(f"  Processed {added + skipped:,} (kept {added:,}, skipped {skipped:,})")
                db.commit()
        
        db.commit()
        print(f"  [FR] Done: {added:,} added, {skipped:,} filtered")
    except Exception as e:
        print(f"  [FR] Error: {e}")
    
    return added


def ingest_japan(db):
    """Japan Cabinet Office NPO Portal."""
    c = db.cursor()
    added = 0
    skipped = 0
    
    print("[JP] Downloading Cabinet Office NPO data...")
    npo_url = "https://www.npo-homepage.go.jp/npoportal/datadownload"
    
    try:
        # Try to get the bulk CSV
        resp = requests.get(npo_url, timeout=30, headers={'User-Agent': 'Ecolibrium/1.0'})
        # Look for CSV download links
        csv_links = re.findall(r'https://[^"]+\.csv[^"]*', resp.text)
        
        if not csv_links:
            # Try direct known URL
            csv_links = ['https://www.npo-homepage.go.jp/npoportal/datadownload/npoinfo_all.csv']
        
        for csv_url in csv_links[:1]:
            print(f"  Downloading {csv_url}...")
            csv_resp = requests.get(csv_url, timeout=120, headers={'User-Agent': 'Ecolibrium/1.0'})
            
            if csv_resp.status_code != 200:
                print(f"  Failed ({csv_resp.status_code})")
                continue
            
            # Japanese CSV - try Shift-JIS and UTF-8
            for encoding in ['utf-8-sig', 'shift_jis', 'cp932', 'utf-8']:
                try:
                    text = csv_resp.content.decode(encoding, errors='replace')
                    break
                except Exception:
                    continue
            
            reader = csv.DictReader(io.StringIO(text))
            
            for row in reader:
                # Try common Japanese NPO CSV column names
                name = (row.get('法人名', '') or row.get('名称', '') or 
                       row.get('name', '') or list(row.values())[0] if row else '')
                if not name:
                    continue
                
                desc = row.get('定款に記載された目的', '') or row.get('活動分野', '') or ''
                
                kept = ingest_org(c, {
                    'name': name,
                    'country_code': 'JP',
                    'country_name': 'Japan',
                    'state_province': row.get('所在地', '') or row.get('都道府県', ''),
                    'registration_id': row.get('法人番号', '') or row.get('認証番号', ''),
                    'registration_type': 'cabinet_office_npo',
                    'description': desc,
                    'website': row.get('ホームページ', '') or row.get('HP', ''),
                    'source': 'japan_npo_portal',
                    'source_id': row.get('法人番号', ''),
                })
                if kept:
                    added += 1
                else:
                    skipped += 1
            
            db.commit()
            print(f"  [JP] Done: {added:,} added, {skipped:,} filtered")
    except Exception as e:
        print(f"  [JP] Error: {e}")
    
    return added


def ingest_australia(db):
    """Australia ACNC Charity Register."""
    c = db.cursor()
    added = 0
    skipped = 0
    
    print("[AU] Downloading ACNC Charity Register...")
    acnc_url = "https://data.gov.au/data/dataset/b050b242-4487-4306-abf5-07ca073e5594"
    
    try:
        resp = requests.get(acnc_url, timeout=30)
        csv_links = re.findall(r'https://[^"]+\.csv[^"]*', resp.text)
        
        if not csv_links:
            print(f"  Could not find CSV link on ACNC page")
            return 0
        
        csv_url = csv_links[0]
        print(f"  Found: {csv_url}")
        csv_resp = requests.get(csv_url, timeout=120)
        
        text = csv_resp.content.decode('utf-8-sig', errors='replace')
        reader = csv.DictReader(io.StringIO(text))
        
        for row in reader:
            name = row.get('Charity_Legal_Name', '') or row.get('name', '')
            if not name:
                continue
            
            status = row.get('Registration_Status', '')
            if status and 'revoked' in status.lower():
                continue
            
            kept = ingest_org(c, {
                'name': name,
                'country_code': 'AU',
                'country_name': 'Australia',
                'state_province': row.get('State', ''),
                'city': row.get('Town_City', ''),
                'registration_id': row.get('ABN', ''),
                'registration_type': 'acnc_australia',
                'description': row.get('Charity_Sub_Type', ''),
                'website': row.get('Website', ''),
                'source': 'acnc_australia',
                'source_id': row.get('ABN', ''),
            })
            if kept:
                added += 1
            else:
                skipped += 1
        
        db.commit()
        print(f"  [AU] Done: {added:,} added, {skipped:,} filtered")
    except Exception as e:
        print(f"  [AU] Error: {e}")
    
    return added


def ingest_nz(db):
    """New Zealand Charities Register."""
    c = db.cursor()
    added = 0
    skipped = 0
    
    print("[NZ] Downloading NZ Charities Register...")
    nz_url = "https://www.charities.govt.nz/charities-in-new-zealand/the-charities-register/"
    
    try:
        # Try to get the CSV/data download
        resp = requests.get("https://www.charities.govt.nz/assets/Charities-Data/charities-register-all.csv", 
                          timeout=60, headers={'User-Agent': 'Ecolibrium/1.0'})
        
        if resp.status_code != 200:
            print(f"  Direct CSV failed ({resp.status_code}). Trying alternate...")
            # Try data.govt.nz
            resp = requests.get("https://catalogue.data.govt.nz/dataset/charities-register-download", timeout=30)
            csv_links = re.findall(r'https://[^"]+\.csv[^"]*', resp.text)
            if csv_links:
                resp = requests.get(csv_links[0], timeout=60)
            else:
                print(f"  Could not find NZ charities CSV")
                return 0
        
        text = resp.content.decode('utf-8-sig', errors='replace')
        reader = csv.DictReader(io.StringIO(text))
        
        for row in reader:
            name = row.get('Organisation Name', '') or row.get('name', '')
            if not name:
                continue
            
            status = row.get('Status', '')
            if status and 'deregistered' in status.lower():
                continue
            
            kept = ingest_org(c, {
                'name': name,
                'country_code': 'NZ',
                'country_name': 'New Zealand',
                'city': row.get('City', ''),
                'registration_id': row.get('Registration Number', ''),
                'registration_type': 'nz_charities',
                'description': row.get('Activities', '') or row.get('Purpose', ''),
                'website': row.get('Website', ''),
                'source': 'nz_charities_register',
                'source_id': row.get('Registration Number', ''),
            })
            if kept:
                added += 1
            else:
                skipped += 1
        
        db.commit()
        print(f"  [NZ] Done: {added:,} added, {skipped:,} filtered")
    except Exception as e:
        print(f"  [NZ] Error: {e}")
    
    return added


def main():
    parser = argparse.ArgumentParser(description='Ecolibrium Government Registry Ingestion')
    parser.add_argument('--source', required=True, 
                       choices=['uk', 'france', 'japan', 'australia', 'nz', 'all'],
                       help='Which registry to ingest')
    args = parser.parse_args()
    
    db = sqlite3.connect(DB_PATH)
    
    sources = {
        'uk': ingest_uk,
        'france': ingest_france,
        'japan': ingest_japan,
        'australia': ingest_australia,
        'nz': ingest_nz,
    }
    
    if args.source == 'all':
        total = 0
        for name, func in sources.items():
            result = func(db)
            total += (result or 0)
        print(f"\n=== TOTAL INGESTED: {total:,} orgs ===")
    else:
        result = sources[args.source](db)
        print(f"\n=== INGESTED: {result or 0:,} orgs ===")
    
    # Show final counts
    c = db.cursor()
    c.execute("SELECT COUNT(*) FROM organizations WHERE status = 'active'")
    print(f"Total active orgs in DB: {c.fet