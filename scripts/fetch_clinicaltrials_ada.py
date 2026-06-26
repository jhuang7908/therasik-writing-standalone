import requests
import json
import time

def fetch_clinicaltrials(antibody_name):
    print(f"Fetching ClinicalTrials.gov for {antibody_name}...")
    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        "query.term": antibody_name,
        "filter.hasResults": "true",
        "pageSize": 50
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None

def analyze_studies(studies_data, antibody_name):
    if not studies_data or 'studies' not in studies_data:
        return []
    
    results = []
    keywords = ["anti-drug antibody", "ada", "immunogenicity", "neutralizing antibody", "nab", "anti-therapeutic antibody", "ata"]
    
    for study in studies_data['studies']:
        protocol = study.get('protocolSection', {})
        results_sec = study.get('resultsSection', {})
        
        nct_id = protocol.get('identificationModule', {}).get('nctId', 'Unknown')
        title = protocol.get('identificationModule', {}).get('briefTitle', 'Unknown')
        
        ada_found = False
        findings = []
        
        # Check outcome measures
        outcome_measures = results_sec.get('outcomeMeasuresModule', {}).get('outcomeMeasures', [])
        for outcome in outcome_measures:
            title_out = outcome.get('title', '').lower()
            desc = outcome.get('description', '').lower()
            
            if any(k in title_out or k in desc for k in keywords):
                ada_found = True
                findings.append({
                    "type": "Outcome Measure",
                    "title": outcome.get('title'),
                    "description": outcome.get('description'),
                    "classes": outcome.get('classes', [])
                })
        
        # Check adverse events
        ae_module = results_sec.get('adverseEventsModule', {})
        events = ae_module.get('seriousEvents', []) + ae_module.get('otherEvents', [])
        for ev in events:
            term = ev.get('term', '').lower()
            if any(k in term for k in keywords):
                ada_found = True
                findings.append({
                    "type": "Adverse Event",
                    "term": ev.get('term'),
                    "stats": ev.get('stats', [])
                })
                
        if ada_found:
            results.append({
                "nct_id": nct_id,
                "title": title,
                "findings": findings
            })
            
    return results

if __name__ == "__main__":
    antibodies = ["Pembrolizumab", "Nivolumab", "Trastuzumab"]
    all_results = {}
    
    for ab in antibodies:
        data = fetch_clinicaltrials(ab)
        if data:
            analyzed = analyze_studies(data, ab)
            all_results[ab] = analyzed
            print(f"Found {len(analyzed)} trials with ADA data for {ab}")
        time.sleep(1) # Be nice to the API
        
    with open("clinicaltrials_ada_extracted.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print("Done. Saved to clinicaltrials_ada_extracted.json")
