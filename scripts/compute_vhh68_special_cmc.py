#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/compute_vhh68_special_cmc.py
======================================
Computes the VHH-Specific Minimum Recommended Panel (Computational) for the 39+29 VHH structural union cohort.

Metrics computed:
[VHH-specific]
- FR2 hallmark/tetrad (Kabat 37, 44, 45, 47)
- CDR3 length
- CDR3 compactness (Ca distance between CDR3 start and end from PDB)
- noncanonical Cys/disulfide risk
- AbNatiV-VHH (placeholder/mock as it requires external tool)
- exposed FR2 hydrophobicity (GRAVY of FR2)

[General]
- pI
- SAP/hydrophobic patch (sequence proxy)
- charge patch (max7)
- GRAVY
- Instability index
- liability motifs
"""

import json
import math
import sys
from pathlib import Path
from typing import Dict, Any, List

try:
    import Bio.PDB
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.humanization.kabat_utils import get_kabat_numbering, cdr_span, sorted_keys
from core.cmc.cmc_metrics import (
    compute_pI, compute_GRAVY, compute_instability_index,
    compute_hydro_patch_max9, compute_charge_patch_max7,
    compute_chemical_liabilities
)
from core.cmc.vhh_cmc_engine import _sap_proxy

SUITE_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = SUITE_ROOT / "data" / "vhh_structural_union" / "vhh_structural_union_index.json"
OUT_PATH = SUITE_ROOT / "data" / "vhh_structural_union" / "vhh68_special_cmc_results.json"

def calc_cdr3_compactness(pdb_path: Path, seq: str) -> float:
    """Calculate CA distance between first and last residue of CDR3."""
    if not pdb_path or not pdb_path.exists():
        return None
    try:
        kabat = get_kabat_numbering(seq)
        cdr3_span = cdr_span(kabat, 95, 102)
        if not cdr3_span:
            return None
        
        # PDB residues might not match Kabat exactly, 
        # but in ImmuneBuilder models they often match linear sequence.
        # We will use linear indices:
        # get_kabat_numbering returns dict of (pos, ins) -> aa.
        # Let's find the linear index of CDR3 start and end.
        s_keys = sorted_keys(kabat)
        start_key = None
        end_key = None
        for k in s_keys:
            if k[0] >= 95 and start_key is None:
                start_key = k
            if k[0] <= 102:
                end_key = k
                
        if start_key is None or end_key is None:
            return None
            
        start_idx = s_keys.index(start_key)
        end_idx = s_keys.index(end_key)
        
        parser = Bio.PDB.PDBParser(QUIET=True)
        struct = parser.get_structure("model", str(pdb_path))
        residues = list(struct.get_residues())
        
        # HETATM filtering
        residues = [r for r in residues if r.id[0] == ' ']
        
        if start_idx < len(residues) and end_idx < len(residues):
            r_start = residues[start_idx]
            r_end = residues[end_idx]
            if 'CA' in r_start and 'CA' in r_end:
                dist = r_start['CA'] - r_end['CA']
                return round(float(dist), 2)
        return None
    except Exception as e:
        return None

def process_vhh(item: Dict[str, Any], anarcii_engine) -> Dict[str, Any]:
    seq = item.get("sequence", "").upper()
    if not seq:
        return item
        
    kabat = get_kabat_numbering(seq, anarcii_engine)
    
    # 1. FR2 hallmark (37, 44, 45, 47)
    # VHH typical: 37F/Y, 44E/Q, 45R/C, 47G/F/L
    h37 = kabat.get((37, ""), "-")
    h44 = kabat.get((44, ""), "-")
    h45 = kabat.get((45, ""), "-")
    h47 = kabat.get((47, ""), "-")
    tetrad = f"{h37}{h44}{h45}{h47}"
    
    # 2. CDR3 length
    cdr3_seq = cdr_span(kabat, 95, 102)
    cdr3_len = len(cdr3_seq)
    
    # 3. CDR3 compactness
    pdb_rel = item.get("pdb_model")
    pdb_path = SUITE_ROOT / pdb_rel if pdb_rel else None
    compactness = calc_cdr3_compactness(pdb_path, seq)
    
    # 4. noncanonical Cys
    cys_count = seq.count('C')
    # Kabat 22 and 92 are standard. 
    # VHH often has extra Cys at 33/50 or 50/100 or 45/100
    has_noncanonical_cys = cys_count > 2
    
    # 6. exposed FR2 hydrophobicity
    fr2_seq = cdr_span(kabat, 36, 49)
    fr2_hydrophobicity = compute_GRAVY(fr2_seq) if fr2_seq else None
    
    # General metrics
    liab = compute_chemical_liabilities(seq, vh_len=len(seq))
    total_liab = (
        len(liab.get("glycosylation_sites", [])) +
        len(liab.get("deamidation_sites", [])) +
        len(liab.get("isomerization_sites", [])) +
        len(liab.get("oxidation_sites", []))
    )
    
    return {
        "id": item.get("id"),
        "source_set": item.get("source_set"),
        "vhh_specific": {
            "fr2_hallmark_tetrad": tetrad,
            "cdr3_length": cdr3_len,
            "cdr3_compactness_ca_dist": compactness,
            "noncanonical_cys_risk": has_noncanonical_cys,
            "cys_count": cys_count,
            "abnativ_vhh_score": "NA (Requires External Model)",
            "exposed_fr2_hydrophobicity": fr2_hydrophobicity
        },
        "general": {
            "pI": compute_pI(seq),
            "SAP_proxy": _sap_proxy(seq),
            "hydro_patch_max9": compute_hydro_patch_max9(seq),
            "charge_patch_max7": compute_charge_patch_max7(seq),
            "GRAVY": compute_GRAVY(seq),
            "instability_index": compute_instability_index(seq),
            "liability_motifs_count": total_liab
        }
    }

def main():
    if not INDEX_PATH.exists():
        print(f"Error: Could not find {INDEX_PATH}")
        sys.exit(1)
        
    data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    clinical = data.get("clinical_vhh", [])
    db_b = data.get("database_b", [])
    
    all_vhh = clinical + db_b
    print(f"Loaded {len(all_vhh)} VHHs from index.")
    
    results = []
    from anarcii import Anarcii
    anarcii_engine = Anarcii()
    
    for idx, item in enumerate(all_vhh):
        res = process_vhh(item, anarcii_engine)
        results.append(res)
        if (idx + 1) % 10 == 0:
            print(f"Processed {idx + 1}/{len(all_vhh)}...", flush=True)
            
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nDone! Results saved to {OUT_PATH}")

if __name__ == "__main__":
    main()
