"""
core/cmc/bispecific_cmc_engine.py
==================================
InSynBio AbEngineCore — Bispecific VHH CMC Engine

Provides bispecific-specific computation logic (fusion pI matrix, SmartLink™
recommendation, Markdown report generation) for dual-VHH bispecific constructs.

Imports per-arm logic from core.cmc.vhh_cmc_engine — no duplication.

Public API
----------
  compute_fusion_matrix(arm_a_results, arm_b_results, linkers, er_threshold) -> list[dict]
  select_recommendations(fusion_matrix, arm_a_dict, arm_b_dict, er_threshold) -> dict
  generate_markdown(arm_a_results, arm_b_results, fusion_matrix, recommendations,
                    ref_stats, er_threshold, meta) -> str

  Constants:
    ER_PI_WARN, ER_PI_CRIT, ER_PH, DEFAULT_LINKERS
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.cmc.cmc_metrics import compute_pI, compute_net_charge
from core.cmc.vhh_cmc_engine import _METRIC_LABELS, _METRIC_DISPLAY_ORDER

# ── ER expression constants ───────────────────────────────────────────────────
ER_PI_WARN = 8.5   # pI above this → expression risk (WARN)
ER_PI_CRIT = 9.0   # pI above this → critical expression risk
ER_PH      = 7.2   # ER lumen pH

# ── Default linker panel (SmartLink™) ─────────────────────────────────────────
DEFAULT_LINKERS: Dict[str, str] = {
    "(G4S)3":    "GGGGSGGGGSGGGGS",
    "(G4S)4":    "GGGGSGGGGSGGGGSGGGGS",
    "(G4S)3+2E": "GGGGSGGGGSGGGGSEE",
    "(G4S)3+3E": "GGGGSGGGGSGGGGSEEE",
    "(G4S)3+4E": "GGGGSGGGGSGGGGSEEEE",
    "Whitlow":   "GSTSGSGKPGSGEGSTKG",
    "EAAAK3":    "EAAAKEAAAKEAAAK",
}


# ═════════════════════════════════════════════════════════════════════════════
# Fusion pI matrix
# ═════════════════════════════════════════════════════════════════════════════

def _pi_flag(pi: float, er_threshold: float = ER_PI_WARN) -> str:
    if pi >= ER_PI_CRIT:
        return "critical"
    if pi >= er_threshold:
        return "warn"
    return "pass"


def compute_fusion_matrix(
    arm_a_results: List[Dict],
    arm_b_results: List[Dict],
    linkers: Optional[Dict[str, str]] = None,
    er_threshold: float = ER_PI_WARN,
) -> List[Dict]:
    """
    Compute fusion pI/charge for all (arm_a × arm_b × linker) combinations.

    Parameters
    ----------
    arm_a_results : list of dicts from evaluate_single_vhh()
    arm_b_results : list of dicts from evaluate_single_vhh()
    linkers       : {name: sequence}; defaults to DEFAULT_LINKERS if None
    er_threshold  : pI above which flag='warn' (default 8.5)

    Returns
    -------
    list of dicts sorted by fusion_pi ascending:
      arm_a, arm_b, linker, linker_seq,
      fusion_pi, fusion_nc, fusion_len, pi_flag
    """
    if linkers is None:
        linkers = DEFAULT_LINKERS
    rows = []
    for ra in arm_a_results:
        for rb in arm_b_results:
            for lname, lseq in linkers.items():
                fusion_seq = ra["sequence"] + lseq + rb["sequence"]
                fusion_pi  = compute_pI(fusion_seq)
                rows.append({
                    "arm_a":      ra["name"],
                    "arm_b":      rb["name"],
                    "linker":     lname,
                    "linker_seq": lseq,
                    "fusion_pi":  fusion_pi,
                    "fusion_nc":  compute_net_charge(fusion_seq, 7.0),
                    "fusion_len": len(fusion_seq),
                    "pi_flag":    _pi_flag(fusion_pi, er_threshold),
                })
    rows.sort(key=lambda x: x["fusion_pi"])
    return rows


# ═════════════════════════════════════════════════════════════════════════════
# SmartLink™ recommendation engine
# ═════════════════════════════════════════════════════════════════════════════

def select_recommendations(
    fusion_matrix: List[Dict],
    arm_a_dict: Dict[str, Dict],
    arm_b_dict: Dict[str, Dict],
    er_threshold: float = ER_PI_WARN,
) -> Dict:
    """
    Select primary recommendation and runner-up.

    Priority: lowest fusion pI among PASS → WARN → CRITICAL.
    Runner-up: second lowest among PASS; otherwise first WARN.

    Returns
    -------
    dict: primary, runner_up, best_adi_arm_a, best_adi_arm_b,
          n_passing, n_warning, n_critical
    """
    passing  = [r for r in fusion_matrix if r["pi_flag"] == "pass"]
    warning  = [r for r in fusion_matrix if r["pi_flag"] == "warn"]
    critical = [r for r in fusion_matrix if r["pi_flag"] == "critical"]

    primary = (passing[0] if passing
               else (warning[0] if warning else fusion_matrix[0]))
    runner  = (passing[1] if len(passing) > 1
               else (warning[0] if warning else None))

    best_a = max(arm_a_dict.values(), key=lambda x: x["adi_score"])
    best_b = max(arm_b_dict.values(), key=lambda x: x["adi_score"])

    return {
        "primary":        primary,
        "runner_up":      runner,
        "best_adi_arm_a": best_a["name"],
        "best_adi_arm_b": best_b["name"],
        "n_passing":      len(passing),
        "n_warning":      len(warning),
        "n_critical":     len(critical),
    }


# ═════════════════════════════════════════════════════════════════════════════
# Markdown report generator
# ═════════════════════════════════════════════════════════════════════════════

def _flag_icon(flag: str) -> str:
    return {
        "PASS": "✅", "WARN": "⚠️", "FAIL": "❌",
        "pass": "✅", "warn": "⚠️", "critical": "🔴",
        "NA": "—",
    }.get(flag, "—")


def _render_arm_detail(
    results: List[Dict],
    arm_label: str,
    ref_stats: Dict[str, Any],
) -> List[str]:
    """Render full 15-metric CMC detail section for one arm."""
    lines: List[str] = [
        "---", "",
        f"## {arm_label} — Full CMC Assessment", "",
    ]
    for r in results:
        m     = r["metrics"]
        flags = r["risk_flags"]
        pct   = r.get("percentile_ranks_vs_vhh42", {})

        lines += [
            f"### {r['name']}", "",
            "| Field | Value |",
            "|---|---|",
            f"| Sequence length | {r['length']} aa |",
            f"| **ADI score** | **{r['adi_score']:.0f} / 100** — {r['adi_grade']} |",
            f"| WARN / FAIL flags | {r['n_warn']} WARN · {r['n_fail']} FAIL |",
            f"| Overall status | {r['overall_status']} |",
            f"| pI expression flag | {r['pi_flag'].upper()} (pI = {m['pI']}) |",
            "",
            "| Metric | Value | Flag | vs Clinical VHH Benchmark |",
            "|---|---|:---:|:---:|",
        ]
        for key in _METRIC_DISPLAY_ORDER:
            val = m.get(key)
            if val is None:
                continue
            flag  = flags.get(key, "PASS")
            rank  = pct.get(key, "N/A")
            v_str = ("%.3f" % val) if isinstance(val, float) else str(val)
            ref   = ref_stats.get(key, {})
            ref_s = (f" (p50={ref['p50']:.3g})"
                     if isinstance(ref.get("p50"), (int, float)) else "")
            lines.append(
                f"| {_METRIC_LABELS.get(key, key)} | {v_str}{ref_s} "
                f"| {_flag_icon(flag)} {flag} | {rank} |"
            )

        pos = m.get("_positions", {})
        if any(pos.get(k) for k in ("glycosylation", "deamidation",
                                     "isomerization", "oxidation", "free_cys")):
            lines += ["", "**Chemical liability sites (0-based positions):**", ""]
            for k, label in [
                ("glycosylation", "N-glycosylation"),
                ("deamidation",   "Deamidation"),
                ("isomerization", "Isomerization"),
                ("oxidation",     "Oxidation M/W"),
                ("free_cys",      "Free Cys"),
            ]:
                if pos.get(k):
                    lines.append(f"- **{label}**: positions {pos[k]}")
        lines.append("")
    return lines


def generate_markdown(
    arm_a_results: List[Dict],
    arm_b_results: List[Dict],
    fusion_matrix: List[Dict],
    recommendations: Dict,
    ref_stats: Dict[str, Any],
    er_threshold: float = ER_PI_WARN,
    meta: Optional[Dict] = None,
) -> str:
    """
    Generate full Markdown report for bispecific VHH CMC assessment.

    Sections:
      1. Executive summary (ADI overview + primary recommendation)
      2. Arm A full CMC detail (15-metric table per variant)
      3. Arm B full CMC detail
      4. Fusion pI matrix top-10
      5. ER expression mechanism
      6. Recommendations
    """
    if meta is None:
        meta = {}
    ts = meta.get("timestamp", datetime.now().isoformat())
    lines: List[str] = [
        "# Bispecific VHH CMC Assessment Report",
        f"> Generated by InSynBio AbEngineCore v2.0 · {ts}",
        f"> Reference: Clinical VHH Benchmark · ADI: flag-discrete, aligned with run_vhh_cmc_eval",
        "", "---", "", "## Executive Summary", "",
        "| Arm | Variant | ADI | Grade | WARN | FAIL | pI | ER Flag |",
        "|---|---|:---:|---|:---:|:---:|:---:|:---:|",
    ]
    for r in arm_a_results:
        lines.append(
            f"| **Arm A** | {r['name']} | **{r['adi_score']:.0f}** | {r['adi_grade']} | "
            f"{r['n_warn']} | {r['n_fail']} | {r['metrics']['pI']} | "
            f"{_flag_icon(r['pi_flag'])} {r['pi_flag'].upper()} |"
        )
    for r in arm_b_results:
        lines.append(
            f"| **Arm B** | {r['name']} | **{r['adi_score']:.0f}** | {r['adi_grade']} | "
            f"{r['n_warn']} | {r['n_fail']} | {r['metrics']['pI']} | "
            f"{_flag_icon(r['pi_flag'])} {r['pi_flag'].upper()} |"
        )

    p = recommendations["primary"]
    lines += [
        "", "### Recommended Construct", "",
        "| Field | Value |", "|---|---|",
        f"| **Construct** | **{p['arm_a']} — {p['linker']} — {p['arm_b']}** |",
        f"| Fusion pI | **{p['fusion_pi']}** ({_flag_icon(p['pi_flag'])} {p['pi_flag'].upper()}) |",
        f"| Net charge @pH7 | {p['fusion_nc']:+.1f} |",
        f"| Total length | {p['fusion_len']} aa |",
        f"| Passing combos | {recommendations['n_passing']} / "
        f"{recommendations['n_passing'] + recommendations['n_warning'] + recommendations['n_critical']} |",
        "",
    ]

    lines += _render_arm_detail(arm_a_results, "Arm A", ref_stats)
    lines += _render_arm_detail(arm_b_results, "Arm B", ref_stats)

    lines += [
        "---", "",
        "## Fusion pI Matrix — Top 10 (sorted by pI ascending)", "",
        "| Arm A | Linker | Arm B | Fusion pI | Net Charge | Length | Flag |",
        "|---|---|---|:---:|:---:|:---:|:---:|",
    ]
    for row in fusion_matrix[:10]:
        lines.append(
            f"| {row['arm_a']} | `{row['linker']}` | {row['arm_b']} | "
            f"**{row['fusion_pi']}** | {row['fusion_nc']:+.1f} | "
            f"{row['fusion_len']} | {_flag_icon(row['pi_flag'])} {row['pi_flag'].upper()} |"
        )

    lines += [
        "", "---", "",
        "## Expression Risk — pI / ER Electrostatic Mechanism", "",
        f"ER lumen pH ≈ {ER_PH}. A fusion with pI > {er_threshold} carries net positive charge "
        "in the secretory pathway, promoting non-specific adsorption to luminal chaperones "
        "(BiP/GRP78, calreticulin) and ER membrane phospholipids. "
        "Extended ER dwell time increases ERAD susceptibility and reduces secretion yield.",
        "",
        "| pI Zone | Charge at ER pH | Expression Risk |",
        "|---|---|---|",
        f"| pI < {er_threshold} | Near-neutral to negative | Low — recommended |",
        f"| pI {er_threshold}–{ER_PI_CRIT} | Moderately positive | Warning — consider charged linker |",
        f"| pI > {ER_PI_CRIT} | Highly cationic | Critical — likely poor secretion |",
        "",
    ]

    ru = recommendations["runner_up"]
    lines += [
        "---", "", "## Recommendations", "",
        f"- **Primary:** `{p['arm_a']} — {p['linker']} — {p['arm_b']}` "
        f"(pI {p['fusion_pi']}, net charge {p['fusion_nc']:+.1f})",
    ]
    if ru:
        lines.append(
            f"- **Runner-up / Backup:** `{ru['arm_a']} — {ru['linker']} — {ru['arm_b']}` "
            f"(pI {ru['fusion_pi']}, net charge {ru['fusion_nc']:+.1f})"
        )
    lines += [
        f"- Combinations passing pI < {er_threshold}: **{recommendations['n_passing']}**",
        f"- Warning: **{recommendations['n_warning']}** · Critical: **{recommendations['n_critical']}**",
        "", "---", "",
        "> **ADI:** 80–100 Excellent · 60–79 Acceptable · 40–59 Moderate risk · <40 High risk  ",
        "> Flag-discrete scoring (PASS=100/WARN=50/FAIL=0) · 4-category weights  ",
        "> (hydrophobicity 30% · charge 25% · chemical 25% · aggregation 20%)",
        "",
        "*InSynBio AbEngineCore v2.0 · Bispecific VHH CMC Standard V1.0 · "
        "All analyses are in silico. Experimental validation required.*", "",
    ]
    return "\n".join(lines)
