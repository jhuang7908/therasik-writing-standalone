import json
import os
import pandas as pd
from datetime import datetime

class InSynBioADATierManager:
    """
    Organizes ADA data into a clean, three-tier architecture to ensure 
    data integrity and efficient decision making.
    """
    def __init__(self, base_dir: str):
        self.base_dir = os.path.join(base_dir, "data/ADA_reliable_package/tiered_db")
        os.makedirs(self.base_dir, exist_ok=True)
        self.tier1 = [] # Verified (PMID/FDA)
        self.tier2 = [] # Proprietary (AI/Paid)
        self.tier3 = [] # Untraceable (No info)

    def load_confirmed_xlsx(self, path: str):
        if os.path.exists(path):
            df = pd.read_excel(path, skiprows=1)
            for _, row in df.iterrows():
                entry = {
                    "antibody_name": str(row.get("Antibody Name", "")),
                    "target": str(row.get("Target", "")),
                    "indication": str(row.get("Disease / Indication", "")),
                    "ada_value_verified": str(row.get("ADA Value", "")),
                    "evidence_summary": str(row.get("ADA Evidence Chain Summary", "")),
                    "clinical_context": str(row.get("ADA Clinical Context", "")),
                    "verification_method": str(row.get("Verification Method", "")),
                    "pmid": str(row.get("Reference (PMID / Source)", "")),
                    "url": str(row.get("Citation URL(s)", "")),
                    "tier_label": str(row.get("Tier", "")),
                    "status": "VERIFIED",
                    "last_audit": "2026-04-01",
                    "source": "Confirmed XLSX (80 Entries)"
                }
                if entry["antibody_name"] and entry["antibody_name"] != "nan":
                    if not any(e['antibody_name'].lower() == entry['antibody_name'].lower() for e in self.tier1):
                        self.tier1.append(entry)
            print(f"[*] Integrated {len(self.tier1)} entries into Tier 1")

    def load_need_fulltext_xlsx(self, path: str):
        if os.path.exists(path):
            df = pd.read_excel(path, skiprows=1)
            for _, row in df.iterrows():
                entry = {
                    "antibody_name": str(row.get("Antibody Name", "")),
                    "target": str(row.get("Target", "")),
                    "indication": str(row.get("Disease / Indication", "")),
                    "ada_value_ai": str(row.get("Claimed ADA Value", "")),
                    "evidence_note": str(row.get("Evidence Chain Note", "")),
                    "chain_origin": str(row.get("Chain Origin", "")),
                    "why_manual": str(row.get("Why Manual?", "")),
                    "action_required": str(row.get("Action Required", "")),
                    "reference": str(row.get("Reference (PMID / Source)", "")),
                    "url": str(row.get("Manual Check URL(s)", "")),
                    "status": "PROPRIETARY_UNVERIFIED",
                    "note": "AI-generated value, source requires proprietary access or manual check.",
                    "last_audit": "2026-04-01"
                }
                if entry["antibody_name"] and entry["antibody_name"] != "nan":
                    self.tier2.append(entry)
            print(f"[*] Integrated {len(self.tier2)} entries into Tier 2")

    def organize(self):
        print("=== InSynBio ADA Three-Tier Architecture Implementation ===")
        
        # 1. Load Tier 1
        xlsx_path = "C:/Users/NextVivo/.openclaw/workspace/ADA/confirmed_ada.xlsx"
        self.load_confirmed_xlsx(xlsx_path)

        # 2. Load Tier 2
        need_path = "C:/Users/NextVivo/.openclaw/workspace/ADA/need_fulltext.xlsx"
        self.load_need_fulltext_xlsx(need_path)

        # 3. Tier 3: Untraceable
        self.tier3 = [
            {"antibody_name": "Avelumab", "status": "NO_DATA_FOUND", "last_checked": "2026-03-30"},
            {"antibody_name": "Alirocumab", "status": "NO_DATA_FOUND", "last_checked": "2026-03-30"},
            {"antibody_name": "Amivantamab", "status": "NO_DATA_FOUND", "last_checked": "2026-03-30"}
        ]

        # Save files
        self._save_tier("Tier1_Verified.json", self.tier1, "Evidence-based ADA data with PMID/FDA links.")
        self._save_tier("Tier2_Proprietary.json", self.tier2, "AI-generated values from non-public or paid sources.")
        self._save_tier("Tier3_Untraceable.json", self.tier3, "Antibodies with no traceable ADA info. DO NOT RE-SEARCH.")

    def _save_tier(self, filename, entries, desc):
        path = os.path.join(self.base_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "tier": filename.split('_')[0],
                    "description": desc,
                    "count": len(entries),
                    "last_updated": datetime.now().strftime("%Y-%m-%d")
                },
                "entries": entries
            }, f, indent=2, ensure_ascii=False)
        print(f"[SUCCESS] Saved {filename} ({len(entries)} entries)")

if __name__ == "__main__":
    manager = InSynBioADATierManager("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
    manager.organize()
