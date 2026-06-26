#!/usr/bin/env python3
"""
 50  CH1/CL，：

- CrossMab（7 ）：2  arm。Arm1  (VH1+CH1, VL1+CL)；Arm2  (VH2+CL, VL2+CH1)。
-  CrossMab（43 ）：4  arm（H-L  4  Fab）：H1L1, H1L2, H2L1, H2L2。

3-arm  build_fab_23_three_arm.py （igg_like_23_three_arm_fab.json）， 50 。

: igg_like_50_four_arm_names.txt, igg_like_50_four_arm_crossmab_stats.json,
      thera_export.xlsx, data/germlines/fc_aa/human/ IGHC + IGKC
: data/design_rules/igg_like_50_four_arm_fab.json, igg_like_50_four_arm_fab_fasta/

Usage:
  python scripts/build_fab_50_four_arm.py
"""

import json
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "design_rules"
THERA_XLSX = PROJECT_ROOT / "data" / "thera_sabdab" / "thera_export.xlsx"
NAMES_50 = DATA_DIR / "igg_like_50_four_arm_names.txt"
CROSSMAB_JSON = DATA_DIR / "igg_like_50_four_arm_crossmab_stats.json"
GERMLINE_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa" / "human"
OUT_JSON = DATA_DIR / "igg_like_50_four_arm_fab.json"
OUT_FASTA_DIR = DATA_DIR / "igg_like_50_four_arm_fab_fasta"

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


def load_50_four_arm_ids() -> list[str]:
    ids = []
    with open(NAMES_50, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                ids.append(line)
    return ids


def main():
    fifty_ids = load_50_four_arm_ids()
    with open(CROSSMAB_JSON, encoding="utf-8") as f:
        crossmab_data = json.load(f)
    crossmab_set = set(crossmab_data["crossmab"])

    if not THERA_XLSX.exists():
        raise FileNotFoundError(
            f"Not found: {THERA_XLSX}. Need thera_export.xlsx with HeavySequence, LightSequence, "
            "HeavySequence(ifbispec), LightSequence(ifbispec)."
        )
    df = pd.read_excel(THERA_XLSX)
    df["Therapeutic_Clean"] = df["Therapeutic"].astype(str).str.strip()
    thera_by_id = {}
    for aid in fifty_ids:
        rows = df[df["Therapeutic_Clean"] == aid]
        if not rows.empty:
            thera_by_id[aid] = rows.iloc[0]

    ch1_seq, cl_seq = load_ch1_cl()
    print(f"CH1 length: {len(ch1_seq)}, CL length: {len(cl_seq)}")
    print(f"CrossMab: {len(crossmab_set)}, non-CrossMab: {len(fifty_ids) - len(crossmab_set)}")

    results = []
    for aid in sorted(fifty_ids):
        row = thera_by_id.get(aid)
        if row is None:
            results.append({
                "antibody_id": aid,
                "is_crossmab": aid in crossmab_set,
                "error": "no_row_in_thera",
                "arms": [],
            })
            continue
        h1 = row.get(COL_H1)
        l1 = row.get(COL_L1)
        h2 = row.get(COL_H2)
        l2 = row.get(COL_L2)
        if not all(_valid_seq(x) for x in (h1, l1, h2, l2)):
            results.append({
                "antibody_id": aid,
                "is_crossmab": aid in crossmab_set,
                "error": "missing_or_invalid_h1_l1_h2_l2",
                "arms": [],
            })
            continue

        h1_s = str(h1).strip()
        l1_s = str(l1).strip()
        h2_s = str(h2).strip()
        l2_s = str(l2).strip()

        arms = []
        if aid in crossmab_set:
            # CrossMab: 2 arms. Arm1 standard (VH1+CH1, VL1+CL), Arm2 cross (VH2+CL, VL2+CH1)
            arms = [
                {
                    "arm_id": "Arm1",
                    "description": "standard VH+CH1, VL+CL",
                    "heavy_fab": h1_s + ch1_seq,
                    "light_fab": l1_s + cl_seq,
                },
                {
                    "arm_id": "Arm2_cross",
                    "description": "CrossMab: VH+CL, VL+CH1",
                    "heavy_fab": h2_s + cl_seq,
                    "light_fab": l2_s + ch1_seq,
                },
            ]
        else:
            # Non-CrossMab: 4 arms (H-L free pairing)
            arms = [
                {"arm_id": "H1L1", "description": "VH1+CH1, VL1+CL", "heavy_fab": h1_s + ch1_seq, "light_fab": l1_s + cl_seq},
                {"arm_id": "H1L2", "description": "VH1+CH1, VL2+CL", "heavy_fab": h1_s + ch1_seq, "light_fab": l2_s + cl_seq},
                {"arm_id": "H2L1", "description": "VH2+CH1, VL1+CL", "heavy_fab": h2_s + ch1_seq, "light_fab": l1_s + cl_seq},
                {"arm_id": "H2L2", "description": "VH2+CH1, VL2+CL", "heavy_fab": h2_s + ch1_seq, "light_fab": l2_s + cl_seq},
            ]

        results.append({
            "antibody_id": aid,
            "is_crossmab": aid in crossmab_set,
            "error": None,
            "arms": arms,
            "v_only": {"VH1_len": len(h1_s), "VL1_len": len(l1_s), "VH2_len": len(h2_s), "VL2_len": len(l2_s)},
        })

    out = {
        "meta": {
            "source": "igg_like_50_four_arm_names.txt + crossmab_stats + thera_export.xlsx + IGHC/IGKC germline",
            "description": "50 four-arm: CrossMab -> 2 arms (Arm2 CH1/CL swap); non-CrossMab -> 4 arms (H-L free pairing). All with CH1/CL added.",
            "ch1_source": "Human IGHG1*01 CH1",
            "cl_source": "Human IGKC*01",
        },
        "per_antibody": results,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Written: {OUT_JSON}")

    OUT_FASTA_DIR.mkdir(parents=True, exist_ok=True)
    for rec in results:
        if rec.get("error"):
            continue
        aid = rec["antibody_id"]
        for a in rec["arms"]:
            fpath = OUT_FASTA_DIR / f"{aid}_{a['arm_id']}.fasta"
            lines = [
                f">{aid}_{a['arm_id']}_heavy",
                a["heavy_fab"],
                f">{aid}_{a['arm_id']}_light",
                a["light_fab"],
            ]
            fpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ok = sum(1 for r in results if not r.get("error"))
    err = [r["antibody_id"] for r in results if r.get("error")]
    print(f"Success: {ok}/50. FASTA dir: {OUT_FASTA_DIR}")
    if err:
        print(f"Errors: {err}")

    n_cross = sum(1 for r in results if r.get("is_crossmab") and not r.get("error"))
    n_non = ok - n_cross
    print(f"  CrossMab (2 arms each): {n_cross}, non-CrossMab (4 arms each): {n_non}")


if __name__ == "__main__":
    main()
