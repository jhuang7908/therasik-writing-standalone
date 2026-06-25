"""
VHH Humanization Mutation Rules

hallmarkvernier zone（Rulebook v1.0）
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from core.humanize.rulebook_v1 import (
    RuleLayer,
    RuleMode,
    RiskLevel,
    TargetRegion,
    RuleDefinition,
    get_rule_definition,
    format_trigger_explanation,
    format_rationale,
    RULEBOOK_V1,
)


@dataclass
class MutationRecord:
    """（Rulebook v1.0）"""
    rule_id: str
    numbering: Dict[str, Any]  # {kabat: int, imgt: str, aho: Optional[str]}
    from_aa: str
    to_aa: str
    rationale: str
    evidence_level: str
    position_in_sequence: Optional[int] = None  # （0-based）
    # Rulebook v1.0 
    layer: Optional[str] = None  # "A" or "B"
    risk_level: Optional[str] = None  # "low", "medium", "high"
    purpose: Optional[str] = None  # 
    trigger_explanation: Optional[str] = None  # （query vs scaffold）


# ============================================================================
# Vernier Zone Whitelist (Kabat positions)
# ============================================================================

# Vernier Zone Whitelist (Rulebook v1.0)
VERNIER_ANCHOR_POSITIONS = [27, 28, 29, 47, 71, 93, 94]  # High-risk anchor points (expert_mode only)
VERNIER_TUNING_POSITIONS = [30, 49, 73, 78]  # Low-risk tuning points (mvp_mode available)
VERNIER_WHITELIST_KABAT = VERNIER_ANCHOR_POSITIONS + VERNIER_TUNING_POSITIONS


# ============================================================================
# Hallmark Rules (FR2)
# ============================================================================

def apply_hallmark_rules(
    query_kabat_map: Dict[int, str],
    scaffold_fr2: str,
    scaffold_kabat_map: Dict[int, str],
    numbering_maps: Dict[str, Any],
    mode: RuleMode = RuleMode.MVP,
) -> List[MutationRecord]:
    """
    hallmark（FR244/45）
    
    ：
    -  query(44) ∈ {E,Q} → scaffold FR2  Kabat44  E（G44E）
    -  query(45) == R → scaffold FR2  Kabat45  R（L45R）
    
    Args:
        query_kabat_map: queryKabat {kabat_pos: aa}
        scaffold_fr2: scaffoldFR2
        scaffold_kabat_map: scaffoldKabat {kabat_pos: aa}
        numbering_maps: ，kabat_to_imgt
    
    Returns:
        
    """
    mutations = []
    
    # KabatIMGT
    kabat_to_imgt = numbering_maps.get("kabat_to_imgt", {})
    
    def get_imgt_pos(kabat_pos: int) -> Optional[str]:
        """kabat_to_imgtIMGT"""
        # 1: {"kabat_44": "imgt_44"}
        key1 = f"kabat_{kabat_pos}"
        if key1 in kabat_to_imgt:
            imgt_label = kabat_to_imgt[key1]
            if isinstance(imgt_label, str):
                if imgt_label.startswith("imgt_"):
                    return imgt_label[5:]  # "imgt_"
                return imgt_label
        
        # 2: {44: "44"}  {44: 44}
        if kabat_pos in kabat_to_imgt:
            imgt_pos = kabat_to_imgt[kabat_pos]
            if isinstance(imgt_pos, (str, int)):
                return str(imgt_pos)
        
        return None
    
    # 1: Kabat 44 (HALLMARK_FR2_44)
    rule_def_44 = get_rule_definition("HALLMARK_FR2_44")
    if rule_def_44 and (rule_def_44.default_mode == mode or mode == RuleMode.EXPERT):
        query_aa_44 = query_kabat_map.get(44)
        if query_aa_44 in ("E", "Q"):
            scaffold_aa_44 = scaffold_kabat_map.get(44)
            if scaffold_aa_44 and scaffold_aa_44 != "E":
                imgt_pos_44 = get_imgt_pos(44)
                mutations.append(MutationRecord(
                    rule_id="HALLMARK_FR2_44",
                    numbering={
                        "kabat": 44,
                        "imgt": imgt_pos_44,
                        "aho": None,
                    },
                    from_aa=scaffold_aa_44,
                    to_aa="E",
                    rationale=format_rationale(rule_def_44, 44, query_aa_44, scaffold_aa_44),
                    evidence_level=rule_def_44.evidence_level,
                    layer=rule_def_44.layer.value,
                    risk_level=rule_def_44.risk_level.value,
                    purpose=rule_def_44.purpose,
                    trigger_explanation=format_trigger_explanation(rule_def_44, 44, query_aa_44, scaffold_aa_44),
                ))
    
    # 2: Kabat 45 (HALLMARK_FR2_45)
    rule_def_45 = get_rule_definition("HALLMARK_FR2_45")
    if rule_def_45 and (rule_def_45.default_mode == mode or mode == RuleMode.EXPERT):
        query_aa_45 = query_kabat_map.get(45)
        if query_aa_45 == "R":
            scaffold_aa_45 = scaffold_kabat_map.get(45)
            if scaffold_aa_45 and scaffold_aa_45 != "R":
                imgt_pos_45 = get_imgt_pos(45)
                mutations.append(MutationRecord(
                    rule_id="HALLMARK_FR2_45",
                    numbering={
                        "kabat": 45,
                        "imgt": imgt_pos_45,
                        "aho": None,
                    },
                    from_aa=scaffold_aa_45,
                    to_aa="R",
                    rationale=format_rationale(rule_def_45, 45, query_aa_45, scaffold_aa_45),
                    evidence_level=rule_def_45.evidence_level,
                    layer=rule_def_45.layer.value,
                    risk_level=rule_def_45.risk_level.value,
                    purpose=rule_def_45.purpose,
                    trigger_explanation=format_trigger_explanation(rule_def_45, 45, query_aa_45, scaffold_aa_45),
                ))
    
    return mutations


# ============================================================================
# Vernier Zone Rules (Backfill)
# ============================================================================

def is_position_in_cdr(kabat_pos: int, numbering_maps: Dict[str, Any]) -> bool:
    """
    KabatCDR
    
    Args:
        kabat_pos: Kabat
        numbering_maps: 
    
    Returns:
        True if position is in CDR, False otherwise
    """
    # IMGT
    # CDR1: IMGT 27-38
    # CDR2: IMGT 56-65
    # CDR3: IMGT 105-117
    
    # kabat_to_imgt
    kabat_to_imgt = numbering_maps.get("kabat_to_imgt", {})
    
    # 
    imgt_pos = None
    
    # 1: {"kabat_44": "imgt_44"}
    key1 = f"kabat_{kabat_pos}"
    if key1 in kabat_to_imgt:
        imgt_label = kabat_to_imgt[key1]
        if isinstance(imgt_label, str) and imgt_label.startswith("imgt_"):
            imgt_pos = imgt_label[5:]  # "imgt_"
    
    # 2: {44: "44"}  {44: 44}
    if imgt_pos is None and kabat_pos in kabat_to_imgt:
        imgt_pos = kabat_to_imgt[kabat_pos]
    
    if imgt_pos is None:
        return False
    
    # imgt_pos（）
    if isinstance(imgt_pos, str):
        # 
        try:
            imgt_num = int(''.join(filter(str.isdigit, imgt_pos)))
        except ValueError:
            return False
    elif isinstance(imgt_pos, int):
        imgt_num = imgt_pos
    else:
        return False
    
    # CDR
    if (27 <= imgt_num <= 38) or (56 <= imgt_num <= 65) or (105 <= imgt_num <= 117):
        return True
    
    return False


def apply_vernier_backfill(
    query_kabat_map: Dict[int, str],
    scaffold_kabat_map: Dict[int, str],
    numbering_maps: Dict[str, Any],
    mode: RuleMode = RuleMode.MVP,
) -> List[MutationRecord]:
    """
    vernier zone
    
    （）：
     query  Kabat  aa ≠ scaffold  aa
     CDR（）
    ""： humanized  query aa
    
    Args:
        query_kabat_map: queryKabat {kabat_pos: aa}
        scaffold_kabat_map: scaffoldKabat {kabat_pos: aa}
        numbering_maps: 
    
    Returns:
        
    """
    mutations = []
    
    kabat_to_imgt = numbering_maps.get("kabat_to_imgt", {})
    
    # mode
    if mode == RuleMode.MVP:
        available_positions = VERNIER_TUNING_POSITIONS
    else:  # EXPERT mode
        available_positions = VERNIER_WHITELIST_KABAT  # anchortuning
    
    for kabat_pos in available_positions:
        # query
        query_aa = query_kabat_map.get(kabat_pos)
        if query_aa is None:
            continue
        
        # scaffold
        scaffold_aa = scaffold_kabat_map.get(kabat_pos)
        if scaffold_aa is None:
            continue
        
        # queryscaffoldaa
        if query_aa != scaffold_aa:
            # CDR
            if not is_position_in_cdr(kabat_pos, numbering_maps):
                # 
                if kabat_pos in VERNIER_ANCHOR_POSITIONS:
                    rule_def = get_rule_definition("VERNIER_ANCHOR")
                    rule_id = "VERNIER_ANCHOR"
                else:
                    rule_def = get_rule_definition("VERNIER_TUNING")
                    rule_id = "VERNIER_TUNING"
                
                # mode
                if rule_def and (rule_def.default_mode == mode or mode == RuleMode.EXPERT):
                    imgt_pos = kabat_to_imgt.get(kabat_pos)
                    mutations.append(MutationRecord(
                        rule_id=rule_id,
                        numbering={
                            "kabat": kabat_pos,
                            "imgt": imgt_pos if imgt_pos else None,
                            "aho": None,
                        },
                        from_aa=scaffold_aa,
                        to_aa=query_aa,
                        rationale=format_rationale(rule_def, kabat_pos, query_aa, scaffold_aa),
                        evidence_level=rule_def.evidence_level,
                        layer=rule_def.layer.value,
                        risk_level=rule_def.risk_level.value,
                        purpose=rule_def.purpose,
                        trigger_explanation=format_trigger_explanation(rule_def, kabat_pos, query_aa, scaffold_aa),
                    ))
    
    return mutations


# ============================================================================
# Apply All Rules
# ============================================================================

def apply_all_mutation_rules(
    query_kabat_map: Dict[int, str],
    scaffold_fr2: str,
    scaffold_kabat_map: Dict[int, str],
    numbering_maps: Dict[str, Any],
    mode: RuleMode = RuleMode.MVP,
) -> Tuple[List[MutationRecord], Dict[str, Any]]:
    """
    （hallmark + vernier）
    
    Args:
        query_kabat_map: queryKabat
        scaffold_fr2: scaffoldFR2
        scaffold_kabat_map: scaffoldKabat
        numbering_maps: 
    
    Returns:
        (mutations, summary)
        mutations: 
        summary: {
            "hallmark_applied": bool,
            "vernier_applied": bool,
            "n_mutations_total": int,
            "vernier_backfill_count": int,
        }
    """
    # hallmark
    hallmark_mutations = apply_hallmark_rules(
        query_kabat_map,
        scaffold_fr2,
        scaffold_kabat_map,
        numbering_maps,
        mode=mode,
    )
    
    # vernier
    vernier_mutations = apply_vernier_backfill(
        query_kabat_map,
        scaffold_kabat_map,
        numbering_maps,
        mode=mode,
    )
    
    # 
    all_mutations = hallmark_mutations + vernier_mutations
    
    # 
    summary = {
        "hallmark_applied": len(hallmark_mutations) > 0,
        "vernier_applied": len(vernier_mutations) > 0,
        "n_mutations_total": len(all_mutations),
        "vernier_backfill_count": len(vernier_mutations),
    }
    
    return all_mutations, summary

