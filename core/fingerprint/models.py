"""Clinical molecular fingerprint data models.

This module is intentionally JSON-first and read-only. It defines the small
contract used by the fingerprint store without importing pipeline engines.
The fingerprint layer is evidence support for tool design and threshold
calibration; it must not make autonomous AI judgments or render reports.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ProfileStatus = Literal[
    "active",
    "active_reference",
    "reference",
    "raw_only",
    "curation_backlog",
    "reserved",
]


@dataclass(frozen=True)
class FingerprintCohort:
    """One data-backed cohort or reserved taxonomy node."""

    cohort_id: str
    molecule_family: str
    count: int | None
    status: ProfileStatus
    primary_use: str
    source_files: tuple[str, ...] = field(default_factory=tuple)
    design_support_allowed: bool = False
    threshold_support_allowed: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FingerprintRelease:
    """Versioned manifest for the clinical molecular fingerprint taxonomy."""

    release_id: str
    status: str
    taxonomy_doc: str
    cohorts: tuple[FingerprintCohort, ...]

    def cohort_ids(self) -> tuple[str, ...]:
        return tuple(c.cohort_id for c in self.cohorts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "release_id": self.release_id,
            "status": self.status,
            "taxonomy_doc": self.taxonomy_doc,
            "cohorts": [c.to_dict() for c in self.cohorts],
        }


@dataclass(frozen=True)
class FingerprintLookupResult:
    """Result returned by cohort lookup, including fallback information."""

    requested_family: str | None
    requested_cohort_id: str | None
    matched: FingerprintCohort | None
    fallback_used: bool
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_family": self.requested_family,
            "requested_cohort_id": self.requested_cohort_id,
            "matched": self.matched.to_dict() if self.matched else None,
            "fallback_used": self.fallback_used,
            "warning": self.warning,
        }
