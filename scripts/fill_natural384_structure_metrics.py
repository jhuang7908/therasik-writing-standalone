#!/usr/bin/env python3
"""Fill Natural-384 VH/VL geometry and Vernier SASA metrics.

This script builds the per-antibody Vernier/CDR lookup from the existing
Natural-384 VH/VL sequences using Anarcii, then reuses the canonical
structure_metrics_humanization analyzer without invoking legacy ANARCI/HMMER.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))

from anarcii import Anarcii  # noqa: E402

from scripts.structure_metrics_humanization import (  # noqa: E402
    KABAT_CDR_VH,
    KABAT_CDR_VL,
    VERNIER_KABAT_VH,
    VERNIER_KABAT_VL,
    analyze_structure,
    metrics_to_dict,
)

IN_CSV = SUITE / "data" / "natural_380_atlas" / "master_table.csv"
OUT_CSV = IN_CSV
STRUCT_COLS = [
    "vh_vl_angle_deg",
    "interface_n_pairs",
    "interface_mean_dist_A",
    "interface_min_dist_A",
    "vernier_sasa_total",
]


def _number_kabat(engine: Anarcii, seq_id: str, seq: str) -> List:
    result = engine.number([(seq_id, seq)])
    try:
        result = engine.to_scheme("kabat")
    except Exception:
        pass
    entry = result.get(seq_id, {})
    return list(entry.get("numbering") or [])


def _base_pos_to_seq_index(numbering: List, positions: List[int]) -> Dict[str, int]:
    wanted = set(positions)
    out: Dict[str, int] = {}
    seq_idx = -1
    for (pos, ins), aa in numbering:
        if aa == "-":
            continue
        seq_idx += 1
        if ins in ("", " ") and pos in wanted:
            out[str(pos)] = seq_idx
    return out


def _cdr_indices(numbering: List, ranges: Dict[str, Tuple[int, int]]) -> Dict[str, List[int]]:
    out: Dict[str, List[int]] = {k: [] for k in ranges}
    seq_idx = -1
    for (pos, _ins), aa in numbering:
        if aa == "-":
            continue
        seq_idx += 1
        for name, (lo, hi) in ranges.items():
            if lo <= pos <= hi:
                out[name].append(seq_idx)
                break
    return out


def _lookup_for_row(engine: Anarcii, row: Dict[str, str]) -> Dict[str, Any]:
    vh_num = _number_kabat(engine, row["antibody_id"] + "_H", row["vh_seq"])
    vl_num = _number_kabat(engine, row["antibody_id"] + "_L", row["vl_seq"])
    return {
        "canonical": {
            "H1": row.get("canonical_H1", ""),
            "H2": row.get("canonical_H2", ""),
            "H3": row.get("canonical_H3", ""),
            "L1": row.get("canonical_L1", ""),
            "L2": row.get("canonical_L2", ""),
            "L3": row.get("canonical_L3", ""),
        },
        "VH": _base_pos_to_seq_index(vh_num, VERNIER_KABAT_VH),
        "VL": _base_pos_to_seq_index(vl_num, VERNIER_KABAT_VL),
        "VH_cdr_indices": _cdr_indices(vh_num, KABAT_CDR_VH),
        "VL_cdr_indices": _cdr_indices(vl_num, KABAT_CDR_VL),
    }


def _fmt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.6f}".rstrip("0").rstrip(".")
    return str(v)


def main() -> int:
    rows = list(csv.DictReader(open(IN_CSV, encoding="utf-8")))
    if not rows:
        print(f"ERROR: no rows in {IN_CSV}", file=sys.stderr)
        return 1

    fieldnames = list(rows[0].keys())
    for col in STRUCT_COLS:
        if col not in fieldnames:
            fieldnames.append(col)

    engine = Anarcii()
    processed = 0
    errors = 0
    for i, row in enumerate(rows, start=1):
        ab = row.get("antibody_id", "")
        pdb_str = row.get("pdb_path", "")
        pdb = SUITE / pdb_str if pdb_str and not Path(pdb_str).is_absolute() else Path(pdb_str)
        if not ab or not pdb.is_file():
            print(f"[{i}/{len(rows)}] missing PDB: {ab}")
            errors += 1
            continue
        try:
            lookup = {ab: _lookup_for_row(engine, row)}
            m = analyze_structure(pdb, chain_vh="H", chain_vl="L", vernier_lookup=lookup)
            d = metrics_to_dict(m)
            if d.get("errors"):
                print(f"[{i}/{len(rows)}] WARN {ab}: {d.get('errors')}")
            row["vh_vl_angle_deg"] = _fmt(d.get("vh_vl_angle_deg"))
            row["interface_n_pairs"] = _fmt(d.get("interface_n_pairs"))
            row["interface_mean_dist_A"] = _fmt(d.get("interface_mean_dist_A"))
            row["interface_min_dist_A"] = _fmt(d.get("interface_min_dist_A"))
            row["vernier_sasa_total"] = _fmt(d.get("vernier_sasa_total"))
            processed += 1
            if processed % 25 == 0 or processed == 1:
                print(f"[{i}/{len(rows)}] structure metrics ok x{processed}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[{i}/{len(rows)}] ERROR {ab}: {exc}", flush=True)
            errors += 1

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"Done. processed={processed}, errors={errors}, out={OUT_CSV.relative_to(SUITE)}")
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
