import json
import os
import requests
from core.resources.knowledge_bridge import InSynBioKnowledgeBridge

class InSynBioDbCompleter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.bridge = InSynBioKnowledgeBridge()
        self.uniprot_cache = {}

    def fetch_full_sequence(self, uniprot_id):
        """Fetch full protein sequence from UniProt."""
        if uniprot_id in self.uniprot_cache:
            return self.uniprot_cache[uniprot_id]
        
        try:
            print(f"[*] Fetching sequence for {uniprot_id}...")
            url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.fasta"
            response = requests.get(url)
            response.raise_for_status()
            lines = response.text.splitlines()
            sequence = "".join(lines[1:])
            self.uniprot_cache[uniprot_id] = sequence
            return sequence
        except Exception as e:
            print(f"    [FAIL] Could not fetch {uniprot_id}: {e}")
            return None

    def complete_db(self):
        with open(self.file_path, 'r', encoding='utf-8') as f:
            db = json.load(f)

        updated_count = 0
        for entry in db.get("entries", []):
            entry_id = entry.get("entry_id")
            design_info = entry.get("design_info", {})
            uniprot_id = design_info.get("uniprot_id") if isinstance(design_info, dict) else None
            
            # Special case for entries that mention UniProt ID in description but lack design_info
            if not uniprot_id and "fetch" in entry.get("description", "").lower():
                import re
                match = re.search(r'[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}', entry["description"])
                if match:
                    uniprot_id = match.group(0)
                    if not isinstance(entry.get("design_info"), dict):
                        entry["design_info"] = {}
                    entry["design_info"]["uniprot_id"] = uniprot_id
                    print(f"[*] Identified UniProt ID {uniprot_id} for {entry_id}")

            if uniprot_id:
                # 1. Fetch sequence if missing
                if not entry.get("canonical_sequence"):
                    full_seq = self.fetch_full_sequence(uniprot_id)
                    if full_seq:
                        res_range = design_info.get("residue_range")
                        if res_range and len(res_range) == 2:
                            start, end = res_range
                            # UniProt is 1-indexed
                            sub_seq = full_seq[start-1:end]
                            entry["canonical_sequence"] = sub_seq
                            print(f"    [PASS] Completed sequence for {entry_id} (Range: {start}-{end})")
                            updated_count += 1
                        else:
                            entry["canonical_sequence"] = full_seq
                            print(f"    [PASS] Completed full sequence for {entry_id}")
                            updated_count += 1

                # 2. Enhance description if UniProt data is available
                if "needs fetch" in entry.get("description", "").lower() or not entry.get("description"):
                    info = self.bridge.fetch_uniprot_info(uniprot_id)
                    if not "error" in info:
                        entry["description"] = f"{info['name']} ({info['organism']})"
                        print(f"    [PASS] Updated description for {entry_id}")
                        updated_count += 1

        if updated_count > 0:
            db["metadata"]["generated"] = "2026-04-02 (Auto-Completed)"
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(db, f, indent=2, ensure_ascii=False)
            print(f"\n[DONE] Successfully updated {updated_count} fields in {self.file_path}")
        else:
            print("\n[INFO] No updates needed.")

if __name__ == "__main__":
    path = "data/actes_sequences/sequence_db.json"
    completer = InSynBioDbCompleter(path)
    completer.complete_db()
