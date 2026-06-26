#!/usr/bin/env python3
"""
 23  3-arm  Fab （QC）。

：、V/C 、C  germline 。
: data/design_rules/igg_like_23_three_arm_fab.json, IGHC/IGKC germline
: data/design_rules/igg_like_23_three_arm_fab_qc.json + 

Usage:
  python scripts/qc_fab_23_three_arm.py
"""

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "design_rules"
FAB_JSON = DATA_DIR / "igg_like_23_three_arm_fab.json"
GERMLINE_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa" / "human"
OUT_QC_JSON = DATA_DIR / "igg_like_23_three_arm_fab_qc.json"

# （，Kabat VH/VL ）
VH_LEN_MIN, VH_LEN_MAX = 100, 150
VL_LEN_MIN, VL_LEN_MAX = 95, 125
CH1_LEN_EXPECT = 98
CL_LEN_EXPECT = 107
HEAVY_FAB_LEN_MIN, HEAVY_FAB_LEN_MAX = 200, 250
LIGHT_FAB_LEN_MIN, LIGHT_FAB_LEN_MAX = 200, 230
VALID_AA = set("ACDEFGHIKLMNPQRSTVWY")


def _read_first_fasta_sequence(path: Path, name_contains: str = "") -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    seqs = []
    current_header, current_seq = "", []
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
            return re.sub(r"\s+", "", seq)
    return seqs[0][1] if seqs else ""


def run_qc_one(rec: dict, ch1_ref: str, cl_ref: str) -> dict:
    """Single antibody QC. Returns dict with pass/warn/fail and details."""
    aid = rec.get("antibody_id", "")
    out = {"antibody_id": aid, "overall": "pass", "checks": {}, "warnings": [], "errors": []}
    if rec.get("error"):
        out["overall"] = "fail"
        out["errors"].append(f"build_error: {rec['error']}")
        return out
    h1 = rec.get("heavy_fab_1") or ""
    h2 = rec.get("heavy_fab_2") or ""
    light = rec.get("light_fab") or ""
    lens = rec.get("chain_lengths") or {}
    v_only = rec.get("v_only") or {}

    # 1) 
    for name, seq in [("heavy_fab_1", h1), ("heavy_fab_2", h2), ("light_fab", light)]:
        if not seq:
            out["errors"].append(f"{name}: empty")
            continue
        bad = set(c.upper() for c in seq if c.upper() not in VALID_AA)
        if bad:
            out["errors"].append(f"{name}: invalid_aa {bad}")
        out["checks"][f"{name}_valid_aa"] = len(bad) == 0

    # 2) C  germline （）
    if len(h1) >= len(ch1_ref) and ch1_ref:
        suffix_h1 = h1[-len(ch1_ref):]
        out["checks"]["heavy_fab_1_C_matches_CH1"] = suffix_h1 == ch1_ref
        if suffix_h1 != ch1_ref:
            out["warnings"].append("heavy_fab_1 C-terminal does not match reference CH1")
    if len(h2) >= len(ch1_ref) and ch1_ref:
        suffix_h2 = h2[-len(ch1_ref):]
        out["checks"]["heavy_fab_2_C_matches_CH1"] = suffix_h2 == ch1_ref
        if suffix_h2 != ch1_ref:
            out["warnings"].append("heavy_fab_2 C-terminal does not match reference CH1")
    if len(light) >= len(cl_ref) and cl_ref:
        suffix_l = light[-len(cl_ref):]
        out["checks"]["light_fab_C_matches_CL"] = suffix_l == cl_ref
        if suffix_l != cl_ref:
            out["warnings"].append("light_fab C-terminal does not match reference CL")

    # 3) V 
    vh1_len = v_only.get("VH1_len") or (len(h1) - len(ch1_ref) if h1 and ch1_ref else 0)
    vh2_len = v_only.get("VH2_len") or (len(h2) - len(ch1_ref) if h2 and ch1_ref else 0)
    vl_len = v_only.get("VL_len") or (len(light) - len(cl_ref) if light and cl_ref else 0)
    out["checks"]["VH1_len_plausible"] = VH_LEN_MIN <= vh1_len <= VH_LEN_MAX
    out["checks"]["VH2_len_plausible"] = VH_LEN_MIN <= vh2_len <= VH_LEN_MAX
    out["checks"]["VL_len_plausible"] = VL_LEN_MIN <= vl_len <= VL_LEN_MAX
    if not (VH_LEN_MIN <= vh1_len <= VH_LEN_MAX):
        out["warnings"].append(f"VH1_len={vh1_len} outside [{VH_LEN_MIN},{VH_LEN_MAX}]")
    if not (VH_LEN_MIN <= vh2_len <= VH_LEN_MAX):
        out["warnings"].append(f"VH2_len={vh2_len} outside [{VH_LEN_MIN},{VH_LEN_MAX}]")
    if not (VL_LEN_MIN <= vl_len <= VL_LEN_MAX):
        out["warnings"].append(f"VL_len={vl_len} outside [{VL_LEN_MIN},{VL_LEN_MAX}]")

    # 4) Fab 
    lh1, lh2, ll = len(h1), len(h2), len(light)
    out["checks"]["heavy_fab_1_len_plausible"] = HEAVY_FAB_LEN_MIN <= lh1 <= HEAVY_FAB_LEN_MAX
    out["checks"]["heavy_fab_2_len_plausible"] = HEAVY_FAB_LEN_MIN <= lh2 <= HEAVY_FAB_LEN_MAX
    out["checks"]["light_fab_len_plausible"] = LIGHT_FAB_LEN_MIN <= ll <= LIGHT_FAB_LEN_MAX
    if not (HEAVY_FAB_LEN_MIN <= lh1 <= HEAVY_FAB_LEN_MAX):
        out["warnings"].append(f"heavy_fab_1 len={lh1} outside [{HEAVY_FAB_LEN_MIN},{HEAVY_FAB_LEN_MAX}]")
    if not (HEAVY_FAB_LEN_MIN <= lh2 <= HEAVY_FAB_LEN_MAX):
        out["warnings"].append(f"heavy_fab_2 len={lh2} outside [{HEAVY_FAB_LEN_MIN},{HEAVY_FAB_LEN_MAX}]")
    if not (LIGHT_FAB_LEN_MIN <= ll <= LIGHT_FAB_LEN_MAX):
        out["warnings"].append(f"light_fab len={ll} outside [{LIGHT_FAB_LEN_MIN},{LIGHT_FAB_LEN_MAX}]")

    if out["errors"]:
        out["overall"] = "fail"
    elif out["warnings"]:
        out["overall"] = "warn"
    return out


