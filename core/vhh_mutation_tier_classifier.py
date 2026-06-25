"""
VHH （Tier Classification System）

 CURSOR_REPORT_ENGINE v3.0 ，：
- Tier 0: 
- Tier 1: 
- Tier 2: 
- Tier 3: /
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TieredMutation:
    """"""
    position: int
    from_aa: str
    to_aa: str
    region: str
    tier: int  # 0, 1, 2, 3
    rationale: str
    risk_level: str  # "Low", "Medium", "High"
    confidence: float  # 0.0-1.0
    affects_affinity: bool
    affects_structure: bool
    warning: Optional[str] = None  # Tier 3  warning


# VHH Hallmark （IMGT ）— FR2 only; pos37 is CDR1 (IMGT 27-38), not a hallmark
VHH_HALLMARK_POSITIONS = {44, 45, 47}

# Vernier （IMGT ）
VERNIER_CRITICAL_POSITIONS = {37, 39, 45, 47, 91}  # 37 is CDR1 but also a Vernier anchor

# CMC 
CMC_HIGH_RISK_PATTERNS = {
    "NXS": " (N-X-S)",
    "NXT": " (N-X-T)",
    "NG": " (N-G)",
    "DG": " (D-G)",
    "M": " (M)",
    "W": " (W)",
}


def classify_mutation_tier(
    mutation: Dict[str, Any],
    sequence: str,
    segmentation: Dict[str, Any],
    cmc_risks: Optional[List[Dict[str, Any]]] = None,
    immunogenicity_risks: Optional[List[Dict[str, Any]]] = None,
    hallmark_positions: Optional[Dict[str, List[int]]] = None,
) -> TieredMutation:
    """
    
    
    Args:
        mutation: ， position, from_aa, to_aa, region 
        sequence: 
        segmentation: IMGT 
        cmc_risks: CMC 
        immunogenicity_risks: 
        hallmark_positions: Hallmark 
    
    Returns:
        TieredMutation 
    """
    position = mutation.get("position", 0)
    from_aa = mutation.get("from_aa", mutation.get("from", ""))
    to_aa = mutation.get("to_aa", mutation.get("to", ""))
    region = mutation.get("region", "")
    
    #  Tier 0（）
    tier, rationale, risk_level, warning = _check_tier_0(
        position, from_aa, to_aa, region, sequence, hallmark_positions
    )
    if tier == 0:
        return TieredMutation(
            position=position,
            from_aa=from_aa,
            to_aa=to_aa,
            region=region,
            tier=0,
            rationale=rationale,
            risk_level="High",
            confidence=1.0,
            affects_affinity=True,
            affects_structure=True,
            warning="， CDR  VHH hallmark。",
        )
    
    #  Tier 1（）
    tier, rationale, risk_level = _check_tier_1(
        position, from_aa, to_aa, region, sequence, cmc_risks, immunogenicity_risks
    )
    if tier == 1:
        return TieredMutation(
            position=position,
            from_aa=from_aa,
            to_aa=to_aa,
            region=region,
            tier=1,
            rationale=rationale,
            risk_level=risk_level,
            confidence=0.9,
            affects_affinity=False,
            affects_structure=False,
        )
    
    #  Tier 2（）
    tier, rationale, risk_level = _check_tier_2(
        position, from_aa, to_aa, region, sequence, cmc_risks, immunogenicity_risks
    )
    if tier == 2:
        return TieredMutation(
            position=position,
            from_aa=from_aa,
            to_aa=to_aa,
            region=region,
            tier=2,
            rationale=rationale,
            risk_level=risk_level,
            confidence=0.75,
            affects_affinity=False,
            affects_structure=False,
        )
    
    #  Tier 3（/）
    tier, rationale, risk_level, warning = _check_tier_3(
        position, from_aa, to_aa, region, sequence
    )
    return TieredMutation(
        position=position,
        from_aa=from_aa,
        to_aa=to_aa,
        region=region,
        tier=3,
        rationale=rationale,
        risk_level=risk_level,
        confidence=0.6,
        affects_affinity=True,
        affects_structure=False,
        warning=warning,
    )


def _check_tier_0(
    position: int,
    from_aa: str,
    to_aa: str,
    region: str,
    sequence: str,
    hallmark_positions: Optional[Dict[str, List[int]]] = None,
) -> Tuple[int, str, str, Optional[str]]:
    """ Tier 0（）"""
    
    # 1. CDR 
    if region in ["CDR1", "CDR2", "CDR3"]:
        return (
            0,
            f"CDR {region} ，。",
            "High",
            "CDR 。",
        )
    
    # 2. VHH Hallmark 
    if position in VHH_HALLMARK_POSITIONS:
        return (
            0,
            f" {position}  VHH hallmark （FR2），。",
            "High",
            "VHH hallmark  VHH 。",
        )
    
    # 3. Vernier 
    if position in VERNIER_CRITICAL_POSITIONS:
        return (
            0,
            f" {position}  Vernier  packing ，。",
            "High",
            "Vernier 。",
        )
    
    # 4. Cys 
    if from_aa == "C" or to_aa == "C":
        #  Cys 
        cys_positions = [i + 1 for i, aa in enumerate(sequence) if aa == "C"]
        if position in cys_positions:
            return (
                0,
                f" {position}  Cys ，。",
                "High",
                "Cys 。",
            )
    
    return (-1, "", "", None)


def _check_tier_1(
    position: int,
    from_aa: str,
    to_aa: str,
    region: str,
    sequence: str,
    cmc_risks: Optional[List[Dict[str, Any]]] = None,
    immunogenicity_risks: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[int, str, str]:
    """ Tier 1（）"""
    
    # 1.  CMC 
    if cmc_risks:
        for risk in cmc_risks:
            risk_pos = risk.get("position", 0)
            risk_type = risk.get("type", "")
            risk_level = risk.get("risk_level", "")
            
            if risk_pos == position and risk_level == "high":
                # 
                if _fixes_cmc_risk(from_aa, to_aa, risk_type):
                    return (
                        1,
                        f" CMC {risk_type} （ {position}）。",
                        "High",
                    )
    
    # 2.  anchor residue（ FR ）
    if immunogenicity_risks and region.startswith("FR"):
        for risk in immunogenicity_risks:
            risk_pos = risk.get("position", 0)
            risk_level = risk.get("risk_level", "")
            
            if risk_pos == position and risk_level == "high":
                # 
                if _reduces_immunogenicity(from_aa, to_aa):
                    return (
                        1,
                        f" anchor residue（ {position}）。",
                        "High",
                    )
    
    # 3.  FR mismatch（）
    if region.startswith("FR") and position not in VHH_HALLMARK_POSITIONS:
        # ，
        if _is_humanization_mutation(from_aa, to_aa, region):
            return (
                1,
                f" FR {region} （ {position}），。",
                "Low",
            )
    
    return (-1, "", "")


def _check_tier_2(
    position: int,
    from_aa: str,
    to_aa: str,
    region: str,
    sequence: str,
    cmc_risks: Optional[List[Dict[str, Any]]] = None,
    immunogenicity_risks: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[int, str, str]:
    """ Tier 2（）"""
    
    # 1. 
    if immunogenicity_risks:
        for risk in immunogenicity_risks:
            risk_pos = risk.get("position", 0)
            risk_level = risk.get("risk_level", "")
            
            if risk_pos == position and risk_level in ["medium", "high"]:
                if _reduces_immunogenicity(from_aa, to_aa):
                    return (
                        2,
                        f"（ {position}）。",
                        "Medium",
                    )
    
    # 2.  CMC 
    if cmc_risks:
        for risk in cmc_risks:
            risk_pos = risk.get("position", 0)
            risk_level = risk.get("risk_level", "")
            
            if risk_pos == position and risk_level in ["medium", "high"]:
                if _fixes_cmc_risk(from_aa, to_aa, risk.get("type", "")):
                    return (
                        2,
                        f" CMC {risk.get('type', '')} （ {position}）。",
                        "Medium",
                    )
    
    # 3.  aggregation（：→）
    if _reduces_aggregation(from_aa, to_aa):
        return (
            2,
            f"（ {position}：{from_aa}→{to_aa}）。",
            "Low",
        )
    
    # 4.  paratope（FR ， CDR）
    if region.startswith("FR") and position not in VHH_HALLMARK_POSITIONS:
        return (
            2,
            f"FR {region} （ {position}）， paratope。",
            "Low",
        )
    
    return (-1, "", "")


def _check_tier_3(
    position: int,
    from_aa: str,
    to_aa: str,
    region: str,
    sequence: str,
) -> Tuple[int, str, str, str]:
    """ Tier 3（/）"""
    
    # 1. CDR aromatic enrichment
    if region in ["CDR1", "CDR2", "CDR3"]:
        aromatic_aas = {"Y", "W", "F", "H"}
        if to_aa in aromatic_aas and from_aa not in aromatic_aas:
            return (
                3,
                f"CDR {region} （ {position}：{from_aa}→{to_aa}）， π-π stacking。",
                "Medium",
                "⚠️ ：CDR ，。",
            )
    
    # 2. Apex rigidification（CDR3 ）
    if region == "CDR3":
        if from_aa in {"G", "S"} and to_aa == "P":
            return (
                3,
                f"CDR3 （ {position}：{from_aa}→{to_aa}）， loop 。",
                "Medium",
                "⚠️ ：Proline  CDR3 ，。",
            )
    
    # 3. Electrostatic steering
    pos_charged = {"K", "R", "H"}
    neg_charged = {"D", "E"}
    if (from_aa in pos_charged and to_aa in neg_charged) or (
        from_aa in neg_charged and to_aa in pos_charged
    ):
        return (
            3,
            f"（ {position}：{from_aa}→{to_aa}）， electrostatic steering。",
            "Medium",
            "⚠️ ：， SPR 。",
        )
    
    #  Tier 3
    return (
        3,
        f"（ {position}：{from_aa}→{to_aa}），。",
        "Medium",
        "⚠️ ：，， Seq1/Seq2。",
    )


# 

def _fixes_cmc_risk(from_aa: str, to_aa: str, risk_type: str) -> bool:
    """ CMC """
    if risk_type in ["deamidation", ""]:
        # N→Q, N→N
        return from_aa == "N" and to_aa != "N"
    if risk_type in ["isomerization", ""]:
        # D→E, D→D
        return from_aa == "D" and to_aa != "D"
    if risk_type in ["oxidation", ""]:
        # M→L, M→I, W→F, W→Y
        return (from_aa == "M" and to_aa in {"L", "I"}) or (
            from_aa == "W" and to_aa in {"F", "Y"}
        )
    return False


def _reduces_immunogenicity(from_aa: str, to_aa: str) -> bool:
    """（：→）"""
    # 
    human_common = {"A", "S", "T", "N", "D", "E", "Q", "K", "R", "H", "G", "P", "V", "L", "I", "M", "F", "Y", "W"}
    # ： to_aa ， from_aa ，
    return to_aa in human_common


def _reduces_aggregation(from_aa: str, to_aa: str) -> bool:
    """（→）"""
    hydrophobic = {"F", "W", "Y", "L", "I", "V", "M", "A"}
    hydrophilic = {"S", "T", "N", "D", "E", "Q", "K", "R", "H", "G", "P"}
    return from_aa in hydrophobic and to_aa in hydrophilic


def _is_humanization_mutation(from_aa: str, to_aa: str, region: str) -> bool:
    """（：FR ，）"""
    # ：FR 
    return region.startswith("FR")


def classify_all_mutations(
    mutations: List[Dict[str, Any]],
    sequence: str,
    segmentation: Dict[str, Any],
    cmc_risks: Optional[List[Dict[str, Any]]] = None,
    immunogenicity_risks: Optional[List[Dict[str, Any]]] = None,
    hallmark_positions: Optional[Dict[str, List[int]]] = None,
) -> Dict[int, List[TieredMutation]]:
    """
    
    
    Returns:
         Tier  {tier: [TieredMutation, ...]}
    """
    tiered_mutations: Dict[int, List[TieredMutation]] = {0: [], 1: [], 2: [], 3: []}
    
    for mut in mutations:
        tiered = classify_mutation_tier(
            mut, sequence, segmentation, cmc_risks, immunogenicity_risks, hallmark_positions
        )
        tiered_mutations[tiered.tier].append(tiered)
    
    return tiered_mutations


def generate_three_final_sequences(
    original_sequence: str,
    tiered_mutations: Dict[int, List[TieredMutation]],
) -> Dict[str, Dict[str, Any]]:
    """
    （Seq1, Seq2, Seq3）
    
    Returns:
        {
            "seq1": {"sequence": str, "mutations": [...], "description": str},
            "seq2": {"sequence": str, "mutations": [...], "description": str},
            "seq3": {"sequence": str, "mutations": [...], "description": str},
        }
    """
    seq_list = list(original_sequence)
    
    # Seq1: Base Humanized · Mandatory Tier 1 Only
    seq1_mutations = tiered_mutations.get(1, [])
    seq1 = seq_list.copy()
    for mut in seq1_mutations:
        if 0 < mut.position <= len(seq1):
            seq1[mut.position - 1] = mut.to_aa
    
    # Seq2: Safety-Optimized · Tier 1 + 2–4  Tier 2
    seq2_mutations = tiered_mutations.get(1, []) + tiered_mutations.get(2, [])[:4]
    seq2 = seq_list.copy()
    for mut in seq2_mutations:
        if 0 < mut.position <= len(seq2):
            seq2[mut.position - 1] = mut.to_aa
    
    # Seq3: Affinity-Optimized · Tier 1 + T2/T3（≤4 ）
    #  Tier 2， Tier 3（4）
    seq3_tier2 = tiered_mutations.get(2, [])[:2]  # 2 Tier 2
    seq3_tier3 = tiered_mutations.get(3, [])[:2]  # 2 Tier 3
    seq3_mutations = tiered_mutations.get(1, []) + seq3_tier2 + seq3_tier3
    seq3 = seq_list.copy()
    for mut in seq3_mutations:
        if 0 < mut.position <= len(seq3):
            seq3[mut.position - 1] = mut.to_aa
    
    return {
        "seq1": {
            "sequence": "".join(seq1),
            "mutations": seq1_mutations,
            "description": "Base Humanized · Mandatory Tier 1 Only（，）",
        },
        "seq2": {
            "sequence": "".join(seq2),
            "mutations": seq2_mutations,
            "description": "Safety-Optimized · Tier 1 + 2–4  Tier 2（）",
        },
        "seq3": {
            "sequence": "".join(seq3),
            "mutations": seq3_mutations,
            "description": "Affinity-Optimized · Tier 1 + T2/T3（≤4 ）（， SPR ）",
        },
    }
















