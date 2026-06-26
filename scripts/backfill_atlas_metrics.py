#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Backfill missing Germline and CMC metrics for Clinical Atlas.

Usage:
  python scripts/backfill_atlas_metrics.py --atlas api/static/assets/clinical_atlas_unified.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from core.numbering.germline_quick_assign import assign_vh_vl_germlines


def normalize_seq(seq: str) -> str:
    return re.sub(r"[^A-Z]", "", (seq or "").upper())


def calculate_pi_and_charge(seq: str) -> Tuple[float | None, float | None]:
    from Bio.SeqUtils.ProtParam import ProteinAnalysis

    clean = normalize_seq(seq)
    if not clean:
        return None, None
    try:
        analyser = ProteinAnalysis(clean)
        pi = analyser.isoelectric_point()
        charge = analyser.charge_at_pH(7.0)
        return round(pi, 2), round(charge, 2)
    except Exception:
        return None, None


def calculate_instability(seq: str) -> float | None:
    from Bio.SeqUtils.ProtParam import ProteinAnalysis

    clean = normalize_seq(seq)
    if not clean:
        return None
    try:
        analyser = ProteinAnalysis(clean)
        return round(analyser.instability_index(), 2)
    except Exception:
        return None


def has_germline(item: Dict[str, Any]) -> bool:
    gl = item.get("germline") or {}
    return bool(gl.get("vh") or gl.get("vl"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill missing Germline and CMC fields in Clinical Atlas JSON.")
    parser.add_argument(
        "--atlas",
        default=str(PROJECT_ROOT / "api" / "static" / "assets" / "clinical_atlas_unified.json"),
        help="Path to atlas JSON file.",
    )
    parser.add_argument(
        "--backup",
        default=str(PROJECT_ROOT / "api" / "static" / "assets" / "clinical_atlas_unified.bak.json"),
        help="Backup output path.",
    )
    parser.add_argument("--skip-cmc", action="store_true", help="Only backfill germline.")
    args = parser.parse_args()

    atlas_path = Path(args.atlas)
    backup_path = Path(args.backup)
    if not atlas_path.exists():
        print(f"ERROR: atlas not found: {atlas_path}")
        return 1

    print(f"Loading atlas: {atlas_path}")
    data = json.loads(atlas_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print("ERROR: atlas JSON root is not a list.")
        return 1

    backup_path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
        encoding="utf-8",
    )
    print(f"Backup written: {backup_path}")

    before_gl = sum(1 for item in data if has_germline(item))
    before_cmc = sum(1 for item in data if bool(item.get("cmc")))

    gl_updates = 0
    cmc_updates = 0
    touched = 0

    for item in tqdm(data, desc="Backfilling atlas"):
        changed = False
        vh = normalize_seq(item.get("heavy_aa", ""))
        vl = normalize_seq(item.get("light_aa", ""))
        if not vh and not vl:
            continue

        gl = item.get("germline")
        if not isinstance(gl, dict):
            gl = {"vh": "", "vl": ""}
            item["germline"] = gl
            changed = True

        need_vh = bool(vh) and not str(gl.get("vh") or "").strip()
        need_vl = bool(vl) and not str(gl.get("vl") or "").strip()
        if need_vh or need_vl:
            try:
                pred = assign_vh_vl_germlines(vh, vl, "human")
                vh_name = ((pred.get("vh") or {}).get("closest_vh_germline") or "").strip()
                vl_name = ((pred.get("vl") or {}).get("closest_vl_germline") or "").strip()

                if need_vh and vh_name and vh_name.lower() != "unknown":
                    gl["vh"] = vh_name
                    changed = True
                    gl_updates += 1
                if need_vl and vl_name and vl_name.lower() != "unknown":
                    gl["vl"] = vl_name
                    changed = True
                    gl_updates += 1
            except Exception:
                pass

        if not args.skip_cmc and not item.get("cmc"):
            combined = vh + vl
            if combined:
                pi, charge = calculate_pi_and_charge(combined)
                instability = calculate_instability(combined)
                item["cmc"] = {
                    "pI": pi,
                    "net_charge_pH7": charge,
                    "hydro_patch": None,
                    "instability": instability,
                    "immuno_risk": "unknown",
                }
                changed = True
                cmc_updates += 1

        if changed:
            touched += 1

    atlas_path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
        encoding="utf-8",
    )

    after_gl = sum(1 for item in data if has_germline(item))
    after_cmc = sum(1 for item in data if bool(item.get("cmc")))
    print("Backfill done.")
    print(f"Germline coverage: {before_gl} -> {after_gl} (delta {after_gl - before_gl})")
    if args.skip_cmc:
        print(f"CMC coverage: {before_cmc} -> {before_cmc} (skip-cmc enabled)")
    else:
        print(f"CMC coverage: {before_cmc} -> {after_cmc} (delta {after_cmc - before_cmc})")
    print(f"Items touched: {touched}, germline fields updated: {gl_updates}, cmc entries added: {cmc_updates}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
