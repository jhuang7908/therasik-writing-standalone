#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/extend_vhh68_full_panel.py
==================================
Extends the 68-VHH special CMC JSON with:
  1) VHH CMC engine: risk flags, ADI, percentile ranks vs VHH42 (sequence-based; no duplicate
     scalars written into existing "general" / "vhh_specific" — new block only).
  2) Structure (apo): SASA, FR2 window hydrophobic SASA, FR2–CDR3 min distance, Rg — from
     existing ImmuneBuilder pdb_model paths.

Skips overwrite of existing top-level keys "vhh_specific" and "general".
Re-run safe: only fills missing new sections; use --force to recompute structure/eval blocks.

Usage:
  python scripts/extend_vhh68_full_panel.py
  python scripts/extend_vhh68_full_panel.py --force
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE_ROOT))

from core.cmc.vhh_cmc_engine import (  # noqa: E402
    evaluate_single_vhh,
    load_vhh_ref,
)

INDEX_PATH = SUITE_ROOT / "data" / "vhh_structural_union" / "vhh_structural_union_index.json"
CMC_PATH = SUITE_ROOT / "data" / "vhh_structural_union" / "vhh68_special_cmc_results.json"
OUT_PATH = CMC_PATH  # in-place extend; optional copy below


def _load_apo_analyze():
    apo_path = SUITE_ROOT / "reports" / "apo_vhh_metrics.py"
    spec = importlib.util.spec_from_file_location("apo_vhh_metrics", apo_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[spec.name] = mod  # required for @dataclass in exec_module
    spec.loader.exec_module(mod)
    return mod.analyze_one


def _rg_ca(pdb_path: Path) -> Optional[float]:
    """Radius of gyration (Å) from CA atoms, main chain = longest AA chain."""
    try:
        from Bio.PDB import PDBParser
    except ImportError:
        return None
    parser = PDBParser(QUIET=True)
    try:
        s = parser.get_structure("m", str(pdb_path))
    except Exception:
        return None
    best = []
    for ch in s[0]:
        ca = []
        for r in ch.get_residues():
            if r.id[0] != " ":
                continue
            if "CA" in r:
                ca.append(r["CA"].get_coord())
        if len(ca) > len(best):
            best = ca
    if len(best) < 2:
        return None
    n = len(best)
    mx = sum(p[0] for p in best) / n
    my = sum(p[1] for p in best) / n
    mz = sum(p[2] for p in best) / n
    acc = 0.0
    for p in best:
        dx, dy, dz = p[0] - mx, p[1] - my, p[2] - mz
        acc += dx * dx + dy * dy + dz * dz
    return round(math.sqrt(acc / n), 2)


def extend_entry(
    item: Dict[str, Any],
    existing: Optional[Dict[str, Any]],
    ref_stats: Dict[str, Any],
    analyze_one,
    force: bool,
) -> Dict[str, Any]:
    eid = item["id"]
    seq = (item.get("sequence") or "").strip().upper()
    pdb_rel = item.get("pdb_model")
    pdb_path = SUITE_ROOT / pdb_rel if pdb_rel else None

    if existing is None:
        out: Dict[str, Any] = {"id": eid, "source_set": item.get("source_set", "")}
    else:
        out = json.loads(json.dumps(existing))  # deep copy

    # --- VHH CMC engine eval (sequence, VHH42 reference) ---
    if force or "vhh_cmc_eval" not in out:
        ev = evaluate_single_vhh(
            eid, seq, ref_stats, skip_percentile=False
        )
        mfull = ev["metrics"]
        # Avoid duplicating scalars already present under "general" in vhh68_special_cmc_results.json
        incremental_keys = (
            "net_charge_pH7",
            "SAP_score",
            "SAP_mode",
            "agg_motifs",
            "hydro_cluster_count",
            "glycosylation_sites",
            "deamidation_sites",
            "isomerization_sites",
            "oxidation_sites",
            "free_cys",
            "_positions",
        )
        metrics_incremental = {k: mfull[k] for k in incremental_keys if k in mfull}
        out["vhh_cmc_eval"] = {
            "adi_score": ev["adi_score"],
            "adi_grade": ev["adi_grade"],
            "risk_flags": ev["risk_flags"],
            "percentile_ranks_vs_vhh42": ev["percentile_ranks_vs_vhh42"],
            "n_warn": ev["n_warn"],
            "n_fail": ev["n_fail"],
            "overall_status": ev["overall_status"],
            "pi_flag": ev["pi_flag"],
            "metrics_incremental": metrics_incremental,
        }

    # --- Structure apo metrics ---
    if force or "structure_apo" not in out:
        struct_blk: Dict[str, Any] = {}
        if pdb_path and pdb_path.is_file():
            try:
                met = analyze_one(str(pdb_path))
                d = asdict(met)
                for k, v in list(d.items()):
                    if isinstance(v, float):
                        d[k] = round(v, 4) if v is not None else None
                struct_blk["apo_metrics"] = d
                rg = _rg_ca(pdb_path)
                struct_blk["radius_of_gyration_ca_A"] = rg
                struct_blk["pdb_model_resolved"] = True
            except Exception as ex:
                struct_blk["error"] = str(ex)
                struct_blk["pdb_model_resolved"] = False
        else:
            struct_blk["pdb_model_resolved"] = False
            struct_blk["error"] = "pdb_model missing or path not found"
        out["structure_apo"] = struct_blk

    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Extend VHH68 CMC JSON with full panel blocks.")
    ap.add_argument("--force", action="store_true", help="Recompute vhh_cmc_eval and structure_apo")
    ap.add_argument(
        "--out",
        type=str,
        default="",
        help="Optional output path (default: overwrite vhh68_special_cmc_results.json)",
    )
    args = ap.parse_args()

    if not INDEX_PATH.is_file():
        print(f"Missing {INDEX_PATH}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    items: List[Dict[str, Any]] = data.get("clinical_vhh", []) + data.get("database_b", [])

    existing_list: List[Dict[str, Any]] = []
    if CMC_PATH.is_file():
        existing_list = json.loads(CMC_PATH.read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in existing_list if isinstance(e, dict) and e.get("id")}

    ref_stats = load_vhh_ref()
    analyze_one = _load_apo_analyze()

    out_list: List[Dict[str, Any]] = []
    for i, item in enumerate(items):
        eid = item["id"]
        merged = extend_entry(item, by_id.get(eid), ref_stats, analyze_one, args.force)
        out_list.append(merged)
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{len(items)}...", flush=True)

    out_path = Path(args.out) if args.out else OUT_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_list, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(out_list)} entries to {out_path}")
    print("Blocks per entry: vhh_specific, general (preserved), vhh_cmc_eval, structure_apo")


if __name__ == "__main__":
    main()
