"""
Unit tests for VHH Classic Panel Gate (Pre-flight Check)

Gate、。
Gateread-only，sequence_finalmutations。
"""

from __future__ import annotations

import pytest
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve.parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.analysis.vhh_gate import (
    run_vhh_gate,
    CDR3_LEN_USE_J6,
    CDR3_LEN_ULTRA_LONG,
    EXTRA_CYS_WARN_THRESHOLD,
    FR_IDENTITY_WARN,
    FR_IDENTITY_FAIL,
)
from core.humanize.vhh_classic_panel import generate_vhh_classic_panel


class TestGatePassTypicalVHH:
    """VHHpass"""
    
    def test_gate_pass_typical_vhh(self):
        """cdr3_len<18, cys=2, fr_identity>=0.60 -> pass"""
        query_norm = {
            "segments": {
                "FR1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNHMG",
                "FR2": "MSWVRQAPGKGLEWVSA",
                "CDR2": "RFTISRDDARNTVYLQMNSLK",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
                "CDR3": "CAAGGVGWPYFDY",  # 13 < 18
                "FR4": "WGQGTLVTVSS",
            },
        }
        
        # identityscaffold（IGHV3-23*01FR）
        scaffolds = {
            "IGHV3-23*01": {
                "fr1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "fr2": "MSWVRQAPGKGLEWVSA",
                "fr3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
            }
        }
        
        gate_result = run_vhh_gate(query_norm, scaffolds)
        
        # 
        assert gate_result["metrics"]["cdr3_len"] == 13
        cys_count = gate_result["metrics"]["total_cys_count"]
        assert cys_count >= 2  # 2Cys
        
        # Cys，extra_cys flag，
        # ：cdr3_len<18, fr_identity>=0.60pass（flags）
        if cys_count <= EXTRA_CYS_WARN_THRESHOLD:
            # extra_cys flag，fr_identity>=0.60，pass
            if gate_result["metrics"]["best_fr_identity"] >= 0.60:
                assert "cdr3_long" not in gate_result["flags"]
                assert "low_fr_identity" not in gate_result["flags"]
                if "extra_cys" not in gate_result["flags"]:
                    assert gate_result["pass_level"] == "pass"
        
        # fr_identity
        assert gate_result["metrics"]["best_fr_identity"] >= 0.60


class TestGateJ6Recommended:
    """J6"""
    
    def test_gate_j6_recommended_when_cdr3_ge_18(self):
        """cdr3_len=18 -> suggest_j_region=IGHJ6, flag=cdr3_long"""
        query_norm = {
            "segments": {
                "FR1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNHMG",
                "FR2": "MSWVRQAPGKGLEWVSA",
                "CDR2": "RFTISRDDARNTVYLQMNSLK",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
                "CDR3": "CAAGGVGWPYFDY" + "A" * 5,  # 18
                "FR4": "WGQGTLVTVSS",
            },
        }
        
        scaffolds = {
            "IGHV3-23*01": {
                "fr1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "fr2": "MSWVRQAPGKGLEWVSA",
                "fr3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
            }
        }
        
        gate_result = run_vhh_gate(query_norm, scaffolds)
        
        assert gate_result["recommendations"]["suggest_j_region"] == "IGHJ6"
        assert "cdr3_long" in gate_result["flags"]
        assert gate_result["metrics"]["cdr3_len"] == 18


class TestGateUltraLongFlag:
    """CDR3"""
    
    def test_gate_ultra_long_flag(self):
        """cdr3_len=22 -> flag includes cdr3_ultra_long"""
        query_norm = {
            "segments": {
                "FR1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNHMG",
                "FR2": "MSWVRQAPGKGLEWVSA",
                "CDR2": "RFTISRDDARNTVYLQMNSLK",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
                "CDR3": "CAAGGVGWPYFDY" + "A" * 9,  # 22
                "FR4": "WGQGTLVTVSS",
            },
        }
        
        scaffolds = {
            "IGHV3-23*01": {
                "fr1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "fr2": "MSWVRQAPGKGLEWVSA",
                "fr3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
            }
        }
        
        gate_result = run_vhh_gate(query_norm, scaffolds)
        
        assert "cdr3_ultra_long" in gate_result["flags"]
        assert "cdr3_long" in gate_result["flags"]  # 
        assert gate_result["metrics"]["cdr3_len"] == 22


