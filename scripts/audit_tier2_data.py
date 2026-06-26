import json
import os
import requests
import time
from core.resources.knowledge_bridge import InSynBioKnowledgeBridge

class Tier2Auditor:
    def __init__(self, tier2_path: str, output_path: str):
        self.tier2_path = tier2_path
        self.output_path = output_path
        self.bridge = InSynBioKnowledgeBridge()
        self.results = []

    def audit(self):
        if not os.path.exists(self.tier2_path):
            print(f"Error: {self.tier2_path} not found.")
            return

        with open(self.tier2_path, 'r', encoding='utf-8') as f:
            tier2_data = json.load(f)
        
        entries = tier2_data.get("entries", [])
        print(f"[*] Starting deep audit for {len(entries)} Tier 2 entries...")

        for entry in entries:
            name = entry.get("antibody_name")
            if not name or name == "nan": continue
            
            print(f"  > Auditing: {name}...")
            audit_result = {
                "antibody_name": name,
                "original_ai_value": entry.get("ada_value_ai"),
                "pubmed_findings": [],
                "clinical_trials_findings": [],
                "status": "AUDITED"
            }

            # 1. PubMed Cross-Reference
            try:
                query = f'{name} AND (immunogenicity OR "anti-drug antibody" OR ADA)'
                pubmed_results = self.bridge.search_pubmed(query, max_results=3)
                audit_result["pubmed_findings"] = pubmed_results
            except Exception as e:
                print(f"    [PubMed Error] {e}")

            # 2. ClinicalTrials.gov (Simulated via Knowledge Bridge / PDB / General Search)
            # Note: The current bridge focuses on PDB/UniProt/PubMed. 
            # For CT.gov, we use PubMed results that often cite NCT IDs.
            nct_ids = []
            for res in audit_result["pubmed_findings"]:
                if "NCT" in res.get("summary", ""):
                    # Simple extraction logic
                    import re
                    found = re.findall(r"NCT\d{8}", res.get("summary", ""))
                    nct_ids.extend(found)
            
            audit_result["clinical_trials_findings"] = list(set(nct_ids))
            
            # 3. Decision Logic (Upgrade to Tier 1?)
            match_found = False
            for res in audit_result["pubmed_findings"]:
                # Look for percentage matches in summary
                if entry.get("ada_value_ai") and str(entry.get("ada_value_ai")).replace("%","") in res.get("summary", ""):
                    match_found = True
                    audit_result["verification_note"] = f"Match found in PubMed: {res['title']}"
                    break
            
            if match_found:
                audit_result["recommendation"] = "UPGRADE_TO_TIER1"
            else:
                audit_result["recommendation"] = "STAY_IN_TIER2"

            self.results.append(audit_result)
            time.sleep(1) # Rate limiting

        # Save results
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n[SUCCESS] Audit complete. Results saved to {self.output_path}")

if __name__ == "__main__":
    auditor = Tier2Auditor(
        "data/ADA_reliable_package/tiered_db/Tier2_Proprietary.json",
        "data/ADA_reliable_package/tiered_db/Tier2_Audit_Results.json"
    )
    auditor.audit()
