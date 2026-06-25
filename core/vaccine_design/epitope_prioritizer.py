"""
core/vaccine_design/epitope_prioritizer.py
──────────────────────────────────────────
Three-layer epitope prioritization pipeline:

  Layer 1 — SelfToleranceFilter
      Reject peptides that match a small curated self-seed set, or show
      insufficient DAI vs wild-type (WT binding + anchor rules).  A full
      human proteome k-mer DB is optional (large disk/RAM); off by default —
      set env INSYNBIO_USE_PROTEOME_KMER_DB=1 only after building it.

  Layer 2 — ExpressionWeighter
      Up-weight epitopes from genes that are overexpressed in the
      target tumor relative to normal tissue (TCGA/GTEx medians).

  Layer 3 — EpitopeCoverageOptimizer
      Greedy set-cover: select N epitopes to maximise HLA population
      coverage in a target ethnic group, weighted by composite score.

Composite score formula:
    S = presentation_score
      × expression_weight
      × (1 + 0.3 × max(DAI, 0))   # DAI bonus for neoantigens
      × tolerance_pass             # hard gate (0 or 1)

Usage:
    prioritizer = EpitopePrioritizer(cancer_type="LUAD")
    ranked = prioritizer.prioritize(candidates)          # List[EpitopeCandidate]
    vaccine_set = prioritizer.select_for_vaccine(n=10)   # coverage-optimised
"""
from __future__ import annotations

import logging
import math
import os
import pickle
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Tuple

__version__ = "1.0.0"

logger = logging.getLogger(__name__)


# ── constants ─────────────────────────────────────────────────────────────────

# HLA anchor positions (0-indexed) for common lengths
# MHC-I anchor: P2 (index 1) and C-terminus (index -1)
_ANCHOR_OFFSETS = {8: (1, 7), 9: (1, 8), 10: (1, 9), 11: (1, 10)}

# Tolerance veto thresholds
_WT_BIND_VETO_NM  = 500.0   # if WT affinity < this → likely presented in thymus
_DAI_MINIMUM      = 0.0     # DAI must be > 0 (mut binds better than WT)

# MHCflurry SB percentile for self-peptide check
_SELF_SB_PERCENTILE = 2.0

# Expression weight caps
_MAX_EXPR_WEIGHT = 8.0
_MIN_EXPR_WEIGHT = 0.5


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1: Self-tolerance filter
# ─────────────────────────────────────────────────────────────────────────────

# Curated set of canonical human peptides known to be self-presented.
# Source: SYFPEITHI + IEDB + manual curation.  This is the SEED set; the full
# proteome-derived set must be built with build_self_tolerance_db.py.
_SEED_SELF_PEPTIDES: Set[str] = {
    # HLA-A*02:01 high-confidence self-epitopes
    "NLVPMVATV",  # CMV pp65 cross-reactive self (not a true self but used as ref)
    "GLCTLVAML",  # EBV BMLF1 — known cross-reactive
    "FLPSDFFPSV", "KTWGQYWQV", "LLFGYPVYV",
    # Common HLA-B*07:02 self-presented
    "RPPIFIRRL", "IPNSSPTGL",
}

# Optional full proteome k-mer DB (~80 MB compressed on disk; ~hundreds MB RAM
# when loaded).  Disabled by default so laptops/CI never touch it.
# Enable only after: python scripts/build_self_tolerance_db.py
#   then: set INSYNBIO_USE_PROTEOME_KMER_DB=1
_KMER_DB_PATH = os.path.expanduser("~/.insynbio/human_proteome_kmers.pkl.gz")
_ENV_ENABLE_KMER = "INSYNBIO_USE_PROTEOME_KMER_DB"


