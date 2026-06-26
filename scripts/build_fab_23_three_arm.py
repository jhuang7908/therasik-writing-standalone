#!/usr/bin/env python3
"""
 23  3-arm  VH+CH1、VL+CL， Fab 。

3-arm =  (4_two_arms_common_LC)   3  (3_other)。
：H1+CH1, H2+CH1, L+CL（L ）。

: data/design_rules/igg_like_75_sequence_stats.json, thera_export.xlsx,
      data/germlines/fc_aa/human/ IGHC + IGKC ( IGLC)
: data/design_rules/igg_like_23_three_arm_fab.json,  FASTA 

Usage:
  python scripts/build_fab_23_three_arm.py
"""

import json
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "design_rules"
THERA_XLSX = PROJECT_ROOT / "data" / "thera_sabdab" / "thera_export.xlsx"
STATS_JSON = DATA_DIR / "igg_like_75_sequence_stats.json"
GERMLINE_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa" / "human"
OUT_JSON = DATA_DIR / "igg_like_23_three_arm_fab.json"
OUT_FASTA_DIR = DATA_DIR / "igg_like_23_three_arm_fab_fasta"

# 3-arm  chain_class
THREE_ARM_CLASSES = {"4_two_arms_common_LC", "3_other"}

COL_H1 = "HeavySequence"
COL_L1 = "LightSequence"
COL_H2 = "HeavySequence(ifbispec)"
COL_L2 = "LightSequence(ifbispec)"


def _valid_seq(s) -> bool:
    if s is None or not isinstance(s, str):
        return False
    t = s.strip()
    return len(t) > 10 and set(t.upper()) <= set("ACDEFGHIKLMNPQRSTVWY")


def _read_first_fasta_sequence(path: Path, name_contains: str = "") -> str:
    """Read first FASTA entry whose header contains name_contains; return sequence (single line)."""
    raw = path.read_text(encoding="utf-8", errors="ignore")
    seqs = []
    current_header = ""
    current_seq = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if current_header and current_seq:
                seqs.append((current_header, "".join(current_seq)))
            current_header = line[1:]
            current_seq = []
        else:
            current_seq.append(line)
    if current_header and current_seq:
        seqs.append((current_header, "".join(current_seq)))
    for header, seq in seqs:
        if name_contains in header:
            return seq
    if seqs and not name_contains:
        return seqs[0][1]
    return ""


def load_ch1_cl():
    """Load CH1 (human IGHG1*01) and CL (human IGKC*01) as single-letter sequences."""
    ighc = GERMLINE_DIR / "IGHC_human.fasta"
    igkc = GERMLINE_DIR / "IGKC_human.fasta"
    if not ighc.exists():
        raise FileNotFoundError(f"Not found: {ighc}")
    if not igkc.exists():
        raise FileNotFoundError(f"Not found: {igkc}")
    ch1 = _read_first_fasta_sequence(ighc, "CH1")
    cl = _read_first_fasta_sequence(igkc, "IGKC")
    ch1 = re.sub(r"\s+", "", ch1)
    cl = re.sub(r"\s+", "", cl)
    if len(ch1) < 90:
        raise ValueError(f"CH1 too short: {len(ch1)} aa from {ighc}")
    if len(cl) < 90:
        raise ValueError(f"CL too short: {len(cl)} aa from {igkc}")
    return ch1, cl


