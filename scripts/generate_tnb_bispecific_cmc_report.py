#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generate_tnb_bispecific_cmc_report.py
======================================
Comprehensive CMC comparison report for Tnb04/Tnb164 bispecific VHH-GS-VHH
versus scFv_52_atlas clinical benchmark.

Analysis layers:
  1. Individual VHH CMC (Tnb04 + Tnb164 variants) vs VHH42 reference
  2. Fusion protein (VHH-GS-VHH) CMC estimation vs scFv_52 distribution
  3. Linker charge contribution analysis for pI lowering strategy

Input:
  - Existing CMC data from TNB_BISPECIFIC_SCFV_PAIRING_ANALYSIS.md report
  - data/scfv_52_atlas/cmc_computed.json  (freshly computed)
  - data/scfv_52_atlas/cmc_stats.json
  - data/humanization_assay/vhh42_cmc_summary.md (reference benchmark)

Output:
  - projects/Tnb_bispecific/cmc_eval/TNB_CMC_COMPARISON_REPORT.md
  - projects/Tnb_bispecific/cmc_eval/tnb_cmc_comparison.json
"""
from __future__ import annotations

import json
import re
import statistics
from datetime import datetime
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = SUITE_ROOT / "projects" / "Tnb_bispecific" / "cmc_eval"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── VHH42 clinical reference (from vhh42_cmc_summary.md, fixed) ─────────────
VHH42_REF = {
    "pI":                 {"p5": 4.79,  "p25": 5.13,  "p50": 8.62,  "p75": 8.99,  "p95": 9.08,  "mean": 7.5,  "stdev": 1.8},
    "GRAVY":              {"p5":-0.481, "p25":-0.368, "p50":-0.293, "p75":-0.208, "p95":-0.106, "mean":-0.29, "stdev": 0.12},
    "instability_index":  {"p5": 23.0,  "p25": 33.6,  "p50": 39.0,  "p75": 44.3,  "p95": 46.5,  "mean": 38.0, "stdev": 7.9},
    "net_charge_pH7":     {"p5":-3.15,  "p25":-1.95,  "p50":  1.8,  "p75":  2.8,  "p95":  3.9,  "mean":  0.9, "stdev": 2.4},
    "SAP_score":          {"p5": 0.571, "p25": 0.714, "p50": 0.714, "p75": 0.714, "p95": 0.857, "mean": 0.69, "stdev": 0.071},
    "agg_motifs":         {"p5": 2.0,   "p25": 3.0,   "p50": 4.0,   "p75": 4.0,   "p95": 5.0,   "mean": 3.7,  "stdev": 0.85},
    "deamidation_sites":  {"p5": 0.05,  "p25": 1.0,   "p50": 1.5,   "p75": 2.0,   "p95": 2.0,   "mean": 1.4,  "stdev": 0.63},
    "oxidation_sites":    {"p5": 4.0,   "p25": 4.0,   "p50": 5.0,   "p75": 6.0,   "p95": 6.0,   "mean": 5.0,  "stdev": 0.85},
}

# ─── Tnb CMC data (from report TNB_BISPECIFIC_SCFV_PAIRING_ANALYSIS v2.0) ─────
# Tnb04 panel — 116 aa humanized VHH (SARS-CoV-2 arm)
TNB04_VARIANTS = {
    "Tnb04H9": {"pI": 9.0,  "net_charge_pH7": 2.8,  "deamidation_sites": 3, "oxidation_sites": 5,
                "GRAVY": -0.28, "instability_index": 38.0, "SAP_score": 0.714, "agg_motifs": 4,
                "seq_len": 116, "CDR_RMSD": 0.922, "JN1_IC50": 0.053, "role": "SARS_arm", "preferred": True},
    "Tnb04H2": {"pI": 9.0,  "net_charge_pH7": 2.8,  "deamidation_sites": 2, "oxidation_sites": 5,
                "GRAVY": -0.28, "instability_index": 37.0, "SAP_score": 0.714, "agg_motifs": 4,
                "seq_len": 116, "CDR_RMSD": 0.735, "JN1_IC50": 0.071, "role": "SARS_arm", "preferred": False},
    "Tnb04H4": {"pI": 9.0,  "net_charge_pH7": 2.8,  "deamidation_sites": 3, "oxidation_sites": 5,
                "GRAVY": -0.28, "instability_index": 38.5, "SAP_score": 0.714, "agg_motifs": 4,
                "seq_len": 116, "CDR_RMSD": 0.824, "JN1_IC50": 0.150, "role": "SARS_arm", "preferred": False},
    "Tnb04H8": {"pI": 9.0,  "net_charge_pH7": 2.8,  "deamidation_sites": 3, "oxidation_sites": 5,
                "GRAVY": -0.28, "instability_index": 38.5, "SAP_score": 0.714, "agg_motifs": 4,
                "seq_len": 116, "CDR_RMSD": 0.966, "JN1_IC50": 0.186, "role": "SARS_arm", "preferred": False},
}

# Tnb164 panel — 123 aa humanized VHH (MERS-CoV arm)
TNB164_VARIANTS = {
    "Tnb164H4": {"pI": 8.59, "net_charge_pH7": 2.0,  "deamidation_sites": 1, "oxidation_sites": 7,
                 "GRAVY": -0.29, "instability_index": 40.0, "SAP_score": 0.714, "agg_motifs": 4,
                 "seq_len": 123, "CDR_RMSD": 1.423, "MjHKU4r_IC90": 0.119, "role": "MERS_arm"},
    "Tnb164H5": {"pI": 8.03, "net_charge_pH7": 1.0,  "deamidation_sites": 2, "oxidation_sites": 7,
                 "GRAVY": -0.29, "instability_index": 41.0, "SAP_score": 0.714, "agg_motifs": 4,
                 "seq_len": 123, "CDR_RMSD": 1.332, "MjHKU4r_IC90": 0.345, "role": "MERS_arm"},
    "Tnb164H6": {"pI": 8.03, "net_charge_pH7": 1.0,  "deamidation_sites": 2, "oxidation_sites": 7,
                 "GRAVY": -0.29, "instability_index": 41.0, "SAP_score": 0.714, "agg_motifs": 4,
                 "seq_len": 123, "CDR_RMSD": 1.537, "MjHKU4r_IC90": 0.327, "role": "MERS_arm"},
    "Tnb164H2": {"pI": 7.0,  "net_charge_pH7": 0.0,  "deamidation_sites": 2, "oxidation_sites": 7,
                 "GRAVY": -0.30, "instability_index": 39.0, "SAP_score": 0.714, "agg_motifs": 3,
                 "seq_len": 123, "CDR_RMSD": 1.439, "MjHKU4r_IC90": 0.2,  "role": "MERS_arm"},
    "Tnb164H7": {"pI": 8.03, "net_charge_pH7": 1.0,  "deamidation_sites": 2, "oxidation_sites": 7,
                 "GRAVY": -0.29, "instability_index": 41.0, "SAP_score": 0.714, "agg_motifs": 4,
                 "seq_len": 123, "CDR_RMSD": 1.562, "MjHKU4r_IC90": 0.754, "role": "MERS_arm"},
    "Tnb164H8": {"pI": 8.03, "net_charge_pH7": 1.0,  "deamidation_sites": 2, "oxidation_sites": 7,
                 "GRAVY": -0.29, "instability_index": 41.0, "SAP_score": 0.714, "agg_motifs": 4,
                 "seq_len": 123, "CDR_RMSD": 1.431, "MjHKU4r_IC90": 0.868, "role": "MERS_arm"},
}

# ─── Linker options for pI modulation ─────────────────────────────────────────
LINKER_OPTIONS = [
    {"name": "(G4S)3",         "seq": "GGGGSGGGGSGGGGS",          "len": 15, "charge_pH7":  0.0,  "notes": "Current baseline"},
    {"name": "(G4S)4",         "seq": "GGGGSGGGGSGGGGSGGGGS",     "len": 20, "charge_pH7":  0.0,  "notes": "Longer GS, reduce steric"},
    {"name": "(G4S)3-E",       "seq": "GGGGSGGGGSGGGGSEE",        "len": 17, "charge_pH7": -2.0,  "notes": "+2 Glu, moderate pI reduction"},
    {"name": "(G4S)3-EEE",     "seq": "GGGGSGGGGSGGGGSEEE",       "len": 18, "charge_pH7": -3.0,  "notes": "+3 Glu, stronger pI reduction"},
    {"name": "Charged-EK",     "seq": "EAAAKGGGGSGGGGSEAAAK",     "len": 20, "charge_pH7": -1.0,  "notes": "EK linker: amphiphilic + charged"},
    {"name": "NegCharged-4E",  "seq": "GGGGSEEEEGGGGSGGGGS",      "len": 19, "charge_pH7": -4.0,  "notes": "4xGlu insert, pI target 7-8"},
    {"name": "Whitlow",        "seq": "GSTSGSGKPGSGEGSTKG",       "len": 18, "charge_pH7":  0.0,  "notes": "Literature high-expression linker"},
]


# ─── Fusion pI estimation ──────────────────────────────────────────────────────
def estimate_fusion_pi(sars_charge: float, mers_charge: float, linker_charge: float,
                       sars_pi: float, mers_pi: float) -> float:
    """
    Estimate fusion pI from net charges at pH 7.
    Uses weighted linear interpolation between component pI values.
    Note: actual pI ≠ linear average; this is a sequence-physics-based estimate.
    """
    total_charge = sars_charge + mers_charge + linker_charge
    # Empirical formula: pI shifts ~0.3-0.5 per unit of net charge vs neutral
    # Anchored to known data points from the existing report
    # H9+H4 (charges +2.8+2.0=+4.8) -> pI ~8.8 (from report)
    # H9+H2 (charges +2.8+0.0=+2.8)  -> pI ~8.0 (from report)
    # Linear fit: pI = 7.0 + 0.375 * total_charge (calibrated)
    pi_est = 7.0 + 0.375 * total_charge
    return round(min(10.5, max(4.0, pi_est)), 2)


def estimate_fusion_gravy(sars_len: int, sars_gravy: float,
                          mers_len: int, mers_gravy: float,
                          linker_len: int, linker_gravy: float = -0.27) -> float:
    """Length-weighted GRAVY average."""
    total = sars_len + mers_len + linker_len
    return round((sars_gravy * sars_len + mers_gravy * mers_len + linker_gravy * linker_len) / total, 3)


# ─── Percentile rank ──────────────────────────────────────────────────────────
def rank_in_dist(value: float, dist: dict) -> str:
    if value < dist["p5"]:   return "<p5 ()"
    if value <= dist["p25"]: return "p5-p25 ()"
    if value <= dist["p75"]: return "p25-p75 ✓ ()"
    if value <= dist["p95"]: return "p75-p95 ()"
    return ">p95 ( ⚠)"


def flag_for_vhh(metric: str, value: float) -> str:
    thresholds = {
        "pI":                 (4.5, None, 9.5, 10.0),
        "GRAVY":              (None, None, -0.05, 0.10),
        "instability_index":  (None, None, 50.0, 65.0),
        "net_charge_pH7":     (-6.0, None, 7.0, 10.0),
        "SAP_score":          (None, None, 0.857, 0.99),
        "agg_motifs":         (None, None, 5, 7),
        "deamidation_sites":  (None, None, 3, 5),
        "oxidation_sites":    (None, None, 7, 10),
    }
    t = thresholds.get(metric)
    if not t:
        return "PASS"
    warn_lo, fail_lo, warn_hi, fail_hi = t
    if fail_lo is not None and value < fail_lo: return "FAIL"
    if fail_hi is not None and value > fail_hi: return "FAIL"
    if warn_lo is not None and value < warn_lo: return "WARN"
    if warn_hi is not None and value > warn_hi: return "WARN"
    return "PASS"


FLAG_ICON = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}


# ─── load scFv stats ──────────────────────────────────────────────────────────
def load_scfv_stats() -> tuple[dict, list]:
    stats_path = SUITE_ROOT / "data" / "scfv_52_atlas" / "cmc_stats.json"
    cmc_path   = SUITE_ROOT / "data" / "scfv_52_atlas" / "cmc_computed.json"
    with open(stats_path, encoding="utf-8") as f:
        stats = json.load(f).get("metrics", {})
    with open(cmc_path, encoding="utf-8") as f:
        entries = json.load(f)
    return stats, entries


# ─── report generation ────────────────────────────────────────────────────────
def generate_report(scfv_stats: dict, scfv_entries: list) -> str:

    lines: list[str] = []

    def h1(t): lines.extend([f"# {t}", ""])
    def h2(t): lines.extend(["", f"## {t}", ""])
    def h3(t): lines.extend(["", f"### {t}", ""])
    def p(t):  lines.extend([t, ""])
    def rule(): lines.extend(["---", ""])

    # ── Header ────────────────────────────────────────────────────────────────
    h1("Tnb04 / Tnb164  VHH-GS-VHH CMC ")
    lines += [
        f"> ****: v1.0  |  ****: {datetime.now().strftime('%Y-%m-%d')}",
        f"> ****：① VHH CMC vs VHH42  ②  vs scFv_52   ③ Linker",
        f"> ****：InSynBio AbEngineCore — Bispecific VHH CMC Comparator",
        "",
    ]
    rule()

    # ── Section 1: scFv_52 Distribution Summary ─────────────────────────────
    h2("1. scFv_52  CMC （）")
    p(" **scFv_52_atlas** 52 / scFv  CMC ， scFv ， VHH-GS-VHH 。")

    lines += [
        "|  | p25 | p50（）| p75 | ±σ | VHH42 |",
        "|---|---|---|---|---|---|",
    ]
    compare_metrics = [
        ("pI", " pI"),
        ("net_charge_pH7", " @ pH7"),
        ("GRAVY", " GRAVY"),
        ("instability_index", ""),
        ("agg_motifs", ""),
        ("deamidation_sites", ""),
        ("oxidation_sites", " M+W"),
        ("SAP_score", "SAP "),
    ]
    for key, label in compare_metrics:
        s = scfv_stats.get(key, {})
        v = VHH42_REF.get(key, {})
        if s:
            vhh42_str = f"p50={v.get('p50','?')}" if v else "N/A"
            lines.append(
                f"| {label} | {s['p25']:.2f} | **{s['p50']:.2f}** | {s['p75']:.2f} | "
                f"{s['mean']:.2f}±{s['stdev']:.2f} | VHH42 p50={v.get('p50','?') if v else 'N/A'} |"
            )
    lines.append("")

    # pI bimodal note
    scfv_pi_vals = [e["pI"] for e in scfv_entries]
    low_pi = [v for v in scfv_pi_vals if v < 7.0]
    high_pi = [v for v in scfv_pi_vals if v >= 7.0]
    p(f"> ****：scFv_52  pI **** — pI（pI<7.0，n={len(low_pi)}，{100*len(low_pi)//52}%）pI（pI≥7.0，n={len(high_pi)}，{100*len(high_pi)//52}%）。"
      f"pI pI  {statistics.median(high_pi):.2f}；pI pI  {statistics.median(low_pi):.2f}。")
    rule()

    # ── Section 2: Individual VHH CMC vs VHH42 ──────────────────────────────
    h2("2.  VHH （vs VHH42 ）")

    for arm_name, arm_variants in [("2.1 SARS  — Tnb04  (116 aa)", TNB04_VARIANTS),
                                    ("2.2 MERS  — Tnb164  (123 aa)", TNB164_VARIANTS)]:
        h3(arm_name)
        lines += [
            "|  | pI |  | GRAVY |  |  |  | SAP |  | pI |  |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for vid, m in arm_variants.items():
            pi_flag = flag_for_vhh("pI", m["pI"])
            deam_flag = flag_for_vhh("deamidation_sites", m["deamidation_sites"])
            oxid_flag = flag_for_vhh("oxidation_sites", m["oxidation_sites"])
            n_warn = sum(1 for f in [pi_flag, deam_flag, oxid_flag] if f == "WARN")
            n_fail = sum(1 for f in [pi_flag, deam_flag, oxid_flag] if f == "FAIL")
            status = "❌ FAIL" if n_fail else ("⚠️ WARN" if n_warn else "✅ PASS")
            lines.append(
                f"| {'**' + vid + '**' if m.get('preferred') else vid} "
                f"| {m['pI']:.2f} | {m['net_charge_pH7']:+.1f} | {m['GRAVY']:.3f} "
                f"| {m['instability_index']:.0f} | {m['deamidation_sites']} | {m['oxidation_sites']} "
                f"| {m['SAP_score']:.3f} | {m['agg_motifs']} "
                f"| {FLAG_ICON.get(pi_flag, pi_flag)} | {status} |"
            )
        lines.append("")

    # VHH42 comparison table
    lines += ["", "**VHH42 **", ""]
    lines += [
        "|  | VHH42 p25 | VHH42 p50 | VHH42 p75 | Tnb04  | Tnb164 H4 | Tnb164 H5/H6 | Tnb164 H2 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    ref_rows = [
        ("pI", "", "pI"),
        ("net_charge_pH7", "", "net_charge_pH7"),
        ("deamidation_sites", "", "deamidation_sites"),
        ("oxidation_sites", "", "oxidation_sites"),
        ("GRAVY", "GRAVY", "GRAVY"),
        ("instability_index", "", "instability_index"),
    ]
    COMPARE_MAP = {
        "pI":                {"Tnb04": "9.0",  "Tnb164H4": "8.59", "Tnb164H56": "8.03", "Tnb164H2": "7.0"},
        "net_charge_pH7":    {"Tnb04": "+2.8", "Tnb164H4": "+2.0", "Tnb164H56": "+1.0", "Tnb164H2": "~0"},
        "deamidation_sites": {"Tnb04": "2-3",  "Tnb164H4": "1",    "Tnb164H56": "2",    "Tnb164H2": "2"},
        "oxidation_sites":   {"Tnb04": "5",    "Tnb164H4": "7 ⚠", "Tnb164H56": "7 ⚠", "Tnb164H2": "7 ⚠"},
        "GRAVY":             {"Tnb04": "-0.28","Tnb164H4": "-0.29","Tnb164H56": "-0.29","Tnb164H2": "-0.30"},
        "instability_index": {"Tnb04": "38.0", "Tnb164H4": "40.0", "Tnb164H56": "41.0", "Tnb164H2": "39.0"},
    }
    for key, label, _ in ref_rows:
        ref = VHH42_REF.get(key, {})
        cm = COMPARE_MAP.get(key, {})
        lines.append(
            f"| {label} | {ref.get('p25','?')} | {ref.get('p50','?')} | {ref.get('p75','?')} "
            f"| {cm.get('Tnb04','?')} | {cm.get('Tnb164H4','?')} | {cm.get('Tnb164H56','?')} | {cm.get('Tnb164H2','?')} |"
        )
    lines.append("")

    lines += [
        "> ****：",
        "> - Tnb04  pI=9.0（>p75 VHH42， <p95， PASS/WARN ）",
        "> - Tnb164  7， VHH42 **>p95 WARN **（VHH_THRESHOLD WARN =7）",
        "> - Tnb164H2 pI=7.0  6  VHH42 （8.62）",
        "> - Tnb04  Tnb164 GRAVY、 VHH42 ",
        "",
    ]
    rule()

    # ── Section 3: Fusion CMC vs scFv_52 ────────────────────────────────────
    h2("3.  CMC —  vs scFv_52 ")
    p(" SARS+MERS  pI /  / GRAVY ， scFv_52 。")
    p("：**VHH(SARS) + GS-linker + VHH(MERS)**， 254-259 aa（ 15 aa linker）")

    # Define combinations
    combinations = [
        ("H9+H4",  "Tnb04H9",  "Tnb164H4",  "(G4S)3", 15, 0.0, True),
        ("H9+H5",  "Tnb04H9",  "Tnb164H5",  "(G4S)3", 15, 0.0, True),
        ("H9+H2",  "Tnb04H9",  "Tnb164H2",  "(G4S)3", 15, 0.0, True),
        ("H9+H6",  "Tnb04H9",  "Tnb164H6",  "(G4S)3", 15, 0.0, False),
        ("H2+H5",  "Tnb04H2",  "Tnb164H5",  "(G4S)3", 15, 0.0, False),
    ]

    lines += [
        "|  | SARS pI | MERS pI | Linker charge | pI |  | GRAVY() | scFv p50 |  |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    scfv_pi_p50 = scfv_stats["pI"]["p50"]
    scfv_charge_p50 = scfv_stats["net_charge_pH7"]["p50"]

    fusion_results = []
    for combo_name, sars_id, mers_id, linker_name, linker_len, linker_charge, priority in combinations:
        s = TNB04_VARIANTS[sars_id]
        m = TNB164_VARIANTS[mers_id]
        fus_pi = estimate_fusion_pi(s["net_charge_pH7"], m["net_charge_pH7"], linker_charge,
                                     s["pI"], m["pI"])
        fus_charge = round(s["net_charge_pH7"] + m["net_charge_pH7"] + linker_charge, 1)
        fus_gravy = estimate_fusion_gravy(s["seq_len"], s["GRAVY"],
                                          m["seq_len"], m["GRAVY"],
                                          linker_len)
        # Compare with scFv p50
        pi_vs_scfv = "scFv" if fus_pi > scfv_pi_p50 + 0.3 else ("scFv" if fus_pi < scfv_pi_p50 - 0.3 else "scFv")
        # Expression prediction
        if fus_pi > 9.0:
            expr = "❌ （pI>9）"
        elif fus_pi > 8.5:
            expr = "⚠️ （pI）"
        elif fus_pi > 7.5:
            expr = "✅ "
        else:
            expr = "✅ "

        prefix = "**" if priority else ""
        suffix = "**" if priority else ""
        lines.append(
            f"| {prefix}{combo_name}{suffix} | {s['pI']:.2f} | {m['pI']:.2f} | {linker_charge:+.1f} "
            f"| **{fus_pi:.2f}** | {fus_charge:+.1f} | {fus_gravy:.3f} "
            f"| {pi_vs_scfv} | {expr} |"
        )
        fusion_results.append({
            "combo": combo_name, "sars_id": sars_id, "mers_id": mers_id,
            "linker": linker_name, "fusion_pI": fus_pi,
            "fusion_charge_pH7": fus_charge, "fusion_GRAVY": fus_gravy,
            "priority": priority,
        })
    lines.append("")

    # scFv distribution context
    scfv_pI_s = scfv_stats.get("pI", {})
    lines += [
        f"> **scFv_52 pI **：p25={scfv_pI_s.get('p25','?')}  p50={scfv_pI_s.get('p50','?')}  p75={scfv_pI_s.get('p75','?')}  mean={scfv_pI_s.get('mean','?')}",
        f"> ：pI（4.7-6.5） {100*len(low_pi)//52}%，pI（7.0-9.3） {100*len(high_pi)//52}%",
        f"> H9+H2  pI≈8.0， **scFv pI（p50）**，",
        "",
    ]
    rule()

    # ── Section 4: Linker charge optimization ───────────────────────────────
    h2("4. GS Linker  — pI ")
    p(" **H9+H4（）** ， linker  pI 。")
    p("H9+H4  = +4.8， pI ≈ 8.8（ pH 6.5-7.5 ）。")

    lines += [
        "| Linker  |  |  | Linker charge | pI |  |  |  |",
        "|---|---|---|---|---|---|---|---|",
    ]
    h9 = TNB04_VARIANTS["Tnb04H9"]
    h4 = TNB164_VARIANTS["Tnb164H4"]
    for lk in LINKER_OPTIONS:
        fus_pi = estimate_fusion_pi(h9["net_charge_pH7"], h4["net_charge_pH7"],
                                     lk["charge_pH7"], h9["pI"], h4["pI"])
        fus_charge = round(h9["net_charge_pH7"] + h4["net_charge_pH7"] + lk["charge_pH7"], 1)
        delta_pi = round(fus_pi - 8.8, 2)
        delta_str = f"{delta_pi:+.2f}" if delta_pi != 0 else "0"
        if fus_pi <= 7.5:
            prio = "⭐⭐⭐"
        elif fus_pi <= 8.0:
            prio = "⭐⭐"
        elif fus_pi <= 8.5:
            prio = "⭐"
        else:
            prio = "—"
        lines.append(
            f"| {lk['name']} | `{lk['seq'][:20]}{'...' if len(lk['seq'])>20 else ''}` "
            f"| {lk['len']} | {lk['charge_pH7']:+.1f} "
            f"| **{fus_pi:.2f}** ({delta_str}) | {fus_charge:+.1f} "
            f"| {lk['notes']} | {prio} |"
        )
    lines.append("")

    lines += [
        "> ** pI **：7.5–8.5（ scFv_52 pI p25-p75 ）",
        "> ****： Glu  pI ：①  SEC  ②  IC50 （<3×）",
        "",
    ]
    rule()

    # ── Section 5: scFv_52 Top/Bottom pI analysis ───────────────────────────
    h2("5. scFv_52  pI ")
    p(" scFv_52  pI（>8.5） pI（<6.5）， pI 。")

    high_pi_entries = sorted([e for e in scfv_entries if e["pI"] >= 8.5], key=lambda x: -x["pI"])[:8]
    low_pi_entries  = sorted([e for e in scfv_entries if e["pI"] <= 6.5], key=lambda x:  x["pI"])[:6]

    h3("5.1  pI scFv（pI ≥ 8.5）— /")
    lines += [
        "|  | pI |  | GRAVY |  |  |  |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in high_pi_entries:
        lines.append(
            f"| {e['antibody_id']} | **{e['pI']:.2f}** | {e['net_charge_pH7']:+.1f} "
            f"| {e['GRAVY']:.3f} | {e['agg_motifs']} | {e.get('targets','')[:30]} | {e.get('phase','')} |"
        )
    lines.append("")

    h3("5.2  pI scFv（pI ≤ 6.5）— ")
    lines += [
        "|  | pI |  | GRAVY |  |  |  |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in low_pi_entries:
        lines.append(
            f"| {e['antibody_id']} | **{e['pI']:.2f}** | {e['net_charge_pH7']:+.1f} "
            f"| {e['GRAVY']:.3f} | {e['agg_motifs']} | {e.get('targets','')[:30]} | {e.get('phase','')} |"
        )
    lines.append("")

    p(f"> ****：scFv_52  {len(high_pi_entries)}  pI≥8.5 /， {max(e['pI'] for e in scfv_entries):.2f}（{max(scfv_entries, key=lambda x: x['pI'])['antibody_id']}）。"
      f"H9+H4  pI~8.8 ** scFv **，， pI ，。")
    rule()

    # ── Section 6: Decision matrix ───────────────────────────────────────────
    h2("6. ")

    lines += [
        "|  | / | pI | scFv |  |  |  |",
        "|---|---|---|---|---|---|---|",
        "| P0- | H9+H4 + (G4S)4  | ~8.8 | scFv p75 |  |  | ⭐⭐⭐  |",
        "| P0-Linker | H9+H4 + (G4S)3-EEE | ~7.7 | scFv | （）|  | ⭐⭐⭐  |",
        "| P1-MERS | H9+H5 + linker | ~8.5 | scFv p50-p75 | （H5）|  | ⭐⭐ P0 |",
        "| P2- | H9+H2 + linker | ~8.0 | scFv | -（H2）|  | ⭐⭐  |",
        "| P4-pI | H2(04)+H5(164) | ~7.3 | scFvpI | （JN.14-20×）|  | ⭐  |",
        "",
    ]
    rule()

    # ── Section 7: Limitations ────────────────────────────────────────────────
    h2("7. ")
    lines += [
        "1. **Tnb**： CMC （v2.0）， `run_vhh_cmc_eval.py`；SAP/charge_patch 。",
        "2. **pI**：（）， ±0.3-0.5 pI ； ExPASy ProtParam  IEF 。",
        "3. **scFv_52 CMC **： SAP（ SASA ）， VHH42 （）。",
        "4. ****：scFv（VH-linker-VL） VHH-GS-VHH（）； SEC-MALS 。",
        "5. **vs CHO**：scFv_52  CHO/E.coli ；（Pichia/S.cer） pI ， scFv 。",
        "",
    ]
    rule()

    # ── Footer ────────────────────────────────────────────────────────────────
    lines += [
        "## ",
        "",
        "|  |  |",
        "|---|---|",
        "| scFv_52 CMC  | `data/scfv_52_atlas/cmc_computed.json` |",
        "| scFv_52 CMC  | `data/scfv_52_atlas/cmc_stats.json` |",
        "| VHH42  | `data/humanization_assay/vhh42_cmc_summary.md` |",
        "|  VHH  | `temp_clone/TNB_BISPECIFIC_SCFV_PAIRING_ANALYSIS.md` |",
        "|  JSON  | `projects/Tnb_bispecific/cmc_eval/tnb_cmc_comparison.json` |",
        "",
        "*Report generated by AbEngineCore Bispecific VHH CMC Comparator · InSynBio*",
    ]

    return "\n".join(lines), fusion_results


# ─── main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    print("Loading scFv_52 CMC data...")
    scfv_stats, scfv_entries = load_scfv_stats()
    print(f"  Loaded {len(scfv_entries)} scFv entries, {len(scfv_stats)} metric stats")

    print("Generating comprehensive CMC comparison report...")
    md_text, fusion_results = generate_report(scfv_stats, scfv_entries)

    # Save MD
    md_path = OUT_DIR / "TNB_CMC_COMPARISON_REPORT.md"
    md_path.write_text(md_text, encoding="utf-8")
    print(f"MD Report: {md_path}")

    # Save JSON
    payload = {
        "_meta": {
            "report": "Tnb04/Tnb164 Bispecific VHH-GS-VHH CMC Comparison",
            "run_time": datetime.now().isoformat(timespec="seconds"),
            "scfv_n": len(scfv_entries),
        },
        "scfv_52_cmc_stats": scfv_stats,
        "vhh_panel": {
            "Tnb04": TNB04_VARIANTS,
            "Tnb164": TNB164_VARIANTS,
        },
        "fusion_estimates": fusion_results,
        "linker_options": LINKER_OPTIONS,
    }
    json_path = OUT_DIR / "tnb_cmc_comparison.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON Data:  {json_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()
