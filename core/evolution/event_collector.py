"""
event_collector.py — Non-invasive RunEvent factory.

Converts outputs from EvidenceGate, CLI exit codes, evaluation results,
and report metadata into normalized RunEvent objects.  Each factory
method corresponds to one integration point in the suite.

Usage from a CLI entrypoint (post-run)::

    from core.evolution.event_collector import EventCollector

    collector = EventCollector()
    event = collector.from_evidence_gate(
        project_id="my_ab",
        family="vhvl_humanization",
        entrypoint="run_engineering_pipeline.py",
        evidence_ctx=ctx,
        exit_code=0,
    )
    collector.store.append(event)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.evolution.run_event import RunEvent, RunEventStore


class EventCollector:
    """Stateless factory + store handle for RunEvent collection."""

    def __init__(self, store: Optional[RunEventStore] = None):
        self.store = store or RunEventStore()

    def from_evidence_gate(
        self,
        project_id: str,
        family: str,
        entrypoint: str,
        evidence_ctx: Any = None,
        exit_code: Optional[int] = None,
    ) -> RunEvent:
        """Build a RunEvent from an EvidenceContext object.

        Works with both ``core.resources.evidence_gate.EvidenceContext``
        dataclass instances and plain dicts (like CAR-T's evidence_context).
        """
        ev = RunEvent(
            project_id=project_id,
            family=family,
            entrypoint=entrypoint,
            exit_code=exit_code,
            status="ok" if exit_code == 0 else ("fail" if exit_code else "unknown"),
        )

        if evidence_ctx is None:
            ev.tags.append("no_evidence_gate")
            return ev

        if isinstance(evidence_ctx, dict):
            ev.ada_tier = evidence_ctx.get("ada_tier", "NOT_CHECKED")
            ev.ada_value = evidence_ctx.get("ada_value")
            ev.needs_disclaimer = evidence_ctx.get("needs_disclaimer", False)
            ev.target = evidence_ctx.get("target", "")
            ev.pubmed_hits = evidence_ctx.get("pubmed_hit_count", 0)
            ev.knowledge_offline = ev.ada_tier == "OFFLINE"
        else:
            ev.ada_tier = getattr(evidence_ctx, "ada_tier", "NOT_CHECKED")
            ev.ada_value = getattr(evidence_ctx, "ada_value", None)
            ev.needs_disclaimer = getattr(evidence_ctx, "needs_disclaimer", False)
            ev.target = getattr(evidence_ctx, "target", "")
            ev.pubmed_hits = len(getattr(evidence_ctx, "pubmed_hits", []))
            ev.pdb_hits = len(getattr(evidence_ctx, "pdb_hits", []))
            ev.knowledge_offline = ev.ada_tier == "OFFLINE"

        if ev.ada_tier in ("TIER2", "TIER3"):
            ev.tags.append(f"ada_{ev.ada_tier.lower()}")
        if ev.needs_disclaimer:
            ev.tags.append("disclaimer_needed")
        if ev.knowledge_offline:
            ev.tags.append("knowledge_offline")
        if not ev.target:
            ev.tags.append("missing_target")

        return ev

    def from_cmc_result(
        self,
        project_id: str,
        family: str,
        entrypoint: str,
        n_pass: int = 0,
        n_warn: int = 0,
        n_fail: int = 0,
        adi_score: Optional[float] = None,
        evidence_ctx: Any = None,
        exit_code: Optional[int] = None,
    ) -> RunEvent:
        """Build a RunEvent from CMC evaluation metrics."""
        ev = self.from_evidence_gate(
            project_id=project_id,
            family=family,
            entrypoint=entrypoint,
            evidence_ctx=evidence_ctx,
            exit_code=exit_code,
        )
        ev.n_pass = n_pass
        ev.n_warn = n_warn
        ev.n_fail = n_fail
        if adi_score is not None:
            ev.extra["adi_score"] = adi_score
        if n_fail > 0:
            ev.tags.append("cmc_has_fail")
        return ev

    def from_vam_result(
        self,
        project_id: str,
        entrypoint: str,
        tools_used: List[str],
        n_mutations: int = 0,
        evidence_ctx: Any = None,
        exit_code: Optional[int] = None,
    ) -> RunEvent:
        """Build a RunEvent from VAM affinity scan."""
        ev = self.from_evidence_gate(
            project_id=project_id,
            family="vam",
            entrypoint=entrypoint,
            evidence_ctx=evidence_ctx,
            exit_code=exit_code,
        )
        ev.extra["tools_used"] = tools_used
        ev.extra["n_mutations"] = n_mutations
        return ev

    def from_car_result(
        self,
        project_id: str,
        target: str,
        indication: str,
        evidence_context_dict: Optional[Dict[str, Any]] = None,
        score: Optional[Dict[str, Any]] = None,
    ) -> RunEvent:
        """Build a RunEvent from CARDesigner.design() output."""
        ev = self.from_evidence_gate(
            project_id=project_id,
            family="car_design",
            entrypoint="CARDesigner.design",
            evidence_ctx=evidence_context_dict,
            exit_code=0,
        )
        ev.target = target
        if indication:
            ev.extra["indication"] = indication
        if score:
            ev.extra["construct_score"] = score
        return ev

    def from_report_output(
        self,
        project_id: str,
        family: str,
        report_generated: bool = True,
        has_traceability: bool = False,
        has_disclaimer: bool = False,
    ) -> RunEvent:
        """Build a RunEvent from report generation metadata."""
        ev = RunEvent(
            project_id=project_id,
            family=family,
            entrypoint="report_output",
            report_generated=report_generated,
            has_traceability=has_traceability,
            needs_disclaimer=has_disclaimer,
        )
        if not has_traceability:
            ev.tags.append("report_no_traceability")
        if has_disclaimer:
            ev.tags.append("report_has_disclaimer")
        return ev

    def emit(self, event: RunEvent) -> None:
        """Convenience: append event to store."""
        self.store.append(event)
