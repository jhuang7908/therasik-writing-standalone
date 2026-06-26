#!/usr/bin/env python3
"""
Build 125 bispecific antibody knowledge base from slice_4.
Output: data/design_rules/bispecific_125_knowledge.json
Used by design_bispecific.py for format/target recommendation.
"""
import json
import os
from collections import Counter, defaultdict

def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    meta_path = os.path.join(base, "data", "thera_sabdab", "out", "antibody_meta_models.json")
    slices_path = os.path.join(base, "data", "thera_sabdab", "out", "reference_slices.json")
    out_path = os.path.join(base, "data", "design_rules", "bispecific_125_knowledge.json")

    with open(meta_path) as f:
        meta = json.load(f)
    with open(slices_path) as f:
        slices = json.load(f)

    bis_ids = set(slices.get("slice_4_bispecific_engineering", {}).get("antibody_ids", []))

    records = []
    for m in meta:
        aid = m.get("antibody_id")
        if aid not in bis_ids:
            continue
        fmt = m.get("format") or {}
        tgt = m.get("target") or {}
        clin = m.get("clinical") or {}
        fc = m.get("fc") or {}
        records.append({
            "antibody_id": aid,
            "format_class": fmt.get("format_class"),
            "format_raw": fmt.get("format_raw"),
            "targets": tgt.get("targets", []),
            "target_raw": tgt.get("target_raw", ""),
            "target_count": tgt.get("target_count", 0),
            "phase_bucket": clin.get("phase_bucket"),
            "phase_raw": clin.get("phase_raw"),
            "fc_isotype": fc.get("isotype_primary"),
        })

    # Demand classification
    tce, dual_tumor, immune_costim, other = [], [], [], []
    for r in records:
        tr = r.get("target_raw", "") or ""
        has_cd3 = "CD3" in tr
        has_tumor = any(x in tr for x in ["EGFR", "HER2", "PD", "CD19", "BCMA", "CD20", "MSLN", "MET", "CD274", "CD279"])
        has_costim = any(x in tr for x in ["4-1BB", "CD137", "CD28", "OX40", "GITR", "CD27", "TNFRSF"])
        if has_cd3:
            r["demand_type"] = "TCE"
            tce.append(r)
        elif has_costim and has_tumor:
            r["demand_type"] = "immune_costim"
            immune_costim.append(r)
        elif r.get("target_count", 0) >= 2 and has_tumor:
            r["demand_type"] = "dual_tumor"
            dual_tumor.append(r)
        else:
            r["demand_type"] = "other"
            other.append(r)

    # Summary stats
    format_by_demand = defaultdict(lambda: Counter())
    for r in records:
        format_by_demand[r["demand_type"]][r["format_class"]] += 1

    target_pairs_tce = Counter(r["target_raw"] for r in tce if r.get("target_raw"))

    knowledge = {
        "meta": {
            "source": "slice_4_bispecific_engineering",
            "n_total": len(records),
            "demand_counts": {
                "TCE": len(tce),
                "dual_tumor": len(dual_tumor),
                "immune_costim": len(immune_costim),
                "other": len(other),
            },
        },
        "demand_format_preference": {
            k: dict(v) for k, v in format_by_demand.items()
        },
        "tce_target_pairs_top10": [
            {"target_raw": k, "count": v} for k, v in target_pairs_tce.most_common(10)
        ],
        "records": records,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(knowledge, f, ensure_ascii=False, indent=2)

    print(f"Wrote {out_path}")
    print(f"  TCE: {len(tce)}, dual_tumor: {len(dual_tumor)}, immune_costim: {len(immune_costim)}, other: {len(other)}")
    print("  Top TCE pairs:", target_pairs_tce.most_common(5))

if __name__ == "__main__":
    main()