def main():
    with open(STATS_JSON, encoding="utf-8") as f:
        stats = json.load(f)
    three_arm_ids = [
        r["antibody_id"]
        for r in stats["per_antibody"]
        if r.get("chain_class") in THREE_ARM_CLASSES
    ]
    print(f"3-arm antibodies: {len(three_arm_ids)}")

    if not THERA_XLSX.exists():
        raise FileNotFoundError(f"Not found: {THERA_XLSX}")
    df = pd.read_excel(THERA_XLSX)
    df["Therapeutic_Clean"] = df["Therapeutic"].astype(str).str.strip()
    thera_by_id = {}
    for aid in three_arm_ids:
        rows = df[df["Therapeutic_Clean"] == aid]
        if not rows.empty:
            thera_by_id[aid] = rows.iloc[0]

    ch1_seq, cl_seq = load_ch1_cl()
    print(f"CH1 length: {len(ch1_seq)}, CL length: {len(cl_seq)}")

    results = []
    for aid in sorted(three_arm_ids):
        row = thera_by_id.get(aid)
        if row is None:
            results.append({
                "antibody_id": aid,
                "error": "no_row_in_thera",
                "heavy_fab_1": None,
                "heavy_fab_2": None,
                "light_fab": None,
            })
            continue
        h1 = row.get(COL_H1)
        l1 = row.get(COL_L1)
        h2 = row.get(COL_H2)
        l2 = row.get(COL_L2)
        if not _valid_seq(h1):
            results.append({
                "antibody_id": aid,
                "error": "missing_or_invalid_h1",
                "heavy_fab_1": None,
                "heavy_fab_2": None,
                "light_fab": None,
            })
            continue
        # 3-arm:  L1==L2， L1；3_other  L1  L2
        if _valid_seq(l1):
            light_v = str(l1).strip()
        elif _valid_seq(l2):
            light_v = str(l2).strip()
        else:
            results.append({
                "antibody_id": aid,
                "error": "missing_light_chain",
                "heavy_fab_1": None,
                "heavy_fab_2": None,
                "light_fab": None,
            })
            continue
        if not _valid_seq(h2):
            results.append({
                "antibody_id": aid,
                "error": "missing_or_invalid_h2",
                "heavy_fab_1": None,
                "heavy_fab_2": None,
                "light_fab": None,
            })
            continue
        h1_s = str(h1).strip()
        h2_s = str(h2).strip()
        heavy_fab_1 = h1_s + ch1_seq
        heavy_fab_2 = h2_s + ch1_seq
        light_fab = light_v + cl_seq
        results.append({
            "antibody_id": aid,
            "error": None,
            "heavy_fab_1": heavy_fab_1,
            "heavy_fab_2": heavy_fab_2,
            "light_fab": light_fab,
            "chain_lengths": {
                "heavy_fab_1": len(heavy_fab_1),
                "heavy_fab_2": len(heavy_fab_2),
                "light_fab": len(light_fab),
            },
            "v_only": {
                "VH1_len": len(h1_s),
                "VH2_len": len(h2_s),
                "VL_len": len(light_v),
            },
        })
    out = {
        "meta": {
            "source": "igg_like_75_sequence_stats.json (3-arm) + thera_export.xlsx + IGHC/IGKC germline",
            "description": "23 three-arm bispecific: VH+CH1, VL+CL concatenated (one CH1, one CL shared).",
            "ch1_source": "Human IGHG1*01 CH1 (first in IGHC_human.fasta)",
            "cl_source": "Human IGKC*01 (first in IGKC_human.fasta)",
        },
        "per_antibody": results,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Written: {OUT_JSON}")

    # Optional: write one FASTA per antibody (3 sequences: H1_fab, H2_fab, L_fab)
    OUT_FASTA_DIR.mkdir(parents=True, exist_ok=True)
    for rec in results:
        if rec.get("error"):
            continue
        aid = rec["antibody_id"]
        fpath = OUT_FASTA_DIR / f"{aid}_fab.fasta"
        lines = [
            f">{aid}_heavy_fab_1",
            rec["heavy_fab_1"],
            f">{aid}_heavy_fab_2",
            rec["heavy_fab_2"],
            f">{aid}_light_fab",
            rec["light_fab"],
        ]
        fpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ok = sum(1 for r in results if not r.get("error"))
    err = [r["antibody_id"] for r in results if r.get("error")]
    print(f"Success: {ok}/23. FASTA dir: {OUT_FASTA_DIR}")
    if err:
        print(f"Errors: {err}")


if __name__ == "__main__":
    main()
