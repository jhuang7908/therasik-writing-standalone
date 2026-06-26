import os
import json
import pandas as pd
from typing import List, Dict, Any
from core.resources.knowledge_bridge import InSynBioKnowledgeBridge

class InSynBioDataAuditor:
    """
    InSynBio Data Auditor (Therasik Mode).
    Focuses on authenticity and completeness of private databases.
    Skips heavy re-calculation for secondary computational products.
    """
    def __init__(self):
        self.bridge = InSynBioKnowledgeBridge()
        self.data_dir = "data"
        self.results = []

    def is_secondary_product(self, data: Any) -> bool:
        """Heuristic to identify if data is a secondary computational product."""
        if isinstance(data, dict):
            # Check for common computational output keys
            comp_keys = ["delta_delta_g", "energy_score", "docking_rank", "adi_score", "predicted_pI"]
            if any(key in data for key in comp_keys):
                return True
            # Check metadata
            meta = data.get("metadata", {})
            if isinstance(meta, dict) and "generated_by" in meta:
                return True
        return False

    def check_completeness(self, entry: Dict[str, Any]) -> Dict[str, bool]:
        """Check if required fields for clinical/scientific validity are present."""
        required_fields = {
            "sequence": bool(entry.get("sequence")),
            "target": bool(entry.get("target")),
            "provenance": bool(entry.get("uniprot_id") or entry.get("pubmed_id") or entry.get("source_file")),
            "metadata": "design_info" in entry or "metadata" in entry
        }
        return required_fields

    def audit_file(self, file_path: str):
        """Audit a single file for authenticity and completeness."""
        print(f"\n[FILE] {os.path.relpath(file_path, self.data_dir)}")
        
        try:
            if file_path.endswith(".json"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Identify if this is a secondary product file
                is_secondary = self.is_secondary_product(data)
                if is_secondary:
                    print(f"    [TYPE] Secondary Computational Product (Skipping heavy re-calc)")
                else:
                    print(f"    [TYPE] Primary/Source Data")

                # Extract entries
                entries = data.get("entries", []) if isinstance(data, dict) else (data if isinstance(data, list) else [data])
                
                for i, entry in enumerate(entries[:10]): # Limit to first 10 for audit speed
                    if not isinstance(entry, dict): continue
                    
                    name = entry.get("entry_id") or entry.get("name") or f"Entry_{i}"
                    seq = entry.get("canonical_sequence") or entry.get("sequence")
                    target = entry.get("target") or entry.get("description")
                    uniprot_id = entry.get("design_info", {}).get("uniprot_id") if isinstance(entry.get("design_info"), dict) else entry.get("uniprot_id")

                    # 1. Completeness Check
                    comp = self.check_completeness(entry)
                    missing = [k for k, v in comp.items() if not v]
                    if missing:
                        print(f"    [*] {name}: [INCOMPLETE] Missing: {', '.join(missing)}")
                    else:
                        print(f"    [*] {name}: [COMPLETE]")

                    # 2. Authenticity Check (Only for Primary Data or if explicitly requested)
                    if not is_secondary and uniprot_id:
                        print(f"        - Verifying UniProt '{uniprot_id}'...")
                        info = self.bridge.fetch_uniprot_info(uniprot_id)
                        if "error" in info:
                            print(f"        [FAIL] Authenticity check failed: {info['error']}")
                        else:
                            print(f"        [PASS] Authenticity verified: {info['name']}")
                    
                    # 3. Sequence Sanity
                    if seq and "X" in seq:
                        print(f"        [FAIL] Sequence contains unknown residue 'X'")

        except Exception as e:
            print(f"    [ERROR] Failed to audit file: {e}")

    def run_audit(self):
        """Scan data directory and perform audit."""
        print("=== InSynBio Data Authenticity & Completeness Audit ===")
        print("Protocol: Therasik Evidence-Based Validation")
        
        for root, _, files in os.walk(self.data_dir):
            for file in files:
                if file.endswith(".json") or file.endswith(".csv"):
                    file_path = os.path.join(root, file)
                    self.audit_file(file_path)

if __name__ == "__main__":
    auditor = InSynBioDataAuditor()
    auditor.run_audit()
