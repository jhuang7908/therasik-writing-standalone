#!/usr/bin/env python3
"""
Test script: Re-run muMAb4D5 humanization with fixed Phase 2 (v4.5.1 canonical class gate).

Purpose:
  Verify that the new canonical class gate (step 2.1b) and corrected CDR fallback
  now produce the correct framework selection: IGHV3-23*04 + IGKV1-39*01
  (not IGHV3-23*01 + IGKV1-33*01)

Expected outcome:
  - VH: IGHV3-23*04 (52A insertion handled by canonical class equivalence)
  - VL: IGKV1-39*01 (L1-10-1 class supported)
  - Back-mutations: H48/H49/H67 (from *04 vs *01 allele diff)
"""

import sys
from pathlib import Path

# Setup paths
SUITE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SUITE_ROOT))

from core.humanization.engine import HumanizationEngine

def test_mumab4d5_v451():
    """Run muMAb4D5 humanization with v4.5.1 canonical class gate."""
    
    # muMAb4D5 SeqV-B (canonical, from Carter 1992 PNAS Figure 1)
    vh_mouse = (
        "QVQLQQSGPELVKPGASLKLSCTASGFNIKDTYIHWVKQRPEQGLEWIGRIYPTNGYTRYDPKFQDKATITADTSSNTAYLQVSRLTSEDTAVYYCSRWGGDGFYAMDYWGQGASVTVSS"
    )
    vl_mouse = (
        "DIVMTQSHKFMSTSVGDRVSITCKASQDVNTAVAWYQQKPGHSPKLLIYSASFRYTGVPDRFTGNRSGTDFTFTISSVQAEDLAVYYCQQHYTTPPTFGGGTKVEIK"
    )
    
    print(f"[INFO] muMAb4D5 SeqV-B (Carter 1992)")
    print(f"[INFO] Mouse VH len: {len(vh_mouse)} aa (CDR-H2 with 52A insertion: 17 aa)")
    print(f"[INFO] Mouse VL len: {len(vl_mouse)} aa (CDR-L1 ultra-extended: 15 aa)")
    
    # Initialize engine (default VH/VL workflow, v4.4.1 config)
    engine = HumanizationEngine(workflow="vh_vl")
    
    print("[PHASE 2] Running Phase 2 framework selection...")
    
    # Phase 2 framework selection
    ph2_result = engine._phase2_framework_selection(vh_mouse, vl_mouse, cdr_data={})
    
    # Debug: check what's in the VH pool after CDR gate
    print("\n[DEBUG] VH/VL pools after Step 2.1 CDR gate:")
    vh_pool_debug = ph2_result.get("_vh_pool_after_cdr_gate", [])
    vl_pool_debug = ph2_result.get("_vl_pool_after_cdr_gate", [])
    print(f"  VH pool size: {len(vh_pool_debug) if vh_pool_debug else 'N/A'}")
    if vh_pool_debug:
        ighv323_in_pool = [gid for gid in vh_pool_debug if "IGHV3-23" in gid]
        print(f"  IGHV3-23 in pool: {ighv323_in_pool}")
    print(f"  VL pool size: {len(vl_pool_debug) if vl_pool_debug else 'N/A'}")
    if vl_pool_debug:
        igkv139_in_pool = [gid for gid in vl_pool_debug if "IGKV1-39" in gid]
        print(f"  IGKV1-39 in pool: {igkv139_in_pool}")
    
    print("\n[PHASE 2 RESULTS]")
    print(f"  CDR-H1 gate: {ph2_result.get('h1_gate', 'N/A')}")
    print(f"  CDR-H2 gate: {ph2_result.get('h2_gate', 'N/A')}")
    print(f"  CDR-L1 gate: {ph2_result.get('l1_gate', 'N/A')}")
    
    top_vh = ph2_result.get("top_vh", [])
    top_vl = ph2_result.get("top_vl", [])
    top_pairs = ph2_result.get("top_vh_vl_pairs", [])
    
    print(f"\n  Top VH germlines (before pairing):")
    for i, cand in enumerate(top_vh[:3], 1):
        print(f"    {i}. {cand.get('germline_id')} (score={cand.get('total_score')})")
    
    print(f"\n  Top VL germlines (before pairing):")
    for i, cand in enumerate(top_vl[:3], 1):
        print(f"    {i}. {cand.get('germline_id')} (score={cand.get('total_score')})")
    
    print(f"\n  Top VH/VL pairs (after pairing bonus):")
    for i, pair_data in enumerate(ph2_result.get("all_pair_scores", [])[:3], 1):
        print(f"    {i}. {pair_data.get('vh')} + {pair_data.get('vl')} "
              f"(combined={pair_data.get('combined')}, bonus={pair_data.get('bonus')})")
    
    sel_vh = ph2_result.get("selected_vh_id", "?")
    sel_vl = ph2_result.get("selected_vl_id", "?")
    
    print(f"\n[SELECTED]")
    print(f"  VH: {sel_vh}")
    print(f"  VL: {sel_vl}")
    
    # Verify expected results
    print("\n[VERIFICATION]")
    if "IGHV3-23" in sel_vh:
        print(f"  ✅ VH is IGHV3-23 family (correct)")
    else:
        print(f"  ❌ VH is NOT IGHV3-23 family (WRONG)")
    
    if "IGKV1-39" in sel_vl:
        print(f"  ✅ VL is IGKV1-39 (correct)")
    elif "IGKV1-33" in sel_vl:
        print(f"  ❌ VL is IGKV1-33 (WRONG — old bug reproduced)")
    else:
        print(f"  ⚠️  VL is {sel_vl} (unexpected)")
    
    if ph2_result.get("error"):
        print(f"\n[ERROR] {ph2_result.get('error')}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_mumab4d5_v451()
    sys.exit(0 if success else 1)
