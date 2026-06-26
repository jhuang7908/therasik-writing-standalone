"""
Unit tests for Rulebook v1.0

、。
"""

from __future__ import annotations

import pytest
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve.parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.humanize.rulebook_v1 import (
    RuleLayer,
    RuleMode,
    RiskLevel,
    TargetRegion,
    RuleDefinition,
    get_rule_definition,
    get_rules_by_layer,
    get_rules_by_mode,
    RULEBOOK_V1,
)
from core.humanize.mutations_rules import (
    apply_hallmark_rules,
    apply_vernier_backfill,
    apply_all_mutation_rules,
    MutationRecord,
)
from core.humanize.vhh_classic_panel import generate_vhh_classic_panel


class TestRulebookDefinitions:
    """"""
    
    def test_rulebook_has_all_required_rules(self):
        """Rulebook"""
        required_rules = ["HALLMARK_FR2_44", "HALLMARK_FR2_45", "VERNIER_ANCHOR", "VERNIER_TUNING"]
        for rule_id in required_rules:
            assert rule_id in RULEBOOK_V1, f"Rule {rule_id} not found in RULEBOOK_V1"
    
    def test_rule_definitions_have_all_fields(self):
        """"""
        for rule_id, rule_def in RULEBOOK_V1.items:
            assert rule_def.rule_id == rule_id
            assert rule_def.layer in (RuleLayer.A, RuleLayer.B)
            assert rule_def.target_region in (TargetRegion.FR2, TargetRegion.VERNIER, TargetRegion.CANONICAL)
            assert rule_def.purpose
            assert rule_def.evidence_level
            assert rule_def.trigger_conditions
            assert rule_def.action
            assert rule_def.default_mode in (RuleMode.MVP, RuleMode.EXPERT)
            assert rule_def.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH)
            assert rule_def.rationale_template
            assert rule_def.rationale_explanation
    
    def test_hallmark_rules_are_layer_a(self):
        """HallmarkLayer A"""
        rule_44 = get_rule_definition("HALLMARK_FR2_44")
        rule_45 = get_rule_definition("HALLMARK_FR2_45")
        
        assert rule_44.layer == RuleLayer.A
        assert rule_45.layer == RuleLayer.A
    
    def test_vernier_rules_are_layer_b(self):
        """VernierLayer B"""
        rule_anchor = get_rule_definition("VERNIER_ANCHOR")
        rule_tuning = get_rule_definition("VERNIER_TUNING")
        
        assert rule_anchor.layer == RuleLayer.B
        assert rule_tuning.layer == RuleLayer.B
    
    def test_hallmark_rules_exclude_positions(self):
        """Hallmarkexcluded_positions"""
        rule_44 = get_rule_definition("HALLMARK_FR2_44")
        rule_45 = get_rule_definition("HALLMARK_FR2_45")
        
        assert rule_44.excluded_positions == [37, 47, 49]
        assert rule_45.excluded_positions == [37, 47, 49]
        assert rule_44.excluded_rationale
        assert rule_45.excluded_rationale


class TestRuleFiltering:
    """"""
    
    def test_get_rules_by_layer(self):
        """"""
        layer_a_rules = get_rules_by_layer(RuleLayer.A)
        layer_b_rules = get_rules_by_layer(RuleLayer.B)
        
        assert len(layer_a_rules) == 2  # HALLMARK_FR2_44, HALLMARK_FR2_45
        assert len(layer_b_rules) == 2  # VERNIER_ANCHOR, VERNIER_TUNING
        
        assert all(rule.layer == RuleLayer.A for rule in layer_a_rules)
        assert all(rule.layer == RuleLayer.B for rule in layer_b_rules)
    
    def test_get_rules_by_mode_mvp(self):
        """MVP"""
        mvp_rules = get_rules_by_mode(RuleMode.MVP)
        mvp_rule_ids = {rule.rule_id for rule in mvp_rules}
        
        # MVPMVPLayer A
        assert "HALLMARK_FR2_44" in mvp_rule_ids
        assert "HALLMARK_FR2_45" in mvp_rule_ids
        assert "VERNIER_TUNING" in mvp_rule_ids
        # VERNIER_ANCHORexpert
        assert "VERNIER_ANCHOR" not in mvp_rule_ids
    
    def test_get_rules_by_mode_expert(self):
        """Expert"""
        expert_rules = get_rules_by_mode(RuleMode.EXPERT)
        expert_rule_ids = {rule.rule_id for rule in expert_rules}
        
        # Expert
        assert "HALLMARK_FR2_44" in expert_rule_ids
        assert "HALLMARK_FR2_45" in expert_rule_ids
        assert "VERNIER_TUNING" in expert_rule_ids
        assert "VERNIER_ANCHOR" in expert_rule_ids


