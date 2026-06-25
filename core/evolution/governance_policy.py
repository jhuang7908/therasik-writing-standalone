"""
governance_policy.py — Machine-readable governance rules.

Mirrors ``docs/ABENGINECORE_GOVERNANCE.md`` Section 3 and the
``evolution-governance.mdc`` Cursor rule.  Used by ProposalEngine
to determine whether a suggestion can be auto-applied or must be
written as a PROPOSAL awaiting owner approval.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path, PurePosixPath
from typing import List

_SUITE_ROOT = Path(__file__).resolve().parents[2]


class FileClass(str, Enum):
    LOCKED = "LOCKED"
    APPEND_ONLY = "APPEND_ONLY"
    TUNABLE = "TUNABLE"
    PROJECT = "PROJECT"
    UNKNOWN = "UNKNOWN"


class ProposalLevel(str, Enum):
    OBSERVATION = "OBSERVATION"
    PROPOSAL = "PROPOSAL"


LOCKED_PATHS: List[str] = [
    "config/vh_vl_humanization_v44.json",
    "config/vh_vl_humanization_v43.json",
    "config/tier_system_config.json",
    "config/abenginecore_registry.json",
    "docs/ABENGINECORE_GOVERNANCE.md",
    "docs/VH_VL_HUMANIZATION_STANDARD_V4.4.md",
    "docs/VH_VL_HUMANIZATION_STANDARD_V4.3.md",
    "docs/VHH_HUMANIZATION_DESIGN_STANDARD.md",
    "docs/VIRTUAL_AFFINITY_MATURATION_STANDARD.md",
    "docs/EPIDESIGNCORE_STANDARD_V1.0.md",
    "docs/STANDARDS_INDEX.md",
    "docs/CURSOR_REPORT_ENGINE_V3.md",
    "scripts/structure_metrics_humanization.py",
    "scripts/ml_vernier_analysis.py",
    "core/structure/affinity_energy_toolkit.py",
    "core/evaluation/evaluator.py",
]

LOCKED_DIRS: List[str] = [
    "data/humanization_assay/",
]

APPEND_ONLY_PATHS: List[str] = [
    "docs/EVOLUTION_LOG.md",
]

PROJECT_PREFIXES: List[str] = [
    "projects/",
    "delivery_",
    "output/",
]


class GovernancePolicy:
    """Stateless governance classifier."""

    def __init__(self, suite_root: str | Path | None = None):
        self._root = Path(suite_root) if suite_root else _SUITE_ROOT

    def classify(self, rel_path: str) -> FileClass:
        """Classify a repo-relative path into governance tiers."""
        norm = rel_path.replace("\\", "/").strip("/")

        if norm in LOCKED_PATHS:
            return FileClass.LOCKED
        for d in LOCKED_DIRS:
            if norm.startswith(d):
                return FileClass.LOCKED
        if norm in APPEND_ONLY_PATHS:
            return FileClass.APPEND_ONLY

        if norm.startswith("docs/") and "_STANDARD" in norm:
            return FileClass.LOCKED
        if norm.startswith("config/") and norm.endswith(".json"):
            return FileClass.LOCKED

        for prefix in PROJECT_PREFIXES:
            if norm.startswith(prefix):
                return FileClass.PROJECT

        return FileClass.UNKNOWN

    def required_level(self, affected_paths: List[str]) -> ProposalLevel:
        """Determine the minimum governance level for a set of changes.

        If ANY affected path is LOCKED or APPEND_ONLY, the proposal
        must be a PROPOSAL (requires owner approval).  Otherwise an
        OBSERVATION is sufficient.
        """
        for p in affected_paths:
            cls = self.classify(p)
            if cls in (FileClass.LOCKED, FileClass.APPEND_ONLY):
                return ProposalLevel.PROPOSAL
        return ProposalLevel.OBSERVATION

    def is_locked(self, rel_path: str) -> bool:
        return self.classify(rel_path) == FileClass.LOCKED

    def can_auto_apply(self, rel_path: str) -> bool:
        cls = self.classify(rel_path)
        return cls in (FileClass.PROJECT, FileClass.UNKNOWN)
