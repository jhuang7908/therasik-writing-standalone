import json
import sys
from pathlib import Path
from datetime import datetime

suite_root = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.append(str(suite_root))

from core.evaluation import AbEvaluator, AntibodyType

# 1. Base Sequences
v3_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFSLIGYDLNWVRQAPGKGLQWLGIIWGDGTTDYNSAVKSRVTISKDSAKNTFYLQLQSLRAEETAVYYCARGGYWYATSYYFDYWGQGTSVTVSS"
v3_vl = "EIVLTQSPASLSLSQEEKVTITCRASQSISNNLNWYQQKPGQAPKLLIYYTSRFHSGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQEHTLPYTFGQGTKVELK"

# 2. Create V3b
# Replace WLG with WVA in VH
v3b_vh = v3_vh.replace("GLQWLG", "GLQWVA")

print(f"V3 VH:  {v3_vh}")
print(f"V3b VH: {v3b_vh}")

# 3. CMC Evaluation for V3b
def run_eval(name, vh, vl, ab_type, species):
    print(f"Evaluating {name}...")
    ev = AbEvaluator(
        project_name=name,
        vh_seq=vh,
        vl_seq=vl,
        ab_type=ab_type,
        germline_species=species,
        strict_qa=False
    )
    result = ev.run(modules=["developability", "cdr_scan", "cmc_advisor"])
    return {
        "project_name": result.project_name,
        "results": result.results,
        "overall_status": result.overall_status,
        "overall_flags": result.overall_flags
    }

results = run_eval("V3b", v3b_vh, v3_vl, AntibodyType.DOG, "Canis_lupus_familiaris")

# 4. Save results
with open("v3b_design_results.json", "w") as f:
    json.dump({
        "v3b_vh": v3b_vh,
        "v3b_vl": v3_vl,
        "cmc_results": results
    }, f, indent=2)

print("\nV3b Design and Evaluation complete.")
print(f"V3b VH: {v3b_vh}")
print(f"CMC Status: {results['overall_status']}")
