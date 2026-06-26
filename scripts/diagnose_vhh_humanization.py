#!/usr/bin/env python3
"""
VHH
scaffold
"""

import sys
from pathlib import Path

# 
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import json
from typing import Dict, Any, List, Optional, Tuple

from core.scaffolds import (
    load_alpaca_vhh_scaffolds,
    load_human_vhh_safe_templates,
    load_alignment_matrix,
)
from core.vhh_humanization import find_best_matching_scaffold
from core.numbering.imgt_anarcii import imgt_number_anarcii


def diagnose_vhh_humanization(sequence: str, panel: str = "A") -> Dict[str, Any]:
    """
    VHH
    
    Returns:
        
    """
    result = {
        "sequence": sequence,
        "sequence_length": len(sequence),
        "panel": panel,
        "steps": {},
        "errors": [],
        "warnings": [],
    }
    
    # Step 1: IMGT
    try:
        rows = imgt_number_anarcii(sequence)
        result["steps"]["imgt_numbering"] = {
            "success": True,
            "num_positions": len(rows),
        }
    except Exception as e:
        result["steps"]["imgt_numbering"] = {
            "success": False,
            "error": str(e),
        }
        result["errors"].append(f"IMGT: {e}")
        return result
    
    # Step 2: alpaca scaffolds
    try:
        alpaca_scaffolds = load_alpaca_vhh_scaffolds()
        result["steps"]["load_alpaca_scaffolds"] = {
            "success": True,
            "num_scaffolds": len(alpaca_scaffolds),
            "scaffold_ids": [s["scaffold_id"] for s in alpaca_scaffolds],
        }
    except Exception as e:
        result["steps"]["load_alpaca_scaffolds"] = {
            "success": False,
            "error": str(e),
        }
        result["errors"].append(f"alpaca scaffolds: {e}")
        return result
    
    # Step 3: scaffold
    best_scaffold, scaffold_identity = find_best_matching_scaffold(sequence, alpaca_scaffolds)
    
    if not best_scaffold:
        result["steps"]["scaffold_matching"] = {
            "success": False,
            "error": "scaffold",
        }
        result["errors"].append("alpaca scaffold")
        return result
    
    result["steps"]["scaffold_matching"] = {
        "success": True,
        "best_scaffold_id": best_scaffold["scaffold_id"],
        "scaffold_identity": round(scaffold_identity, 3),
        "scaffold_n_members": best_scaffold.get("n_members", 0),
    }
    
    # Step 4: 
    try:
        alignment_index = load_alignment_matrix()
        result["steps"]["load_alignment_matrix"] = {
            "success": True,
            "num_alpaca_scaffolds_in_matrix": len(alignment_index),
            "alpaca_scaffold_ids_in_matrix": list(alignment_index.keys()),
        }
    except Exception as e:
        result["steps"]["load_alignment_matrix"] = {
            "success": False,
            "error": str(e),
        }
        result["errors"].append(f": {e}")
        return result
    
    # Step 5: scaffold ID
    scaffold_id = best_scaffold["scaffold_id"]
    if scaffold_id not in alignment_index:
        result["steps"]["scaffold_in_matrix"] = {
            "success": False,
            "scaffold_id": scaffold_id,
            "error": f"Scaffold ID '{scaffold_id}' ",
        }
        result["errors"].append(f"scaffold '{scaffold_id}' ")
        
        # scaffold ID
        similar_ids = [sid for sid in alignment_index.keys() if scaffold_id[:10] in sid or sid[:10] in scaffold_id]
        if similar_ids:
            result["warnings"].append(f"scaffold ID: {similar_ids[:5]}")
        
        return result
    
    result["steps"]["scaffold_in_matrix"] = {
        "success": True,
        "scaffold_id": scaffold_id,
        "num_human_templates": len(alignment_index[scaffold_id]),
    }
    
    # Step 6: panel
    alignments = alignment_index[scaffold_id]
    
    # ID
    def extract_plan_from_template_id(template_id: str) -> str:
        """ID（A/B/C）"""
        if template_id.endswith('_SAFE_A'):
            return 'A'
        elif template_id.endswith('_SAFE_B'):
            return 'B'
        elif template_id.endswith('_SAFE_C'):
            return 'C'
        return ''
    
    # （）
    panel_templates = {}
    for tid, scores in alignments.items():
        plan = scores.get("human_plan", "") or extract_plan_from_template_id(tid)
        if plan.upper() == panel.upper():
            panel_templates[tid] = scores
    
    result["steps"]["panel_templates"] = {
        "success": len(panel_templates) > 0,
        "panel": panel,
        "num_templates": len(panel_templates),
        "template_ids": list(panel_templates.keys())[:10],  # 10
    }
    
    if len(panel_templates) == 0:
        result["errors"].append(f" {panel} human")
        
        # 
        all_plans = set()
        for scores in alignments.values():
            plan = scores.get("human_plan", "")
            if plan:
                all_plans.add(plan.upper())
        
        if all_plans:
            result["warnings"].append(f": {sorted(all_plans)}")
    
    # Step 7: human
    try:
        human_templates = load_human_vhh_safe_templates()
        result["steps"]["load_human_templates"] = {
            "success": True,
            "num_templates": len(human_templates),
        }
        
        # panelhuman
        if panel_templates:
            template_ids_in_panel = set(panel_templates.keys())
            template_ids_available = {t["template_id"] for t in human_templates}
            missing_templates = template_ids_in_panel - template_ids_available
            
            if missing_templates:
                result["warnings"].append(f" {len(missing_templates)} human")
                result["steps"]["template_availability"] = {
                    "success": False,
                    "missing_templates": list(missing_templates)[:5],
                }
            else:
                result["steps"]["template_availability"] = {
                    "success": True,
                }
    except Exception as e:
        result["steps"]["load_human_templates"] = {
            "success": False,
            "error": str(e),
        }
        result["warnings"].append(f"human: {e}")
    
    return result


def main():
    """"""
    import sys
    
    # 7D12 VHH
    seq_7d12 = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
    
    print("=" * 80)
    print("VHH")
    print("=" * 80)
    print(f"\n: {seq_7d12[:50]}...")
    print(f": {len(seq_7d12)}")
    print()
    
    # A
    print(" A:")
    print("-" * 80)
    result_a = diagnose_vhh_humanization(seq_7d12, panel="A")
    
    # 
    for step_name, step_result in result_a["steps"].items():
        status = "✅" if step_result.get("success", False) else "❌"
        print(f"{status} {step_name}:")
        if step_result.get("success"):
            for key, value in step_result.items():
                if key != "success":
                    print(f"    {key}: {value}")
        else:
            print(f"    : {step_result.get('error', 'Unknown error')}")
        print()
    
    # 
    if result_a["errors"]:
        print("❌ :")
        for error in result_a["errors"]:
            print(f"    - {error}")
        print()
    
    if result_a["warnings"]:
        print("⚠️  :")
        for warning in result_a["warnings"]:
            print(f"    - {warning}")
        print()
    
    # 
    print("=" * 80)
    print("")
    print("=" * 80)
    
    if result_a["errors"]:
        print("❌ ")
        print("\n:")
        for error in result_a["errors"]:
            print(f"  - {error}")
    else:
        print("✅ ")
        print("\n")
    
    # 
    output_file = Path("output/vhh_humanization_diagnosis.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result_a, f, indent=2, ensure_ascii=False)
    print(f"\n: {output_file}")


if __name__ == "__main__":
    main()

