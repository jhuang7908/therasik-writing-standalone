"""
signal_analyzer.py — Detect recurring patterns from RunEvent history.

Scans the RunEventStore for repeated tags/conditions and emits
structured Signal objects that the ProposalEngine converts into
governed OBSERVATION / PROPOSAL entries.

V1 rule set (hardcoded, no ML):
  - TIER2/TIER3 antibodies appearing across multiple runs
  - Repeated missing-target metadata
  - Repeated knowledge-offline events
  - Reports lacking traceability
  - CMC pipelines with recurring FAIL metrics
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.evolution.run_event import RunEvent, RunEventStore


@dataclass
class Signal:
    """A detected recurring pattern worth logging or proposing."""

    signal_id: str
    category: str           # data | report | entrypoint | knowledge | cmc
    severity: str           # info | warning | action_needed
    title: str
    description: str
    occurrence_count: int = 0
    affected_projects: List[str] = field(default_factory=list)
    suggested_action: str = ""
    affected_paths: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)


# Minimum occurrences to trigger a signal (noise filter)
_THRESHOLD_OBSERVATION = 2
_THRESHOLD_PROPOSAL = 4


class SignalAnalyzer:
    """Rule-based pattern detector over RunEvent history.

    Usage::

        store = RunEventStore()
        analyzer = SignalAnalyzer(store)
        signals = analyzer.analyze()
    """

    def __init__(self, store: RunEventStore, observation_threshold: int = _THRESHOLD_OBSERVATION,
                 proposal_threshold: int = _THRESHOLD_PROPOSAL):
        self._store = store
        self._obs_thresh = observation_threshold
        self._prop_thresh = proposal_threshold

    def analyze(self) -> List[Signal]:
        """Run all V1 detection rules and return de-duplicated signals."""
        events = self._store.load_all()
        if not events:
            return []

        signals: List[Signal] = []
        signals.extend(self._detect_tier_patterns(events))
        signals.extend(self._detect_missing_target(events))
        signals.extend(self._detect_knowledge_offline(events))
        signals.extend(self._detect_report_gaps(events))
        signals.extend(self._detect_cmc_failures(events))
        return signals

    def _detect_tier_patterns(self, events: List[RunEvent]) -> List[Signal]:
        """Detect antibodies repeatedly hitting Tier 2 or Tier 3."""
        signals: List[Signal] = []
        for tier in ("TIER2", "TIER3"):
            tier_events = [e for e in events if e.ada_tier == tier]
            if len(tier_events) < self._obs_thresh:
                continue

            projects = list({e.project_id for e in tier_events})
            severity = "action_needed" if len(tier_events) >= self._prop_thresh else "warning"
            signals.append(Signal(
                signal_id=f"ada_{tier.lower()}_recurring",
                category="data",
                severity=severity,
                title=f"Recurring {tier} ADA data across {len(projects)} project(s)",
                description=(
                    f"{len(tier_events)} run(s) encountered {tier} ADA data. "
                    f"Projects: {', '.join(projects[:10])}."
                ),
                occurrence_count=len(tier_events),
                affected_projects=projects,
                suggested_action=(
                    f"Consider {'removing from re-search list' if tier == 'TIER3' else 'prioritizing paid verification'} "
                    f"for these antibodies."
                ),
                affected_paths=["data/ADA_reliable_package/tiered_db/"],
            ))
        return signals

    def _detect_missing_target(self, events: List[RunEvent]) -> List[Signal]:
        """Detect runs repeatedly lacking target/antigen metadata."""
        missing = [e for e in events if "missing_target" in e.tags]
        if len(missing) < self._obs_thresh:
            return []

        projects = list({e.project_id for e in missing})
        entrypoints = list({e.entrypoint for e in missing})
        return [Signal(
            signal_id="missing_target_metadata",
            category="entrypoint",
            severity="warning" if len(missing) < self._prop_thresh else "action_needed",
            title=f"Missing target/antigen metadata in {len(projects)} project(s)",
            description=(
                f"{len(missing)} run(s) had no target specified. "
                f"Entrypoints: {', '.join(entrypoints[:5])}. "
                f"This limits Knowledge Bridge enrichment and report traceability."
            ),
            occurrence_count=len(missing),
            affected_projects=projects,
            suggested_action=(
                "Add --target / TARGET field to input YAML/JSON for these pipelines. "
                "Consider making TARGET a recommended (non-mandatory) input."
            ),
            affected_paths=[f"scripts/{ep}" for ep in entrypoints if not ep.startswith("scripts/")],
        )]

    def _detect_knowledge_offline(self, events: List[RunEvent]) -> List[Signal]:
        """Detect repeated knowledge bridge failures."""
        offline = [e for e in events if e.knowledge_offline]
        if len(offline) < self._obs_thresh:
            return []

        return [Signal(
            signal_id="knowledge_offline_recurring",
            category="knowledge",
            severity="info" if len(offline) < self._prop_thresh else "warning",
            title=f"Knowledge Bridge offline in {len(offline)} run(s)",
            description=(
                f"PubMed/UniProt/PDB enrichment failed or was unavailable. "
                f"Reports generated without live literature context."
            ),
            occurrence_count=len(offline),
            affected_projects=list({e.project_id for e in offline}),
            suggested_action="Check network connectivity or add local cache fallback for critical targets.",
            affected_paths=["core/resources/knowledge_bridge.py"],
        )]

    def _detect_report_gaps(self, events: List[RunEvent]) -> List[Signal]:
        """Detect reports generated without traceability section."""
        no_trace = [e for e in events if "report_no_traceability" in e.tags]
        if len(no_trace) < self._obs_thresh:
            return []

        projects = list({e.project_id for e in no_trace})
        return [Signal(
            signal_id="report_missing_traceability",
            category="report",
            severity="warning" if len(no_trace) < self._prop_thresh else "action_needed",
            title=f"Reports lacking evidence traceability in {len(projects)} project(s)",
            description=(
                f"{len(no_trace)} report(s) were generated without the evidence_traceability section. "
                f"This may indicate the pipeline did not pass evidence_context to the report generator."
            ),
            occurrence_count=len(no_trace),
            affected_projects=projects,
            suggested_action="Ensure all report generators receive evidence_context from EvidenceGate.",
            affected_paths=["core/evaluation/client_report.py", "core/reporting/spec.py"],
        )]

    def _detect_cmc_failures(self, events: List[RunEvent]) -> List[Signal]:
        """Detect CMC pipelines with recurring FAIL metrics."""
        cmc_fails = [e for e in events if "cmc_has_fail" in e.tags]
        if len(cmc_fails) < self._obs_thresh:
            return []

        projects = list({e.project_id for e in cmc_fails})
        return [Signal(
            signal_id="cmc_recurring_fails",
            category="cmc",
            severity="warning",
            title=f"Recurring CMC FAIL metrics in {len(projects)} project(s)",
            description=(
                f"{len(cmc_fails)} CMC evaluation(s) had at least one FAIL metric. "
                f"Projects: {', '.join(projects[:10])}."
            ),
            occurrence_count=len(cmc_fails),
            affected_projects=projects,
            suggested_action="Review common failure modes; consider adjusting formulation or sequence optimization.",
            affected_paths=[],
        )]
