#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Stage 1 & Stage 2 


"""

from __future__ import annotations

from typing import Dict, Any, List


def audit_stage12(result: Dict[str, Any]) -> str:
    """
     Stage 1 & Stage 2 
    
    Returns:
        Markdown 
    """
    lines = []
    lines.append("# Stage 1 & Stage 2 ")
    lines.append("")
    
    all_passed = True
    errors = []
    warnings = []
    
    # ========== Stage 1  ==========
    lines.append("## Stage 1: Scaffold ")
    lines.append("")
    
    # 1. 
    required_fields = [
        "input_provenance",
        "segmentation_provenance",
        "scaffold_library_provenance",
        "excluded_scaffolds",
        "stage1",
    ]
    
    for field in required_fields:
        if field not in result:
            all_passed = False
            errors.append(f": {field}")
            lines.append(f"❌ **{field}**: ")
        else:
            lines.append(f"✅ **{field}**: ")
    
    lines.append("")
    
    # 2.  scaffold_library_provenance
    if "scaffold_library_provenance" in result:
        prov = result["scaffold_library_provenance"]
        if not prov.get("sha256"):
            all_passed = False
            errors.append("scaffold_library_provenance.sha256 ")
            lines.append("❌ **scaffold_library_provenance.sha256**: ")
        else:
            lines.append(f"✅ **scaffold_library_provenance.sha256**: {prov['sha256'][:16]}...")
        
        if not prov.get("entry_count"):
            all_passed = False
            errors.append("scaffold_library_provenance.entry_count 0")
            lines.append("❌ **scaffold_library_provenance.entry_count**: 0")
        else:
            lines.append(f"✅ **scaffold_library_provenance.entry_count**: {prov['entry_count']}")
    
    lines.append("")
    
    # 3.  stage1.scaffold_alignment_provenance
    if "stage1" in result:
        stage1 = result["stage1"]
        
        if "scaffold_alignment_provenance" not in stage1:
            all_passed = False
            errors.append("stage1.scaffold_alignment_provenance ")
            lines.append("❌ **stage1.scaffold_alignment_provenance**: ")
        else:
            align_prov = stage1["scaffold_alignment_provenance"]
            if align_prov.get("algorithm") != "imgt_position_identity":
                all_passed = False
                errors.append(f"stage1.scaffold_alignment_provenance.algorithm  'imgt_position_identity'， '{align_prov.get('algorithm')}'")
                lines.append(f"❌ **algorithm**:  'imgt_position_identity'， '{align_prov.get('algorithm')}'")
            else:
                lines.append(f"✅ **algorithm**: {align_prov.get('algorithm')}")
    
    lines.append("")
    
    # 4.  ranked_top10
    if "stage1" in result and "ranked_top10" in result["stage1"]:
        ranked_top10 = result["stage1"]["ranked_top10"]
        
        if not ranked_top10:
            all_passed = False
            errors.append("stage1.ranked_top10 ")
            lines.append("❌ **ranked_top10**: ")
        else:
            lines.append(f"✅ **ranked_top10**: {len(ranked_top10)} ")
            
            #  imgt_positions_compared
            for i, cand in enumerate(ranked_top10, 1):
                if cand.get("imgt_positions_compared", 0) == 0:
                    all_passed = False
                    errors.append(f"ranked_top10[{i}] ({cand.get('scaffold_id')})  imgt_positions_compared=0")
                    lines.append(f"❌ **ranked_top10[{i}].imgt_positions_compared**: 0")
                else:
                    lines.append(f"✅ **ranked_top10[{i}].imgt_positions_compared**: {cand.get('imgt_positions_compared')}")
    else:
        all_passed = False
        errors.append("stage1.ranked_top10 ")
        lines.append("❌ **ranked_top10**: ")
    
    lines.append("")
    
    # 5.  selected_scaffold
    if "stage1" in result and "selected_scaffold" in result["stage1"]:
        selected = result["stage1"]["selected_scaffold"]
        selected_id = selected.get("scaffold_id")
        
        #  selected  top10 
        if "ranked_top10" in result["stage1"]:
            top10_ids = [c.get("scaffold_id") for c in result["stage1"]["ranked_top10"]]
            if selected_id not in top10_ids:
                all_passed = False
                errors.append(f"selected_scaffold ({selected_id})  ranked_top10 ")
                lines.append(f"❌ **selected_scaffold  top10 **: ")
            else:
                lines.append(f"✅ **selected_scaffold  top10 **: ")
        
        lines.append(f"✅ **selected_scaffold.scaffold_id**: {selected_id}")
        lines.append(f"✅ **selected_scaffold.framework_identity**: {selected.get('framework_identity', 0.0):.4f}")
    else:
        all_passed = False
        errors.append("stage1.selected_scaffold ")
        lines.append("❌ **selected_scaffold**: ")
    
    lines.append("")
    
    # ========== Stage 2  ==========
    lines.append("## Stage 2: SAFE A/B/C ")
    lines.append("")
    
    # 1. 
    if "stage2" not in result:
        all_passed = False
        errors.append("stage2 ")
        lines.append("❌ **stage2**: ")
    else:
        stage2 = result["stage2"]
        
        if "safe_strategy_definitions" not in stage2:
            all_passed = False
            errors.append("stage2.safe_strategy_definitions ")
            lines.append("❌ **safe_strategy_definitions**: ")
        else:
            lines.append("✅ **safe_strategy_definitions**: ")
        
        if "safe_variants" not in stage2:
            all_passed = False
            errors.append("stage2.safe_variants ")
            lines.append("❌ **safe_variants**: ")
        else:
            safe_variants = stage2["safe_variants"]
            
            # 3
            if len(safe_variants) != 3:
                all_passed = False
                errors.append(f"stage2.safe_variants 3， {len(safe_variants)} ")
                lines.append(f"❌ **safe_variants **: 3， {len(safe_variants)}")
            else:
                lines.append(f"✅ **safe_variants **: {len(safe_variants)}")
            
            # 
            for plan_key in ["A", "B", "C"]:
                variant_key = f"SAFE_{plan_key}"
                if variant_key not in safe_variants:
                    all_passed = False
                    errors.append(f"stage2.safe_variants.{variant_key} ")
                    lines.append(f"❌ **{variant_key}**: ")
                else:
                    variant = safe_variants[variant_key]
                    
                    # 
                    required_variant_fields = ["template_id", "sequence", "diff_vs_scaffold", "physiology_explanations"]
                    for field in required_variant_fields:
                        if field not in variant:
                            all_passed = False
                            errors.append(f"stage2.safe_variants.{variant_key}.{field} ")
                            lines.append(f"❌ **{variant_key}.{field}**: ")
                        else:
                            lines.append(f"✅ **{variant_key}.{field}**: ")
                    
                    # ：diff_vs_scaffold 
                    if "diff_vs_scaffold" in variant and "sequence" in variant:
                        diff_count = len(variant["diff_vs_scaffold"])
                        if diff_count > 0:
                            lines.append(f"✅ **{variant_key}.diff_vs_scaffold **: {diff_count}")
                        else:
                            warnings.append(f"{variant_key} （diff_vs_scaffold ）")
                            lines.append(f"⚠️  **{variant_key}.diff_vs_scaffold**: （）")
    
    lines.append("")
    
    # ==========  ==========
    lines.append("## ")
    lines.append("")
    
    if all_passed and not errors:
        lines.append("✅ ****")
    else:
        lines.append("❌ ****")
        lines.append("")
        lines.append("### ")
        for error in errors:
            lines.append(f"- ❌ {error}")
    
    if warnings:
        lines.append("")
        lines.append("### ")
        for warning in warnings:
            lines.append(f"- ⚠️  {warning}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path
    
    if len(sys.argv) < 2:
        print("Usage: python audit_stage12.py <result_stage12.json>")
        sys.exit(1)
    
    result_path = Path(sys.argv[1])
    with open(result_path, "r", encoding="utf-8") as f:
        result = json.load(f)
    
    audit_report = audit_stage12(result)
    print(audit_report)













