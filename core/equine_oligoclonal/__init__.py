"""
core/equine_oligoclonal
=======================

（Equine）（Skeleton — V0.1, 2026-05-01）


----
-  `docs/NON_TRADITIONAL_SPECIES_HUMANIZATION_GUIDE_V1.0.md` §5。
- ； “3–8  +  +
   VH framework + ” 。
-  `core/humanization` (VH/VL)； IMGT germline ，
  ** VH/VL **。

（）
------------------
- `humanize_equine_oligoclonal(clones: list[EquineClone], **opts) -> OligoclonalResult`
    * ：3–8  (VH, VL)  + 
    * ： N  VH  1  VL，CMC pI 

- `select_common_light_chain(clones, options) -> str`
    *  VL  /  / CMC 
    *  human IGKV1-39\*01 / IGLV3-1\*01  carrier

- `build_consensus_vh_framework(clones) -> dict`
    *  N  VH  FR1–FR3，
    *  1  human IGHV（IGHV1-69 / IGHV3-23  CDR ）
    *  Vernier 

- `graft_each_vh_to_consensus(clones, common_vl, vh_acceptor) -> list`
    *  VH  CDR1–CDR3  VH 
    *  VH  VL

- `cmc_convergence_check(humanized_panel) -> dict`
    * pI、、
    * ：N  mAb  pI  < 0.5
    * ：FR-only （ CDR）

- `coexpression_feasibility(panel, ratio_test=True) -> dict`
    *  CHO  1  VL + N  VH 
    * LC-MS / native MS （）


--------
- `data/germlines/equus_caballus_ig_aa/`（，）
- `data/germlines/equus_caballus_ig_aa/segmented/`
- `data/germlines/human_ig_aa/`（ VH framework + carrier VL）
-  B （）


--------
- ANARCII（IMGT + Kabat）
- （t-SNE / UMAP /  fingerprint）
- BioPython ProtParam（pI、GRAVY、charge）
- AbEvaluator CMC（mini-CMC pre-check）


----
-  VH/VL （germline ）
-  CDR （V5.1.0 Union  + `verify_cdr_preservation`）
- pI  < 0.5（ CMC）
- ：YTE  (M252Y/S254T/T256E)  IgG1 Fc 


----------
（skeleton）。：
1.  `docs/NON_TRADITIONAL_SPECIES_HUMANIZATION_GUIDE_V1.0.md` §5
2.  `core/cmc/`  pI/charge 
3.  LOCKED 
4.  EVOLUTION_LOG 

"""

__version__ = "0.1.0-skeleton"
__all__: list[str] = []
