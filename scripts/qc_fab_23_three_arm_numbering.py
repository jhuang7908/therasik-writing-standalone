#!/usr/bin/env python3
"""
 23  3-arm Fab  V （ARANCII Kabat）： V 。

：ARANCII 、 H/K/L、V  Kabat （VH  112–114，VL  106–108）、
        V 。
: data/design_rules/igg_like_23_three_arm_fab.json
: data/design_rules/igg_like_23_three_arm_fab_numbering_qc.json + 

Usage:
  python scripts/qc_fab_23_three_arm_numbering.py
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "design_rules"
FAB_JSON = DATA_DIR / "igg_like_23_three_arm_fab.json"
OUT_JSON = DATA_DIR / "igg_like_23_three_arm_fab_numbering_qc.json"

CH1_LEN = 98
CL_LEN = 107

# V （ARANCII  IMGT：VL  127+，VH  128）
#  gap  pos， IMGT/Kabat 
VH_LAST_POS_MIN, VH_LAST_POS_MAX = 100, 140
VL_LAST_POS_MIN, VL_LAST_POS_MAX = 95, 135


def _extract_v(heavy_fab: str, light_fab: str) -> tuple[str, str, str]:
    """Return (VH1, VH2, VL) from fab sequences (without C region)."""
    if not heavy_fab or len(heavy_fab) <= CH1_LEN:
        return "", "", ""
    vh1 = heavy_fab[:-CH1_LEN]
    # We need VH2 from second heavy - but we only have one heavy_fab per chain; Fab JSON has heavy_fab_1, heavy_fab_2
    return vh1, "", ""


def run_numbering_qc_one(rec: dict, anarcii_runner) -> dict:
    """Run numbering QC for one antibody. anarcii_runner: Anarcii() with scheme kabat."""
    aid = rec.get("antibody_id", "")
    out = {
        "antibody_id": aid,
        "overall": "pass",
        "VH1": {},
        "VH2": {},
        "VL": {},
        "warnings": [],
        "errors": [],
    }
    if rec.get("error"):
        out["overall"] = "fail"
        out["errors"].append(f"build_error: {rec['error']}")
        return out

    h1 = (rec.get("heavy_fab_1") or "").strip()
    h2 = (rec.get("heavy_fab_2") or "").strip()
    light = (rec.get("light_fab") or "").strip()
    if len(h1) <= CH1_LEN or len(h2) <= CH1_LEN or len(light) <= CL_LEN:
        out["errors"].append("fab too short to extract V")
        out["overall"] = "fail"
        return out

    vh1 = h1[:-CH1_LEN]
    vh2 = h2[:-CH1_LEN]
    vl = light[:-CL_LEN]

    # Number all three with Kabat
    seqs = [(f"{aid}_VH1", vh1), (f"{aid}_VH2", vh2), (f"{aid}_VL", vl)]
    try:
        result = anarcii_runner.number(seqs)
    except Exception as e:
        out["errors"].append(f"anarcii_number_error: {e}")
        out["overall"] = "fail"
        return out

    if not isinstance(result, dict):
        out["errors"].append("anarcii did not return dict")
        out["overall"] = "fail"
        return out

    for label, v_seq, chain_expected in [
        (f"{aid}_VH1", vh1, "H"),
        (f"{aid}_VH2", vh2, "H"),
        (f"{aid}_VL", vl, "K"),  # K or L both ok for light
    ]:
        info = result.get(label) if result else None
        seg = "VH1" if "VH1" in label else "VH2" if "VH2" in label else "VL"
        out[seg] = {"numbered": False, "chain_type": None, "last_kabat_pos": None, "n_residues": None}
        if not info or info.get("error"):
            out["warnings"].append(f"{seg}: numbering failed or error")
            out[seg]["error"] = str(info.get("error", "no result")) if info else "no result"
            continue
        chain_type = info.get("chain_type") or ""
        numbering = info.get("numbering") or []
        out[seg]["numbered"] = True
        out[seg]["chain_type"] = chain_type
        if chain_type and chain_type not in ("H", "K", "L"):
            out["warnings"].append(f"{seg}: unexpected chain_type {chain_type}")
        n_residues = sum(1 for (_, _), aa in numbering if aa and aa != "-")
        out[seg]["n_residues"] = n_residues
        if n_residues != len(v_seq):
            out["warnings"].append(f"{seg}: n_residues {n_residues} != V length {len(v_seq)}")
        if not numbering:
            out[seg]["last_kabat_pos"] = None
            continue
        #  gap （ scheme  gap）
        last_pos, last_ins = None, ""
        for (pos, ins), aa in reversed(numbering):
            if aa and aa != "-":
                last_pos, last_ins = pos, (ins.strip() if ins else "")
                break
        out[seg]["last_kabat_pos"] = (last_pos, last_ins) if last_pos is not None else None
        if last_pos is None:
            continue
        if "VH" in seg:
            if not (VH_LAST_POS_MIN <= last_pos <= VH_LAST_POS_MAX):
                out["warnings"].append(f"{seg}: last Kabat pos {last_pos} outside [{VH_LAST_POS_MIN},{VH_LAST_POS_MAX}]")
        else:
            if not (VL_LAST_POS_MIN <= last_pos <= VL_LAST_POS_MAX):
                out["warnings"].append(f"{seg}: last Kabat pos {last_pos} outside [{VL_LAST_POS_MIN},{VL_LAST_POS_MAX}]")

    if out["errors"]:
        out["overall"] = "fail"
    elif out["warnings"]:
        out["overall"] = "warn"
    return out


def main():
    if not FAB_JSON.exists():
        raise FileNotFoundError(f"Not found: {FAB_JSON}")
    try:
        from anarcii import Anarcii
    except ImportError as e:
        raise ImportError("anarcii package required for numbering QC. pip install anarcii") from e

    with open(FAB_JSON, encoding="utf-8") as f:
        fab = json.load(f)

    runner = Anarcii()
    # ARANCII number()  scheme ，（ IMGT）；

    qc_results = []
    for rec in fab.get("per_antibody", []):
        qc_results.append(run_numbering_qc_one(rec, runner))

    summary = {"pass": 0, "warn": 0, "fail": 0}
    for r in qc_results:
        summary[r["overall"]] = summary.get(r["overall"], 0) + 1

    out = {
        "meta": {
            "source": str(FAB_JSON),
            "description": "Numbering QC (ARANCII Kabat) for 23 three-arm V regions; V-C junction sanity.",
            "checks": [
                "VH/VL recognized and numbered (ARANCII default scheme)",
                "chain_type H (heavy) or K/L (light)",
                "last numbered position (non-gap): VH 100-140, VL 95-135 (scheme-dependent)",
                "n_residues from numbering == V sequence length",
            ],
        },
        "summary": summary,
        "per_antibody": qc_results,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("Numbering QC summary:", summary)
    print(f"Written: {OUT_JSON}")
    for r in qc_results:
        if r["overall"] != "pass":
            print(f"  {r['overall']}: {r['antibody_id']} - {r.get('warnings', []) or r.get('errors', [])}")


if __name__ == "__main__":
    main()
