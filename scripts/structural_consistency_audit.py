import json
import os
from typing import List, Dict, Any

class TherasikStructuralAuditor:
    """
    Therasik Structural Consistency Auditor.
    Checks for:
    1. Junction Site Integrity: Are domain boundaries (SP, TM, Cyto) physically plausible?
    2. Sequence Motifs: Are there any problematic motifs (e.g., unpaired Cysteines, N-glycosylation in cytoplasmic domains)?
    3. Length Consistency: Do the domain lengths match known biological standards?
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def audit_entry(self, entry: Dict[str, Any]) -> List[str]:
        warnings = []
        seq = entry.get("canonical_sequence", "")
        entry_id = entry.get("entry_id", "")
        desc = entry.get("description", "").lower()
        
        if not seq:
            return ["ERROR: Missing sequence"]

        # 1. Signal Peptide (SP) Audit
        if "sp" in entry_id.lower() or "sig" in entry_id.lower() or "leader" in desc:
            if len(seq) < 15 or len(seq) > 30:
                warnings.append(f"SP length ({len(seq)}) is unusual (standard: 18-25aa)")
            if not any(aa in seq[:5] for aa in "ML"): # Most SPs start with Met or Leu
                warnings.append("SP does not start with standard hydrophobic residues (M/L)")

        # 2. Transmembrane (TM) Audit
        if "tm" in entry_id.lower() or "transmembrane" in desc:
            # TM domains should be hydrophobic
            hydrophobic_count = sum(1 for aa in seq if aa in "AILMFVWY")
            hydro_ratio = hydrophobic_count / len(seq) if len(seq) > 0 else 0
            if hydro_ratio < 0.6:
                warnings.append(f"TM domain has low hydrophobicity ({hydro_ratio:.1%}). Potential boundary error.")
            if len(seq) < 20 or len(seq) > 35:
                warnings.append(f"TM length ({len(seq)}) is unusual for a single-pass helix.")

        # 3. Cytoplasmic (Cyto) Audit
        if "cyto" in entry_id.lower() or "intracellular" in desc:
            if "N" in seq and "S" in seq and "T" in seq: # Simplified N-glycosylation check: N-X-S/T
                # N-glycosylation shouldn't happen in cytoplasm
                for i in range(len(seq) - 2):
                    if seq[i] == 'N' and seq[i+1] != 'P' and (seq[i+2] in 'ST'):
                        warnings.append(f"Potential N-glycosylation site (N{i+1}) found in cytoplasmic domain. Check orientation.")

        # 4. General Integrity: Unpaired Cysteines
        cys_count = seq.count('C')
        if cys_count % 2 != 0:
            # For VHH/scFv this is common if only one chain is present, but for components it might be a risk
            if "scfv" not in entry_id.lower() and "vhh" not in entry_id.lower():
                warnings.append(f"Unpaired Cysteine detected ({cys_count} total). Risk of non-specific disulfide bonding.")

        return warnings

    def run_audit(self):
        print("=== Therasik Structural Consistency Audit ===")
        print(f"Target: {self.db_path}\n")
        
        with open(self.db_path, 'r', encoding='utf-8') as f:
            db = json.load(f)
            
        issues_found = 0
        for entry in db.get("entries", []):
            warnings = self.audit_entry(entry)
            if warnings:
                print(f"[*] {entry['entry_id']} ({entry.get('description', 'No desc')[:40]}...)")
                for w in warnings:
                    print(f"    - {w}")
                issues_found += 1
        
        print(f"\n[DONE] Audit complete. Found issues in {issues_found} entries.")

if __name__ == "__main__":
    auditor = TherasikStructuralAuditor("data/actes_sequences/sequence_db.json")
    auditor.run_audit()