def _proteome_kmer_db_enabled() -> bool:
    v = os.environ.get(_ENV_ENABLE_KMER, "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _load_kmer_db() -> Optional[Set[str]]:
    """Load pre-built human proteome 8-11mer set only if explicitly enabled.

    Returns None when disabled (default), missing file, or load error.
    """
    if not _proteome_kmer_db_enabled():
        logger.debug(
            "Proteome k-mer DB skipped (set %s=1 to enable after building)",
            _ENV_ENABLE_KMER,
        )
        return None
    if not os.path.exists(_KMER_DB_PATH):
        logger.warning(
            "%s=1 but file missing: %s — using seed self-peptides only",
            _ENV_ENABLE_KMER,
            _KMER_DB_PATH,
        )
        return None
    import gzip
    try:
        with gzip.open(_KMER_DB_PATH, "rb") as fh:
            db = pickle.load(fh)
        logger.info("Loaded human proteome k-mer DB: %d entries", len(db))
        return db
    except Exception as exc:
        logger.warning("Failed to load k-mer DB: %s", exc)
        return None


# Cached result of a single load attempt (None = use seed only; non-None = full set)
_KMER_DB: Optional[Set[str]] = None
_KMER_DB_RESOLVED: bool = False


def _get_kmer_db() -> Optional[Set[str]]:
    """Return proteome k-mer set once, or None when disabled / missing / failed."""
    global _KMER_DB, _KMER_DB_RESOLVED
    if not _KMER_DB_RESOLVED:
        _KMER_DB = _load_kmer_db()
        _KMER_DB_RESOLVED = True
    return _KMER_DB


def _check_proteome_hit(peptide: str) -> bool:
    """Return True if peptide exactly matches a normal human protein sequence."""
    db = _get_kmer_db()
    if db is not None:
        return peptide.upper() in db

    # Default: seed set only (~10 peptides) + DAI/WT rules in filter()
    return peptide.upper() in _SEED_SELF_PEPTIDES


def _is_anchor_mutation(wt_peptide: str, mut_peptide: str) -> bool:
    """Return True if mutation is at a MHC-I anchor position (P2 or C-term)."""
    if not wt_peptide or not mut_peptide:
        return False
    plen = len(mut_peptide)
    anchors = _ANCHOR_OFFSETS.get(plen)
    if anchors is None:
        return False
    p2_idx, ctail_idx = anchors
    for i, (waa, maa) in enumerate(zip(wt_peptide, mut_peptide)):
        if waa != maa and i in (p2_idx, ctail_idx):
            return True
    return False


@dataclass
class ToleranceVerdict:
    peptide: str
    in_proteome: bool          # exact match in human proteome
    wt_binds_well: bool        # WT affinity < 500 nM  → thymic tolerance likely
    dai_positive: bool         # DAI > 0  → mut binds better than WT
    anchor_mutation: bool      # mutation at P2 or C-anchor → escape-prone
    pass_filter: bool          # True = keep this epitope
    reason: str


class SelfToleranceFilter:
    """
    Layer 1 — reject epitopes that are:
      a) Exact matches to a normal human protein sequence, OR
      b) WT peptide binds MHC well (< 500 nM) AND DAI ≤ 0
         (mutant is no better binder than WT → no immunogenic advantage)

    Anchor-position mutations get a pass-through bonus because P2/C-tail
    mutations disrupt both central tolerance induction AND increase
    immunogenicity of the neoantigenic peptide.

    By default, (a) uses only a small seed self-peptide list plus DAI/WT rules —
    no large download.  Optional full proteome lookup (~80 MB+ on disk, high RAM
    when loaded): build with ``python scripts/build_self_tolerance_db.py``, then
    set environment variable ``INSYNBIO_USE_PROTEOME_KMER_DB=1``.
    """

    def __init__(
        self,
        veto_wt_affinity_nm: float = _WT_BIND_VETO_NM,
        min_dai: float = _DAI_MINIMUM,
        require_anchor_override: bool = True,
    ):
        self.veto_wt_affinity_nm = veto_wt_affinity_nm
        self.min_dai = min_dai
        self.require_anchor_override = require_anchor_override

    def filter(
        self,
        peptide: str,
        wt_peptide: str = "",
        wt_affinity_nm: float = 9999.0,
        dai: float = 0.0,
    ) -> ToleranceVerdict:
        peptide = peptide.upper()
        in_proteome = _check_proteome_hit(peptide)
        wt_binds_well = wt_affinity_nm < self.veto_wt_affinity_nm
        dai_positive = dai > self.min_dai
        anchor_mut = _is_anchor_mutation(wt_peptide, peptide) if wt_peptide else False

        # Decision logic
        if in_proteome:
            # If the mutant peptide is itself in the normal proteome, it cannot
            # be neoantigen-specific.
            pass_filter = False
            reason = "SELF_SEQUENCE: exact match in normal human proteome"
        elif wt_binds_well and not dai_positive and not anchor_mut:
            # WT was likely thymic-presented; mutant offers no binding advantage;
            # no anchor-position escape → very likely tolerized.
            pass_filter = False
            reason = (
                f"WT_TOLERIZED: WT binds at {wt_affinity_nm:.0f} nM "
                f"(< {self.veto_wt_affinity_nm} nM), DAI={dai:.2f} ≤ 0, "
                f"no anchor mutation → thymic tolerance likely"
            )
        elif wt_binds_well and not dai_positive and anchor_mut:
            # WT was thymic-presented but anchor mutation disrupts WT processing.
            # Borderline — pass with caveat.
            pass_filter = True
            reason = (
                f"ANCHOR_RESCUE: WT binds at {wt_affinity_nm:.0f} nM but "
                f"anchor-position mutation disrupts WT MHC loading → pass"
            )
        else:
            pass_filter = True
            reason = "PASS"
            if not wt_peptide:
                reason = "PASS (no WT sequence provided — TAA mode, tolerance not checked)"

        return ToleranceVerdict(
            peptide=peptide,
            in_proteome=in_proteome,
            wt_binds_well=wt_binds_well,
            dai_positive=dai_positive,
            anchor_mutation=anchor_mut,
            pass_filter=pass_filter,
            reason=reason,
        )

    def batch_filter(
        self,
        records: List[Dict],
    ) -> List[ToleranceVerdict]:
        """Filter a list of dicts with keys: peptide, wt_peptide, wt_affinity_nm, dai."""
        return [
            self.filter(
                peptide=r.get("peptide", ""),
                wt_peptide=r.get("wt_peptide", ""),
                wt_affinity_nm=r.get("wt_affinity_nm", 9999.0),
                dai=r.get("dai", 0.0),
            )
            for r in records
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2: Expression weighter
# ─────────────────────────────────────────────────────────────────────────────

# Mini expression table: (tumor_median_tpm, normal_median_tpm)
# Sources:
#   Tumor: TCGA GDC portal, cancer-type median from HTSeq-counts → TPM conversion
#   Normal: GTEx v8 median per-tissue TPM (closest matched tissue)
# Cancer type codes: LUAD, COAD, SKCM, BRCA, PRAD, GBM, PAAD, HNSC, OV, BLCA
_EXPRESSION_TABLE: Dict[str, Dict[str, Tuple[float, float]]] = {
    # gene: {cancer_type: (tumor_tpm, normal_tpm)}
    "KRAS": {
        "LUAD": (62.0, 18.0), "COAD": (28.0, 20.0), "PAAD": (45.0, 16.0),
        "SKCM": (18.0, 15.0), "BRCA": (25.0, 22.0), "global": (30.0, 18.0),
    },
    "TP53": {
        "LUAD": (280.0, 120.0), "COAD": (260.0, 110.0), "BRCA": (320.0, 130.0),
        "SKCM": (310.0, 125.0), "GBM": (350.0, 100.0), "global": (290.0, 115.0),
    },
    "BRAF": {
        "SKCM": (180.0, 40.0), "COAD": (80.0, 35.0), "LUAD": (60.0, 38.0),
        "PAAD": (55.0, 32.0), "global": (90.0, 38.0),
    },
    "EGFR": {
        "LUAD": (320.0, 60.0), "HNSC": (280.0, 120.0), "GBM": (420.0, 45.0),
        "BRCA": (180.0, 70.0), "global": (250.0, 65.0),
    },
    "ERBB2": {
        "BRCA": (380.0, 40.0), "GC": (300.0, 35.0), "LUAD": (95.0, 38.0),
        "global": (180.0, 38.0),
    },
    "MYC": {
        "BRCA": (250.0, 80.0), "LUAD": (220.0, 75.0), "COAD": (280.0, 90.0),
        "DLBC": (480.0, 85.0), "global": (260.0, 82.0),
    },
    "CDKN2A": {
        "SKCM": (320.0, 12.0), "LUAD": (180.0, 15.0), "COAD": (160.0, 14.0),
        "PAAD": (220.0, 10.0), "global": (200.0, 13.0),
    },
    "PIK3CA": {
        "BRCA": (340.0, 220.0), "COAD": (310.0, 200.0), "LUAD": (290.0, 210.0),
        "global": (310.0, 210.0),
    },
    "PTEN": {
        "GBM": (90.0, 280.0), "BRCA": (120.0, 240.0), "PRAD": (80.0, 260.0),
        "global": (100.0, 270.0),  # suppressor — lower in tumor
    },
    "IDH1": {
        "GBM": (320.0, 280.0), "LGG": (380.0, 270.0), "global": (340.0, 275.0),
    },
    "NRAS": {
        "SKCM": (180.0, 60.0), "global": (100.0, 58.0),
    },
    # Cancer-testis antigens (very low/absent in normal somatic tissue)
    "CTAG1B": {  # NY-ESO-1
        "SKCM": (120.0, 0.4), "OV": (180.0, 0.3), "LUAD": (60.0, 0.2),
        "global": (90.0, 0.3),
    },
    "MAGEA3": {
        "SKCM": (90.0, 0.2), "LUAD": (50.0, 0.15), "BRCA": (40.0, 0.1),
        "global": (60.0, 0.15),
    },
    "MAGEA1": {
        "SKCM": (70.0, 0.1), "LUAD": (35.0, 0.1), "global": (45.0, 0.1),
    },
    "SSX2": {
        "SKCM": (55.0, 0.05), "global": (30.0, 0.05),
    },
    # Tumour-suppressor context (often high expression of mutant allele)
    "RB1": {
        "SKCM": (130.0, 180.0), "LUAD": (120.0, 175.0), "global": (125.0, 178.0),
    },
    "APC": {
        "COAD": (280.0, 240.0), "global": (270.0, 238.0),
    },
    "BRCA1": {
        "BRCA": (160.0, 180.0), "OV": (140.0, 175.0), "global": (150.0, 178.0),
    },
    "BRCA2": {
        "BRCA": (120.0, 140.0), "global": (115.0, 138.0),
    },
    "VHL": {
        "KIRC": (80.0, 160.0), "global": (85.0, 158.0),
    },
    # Kinases frequently amplified
    "ALK": {
        "LUAD": (85.0, 8.0), "ALCL": (620.0, 7.0), "global": (80.0, 8.0),
    },
    "MET": {
        "LUAD": (120.0, 30.0), "GC": (180.0, 35.0), "global": (100.0, 32.0),
    },
    "RET": {
        "THCA": (280.0, 20.0), "LUAD": (45.0, 18.0), "global": (60.0, 19.0),
    },
    "FGFR3": {
        "BLCA": (180.0, 40.0), "global": (100.0, 38.0),
    },
    "PDGFRA": {
        "GBM": (340.0, 25.0), "global": (80.0, 24.0),
    },
    # Immune checkpoints (often expressed in TME)
    "CD274": {  # PD-L1
        "LUAD": (80.0, 12.0), "SKCM": (120.0, 10.0), "global": (75.0, 11.0),
    },
    "CTLA4": {
        "global": (8.0, 2.0),
    },
}

# Fallback for any gene not in table
_DEFAULT_EXPR = (50.0, 50.0)  # neutral weight = 1.0


@dataclass
class ExpressionScore:
    gene: str
    cancer_type: str
    tumor_tpm: float
    normal_tpm: float
    diff_ratio: float
    weight: float
    source: str  # "table" | "default"


class ExpressionWeighter:
    """
    Layer 2 — weight epitope by source-gene tumor expression and
    differential expression vs normal tissue.

    Weight formula:
        expr_weight = log2(tumor_tpm + 1)
                    × clamp(diff_ratio, 1, max_weight)
                    / log2(50 + 1)   # normalise so 50 TPM, equal expr → 1.0

    Where:
        diff_ratio = tumor_tpm / max(normal_tpm, 0.1)
        log2(50+1) ≈ 5.67 — normalisation constant (median expressed gene)

    Result is clamped to [min_weight, max_weight].

    Extend the expression table by passing custom_table at construction, or
    call ExpressionWeighter.add_gene() to add your own TCGA-derived values.
    """

    _NORM_FACTOR = math.log2(50.0 + 1)  # ≈ 5.67

    def __init__(
        self,
        cancer_type: str = "global",
        custom_table: Optional[Dict] = None,
        max_weight: float = _MAX_EXPR_WEIGHT,
        min_weight: float = _MIN_EXPR_WEIGHT,
    ):
        self.cancer_type = cancer_type
        self.table = dict(_EXPRESSION_TABLE)
        if custom_table:
            self.table.update(custom_table)
        self.max_weight = max_weight
        self.min_weight = min_weight

    def add_gene(
        self,
        gene: str,
        tumor_tpm: float,
        normal_tpm: float,
        cancer_type: Optional[str] = None,
    ) -> None:
        """Register a custom gene expression entry at runtime."""
        ct = cancer_type or self.cancer_type
        if gene not in self.table:
            self.table[gene] = {}
        self.table[gene][ct] = (tumor_tpm, normal_tpm)

    def score(self, gene: str, cancer_type: Optional[str] = None) -> ExpressionScore:
        ct = cancer_type or self.cancer_type
        gene_upper = gene.upper()
        gene_data = self.table.get(gene_upper, {})

        if not gene_data:
            tumor_tpm, normal_tpm = _DEFAULT_EXPR
            source = "default"
        elif ct in gene_data:
            tumor_tpm, normal_tpm = gene_data[ct]
            source = "table"
        elif "global" in gene_data:
            tumor_tpm, normal_tpm = gene_data["global"]
            source = "table-global"
        else:
            tumor_tpm, normal_tpm = list(gene_data.values())[0]
            source = "table-other"

        diff_ratio = tumor_tpm / max(normal_tpm, 0.1)
        raw_weight = (math.log2(tumor_tpm + 1) / self._NORM_FACTOR) * max(1.0, diff_ratio)
        weight = round(
            min(self.max_weight, max(self.min_weight, raw_weight)), 3
        )

        return ExpressionScore(
            gene=gene_upper,
            cancer_type=ct,
            tumor_tpm=round(tumor_tpm, 1),
            normal_tpm=round(normal_tpm, 1),
            diff_ratio=round(diff_ratio, 2),
            weight=weight,
            source=source,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3: Coverage-weighted epitope optimizer
# ─────────────────────────────────────────────────────────────────────────────

# Population HLA phenotype frequencies (from population_coverage.py, mirrored here
# to keep this module self-contained)
from .population_coverage import HLA_FREQ, POPULATIONS


@dataclass
class CoverageStep:
    step: int
    epitope_idx: int
    peptide: str
    allele: str
    composite_score: float
    delta_coverage: Dict[str, float]
    cumulative_coverage: Dict[str, float]


class EpitopeCoverageOptimizer:
    """
    Layer 3 — greedy set-cover epitope selection.

    Problem:
        Given K candidate epitopes, each binding to a specific HLA allele
        (or multiple alleles), select N epitopes that maximise:
            total_population_coverage × composite_score

    Algorithm:
        Greedy (provably ≥ (1 − 1/e) ≈ 63% of optimal for standard set cover).
        At each step pick the epitope maximising:
            gain = Δcov(target_pop) + α × norm_composite_score(epitope)

    Args:
        alpha: trade-off weight between coverage gain and binding quality
               α=0 → pure coverage maximisation
               α=1 → equal weight to coverage and quality
    """

    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha

    def _allele_pop_coverage(self, allele: str) -> Dict[str, float]:
        return HLA_FREQ.get(allele, {pop: 0.0 for pop in POPULATIONS})

    def _coverage_of_set(
        self, alleles: List[str]
    ) -> Dict[str, float]:
        """Probability at least one allele in the set is carried by a random person."""
        cov: Dict[str, float] = {}
        for pop in POPULATIONS:
            not_covered = 1.0
            for a in alleles:
                freq = HLA_FREQ.get(a, {}).get(pop, 0.0)
                not_covered *= (1.0 - freq)
            cov[pop] = round(1.0 - not_covered, 4)
        return cov

    def optimize(
        self,
        candidates: List["EpitopeCandidate"],
        n: int = 10,
        target_population: str = "global",
        min_coverage: float = 0.0,
    ) -> Tuple[List["EpitopeCandidate"], List[CoverageStep]]:
        """
        Select up to N epitopes maximising population coverage.

        Returns:
            selected: List of selected EpitopeCandidate in selection order
            trace: Step-by-step coverage trace (for audit/visualisation)
        """
        if not candidates:
            return [], []

        # Normalise composite scores to [0, 1]
        scores = [c.composite_score for c in candidates]
        max_s = max(scores) if scores else 1.0
        norm_scores = [s / max_s for s in scores]

        selected_alleles: List[str] = []
        selected: List["EpitopeCandidate"] = []
        trace: List[CoverageStep] = []
        remaining_idx = list(range(len(candidates)))

        for step_i in range(n):
            if not remaining_idx:
                break

            best_idx = None
            best_gain_score = -1.0
            prev_cov = self._coverage_of_set(selected_alleles)

            for idx in remaining_idx:
                cand = candidates[idx]
                trial_alleles = selected_alleles + [cand.allele]
                trial_cov = self._coverage_of_set(trial_alleles)
                delta = trial_cov.get(target_population, 0) - prev_cov.get(target_population, 0)
                gain = delta + self.alpha * norm_scores[idx]
                if gain > best_gain_score:
                    best_gain_score = gain
                    best_idx = idx

            if best_idx is None:
                break

            chosen = candidates[best_idx]
            selected_alleles.append(chosen.allele)
            selected.append(chosen)
            remaining_idx.remove(best_idx)

            new_cov = self._coverage_of_set(selected_alleles)
            trace.append(CoverageStep(
                step=step_i + 1,
                epitope_idx=best_idx,
                peptide=chosen.peptide,
                allele=chosen.allele,
                composite_score=round(chosen.composite_score, 4),
                delta_coverage={
                    pop: round(new_cov[pop] - prev_cov.get(pop, 0), 4)
                    for pop in POPULATIONS
                },
                cumulative_coverage=new_cov,
            ))

            if new_cov.get(target_population, 0) >= min_coverage > 0:
                logger.info(
                    "Reached %.1f%% %s coverage at step %d",
                    min_coverage * 100, target_population, step_i + 1,
                )
                break

        return selected, trace


# ─────────────────────────────────────────────────────────────────────────────
# Integrated pipeline
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EpitopeCandidate:
    """Input record for the prioritisation pipeline."""
    peptide: str
    allele: str
    mhc_class: str = "I"
    gene: str = ""
    cancer_type: str = ""
    # MHCflurry-derived (from NeoantigenScanner)
    presentation_score: float = 0.0
    affinity_nM: float = 9999.0
    processing_score: float = 0.0
    # Neoantigen-specific
    dai: float = 0.0
    wt_peptide: str = ""
    wt_affinity_nM: float = 9999.0
    # Extra metadata
    source_protein: str = ""
    mutation_id: str = ""
    # Filled by prioritize()
    composite_score: float = 0.0


@dataclass
class PrioritizedEpitope:
    """Output record from the prioritisation pipeline."""
    rank: int
    candidate: EpitopeCandidate
    # Layer outputs
    tolerance: ToleranceVerdict
    expression: ExpressionScore
    # Composite
    composite_score: float
    # Population coverage contribution (filled during coverage optimisation)
    coverage_gain: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["candidate"] = asdict(self.candidate)
        d["tolerance"] = asdict(self.tolerance)
        d["expression"] = asdict(self.expression)
        return d


class EpitopePrioritizer:
    """
    Three-layer epitope prioritisation pipeline.

    Pipeline flow:
        [EpitopeCandidate list]
            ↓  SelfToleranceFilter      (Layer 1 — hard gate)
            ↓  ExpressionWeighter       (Layer 2 — soft weight)
            ↓  composite_score()
            ↓  EpitopeCoverageOptimizer (Layer 3 — set selection)
        [PrioritizedEpitope list]

    Composite score formula (after Layer 1 gate):
        S = presentation_score
          × expression_weight
          × (1 + 0.3 × max(DAI, 0))
          × tolerance_pass  ← hard gate

    Usage:
        prioritizer = EpitopePrioritizer(cancer_type="LUAD")
        ranked = prioritizer.prioritize(candidates)
        selected, trace = prioritizer.select_for_vaccine(
            ranked, n=12, target_population="east_asian", min_coverage=0.80
        )
    """

    def __init__(
        self,
        cancer_type: str = "global",
        tolerance_filter: Optional[SelfToleranceFilter] = None,
        expression_weighter: Optional[ExpressionWeighter] = None,
        coverage_optimizer: Optional[EpitopeCoverageOptimizer] = None,
        dai_bonus_coeff: float = 0.3,
    ):
        self.cancer_type = cancer_type
        self.tol = tolerance_filter or SelfToleranceFilter()
        self.expr = expression_weighter or ExpressionWeighter(cancer_type=cancer_type)
        self.cov = coverage_optimizer or EpitopeCoverageOptimizer()
        self.dai_bonus = dai_bonus_coeff

    # ── from_scanner_output ──────────────────────────────────────────────────

    @classmethod
    def from_scanner_df(
        cls,
        df,  # pd.DataFrame from NeoantigenScanner.scan_protein()
        gene: str = "",
        cancer_type: str = "global",
        mhc_class: str = "I",
    ) -> List[EpitopeCandidate]:
        """
        Convert NeoantigenScanner output DataFrame to EpitopeCandidate list.

        Expected df columns: peptide, allele, affinity, processing_score,
                             presentation_score, presentation_percentile
        """
        candidates = []
        for _, row in df.iterrows():
            candidates.append(EpitopeCandidate(
                peptide=str(row.get("peptide", "")),
                allele=str(row.get("allele", "HLA-A*02:01")),
                mhc_class=mhc_class,
                gene=gene,
                cancer_type=cancer_type,
                presentation_score=float(row.get("presentation_score", 0.0)),
                affinity_nM=float(row.get("affinity", 9999.0)),
                processing_score=float(row.get("processing_score", 0.0)),
            ))
        return candidates

    @classmethod
    def from_neoantigen_results(
        cls,
        results,  # List[NeoantigenResult]
        allele: str,
        gene: str = "",
        cancer_type: str = "global",
    ) -> List[EpitopeCandidate]:
        """Convert NeoantigenScanner.scan_mutations() results."""
        candidates = []
        for r in results:
            candidates.append(EpitopeCandidate(
                peptide=r.mut_peptide,
                allele=allele,
                mhc_class="I",
                gene=gene,
                cancer_type=cancer_type,
                presentation_score=r.mut_presentation,
                affinity_nM=r.mut_affinity,
                dai=r.dai,
                wt_peptide=r.wt_peptide,
                wt_affinity_nM=r.wt_affinity,
            ))
        return candidates

    # ── core scoring ─────────────────────────────────────────────────────────

    def _composite(
        self,
        cand: EpitopeCandidate,
        tol: ToleranceVerdict,
        expr: ExpressionScore,
    ) -> float:
        if not tol.pass_filter:
            return 0.0
        dai_bonus = 1.0 + self.dai_bonus * max(cand.dai, 0.0)
        score = cand.presentation_score * expr.weight * dai_bonus
        return round(score, 6)

    # ── prioritize ───────────────────────────────────────────────────────────

    def prioritize(
        self,
        candidates: List[EpitopeCandidate],
        keep_failed: bool = False,
    ) -> List[PrioritizedEpitope]:
        """
        Score and rank all candidates through all three layers.

        Args:
            candidates: List[EpitopeCandidate]
            keep_failed: if True, include tolerance-failed epitopes in output
                         with composite_score = 0 (useful for reporting)

        Returns:
            Ranked List[PrioritizedEpitope], highest composite_score first.
        """
        results = []
        for cand in candidates:
            tol = self.tol.filter(
                peptide=cand.peptide,
                wt_peptide=cand.wt_peptide,
                wt_affinity_nm=cand.wt_affinity_nM,
                dai=cand.dai,
            )
            expr_score = self.expr.score(
                gene=cand.gene or "UNKNOWN",
                cancer_type=cand.cancer_type or self.cancer_type,
            )
            composite = self._composite(cand, tol, expr_score)
            cand.composite_score = composite

            if not keep_failed and not tol.pass_filter:
                continue

            results.append(PrioritizedEpitope(
                rank=0,
                candidate=cand,
                tolerance=tol,
                expression=expr_score,
                composite_score=composite,
            ))

        results.sort(key=lambda x: x.composite_score, reverse=True)
        for i, r in enumerate(results):
            r.rank = i + 1

        return results

    # ── select_for_vaccine ───────────────────────────────────────────────────

    def select_for_vaccine(
        self,
        prioritized: List[PrioritizedEpitope],
        n: int = 10,
        target_population: str = "global",
        min_coverage: float = 0.0,
        pre_filter_top: int = 50,
    ) -> Tuple[List[PrioritizedEpitope], List[CoverageStep]]:
        """
        From pre-prioritized epitopes, select N for the vaccine construct
        using greedy population-coverage optimisation (Layer 3).

        Args:
            prioritized:       Output of prioritize()
            n:                 Maximum number of epitopes in final set
            target_population: 'global' | 'european' | 'east_asian' | 'african' | 'south_asian'
            min_coverage:      Stop early if this coverage fraction is reached
            pre_filter_top:    Only consider top-K by composite score as candidates
                               (avoids exhaustive search over low-quality epitopes)

        Returns:
            selected_epitopes: List[PrioritizedEpitope] in selection order
            coverage_trace:    Step-by-step CoverageStep list
        """
        # Pre-filter: only tolerance-passed epitopes
        pool = [p for p in prioritized if p.tolerance.pass_filter]
        # Take top candidates by composite score
        pool = pool[:pre_filter_top]

        candidates_for_opt = [p.candidate for p in pool]
        selected_cands, trace = self.cov.optimize(
            candidates=candidates_for_opt,
            n=n,
            target_population=target_population,
            min_coverage=min_coverage,
        )

        # Map back to PrioritizedEpitope objects
        selected_pep_set = {c.peptide for c in selected_cands}
        selected_epitopes = [p for p in pool if p.candidate.peptide in selected_pep_set]

        # Attach coverage_gain from trace
        for step in trace:
            for ep in selected_epitopes:
                if ep.candidate.peptide == step.peptide:
                    ep.coverage_gain = step.delta_coverage

        return selected_epitopes, trace

    # ── summary report ───────────────────────────────────────────────────────

    @staticmethod
    def coverage_report(trace: List[CoverageStep]) -> str:
        """Human-readable coverage optimisation trace."""
        if not trace:
            return "No coverage trace available."
        lines = ["Epitope Coverage Optimisation Trace", "=" * 50]
        for step in trace:
            cumcov = step.cumulative_coverage
            lines.append(
                f"Step {step.step:2d}: {step.peptide:<12} / {step.allele:<14}  "
                f"score={step.composite_score:.4f}  "
                f"global={cumcov.get('global', 0):.1%}  "
                f"east_asian={cumcov.get('east_asian', 0):.1%}  "
                f"european={cumcov.get('european', 0):.1%}"
            )
        final = trace[-1].cumulative_coverage
        lines += [
            "",
            "Final population coverage:",
            *[f"  {pop:<15}: {final.get(pop, 0):.1%}" for pop in POPULATIONS],
        ]
        return "\n".join(lines)
