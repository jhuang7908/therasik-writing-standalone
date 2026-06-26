#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_runtime_alignment.py — lightweight drift detection for VHH runtime files
"""
from __future__ import annotations

import sys
from pathlib import Path

_SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SUITE_ROOT))

from scripts.pipeline_policy import load_standards_ssot  # noqa: E402


TARGET_FILES = [
    _SUITE_ROOT / "projects" / "four_vhh_structure_qc" / "run_structure_qc_pipeline.py",
    _SUITE_ROOT / "scripts" / "vhh_conversion_pipeline.py",
]


def _quoted_literals(token: str) -> list[str]:
    return [f'"{token}"', f"'{token}'"]


def main() -> int:
    ssot = load_standards_ssot()
    policies = ssot.get("runtime_policies") or {}
    vhh_source_types = (
        "camelid_wt",
        "transgenic_mouse",
        "murine_wt_vh",
        "conventional_vh",
    )
    forbidden_predictors = set()
    forbidden_modules = set()
    for source_type in vhh_source_types:
        pol = policies.get(source_type) or {}
        forbidden_predictors.update((pol.get("structure_policy") or {}).get("forbidden_predictors") or [])
        forbidden_modules.update((pol.get("evaluator_policy") or {}).get("forbidden_modules") or [])

    ok = True
    for path in TARGET_FILES:
        if not path.is_file():
            ok = False
            print(f"[FAIL] missing target file: {path.relative_to(_SUITE_ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")

        for token in sorted(forbidden_predictors):
            if any(lit in text for lit in _quoted_literals(token)):
                ok = False
                print(
                    f"[FAIL] {path.relative_to(_SUITE_ROOT)} contains forbidden predictor literal {token!r}"
                )

        for token in sorted(forbidden_modules):
            if any(lit in text for lit in _quoted_literals(token)):
                ok = False
                print(
                    f"[FAIL] {path.relative_to(_SUITE_ROOT)} contains forbidden module literal {token!r}"
                )

    if ok:
        print("PASS — runtime files do not contain forbidden VHH predictors/modules.")
        return 0

    print("FAIL — runtime alignment drift detected.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

