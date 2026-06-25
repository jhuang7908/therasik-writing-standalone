"""
mutation_advisor.py — InSynBio AbEngineCore CMC Mutation Advisor
================================================================
Generates FR-only mutation suggestions for CMC metrics that exceed
their Clinical Reference Cohort gate thresholds.

This module is intentionally rule-driven (no ML). Rules are loaded
from data/rules/cmc_rules_v1.json.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class MutationAdvisor:
    """
    Rule-driven mutation suggestions for CMC optimization.

    Args:
        vh_seq:          VH amino acid sequence
        vl_seq:          VL amino acid sequence (optional)
        metrics:         Dict of computed CMC metrics
        reference_stats: Clinical Reference Cohort reference statistics dict
        rules:           Loaded cmc_rules_v1.json
    """

    def __init__(
        self,
        vh_seq: str,
        vl_seq: str,
        metrics: Dict[str, Any],
        reference_stats: Dict[str, Any],
        rules: Dict[str, Any],
    ) -> None:
        self.vh_seq = (vh_seq or "").strip().upper()
        self.vl_seq = (vl_seq or "").strip().upper()
        self.metrics = metrics or {}
        self.ref     = reference_stats.get("metrics", reference_stats) if reference_stats else {}
        self.rules   = rules or {}

    def advise(self) -> List[Dict[str, Any]]:
        """
        Return a list of mutation suggestion dicts.
        Each dict has: metric, current_value, gate, suggestion, rationale.
        """
        suggestions: List[Dict[str, Any]] = []
        metric_rules: Dict[str, Any] = self.rules.get("metric_rules", {})

        for metric, rule in metric_rules.items():
            value = self.metrics.get(metric)
            if value is None:
                continue
            ref = self.ref.get(metric, {})
            p5  = ref.get("p5",  float("-inf"))
            p95 = ref.get("p95", float("inf"))

            gate = "PASS"
            span = max(0.01, abs(p95 - p5))
            p0   = ref.get("p0",   p5  - 0.05 * span)
            p100 = ref.get("p100", p95 + 0.05 * span)

            if isinstance(value, list):
                fv = len(value)
            else:
                try:
                    fv = float(value)
                except (TypeError, ValueError):
                    continue

            if fv < p0 or fv > p100:
                gate = "FAIL"
            elif fv < p5 or fv > p95:
                gate = "WARN"

            if gate in ("WARN", "FAIL"):
                direction = "too_high" if fv > p95 else "too_low"
                action = rule.get("action_high" if fv > p95 else "action_low", {})
                if action:
                    entry: Dict[str, Any] = {
                        "metric":        metric,
                        "current_value": fv,
                        "gate":          gate,
                        "direction":     direction,
                        "suggestion":    action.get("suggestion", "See developer report for details."),
                        "rationale":     action.get("rationale", ""),
                        "target_range":  f"p5–p95 ({p5:.2f}–{p95:.2f})",
                    }
                    try:
                        from core.cmc.fr_mutation_sites import build_candidate_payload_for_metric
                        sites_payload = build_candidate_payload_for_metric(
                            metric, direction, self.vh_seq, self.vl_seq
                        )
                        if sites_payload:
                            entry["sequence_candidates"] = sites_payload
                    except Exception:
                        pass
                    suggestions.append(entry)

        return suggestions
