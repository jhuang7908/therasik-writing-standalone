"""
core.vh2vhh — VH→VHH conversion helper modules.

Currently exposes:
- engineered_vh_similarity: V1.6 evidence layer scoring a candidate VHH against
  the frozen Atlas-24 (Engineered_Human_VH) prior derived from
  data/vhh_design_atlas_v3.json.
- glycan_dependency_checker: V1.7 evidence layer detecting glycan-dependent
  epitope contact risk from CDR-H3 motif scan + frozen knowledge base.

Both modules are additive — they do NOT modify V1.5 algorithm tree. Removal of
either import keeps prior-version behavior intact.
"""

from .engineered_vh_similarity import (  # noqa: F401
    ATLAS24_PRIOR_VERSION,
    EngineeredVhSimilarityResult,
    score_engineered_vh_similarity,
)

from .glycan_dependency_checker import (  # noqa: F401
    GLYCAN_CHECKER_VERSION,
    GLYCAN_CONTACT_AB_KB,
    GlycanDependencyResult,
    score_glycan_dependency_risk,
)
