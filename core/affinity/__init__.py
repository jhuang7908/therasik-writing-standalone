"""
core/affinity — Virtual Affinity Maturation Engine
====================================================
Standard: Humanization v4.4.1 × VHH Design v2.2
Platform: InSynBio AbEngineCore

Entry points:
  from core.affinity import AffinityMaturator
  result = AffinityMaturator(config).run(complex_pdb, sequences, ...)
"""
from .maturation_engine import AffinityMaturator, MaturationResult, MutationCandidate

__version__ = "1.0.0"
__all__ = ["AffinityMaturator", "MaturationResult", "MutationCandidate"]
