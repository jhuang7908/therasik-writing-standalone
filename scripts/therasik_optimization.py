import json
import os

class TherasikOptimizer:
    """
    Therasik Sequence Optimizer.
    Creates optimized variants of biological components (e.g., C->S mutations for stability).
    Ensures optimized variants have unique names.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path

    def optimize_sequence(self, seq: str) -> str:
        """Perform C->S mutation for all Cysteines to ensure stability."""
        return seq.replace('C', 'S')

    def run_optimization(self):
        print("=== Therasik Sequence Optimization (Stability Focus) ===")
        
        with open(self.db_path, 'r', encoding='utf-8') as f:
            db = json.load(f)
            
        new_entries = []
        target_ids = ["4-1BB_cyto", "IL2_SP", "GM-CSF_SP", "T2A", "P2A"]
        
        for entry in db.get("entries", []):
            if entry["entry_id"] in target_ids:
                orig_seq = entry.get("canonical_sequence", "")
                if not orig_seq: continue
                
                cys_count = orig_seq.count('C')
                if cys_count > 0:
                    opt_seq = self.optimize_sequence(orig_seq)
                    opt_entry = entry.copy()
                    
                    # Rename with Therasik suffix
                    opt_entry["entry_id"] = f"{entry['entry_id']}_Opt"
                    opt_entry["canonical_sequence"] = opt_seq
                    opt_entry["description"] = f"Therasik Optimized (C->S for stability): {entry.get('description', '')}"
                    
                    # Remove UniProt ID from design_info as it's now a synthetic variant
                    if "design_info" in opt_entry:
                        opt_entry["design_info"]["note"] = f"Derived from {entry['design_info'].get('uniprot_id')} with C->S mutations."
                        # Keep UniProt ID for reference but mark as variant
                        opt_entry["design_info"]["variant_of"] = opt_entry["design_info"].pop("uniprot_id", None)
                    
                    new_entries.append(opt_entry)
                    print(f"[+] Created optimized variant: {opt_entry['entry_id']}")
                    print(f"    Original: {orig_seq}")
                    print(f"    Optimized: {opt_seq}")

        if new_entries:
            # Check if they already exist to avoid duplicates
            existing_ids = {e["entry_id"] for e in db["entries"]}
            added_count = 0
            for ne in new_entries:
                if ne["entry_id"] not in existing_ids:
                    db["entries"].append(ne)
                    added_count += 1
            
            if added_count > 0:
                db["metadata"]["generated"] = "2026-04-02 (Therasik Optimized)"
                with open(self.db_path, 'w', encoding='utf-8') as f:
                    json.dump(db, f, indent=2, ensure_ascii=False)
                print(f"\n[DONE] Added {added_count} optimized variants to {self.db_path}")
            else:
                print("\n[INFO] Optimized variants already exist in database.")
        else:
            print("\n[INFO] No targets found for optimization.")

if __name__ == "__main__":
    optimizer = TherasikOptimizer("data/actes_sequences/sequence_db.json")
    optimizer.run_optimization()
