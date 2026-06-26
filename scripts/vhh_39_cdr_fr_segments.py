#!/usr/bin/env python3
"""
Run ANARCII (IMGT) on 39 clinical VHH and output CDR/FR segmentation for each.
Input: data/vhh_clinical_39_union/vhh_39_sequences_clinical_validated.json
Output: data/vhh_clinical_39_union/vhh_39_cdr_fr_segments.csv (and .json)

All 39 with a sequence get segment assignment (FR1, CDR1, FR2, CDR2, FR3, CDR3, FR4).
Requires: anarcii package, core.numbering.anarcii_adapter.number_sequence.
"""
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UNION_DIR = PROJECT_ROOT / "data" / "vhh_clinical_39_union"
INPUT_JSON = UNION_DIR / "vhh_39_sequences_clinical_validated.json"
OUT_CSV = UNION_DIR / "vhh_39_cdr_fr_segments.csv"
OUT_JSON = UNION_DIR / "vhh_39_cdr_fr_segments.json"

# IMGT CDR boundaries for VH (VHH)
IMGT_CDR1_START, IMGT_CDR1_END = 27, 38
IMGT_CDR2_START, IMGT_CDR2_END = 56, 65
IMGT_CDR3_START, IMGT_CDR3_END = 105, 117


def _parse_position_label(label: str) -> tuple[int, str]:
    m = re.match(r"^(\d+)([A-Z]?)$", (label or "").strip())
    if m:
        return int(m.group(1)), (m.group(2) or "")
    return 0, ""


def _region_from_pos(pos_num: int) -> str:
    if IMGT_CDR1_START <= pos_num <= IMGT_CDR1_END:
        return "CDR1"
    if IMGT_CDR2_START <= pos_num <= IMGT_CDR2_END:
        return "CDR2"
    if IMGT_CDR3_START <= pos_num <= IMGT_CDR3_END:
        return "CDR3"
    if pos_num < IMGT_CDR1_START:
        return "FR1"
    if pos_num < IMGT_CDR2_START:
        return "FR2"
    if pos_num < IMGT_CDR3_START:
        return "FR3"
    return "FR4"


def segment_sequence(seq: str):
    """Run ANARCII IMGT and return dict with FR1, CDR1, FR2, CDR2, FR3, CDR3, FR4 and lengths."""
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))
        from core.numbering.anarcii_adapter import number_sequence
    except ImportError:
        return None
    try:
        pos_to_aa, residue_table = number_sequence(seq.strip(), "imgt")
    except Exception:
        return None
    if not residue_table:
        return None
    regions = {}
    for res in residue_table:
        pos_label = res.get("position_label") or ""
        aa = res.get("aa") or ""
        pos_num, _ = _parse_position_label(pos_label)
        reg = _region_from_pos(pos_num)
        regions[reg] = regions.get(reg, "") + aa
    return {
        "FR1": regions.get("FR1", ""),
        "CDR1": regions.get("CDR1", ""),
        "FR2": regions.get("FR2", ""),
        "CDR2": regions.get("CDR2", ""),
        "FR3": regions.get("FR3", ""),
        "CDR3": regions.get("CDR3", ""),
        "FR4": regions.get("FR4", ""),
        "CDR1_len": len(regions.get("CDR1", "")),
        "CDR2_len": len(regions.get("CDR2", "")),
        "CDR3_len": len(regions.get("CDR3", "")),
    }


def main():
    with open(INPUT_JSON, encoding="utf-8") as f:
        data = json.load(f)
    rows = list(data.get("vhh", []))
    out_rows = []
    n_ok = 0
    for r in rows:
        name = r.get("Name", "")
        seq = (r.get("Sequence") or "").strip()
        seg = segment_sequence(seq) if seq else None
        if seg:
            n_ok += 1
            out_rows.append({
                "Name": name,
                "has_segment": "Y",
                "FR1": seg["FR1"],
                "CDR1": seg["CDR1"],
                "FR2": seg["FR2"],
                "CDR2": seg["CDR2"],
                "FR3": seg["FR3"],
                "CDR3": seg["CDR3"],
                "FR4": seg["FR4"],
                "CDR1_len": seg["CDR1_len"],
                "CDR2_len": seg["CDR2_len"],
                "CDR3_len": seg["CDR3_len"],
            })
        else:
            out_rows.append({
                "Name": name,
                "has_segment": "N",
                "FR1": "", "CDR1": "", "FR2": "", "CDR2": "", "FR3": "", "CDR3": "", "FR4": "",
                "CDR1_len": "", "CDR2_len": "", "CDR3_len": "",
            })

    import csv
    fieldnames = ["Name", "has_segment", "FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4",
                  "CDR1_len", "CDR2_len", "CDR3_len"]
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)
    print(f"Wrote {OUT_CSV}")

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"count": len(out_rows), "with_segment": n_ok, "segments": out_rows}, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_JSON}")
    print(f"39 VHH: {n_ok} with CDR/FR segment (IMGT).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
