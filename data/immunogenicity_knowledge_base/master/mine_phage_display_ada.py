import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import pandas as pd
import re
import time
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_245_curated.csv'
output_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\phage_display_ada_hits.csv'

phage_display_list = [
    "Abelacimab", "Adalimumab", "Adecatumumab", "Afasevikumab", "Alextatug", "Alomfilimab", "Alsevalimab", 
    "Amlitelimab", "Anumigilimab", "Astegolimab", "Atisnolerbart", "Avdoralimab", "Avelumab", "Barecetamab", 
    "Belimumab", "Beludavimab", "Bempikibart", "Botensilimab", "Bremzalerbart", "Canrivitug", "Cenvacibart", 
    "Cliramitug", "Cosibelimab", "Crexavibart", "Crovalimab", "Dalnicastobart", "Daxdilimab", "Dusigitumab", 
    "Duvakitug", "Ecleralimab", "Efalizumab", "Enuzovimab", "Erzotabart", "Exerenibart", "Fasinumab", 
    "Felmetatug", "Fiztasovimab", "Flanvotumab", "Fletikumab", "Freneslerbart", "Fresolimumab", "Ganitumab", 
    "Garadacimab", "Gedivumab", "Ginisortamab", "Golocdacimab", "Gorivitug", "Guselkumab", "Ibramvibart", 
    "Iluzanebart", "Izastobart", "Lerdelimumab", "Letaplimab", "Lexatumumab", "Lomtegovimab", "Lucatumumab", 
    "Maridebart", "Metelimumab", "Mevonlerbart", "Mibavademab", "Narnatumab", "Necitumumab", "Negalstobart", 
    "Nepuvibart", "Nesvacumab", "Nurulimab", "Nuvustotug", "Oberotatug", "Odesivimab", "Oleclumab", "Omodenbamab", 
    "Ontamalimab", "Onvatilimab", "Opicinumab", "Ormutivimab", "Otilimab", "Pamrevlumab", "Patritumab", 
    "Ponsegromab", "Pozelimab", "Quisovalimab", "Rademikibart", "Ramucirumab", "Relatlimab", "Rinatabart", 
    "Robatumumab", "Rocatinlimab", "Roledumab", "Secukinumab", "Sintilimab", "Sonavibart", "Stamulumab", 
    "Sudubrilimab", "Sugemalimab", "Surzebiclimab", "Tamgiblimab", "Timcevibart", "Tiragolumab", "Tobevibart", 
    "Trabikibart", "Tremelimumab", "Trevogrumab", "Urelumab", "Verzistobart", "Vilamakitug", "Vofatamab", 
    "Zalutumumab", "Zinlirvimab"
]

# Get existing master
try:
    master_df = pd.read_csv(master_path)
    ada_found = set(master_df[master_df['ada_first_pct'].notna()]['antibody_name'].str.lower().dropna())
except Exception as e:
    ada_found = set()
    print("Master not found or error:", e)

missing_phage = [ab for ab in phage_display_list if ab.lower() not in ada_found]
print(f"Total Phage Display: {len(phage_display_list)}")
print(f"Already have ADA data: {len(phage_display_list) - len(missing_phage)}")
print(f"Missing ADA data (to search): {len(missing_phage)}")

def search_pubmed(query):
    try:
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(query)}&retmax=5"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, context=ctx, timeout=10)
        xml_data = response.read()
        root = ET.fromstring(xml_data)
        ids = [id_elem.text for id_elem in root.findall('.//IdList/Id')]
        return ids
    except Exception as e:
        print(f"Search error for {query}: {e}")
        return []

def fetch_abstracts(id_list):
    if not id_list: return []
    try:
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={','.join(id_list)}&retmode=xml"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, context=ctx, timeout=10)
        xml_data = response.read()
        root = ET.fromstring(xml_data)
        abstracts = []
        for article in root.findall('.//PubmedArticle'):
            abstract_texts = article.findall('.//AbstractText')
            full_abstract = " ".join([elem.text for elem in abstract_texts if elem.text])
            if full_abstract:
                abstracts.append(full_abstract)
        return abstracts
    except Exception as e:
        print(f"Fetch error: {e}")
        return []

def extract_ada_snippet(abstract, antibody):
    sentences = re.split(r'(?<=[.!?]) +', abstract)
    for sentence in sentences:
        s_lower = sentence.lower()
        if '%' in s_lower and ('ada' in s_lower or 'anti-drug antibody' in s_lower or 'immunogenicity' in s_lower or 'antibody' in s_lower):
            # Extract percentages
            pcts = re.findall(r'(\d+(?:\.\d+)?)\s*%', sentence)
            if pcts:
                return sentence, float(pcts[0])
    return None, None

results = []

print("Starting automated PubMed scraping...")
for i, antibody in enumerate(missing_phage):
    print(f"[{i+1}/{len(missing_phage)}] Searching {antibody}...")
    query = f"{antibody} AND (anti-drug antibody OR immunogenicity OR ADA)"
    ids = search_pubmed(query)
    
    if ids:
        abstracts = fetch_abstracts(ids)
        snippet_found = False
        for abstract in abstracts:
            snippet, pct = extract_ada_snippet(abstract, antibody)
            if snippet:
                results.append({
                    'antibody_name': antibody,
                    'ada_pct': pct,
                    'snippet': snippet,
                    'source': 'PubMed'
                })
                print(f"  -> Found ADA data: {pct}%")
                snippet_found = True
                break # Just take the first good abstract
        if not snippet_found:
            print("  -> No percentage data in abstracts.")
    else:
        print("  -> No PubMed hits.")
        
    time.sleep(0.4) # Respect rate limits (NCBI allows 3/sec without API key)

if results:
    df_res = pd.DataFrame(results)
    df_res.to_csv(output_path, index=False)
    print(f"Saved {len(results)} hits to {output_path}")
else:
    print("No ADA percentage data found across all candidates.")
