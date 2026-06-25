"""
core/bovine_ultralong
=====================

（Bovine, ultralong CDR-H3） knob/stalk 
（Skeleton — V0.1, 2026-05-01）


----
-  `docs/NON_TRADITIONAL_SPECIES_HUMANIZATION_GUIDE_V1.0.md` §4。
-  CDR-H3  ≥ ~35 aa  knob-stalk 。
-  `core/humanization` (VH/VL)； VH（CDR3 < 35 aa） VH/VL 。

（）
------------------
- `detect_ultralong_cdr3(vh_seq) -> UltralongCdr3Topology`
    *  ANARCII IMGT  CDR-H3
    *  Cys ， knob/stalk 
    *  long_threshold_hit、cys_pairs、knob_span、stalk_span

- `select_engineering_path(topology, options) -> str`
    *  "knob_grafting" | "fr_only_humanization" | "vhh_like"

- `graft_knob_to_human_scaffold(knob_seq, scaffold="IGHV1-69" | "IGHV4-34", stalk="engineered") -> dict`
    *  knob  CDR3 
    *  ThermoMPNN/EvoEF2 ΔΔG 
    *  +  ≥ 95% 

- `verify_disulfide_topology(seq, predicted_pdb) -> dict`
    * OpenMM / ESM-IF1 / AntiFold 
    *  correct_pair_rate、broken_pairs 

- `verify_bovine_graft(donor_vh, humanized_vh, antigen_complex_pdb=None) -> dict`
    * CDR-H3 Cα RMSD（）< 2.5 Å（knob  RMSD）
    *  ≥ 90%（）


--------
- `data/germlines/bos_taurus_ig_aa/`
- `data/germlines/bos_taurus_ig_aa/segmented/`
- `data/germlines/human_ig_aa/`（IGHV1-69 / IGHV4-34）
-  ultralong （）


--------
- ANARCII
- IgFold / ABodyBuilder2 / NanoBodyBuilder2
- OpenMM、ESM-IF1、AntiFold（）
- ThermoMPNN、EvoEF2（ ΔΔG）


----
-  Cys 
-  ≥ 95%（）
-  ΔΔG > +2 kcal/mol  stalk
- knob ； stalk


----------
（skeleton）。：
1.  `docs/NON_TRADITIONAL_SPECIES_HUMANIZATION_GUIDE_V1.0.md` §4
2.  `core/structure/affinity_energy_toolkit.py` 
3.  LOCKED 
4.  EVOLUTION_LOG 

"""

__version__ = "0.1.0-skeleton"
__all__: list[str] = []
