#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
compute_tnb_adi_graded.py
=========================
Compute GRADED (continuous tent-function) ADI for Tnb04/Tnb164 variants
using the real adi_score.py engine with VHH42 as reference.

This is the CORRECT ADI system (NOT the gate-only VHH system).
CMC values sourced from existing report v2.0 (sequences not on disk).
"""
from __future__ import annotations
import json, sys, tempfile
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE_ROOT))

from core.cmc.adi_score import compute_adi_with_breakdown, adi_interpretation

# VHH42 reference stats from vhh42_cmc_summary.md
VHH42_STATS = {
    "pI":                 {"p5": 4.79, "p25": 5.13, "p50": 8.62, "p75": 8.99, "p95": 9.08},
    "GRAVY":              {"p5":-0.481,"p25":-0.368,"p50":-0.293,"p75":-0.208,"p95":-0.106},
    "instability_index":  {"p5": 23.0, "p25": 33.6, "p50": 39.0, "p75": 44.3, "p95": 46.5},
    "net_charge_pH7":     {"p5":-3.15, "p25":-1.95, "p50":  1.8, "p75":  2.8, "p95":  3.9},
    "SAP_score":          {"p5": 0.571,"p25": 0.714,"p50": 0.714,"p75": 0.714,"p95": 0.857},
    "agg_motifs":         {"p5": 2.0,  "p25": 3.0,  "p50": 4.0,  "p75": 4.0,  "p95": 5.0},
    "deamidation_sites":  {"p5": 0.05, "p25": 1.0,  "p50": 1.5,  "p75": 2.0,  "p95": 2.0},
    "oxidation_sites":    {"p5": 4.0,  "p25": 4.0,  "p50": 5.0,  "p75": 6.0,  "p95": 6.0},
    "charge_patch_max7":  {"p5": 2.0,  "p25": 2.0,  "p50": 2.0,  "p75": 3.0,  "p95": 3.0},
    "hydro_patch_max9":   {"p5": 0.556,"p25": 0.556,"p50": 0.556,"p75": 0.639,"p95": 0.772},
    "glycosylation_sites":{"p5": 0.0,  "p25": 0.0,  "p50": 0.0,  "p75": 0.0,  "p95": 0.0},
    "isomerization_sites":{"p5": 0.0,  "p25": 1.0,  "p50": 1.0,  "p75": 2.0,  "p95": 2.0},
    "free_cys":           {"p5": 0.0,  "p25": 0.0,  "p50": 0.0,  "p75": 0.0,  "p95": 1.95},
}

# CMC data FROM existing report v2.0 (TNB_BISPECIFIC_SCFV_PAIRING_ANALYSIS.md)
# IMPORTANT: these are NOT freshly computed — sequences not on disk
# charge_patch_max7, hydro_patch_max9 are ESTIMATED (typical VHH values used as placeholder)
VARIANTS = {
    # Tnb04 panel (116 aa SARS-CoV-2 VHH)
    "Tnb04H9": {"pI": 9.0,  "net_charge_pH7": 2.8, "GRAVY": -0.28,
                "instability_index": 38.0, "SAP_score": 0.714, "agg_motifs": 4,
                "deamidation_sites": 3, "oxidation_sites": 5,
                "charge_patch_max7": 2.5, "hydro_patch_max9": 0.60,
                "glycosylation_sites": 0, "isomerization_sites": 1, "free_cys": 0,
                "_data_source": "report_v2.0", "_seq_available": False},
    "Tnb04H2": {"pI": 9.0,  "net_charge_pH7": 2.8, "GRAVY": -0.28,
                "instability_index": 37.0, "SAP_score": 0.714, "agg_motifs": 4,
                "deamidation_sites": 2, "oxidation_sites": 5,
                "charge_patch_max7": 2.5, "hydro_patch_max9": 0.60,
                "glycosylation_sites": 0, "isomerization_sites": 1, "free_cys": 0,
                "_data_source": "report_v2.0", "_seq_available": False},
    "Tnb04H4": {"pI": 9.0,  "net_charge_pH7": 2.8, "GRAVY": -0.28,
                "instability_index": 38.5, "SAP_score": 0.714, "agg_motifs": 4,
                "deamidation_sites": 3, "oxidation_sites": 5,
                "charge_patch_max7": 2.5, "hydro_patch_max9": 0.60,
                "glycosylation_sites": 0, "isomerization_sites": 1, "free_cys": 0,
                "_data_source": "report_v2.0", "_seq_available": False},
    "Tnb04H8": {"pI": 9.0,  "net_charge_pH7": 2.8, "GRAVY": -0.28,
                "instability_index": 38.5, "SAP_score": 0.714, "agg_motifs": 4,
                "deamidation_sites": 3, "oxidation_sites": 5,
                "charge_patch_max7": 2.5, "hydro_patch_max9": 0.60,
                "glycosylation_sites": 0, "isomerization_sites": 1, "free_cys": 0,
                "_data_source": "report_v2.0", "_seq_available": False},
    # Tnb164 panel (123 aa MERS-CoV VHH)
    "Tnb164H4": {"pI": 8.59, "net_charge_pH7": 2.0, "GRAVY": -0.29,
                 "instability_index": 40.0, "SAP_score": 0.714, "agg_motifs": 4,
                 "deamidation_sites": 1, "oxidation_sites": 7,
                 "charge_patch_max7": 2.0, "hydro_patch_max9": 0.60,
                 "glycosylation_sites": 0, "isomerization_sites": 1, "free_cys": 0,
                 "_data_source": "report_v2.0", "_seq_available": False},
    "Tnb164H5": {"pI": 8.03, "net_charge_pH7": 1.0, "GRAVY": -0.29,
                 "instability_index": 41.0, "SAP_score": 0.714, "agg_motifs": 4,
                 "deamidation_sites": 2, "oxidation_sites": 7,
                 "charge_patch_max7": 2.0, "hydro_patch_max9": 0.60,
                 "glycosylation_sites": 0, "isomerization_sites": 1, "free_cys": 0,
                 "_data_source": "report_v2.0", "_seq_available": False},
    "Tnb164H6": {"pI": 8.03, "net_charge_pH7": 1.0, "GRAVY": -0.29,
                 "instability_index": 41.0, "SAP_score": 0.714, "agg_motifs": 4,
                 "deamidation_sites": 2, "oxidation_sites": 7,
                 "charge_patch_max7": 2.0, "hydro_patch_max9": 0.60,
                 "glycosylation_sites": 0, "isomerization_sites": 1, "free_cys": 0,
                 "_data_source": "report_v2.0", "_seq_available": False},
    "Tnb164H2": {"pI": 7.0,  "net_charge_pH7": 0.0, "GRAVY": -0.30,
                 "instability_index": 39.0, "SAP_score": 0.714, "agg_motifs": 3,
                 "deamidation_sites": 2, "oxidation_sites": 7,
                 "charge_patch_max7": 2.0, "hydro_patch_max9": 0.60,
                 "glycosylation_sites": 0, "isomerization_sites": 1, "free_cys": 0,
                 "_data_source": "report_v2.0", "_seq_available": False},
    "Tnb164H7": {"pI": 8.03, "net_charge_pH7": 1.0, "GRAVY": -0.29,
                 "instability_index": 41.0, "SAP_score": 0.714, "agg_motifs": 4,
                 "deamidation_sites": 2, "oxidation_sites": 7,
                 "charge_patch_max7": 2.0, "hydro_patch_max9": 0.60,
                 "glycosylation_sites": 0, "isomerization_sites": 1, "free_cys": 0,
                 "_data_source": "report_v2.0", "_seq_available": False},
    "Tnb164H8": {"pI": 8.03, "net_charge_pH7": 1.0, "GRAVY": -0.29,
                 "instability_index": 41.0, "SAP_score": 0.714, "agg_motifs": 4,
                 "deamidation_sites": 2, "oxidation_sites": 7,
                 "charge_patch_max7": 2.0, "hydro_patch_max9": 0.60,
                 "glycosylation_sites": 0, "isomerization_sites": 1, "free_cys": 0,
                 "_data_source": "report_v2.0", "_seq_available": False},
}

# Write temp ref stats JSON for adi_score.py
_tmp = Path(tempfile.mktemp(suffix=".json"))
_tmp.write_text(json.dumps({"metrics": VHH42_STATS}), encoding="utf-8")

METRIC_LABELS = {
    "pI": "pI", "net_charge_pH7": "charge@7",
    "GRAVY": "GRAVY", "instability_index": "instab",
    "oxidation_sites": "oxid", "deamidation_sites": "deamid",
    "SAP_score": "SAP", "agg_motifs": "agg",
}

def main():
    print("\n" + "="*90)
    print("  Tnb04 / Tnb164 —  ADI (tent, VHH42) vs ADI")
    print("="*90)
    print(f"  :  v2.0 (, charge_patch/hydro_patch )")
    print(f"  : VHH42 (39 + 3 SAbDab VHH, vhh42_cmc_summary.md)")
    print("="*90)

    # Per-metric score table
    print(f"\n{'':12s} {'ADI':>8s} {'':>14s} | {'pI':>5s} {'charge':>8s} {'GRAVY':>7s} {'instab':>8s} {'oxid':>6s} {'deamid':>8s}")
    print("-"*90)

    results = {}
    for vid, m in VARIANTS.items():
        cmc = {k: v for k, v in m.items() if not k.startswith("_")}
        r = compute_adi_with_breakdown(cmc, ref_stats_path=_tmp)
        ms = r["metric_scores"]
        cs = r["category_scores"]
        interp = adi_interpretation(r["ADI"])
        results[vid] = r
        # Gate-based ADI (old VHH system: PASS=100, WARN=50)
        # pI=9.0 > p95(9.08)? No, just below, PASS. oxidation=7 = p95, borderline WARN
        # So gate ADI ≈ 97-100
        # Continuous ADI will be lower because pI=9.0 is between p75(8.99) and p95(9.08)
        print(f"{vid:12s} {r['ADI']:>8.1f} {interp:>14s} | "
              f"{ms.get('pI', 0):>5.1f} {cs.get('charge', 0):>8.1f} "
              f"{ms.get('GRAVY', 0):>7.1f} {ms.get('instability_index', 0):>8.1f} "
              f"{ms.get('oxidation_sites', 0):>6.1f} {ms.get('deamidation_sites', 0):>8.1f}")

    print("\n" + "="*90)
    print("  ADI")
    print("="*90)
    print("""
  [ADI — run_vhh_cmc_eval.py]
    - PASS → 100，WARN → 50，FAIL → 0
    - VHH_THRESHOLD
    - pI=9.0 < WARN9.5 → PASS(100)
    - oxidation=7 = WARN7 → WARN(50) → 
    - : ADI ≈ 97-100，，

  [ADI — adi_score.py, tent]
    - VHH42 p50(100)，
    - p50= → 100; p25/p75 → 75; p5/p95 → 40;  → 0
    - pI=9.0: VHH42 p75(8.99)~p95(9.08) → pI≈40-42
    - oxidation=7: VHH42 p95(6.0) →  → <40
    - : ADI ，
    """)

    # Highlight key metric scores
    print("\n   (ADI):")
    print(f"  {'':20s} VHH42_p50  {'Tnb04H9':>8s} {'Tnb164H4':>9s} {'Tnb164H5':>9s} {'Tnb164H2':>9s}")
    print("  " + "-"*65)
    key_metrics = [
        ("pI",               8.62, "Tnb04H9", "Tnb164H4", "Tnb164H5", "Tnb164H2"),
        ("net_charge_pH7",   1.8,  "Tnb04H9", "Tnb164H4", "Tnb164H5", "Tnb164H2"),
        ("GRAVY",           -0.29, "Tnb04H9", "Tnb164H4", "Tnb164H5", "Tnb164H2"),
        ("instability_index",39.0, "Tnb04H9", "Tnb164H4", "Tnb164H5", "Tnb164H2"),
        ("oxidation_sites",  5.0,  "Tnb04H9", "Tnb164H4", "Tnb164H5", "Tnb164H2"),
        ("deamidation_sites",1.5,  "Tnb04H9", "Tnb164H4", "Tnb164H5", "Tnb164H2"),
    ]
    for (mkey, p50, v1, v2, v3, v4) in key_metrics:
        scores = [results[v]["metric_scores"].get(mkey, 0) for v in [v1, v2, v3, v4]]
        val_map = {
            "Tnb04H9": VARIANTS[v1][mkey],
            "Tnb164H4": VARIANTS[v2][mkey],
            "Tnb164H5": VARIANTS[v3][mkey],
            "Tnb164H2": VARIANTS[v4][mkey],
        }
        print(f"  {mkey:20s} {p50:>9.2f}  "
              f"{scores[0]:>5.1f}({val_map['Tnb04H9']:>5.2f})  "
              f"{scores[1]:>5.1f}({val_map['Tnb164H4']:>5.2f})  "
              f"{scores[2]:>5.1f}({val_map['Tnb164H5']:>5.2f})  "
              f"{scores[3]:>5.1f}({val_map['Tnb164H2']:>5.2f})")

    print("\n  ⚠ : charge_patch_max7, hydro_patch_max9 ()")
    print("  ⚠ ADI\n")

    _tmp.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
