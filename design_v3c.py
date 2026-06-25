"""Design V3c (DeepFR-CTX on V3b/Kappa scaffold) from Tanezumab donor."""
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

tanezumab_vh = "QVQLQESGPGLVRPSQTLSLTCTVSGFSLIGYDLNWVRQPPGRGLEWIGIIWGDGTTDYNSAVKSRVTMLKDTSKNQFSLRLSSVTAADTAVYYCARGGYWYATSYYFDYWGQGTLVTVSS"
tanezumab_vl = "DIQMTQSPSSLSASVGDRVTITCRASQSISNNLNWYQQKPGKAPKLLIYYTSRFHSGVPSRFSGSGSGTDFTFTISSLQPEDIATYYCQQEHTLPYTFGQGTKLEIK"

# V3b scaffolds: IGHV3-9*01 / IGKV3-18*02
scaffold_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFTFSSYGMHWVRQAPGKGLQWVAVISYDGSNKYYADAVKGRFTISKDSAKNTLYLQMNSLRAEDTAVYYCAR"
scaffold_vl = "EIVLTQSPASLSLSQEEKVTITCRASQSIGSSLNWYQQKPGQAPKLLIYYATSRLHSGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQGYS"

print("Designing V3c VH (DeepFR-CTX-Pet)...")
v3c_vh_body, vh_changes, _vh_meta = design_deepfr_ctx_chain(
    tanezumab_vh, scaffold_vh, "VH", anchors={}
)
v3c_vh = v3c_vh_body + DOG_FR4["VH"]

print("Designing V3c VL (DeepFR-CTX-Pet)...")
v3c_vl_body, vl_changes, _vl_meta = design_deepfr_ctx_chain(
    tanezumab_vl, scaffold_vl, "VL", anchors={}
)
v3c_vl = v3c_vl_body + DOG_FR4["VL_KAPPA"]

print(f"VH changes: {len(vh_changes)}, VL changes: {len(vl_changes)}")

for chain, seq in [("VH", v3c_vh), ("VL", v3c_vl)]:
    errs = validate_conserved_cys(seq, chain)
    if errs:
        raise SystemExit(f"FATAL: {chain} Cys validation failed: {errs}")
    print(f"{chain} Cys validation: PASS")

ev = AbEvaluator(
    project_name="V3c_Recalculated",
    vh_seq=v3c_vh,
    vl_seq=v3c_vl,
    ab_type=AntibodyType.DOG,
    germline_species="Canis_lupus_familiaris",
    strict_qa=False,
)
result = ev.run(modules=["developability", "cdr_scan", "cmc_advisor"])

output = {
    "variant": "V3c",
    "vh": v3c_vh,
    "vl": v3c_vl,
    "vh_changes": vh_changes,
    "vl_changes": vl_changes,
    "cmc": {
        "pI": result.results["developability"]["pI_fab_estimate"],
        "instability": result.results["developability"]["instability_index"],
        "status": result.overall_status,
    },
}

with open("v3c_design_results.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print("\nV3c VH:", v3c_vh)
print("V3c VL:", v3c_vl)
print("CMC status:", result.overall_status)
