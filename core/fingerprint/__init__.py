"""Clinical Molecular Fingerprint API.

First-pass API for data-backed cohort lookup. It is intentionally read-only and
does not alter existing humanization, CMC, VHH, or bispecific pipelines.
It provides evidence support for engineering scripts and threshold calibration,
not autonomous AI decisions or report-language generation.
Tool developers must query cohort statistics before proposing thresholds.
"""

from .models import FingerprintCohort, FingerprintLookupResult, FingerprintRelease
from .store import DEFAULT_RELEASE_ID, FingerprintStore, default_release

__all__ = [
    "DEFAULT_RELEASE_ID",
    "FingerprintCohort",
    "FingerprintLookupResult",
    "FingerprintRelease",
    "FingerprintStore",
    "default_release",
]
