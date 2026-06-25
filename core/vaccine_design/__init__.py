"""
InSynBio Vaccine Design Engine
==============================
Lightweight, open-source, CPU-only, clinically-driven vaccine design platform.

Design Modules:
  - NeoantigenScanner      : MHC-I binding prediction + neoantigen DAI analysis (local, MHCflurry)
  - MHC2Predictor          : MHC-II binding prediction (IEDB API, online, free)
  - HeteroclicticDesigner  : TAA anchor mutation with cross-reactivity guard
  - MultiEpitopeAssembler  : Multi-epitope mRNA vaccine construct design
  - CodonOptimizer         : mRNA codon + structure co-optimization
  - PopulationCoverage     : HLA population coverage analysis
  - EpitopePrioritizer     : Three-layer prioritisation pipeline:
                               Layer 1 SelfToleranceFilter  — proteome k-mer + DAI gate
                               Layer 2 ExpressionWeighter   — TCGA/GTEx diff-expression weight
                               Layer 3 EpitopeCoverageOptimizer — greedy set-cover selection

Online Services:
  - IEDBSearcher           : IEDB epitope search client (online, requires internet)
  - iedb_search()          : One-line IEDB T cell epitope search
  - iedb_url()             : Generate IEDB browser URL for client portal

Knowledge Bases (clinical evidence-driven):
  - knowledge.TAA_DATABASE           : NCI-ranked tumor-associated antigens (30 entries, 56+ MHC-I epitopes)
  - knowledge.AUTOIMMUNE_TARGETS     : Tolerogenic vaccine targets (11 diseases)
  - knowledge.INFECTIOUS_ANTIGENS    : Infectious disease antigens (9 pathogens)
  - knowledge.VACCINE_VECTORS        : Clinical vaccine platforms (10 vectors)
  - knowledge.ADJUVANT_DATABASE      : Immune adjuvants (10 adjuvants)
  - knowledge.TCR_DATABASE           : Curated TCR-pMHC pairs (clinical + classic viral + neoantigen)
  - knowledge.VaccineKnowledgeBase   : Unified search + recommendation engine

Environment: conda activate vaccine  (Python 3.11)
Core dependencies:
  - MHCflurry ≥ 2.2.0 (local, no API) — MHC-I
  - IEDB API (online) — MHC-II, epitope search
"""
from .neoantigen_scanner import NeoantigenScanner
from .heteroclitic_designer import HeteroclicticDesigner
from .multi_epitope_assembler import MultiEpitopeAssembler
from .codon_optimizer import CodonOptimizer
from .population_coverage import PopulationCoverage
from .mhc2_predictor import MHC2Predictor
from .iedb_search import IEDBSearcher, iedb_search, iedb_url
from .epitope_prioritizer import (
    EpitopePrioritizer,
    EpitopeCandidate,
    PrioritizedEpitope,
    SelfToleranceFilter,
    ExpressionWeighter,
    EpitopeCoverageOptimizer,
)

from .neoantigen_scanner import __version__ as _ns_ver
from .multi_epitope_assembler import __version__ as _mea_ver
from .codon_optimizer import __version__ as _co_ver
from .heteroclitic_designer import __version__ as _hd_ver
from .population_coverage import __version__ as _pc_ver
from .mhc2_predictor import __version__ as _mhc2_ver
from .iedb_search import __version__ as _iedb_ver
from .epitope_prioritizer import __version__ as _ep_ver

MODULE_VERSIONS = {
    "NeoantigenScanner": _ns_ver,
    "MultiEpitopeAssembler": _mea_ver,
    "CodonOptimizer": _co_ver,
    "HeteroclicticDesigner": _hd_ver,
    "PopulationCoverage": _pc_ver,
    "MHC2Predictor": _mhc2_ver,
    "IEDBSearcher": _iedb_ver,
    "EpitopePrioritizer": _ep_ver,
}

__all__ = [
    "NeoantigenScanner",
    "MHC2Predictor",
    "HeteroclicticDesigner",
    "MultiEpitopeAssembler",
    "CodonOptimizer",
    "PopulationCoverage",
    "EpitopePrioritizer",
    "EpitopeCandidate",
    "PrioritizedEpitope",
    "SelfToleranceFilter",
    "ExpressionWeighter",
    "EpitopeCoverageOptimizer",
    "IEDBSearcher",
    "iedb_search",
    "iedb_url",
    "MODULE_VERSIONS",
]
