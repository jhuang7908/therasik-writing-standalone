"""
VHH Classic Panel Rulebook v1.0

、、
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class RuleLayer(str, Enum):
    """"""
    A = "A"  # Hard rule: 
    B = "B"  # Conditional rule: 


class RuleMode(str, Enum):
    """"""
    MVP = "mvp"  # MVP：
    EXPERT = "expert"  # Expert：


class RiskLevel(str, Enum):
    """"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TargetRegion(str, Enum):
    """"""
    FR2 = "FR2"
    VERNIER = "Vernier"
    CANONICAL = "Canonical"


@dataclass
class RuleDefinition:
    """"""
    rule_id: str
    layer: RuleLayer
    target_region: TargetRegion
    purpose: str
    evidence_level: str
    trigger_conditions: Dict[str, Any]  # 
    action: str  # 
    default_mode: RuleMode
    risk_level: RiskLevel
    rationale_template: str  # ，
    rationale_explanation: str  # 
    excluded_positions: Optional[List[int]] = None  # （V2）
    excluded_rationale: Optional[str] = None  # 


# ============================================================================
# Rulebook v1.0 Definitions
# ============================================================================

RULEBOOK_V1: Dict[str, RuleDefinition] = {
    "HALLMARK_FR2_44": RuleDefinition(
        rule_id="HALLMARK_FR2_44",
        layer=RuleLayer.A,
        target_region=TargetRegion.FR2,
        purpose="Maintain VHH hydrophilic FR2 interface to reduce aggregation risk",
        evidence_level="rule_based",
        trigger_conditions={
            "query_aa_in": ["E", "Q"],
            "scaffold_aa_not": "E",
            "position": 44,
        },
        action="Mutate scaffold Kabat 44 to E (G44E)",
        default_mode=RuleMode.MVP,
        risk_level=RiskLevel.LOW,
        rationale_template="Query position {kabat_pos} has {query_aa} (E/Q), scaffold has {scaffold_aa}. Mutating to E to maintain VHH hydrophilic FR2 interface.",
        rationale_explanation=(
            "Position 44 (Kabat) is selected as MVP minimal strong evidence set because:\n"
            "1. High conservation in VHH sequences (E/Q frequency >80%)\n"
            "2. Direct impact on aggregation risk (hydrophilic interface)\n"
            "3. Low structural risk (FR2 surface position)\n"
            "4. Positions 37/47/49 have higher variability and are reserved for V2 expansion"
        ),
        excluded_positions=[37, 47, 49],
        excluded_rationale=(
            "Positions 37, 47, 49 show higher variability across VHH sequences and may have "
            "context-dependent effects. They are reserved for V2 expansion with additional "
            "structural validation."
        ),
    ),
    "HALLMARK_FR2_45": RuleDefinition(
        rule_id="HALLMARK_FR2_45",
        layer=RuleLayer.A,
        target_region=TargetRegion.FR2,
        purpose="Maintain VHH hydrophilic FR2 interface to reduce aggregation risk",
        evidence_level="rule_based",
        trigger_conditions={
            "query_aa_equals": "R",
            "scaffold_aa_not": "R",
            "position": 45,
        },
        action="Mutate scaffold Kabat 45 to R (L45R)",
        default_mode=RuleMode.MVP,
        risk_level=RiskLevel.LOW,
        rationale_template="Query position {kabat_pos} has {query_aa} (R), scaffold has {scaffold_aa}. Mutating to R to maintain VHH hydrophilic FR2 interface.",
        rationale_explanation=(
            "Position 45 (Kabat) is selected as MVP minimal strong evidence set because:\n"
            "1. Critical for VHH-specific FR2 interface (R frequency >90% in VHH)\n"
            "2. Strong correlation with aggregation reduction\n"
            "3. Low structural risk (FR2 surface position)\n"
            "4. Positions 37/47/49 have higher variability and are reserved for V2 expansion"
        ),
        excluded_positions=[37, 47, 49],
        excluded_rationale=(
            "Positions 37, 47, 49 show higher variability across VHH sequences and may have "
            "context-dependent effects. They are reserved for V2 expansion with additional "
            "structural validation."
        ),
    ),
    "VERNIER_ANCHOR": RuleDefinition(
        rule_id="VERNIER_ANCHOR",
        layer=RuleLayer.B,
        target_region=TargetRegion.VERNIER,
        purpose="Preserve critical CDR support geometry at high-risk structural anchor points",
        evidence_level="rule_based",
        trigger_conditions={
            "query_aa_not_equals_scaffold": True,
            "position_in_whitelist": [27, 28, 29, 71, 93, 94],  # High-risk anchor points
            "not_in_cdr": True,
        },
        action="Backfill query amino acid at Vernier anchor position",
        default_mode=RuleMode.EXPERT,  # Only in expert mode
        risk_level=RiskLevel.MEDIUM,
        rationale_template="Query position {kabat_pos} has {query_aa}, scaffold has {scaffold_aa}. Backfilling to preserve CDR support geometry at anchor point.",
        rationale_explanation=(
            "Vernier anchor positions (27-29, 71, 93-94) are high-risk structural anchor points "
            "that directly support CDR geometry. These mutations are only applied in expert_mode "
            "because they require careful structural validation."
        ),
    ),
    "VERNIER_TUNING": RuleDefinition(
        rule_id="VERNIER_TUNING",
        layer=RuleLayer.B,
        target_region=TargetRegion.VERNIER,
        purpose="Preserve CDR support geometry at low-risk tuning points",
        evidence_level="rule_based",
        trigger_conditions={
            "query_aa_not_equals_scaffold": True,
            "position_in_whitelist": [30, 49, 73, 78],  # Low-risk tuning points
            "not_in_cdr": True,
        },
        action="Backfill query amino acid at Vernier tuning position",
        default_mode=RuleMode.MVP,  # Available in MVP mode
        risk_level=RiskLevel.LOW,
        rationale_template="Query position {kabat_pos} has {query_aa}, scaffold has {scaffold_aa}. Backfilling to preserve CDR support geometry.",
        rationale_explanation=(
            "Vernier tuning positions (30, 49, 73, 78) are low-risk points that can be safely "
            "adjusted in MVP mode to preserve CDR support geometry without significant structural risk."
        ),
    ),
}


def get_rule_definition(rule_id: str) -> Optional[RuleDefinition]:
    """"""
    return RULEBOOK_V1.get(rule_id)


def get_rules_by_layer(layer: RuleLayer) -> List[RuleDefinition]:
    """"""
    return [rule for rule in RULEBOOK_V1.values() if rule.layer == layer]


def get_rules_by_mode(mode: RuleMode) -> List[RuleDefinition]:
    """"""
    return [rule for rule in RULEBOOK_V1.values() if rule.default_mode == mode or mode == RuleMode.EXPERT]


def format_trigger_explanation(
    rule_def: RuleDefinition,
    kabat_pos: int,
    query_aa: str,
    scaffold_aa: str,
) -> str:
    """"""
    return (
        f"Query Kabat {kabat_pos}: {query_aa} | "
        f"Scaffold Kabat {kabat_pos}: {scaffold_aa} | "
        f"Condition: {rule_def.trigger_conditions}"
    )


def format_rationale(
    rule_def: RuleDefinition,
    kabat_pos: int,
    query_aa: str,
    scaffold_aa: str,
) -> str:
    """（）"""
    return rule_def.rationale_template.format(
        kabat_pos=kabat_pos,
        query_aa=query_aa,
        scaffold_aa=scaffold_aa,
    )