def main():
    if not FAB_JSON.exists():
        raise FileNotFoundError(f"Not found: {FAB_JSON}")
    with open(FAB_JSON, encoding="utf-8") as f:
        fab = json.load(f)
    ch1_ref = _read_first_fasta_sequence(GERMLINE_DIR / "IGHC_human.fasta", "CH1")
    cl_ref = _read_first_fasta_sequence(GERMLINE_DIR / "IGKC_human.fasta", "IGKC")
    ch1_ref = ch1_ref[:CH1_LEN_EXPECT] if len(ch1_ref) >= CH1_LEN_EXPECT else ch1_ref
    cl_ref = cl_ref[:CL_LEN_EXPECT] if len(cl_ref) >= CL_LEN_EXPECT else cl_ref

    qc_results = []
    for rec in fab.get("per_antibody", []):
        qc_results.append(run_qc_one(rec, ch1_ref, cl_ref))

    summary = {"pass": 0, "warn": 0, "fail": 0}
    for r in qc_results:
        summary[r["overall"]] = summary.get(r["overall"], 0) + 1

    out = {
        "meta": {
            "source": str(FAB_JSON),
            "description": "QC for 23 three-arm Fab concatenated sequences",
            "checks": [
                "valid_aa: only ACDEFGHIKLMNPQRSTVWY",
                "C_terminus: heavy ends with reference CH1, light with reference CL",
                "V_length: VH 100-150 aa, VL 95-125 aa",
                "Fab_length: heavy_fab 200-250 aa, light_fab 200-230 aa",
            ],
        },
        "summary": summary,
        "per_antibody": qc_results,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_QC_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("QC summary:", summary)
    print(f"Written: {OUT_QC_JSON}")
    if summary.get("warn"):
        for r in qc_results:
            if r["overall"] == "warn":
                print(f"  Warn: {r['antibody_id']}: {r['warnings']}")
    if summary.get("fail"):
        for r in qc_results:
            if r["overall"] == "fail":
                print(f"  Fail: {r['antibody_id']}: {r['errors']}")


if __name__ == "__main__":
    main()
