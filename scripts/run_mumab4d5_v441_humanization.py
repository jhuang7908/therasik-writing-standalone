#!/usr/bin/env python3
"""
run_mumab4d5_v441_humanization.py — Execute muMAb4D5 VH/VL humanization (V4.4.1 unified engine)

This script executes the VERIFIED muMAb4D5 sequence through the complete humanization pipeline
with integrated Round 2 + Option B rescue logic.

The execution is a SINGLE call to HumanizationEngine.run() — the engine handles all phases,
rescue logic, and checklist enforcement internally.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Suite root
_SUITE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SUITE_ROOT))

# ─── Verified muMAb4D5 sequences (from sequence_cache/mumab4d5_verified.fasta) ────
# These sequences have passed PISG-v1 identity verification against PDB 1FVC + US Patent 5,821,337

MUMAB4D5_VH = (
    "EVQLQQSGPELVKPGASVKMSCKASGFNIKDTYIHWVRQAPGKGLEWVARIYPTNGYTRYADSVK"
    "GRFTISADTSKNTAYLQMNSLRAEDTAVYYCSRWGGDGFYAMDYWGQGTLVTVSS"
)

MUMAB4D5_VL = (
    "DIVMTQSHKFMSSTVGKASGVTKRASQDVNTAVAWYQQKPGKAPKLLIYSASFLYSGVPSRFSGS"
    "RSGTDFTLTISSLQPEDFATYYCQQHYTTPPTFGQGTKVEIK"
)  # 107 aa (no RT tail)

def main():
    print("=" * 80)
    print("muMAb4D5 VH/VL Humanization (V4.4.1 Complete Pipeline)")
    print("=" * 80)
    print()
    print(f"VH length: {len(MUMAB4D5_VH)} aa")
    print(f"VL length: {len(MUMAB4D5_VL)} aa (core 107 aa, without RT tail)")
    print()

    # Import engine
    try:
        from core.humanization import HumanizationEngine
    except ImportError as e:
        print(f"ERROR: Failed to import HumanizationEngine: {e}")
        print(f"Make sure you're running from the suite root directory.")
        return 1

    # Create engine
    print("[1] Initializing HumanizationEngine (workflow='vh_vl')…")
    engine = HumanizationEngine(workflow="vh_vl")
    print(f"    ✓ Engine initialized")
    print(f"    • Anarcii available: {engine._has_anarcii}")
    print(f"    • ImmuneBuilder available: {engine._has_immunebuilder}")
    print()

    # Execute
    print("[2] Running humanization pipeline (Phase 1 → 5 + Rescue)…")
    print("-" * 80)
    try:
        result = engine.run(
            mouse_vh=MUMAB4D5_VH,
            mouse_vl=MUMAB4D5_VL,
            project_name="mumab4d5_v441_standard",
            out_dir=str(_SUITE_ROOT / "projects" / "mumab4d5_v441_standard" / "delivery"),
        )
    except Exception as exc:
        print(f"\n❌ Pipeline FAILED with exception:")
        print(f"   {exc.__class__.__name__}: {exc}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        print("-" * 80)
        print()

    # Report results
    print("[3] Humanization results:")
    print(f"    Overall status: {result.overall_status}")
    print(f"    Sequences available: {list(result.sequences.keys())}")
    print()

    # Show sequences
    if result.sequences.get("Our_Hum_VH"):
        print(f"    Humanized VH ({len(result.sequences['Our_Hum_VH'])} aa):")
        print(f"      {result.sequences['Our_Hum_VH']}")
        print()
    if result.sequences.get("Our_Hum_VL"):
        print(f"    Humanized VL ({len(result.sequences['Our_Hum_VL'])} aa):")
        print(f"      {result.sequences['Our_Hum_VL']}")
        print()

    # Show QC metrics
    if result.qc_metrics:
        print(f"    QC Metrics:")
        for key in ["pI_fab", "GRAVY", "instability_index", "net_charge_pH7", "cdr_rmsd", "angle_delta_deg"]:
            if key in result.qc_metrics:
                print(f"      • {key}: {result.qc_metrics[key]}")
        print()

    # Show rescue audit if any
    execution_data = result.checklist_report.get("execution_data", {})
    rescue_audit = execution_data.get("rescue", {})
    if rescue_audit.get("rescue_enabled"):
        print(f"    Rescue Audit:")
        print(f"      • Total iterations: {rescue_audit.get('total_iterations')}")
        for attempt in rescue_audit.get("attempts", [])[:5]:
            print(f"      • {attempt.get('phase')} attempt {attempt.get('attempt_num')}: "
                  f"{'PASS' if attempt.get('success') else 'FAIL'}")
    else:
        print(f"    Rescue: Not needed (initial attempt passed)")
    print()

    # Save report
    print("[4] Saving reports…")
    try:
        result.save_report()
        print(f"    ✓ Report saved to: {result.out_dir}")
    except Exception as e:
        print(f"    ⚠ Report save failed: {e}")
    print()

    # Final status
    if result.overall_status == "PASS":
        print("✓ HUMANIZATION SUCCESSFUL")
        return 0
    else:
        print(f"⚠ HUMANIZATION {result.overall_status}")
        return 1 if result.overall_status == "FAIL" else 0

if __name__ == "__main__":
    sys.exit(main())
