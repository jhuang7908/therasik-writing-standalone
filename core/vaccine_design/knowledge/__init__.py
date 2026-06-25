"""
core/vaccine_design/knowledge — Clinical evidence-driven vaccine knowledge bases.

Data sources:
  - NCI Cancer Antigen Pilot Project (Cheever et al., Clin Cancer Res 2009)
  - IEDB / UniProt / ClinicalTrials.gov
  - VDJdb / McPAS-TCR / primary literature (TCR-epitope pairs)
  - WHO Essential Medicines List (Vaccines)
  - FDA / EMA approved product labels

All data are literature-curated, no LLM-generated content.
"""
from .taa_database import TAA_DATABASE, TumorAntigen, query_taa
from .autoimmune_targets import AUTOIMMUNE_TARGETS, AutoimmuneTarget, query_autoimmune
from .infectious_antigens import INFECTIOUS_ANTIGENS, InfectiousAntigen, query_infectious
from .vaccine_vectors import VACCINE_VECTORS, VaccineVector, query_vectors
from .adjuvants import ADJUVANT_DATABASE, Adjuvant, query_adjuvants
from .tcr_epitope_db import (
    TCR_DATABASE, TUMOR_TCRS, VIRAL_TCRS, PUBLIC_TCR_MOTIFS,
    TCRClone, PublicTCRMotif,
    query_tcr, query_motifs, get_tcr_for_vaccine_design,
)
from .knowledge_base import VaccineKnowledgeBase

__all__ = [
    "TAA_DATABASE", "TumorAntigen", "query_taa",
    "AUTOIMMUNE_TARGETS", "AutoimmuneTarget", "query_autoimmune",
    "INFECTIOUS_ANTIGENS", "InfectiousAntigen", "query_infectious",
    "VACCINE_VECTORS", "VaccineVector", "query_vectors",
    "ADJUVANT_DATABASE", "Adjuvant", "query_adjuvants",
    "TCR_DATABASE", "TUMOR_TCRS", "VIRAL_TCRS", "PUBLIC_TCR_MOTIFS",
    "TCRClone", "PublicTCRMotif",
    "query_tcr", "query_motifs", "get_tcr_for_vaccine_design",
    "VaccineKnowledgeBase",
]
