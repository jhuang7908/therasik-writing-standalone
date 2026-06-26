"""
VHH QA v3.4
"""

from core.vhh_qa_validation_v3_4 import validate_vhh_humanization_result_v3_4
from core.vhh_qa_data_calibration import VHHDataCalibration


def make_minimal_result_skeleton:
    """"""
    return {
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
                "template_id": "HUMAN_VH3_SCF_24",
                "scores": {
                    "fr_identity": 0.82,
                    "combined": 0.70
                },
                "flags": {"has_vhh_hallmark": True},
                "template": {
                    "id": "HUMAN_VH3_SCF_24",
                    "flags": {"has_vhh_hallmark": True},
                    "fr3_sequence": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC"
                }
            }
        ],
        "mutations": {"list": []}
    }


def main:
    print("=" * 80)
    print("VHH QA v3.4 ")
    print("=" * 80)
    
    # 
    dummy_result = make_minimal_result_skeleton
    
    # 1：
    print("\n1: ")
    out1 = validate_vhh_humanization_result_v3_4(dummy_result, strict=True, calibration=None)
    print(f"✅ OK: {out1['ok']}")
    print(f"📊 Structural Risk Components: {out1.get('structural_risk_components', {})}")
    print(f"❌ Errors: {len(out1.get('errors', []))}")
    print(f"⚠️  Warnings: {len(out1.get('warnings', []))}")
    
    # 2：
    print("\n2: ")
    calibration = VHHDataCalibration(calibration_db_path=None)
    out2 = validate_vhh_humanization_result_v3_4(dummy_result, strict=True, calibration=calibration)
    print(f"✅ OK: {out2['ok']}")
    print(f"📊 Calibrated Weights: {calibration.get_calibrated_weights}")
    
    # 3：CDR3 anchor
    print("\n3: CDR3 anchor")
    high_risk_result = make_minimal_result_skeleton
    # FR3101/102，
    fr3_list = list(high_risk_result["sequence_analysis"]["humanized_regions"]["FR3"])
    # FR3IMGT 66，101-66=35, 102-66=36
    if len(fr3_list) > 36:
        fr3_list[35] = "X"  # 101
        fr3_list[36] = "Y"  # 102
    high_risk_result["sequence_analysis"]["humanized_regions"]["FR3"] = "".join(fr3_list)
    out3 = validate_vhh_humanization_result_v3_4(high_risk_result, strict=True, calibration=None)
    print(f"✅ OK: {out3['ok']}")
    print(f"📊 CDR3 Anchor Risk: {out3.get('structural_risk_components', {}).get('cdr3_anchor_risk', 0):.2f}")
    print(f"❌ Errors: {out3.get('errors', [])}")
    
    print("\n" + "=" * 80)
    print("")
    print("=" * 80)


if __name__ == "__main__":
    main

















