#!/usr/bin/env python3
"""
Export VH/VL humanization HTML report — same shell as POST /humanize/vh_vl (Report Version V4.8.2).

Uses HumanizationEngine + api.routers.humanization._humanize_vh_vl_impl (writes under .job_storage/<job_id>/).

Example:
  conda activate anarcii
  python scripts/export_vhvl_humanization_html_v482.py \\
    --vh "DVKL..." --vl "DVVMT..." \\
    --copy-to projects/my_run/humanization_report_V482.html \\
    --dry-run-structure
"""
from __future__ import annotations

import argparse
import shutil
import sys
import uuid
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))


def main() -> int:
    p = argparse.ArgumentParser(description="VH/VL humanization → V4.8.2 HTML report (offline)")
    p.add_argument("--vh", required=True, help="Donor VH aa sequence")
    p.add_argument("--vl", required=True, help="Donor VL aa sequence")
    p.add_argument("--source-species", default="mouse", choices=("mouse", "rat", "rabbit"))
    p.add_argument("--repair-mode", default="standard", choices=("standard", "rescue"))
    p.add_argument("--back-mutation-strategy", default="standard")
    p.add_argument("--report-language", default="en", help="en | zh")
    p.add_argument("--dry-run-structure", action="store_true", help="Skip ABodyBuilder2 (faster, WARN structure rows)")
    p.add_argument(
        "--copy-to",
        default="",
        help="Optional path to copy humanization_report.html after run (file or directory)",
    )
    args = p.parse_args()

    from api.models import VHVLRequest
    from api.routers import humanization as hum

    job_id = f"cli_{uuid.uuid4().hex[:12]}"
    req = VHVLRequest(
        vh_sequence=args.vh.replace(" ", "").strip(),
        vl_sequence=args.vl.replace(" ", "").strip(),
        project_name=job_id,
        source_species=args.source_species,
        report_format="html",
        report_language=args.report_language,
        repair_mode=args.repair_mode,
        back_mutation_strategy=args.back_mutation_strategy,
        dry_run_structure=bool(args.dry_run_structure),
    )

    status = hum._humanize_vh_vl_impl(job_id, req)
    src = SUITE / ".job_storage" / job_id / "humanization_report.html"
    if not src.is_file():
        print(f"ERROR: expected report missing: {src}", file=sys.stderr)
        if status.error:
            print(status.error, file=sys.stderr)
        return 1

    print(str(src))
    if args.copy_to:
        dst = Path(args.copy_to)
        if dst.is_dir() or str(dst).endswith(("/", "\\")):
            dst = dst / "humanization_report.html"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"copied -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
