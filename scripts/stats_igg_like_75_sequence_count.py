#!/usr/bin/env python3
"""
 75  IgG-like （H1, L1, H2, L2 、 4 ）。

: data/thera_sabdab/thera_export.xlsx, data/design_rules/bispecific_125_igg_like.json
: data/design_rules/igg_like_75_sequence_stats.json + 

Usage:
  python scripts/stats_igg_like_75_sequence_count.py
"""

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "design_rules"
THERA_XLSX = PROJECT_ROOT / "data" / "thera_sabdab" / "thera_export.xlsx"
JSON_75 = DATA_DIR / "bispecific_125_igg_like.json"
OUT_JSON = DATA_DIR / "igg_like_75_sequence_stats.json"


def _valid_seq(s) -> bool:
    if s is None or not isinstance(s, str):
        return False
    t = s.strip()
    return len(t) > 10 and set(t.upper()) <= set("ACDEFGHIKLMNPQRSTVWY")


def main():
    with open(JSON_75, encoding="utf-8") as f:
        data = json.load(f)
    ids = set(data["antibody_ids"])

    if not THERA_XLSX.exists():
        raise FileNotFoundError(f"Not found: {THERA_XLSX}")
    df = pd.read_excel(THERA_XLSX)
    df["Therapeutic_Clean"] = df["Therapeutic"].astype(str).str.strip()
    subset = df[df["Therapeutic_Clean"].isin(ids)].copy()

    #  Therapeutic ，
    col_h1 = "HeavySequence"
    col_l1 = "LightSequence"
    col_h2 = "HeavySequence(ifbispec)"
    col_l2 = "LightSequence(ifbispec)"
    cols = [col_h1, col_l1, col_h2, col_l2]

    results = []
    for aid in sorted(ids):
        rows = subset[subset["Therapeutic_Clean"] == aid]
        if rows.empty:
            results.append({
                "antibody_id": aid,
                "n_rows": 0,
                "n_sequences": 0,
                "has_h1": False,
                "has_l1": False,
                "has_h2": False,
                "has_l2": False,
                "common_light_chain": None,
                "chain_class": "no_data",
                "note": "no row in thera_export",
            })
            continue

        # （ predict_igg_like_75_immunebuilder ）
        row = rows.iloc[0]
        h1 = row.get(col_h1)
        l1 = row.get(col_l1)
        h2 = row.get(col_h2)
        l2 = row.get(col_l2)
        has_h1 = _valid_seq(h1)
        has_l1 = _valid_seq(l1)
        has_h2 = _valid_seq(h2)
        has_l2 = _valid_seq(l2)
        n = sum([has_h1, has_l1, has_h2, has_l2])

        common_light_chain = None
        if has_l1 and has_l2:
            common_light_chain = (str(l1).strip() == str(l2).strip())

        if n == 2 and has_h1 and has_l1:
            chain_class = "2_armA_only"
        elif n == 3:
            chain_class = "3_likely_common_LC" if common_light_chain else "3_other"
        elif n == 4:
            chain_class = "4_two_arms" if not common_light_chain else "4_two_arms_common_LC"
        elif n > 4:
            chain_class = "more_than_4"
        elif n < 2:
            chain_class = "incomplete"
        else:
            chain_class = "other"

        results.append({
            "antibody_id": aid,
            "n_rows": len(rows),
            "n_sequences": n,
            "has_h1": has_h1,
            "has_l1": has_l1,
            "has_h2": has_h2,
            "has_l2": has_l2,
            "common_light_chain": common_light_chain,
            "chain_class": chain_class,
        })

    # 
    by_class = {}
    for r in results:
        c = r["chain_class"]
        by_class[c] = by_class.get(c, 0) + 1
    common_lc_true = sum(1 for r in results if r.get("common_light_chain") is True)
    common_lc_false = sum(1 for r in results if r.get("common_light_chain") is False)
    multi_row = [r["antibody_id"] for r in results if r.get("n_rows", 0) > 1]

    out = {
        "meta": {
            "source": "thera_export.xlsx + bispecific_125_igg_like.json",
            "description": "Per-antibody sequence count (H1,L1,H2,L2) and common_light_chain",
        },
        "summary": {
            "total_antibodies": len(results),
            "by_chain_class": by_class,
            "common_light_chain_true": common_lc_true,
            "common_light_chain_false": common_lc_false,
            "multi_row_in_thera": multi_row,
        },
        "per_antibody": results,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("IgG-like 75 sequence count summary", flush=True)
    print(f"  Output: {OUT_JSON}", flush=True)
    print(f"  Total: {len(results)} antibodies", flush=True)
    print("  By chain_class:", flush=True)
    for c, cnt in sorted(by_class.items(), key=lambda x: -x[1]):
        print(f"    {c}: {cnt}", flush=True)
    print(f"  Common light chain (L1==L2): {common_lc_true} yes, {common_lc_false} no", flush=True)
    if multi_row:
        print(f"  Multiple rows in thera for: {multi_row}", flush=True)


if __name__ == "__main__":
    main()
