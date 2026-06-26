#!/usr/bin/env python3
"""
Fv structure test using ABodyBuilder2 (ImmuneBuilder).

Structure predictor for this codebase: ABodyBuilder2 only.
IgFold removed — incompatible with transformers ≥5 in the active env.
ESMFold removed — requires openfold which is Linux-only (unavailable on Windows).

Usage (must run via conda run, not bare python after activate):

    conda run -n anarcii python scripts/compare_fv_structure_predictors.py ^
      --vh EVQLVE... ^
      --vl DIQMTQ... ^
      --out-dir out/fv_test

    conda run -n anarcii python scripts/compare_fv_structure_predictors.py ^
      --vh-file vh.fasta --vl-file vl.fasta ^
      --out-dir out/fv_test
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.humanization.engine import _run_abodybuilder2  # noqa: E402


def _fasta_read_one_sequence(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return "".join(
        ln.strip() for ln in lines if ln.strip() and not ln.startswith(">")
    ).replace(" ", "").upper()


def main() -> int:
    ap = argparse.ArgumentParser(description="ABodyBuilder2 Fv structure test.")
    ap.add_argument("--vh", default="", help="VH amino acid sequence")
    ap.add_argument("--vl", default="", help="VL amino acid sequence")
    ap.add_argument("--vh-file", default="", help="FASTA file containing VH")
    ap.add_argument("--vl-file", default="", help="FASTA file containing VL")
    ap.add_argument("--out-dir", required=True, type=Path, help="Output directory")
    args = ap.parse_args()

    vh = (args.vh or "").strip().replace(" ", "")
    vl = (args.vl or "").strip().replace(" ", "")
    if args.vh_file:
        vh = _fasta_read_one_sequence(Path(args.vh_file))
    if args.vl_file:
        vl = _fasta_read_one_sequence(Path(args.vl_file))

    if len(vh) < 80 or len(vl) < 80:
        print("ERROR: VH/VL too short or missing. Provide --vh/--vl or --vh-file/--vl-file.",
              file=sys.stderr)
        return 2

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[ABB2 test] VH={len(vh)} aa  VL={len(vl)} aa")
    t0 = time.perf_counter()
    try:
        res = _run_abodybuilder2(vh, vl)
    except Exception as e:
        res = {"error": str(e)}
    elapsed = round(time.perf_counter() - t0, 1)

    row: Dict[str, Any] = {
        "tool": "ABodyBuilder2",
        "elapsed_sec": elapsed,
        "ok": "error" not in res and res.get("structure_computed"),
        "plddt": res.get("plddt"),
        "vh_vl_angle_deg": res.get("vh_vl_angle_deg"),
        "error": res.get("error"),
        "pdb_saved": None,
    }

    src_pdb = res.get("pdb_path")
    if row["ok"] and src_pdb and Path(str(src_pdb)).is_file():
        dst = out_dir / "fv_abodybuilder2.pdb"
        shutil.copy2(src_pdb, dst)
        row["pdb_saved"] = str(dst.resolve())
        print(f"  [✓] pLDDT={row['plddt']}  angle={row['vh_vl_angle_deg']}°  → {dst.name}")
    else:
        print(f"  [✗] {row['error']}", file=sys.stderr)

    summary = {
        "vh_length": len(vh),
        "vl_length": len(vl),
        "run": row,
    }

    out_json = out_dir / "fv_structure_test.json"
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nWrote {out_json}", file=sys.stderr)
    return 0 if row["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
