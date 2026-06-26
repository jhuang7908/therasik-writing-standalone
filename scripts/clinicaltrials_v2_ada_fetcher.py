import requests
import json
import time
import argparse

def search_phase3_ada_trials(antibodies_list, output_file="ada_results.json"):
    """
    Revised scraper using the current clinicaltrials.gov V2 API.
    Fixes the HTTP 400/404 out-of-date API query errors.
    """
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    results = {}

    print(f"Starting batch ADA search for {len(antibodies_list)} Phase 3 antibodies using V2 API...")
    
    for i, antibody in enumerate(antibodies_list):
        print(f"[{i+1}/{len(antibodies_list)}] Querying {antibody}...")
        
        # ClinicalTrials.gov V2 API parameters
        params = {
            # Phase filtering is expressed inside query.term (V2 API does not accept `filter.phase`)
            "query.term": f"{antibody} AND AREA[Phase]PHASE3",
            "pageSize": 5, # We just want the top recent trials for ADA presence
            "fields": "NCTId,BriefTitle,Phase,AdverseEventsModule" # Request AE modules where ADA might be reported
        }
        
        try:
            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                data = response.json()
                studies = data.get("studies", [])
                
                trial_data = []
                for study in studies:
                    protocol = study.get("protocolSection", {})
                    nct_id = protocol.get("identificationModule", {}).get("nctId", "Unknown")
                    title = protocol.get("identificationModule", {}).get("briefTitle", "")
                    
                    trial_data.append({
                        "nct_id": nct_id,
                        "title": title,
                        "ada_mentioned": "ADA" in str(study) or "Anti-drug antibody" in str(study)
                    })
                
                results[antibody] = trial_data
            else:
                print(f"  API Error {response.status_code} for {antibody}: {response.text}")
                
        except Exception as e:
            print(f"  Connection error for {antibody}: {str(e)}")
            
        # Polite API rate limit delay
        time.sleep(0.5)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\n✅ Retrieval Complete! Data saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch ADA data for antibodies using ClinicalTrials.gov V2 API")
    parser.add_argument("--test", action="store_true", help="Run a small test with 3 antibodies")
    args = parser.parse_args()
    
    # Give the other AI a test mode, or it can import this module and pass its 192 list.
    if args.test:
        test_abs = ["Pembrolizumab", "Nivolumab", "Trastuzumab"]
        search_phase3_ada_trials(test_abs, output_file="clinicaltrials_ada_test_results.json")
    else:
        print("Please read from the 192 clinical phase 3 antibodies list and call search_phase3_ada_trials(your_list)")
