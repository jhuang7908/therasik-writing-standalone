#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_standards_update.py — one command for SSOT alignment workflow

Usage:
  python scripts/apply_standards_update.py
  python scripts/apply_standards_update.py --check-only
  python scripts/apply_standards_update.py --emit-only
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List

_SUITE_ROOT = Path(__file__).resolve().parents[1]


def _run_step(args: List[str]) -> int:
    pretty = " ".join(args)
    print(f"\n=== Running: {pretty}")
    proc = subprocess.run(args, cwd=str(_SUITE_ROOT))
    return proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Apply standards SSOT update workflow in one command."
    )
    ap.add_argument(
        "--check-only",
        action="store_true",
        help="Run drift/policy/runtime checks only; do not emit generated docs.",
    )
    ap.add_argument(
        "--emit-only",
        action="store_true",
        help="Only regenerate docs/_generated output via sync_standards_alignment.py.",
    )
    args = ap.parse_args()

    if args.check_only and args.emit_only:
        print("Cannot use both --check-only and --emit-only.", file=sys.stderr)
        return 2

    py = sys.executable

    if args.emit_only:
        return _run_step([py, "scripts/sync_standards_alignment.py", "--emit-only"])

    steps: List[List[str]] = []
    if args.check_only:
        steps.append([py, "scripts/sync_standards_alignment.py", "--check-only"])
    else:
        steps.append([py, "scripts/sync_standards_alignment.py"])
    steps.append([py, "scripts/validate_pipeline_policy.py"])
    steps.append([py, "scripts/check_runtime_alignment.py"])

    for step in steps:
        rc = _run_step(step)
        if rc != 0:
            print(f"\nFAILED at step: {' '.join(step)}", file=sys.stderr)
            return rc

    print("\nPASS — standards update workflow completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

