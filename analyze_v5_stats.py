import json
import sys
from pathlib import Path
from anarci import anarci

suite_root = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.append(str(suite_root))

from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys, is_in_cdr

# 1. Sequences
tanezumab_vh = "QVQLQESGPGLVRPSQTLSLTCTVSGFSLIGYDLNWVRQPPGRGLEWIGIIWGDGTTDYNSAVKSRVTMLKDTSKNQFSLRLSSVTAADTAVYYCARGGYWYATSYYFDYWGQGTLVTVSS"
tanezumab_vl = "DIQMTQSPSSLSASVGDRVTITCRASQSISNNLNWYQQKPGKAPKLLIYYTSRFHSGVPSRFSGSGSGTDFTFTISSLQPEDIATYYCQQEHTLPYTFGQGTKLEIK"

# Dog Scaffolds (The "Shell")
scaffold_vh_full = "EVQLVESGGDLVKPGGSLRLSCVASGFTFSSYGMHWVRQAPGKGLQWVAVISYDGSNKYYADSVKGRFTISRDNAKNTVYLQMNSLRAEDTAMYYCAK"
scaffold_vl_full = "QSVLTQPTSVSGSLGQRVTISCSGSSSNIGNNAVSWYQQLPGKAPKLLVYYDDDLRPSGVPDRFSGSKSGTSASLTITGLQAEDEADYYC"

# V5 Recalculated (from previous step)
v5_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFSLIGYDLNWVRQAPGKGLQWVAIIWGDGTTDYNSAVKSRFTISKDNAKNTFYLQMNSLRAEDTAVYYCAKGGYWYATSYYFDYWGQGTLVTVSS"
v5_vl = "QSVLTQPASSVSGSLGQRVTISCRASQSISNNLNWYQQLPGKAPKLLVDYTSRFHSGVPDRFSGSGSGTSATLTISGLQAEDEADYYQQEHTLPYTFGGGTHLTVL"

def analyze_design(donor_seq, scaffold_seq, v5_seq, chain):
    donor_kd = get_kabat_numbering(donor_seq)
    scaffold_kd = get_kabat_numbering(scaffold_seq)
    v5_kd = get_kabat_numbering(v5_seq)
    
    # Anchors used in design
    anchors = {71, 78} if chain == "VH" else set()
    
    results = {
        "protected_cdr": 0,
        "protected_anchor": 0,
        "fr_total": 0,
        "fr_substituted": 0, # V5 != Scaffold
        "fr_not_substituted": 0, # V5 == Scaffold
        "fr_not_sub_identical_to_donor": 0, # V5 == Scaffold == Donor
        "fr_not_sub_different_from_donor": 0, # V5 == Scaffold != Donor
    }
    
    all_pos = sorted_keys(v5_kd)
    for k in all_pos:
        pos, ins = k
        aa_v5 = v5_kd[k]
        aa_donor = donor_kd.get(k, '-')
        aa_scaf = scaffold_kd.get(k, '-')
        
        if is_in_cdr(pos, chain):
            results["protected_cdr"] += 1
            continue
        
        if pos in anchors:
            results["protected_anchor"] += 1
            continue
            
        # This is an FR position
        results["fr_total"] += 1
        
        if aa_v5 != aa_scaf:
            results["fr_substituted"] += 1
        else:
            results["fr_not_substituted"] += 1
            if aa_v5 == aa_donor:
                results["fr_not_sub_identical_to_donor"] += 1
            else:
                results["fr_not_sub_different_from_donor"] += 1
                
    return results

vh_analysis = analyze_design(tanezumab_vh, scaffold_vh_full, v5_vh, "VH")
vl_analysis = analyze_design(tanezumab_vl, scaffold_vl_full, v5_vl, "VL")

print("VH Analysis:")
print(json.dumps(vh_analysis, indent=2))
print("\nVL Analysis:")
print(json.dumps(vl_analysis, indent=2))
