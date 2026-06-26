#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Stage 1 & Stage 2 

 EGFR VHH FASTA
 Stage1（ scaffold）
 Stage2（ SAFE_A/B/C）
 output/result_stage12.json
 output/audit_stage12.md（）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.stage12_germline_selection import (
    stage1_select_scaffold,
    stage2_generate_safe_variants,
    read_fasta,
)


def main():
    parser = argparse.ArgumentParser(description="Stage 1 & Stage 2 ")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help=" FASTA ",
    )
    parser.add_argument(
        "--scaffold",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_scaffolds" / "human_vh3_scaffolds.json",
        help="Scaffold ",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "output",
        help="",
    )
    
    args = parser.parse_args()
    
    # 
    args.out.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("Stage 1 & Stage 2 ")
    print("=" * 80)
    print()
    
    try:
        # 
        print("[1] ...")
        sequence_id, sequence = read_fasta(args.input)
        print(f"  ✅ ID: {sequence_id}")
        print(f"  ✅ : {len(sequence)} aa")
        print()
        
        # Stage 1: Scaffold 
        print("[2] Stage 1: Scaffold ...")
        stage1_result = stage1_select_scaffold(
            query_seq=sequence,
            scaffold_library_path=str(args.scaffold),
            scheme="imgt",
            method="anarcii",
            mask_regions=("CDR1", "CDR2", "CDR3"),
            min_vh_len=75,
            top_k=10,
        )
        
        selected_scaffold = stage1_result["stage1"]["selected_scaffold"]
        print(f"  ✅  scaffold: {selected_scaffold['scaffold_id']}")
        print(f"  ✅ Framework Identity: {selected_scaffold['framework_identity']:.4f}")
        print(f"  ✅ Top 10 : {len(stage1_result['stage1']['ranked_top10'])}")
        print()
        
        #  scaffold （ Stage 2）
        print("[3]  scaffold ...")
        with open(args.scaffold, "r", encoding="utf-8") as f:
            scaffold_library = json.load(f)
        print(f"  ✅ : {len(scaffold_library)}")
        print()
        
        # Stage 2:  SAFE A/B/C
        print("[4] Stage 2:  SAFE A/B/C ...")
        numbering_maps = stage1_result.get("numbering_maps", {})
        stage2_result = stage2_generate_safe_variants(
            selected_scaffold=selected_scaffold,
            scaffold_library=scaffold_library,
            numbering_maps=numbering_maps,
            scheme="imgt",
            method="anarcii",
            safe_rules=None,  # 
        )
        
        for plan_key in ["A", "B", "C"]:
            variant = stage2_result["safe_variants"][f"SAFE_{plan_key}"]
            print(f"  ✅ SAFE_{plan_key}: {variant['template_id']}")
            print(f"     : {len(variant['diff_vs_scaffold'])}")
        print()
        
        # 
        result = {
            **stage1_result,
            "stage2": stage2_result,
        }
        
        #  JSON
        result_json_path = args.out / "result_stage12.json"
        with open(result_json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"✅ : {result_json_path}")
        print()
        
        # 
        print("[5] ...")
        from scripts.audit_stage12 import audit_stage12
        
        audit_result = audit_stage12(result)
        
        audit_md_path = args.out / "audit_stage12.md"
        with open(audit_md_path, "w", encoding="utf-8") as f:
            f.write(audit_result)
        print(f"✅ : {audit_md_path}")
        print()
        
        print("=" * 80)
        print("✅ ！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

