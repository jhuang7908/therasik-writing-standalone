import json
import sys
from pathlib import Path

# Add suite root to path
suite_root = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.append(str(suite_root))

from core.evaluation import AbEvaluator, AntibodyType

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

# V3 Original
v3_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFSLIGYDLNWVRQAPGKGLQWLGIIWGDGTTDYNSAVKSRVTISKDSAKNTFYLQLQSLRAEETAVYYCARGGYWYATSYYFDYWGQGTSVTVSS"
v3_vl = "EIVLTQSPASLSLSQEEKVTITCRASQSISNNLNWYQQKPGQAPKLLIYYTSRFHSGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQEHTLPYTFGQGTKVELK"

# V3 Optimized (Smart-CMC)
# VH: S73A (removes DS risk at 72-73)
# ...RVTISKDSA... -> ...RVTISKDAA...
v3_opt_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFSLIGYDLNWVRQAPGKGLQWLGIIWGDGTTDYNSAVKSRVTISKDSAKNTFYLQLQSLRAEETAVYYCARGGYWYATSYYFDYWGQGTSVTVSS".replace("RVTISKDSA", "RVTISKDAA")

# VL: E79Q, E81Q (raises pI)
# ...TISSLEPEDV... -> ...TISSLQPQDV...
# Let's check sequence: ...TISSLEPEDV...
# 76: S, 77: S, 78: L, 79: E, 80: P, 81: E, 82: D, 83: V
v3_opt_vl = "EIVLTQSPASLSLSQEEKVTITCRASQSISNNLNWYQQKPGQAPKLLIYYTSRFHSGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQEHTLPYTFGQGTKVELK".replace("TISSLEPEDV", "TISSLQPQDV")

results = {}
results["V3_Original"] = run_eval("V3_Original", v3_vh, v3_vl, AntibodyType.DOG, "Canis_lupus_familiaris")
results["V3_Optimized"] = run_eval("V3_Optimized", v3_opt_vh, v3_opt_vl, AntibodyType.DOG, "Canis_lupus_familiaris")

with open("v3_opt_comparison.json", "w") as f:
    json.dump(results, f, indent=2)

print("V3 optimization evaluation complete.")
