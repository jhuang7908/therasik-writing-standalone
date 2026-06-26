import os
import json
import pandas as pd
from typing import List, Dict, Any
from core.resources.knowledge_bridge import InSynBioKnowledgeBridge

class InSynBioPrivateAudit:
    """
    Audits private database files in the data/ directory for consistency and errors
    using the Knowledge Bridge (UniProt, PubMed, PDB).
    """
    def __init__(self):
        self.bridge = InSynBioKnowledgeBridge()
        self.data_dir = "data"

    def scan_json_for_sequences(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract sequences and metadata from JSON files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Support InSynBio sequence_db.json format
            entries_list = data.get("entries", []) if isinstance(data, dict) else data
            if not isinstance(entries_list, list):
                entries_list = [data]

            found = []
            for item in entries_list:
                if isinstance(item, dict):
                    seq = item.get("canonical_sequence") or item.get("sequence") or item.get("vh_sequence") or item.get("vhh_sequence")
                    name = item.get("entry_id") or item.get("name") or item.get("id") or item.get("antibody_name")
                    target = item.get("target") or item.get("antigen") or item.get("description")
                    uniprot_id = item.get("design_info", {}).get("uniprot_id") if isinstance(item.get("design_info"), dict) else None
                    
                    if seq:
                        found.append({
                            "name": name, 
                            "sequence": seq, 
                            "target": target, 
                            "uniprot_id": uniprot_id,
                            "source_file": file_path
                        })
            return found
        except Exception as e:
            print(f"[!] Error scanning {file_path}: {e}")
            return []

    def audit_sequence(self, entry: Dict[str, Any]):
        """Perform BioChatter-style audit on a single sequence entry."""
        print(f"\n[*] Auditing: {entry['name']} (Source: {os.path.basename(entry['source_file'])})")
        
        # 1. UniProt ID Verification
        if entry.get('uniprot_id'):
            print(f"    - Verifying UniProt ID '{entry['uniprot_id']}'...")
            info = self.bridge.fetch_uniprot_info(entry['uniprot_id'])
            if "error" in info:
                print(f"    [FAIL] UniProt ID '{entry['uniprot_id']}' is invalid or inaccessible.")
            else:
                print(f"    [PASS] UniProt Match: {info['name']} ({info['organism']})")

        # 2. Target/Description Validation
        elif entry['target']:
            print(f"    - Checking description/target '{entry['target'][:30]}...' in PDB...")
            pdb_hits = self.bridge.find_pdb_structures(entry['target'][:20], limit=1)
            if not pdb_hits or "error" in pdb_hits[0]:
                print(f"    [WARN] No direct PDB match for target description.")
            else:
                print(f"    [PASS] Found related PDB: {pdb_hits[0]['pdb_id']}")

        # 3. Sequence Integrity
        seq = entry['sequence']
        if "X" in seq:
            print(f"    [FAIL] Sequence contains unknown residue 'X'.")
        
        # 4. Provenance / Literature Check
        if "CD8" in str(entry['name']) or "CD28" in str(entry['name']):
            # Skip common components to avoid PubMed noise
            pass
        elif entry['name']:
            pubmed_hits = self.bridge.search_pubmed(f"{entry['name']} antibody", max_results=1)
            if pubmed_hits and "title" in pubmed_hits[0]:
                print(f"    [INFO] Literature match: '{pubmed_hits[0]['title']}'.")

    def run_full_audit(self, limit_files: int = 5):
        """Scan data directory and audit found sequences."""
        print("=== InSynBio Private Database Audit ===")
        files_scanned = 0
        for root, _, files in os.walk(self.data_dir):
            for file in files:
                if file.endswith(".json"):
                    file_path = os.path.join(root, file)
                    entries = self.scan_json_for_sequences(file_path)
                    for entry in entries:
                        self.audit_sequence(entry)
                    files_scanned += 1
                    if files_scanned >= limit_files:
                        break
            if files_scanned >= limit_files:
                break

if __name__ == "__main__":
    auditor = InSynBioPrivateAudit()
    auditor.run_full_audit(limit_files=2)
