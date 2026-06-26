#!/usr/bin/env python3
"""
run_caninization.py — AbEngineCore （）CLI
======================================================
 HumanizationEngine(workflow="dog")， Phase 2-dog / 4-dog / 5-dog。

：
  - data/germlines/canis_lupus_familiaris_ig_aa/dog_scaffold_shortlist_tier1_tier2_v1.json
  - data/pet_antibody_atlas/master_table.csv（Tier1  VH/VL ）
  - anarcii（）： VH CDR 

：
  cd Antibody_Engineer_Suite
  python scripts/run_caninization.py --project my_ab --vh EVQL... --vl DIV...

  # （， FASTA ）
  python scripts/run_caninization.py --project my_ab --vh-file vh.fa --vl-file vl.fa

：
   scripts/run_dog_humanization_pipeline_v1.py、run_dog_caninization_auto_v1.py
  ； dog workflow。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parents[1]
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))


def _read_seq_arg(raw: str | None, path: Path | None) -> str:
    if path:
        text = path.read_text(encoding="utf-8")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            raise SystemExit(f"Empty file: {path}")
        if lines[0].startswith(">"):
            lines = lines[1:]
        if not lines:
            raise SystemExit(f"No sequence after header in: {path}")
        return "".join(lines).replace(" ", "").upper()
    if raw:
        return raw.strip().replace(" ", "").upper()
    raise SystemExit("Provide --vh/--vl or --vh-file/--vl-file")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Dog caninization via HumanizationEngine(workflow='dog')",
    )
    ap.add_argument("--project", "-p", required=True, help="Project / antibody id (output naming)")
    ap.add_argument("--vh", default=None, help="Donor VH amino acid sequence")
    ap.add_argument("--vl", default=None, help="Donor VL amino acid sequence")
    ap.add_argument("--vh-file", type=Path, default=None, help="File with VH sequence")
    ap.add_argument("--vl-file", type=Path, default=None, help="File with VL sequence")
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: projects/<project>/delivery_caninization)",
    )
    ap.add_argument("--json-only", action="store_true", help="Only write JSON report (skip MD)")
    args = ap.parse_args()

    vh = _read_seq_arg(args.vh, args.vh_file)
    vl = _read_seq_arg(args.vl, args.vl_file)

    out = args.out_dir
    if out is None:
        out = SUITE_ROOT / "projects" / args.project / "delivery_caninization"
    out = Path(out)

    from core.humanization import HumanizationEngine

    engine = HumanizationEngine(workflow="dog")
    result = engine.run(vh, vl, args.project, out_dir=str(out))

    result.save_report()
    if not args.json_only:
        result.save_report_md()

    print(f"\n[run_caninization] overall_status={result.overall_status}")
    print(f"[run_caninization] out_dir={out}")
    sel = result.checklist_report.get("scaffold_selection", {}).get("selected", {})
    if sel.get("id"):
        print(f"[run_caninization] selected_scaffold={sel.get('id')} tier={sel.get('tier')}")

    if result.overall_status == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
