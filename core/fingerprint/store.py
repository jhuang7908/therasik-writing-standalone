"""Read-only store for the Clinical Molecular Fingerprint taxonomy V0.

The first release is intentionally a manifest loader, not a scoring engine.
It exposes only data-backed cohorts documented in
`data/_reconciliation/CLINICAL_MOLECULAR_FINGERPRINT_TAXONOMY_V0.md`.

Boundary: this module provides evidence support for design scripts, tool
development, and owner-approved threshold calibration. It does not decide
candidate quality, set thresholds by itself, or write report conclusions.
Any downstream threshold proposal must query the relevant cohort statistics
first and carry source-file/count/release provenance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .models import FingerprintCohort, FingerprintLookupResult, FingerprintRelease, ProfileStatus

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_DOC = "data/_reconciliation/CLINICAL_MOLECULAR_FINGERPRINT_TAXONOMY_V0.md"
DEFAULT_RELEASE_ID = "clinical_molecular_fingerprint_v0.1.0"


def _cohort(
    cohort_id: str,
    molecule_family: str,
    count: int | None,
    status: ProfileStatus,
    primary_use: str,
    source_files: Iterable[str],
    *,
    design_support_allowed: bool,
    threshold_support_allowed: bool,
    notes: Iterable[str] = (),
) -> FingerprintCohort:
    return FingerprintCohort(
        cohort_id=cohort_id,
        molecule_family=molecule_family,
        count=count,
        status=status,
        primary_use=primary_use,
        source_files=tuple(source_files),
        design_support_allowed=design_support_allowed,
        threshold_support_allowed=threshold_support_allowed,
        notes=tuple(notes),
    )


def default_release() -> FingerprintRelease:
    """Return the built-in V0 taxonomy manifest.

    Cohorts are hard-coded here because they are a versioned release boundary.
    Updating these values should happen via a new release ID after reconciliation.
    """

    cohorts = (
        _cohort(
            "clinical_vhh_42",
            "single_domain_vh_vhh",
            42,
            "active",
            "Clinical VHH reference and CMC baseline",
            (
                "data/vhh_clinical_39_union/vhh42_cmc_metrics.csv",
                "data/_reconciliation/VHH_ID_RECONCILIATION_SUMMARY.json",
            ),
            design_support_allowed=True,
            threshold_support_allowed=True,
        ),
        _cohort(
            "clinical_vhh_39",
            "single_domain_vh_vhh",
            39,
            "active",
            "Validated clinical VHH sequence cohort",
            ("data/vhh_clinical_39_union/vhh_39_sequences_clinical_validated.csv",),
            design_support_allowed=True,
            threshold_support_allowed=True,
        ),
        _cohort(
            "sabdab_humanized_vhh_3",
            "single_domain_vh_vhh",
            3,
            "reference",
            "Supplement to clinical VHH42",
            ("data/_reconciliation/VHH_ID_RECONCILIATION_SUMMARY.json",),
            design_support_allowed=False,
            threshold_support_allowed=False,
        ),
        _cohort(
            "humanized_vhh_29",
            "single_domain_vh_vhh",
            29,
            "active_reference",
            "Humanized camelid VHH design reference",
            (
                "data/sabdab_vhh_atlas/humanized_camelid_vhh_db.json",
                "data/_reconciliation/VHH_ID_RECONCILIATION_SUMMARY.json",
            ),
            design_support_allowed=True,
            threshold_support_allowed=False,
            notes=("Small cohort; use with caveat labels.",),
        ),
        _cohort(
            "engineered_vh_24",
            "single_domain_vh_vhh",
            24,
            "active_reference",
            "Engineered VH / VH-to-single-domain reference",
            ("data/vhh_analytics_reports/ENGINEERED_VH24_SITE_MAP.json",),
            design_support_allowed=True,
            threshold_support_allowed=False,
            notes=("Do not compare directly against camelid VHH thresholds.",),
        ),
        _cohort(
            "single_vh_structural_nr_73",
            "single_domain_vh_vhh",
            73,
            "reference",
            "Nonredundant structural distribution",
            ("data/sabdab_vhh_atlas/vhh_dbs_build_stats.json",),
            design_support_allowed=False,
            threshold_support_allowed=False,
        ),
        _cohort(
            "single_vh_raw_138",
            "single_domain_vh_vhh",
            138,
            "raw_only",
            "Search pool and evidence expansion",
            ("data/sabdab_vhh_atlas/autonomous_human_vh_db.json",),
            design_support_allowed=False,
            threshold_support_allowed=False,
            notes=("Raw atlas has 138 entries but only 73 unique PDBs.",),
        ),
        _cohort(
            "humanized_igg_458",
            "vhvl_igg",
            458,
            "active",
            "Humanized/engineered VH/VL IgG reference",
            ("data/engineered_459_atlas/master_table.csv",),
            design_support_allowed=True,
            threshold_support_allowed=True,
        ),
        _cohort(
            "genetically_human_igg_384",
            "vhvl_igg",
            384,
            "active",
            "Fully human / genetically human VH/VL IgG reference",
            ("data/natural_380_atlas/master_table.csv",),
            design_support_allowed=True,
            threshold_support_allowed=True,
        ),
        _cohort(
            "standard_igg_overlay",
            "vhvl_igg",
            758,
            "active_reference",
            "Standard monospecific IgG context",
            (
                "data/engineered_459_atlas/master_table.csv",
                "data/natural_380_atlas/master_table.csv",
            ),
            design_support_allowed=True,
            threshold_support_allowed=False,
            notes=("Overlay count is 401 engineered + 357 natural.",),
        ),
        _cohort(
            "adc_igg_overlay",
            "vhvl_igg",
            53,
            "reference",
            "ADC modality overlay",
            (
                "data/engineered_459_atlas/master_table.csv",
                "data/natural_380_atlas/master_table.csv",
                "data/ada_master_136_curated.csv",
            ),
            design_support_allowed=False,
            threshold_support_allowed=False,
            notes=("Overlay count is 34 engineered + 14 natural + 5 ADA.",),
        ),
        _cohort(
            "fusion_igg_overlay",
            "vhvl_igg",
            13,
            "reference",
            "Fusion modality overlay",
            (
                "data/engineered_459_atlas/master_table.csv",
                "data/natural_380_atlas/master_table.csv",
            ),
            design_support_allowed=False,
            threshold_support_allowed=False,
        ),
        _cohort(
            "transgenic_mouse",
            "vhvl_igg",
            None,
            "reserved",
            "Future fully human source stratification",
            (),
            design_support_allowed=False,
            threshold_support_allowed=False,
            notes=("Current data lacks stable discovery modality fields.",),
        ),
        _cohort(
            "phage_display",
            "vhvl_igg",
            None,
            "reserved",
            "Future fully human source stratification",
            (),
            design_support_allowed=False,
            threshold_support_allowed=False,
            notes=("Current data lacks stable discovery modality fields.",),
        ),
        _cohort(
            "b_cell_sorting",
            "vhvl_igg",
            None,
            "reserved",
            "Future fully human source stratification",
            (),
            design_support_allowed=False,
            threshold_support_allowed=False,
            notes=("Current data lacks stable discovery modality fields.",),
        ),
        _cohort(
            "bispecific_125_all",
            "bispecific_multispecific",
            125,
            "active_reference",
            "Overall bispecific engineering reference",
            ("data/design_rules/bispecific_125_knowledge.json",),
            design_support_allowed=True,
            threshold_support_allowed=False,
            notes=("Includes some higher-valency records labeled as bispecific entries.",),
        ),
        _cohort(
            "bispecific_igg_like_75",
            "bispecific_multispecific",
            75,
            "active_reference",
            "IgG-like Bi-Ab reference",
            ("data/design_rules/bispecific_125_igg_like.json",),
            design_support_allowed=True,
            threshold_support_allowed=False,
        ),
        _cohort(
            "bispecific_scfv_like_50",
            "bispecific_multispecific",
            50,
            "active_reference",
            "scFv-like, BiTE, tandem scFv, mixed mAb+scFv reference",
            ("data/design_rules/bispecific_125_scfv_like.json",),
            design_support_allowed=True,
            threshold_support_allowed=False,
        ),
        _cohort(
            "scfv_like_50_sequence_template",
            "bispecific_multispecific",
            50,
            "reference",
            "Sequence template support for scFv-like subset",
            ("data/design_rules/scfv_like_50_sequences_template.csv",),
            design_support_allowed=False,
            threshold_support_allowed=False,
        ),
        _cohort(
            "ada_bispecific_overlap_6",
            "bispecific_multispecific",
            6,
            "reference",
            "ADA overlap only; not a bispecific cohort",
            ("data/_reconciliation/ADA_ID_RECONCILIATION_SUMMARY.json",),
            design_support_allowed=False,
            threshold_support_allowed=False,
        ),
        _cohort(
            "ada_panel_136",
            "ada_immunogenicity",
            136,
            "active",
            "Frozen positive ADA panel with germline/CMC annotations",
            ("data/immunogenicity_knowledge_base/master/immunogenicity_panel_136_master.csv",),
            design_support_allowed=True,
            threshold_support_allowed=True,
        ),
        _cohort(
            "ada_master_154",
            "ada_immunogenicity",
            154,
            "active_reference",
            "Curated ADA master copy",
            ("data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv",),
            design_support_allowed=True,
            threshold_support_allowed=False,
        ),
        _cohort(
            "ada_combined_146",
            "ada_immunogenicity",
            146,
            "reference",
            "Combined ADA DB; needs mismatch cleanup",
            ("data/immunogenicity_knowledge_base/InSynBio_Combined_ADA_Database.csv",),
            design_support_allowed=False,
            threshold_support_allowed=False,
            notes=("Seven ADA% mismatches must be resolved before active use.",),
        ),
        _cohort(
            "ada_negative_312",
            "ada_immunogenicity",
            312,
            "active_reference",
            "Negative/reference library",
            ("data/immunogenicity_knowledge_base/master/ada_negative_library_by_phase.csv",),
            design_support_allowed=True,
            threshold_support_allowed=False,
        ),
        _cohort(
            "ada_gap_66",
            "ada_immunogenicity",
            66,
            "curation_backlog",
            "Known missing metadata list",
            ("data/immunogenicity_knowledge_base/master/ada_curation_gap_list.csv",),
            design_support_allowed=False,
            threshold_support_allowed=False,
        ),
    )
    return FingerprintRelease(
        release_id=DEFAULT_RELEASE_ID,
        status="draft",
        taxonomy_doc=TAXONOMY_DOC,
        cohorts=cohorts,
    )


class FingerprintStore:
    """In-memory read-only view of a fingerprint release manifest."""

    def __init__(self, release: FingerprintRelease):
        self.release = release
        self._by_id = {c.cohort_id: c for c in release.cohorts}
        self._by_family: dict[str, tuple[FingerprintCohort, ...]] = {}
        for cohort in release.cohorts:
            self._by_family.setdefault(cohort.molecule_family, tuple())
            self._by_family[cohort.molecule_family] += (cohort,)

    @classmethod
    def load_default(cls) -> "FingerprintStore":
        return cls(default_release())

    def list_families(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_family))

    def list_cohorts(
        self,
        molecule_family: str | None = None,
        *,
        include_reserved: bool = False,
    ) -> tuple[FingerprintCohort, ...]:
        cohorts = self.release.cohorts if molecule_family is None else self._by_family.get(molecule_family, ())
        if include_reserved:
            return tuple(cohorts)
        return tuple(c for c in cohorts if c.status != "reserved")

    def get_cohort(self, cohort_id: str) -> FingerprintCohort:
        try:
            return self._by_id[cohort_id]
        except KeyError as exc:
            raise KeyError(f"Unknown fingerprint cohort: {cohort_id}") from exc

    def resolve(
        self,
        *,
        molecule_family: str | None = None,
        cohort_id: str | None = None,
        allow_fallback: bool = True,
    ) -> FingerprintLookupResult:
        """Resolve a cohort request with explicit fallback reporting."""

        if cohort_id:
            cohort = self._by_id.get(cohort_id)
            if cohort and (molecule_family is None or cohort.molecule_family == molecule_family):
                if cohort.status == "reserved" and allow_fallback:
                    candidates = self.list_cohorts(cohort.molecule_family, include_reserved=False)
                    active = tuple(c for c in candidates if c.status == "active")
                    fallback = active[0] if active else (candidates[0] if candidates else None)
                    return FingerprintLookupResult(
                        molecule_family,
                        cohort_id,
                        fallback,
                        True,
                        "Requested cohort is reserved because current data lacks stable support.",
                    )
                return FingerprintLookupResult(molecule_family, cohort_id, cohort, False)
            if not allow_fallback:
                return FingerprintLookupResult(
                    molecule_family,
                    cohort_id,
                    None,
                    False,
                    f"Requested cohort not found: {cohort_id}",
                )

        if not allow_fallback:
            return FingerprintLookupResult(molecule_family, cohort_id, None, False, "No fallback allowed")

        candidates = self.list_cohorts(molecule_family, include_reserved=False)
        active = tuple(c for c in candidates if c.status == "active")
        if active:
            return FingerprintLookupResult(
                molecule_family,
                cohort_id,
                active[0],
                True,
                "Fallback used because requested cohort was missing or unavailable.",
            )
        if candidates:
            return FingerprintLookupResult(
                molecule_family,
                cohort_id,
                candidates[0],
                True,
                "Fallback used to first non-reserved cohort; no active cohort is available.",
            )
        return FingerprintLookupResult(molecule_family, cohort_id, None, False, "No cohort available")

    def to_dict(self) -> dict:
        return self.release.to_dict()
