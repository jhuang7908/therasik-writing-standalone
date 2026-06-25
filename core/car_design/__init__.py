"""
InSynBio CAR-T Design Engine
=============================
Intelligent CAR construct design, validation, scoring, and export.

Usage:
    from core.car_design import CARDesigner
    designer = CARDesigner()
    result = designer.design(target="CD19", indication="B_ALL")
"""
from .car_designer import CARDesigner
from .decision_advisor import DecisionAdvisor
from .codon_optimizer import CodonOptimizer
from .plasmid_map import PlasmidMapGenerator
from .knowledge_enricher import KnowledgeEnricher

__all__ = [
    "CARDesigner", "DecisionAdvisor", "CodonOptimizer",
    "PlasmidMapGenerator", "KnowledgeEnricher",
]
