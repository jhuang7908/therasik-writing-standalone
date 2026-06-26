import pandas as pd
import os
import json
from typing import Dict, List, Any

class TherasikProvenanceAuditor:
    """
    Audits the alignment between the local processed databases and the 
    master TheraSAbDab source file to ensure authenticity and traceability.
    """
    def __init__(self, master_xlsx: str, data_dir: str):
        self.master_xlsx = master_xlsx
        self.data_dir = data_dir
        self.master_df = None

    def load_master(self):
        print(f"[*] Loading Master Source: {os.path.basename(self.master_xlsx)}")
        # TheraSAbDab usually has columns like 'Antibody Name', 'Target', 'Sequence', etc.
        self.master_df = pd.read_excel(self.master_xlsx)
        print(f"    - Total Master Entries: {len(self.master_df)}")

    def audit_local_db(self, local_file: str, id_column: str):
        """Cross-checks a local CSV/JSON against the master source."""
        print(f"\n[AUDIT] Checking local DB: {os.path.relpath(local_file, self.data_dir)}")
        
        try:
            if local_file.endswith('.csv'):
                local_df = pd.read_csv(local_file)
            elif local_file.endswith('.json'):
                with open(local_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Handle InSynBio standard JSON structure
                    entries = data.get("entries", []) if isinstance(data, dict) else data
                    local_df = pd.DataFrame(entries)
            else:
                return

            if id_column not in local_df.columns:
                print(f"    [FAIL] ID column '{id_column}' not found in local DB.")
                return

            # Check how many IDs exist in master
            local_ids = local_df[id_column].unique()
            # Assuming master has 'Antibody Name' or similar. Adjusting to common TheraSAbDab headers.
            master_names = self.master_df.iloc[:, 0].astype(str).tolist() # Usually the first column
            
            matched = [idx for idx in local_ids if str(idx) in master_names]
            match_rate = len(matched) / len(local_ids) if len(local_ids) > 0 else 0
            
            print(f"    - Match Rate with Master: {match_rate:.1%} ({len(matched)}/{len(local_ids)})")
            if match_rate < 0.9:
                print(f"    [WARN] Low alignment. Contains {len(local_ids) - len(matched)} entries not in master (Secondary/Custom?).")
            else:
                print(f"    [PASS] High provenance integrity.")

        except Exception as e:
            print(f"    [ERROR] Audit failed: {e}")

    def run(self):
        self.load_master()
        # Audit key local databases
        targets = [
            ("data/vhh_clinical_39_union/vhh_39_sequences_clinical.csv", "Name"),
            ("data/scfv_52_atlas/master_table.csv", "Name"),
            ("data/ADA_reliable_package/curated/ada_curated_tier_A.json", "entry_id")
        ]
        
        for path, col in targets:
            full_path = os.path.join("D:/InSynBio-AI-Research/Antibody_Engineer_Suite", path)
            if os.path.exists(full_path):
                self.audit_local_db(full_path, col)

if __name__ == "__main__":
    master = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/data/thera_sabdab/TheraSAbDab_SeqStruc_OnlineDownload.xlsx"
    auditor = TherasikProvenanceAuditor(master, "data")
    auditor.run()
