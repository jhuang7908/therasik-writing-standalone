import os
import json
import pandas as pd
from typing import Dict, List, Any

class TherasikDataScanner:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.report = []

    def judge_file(self, file_path: str) -> Dict[str, Any]:
        name = os.path.basename(file_path)
        ext = os.path.splitext(name)[1].lower()
        
        # Default judgments
        useful = "Unknown"
        complete = "Unknown"
        accurate = "Unknown"
        provenance = "None"
        category = "Primary"

        try:
            if ext == ".json":
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Check for secondary product indicators
                if isinstance(data, dict):
                    if "metadata" in data or any(k in str(data.keys()) for k in ["score", "delta", "predicted"]):
                        category = "Secondary (Computational)"
                    if "source" in data.get("metadata", {}):
                        provenance = data["metadata"]["source"]
                
                # Check completeness
                if isinstance(data, list):
                    useful = "High (List of entries)" if len(data) > 0 else "Low"
                    complete = "Yes" if len(data) > 0 and "sequence" in str(data[0]) else "Partial"
                elif isinstance(data, dict):
                    useful = "High (Structured config/db)"
                    complete = "Yes" if "entries" in data or "rules" in data else "Partial"

            elif ext == ".csv":
                df = pd.read_csv(file_path, nrows=5)
                useful = "High (Tabular data)"
                complete = "Yes" if not df.isnull().values.any() else "Partial"
                category = "Primary/Secondary Mix"
                if "uniprot" in df.columns or "pubmed" in df.columns:
                    provenance = "Embedded in columns"

            elif ext == ".pdb":
                useful = "High (Structural basis)"
                category = "Primary (Structure)"
                provenance = "RCSB PDB"

        except Exception as e:
            return {"file": name, "error": str(e)}

        return {
            "file": name,
            "category": category,
            "useful": useful,
            "complete": complete,
            "provenance": provenance
        }

    def scan_directories(self):
        groups = {
            "CAR & Components": ["actes_sequences", "CAR"],
            "Clinical/ADA DBs": ["ADA_reliable_package", "vhh_clinical_39_union"],
            "Atlases (Secondary)": ["adc_atlas", "engineered_459_atlas", "scfv_52_atlas"],
            "Rules & Germlines": ["design_rules", "germlines", "vernier_zones"]
        }

        print("=== Therasik Comprehensive Data Scan ===")
        for group_name, dirs in groups.items():
            print(f"\n--- Group: {group_name} ---")
            for d in dirs:
                dir_path = os.path.join(self.base_dir, d)
                if not os.path.exists(dir_path): continue
                
                # Sample one key file from each
                files = [f for f in os.listdir(dir_path) if f.endswith(('.json', '.csv', '.pdb'))]
                if files:
                    sample_file = files[0]
                    judgment = self.judge_file(os.path.join(dir_path, sample_file))
                    print(f"[*] Directory: {d}")
                    print(f"    - Sample: {judgment['file']}")
                    print(f"    - Type: {judgment['category']}")
                    print(f"    - Useful: {judgment['useful']}")
                    print(f"    - Complete: {judgment['complete']}")
                    print(f"    - Provenance: {judgment['provenance']}")

if __name__ == "__main__":
    scanner = TherasikDataScanner("data")
    scanner.scan_directories()
