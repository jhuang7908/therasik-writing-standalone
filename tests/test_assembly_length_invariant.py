#!/usr/bin/env python3
"""
tests/test_assembly_length_invariant.py — Regression test for VH/VL assembly length preservation

Bug (2026-03-26 → 2026-03-27):
  _assemble_union_chain had `if imgt_pos >= 105: continue` which silently truncated
  Kabat positions 93–94 (FR3 end) in VH, producing 118 aa instead of 120 aa.

Invariant:
  assembled V region length >= mouse parent length
  (humanization does not remove amino acids from mouse)
"""
from __future__ import annotations

import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))


def test_mumab4d5_assembly_length_preservation():
    """Ensure muMAb4D5 assembly output VH=120 aa, VL=107 aa (parent lengths)."""
    from scripts.run_mumAb4D5_standard_humanization import load_mumab4d5_verified_vh_vl
    import importlib.util

    # Load parent sequences
    mouse_vh, mouse_vl = load_mumab4d5_verified_vh_vl()
    assert len(mouse_vh) == 120, f"Expected mouse VH=120 aa, got {len(mouse_vh)}"
    assert len(mouse_vl) == 107, f"Expected mouse VL=107 aa, got {len(mouse_vl)}"

    # Load pipeline and simulate assembly
    spec = importlib.util.spec_from_file_location(
        "pipe", SUITE / "scripts" / "run_vhvl_v44_pipeline.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    cfg_path = SUITE / "config" / "vh_vl_humanization_v44.json"
    import json
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}

    # v1: CDR graft only
    v1_vh, v1_vl = mod._assemble_v1(mouse_vh, mouse_vl, "IGHV3-23*01", "IGKV1-39*01", cfg)
    assert len(v1_vh) >= len(mouse_vh), (
        f"v1 VH length FAIL: {len(v1_vh)} aa < mouse {len(mouse_vh)} aa "
        "(FR truncation detected)"
    )
    assert len(v1_vl) >= len(mouse_vl), (
        f"v1 VL length FAIL: {len(v1_vl)} aa < mouse {len(mouse_vl)} aa "
        "(FR truncation detected)"
    )

    # v2: CDR graft + backmutations
    v2_vh, v2_vl = mod._assemble_v2(
        mouse_vh, mouse_vl, "IGHV3-23*01", "IGKV1-39*01", {}, {}, cfg
    )
    assert len(v2_vh) >= len(mouse_vh), (
        f"v2 VH length FAIL: {len(v2_vh)} aa < mouse {len(mouse_vh)} aa "
        "(FR truncation detected)"
    )
    assert len(v2_vl) >= len(mouse_vl), (
        f"v2 VL length FAIL: {len(v2_vl)} aa < mouse {len(mouse_vl)} aa "
        "(FR truncation detected)"
    )

    # Specific muMAb4D5 values (after 2026-03-27 fix)
    assert len(v2_vh) == 120, f"v2 VH should be 120 aa, got {len(v2_vh)} (post-fix check)"
    assert len(v2_vl) == 107, f"v2 VL should be 107 aa, got {len(v2_vl)} (post-fix check)"


if __name__ == "__main__":
    test_mumab4d5_assembly_length_preservation()
    print("✓ Assembly length invariant: PASS")