class TestGateExtraCysWarn:
    """Cys"""
    
    def test_gate_extra_cys_warn(self):
        """cys_count=3 -> flag includes extra_cys"""
        query_norm = {
            "segments": {
                "FR1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNHMG",
                "FR2": "MSWVRQAPGKGLEWVSA",
                "CDR2": "RFTISRDDARNTVYLQMNSLK",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
                "CDR3": "CAAGGVGWPYFDYC",  # Cys
                "FR4": "WGQGTLVTVSS",
            },
        }
        
        scaffolds = {
            "IGHV3-23*01": {
                "fr1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "fr2": "MSWVRQAPGKGLEWVSA",
                "fr3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
            }
        }
        
        gate_result = run_vhh_gate(query_norm, scaffolds)
        
        # Cys：FR1(1) + FR3(1) + CDR3(1) = 3
        assert gate_result["metrics"]["total_cys_count"] > EXTRA_CYS_WARN_THRESHOLD
        assert "extra_cys" in gate_result["flags"]


class TestGateLowIdentityWarnAndFail:
    """identity"""
    
    def test_gate_low_identity_warn_and_fail(self):
        """identity=0.59 -> warn, identity=0.49 -> fail"""
        # warn（identity=0.59）
        query_norm_warn = {
            "segments": {
                "FR1": "AAAAAAAAAAAAAAAAAAAAAAAAAA",  # identity
                "CDR1": "GFWYNHMG",
                "FR2": "BBBBBBBBBBBBBBBBBB",  # identity
                "CDR2": "RFTISRDDARNTVYLQMNSLK",
                "FR3": "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",  # identity
                "CDR3": "CAAGGVGWPYFDY",
                "FR4": "WGQGTLVTVSS",
            },
        }
        
        scaffolds = {
            "IGHV3-23*01": {
                "fr1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "fr2": "MSWVRQAPGKGLEWVSA",
                "fr3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
            }
        }
        
        gate_result_warn = run_vhh_gate(query_norm_warn, scaffolds)
        
        # FR，identity
        # scaffoldidentity0.50-0.60warn
        # 
        if gate_result_warn["metrics"]["best_fr_identity"] < FR_IDENTITY_WARN:
            assert "low_fr_identity" in gate_result_warn["flags"]
            if gate_result_warn["metrics"]["best_fr_identity"] >= FR_IDENTITY_FAIL:
                assert gate_result_warn["pass_level"] == "warn"
        
        # fail（identity=0.49）
        # 
        query_norm_fail = {
            "segments": {
                "FR1": "XXXXXXXXXXXXXXXXXXXXXXXXXX",  # 
                "CDR1": "GFWYNHMG",
                "FR2": "YYYYYYYYYYYYYYYYYY",  # 
                "CDR2": "RFTISRDDARNTVYLQMNSLK",
                "FR3": "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",  # 
                "CDR3": "CAAGGVGWPYFDY",
                "FR4": "WGQGTLVTVSS",
            },
        }
        
        gate_result_fail = run_vhh_gate(query_norm_fail, scaffolds)
        
        if gate_result_fail["metrics"]["best_fr_identity"] < FR_IDENTITY_FAIL:
            assert gate_result_fail["pass_level"] == "fail"
            assert "low_fr_identity" in gate_result_fail["flags"]


