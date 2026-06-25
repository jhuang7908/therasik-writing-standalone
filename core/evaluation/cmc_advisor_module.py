"""
cmc_advisor_module.py — InSynBio AbEngineCore Evaluation Module
===============================================================
Full CMC/developability assessment with AbRef-458 percentile benchmarking
and mutation suggestions for flagged metrics.

This module is invoked by AbEvaluator as the 'cmc_advisor' module.
It is intentionally separate from the existing 'developability' module,
which performs a lighter pass used by the clinical rule engine.
'cmc_advisor' provides:
  - All 9 CMC metrics (pI, GRAVY, instability_index, net_charge_pH7,
    hydro_patch_max9, charge_patch_max7, agg_motifs,
    deamidation_sites, isomerization_sites)
  - AbRef-458 percentile band annotation for every metric
  - Gate evaluation (PASS / WARN / FAIL) against AbRef-458 empirical gates
  - Mutation suggestions for any metric that exceeds its gate

Output contract
---------------
  {
    "status": "PASS" | "WARN" | "FAIL",
    "reference_population": "AbRef clinical panel",
    "metrics": {
      "<metric_name>": {
        "value":           float | int,
        "percentile_band": str,   # e.g. "p25–p50"
        "gate":            str,   # "PASS" | "WARN" | "FAIL"
        "ref_p5":  float, "ref_p25": float, "ref_p50": float,
        "ref_p75": float, "ref_p95": float,
        "gate_note": str | None,
      }
    },
    "gate_summary": {"PASS": int, "WARN": int, "FAIL": int},
    "mutation_suggestions": [ <MutationAdvisor dicts> ],
    "flags": [str, ...]
  }

No TCIA, ADA, or immunogenicity content is included.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SUITE_ROOT = Path(__file__).resolve().parents[2]
_REF_STATS_PATH = _SUITE_ROOT / "data" / "reference" / "AbRef458_27m_stats_v1.json"
_RULES_PATH = _SUITE_ROOT / "data" / "rules" / "cmc_rules_v1.json"

_METRIC_LABELS: Dict[str, str] = {
    "pI":                 "pI",
    "GRAVY":              "GRAVY hydrophobicity",
    "instability_index":  "Instability Index",
    "net_charge_pH7":     "Net charge (pH 7)",
    "hydro_patch_max9":   "Hydrophobic patch max (9mer)",
    "charge_patch_max7":  "Charge patch max (7mer)",
    "SAP_score":          "SAP score",
    "Fv_charge_asymmetry":"Fv charge asymmetry",
    "agg_motifs":         "Aggregation Risk",
    "hydro_cluster_count":"Hydrophobic Density",
    "glycosylation_sites":"PTM Site Count",
    "deamidation_sites":  "Deamidation Risk",
    "isomerization_sites":"Isomerization Risk",
    "oxidation_sites":    "Oxidation Risk",
    "free_cys":           "Free Cys Count",
}

# Metrics where lower value = better developability.
# Gate logic for these only checks the upper bound (too high → WARN/FAIL).
# Being below p5 is physically excellent, not a deficiency.
#   SAP_score = 0    → no surface aggregation propensity (ideal)
#   Fv_charge_asymmetry = 0 → perfect VH/VL electrostatic balance (ideal)
_LOWER_IS_BETTER_GATE: frozenset = frozenset({"SAP_score", "Fv_charge_asymmetry"})


# ─────────────────────────────────────────────────────────────────────────────
# Reference stats and rules loaders (deterministic; do NOT recompute)
# ─────────────────────────────────────────────────────────────────────────────

def _load_ref_stats() -> Optional[Dict[str, Any]]:
    """Load AbRef-458 fixed percentile statistics. Never recompute at runtime."""
    if not _REF_STATS_PATH.exists():
        return None
    try:
        with open(_REF_STATS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _load_rules() -> Optional[Dict[str, Any]]:
    """Load CMC mutation rules from cmc_rules_v1.json."""
    if not _RULES_PATH.exists():
        return None
    try:
        with open(_RULES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Percentile banding
# ─────────────────────────────────────────────────────────────────────────────

def _percentile_band(value: float, ref: Dict[str, Any]) -> str:
    """Return band label: p0–p5 / p5–p25 / p25–p75 / p75–p95 / p95+."""
    p5  = ref.get("p5",  float("-inf"))
    p25 = ref.get("p25", float("-inf"))
    p75 = ref.get("p75", float("inf"))
    p95 = ref.get("p95", float("inf"))

    if value < p5:
        return "p0–p5"
    if value <= p25:
        return "p5–p25"
    if value <= p75:
        return "p25–p75"
    if value <= p95:
        return "p75–p95"
    return "p95+"


def _gate_result(metric: str, value: float, ref: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """
    Evaluate gate for a metric against AbRef-458.

    For standard metrics (symmetric gate):
      PASS: p5 ≤ value ≤ p95
      WARN: p0–p5 or p95–p100  (edge 5%)
      FAIL: value < p0 or value > p100  (outside observed range)
      p0/p100 extrapolated as p5 ± 0.05*span when absent.

    For _LOWER_IS_BETTER_GATE metrics (upper-only gate):
      SAP_score, Fv_charge_asymmetry — lower is physically better.
      Values below p5 are excellent, not deficient. Gate only fires high:
      PASS: value ≤ p95
      WARN: p95 < value ≤ p100
      FAIL: value > p100
    """
    p5  = ref.get("p5",  float("-inf"))
    p95 = ref.get("p95", float("inf"))
    span = max(0.01, p95 - p5) if p95 > p5 else 0.01

    if metric in _LOWER_IS_BETTER_GATE:
        p100 = ref.get("p100", p95 + 0.05 * span)
        if value > p100:
            return "FAIL", f"{_METRIC_LABELS.get(metric, metric)} ({value}) > AbRef-458 upper bound (abnormally high)"
        if value > p95:
            return "WARN", f"{_METRIC_LABELS.get(metric, metric)} ({value}) in p95–p100 (borderline high)"
        return "PASS", None

    p0   = ref.get("p0",   p5  - 0.05 * span)
    p100 = ref.get("p100", p95 + 0.05 * span)
    if value < p0:
        return "FAIL", f"{_METRIC_LABELS.get(metric, metric)} ({value}) < AbRef-458 observed range"
    if value > p100:
        return "FAIL", f"{_METRIC_LABELS.get(metric, metric)} ({value}) > AbRef-458 observed range"
    if value < p5:
        return "WARN", f"{_METRIC_LABELS.get(metric, metric)} ({value}) in p0–p5 (marginal 5%)"
    if value > p95:
        return "WARN", f"{_METRIC_LABELS.get(metric, metric)} ({value}) in p95–p100 (marginal 5%)"
    return "PASS", None


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_cmc_advisor(
    vh_seq: str,
    vl_seq: str,
    stored_metrics: Optional[Dict[str, Any]] = None,
    structure_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full CMC/developability assessment against AbRef-458 with mutation suggestions.

    Loads reference from data/reference/AbRef458_stats_v1.json and rules from
    data/rules/cmc_rules_v1.json. Uses CMCMetricEngine and MutationAdvisor.
    Deterministic; no runtime recomputation of statistics.
    """
    vh = (vh_seq or "").strip().upper()
    vl = (vl_seq or "").strip().upper()

    if not vh:
        return {"status": "SKIPPED", "reason": "No VH sequence provided", "flags": []}

    ref_stats = _load_ref_stats()
    if ref_stats is None:
        return {
            "status": "ERROR",
            "reason": f"AbRef-458 reference stats not found at {_REF_STATS_PATH}",
            "flags": ["FAIL:ref_stats_missing"],
        }

    rules = _load_rules()
    if rules is None:
        return {
            "status": "ERROR",
            "reason": f"CMC rules not found at {_RULES_PATH}",
            "flags": ["FAIL:cmc_rules_missing"],
        }

    # Step 1: compute metrics via CMCMetricEngine (database-first: reuse stored if present)
    from core.cmc.cmc_metrics import CMCMetricEngine
    raw_metrics = CMCMetricEngine.compute_metrics(
        vh, vl,
        stored_metrics=stored_metrics,
        structure_path=structure_path,
    )
    if raw_metrics.get("_biopython_missing"):
        return {
            "status": "SKIPPED",
            "reason": "BioPython not installed — required for pI, GRAVY, instability_index",
            "flags": ["WARN:biopython_missing"],
        }

    # Normalize list metrics to scalar for percentile banding
    metrics_for_band: Dict[str, Any] = dict(raw_metrics)
    for k in ("deamidation_sites", "isomerization_sites", "glycosylation_sites", "oxidation_sites", "free_cys"):
        v = raw_metrics.get(k)
        if isinstance(v, list):
            metrics_for_band[k] = len(v)

    # A3: Structural override — replace sequence-level agg_motifs count with the
    # SASA-derived n_hydrophobic_patches from the immunogenicity module.
    # Sequence motif scanning counts pattern matches regardless of surface exposure,
    # overstating aggregation risk. SASA data reflects actual exposed hydrophobic area.
    _stored = stored_metrics or {}
    _struct_agg = _stored.get("_struct_agg_motifs")
    if _struct_agg is not None:
        metrics_for_band["agg_motifs"] = int(_struct_agg)
        raw_metrics = dict(raw_metrics)
        raw_metrics["agg_motifs"] = int(_struct_agg)
        raw_metrics["_agg_motifs_source"] = "structural_SASA"
        raw_metrics["_agg_motifs_seq_count"] = raw_metrics.get("agg_motifs_seq_count",
                                                                raw_metrics.get("agg_motifs"))

    ref_metrics = ref_stats.get("metrics", ref_stats)
    n_ref = ref_stats.get("n", 458)

    # Step 2: annotate each metric with percentile band and gate
    annotated: Dict[str, Any] = {}
    gates: Dict[str, str] = {}
    flags: List[str] = []

    for metric in _METRIC_LABELS:
        value = metrics_for_band.get(metric)
        if value is None:
            continue
        ref = ref_metrics.get(metric, {})
        band = _percentile_band(float(value), ref)
        gate, gate_note = _gate_result(metric, float(value), ref)
        gates[metric] = gate
        if gate != "PASS" and gate_note:
            flags.append(f"{gate}:{gate_note}")
        annotated[metric] = {
            "value":           raw_metrics.get(metric, value),
            "label":           _METRIC_LABELS.get(metric, metric),
            "percentile_band": band,
            "gate":            gate,
            "gate_note":       gate_note,
            "direction":       "lower_is_better" if metric in _LOWER_IS_BETTER_GATE else "in_range",
            "ref_p5":          ref.get("p5"),
            "ref_p25":         ref.get("p25"),
            "ref_p50":         ref.get("p50"),
            "ref_p75":         ref.get("p75"),
            "ref_p95":         ref.get("p95"),
            "ref_n":           n_ref,
        }

    gate_summary = {
        "PASS": sum(1 for g in gates.values() if g == "PASS"),
        "WARN": sum(1 for g in gates.values() if g == "WARN"),
        "FAIL": sum(1 for g in gates.values() if g == "FAIL"),
    }

    # Step 3: overall status
    if gate_summary["FAIL"] > 0:
        overall = "FAIL"
    elif gate_summary["WARN"] > 0:
        overall = "WARN"
    else:
        overall = "PASS"

    # Step 4: mutation suggestions via rule-driven MutationAdvisor
    suggestions: List[Dict[str, Any]] = []
    try:
        from core.cmc.mutation_advisor import MutationAdvisor
        advisor = MutationAdvisor(
            vh_seq=vh,
            vl_seq=vl,
            metrics=raw_metrics,
            reference_stats=ref_stats,
            rules=rules,
        )
        suggestions = advisor.advise()
    except Exception as e:
        flags.append(f"WARN:mutation_advisor_error — {e}")

    # Step 5: ADI (Antibody Developability Index)
    adi_value: Optional[float] = None
    adi_percentile: Optional[float] = None
    adi_interpretation_str: Optional[str] = None
    try:
        from core.cmc.adi_score import compute_adi, adi_interpretation, compute_adi_percentile
        adi_value = compute_adi(raw_metrics)
        adi_interpretation_str = adi_interpretation(adi_value)
        adi_percentile = compute_adi_percentile(adi_value)
    except Exception:
        pass

    return {
        "status":               overall,
        "reference_population": "AbRef clinical panel",
        "evaluation_standard":  "CMC_STANDARD_v1.0",
        "reference_dataset":    "AbRef458_v1",
        "metrics_version":     "METRICS_v1",
        "ADI":                  adi_value,
        "ADI_percentile":       adi_percentile,
        "ADI_interpretation":   adi_interpretation_str,
        "metrics":              annotated,
        "gate_summary":         gate_summary,
        "mutation_suggestions": suggestions,
        "flags":                flags,
    }