class TestMutationRecordEnhancement:
    """MutationRecord"""
    
    def test_mutation_record_has_rulebook_fields(self):
        """MutationRecordRulebook"""
        # 
        rule_def = get_rule_definition("HALLMARK_FR2_44")
        
        mut = MutationRecord(
            rule_id="HALLMARK_FR2_44",
            numbering={"kabat": 44, "imgt": "44", "aho": None},
            from_aa="G",
            to_aa="E",
            rationale="Test rationale",
            evidence_level="rule_based",
            layer=rule_def.layer.value,
            risk_level=rule_def.risk_level.value,
            purpose=rule_def.purpose,
            trigger_explanation="Query Kabat 44: E | Scaffold Kabat 44: G",
        )
        
        assert mut.layer == "A"
        assert mut.risk_level == "low"
        assert mut.purpose
        assert mut.trigger_explanation


class TestMvpModeSequenceConsistency:
    """MVP"""
    
    def test_mvp_mode_sequence_unchanged(self):
        """MVP，（byte-level）"""
        query = {
            "segments": {
                "FR1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MSWVRQAPGKEREGVAV",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTLVTVSS",
            },
            "numbering_maps": {},
        }
        
        # （，Rulebook）
        result1 = generate_vhh_classic_panel(query, panel_config={"mode": "mvp"})
        
        # baseline
        baseline_sequences = {}
        for entry in result1.get("classic_panel", []):
            key = f"{entry.get('scaffold_id')}_{entry.get('j_region_id')}"
            baseline_sequences[key] = entry.get("sequence_final")
            baseline_mutations = entry.get("mutations", [])
            # 
            for mut in baseline_mutations:
                assert "layer" in mut
                assert "risk_level" in mut
                assert "purpose" in mut
                assert "trigger_explanation" in mut
        
        # 
        result2 = generate_vhh_classic_panel(query, panel_config={"mode": "mvp"})
        
        # （byte-level）
        for entry in result2.get("classic_panel", []):
            key = f"{entry.get('scaffold_id')}_{entry.get('j_region_id')}"
            current_seq = entry.get("sequence_final")
            baseline_seq = baseline_sequences.get(key)
            
            assert current_seq == baseline_seq, (
                f"Sequence changed for {key}: MVP mode should not alter sequence_final"
            )
    
    def test_mvp_vs_expert_mode_difference(self):
        """MVPExpert（Expert）"""
        query = {
            "segments": {
                "FR1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MSWVRQAPGKEREGVAV",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTLVTVSS",
            },
            "numbering_maps": {},
        }
        
        result_mvp = generate_vhh_classic_panel(query, panel_config={"mode": "mvp"})
        result_expert = generate_vhh_classic_panel(query, panel_config={"mode": "expert"})
        
        # Expert（Vernier anchor）
        mvp_total_mutations = result_mvp.get("rulebook_summary", {}).get("total_mutations", 0)
        expert_total_mutations = result_expert.get("rulebook_summary", {}).get("total_mutations", 0)
        
        # Expert >= MVP（，anchor）
        assert expert_total_mutations >= mvp_total_mutations
        
        # rulebook_summary
        assert "rulebook_summary" in result_mvp
        assert "rulebook_summary" in result_expert


class TestRulebookOutputFields:
    """Rulebook"""
    
    def test_mutations_have_rulebook_fields(self):
        """mutationsRulebook"""
        query = {
            "segments": {
                "FR1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MSWVRQAPGKEREGVAV",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTLVTVSS",
            },
            "numbering_maps": {},
        }
        
        result = generate_vhh_classic_panel(query, panel_config={"mode": "mvp"})
        
        for entry in result.get("classic_panel", []):
            mutations = entry.get("mutations", [])
            for mut in mutations:
                assert "layer" in mut, f"Mutation {mut.get('rule_id')} missing 'layer' field"
                assert "risk_level" in mut, f"Mutation {mut.get('rule_id')} missing 'risk_level' field"
                assert "purpose" in mut, f"Mutation {mut.get('rule_id')} missing 'purpose' field"
                assert "trigger_explanation" in mut, f"Mutation {mut.get('rule_id')} missing 'trigger_explanation' field"
    
    def test_rulebook_summary_exists(self):
        """rulebook_summary"""
        query = {
            "segments": {
                "FR1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MSWVRQAPGKEREGVAV",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTLVTVSS",
            },
            "numbering_maps": {},
        }
        
        result = generate_vhh_classic_panel(query, panel_config={"mode": "mvp"})
        
        assert "rulebook_summary" in result
        summary = result["rulebook_summary"]
        
        assert "rulebook_version" in summary
        assert "mode" in summary
        assert "triggered_rules" in summary
        assert "available_rules" in summary
        assert "total_mutations" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

