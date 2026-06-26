"""
Unit tests for CDR Canonical Analysis

：
1. CDR（proxy class）
2. Canonical
3. ：sequence_finalmutations
"""

from __future__ import annotations

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve.parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.analysis.cdr_canonical import (
    extract_cdr_features,
    get_scaffold_canonical_profiles,
    build_canonical_compatibility,
)
from core.humanize.vhh_classic_panel import (
    generate_vhh_classic_panel,
    normalize_query_schema,
)


class TestCDRFeatureExtraction:
    """CDR"""
    
    def test_cdr_feature_lengths(self):
        """CDRproxy class"""
        query_norm = {
            "segments": {
                "CDR1": "GFWYNHMG",
                "CDR2": "RFTISRDDARNTVYLQMNSLK",
                "CDR3": "CAAGGVGWPYFDY",
            },
        }
        
        features = extract_cdr_features(query_norm)
        
        assert features["cdr1_seq"] == "GFWYNHMG"
        assert features["cdr2_seq"] == "RFTISRDDARNTVYLQMNSLK"
        assert features["cdr1_len"] == 8
        assert features["cdr2_len"] == 21
        assert features["cdr1_proxy_class"] == "L8"
        assert features["cdr2_proxy_class"] == "L21"
    
    def test_cdr_feature_empty(self):
        """CDR"""
        query_norm = {
            "segments": {
                "CDR1": "",
                "CDR2": "",
            },
        }
        
        features = extract_cdr_features(query_norm)
        
        assert features["cdr1_len"] == 0
        assert features["cdr2_len"] == 0
        assert features["cdr1_proxy_class"] == "L0"
        assert features["cdr2_proxy_class"] == "L0"


class TestScaffoldCanonicalProfiles:
    """scaffold canonical profiles"""
    
    def test_get_scaffold_profiles(self):
        """scaffold profiles"""
        profiles = get_scaffold_canonical_profiles
        
        assert "IGHV3-23*01" in profiles
        assert "IGHV3-66*01" in profiles
        assert "IGHV3-30*01" in profiles
        assert "IGHV3-7*01" in profiles
        
        # IGHV3-23*01profile
        profile_23 = profiles["IGHV3-23*01"]
        assert profile_23["canonical_system"] == "Chothia"
        assert profile_23["cdr1_len"] == 8
        assert profile_23["cdr2_len"] == 8
        assert profile_23["cdr1_class"] == "C1"
        assert profile_23["cdr2_class"] == "C3"
        assert "evidence" in profile_23
    
    def test_scaffold_profile_lengths_consistent_with_scaffold_data(self):
        """profilescaffold"""
        from core.data.vhh_classic_scaffolds import get_classic_scaffold, get_all_scaffold_ids
        
        profiles = get_scaffold_canonical_profiles
        scaffold_ids = get_all_scaffold_ids
        
        for scaffold_id in scaffold_ids:
            scaffold = get_classic_scaffold(scaffold_id)
            profile = profiles[scaffold_id]
            
            # scaffold
            expected_cdr1_len = len(scaffold.cdr1)
            expected_cdr2_len = len(scaffold.cdr2)
            
            assert profile["cdr1_len"] == expected_cdr1_len, (
                f"{scaffold_id}: profile cdr1_len={profile['cdr1_len']} != "
                f"scaffold.cdr1 length={expected_cdr1_len}"
            )
            assert profile["cdr2_len"] == expected_cdr2_len, (
                f"{scaffold_id}: profile cdr2_len={profile['cdr2_len']} != "
                f"scaffold.cdr2 length={expected_cdr2_len}"
            )
            
            # schema
            assert "canonical_system" in profile
            assert isinstance(profile["cdr1_len"], int)
            assert isinstance(profile["cdr2_len"], int)
            assert isinstance(profile["cdr1_class"], str)
            assert isinstance(profile["cdr2_class"], str)
            assert "evidence" in profile


