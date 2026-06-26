#!/usr/bin/env python3
"""
 + ANARCI  Vernier  CDR ，
， PDB  ANARCI。

：data/humanization_assay/thera_human_igG_germline_analysis.xlsx（ vernier_zone_precise.xlsx）
       human_origin_mode == 'engineered_humanisation'， Name, VH, VL。
：data/humanization_assay/vernier_index_lookup.json
      { "Name": { "canonical": { "H1","H2",... }, "VH": { 71: seq_idx, ... }, "VL": { 71: seq_idx, ... },
                  "VH_cdr_indices": { "H1": [i,j], ... }, "VL_cdr_indices": { ... } } }

：python scripts/build_vernier_index_lookup.py [--excel path] [--out path]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import anarci
except ImportError:
    anarci = None

DEFAULT_EXCEL = PROJECT_ROOT / "data/humanization_assay/thera_human_igG_germline_analysis.xlsx"
OUT_JSON = PROJECT_ROOT / "data/humanization_assay/vernier_index_lookup.json"

VERNIER_KABAT_VH = [2, 27, 28, 29, 30, 48, 49, 67, 69, 71, 73, 78, 93, 94]
VERNIER_KABAT_VL = [2, 4, 36, 46, 49, 69, 71, 98]
KABAT_CDR_VH = {"H1": (26, 35), "H2": (50, 65), "H3": (95, 102)}
KABAT_CDR_VL = {"L1": (24, 34), "L2": (50, 56), "L3": (89, 97)}


def numbering_to_kabat_index(numbering_list: list, kabat_positions: list) -> dict:
    """From ANARCI numbering list [((pos, ins), aa), ...], return { kabat_pos: seq_index }."""
    out = {}
    for idx, ((pos, ins), aa) in enumerate(numbering_list):
        if (ins in (" ", "") or not ins) and pos in kabat_positions and aa != "-":
            out[int(pos)] = idx
    return out


def numbering_to_cdr_indices(numbering_list: list, cdr_ranges: dict) -> dict:
    """Return { cdr_name: [start_idx, end_idx_exclusive] } (list of seq indices in that CDR)."""
    indices = {name: [] for name in cdr_ranges}
    for idx, ((pos, ins), aa) in enumerate(numbering_list):
        if aa == "-":
            continue
        for name, (lo, hi) in cdr_ranges.items():
            if lo <= pos <= hi:
                indices[name].append(idx)
                break
    return {k: sorted(v) for k, v in indices.items() if v}


def get_canonical_from_row(row, prefix_h="H", prefix_l="L") -> dict:
    """Get canonical H1/H2/H3/L1/L2/L3 from Excel row (H1_Canonical or VH_CDR1 length-based)."""
    c = {}
    for k in ["H1", "H2", "H3", "L1", "L2", "L3"]:
        col = f"{k}_Canonical"
        if col in row.index and pd.notna(row.get(col)):
            c[k] = str(row[col]).strip()
        else:
            if k.startswith("H"):
                seg = row.get("VH_CDR1") if k == "H1" else (row.get("VH_CDR2") if k == "H2" else row.get("VH_CDR3"))
            else:
                seg = row.get("VL_CDR1") if k == "L1" else (row.get("VL_CDR2") if k == "L2" else row.get("VL_CDR3"))
            c[k] = f"{k}-{len(str(seg or ''))}-?" if seg else "?"
    return c


def run_anarci_kabat(vh_seq: str, vl_seq: str):
    """Return (numbering_h, numbering_l) from anarci with Kabat scheme."""
    if not anarci:
        return None, None
    try:
        numbered, _, _ = anarci.anarci([("H", vh_seq), ("L", vl_seq)], scheme="kabat")
        if not numbered or not numbered[0]:
            return None, None
        num_h = numbered[0][0][0] if numbered[0][0] else []
        num_l = numbered[0][1][0] if len(numbered[0]) > 1 and numbered[0][1] else []
        return num_h, num_l
    except Exception:
        return None, None


def main():
    ap = argparse.ArgumentParser(description="Build Vernier/Kabat index lookup from sequence Excel (ANARCI once per antibody)")
    ap.add_argument("--excel", default=str(DEFAULT_EXCEL), help="Excel with Name, VH, VL (engineered)")
    ap.add_argument("--out", default=str(OUT_JSON), help="Output JSON path")
    args = ap.parse_args()
    excel_path = Path(args.excel)
    out_path = Path(args.out)
    if not excel_path.is_file():
        print(f"Excel not found: {excel_path}", file=sys.stderr)
        return 1
    if not anarci:
        print("ANARCI not available (anarci shim).", file=sys.stderr)
        return 1

    df = pd.read_excel(excel_path)
    if "human_origin_mode" in df.columns:
        df = df[df["human_origin_mode"] == "engineered_humanisation"].copy()
    df = df.dropna(subset=["Name", "VH", "VL"])
    lookup = {}
    for idx, row in df.iterrows():
        name = str(row["Name"]).strip()
        vh = str(row["VH"]).strip().upper().replace(" ", "")
        vl = str(row["VL"]).strip().upper().replace(" ", "")
        if not vh or not vl:
            continue
        num_h, num_l = run_anarci_kabat(vh, vl)
        if not num_h or not num_l:
            continue
        vh_idx = numbering_to_kabat_index(num_h, VERNIER_KABAT_VH)
        vl_idx = numbering_to_kabat_index(num_l, VERNIER_KABAT_VL)
        vh_cdr = numbering_to_cdr_indices(num_h, KABAT_CDR_VH)
        vl_cdr = numbering_to_cdr_indices(num_l, KABAT_CDR_VL)
        canonical = get_canonical_from_row(row)
        lookup[name] = {
            "canonical": canonical,
            "VH": vh_idx,
            "VL": vl_idx,
            "VH_cdr_indices": vh_cdr,
            "VL_cdr_indices": vl_cdr,
        }
        if (idx + 1) % 100 == 0:
            print(f"Processed {idx + 1}/{len(df)}", flush=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(lookup, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(lookup)} entries to {out_path}")
    return 0


if __name__ == "__main__":
    exit(main())
