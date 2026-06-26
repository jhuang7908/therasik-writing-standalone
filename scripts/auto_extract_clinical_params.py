import pandas as pd
import urllib.request
import json
import time
import re
import os

INPUT_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_328_final_comprehensive.csv'
OUTPUT_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_328_with_params.csv'

def extract_from_text(text):
    if not text:
        return None, None, None, None
        
    text_lower = text.lower()
    
    # Extract Route
    route = []
    if 'intravenous' in text_lower or ' iv ' in text_lower or 'infusion' in text_lower:
        route.append('IV')
    if 'subcutaneous' in text_lower or ' sc ' in text_lower:
        route.append('SC')
    route_str = '/'.join(route) if route else None
    
    # Extract Dose (very naive regex for mg/kg or mg)
    dose = None
    dose_match = re.search(r'(\d+(?:\.\d+)?\s*(?:mg/kg|mg|g))', text_lower)
    if dose_match:
        dose = dose_match.group(1)
        
    # Extract Assay Type
    assay = None
    if 'electrochemiluminescence' in text_lower or 'ecl ' in text_lower or 'eclia' in text_lower:
        assay = 'ECLIA/ECL'
    elif 'enzyme-linked immunosorbent assay' in text_lower or 'elisa' in text_lower:
        assay = 'ELISA'
    elif 'radioimmunoassay' in text_lower or ' ria ' in text_lower:
        assay = 'RIA'
    elif 'surface plasmon resonance' in text_lower or ' spr ' in text_lower:
        assay = 'SPR'
        
    # Extract NAb%
    nab_pct = None
    # Look for "neutralizing antibody" or "nab" followed by some numbers
    # We try to find a percentage close to "neutralizing"
    nab_matches = re.finditer(r'(?:neutralizing|nab).*?(\d+(?:\.\d+)?)\s*%', text_lower)
    for m in nab_matches:
        nab_pct = m.group(1)
        break # take first matched
        
    return route_str, dose, assay, nab_pct

def main():
    print(f"Loading {INPUT_CSV}...")
    df = pd.read_csv(INPUT_CSV, low_memory=False)
    
    # Create new columns if they don't exist
    for col in ['route_extracted', 'dose_extracted', 'assay_extracted', 'nab_pct_extracted', 'fda_label_found']:
        if col not in df.columns:
            df[col] = None
            
    total = len(df)
    
    print("Starting OpenFDA API queries (with rate limiting)...")
    
    try:
        for idx, row in df.iterrows():
            ab_name = str(row['antibody_name']).strip()
            if not ab_name or str(ab_name).lower() == 'nan':
                continue
                
            # Skip if already extracted
            if pd.notna(row.get('fda_label_found')) and row.get('fda_label_found') == True:
                continue
                
            print(f"[{idx+1}/{total}] Querying OpenFDA for: {ab_name}")
            
            # API Query
            query_name = urllib.parse.quote(ab_name.lower().split()[0]) # take first word
            url = f"https://api.fda.gov/drug/label.json?search=openfda.generic_name:{query_name}&limit=1"
            
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                response = urllib.request.urlopen(req)
                data = json.loads(response.read().decode('utf-8'))
                
                if 'results' in data and len(data['results']) > 0:
                    result = data['results'][0]
                    df.at[idx, 'fda_label_found'] = True
                    
                    # Aggregate relevant text blocks
                    combined_text = ""
                    for section in ['dosage_and_administration', 'clinical_pharmacology', 'warnings_and_cautions', 'adverse_reactions']:
                        if section in result:
                            combined_text += " ".join(result[section]) + " "
                            
                    # Custom field 'immunogenicity' might exist inside 'adverse_reactions' or 'clinical_pharmacology'
                    
                    route, dose, assay, nab_pct = extract_from_text(combined_text)
                    
                    if route: df.at[idx, 'route_extracted'] = route
                    if dose: df.at[idx, 'dose_extracted'] = dose
                    if assay: df.at[idx, 'assay_extracted'] = assay
                    if nab_pct: df.at[idx, 'nab_pct_extracted'] = nab_pct
                    
                    print(f"  -> Found: Route={route}, Dose={dose}, Assay={assay}, NAb={nab_pct}%")
                else:
                    df.at[idx, 'fda_label_found'] = False
                    print("  -> No label found in OpenFDA.")
                    
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    df.at[idx, 'fda_label_found'] = False
                    print("  -> No label found (404).")
                else:
                    print(f"  -> HTTP Error {e.code}")
                    break # Stop on rate limit (e.g. 429)
            except Exception as e:
                print("  -> Error:", e)
                
            # Polite sleep to avoid rate limits (OpenFDA allows 240/min without key, 40/sec with key)
            # We'll sleep for 1 second just to be safe without an API key
            time.sleep(1)
            
            # Save progress periodically
            if idx > 0 and idx % 20 == 0:
                df.to_csv(OUTPUT_CSV, index=False)
                print(f"--- Progress saved to {OUTPUT_CSV} ---")
                
    except KeyboardInterrupt:
        print("Interrupted by user. Saving current progress...")
        
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nFinished! Extracted parameters saved to:\n{OUTPUT_CSV}")

if __name__ == "__main__":
    main()
