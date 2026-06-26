#!/usr/bin/env python3
"""
 Fab ： IgFold  23  + 50  heavy_fab / light_fab 。

：
  -  20 ，、、
  - （heavy_fab  200–250 aa，light_fab  200–230 aa）
  -  JSON  chain_lengths / （）

：
  - data/design_rules/igg_like_fab_sequence_verify.json（ + ）
  - /， 1
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RULES = PROJECT_ROOT / "data" / "design_rules"
PATH_23 = DATA_RULES / "igg_like_23_three_arm_fab.json"
PATH_50 = DATA_RULES / "igg_like_50_four_arm_fab.json"
OUT_REPORT = DATA_RULES / "igg_like_fab_sequence_verify.json"

VALID_AAs = set("ACDEFGHIKLMNPQRSTVWY")
HEAVY_FAB_LEN_RANGE = (180, 260)
LIGHT_FAB_LEN_RANGE = (180, 250)


def check_sequence(seq: str, name: str) -> tuple[bool, list[str]]:
    """Return (ok, list of error messages)."""
    errs = []
    if not seq or not isinstance(seq, str):
        errs.append(f"{name}: empty or not string")
        return False, errs
    s = seq.strip().upper()
    invalid = [c for c in s if c not in VALID_AAs]
    if invalid:
        errs.append(f"{name}: invalid chars {sorted(set(invalid))}")
    if name == "heavy_fab":
        lo, hi = HEAVY_FAB_LEN_RANGE
    else:
        lo, hi = LIGHT_FAB_LEN_RANGE
    if len(s) < lo or len(s) > hi:
        errs.append(f"{name}: len={len(s)} out of range [{lo},{hi}]")
    return len(errs) == 0, errs


def verify_23() -> list[dict]:
    """Verify 23 three-arm Fab sequences. Return list of record dicts for report."""
    with open(PATH_23, encoding="utf-8") as f:
        data = json.load(f)
    records = []
    for rec in data.get("per_antibody", []):
        if rec.get("error"):
            records.append({
                "antibody_id": rec["antibody_id"],
                "subset": "23_three_arm",
                "arm_id": None,
                "skip": True,
                "reason": "error in source",
            })
            continue
        ab_id = rec["antibody_id"]
        light = rec.get("light_fab") or ""
        for arm_id, hkey in [("Arm1", "heavy_fab_1"), ("Arm2", "heavy_fab_2")]:
            heavy = rec.get(hkey) or ""
            ok_h, err_h = check_sequence(heavy, "heavy_fab")
            ok_l, err_l = check_sequence(light, "light_fab")
            ok = ok_h and ok_l
            records.append({
                "antibody_id": ab_id,
                "subset": "23_three_arm",
                "arm_id": arm_id,
                "heavy_len": len(heavy.strip()),
                "light_len": len(light.strip()),
                "ok": ok,
                "errors": err_h + err_l,
            })
    return records


def verify_50() -> list[dict]:
    """Verify 50 four-arm Fab sequences."""
    with open(PATH_50, encoding="utf-8") as f:
        data = json.load(f)
    records = []
    for rec in data.get("per_antibody", []):
        if rec.get("error"):
            records.append({
                "antibody_id": rec["antibody_id"],
                "subset": "50_four_arm",
                "arm_id": None,
                "skip": True,
                "reason": "error in source",
            })
            continue
        ab_id = rec["antibody_id"]
        for arm in rec.get("arms", []):
            arm_id = arm.get("arm_id", "")
            heavy = arm.get("heavy_fab") or ""
            light = arm.get("light_fab") or ""
            ok_h, err_h = check_sequence(heavy, "heavy_fab")
            ok_l, err_l = check_sequence(light, "light_fab")
            ok = ok_h and ok_l
            records.append({
                "antibody_id": ab_id,
                "subset": "50_four_arm",
                "arm_id": arm_id,
                "heavy_len": len(heavy.strip()),
                "light_len": len(light.strip()),
                "ok": ok,
                "errors": err_h + err_l,
            })
    return records


def main() -> int:
    if not PATH_23.exists():
        print(f"Missing: {PATH_23}", file=sys.stderr)
        return 1
    if not PATH_50.exists():
        print(f"Missing: {PATH_50}", file=sys.stderr)
        return 1

    all_records = verify_23() + verify_50()
    skipped = [r for r in all_records if r.get("skip")]
    checked = [r for r in all_records if not r.get("skip")]
    failed = [r for r in checked if not r.get("ok")]
    passed = [r for r in checked if r.get("ok")]

    report = {
        "meta": {
            "script": "verify_fab_sequences_bispecific.py",
            "verified_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_23": str(PATH_23),
            "source_50": str(PATH_50),
        },
        "summary": {
            "total_records": len(all_records),
            "skipped": len(skipped),
            "checked": len(checked),
            "passed": len(passed),
            "failed": len(failed),
        },
        "records": all_records,
    }

    DATA_RULES.mkdir(parents=True, exist_ok=True)
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Sequence verification report: {OUT_REPORT}")
    print(f"  Checked: {len(checked)}, Passed: {len(passed)}, Failed: {len(failed)}, Skipped: {len(skipped)}")
    if failed:
        for r in failed[:20]:
            print(f"  FAIL {r['antibody_id']}_{r.get('arm_id','')}: {r.get('errors', [])}")
        if len(failed) > 20:
            print(f"  ... and {len(failed) - 20} more (see report)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
