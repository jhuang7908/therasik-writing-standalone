import json
import os
import pandas as pd
from datetime import datetime

class InSynBioADAFullMigrator:
    """
    Migrates the entire 168-antibody dataset into the Three-Tier Architecture.
    """
    def __init__(self, base_dir: str, external_workspace: str):
        self.base_dir = base_dir
        self.external_workspace = external_workspace
        self.tier_dir = os.path.join(base_dir, "data/ADA_reliable_package/tiered_db")
        os.makedirs(self.tier_dir, exist_ok=True)
        
        self.tier1 = []
        self.tier2 = []
        self.tier3 = []
        
        # Load existing verified list to ensure no regression
        self.verified_names = set()

    def load_verified_base(self):
        master_path = os.path.join(self.base_dir, "data/ADA_reliable_package/InSynBio_ADA_Master_v1.0.json")
        if os.path.exists(master_path):
            with open(master_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.tier1 = data.get("entries", [])
                self.verified_names = {e['antibody_name'] for e in self.tier1}
        print(f"[*] Base Tier 1 loaded: {len(self.tier1)} entries.")

    def migrate_from_report(self, report_path: str):
        """
        Parses the 168-antibody MD report and categorizes entries.
        """
        print(f"[*] Migrating from report: {os.path.basename(report_path)}")
        
        # We'll use the logic from the report analysis
        # Tier 1: Has PMID/FDA and marked ''
        # Tier 2: Has values but marked '' or ''
        # Tier 3: Marked '❌ ' for ADA value
        
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            table_started = False
            for line in lines:
                if '| Antibody Name |' in line:
                    table_started = True
                    continue
                if table_started and '|' in line and '---' not in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) < 6: continue
                    
                    name = parts[1]
                    value = parts[2]
                    source = parts[3]
                    evidence = parts[4]
                    completeness = parts[5]
                    
                    if name in self.verified_names:
                        continue # Already in Tier 1
                    
                    entry = {
                        "antibody_name": name,
                        "ada_value": value,
                        "source": source,
                        "evidence": evidence,
                        "completeness": completeness,
                        "migration_date": "2026-04-01"
                    }
                    
                    if "❌ " in value:
                        self.tier3.append(entry)
                    elif "" in completeness:
                        # Double check if it has PMID
                        if "PMID" in evidence or "FDA" in source:
                            entry["status"] = "VERIFIED"
                            self.tier1.append(entry)
                        else:
                            self.tier2.append(entry)
                    else:
                        # Value exists but evidence is missing -> Tier 2
                        self.tier2.append(entry)
                        
        except Exception as e:
            print(f"[ERROR] Migration failed: {e}")

    def save_tiers(self):
        def save(filename, data, desc):
            path = os.path.join(self.tier_dir, filename)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({
                    "metadata": {
                        "description": desc,
                        "count": len(data),
                        "last_updated": datetime.now().strftime("%Y-%m-%d")
                    },
                    "entries": data
                }, f, indent=2, ensure_ascii=False)
            print(f"[SUCCESS] {filename}: {len(data)} entries.")

        save("Tier1_Verified.json", self.tier1, "Verified ADA data with evidence chains.")
        save("Tier2_Proprietary.json", self.tier2, "AI-generated or proprietary ADA data (Unverified).")
        save("Tier3_Untraceable.json", self.tier3, "Antibodies with no found ADA data. DO NOT RE-SEARCH.")

if __name__ == "__main__":
    migrator = InSynBioADAFullMigrator(
        "D:/InSynBio-AI-Research/Antibody_Engineer_Suite",
        "C:/Users/NextVivo/.openclaw/workspace/ADA"
    )
    migrator.load_verified_base()
    report = "C:/Users/NextVivo/.openclaw/workspace/ADA/ada_antibody_168_complete_report_with_analysis_20260330.md"
    migrator.migrate_from_report(report)
    migrator.save_tiers()
