"""
adi_score.py — InSynBio AbEngineCore CMC Module
================================================
Antibody Developability Index (ADI) — weighted composite score.

Category weights (ANTIBODY_EVALUATION_STANDARD_v1):
  Hydrophobicity:     30%
  Charge distribution: 25%
  Chemical liabilities: 25%
  Aggregation risk:   20%

ADI = Σ (metric_score × weight), range 0–100.
Interpretation: 80–100 Excellent, 60–80 Acceptable, 40–60 Moderate risk, <40 High risk.

Scoring design
--------------
Two scoring functions are used depending on metric direction:

1. Tent function (_metric_score_continuous) — symmetric, peaks at p50:
   value       score
   ≤ floor_lo    0        (floor_lo = p5  − 0.5 × span)
   p5           40
   p25          75
   p50         100   ← peak
   p75          75
   p95          40
   ≥ floor_hi    0        (floor_hi = p95 + 0.5 × span)

2. Monotone-low (_metric_score_monotone_low) — for metrics where lower = better:
   Used for: SAP_score, Fv_charge_asymmetry
   value = 0      → 100  (physically perfect: no aggregation / perfect symmetry)
   value = p95    → 40
   value ≥ floor_hi → 0

   Physical justification:
   - SAP_score = 0 means zero surface aggregation propensity (ideal).
     Penalising it for being below Clinical Reference Cohort p5 is scientifically incorrect.
   - Fv_charge_asymmetry = 0 means perfect VH/VL electrostatic balance (ideal).
     Same reasoning applies.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SUITE_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_REF_PATH = _SUITE_ROOT / "data" / "reference" / "AbRef458_stats_v1.json"

# Category weights (must sum to 1.0)
_CATEGORY_WEIGHTS = {
    "hydrophobicity": 0.30,   # GRAVY, hydro_patch_max9, SAP_score
    "charge": 0.25,           # pI, net_charge_pH7, charge_patch_max7, Fv_charge_asymmetry
    "chemical": 0.25,         # glycosylation, deamidation, isomerization, oxidation, free_cys
    "aggregation": 0.20,      # agg_motifs, hydro_cluster_count, instability_index
}

# Metrics where lower value = better outcome.
# These use _metric_score_monotone_low() instead of the tent function.
# SAP_score = 0  → no surface aggregation propensity  (best possible)
# Fv_charge_asymmetry = 0 → perfect VH/VL charge balance (best possible)
_LOWER_IS_BETTER: frozenset = frozenset({"SAP_score", "Fv_charge_asymmetry"})

# Metric → category (weight distributed evenly within category)
_METRIC_CATEGORY: Dict[str, str] = {
    "pI": "charge",
    "GRAVY": "hydrophobicity",
    "instability_index": "aggregation",
    "net_charge_pH7": "charge",
    "charge_patch_max7": "charge",
    "Fv_charge_asymmetry": "charge",
    "hydro_patch_max9": "hydrophobicity",
    "SAP_score": "hydrophobicity",
    "agg_motifs": "aggregation",
    "hydro_cluster_count": "aggregation",
    "glycosylation_sites": "chemical",
    "deamidation_sites": "chemical",
    "isomerization_sites": "chemical",
    "oxidation_sites": "chemical",
    "free_cys": "chemical",
}


def _to_scalar(val: Any) -> float:
    if isinstance(val, list):
        return float(len(val))
    if val is None:
        return 0.0
    return float(val)


def _interp(x: float, x0: float, y0: float, x1: float, y1: float) -> float:
    """Linear interpolation; clamps when x0 == x1."""
    if x1 == x0:
        return y0
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def _metric_score_continuous(value: float, ref: Dict[str, Any]) -> float:
    """
    Continuous score 0–100 using a piecewise-linear tent centred at p50.

    Anchors (x → score):
      floor_lo (p5 - 0.5*span) → 0
      p5                       → 40
      p25                      → 75
      p50                      → 100  ← peak
      p75                      → 75
      p95                      → 40
      floor_hi (p95 + 0.5*span)→ 0

    Falls back to 50.0 when the reference is missing critical percentiles.
    """
    p5  = ref.get("p5")
    p25 = ref.get("p25")
    p50 = ref.get("p50")
    p75 = ref.get("p75")
    p95 = ref.get("p95")

    if p5 is None or p95 is None:
        return 50.0
    if p50 is None:
        p50 = (p5 + p95) / 2.0
    if p25 is None:
        p25 = (p5 + p50) / 2.0
    if p75 is None:
        p75 = (p50 + p95) / 2.0

    span = p95 - p5
    if span <= 0.0:
        return 100.0 if abs(value - p50) < 1e-9 else 50.0

    floor_lo = p5  - 0.5 * span
    floor_hi = p95 + 0.5 * span

    if value <= floor_lo:
        return 0.0
    if value >= floor_hi:
        return 0.0

    anchors: List[Tuple[float, float]] = [
        (floor_lo, 0.0),
        (p5,       40.0),
        (p25,      75.0),
        (p50,     100.0),
        (p75,      75.0),
        (p95,      40.0),
        (floor_hi,  0.0),
    ]

    for i in range(len(anchors) - 1):
        x0, y0 = anchors[i]
        x1, y1 = anchors[i + 1]
        if x0 <= value <= x1:
            return round(_interp(value, x0, y0, x1, y1), 2)

    return 0.0


def _metric_score_monotone_low(value: float, ref: Dict[str, Any]) -> float:
    """
    Monotone-decreasing scorer for metrics where lower is physically better.

    Anchors (x → score):
      value ≤ 0        → 100  (physically perfect value)
      value = p95      → 40   (at the edge of the clinical population)
      value ≥ floor_hi → 0    (floor_hi = p95 + 0.5 * span)

    Linear interpolation between anchors. Falls back to 50.0 when reference
    percentiles are missing.
    """
    p5  = ref.get("p5")
    p95 = ref.get("p95")
    if p95 is None:
        return 50.0
    span = max((p95 - (p5 or 0)), 0.01)
    floor_hi = p95 + 0.5 * span

    if value <= 0.0:
        return 100.0
    if value >= floor_hi:
        return 0.0
    if value <= p95:
        return round(_interp(value, 0.0, 100.0, p95, 40.0), 2)
    return round(_interp(value, p95, 40.0, floor_hi, 0.0), 2)


def _metric_score(value: float, ref: Dict[str, Any]) -> float:
    """
    Legacy bucket scorer (kept for backward compatibility).
    Prefer _metric_score_continuous for new code.
    p25–p75: 100, p5–p25 or p75–p95: 50, outside: 0.
    """
    p5  = ref.get("p5",  float("-inf"))
    p25 = ref.get("p25", float("-inf"))
    p75 = ref.get("p75", float("inf"))
    p95 = ref.get("p95", float("inf"))
    if value < p5 or value > p95:
        return 0.0
    if p25 <= value <= p75:
        return 100.0
    return 50.0


def _load_ref_metrics(path: Path) -> Dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("metrics", data)
    except Exception:
        return {}


def compute_adi(
    metrics: Dict[str, Any],
    ref_stats_path: Optional[Path] = None,
    *,
    excluded_metrics: Optional[set] = None,
    ref_metrics: Optional[Dict[str, Any]] = None,
) -> float:
    """
    Compute ADI using continuous per-metric scoring.
    Returns 0–100 (higher = better developability).

    Parameters
    ----------
    metrics : dict
        CMC metrics dict (same keys as _METRIC_CATEGORY).
    ref_stats_path : Path, optional
        Path to reference stats JSON.  Defaults to Clinical Reference Cohort.
    ref_metrics : dict, optional
        Pre-loaded ``metrics`` sub-dict (same shape as in ``*_stats_v1.json``).
        If set, used instead of loading from ``ref_stats_path``.
    excluded_metrics : set, optional
        Metric keys to skip (e.g. {"Fv_charge_asymmetry"} for VHH).
    """
    if ref_metrics is None:
        path = ref_stats_path or _DEFAULT_REF_PATH
        if not path.exists():
            return 0.0
        ref_metrics = _load_ref_metrics(path)
    if not ref_metrics:
        return 0.0

    excluded = excluded_metrics or set()
    cat_scores: Dict[str, List[float]] = {c: [] for c in _CATEGORY_WEIGHTS}

    for mkey, cat in _METRIC_CATEGORY.items():
        if mkey in excluded:
            continue
        ref = ref_metrics.get(mkey, {})
        if not ref:
            continue
        val = metrics.get(mkey)
        if val is None and mkey not in metrics:
            continue
        scalar = _to_scalar(val)
        if mkey in _LOWER_IS_BETTER:
            sc = _metric_score_monotone_low(scalar, ref)
        else:
            sc = _metric_score_continuous(scalar, ref)
        cat_scores[cat].append(sc)

    total = 0.0
    active_weight = 0.0
    for cat, weight in _CATEGORY_WEIGHTS.items():
        scores = cat_scores.get(cat, [])
        if not scores:
            continue
        cat_avg = sum(scores) / len(scores)
        total += cat_avg * weight
        active_weight += weight

    if active_weight <= 0.0:
        return 0.0
    # Re-normalise if some categories were entirely absent.
    # total is already in 0–100 range (metric scores 0–100 × weights ≤ 1.0).
    return round(total / active_weight, 2)


def compute_adi_with_breakdown(
    metrics: Dict[str, Any],
    ref_stats_path: Optional[Path] = None,
    *,
    excluded_metrics: Optional[set] = None,
    ref_metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Like compute_adi but also returns per-metric and per-category breakdowns.
    Useful for debugging and detailed reports.
    """
    if ref_metrics is None:
        path = ref_stats_path or _DEFAULT_REF_PATH
        if not path.exists():
            return {"ADI": 0.0, "metric_scores": {}, "category_scores": {}}
        ref_metrics = _load_ref_metrics(path)
    if not ref_metrics:
        return {"ADI": 0.0, "metric_scores": {}, "category_scores": {}}
    excluded = excluded_metrics or set()
    cat_scores: Dict[str, List[float]] = {c: [] for c in _CATEGORY_WEIGHTS}
    metric_scores: Dict[str, float] = {}

    for mkey, cat in _METRIC_CATEGORY.items():
        if mkey in excluded:
            continue
        ref = ref_metrics.get(mkey, {})
        if not ref:
            continue
        val = metrics.get(mkey)
        if val is None and mkey not in metrics:
            continue
        scalar = _to_scalar(val)
        if mkey in _LOWER_IS_BETTER:
            sc = _metric_score_monotone_low(scalar, ref)
        else:
            sc = _metric_score_continuous(scalar, ref)
        cat_scores[cat].append(sc)
        metric_scores[mkey] = sc

    category_avgs: Dict[str, float] = {}
    total = 0.0
    active_weight = 0.0
    for cat, weight in _CATEGORY_WEIGHTS.items():
        scores = cat_scores.get(cat, [])
        if not scores:
            category_avgs[cat] = None  # type: ignore[assignment]
            continue
        avg = round(sum(scores) / len(scores), 2)
        category_avgs[cat] = avg
        total += avg * weight
        active_weight += weight

    adi = round(total / active_weight, 2) if active_weight > 0 else 0.0
    return {
        "ADI": adi,
        "metric_scores": metric_scores,
        "category_scores": category_avgs,
    }


