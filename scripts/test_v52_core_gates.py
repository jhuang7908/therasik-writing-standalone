#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 v5.2 Core Gates

 Gate 。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.gates.v52_core_gates import (
    run_v52_core_gates,
    extract_cdr3_from_imgt,
    extract_fr4_from_imgt,
    load_curated_fr4_library,
    build_imgt_numbering_dict_from_rows,
)
from core.segmentation.anarcii_adapter import run_anarcii_imgt


def test_gate_module():
    """ Gate """
    print("=" * 80)
    print(" v5.2 Core Gates")
    print("=" * 80)
    print()
    
    # 1.  curated FR4 
    print("[1/4]  curated FR4 ...")
    try:
        curated_fr4_library = load_curated_fr4_library()
        print(f"  ✅ : {len(curated_fr4_library)} ")
        for ighj_id in sorted(curated_fr4_library.keys()):
            entry = curated_fr4_library[ighj_id]
            print(f"    - {ighj_id}: {entry['fr4_aa']}")
    except Exception as e:
        print(f"  ❌ : {e}")
        return
    print()
    
    # 2. （ EGFR VHH）
    print("[2/4] ...")
    query_seq_path = PROJECT_ROOT / "projects" / "EGFR_7D12_VHH" / "input" / "egfr_vhh.fasta"
    
    if not query_seq_path.exists():
        print(f"  ❌ : {query_seq_path}")
        return
    
    #  query 
    with open(query_seq_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        query_seq = "".join([line.strip() for line in lines if not line.startswith(">")])
    
    print(f"  ✅ Query : {len(query_seq)} aa")
    print(f"    Query: {query_seq[:50]}...")
    print()
    
    # 3.  query  IMGT 
    print("[3/4]  query  IMGT ...")
    try:
        query_regions, query_rows, query_provenance = run_anarcii_imgt(
            seq=query_seq,
            species="camelid",
            chain="H",
        )
        
        #  query IMGT numbering dict（）
        query_imgt_numbering = build_imgt_numbering_dict_from_rows(query_rows)
        
        query_cdr3 = extract_cdr3_from_imgt(query_imgt_numbering)
        query_fr4 = extract_fr4_from_imgt(query_imgt_numbering)
        
        print(f"  ✅ IMGT ")
        print(f"    Query CDR3: {query_cdr3} (len={len(query_cdr3)})")
        print(f"    Query FR4: {query_fr4} (len={len(query_fr4)})")
    except Exception as e:
        print(f"  ❌ IMGT : {e}")
        import traceback
        traceback.print_exc()
        return
    print()
    
    # 4.  v5.2 （）
    print("[4/4] ...")
    
    # ： query  CDR3 + curated FR4
    # ：， FR1-FR3
    test_humanized_seq = query_seq  #  query 
    
    try:
        humanized_regions, humanized_rows, humanized_provenance = run_anarcii_imgt(
            seq=test_humanized_seq,
            species="camelid",
            chain="H",
        )
        
        #  humanized IMGT numbering dict（）
        humanized_imgt_numbering = build_imgt_numbering_dict_from_rows(humanized_rows)
        
        humanized_cdr3 = extract_cdr3_from_imgt(humanized_imgt_numbering)
        humanized_fr4 = extract_fr4_from_imgt(humanized_imgt_numbering)
        
        print(f"  ✅ IMGT ")
        print(f"    Humanized CDR3: {humanized_cdr3} (len={len(humanized_cdr3)})")
        print(f"    Humanized FR4: {humanized_fr4} (len={len(humanized_fr4)})")
    except Exception as e:
        print(f"  ❌ IMGT : {e}")
        import traceback
        traceback.print_exc()
        return
    print()
    
    # 5.  Gate 
    print("=" * 80)
    print(" v5.2 Core Gates ")
    print("=" * 80)
    print()
    
    try:
        gate_result = run_v52_core_gates(
            query_seq=query_seq,
            humanized_seq=test_humanized_seq,
            query_imgt_numbering=query_imgt_numbering,
            humanized_imgt_numbering=humanized_imgt_numbering,
            curated_fr4_library=curated_fr4_library,
        )
        
        if gate_result.passed:
            print("✅ ALL GATES PASS")
            print()
            print("Gate :")
            for gate_name, gate_details in gate_result.details.items():
                print(f"  {gate_name}: {gate_details}")
        else:
            print(f"❌ GATE FAILED: {gate_result.failed_gate}")
            print(f"   : {gate_result.message}")
            if gate_result.details:
                print(f"   : {gate_result.details}")
    except Exception as e:
        print(f"❌ Gate : {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)
    print("")
    print("=" * 80)


if __name__ == "__main__":
    test_gate_module()

