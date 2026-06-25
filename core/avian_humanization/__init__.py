"""
core/avian_humanization
=======================

（Avian, IgY）（Skeleton — V0.1, 2026-05-01）


----
-  `docs/NON_TRADITIONAL_SPECIES_HUMANIZATION_GUIDE_V1.0.md` §3 
  。
-  `core/humanization` (VH/VL)  `core/vhh_humanization` (VHH)；
   FR ， 1–2  CDR ，
  CDR-graft + 5–8  Vernier  +  。

（）
------------------
- `humanize_avian_antibody(vh_seq, vl_seq, **opts) -> AvianHumanizationResult`
- `select_acceptor_framework(vh_seq, vl_seq) -> dict`         #  IGHV3-23 + IGKV1-39 / IGLV3-1
- `compute_vernier_retention_set(donor_kabat, chain) -> set`  #  Vernier 
- `surface_resurface_avian(graft_seq, structure_pdb) -> str`  #  CDR > 5 Å 
- `verify_avian_graft(donor, humanized, structure_pdb) -> dict` # CDR  +  QA + ADA 


--------
- `data/germlines/gallus_gallus_ig_aa/`
- `data/germlines/gallus_gallus_ig_aa/segmented/`
- `data/germlines/human_ig_aa/`（）


--------
- ANARCII（IMGT + Kabat）
- IgFold / ABodyBuilder2（）
- BioPython SASA（）
- IEDB MHC-II 27 （）


----
-  V5.1.0 Union  CDR （ `config/vh_vl_humanization_v490.json`）
-  `verify_cdr_preservation` 
-  `core/humanization/engine.py`  Phase 4 ；
   Vernier  Anchor 


----------
（skeleton）。：
1.  `docs/NON_TRADITIONAL_SPECIES_HUMANIZATION_GUIDE_V1.0.md` §3
2.  `[OBSERVATION]/[PROPOSAL]/[EXECUTED]`  `docs/EVOLUTION_LOG.md` 
3.  LOCKED 

"""

__version__ = "0.1.0-skeleton"
__all__: list[str] = []
