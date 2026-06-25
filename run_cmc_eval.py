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
    # Run developability and cdr_scan (sequence-only)
    # Also run cmc_advisor for optimization suggestions
    result = ev.run(modules=["developability", "cdr_scan", "cmc_advisor", "germline"])
    
    # Manually convert to dict
    return {
        "project_name": result.project_name,
        "ab_type": str(result.ab_type),
        "modules_run": result.modules_run,
        "results": result.results,
        "overall_flags": result.overall_flags,
        "overall_status": result.overall_status,
        "generated_at": result.generated_at
    }

# Tanezumab (Human Control)
tanezumab_vh = "QVQLQESGPGLVRPSQTLSLTCTVSGFSLIGYDLNWVRQPPGRGLEWIGIIWGDGTTDYNSAVKSRVTMLKDTSKNQFSLRLSSVTAADTAVYYCARGGYWYATSYYFDYWGQGTLVTVSS"
tanezumab_vl = "DIQMTQSPSSLSASVGDRVTITCRASQSISNNLNWYQQKPGKAPKLLIYYTSRFHSGVPSRFSGSGSGTDFTFTISSLQPEDIATYYCQQEHTLPYTFGQGTKLEIK"

# V3 (IGHV3-9 + IGKV3-18)
v3_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFSLIGYDLNWVRQAPGKGLQWLGIIWGDGTTDYNSAVKSRVTISKDSAKNTFYLQLQSLRAEETAVYYCARGGYWYATSYYFDYWGQGTSVTVSS"
v3_vl = "EIVLTQSPASLSLSQEEKVTITCRASQSISNNLNWYQQKPGQAPKLLIYYTSRFHSGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQEHTLPYTFGQGTKVELK"

# V4 (IGHV3-19 + IGLV1-141)
# VH: IGHV3-19*01 + H71K, H78F
v4_vh = "EVQLVESGGDLVKPAGSLRLSCVASGFSLIGYDLNWVRQAPEKGLQLVAIIWGDGTTDYNSAVKSRFTISKDFAKNTVYLQMRAEDTAMYYCAKGGYWYATSYYFDYWGQGTSVTVSS"
# VL: IGLV1-141*01 + Tanezumab CDRs + Bedinvetmab FR4
v4_vl = "QSVLTQPTSVSGSLGQRVTISCRASQSISNNLNWYQQLPGKAPKLLVYYTSRFHSGVPDRFSGSNSGNSATLTITGLQAEDEADYYCQQEHTLPYTFGAGTKLEIK"

results = {}
results["Tanezumab"] = run_eval("Tanezumab", tanezumab_vh, tanezumab_vl, AntibodyType.FULLY_HUMAN, "Homo_sapiens")
results["V3"] = run_eval("V3", v3_vh, v3_vl, AntibodyType.DOG, "Canis_lupus_familiaris")
results["V4"] = run_eval("V4", v4_vh, v4_vl, AntibodyType.DOG, "Canis_lupus_familiaris")

with open("cmc_comparison.json", "w") as f:
    json.dump(results, f, indent=2)

print("CMC evaluation complete. Results saved to cmc_comparison.json")
