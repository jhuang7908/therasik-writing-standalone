#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_pipeline_policy.py — validate runtime policy shape in standards_ssot.json
"""
from __future__ import annotations

import sys
from pathlib import Path

_SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SUITE_ROOT))

from scripts.pipeline_policy import load_standards_ssot  # noqa: E402


def main() -> int:
    ssot = load_standards_ssot()
    standards = {s["id"] for s in ssot.get("standards") or []}
    policies = ssot.get("runtime_policies") or {}
    ok = True

    for source_type, policy in policies.items():
        sid = policy.get("standard_id")
        if sid not in standards:
            ok = False
            print(f"[FAIL] {source_type}: unknown standard_id {sid!r}")

        allowed_strategies = list(policy.get("allowed_strategies") or [])
        default_strategy = str(policy.get("default_strategy") or "")
        if (
            allowed_strategies
            and default_strategy
            and default_strategy != "auto"
            and default_strategy not in allowed_strategies
        ):
            ok = False
            print(
                f"[FAIL] {source_type}: default_strategy={default_strategy!r} "
                f"not present in allowed_strategies={allowed_strategies!r}"
            )

        sp = policy.get("structure_policy") or {}
        default_predictor = str(sp.get("default_predictor") or "")
        allowed_predictors = set(sp.get("allowed_predictors") or [])
        forbidden_predictors = set(sp.get("forbidden_predictors") or [])
        if sp.get("required") and not default_predictor:
            ok = False
            print(f"[FAIL] {source_type}: structure required but default_predictor missing")
        if default_predictor and default_predictor not in allowed_predictors:
            ok = False
            print(
                f"[FAIL] {source_type}: default_predictor={default_predictor!r} "
                f"not in allowed_predictors={sorted(allowed_predictors)!r}"
            )
        overlap_predictors = allowed_predictors & forbidden_predictors
        if overlap_predictors:
            ok = False
            print(f"[FAIL] {source_type}: predictor overlap {sorted(overlap_predictors)!r}")

        ep = policy.get("evaluator_policy") or {}
        allowed_modules = set(ep.get("allowed_modules") or [])
        forbidden_modules = set(ep.get("forbidden_modules") or [])
        overlap_modules = allowed_modules & forbidden_modules
        if overlap_modules:
            ok = False
            print(f"[FAIL] {source_type}: evaluator overlap {sorted(overlap_modules)!r}")

        qp = policy.get("qc_policy") or {}
        required_checks = set(qp.get("required_checks") or [])
        forbidden_checks = set(qp.get("forbidden_checks") or [])
        overlap_checks = required_checks & forbidden_checks
        if overlap_checks:
            ok = False
            print(f"[FAIL] {source_type}: qc overlap {sorted(overlap_checks)!r}")

    if ok:
        print("PASS — pipeline runtime policies are internally consistent.")
        return 0

    print("FAIL — fix config/standards_ssot.json runtime_policies.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