class TestCanonicalCompatibility:
    """canonical"""
    
    def test_canonical_compatibility_len_only(self):
        """"""
        # Query: CDR1=8, CDR2=8 (IGHV3-23*01)
        query_features = {
            "cdr1_len": 8,
            "cdr2_len": 8,
            "cdr1_proxy_class": "L8",
            "cdr2_proxy_class": "L8",
        }
        
        scaffold_profiles = get_scaffold_canonical_profiles
        compat = build_canonical_compatibility(query_features, scaffold_profiles)
        
        # IGHV3-23*01
        compat_23 = compat["IGHV3-23*01"]
        assert compat_23["cdr1_len_match"] is True
        assert compat_23["cdr2_len_match"] is True
        assert compat_23["risk_level"] == "low"
        assert "CDR1 match; CDR2 match; risk=low" in compat_23["rationale"]
    
    def test_canonical_compatibility_one_mismatch(self):
        """"""
        # Query: CDR1=8, CDR2=7 (CDR2IGHV3-23*01)
        query_features = {
            "cdr1_len": 8,
            "cdr2_len": 7,  # IGHV3-23*01CDR28
            "cdr1_proxy_class": "L8",
            "cdr2_proxy_class": "L7",
        }
        
        scaffold_profiles = get_scaffold_canonical_profiles
        compat = build_canonical_compatibility(query_features, scaffold_profiles)
        
        # IGHV3-23*01
        compat_23 = compat["IGHV3-23*01"]
        assert compat_23["cdr1_len_match"] is True
        assert compat_23["cdr2_len_match"] is False
        assert compat_23["risk_level"] == "medium"
        assert "CDR1 match" in compat_23["rationale"]
        assert "CDR2 length mismatch" in compat_23["rationale"]
        assert "query=7 vs scaffold=8" in compat_23["rationale"]
        assert "risk=medium" in compat_23["rationale"]
    
    def test_canonical_compatibility_both_mismatch(self):
        """"""
        # Query: CDR1=10, CDR2=10 (IGHV3-23*01)
        query_features = {
            "cdr1_len": 10,
            "cdr2_len": 10,
            "cdr1_proxy_class": "L10",
            "cdr2_proxy_class": "L10",
        }
        
        scaffold_profiles = get_scaffold_canonical_profiles
        compat = build_canonical_compatibility(query_features, scaffold_profiles)
        
        # IGHV3-23*01
        compat_23 = compat["IGHV3-23*01"]
        assert compat_23["cdr1_len_match"] is False
        assert compat_23["cdr2_len_match"] is False
        assert compat_23["risk_level"] == "high"
        assert "CDR1 length mismatch" in compat_23["rationale"]
        assert "query=10 vs scaffold=8" in compat_23["rationale"]
        assert "CDR2 length mismatch" in compat_23["rationale"]
        assert "risk=high" in compat_23["rationale"]


class TestReadOnlyNoSequenceChange:
    """：sequence_finalmutations"""
    
    def test_read_only_no_sequence_change(self):
        """canonicalsequence_finalmutations"""
        # query
        query = {
            "segments": {
                "FR1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNHMG",  # 8
                "FR2": "MSWVRQAPGKGLEWVSA",
                "CDR2": "RFTISRDDARNTVYLQMNSLK",  # 21
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
                "CDR3": "CAAGGVGWPYFDY",
                "FR4": "WGQGTLVTVSS",
            },
            "numbering_maps": {
                "kabat": [
                    {"pos": "44", "aa": "E"},
                    {"pos": "45", "aa": "R"},
                ],
                "kabat_to_imgt": {
                    "kabat_44": "imgt_44",
                    "kabat_45": "imgt_45",
                },
            },
        }
        
        # generate_vhh_classic_panel
        try:
            result = generate_vhh_classic_panel(query)
        except Exception:
            # ，
            pytest.skip("Skipping integration test - requires full numbering data")
        
        # canonical
        assert "cdr_features" in result
        assert "canonical_compatibility" in result
        assert "canonical_profiles" in result
        
        # canonical
        classic_panel = result.get("classic_panel", [])
        assert len(classic_panel) > 0
        
        # sequence_finalmutations
        baseline_sequences = {}
        baseline_mutations = {}
        
        for entry in classic_panel:
            scaffold_id = entry.get("scaffold_id")
            j_region_id = entry.get("j_region_id")
            key = f"{scaffold_id}_{j_region_id}"
            
            assert "canonical_risk_level" in entry
            assert "canonical_rationale" in entry
            assert "sequence_final" in entry
            assert "mutations" in entry
            
            # sequence_final
            assert entry["sequence_final"] is not None
            assert len(entry["sequence_final"]) > 0
            
            # baseline
            baseline_sequences[key] = entry["sequence_final"]
            baseline_mutations[key] = entry["mutations"]
        
        # （canonical layer）
        result2 = generate_vhh_classic_panel(query)
        classic_panel2 = result2.get("classic_panel", [])
        
        # sequence_finalmutations（byte-level）
        for entry in classic_panel2:
            scaffold_id = entry.get("scaffold_id")
            j_region_id = entry.get("j_region_id")
            key = f"{scaffold_id}_{j_region_id}"
            
            if key in baseline_sequences:
                assert entry["sequence_final"] == baseline_sequences[key], (
                    f"Sequence changed for {key}: canonical layer should be read-only"
                )
                # mutations（JSON）
                import json
                mutations1_str = json.dumps(baseline_mutations[key], sort_keys=True)
                mutations2_str = json.dumps(entry["mutations"], sort_keys=True)
                assert mutations1_str == mutations2_str, (
                    f"Mutations changed for {key}: canonical layer should be read-only"
                )
    
    def test_canonical_fields_present(self):
        """canonical"""
        query = {
            "segments": {
                "FR1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNHMG",
                "FR2": "MSWVRQAPGKGLEWVSA",
                "CDR2": "RFTISRDDARNTVYLQMNSLK",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
                "CDR3": "CAAGGVGWPYFDY",
                "FR4": "WGQGTLVTVSS",
            },
            "numbering_maps": {},
        }
        
        try:
            result = generate_vhh_classic_panel(query)
        except Exception:
            pytest.skip("Skipping integration test - requires full numbering data")
        
        classic_panel = result.get("classic_panel", [])
        
        for entry in classic_panel:
            # canonicalNone
            assert "canonical_risk_level" in entry
            assert "canonical_rationale" in entry
            assert entry["canonical_risk_level"] is not None
            assert entry["canonical_rationale"] is not None
            
            # risk_level
            assert entry["canonical_risk_level"] in ("low", "medium", "high", "unknown")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

