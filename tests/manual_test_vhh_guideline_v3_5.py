import sys
from pathlib import Path

# Python
project_root = Path(__file__).resolve.parents[1]
sys.path.insert(0, str(project_root))

from core.vhh_qa_validation_v3_5 import validate_vhh_humanization_result_v3_5


def main:
    #  result，
    # ：sequence_analysisv3.4
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFNIKDTY",
                "FR2": "MHWVRQRPGKGLEWVSA",
                "CDR2": "YISYSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS"
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFNIKDTY",
                "FR2": "MHWVRQRPGKGLEWVSA",
                "CDR2": "YISYSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS"
            }
        },
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFNIKDTYMHWVRQRPGKGLEWVSAYISYSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAAGGVGWPYFDYWGQGTQVTVSS",
            "template": {
                "id": "TEMPLATE_001",
                "flags": {"has_vhh_hallmark": True},
                "fr3_sequence": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC"
            },
            "developability": {"score": 0.65, "score_type": "aggregate"},
            "immunogenicity": {"fr_immuno_risk": "low"}
        },
        "original_developability": {"score": 0.60},
        "original_immunogenicity": {"fr_immuno_risk": "low"},
        "candidates": [
            {
                "template_id": "VHH_TEMPLATE_001",
                "scores": {
                    "final": 0.85,
                    "combined_score": 0.82,
                    "fr_identity": 0.90,
                    "structural_risk": 0.25,
                },
                "flags": {
                    "has_vhh_hallmark": True,
                    "reduced_hallmark": False,
                },
                "template": {
                    "flags": {
                        "has_vhh_hallmark": True,
                    }
                }
            }
        ],
        "mutations": {"list": []}
    }

    qa_v3_5 = validate_vhh_humanization_result_v3_5(
        result,
        strict=True,
        calibration=None,
    )

    print("OK:", qa_v3_5["ok"])
    print("Traffic light:", qa_v3_5["guideline"]["traffic_light"])
    for f in qa_v3_5["guideline"]["flags"]:
        print(f"[{f['id']}] level={f['level']}, value={f['value']:.2f}")
        print("  ", f["message"])


if __name__ == "__main__":
    main

