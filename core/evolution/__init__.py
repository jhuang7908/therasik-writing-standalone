"""
core.evolution — InSynBio Self-Evolution Architecture V1
=========================================================
Proposal-only self-improvement loop that observes project runs,
detects recurring quality/evidence signals, and generates governed
OBSERVATION / PROPOSAL entries without modifying locked core files.

Public API::

    from core.evolution import (
        RunEvent,
        EventCollector,
        SignalAnalyzer,
        ProposalEngine,
        GovernancePolicy,
    )
"""
from core.evolution.run_event import RunEvent, RunEventStore
from core.evolution.governance_policy import GovernancePolicy
from core.evolution.event_collector import EventCollector
from core.evolution.signal_analyzer import SignalAnalyzer, Signal
from core.evolution.proposal_engine import ProposalEngine

__all__ = [
    "RunEvent",
    "RunEventStore",
    "GovernancePolicy",
    "EventCollector",
    "SignalAnalyzer",
    "Signal",
    "ProposalEngine",
]
