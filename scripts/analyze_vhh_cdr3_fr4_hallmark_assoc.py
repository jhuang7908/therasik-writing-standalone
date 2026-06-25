#!/usr/bin/env python3
"""
Association analysis:
- Kabat hallmark residues at positions 37/44/45/47 (FR2 interface sites)
- IMGT CDR3 length (105-117) and FR4 length (118-128)

Reads: data/vhh_clinical_39_union/vhh_39_sequences_clinical_validated.json
Writes: data/vhh_clinical_39_union/vhh_assoc_cdr3_fr4_hallmarks.json
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "vhh_clinical_39_union" / "vhh_39_sequences_clinical_validated.json"
OUT_PATH = PROJECT_ROOT / "data" / "vhh_clinical_39_union" / "vhh_assoc_cdr3_fr4_hallmarks.json"

sys.path.insert(0, str(PROJECT_ROOT / "reports" / "anarci_compat"))
import anarci as anarci_module  # type: ignore


def get_numbering(seq: str, scheme: str):
    numbered, _, _ = anarci_module.anarci([("q", seq)], scheme=scheme, output=False)
    return numbered[0][0][0]


def kabat_hallmarks(num) -> dict[int, str | None]:
    want = {37: None, 44: None, 45: None, 47: None}
    for (pos, ins), aa in num:
        if aa == "-":
            continue
        if ins.strip() != "":
            continue
        if pos in want and want[pos] is None:
            want[pos] = aa
    return want


def imgt_lengths(num) -> dict[str, int]:
    # IMGT: CDR1 27-38, CDR2 56-65, CDR3 105-117, FR4 118-128
    out = {"CDR1": 0, "CDR2": 0, "CDR3": 0, "FR4": 0}
    for (pos, _ins), aa in num:
        if aa == "-":
            continue
        if 27 <= pos <= 38:
            out["CDR1"] += 1
        elif 56 <= pos <= 65:
            out["CDR2"] += 1
        elif 105 <= pos <= 117:
            out["CDR3"] += 1
        elif 118 <= pos <= 128:
            out["FR4"] += 1
    return out


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return (num / den) if den else None


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    entries = data["vhh"]

    rows = []
    for rec in entries:
        name = rec["Name"]
        seq = rec["Sequence"].strip().upper()
        k = get_numbering(seq, "kabat")
        i = get_numbering(seq, "imgt")
        h = kabat_hallmarks(k)
        L = imgt_lengths(i)
        rows.append(
            {
                "Name": name,
                "Hallmarks_Kabat": {str(p): (h[p] if h[p] is not None else "-") for p in (37, 44, 45, 47)},
                "HallmarkPattern": "".join((h[p] if h[p] is not None else "-") for p in (37, 44, 45, 47)),
                "IMGT_CDR3_len": L["CDR3"],
                "IMGT_FR4_len": L["FR4"],
                "IMGT_CDR1_len": L["CDR1"],
                "IMGT_CDR2_len": L["CDR2"],
            }
        )

    # Pattern stats
    by_pattern = defaultdict(list)
    for r in rows:
        by_pattern[r["HallmarkPattern"]].append(r["IMGT_CDR3_len"])

    pattern_stats = []
    for pat, vals in sorted(by_pattern.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        pattern_stats.append(
            {
                "pattern": pat,
                "n": len(vals),
                "cdr3_min": min(vals),
                "cdr3_max": max(vals),
                "cdr3_mean": sum(vals) / len(vals),
            }
        )

    cdr3 = [float(r["IMGT_CDR3_len"]) for r in rows]
    fr4 = [float(r["IMGT_FR4_len"]) for r in rows]

    # Position-37 aromatic vs not
    arom = set("YFW")
    arom_cdr3 = [r["IMGT_CDR3_len"] for r in rows if r["Hallmarks_Kabat"]["37"] in arom]
    non_arom_cdr3 = [r["IMGT_CDR3_len"] for r in rows if r["Hallmarks_Kabat"]["37"] not in arom]

    out = {
        "n": len(rows),
        "pearson_cdr3_vs_fr4": pearson(cdr3, fr4),
        "hallmark_pattern_cdr3_stats": pattern_stats,
        "pos37_aromatic": {"n": len(arom_cdr3), "mean_cdr3": (sum(arom_cdr3) / len(arom_cdr3)) if arom_cdr3 else None},
        "pos37_non_aromatic": {
            "n": len(non_arom_cdr3),
            "mean_cdr3": (sum(non_arom_cdr3) / len(non_arom_cdr3)) if non_arom_cdr3 else None,
        },
        "rows": rows,
    }

    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote: {OUT_PATH}")


if __name__ == "__main__":
    main()