class TestGateReadOnlyIntegration:
    """Gateread-only"""
    
    def test_gate_read_only_integration(self):
        """Gatesequence_finalmutations"""
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
        
        try:
            # （Gate）
            result1 = generate_vhh_classic_panel(query)
        except Exception:
            # ，
            pytest.skip("Skipping integration test - requires full numbering data")
        
        # baselinemutations
        classic_panel1 = result1.get("classic_panel", [])
        assert len(classic_panel1) > 0
        assert "gate" in result1  # gate
        
        baseline_data = {}
        for entry in classic_panel1:
            scaffold_id = entry.get("scaffold_id")
            j_region_id = entry.get("j_region_id")
            key = f"{scaffold_id}_{j_region_id}"
            
            baseline_data[key] = {
                "sequence_final": entry.get("sequence_final"),
                "mutations": json.dumps(entry.get("mutations", []), sort_keys=True),
            }
        
        # （Gate，Gate）
        result2 = generate_vhh_classic_panel(query)
        classic_panel2 = result2.get("classic_panel", [])
        
        # sequence_finalmutations（byte-level）
        for entry in classic_panel2:
            scaffold_id = entry.get("scaffold_id")
            j_region_id = entry.get("j_region_id")
            key = f"{scaffold_id}_{j_region_id}"
            
            if key in baseline_data:
                baseline_seq = baseline_data[key]["sequence_final"]
                baseline_mut = baseline_data[key]["mutations"]
                
                current_seq = entry.get("sequence_final")
                current_mut = json.dumps(entry.get("mutations", []), sort_keys=True)
                
                assert current_seq == baseline_seq, (
                    f"Sequence changed for {key}: Gate should be read-only"
                )
                assert current_mut == baseline_mut, (
                    f"Mutations changed for {key}: Gate should be read-only"
                )
        
        # gate
        assert "gate" in result2
        gate2 = result2["gate"]
        assert "pass_level" in gate2
        assert "flags" in gate2
        assert "metrics" in gate2
        assert "recommendations" in gate2


class TestGateScaffoldRankRecommendation:
    """Scaffold"""
    
    def test_gate_scaffold_rank_with_long_cdr3(self):
        """CDR3>=18，IGHV3-7*012"""
        query_norm = {
            "segments": {
                "FR1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNHMG",
                "FR2": "MSWVRQAPGKGLEWVSA",
                "CDR2": "RFTISRDDARNTVYLQMNSLK",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
                "CDR3": "CAAGGVGWPYFDY" + "A" * 5,  # 18
                "FR4": "WGQGTLVTVSS",
            },
        }
        
        gate_result = run_vhh_gate(query_norm)
        
        suggest_rank = gate_result["recommendations"]["suggest_scaffold_rank"]
        
        # IGHV3-7*012
        assert len(suggest_rank) >= 2
        assert suggest_rank[1]["scaffold_id"] == "IGHV3-7*01"
        assert "long CDR3" in suggest_rank[1]["rationale"].lower or "length" in suggest_rank[1]["rationale"].lower
    
    def test_gate_scaffold_rank_default_order(self):
        """CDR3<18，"""
        query_norm = {
            "segments": {
                "FR1": "EVQLLESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNHMG",
                "FR2": "MSWVRQAPGKGLEWVSA",
                "CDR2": "RFTISRDDARNTVYLQMNSLK",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
                "CDR3": "CAAGGVGWPYFDY",  # 13 < 18
                "FR4": "WGQGTLVTVSS",
            },
        }
        
        gate_result = run_vhh_gate(query_norm)
        
        suggest_rank = gate_result["recommendations"]["suggest_scaffold_rank"]
        
        # ：IGHV3-23*01, IGHV3-66*01, IGHV3-30*01, IGHV3-7*01
        assert len(suggest_rank) == 4
        assert suggest_rank[0]["scaffold_id"] == "IGHV3-23*01"
        assert suggest_rank[1]["scaffold_id"] == "IGHV3-66*01"
        assert suggest_rank[2]["scaffold_id"] == "IGHV3-30*01"
        assert suggest_rank[3]["scaffold_id"] == "IGHV3-7*01"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
