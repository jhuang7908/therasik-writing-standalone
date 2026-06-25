"""
clinical_rule_engine.py — InSynBio AbEngineCore Clinical Rule Engine
=====================================================================
Evaluates antibody sequence metrics against clinical reference populations.

Populations:
  "humanized_458" → AbRef-458 (n=458 humanized/fully-human approved mAbs)
  "vhh_40"        → VHH42 reference panel
  "scfv_84"       → (not yet populated; falls back to industry gates)

Used by AbEvaluator._run_developability().
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_SUITE_ROOT = Path(__file__).resolve().parents[2]

_REF_PATHS: Dict[str, Path] = {
    "humanized_458": _SUITE_ROOT / "data" / "reference" / "AbRef458_stats_v1.json",
    "vhh_40":        _SUITE_ROOT / "data" / "reference" / "VHH42_reference_stats_v1.json",
}

_LOWER_IS_BETTER: frozenset = frozenset({
    "SAP_score", "Fv_charge_asymmetry", "instability_index",
    "hydro_patch_max9", "charge_patch_max7", "agg_motifs",
    "hydro_cluster_count", "glycosylation_sites", "deamidation_sites",
    "isomerization_sites", "oxidation_sites", "free_cys"
})


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ClinicalRuleResult:
    clinical_score:   Optional[float]         = None
    percentile_ranks: Dict[str, Any]          = field(default_factory=dict)
    gate_summary:     Dict[str, int]          = field(default_factory=lambda: {"PASS": 0, "WARN": 0, "FAIL": 0})
    flags:            List[str]               = field(default_factory=list)
    details:          Dict[str, Any]          = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class ClinicalRuleEngine:
    """Evaluate sequence metrics against a fixed clinical reference population."""

    def __init__(self, population: str, ref_stats: Dict[str, Any]) -> None:
        self.population = population
        self._ref = ref_stats.get("metrics", ref_stats)
        self._n   = ref_stats.get("n", 458)

    # ── Internal helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _band(value: float, ref: Dict[str, Any]) -> str:
        p5, p25, p75, p95 = (
            ref.get("p5", float("-inf")),
            ref.get("p25", float("-inf")),
            ref.get("p75", float("inf")),
            ref.get("p95", float("inf")),
        )
        if value <= p5:
            return "p0–p5"
        if value <= p25:
            return "p5–p25"
        if value <= p75:
            return "p25–p75"
        if value <= p95:
            return "p75–p95"
        return "p95+"

    @staticmethod
    def _gate(metric: str, value: float, ref: Dict[str, Any]):
        """Returns (gate_str, flag_str|None)."""
        p5  = ref.get("p5",  float("-inf"))
        p95 = ref.get("p95", float("inf"))
        span = max(0.01, abs(p95 - p5))

        if metric in _LOWER_IS_BETTER:
            p100 = ref.get("p100", p95 + 0.05 * span)
            if value > p100:
                return "FAIL", f"FAIL:{metric}>{p100:.2f}"
            if value > p95:
                return "WARN", f"WARN:{metric}_high"
            return "PASS", None

        p0   = ref.get("p0",   p5  - 0.05 * span)
        p100 = ref.get("p100", p95 + 0.05 * span)
        if value < p0 or value > p100:
            return "FAIL", f"FAIL:{metric}_out_of_range({value:.2f})"
        if value < p5 or value > p95:
            return "WARN", f"WARN:{metric}_edge({value:.2f})"
        return "PASS", None

    # ── Public API ───────────────────────────────────────────────────────────

    def evaluate(self, seq_metrics: Dict[str, float]) -> ClinicalRuleResult:
        """Evaluate a dict of metric→float values against the reference population."""
        result = ClinicalRuleResult()
        gate_counts: Dict[str, int] = {"PASS": 0, "WARN": 0, "FAIL": 0}
        score_components: List[float] = []

        for metric, value in seq_metrics.items():
            if value is None:
                continue
            ref = self._ref.get(metric)
            if ref is None:
                continue
            try:
                fv = float(value)
            except (TypeError, ValueError):
                continue

            band  = self._band(fv, ref)
            gate, flag = self._gate(metric, fv, ref)
            gate_counts[gate] = gate_counts.get(gate, 0) + 1
            if flag:
                result.flags.append(flag)

            p5  = ref.get("p5",  fv)
            p95 = ref.get("p95", fv)
            p50 = ref.get("p50", (p5 + p95) / 2)

            # Component score: 100 at median, scaling linearly to 0 at boundaries
            span = max(0.01, p95 - p5)
            deviation = abs(fv - p50) / span
            component_score = max(0.0, 100.0 - deviation * 100.0)
            score_components.append(component_score)

            result.percentile_ranks[metric] = {
                "value":           fv,
                "band":            band,
                "gate":            gate,
                "ref_p5":          p5,
                "ref_p25":         ref.get("p25"),
                "ref_p50":         p50,
                "ref_p75":         ref.get("p75"),
                "ref_p95":         p95,
                "population":      self.population,
                "n_ref":           self._n,
            }

        result.gate_summary = gate_counts
        result.clinical_score = (
            round(sum(score_components) / len(score_components), 1)
            if score_components else None
        )
        return result


# ─────────────────────────────────────────────────────────────────────────────
# Module-level cache and factory
# ─────────────────────────────────────────────────────────────────────────────

_engine_cache: Dict[str, Optional[ClinicalRuleEngine]] = {}


def get_engine(population: str) -> Optional[ClinicalRuleEngine]:
    """
    Return a ClinicalRuleEngine for the given population, or None if unavailable.

    Populations: "humanized_458" | "vhh_40" | "scfv_84"
    Results are cached after first load.
    """
    if population in _engine_cache:
        return _engine_cache[population]

    ref_path = _REF_PATHS.get(population)
    if ref_path is None or not ref_path.exists():
        _engine_cache[population] = None
        return None

    try:
        with open(ref_path, encoding="utf-8") as f:
            stats = json.load(f)
        engine = ClinicalRuleEngine(population=population, ref_stats=stats)
        _engine_cache[population] = engine
        return engine
    except Exception:
        _engine_cache[population] = None
        return None
