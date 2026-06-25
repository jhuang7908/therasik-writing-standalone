"""Recalculate V4b (DeepFR-CTX on V4/Lambda scaffold) from Tanezumab donor."""
import json
import sys
from pathlib import Path

suite_root = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.append(str(suite_root))

from core.evaluation import AbEvaluator, AntibodyType
from core.humanization.deepfr_ctx_pet import (
    DOG_FR4,
    design_deepfr_ctx_chain,
    validate_conserved_cys,
)

# Tanezumab donor
tanezumab_vh = "QVQLQESGPGLVRPSQTLSLTCTVSGFSLIGYDLNWVRQPPGRGLEWIGIIWGDGTTDYNSAVKSRVTMLKDTSKNQFSLRLSSVTAADTAVYYCARGGYWYATSYYFDYWGQGTLVTVSS"
tanezumab_vl = "DIQMTQSPSSLSASVGDRVTITCRASQSISNNLNWYQQKPGKAPKLLIYYTSRFHSGVPSRFSGSGSGTDFTFTISSLQPEDIATYYCQQEHTLPYTFGQGTKLEIK"

# Dog scaffolds: IGHV3-19*01 / IGLV1-141*01
scaffold_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFTFSSYGMHWVRQAPGKGLQWVAVISYDGSNKYYADSVKGRFTISRDNAKNTVYLQMNSLRAEDTAMYYCAK"
scaffold_vl = "QSVLTQPTSVSGSLGQRVTISCSGSSSNIGNNAVSWYQQLPGKAPKLLVYYDDDLRPSGVPDRFSGSKSGTSASLTITGLQAEDEADYYC"

vh_anchors = {71: "K", 78: "F"}

print("Designing V4b VH (DeepFR-CTX-Pet)...")
v4b_vh_body, vh_changes, _vh_meta = design_deepfr_ctx_chain(
    tanezumab_vh, scaffold_vh, "VH", anchors=vh_anchors
)
v4b_vh = v4b_vh_body + DOG_FR4["VH"]

print("Designing V4b VL (DeepFR-CTX-Pet)...")
v4b_vl_body, vl_changes, _vl_meta = design_deepfr_ctx_chain(
    tanezumab_vl, scaffold_vl, "VL", anchors={}
)
v4b_vl = v4b_vl_body + DOG_FR4["VL_LAMBDA"]

print(f"VH changes: {len(vh_changes)}, VL changes: {len(vl_changes)}")

for chain, seq in [("VH", v4b_vh), ("VL", v4b_vl)]:
    errs = validate_conserved_cys(seq, chain)
    if errs:
        raise SystemExit(f"FATAL: {chain} Cys validation failed: {errs}")
    print(f"{chain} Cys validation: PASS")

ev = AbEvaluator(
    project_name="V4b_Recalculated",
    vh_seq=v4b_vh,
    vl_seq=v4b_vl,
    ab_type=AntibodyType.DOG,
    germline_species="Canis_lupus_familiaris",
    strict_qa=False,
)
result = ev.run(modules=["developability", "cdr_scan", "cmc_advisor"])

output = {
    "variant": "V4b",
    "vh": v4b_vh,
    "vl": v4b_vl,
    "vh_changes": vh_changes,
    "vl_changes": vl_changes,
    "cmc": {
        "pI": result.results["developability"]["pI_fab_estimate"],
        "instability": result.results["developability"]["instability_index"],
        "status": result.overall_status,
    },
}

with open("v4b_design_results.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print("\nV4b VH:", v4b_vh)
print("V4b VL:", v4b_vl)
print("CMC status:", result.overall_status)
