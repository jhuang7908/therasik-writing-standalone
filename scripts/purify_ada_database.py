import json
import os
import pandas as pd
from datetime import datetime

class InSynBioADAPurifier:
    """
    Purifies the ADA database by merging verified sources and isolating deceptive/unverified entries.
    """
    def __init__(self, base_dir: str, external_workspace: str):
        self.base_dir = base_dir
        self.external_workspace = external_workspace
        self.master_entries = []
        self.blacklisted_entries = []
        self.pending_entries = []

    def load_verified_json(self, path: str):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                entries = data.get("entries", [])
                for entry in entries:
                    entry["status"] = "VERIFIED"
                    entry["last_audit"] = "2026-04-01"
                    self.master_entries.append(entry)
            print(f"[*] Loaded {len(entries)} verified entries from {os.path.basename(path)}")

    def load_verified_xlsx(self, path: str):
        if os.path.exists(path):
            df = pd.read_excel(path)
            # Standardize columns for master DB
            for _, row in df.iterrows():
                entry = {
                    "antibody_name": str(row.get("Antibody Name", row.get("antibody_name", ""))),
                    "ada_value_verified": str(row.get("ADA Value", row.get("ada_value", ""))),
                    "pmid": str(row.get("Evidence (PMID/NCT)", row.get("pmid", ""))),
                    "status": "VERIFIED",
                    "last_audit": "2026-04-01",
                    "source": "Confirmed XLSX"
                }
                if entry["antibody_name"] and entry["ada_value_verified"] != "nan":
                    self.master_entries.append(entry)
            print(f"[*] Loaded entries from {os.path.basename(path)}")

    def run_purification(self):
        print("=== InSynBio ADA Database Purification ===")
        
        # 1. Load the 'Gold Standard' verified files
        rehab_path = os.path.join(self.base_dir, "data/ADA_reliable_package/verification/rehabilitated_entries.json")
        self.load_verified_json(rehab_path)
        
        confirmed_xlsx = os.path.join(self.external_workspace, "confirmed_ada.xlsx")
        self.load_verified_xlsx(confirmed_xlsx)

        # 2. Define known deceptive entries to blacklist
        deceptive_names = ["Atoltivimab", "Depemokimab", "Axatilimab"]
        for name in deceptive_names:
            self.blacklisted_entries.append({
                "antibody_name": name,
                "reason": "Deceptive: AI misidentified viral inhibition or statistical CI as ADA rate.",
                "status": "BLACKLISTED",
                "audit_date": "2026-04-01"
            })

        # 3. Save the Master Source of Truth
        master_path = os.path.join(self.base_dir, "data/ADA_reliable_package/InSynBio_ADA_Master_v1.0.json")
        with open(master_path, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "version": "1.0",
                    "description": "Sole source of truth for verified ADA data. All entries have confirmed evidence chains.",
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "entries": self.master_entries
            }, f, indent=2, ensure_ascii=False)
        
        # 4. Save the Blacklist
        blacklist_path = os.path.join(self.base_dir, "data/ADA_reliable_package/blacklisted_ada.json")
        with open(blacklist_path, 'w', encoding='utf-8') as f:
            json.dump(self.blacklisted_entries, f, indent=2, ensure_ascii=False)

        print(f"\n[SUCCESS] Created Master DB: {master_path} ({len(self.master_entries)} entries)")
        print(f"[SUCCESS] Created Blacklist: {blacklist_path} ({len(self.blacklisted_entries)} entries)")

if __name__ == "__main__":
    purifier = InSynBioADAPurifier(
        "D:/InSynBio-AI-Research/Antibody_Engineer_Suite",
        "C:/Users/NextVivo/.openclaw/workspace/ADA"
    )
    purifier.run_purification()
