#!/usr/bin/env python3
"""
Test: Verify that humanization FAILS without structure
"""

import sys
from pathlib import Path

_SUITE_ROOT = Path(__file__).parent

sys.path.insert(0, str(_SUITE_ROOT))

from core.humanization import HumanizationEngine

print("=" * 80)
print("TEST: Humanization should FAIL without structure")
print("=" * 80)
print()

# Use the muMAb4D5 sequences
MUMAB4D5_VH = (
    "EVQLQQSGPELVKPGASVKMSCKASGFNIKDTYIHWVRQAPGKGLEWVARIYPTNGYTRYADSVK"
    "GRFTISADTSKNTAYLQMNSLRAEDTAVYYCSRWGGDGFYAMDYWGQGTLVTVSS"
)

MUMAB4D5_VL = (
    "DIQMTQSPSSLSASVGDRVTITCRASQDVNTAVAWYQQKPGKAPKLLIYSASFLYSGVPSRFSGS"
    "RSGTDFTLTISSLQPEDFATYYCQQHYTTPPTFGQGTKVEIK"
)

print("[TEST] Creating engine with FORCED DRY_RUN to simulate structure failure...")
print()

engine = HumanizationEngine(workflow="vh_vl")
# Force DRY_RUN to simulate structure prediction failure
engine._dry_run = True

print(f"Engine state: _dry_run = {engine._dry_run} (forced)")
print()

print("[TEST] Running humanization (should FAIL at Phase 3)...")
print()

try:
    result = engine.run(
        mouse_vh=MUMAB4D5_VH,
        mouse_vl=MUMAB4D5_VL,
        project_name="test_no_structure",
        out_dir=str(_SUITE_ROOT / "projects" / "test_no_structure" / "delivery"),
    )
    print()
    print("❌ TEST FAILED: Humanization completed even without structure!")
    print(f"   Result status: {result.overall_status}")
    sys.exit(1)

except RuntimeError as e:
    if "MANDATORY HARD GATE" in str(e) or "Structure prediction unavailable" in str(e):
        print()
        print("✅ TEST PASSED: Humanization correctly FAILED at Phase 3")
        print(f"   Error message: {str(e)[:100]}...")
        sys.exit(0)
    else:
        print()
        print(f"❌ TEST FAILED: Wrong error type: {e}")
        sys.exit(1)

except Exception as e:
    print()
    print(f"❌ TEST FAILED: Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