def adi_interpretation(adi: float) -> str:
    """Return interpretation string for ADI value."""
    if adi >= 80:
        return "Excellent"
    if adi >= 60:
        return "Acceptable"
    if adi >= 40:
        return "Moderate risk"
    return "High risk"


def compute_adi_percentile(
    adi: float,
    adi_dist_path: Optional[Path] = None,
) -> Optional[float]:
    """
    Compute approximate percentile rank of ADI within Clinical Reference Cohort.
    Returns p5, p25, p50, p75, p95 or interpolated value.
    """
    path = adi_dist_path or (_SUITE_ROOT / "data" / "reference" / "AbRef458_ADI_distribution.json")
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            dist = json.load(f)
    except Exception:
        return None
    p5, p25, p50, p75, p95 = dist.get("p5"), dist.get("p25"), dist.get("p50"), dist.get("p75"), dist.get("p95")
    if any(x is None for x in (p5, p25, p50, p75, p95)):
        return None
    if adi <= p5:
        return 5.0
    if adi <= p25:
        return 5.0 + 20.0 * (adi - p5) / (p25 - p5) if p25 != p5 else 15.0
    if adi <= p50:
        return 25.0 + 25.0 * (adi - p25) / (p50 - p25) if p50 != p25 else 37.5
    if adi <= p75:
        return 50.0 + 25.0 * (adi - p50) / (p75 - p50) if p75 != p50 else 62.5
    if adi <= p95:
        return 75.0 + 20.0 * (adi - p75) / (p95 - p75) if p95 != p75 else 85.0
    return 95.0 + 5.0 * min(1.0, (adi - p95) / max(0.1, p95 - p50))


# Backward compatibility
def compute_developability_index(
    metrics: Dict[str, Any],
    ref_stats_path: Optional[Path] = None,
) -> float:
    """Alias for compute_adi."""
    return compute_adi(metrics, ref_stats_path)


_NAT384_REF = _SUITE_ROOT / "data" / "reference" / "Natural384_IgG_stats_v1.json"


def compute_adi_natural384(
    metrics: Dict[str, Any],
    *,
    excluded_metrics: Optional[set] = None,
) -> float:
    """
    ADI (continuous tent/monotone) vs frozen **Natural Baseline** (fully human IgG Fv) CMC
    percentiles. Parallel to default Clinical Reference Cohort; do not mix cohorts in the same
    table without relabeling.
    """
    if not _NAT384_REF.exists():
        return 0.0
    return compute_adi(metrics, ref_stats_path=_NAT384_REF, excluded_metrics=excluded_metrics)
