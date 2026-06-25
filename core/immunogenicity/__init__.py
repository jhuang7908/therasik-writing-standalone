"""
core.immunogenicity — InSynBio AbEngineCore v1.0
=================================================
MHC Class II immunogenicity analysis for therapeutic antibodies.

Modules
-------
  iedb_client    : IEDB API client + 27-allele HLA panel definitions.
  mhcii_analyzer : Full MHC-II pipeline (sliding window → IEDB → cluster → score).
  surface_immuno : Hydrophilic/hydrophobic surface patch immunogenicity.

Quick start
-----------
    # Full MHC-II analysis (requires network for IEDB)
    from core.immunogenicity import MHCII_Analyzer
    result = MHCII_Analyzer(vh_seq="EVQLVES...", vl_seq="DIQMTQ...", use_iedb=True).run()

    # Surface immunogenicity (PDB or sequence)
    from core.immunogenicity import SurfaceImmunogenicity
    si = SurfaceImmunogenicity(pdb_path="Ab.pdb", vh_chain="H", vl_chain="L")
    sr = si.analyze()

    # IEDB client directly
    from core.immunogenicity import predict_mhcii_binding, EXT27_HLA_ALLELES
    preds = predict_mhcii_binding("EVQLVES...", EXT27_HLA_ALLELES)

HLA allele panels
-----------------
    from core.immunogenicity import CORE15_HLA_ALLELES, EXT27_HLA_ALLELES
"""

from core.immunogenicity.iedb_client import (
    IEDBError,
    IEDBRequestConfig,
    IEDBPrediction,
    CORE15_HLA_ALLELES,
    EXT27_HLA_ALLELES,
    DEFAULT_HLA_ALLELES,
    predict_mhcii_binding,
    predict_mhci_binding,
)
from core.immunogenicity.mhcii_analyzer import (
    MHCII_Analyzer,
    MHCII_Result,
    EpitopeHit,
)
from core.immunogenicity.surface_immuno import (
    SurfaceImmunogenicity,
    SurfaceImmunoResult,
    SurfacePatch,
)

__all__ = [
    # IEDB
    "IEDBError", "IEDBRequestConfig", "IEDBPrediction",
    "CORE15_HLA_ALLELES", "EXT27_HLA_ALLELES", "DEFAULT_HLA_ALLELES",
    "predict_mhcii_binding", "predict_mhci_binding",
    # MHC-II analyzer
    "MHCII_Analyzer", "MHCII_Result", "EpitopeHit",
    # Surface immunogenicity
    "SurfaceImmunogenicity", "SurfaceImmunoResult", "SurfacePatch",
]