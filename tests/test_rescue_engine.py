#!/usr/bin/env python3
"""
tests/test_rescue_engine.py — Unit tests for Round 2 + Option B rescue logic

Verifies:
  • Trigger conditions for Round 2
  • Iteration limits enforcement
  • Golden backbone selection
  • Failure reporting format
  • Audit log generation
"""

from __future__ import annotations

import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))


def test_rescue_config_limits():
    """Test that rescue config respects iteration limits."""
    from core.humanization.rescue_engine import RescueConfig, RescueEngine
    
    cfg = RescueConfig()
    assert cfg.max_round2_attempts == 3
    assert cfg.max_total_iterations == 5  # 1 + 3 + 1
    
    engine = RescueEngine(SUITE, cfg)
    
    # Check golden backbones exist
    assert "IGHV3-23*01" in cfg.golden_backbones_vh
    assert "IGKV1-39*01" in cfg.golden_backbones_vl
    
    # Check defaults
    vh, vl = engine.get_golden_backup_germlines()
    assert vh == "IGHV3-23*01"
    assert vl == "IGKV1-39*01"


def test_rescue_trigger_conditions():
    """Test that Round 2 is correctly triggered by Phase 5 failures."""
    from core.humanization.rescue_engine import RescueEngine, RescueConfig
    
    engine = RescueEngine(SUITE, RescueConfig())
    
    # pI out of range → trigger
    result_pi_high = {
        "overall_status": "WARN",
        "pI_fab": 9.2,  # > 8.5
    }
    assert engine.should_trigger_round2(result_pi_high) == True
    
    # CDR RMSD high → trigger
    result_rmsd_high = {
        "overall_status": "WARN",
        "cdr_rmsd": {"VH": 1.6, "VL": 0.9},  # VH >= 1.5
    }
    assert engine.should_trigger_round2(result_rmsd_high) == True
    
    # angle high → trigger
    result_angle_high = {
        "overall_status": "WARN",
        "angle_delta_deg": 4.5,  # > 3
    }
    assert engine.should_trigger_round2(result_angle_high) == True
    
    # All PASS → no trigger
    result_pass = {
        "overall_status": "PASS",
        "pI_fab": 7.0,
        "cdr_rmsd": {"VH": 0.8, "VL": 0.7},
        "angle_delta_deg": 1.5,
    }
    assert engine.should_trigger_round2(result_pass) == False


def test_rescue_iteration_limits():
    """Test that iteration limits are enforced."""
    from core.humanization.rescue_engine import RescueEngine, RescueConfig, RescuePhase
    
    engine = RescueEngine(SUITE, RescueConfig())
    
    # Initial: iteration_count = 1
    assert engine.iteration_count == 1
    
    # Record Round 2 attempt
    engine.record_round2_attempt(
        attempt_num=1,
        success=False,
        output_vh="seq1",
        output_vl="seq1_l",
        reason="pI too high",
    )
    assert engine.iteration_count == 2
    assert len(engine.rescue_log) == 1
    
    # Can attempt Round 2 attempt 2?
    can, reason = engine.can_attempt_round2()
    assert can == True
    
    # Record attempts 2 and 3
    engine.record_round2_attempt(2, False, "s2", "s2l", reason="pI still high")
    assert engine.iteration_count == 3
    
    engine.record_round2_attempt(3, False, "s3", "s3l", reason="pI unchanged")
    assert engine.iteration_count == 4
    
    # Now can we attempt another Round 2?
    can, reason = engine.can_attempt_round2()
    assert can == False
    assert "3 attempts" in reason
    
    # Can attempt Option B?
    can, reason = engine.can_attempt_option_b()
    assert can == True
    
    # Record Option B
    engine.record_option_b_attempt(
        success=False,
        output_vh=None,
        output_vl=None,
        vh_germline="IGHV3-23*01",
        vl_germline="IGKV1-39*01",
        reason="RMSD too high",
    )
    assert engine.iteration_count == 5
    
    # Now can we attempt another Option B?
    can, reason = engine.can_attempt_option_b()
    assert can == False


def test_rescue_audit_log():
    """Test that audit log is properly formatted."""
    from core.humanization.rescue_engine import RescueEngine, RescueConfig
    
    engine = RescueEngine(SUITE, RescueConfig())
    
    engine.record_round2_attempt(
        attempt_num=1,
        success=False,
        output_vh="AAAA",
        output_vl="BBBB",
        metrics={"pI_fab": 9.2, "cdr_rmsd_vh": 0.8, "angle_delta_deg": 2.1},
        reason="pI > 8.5",
    )
    
    audit = engine.to_audit_log()
    
    assert audit["rescue_enabled"] == True
    assert audit["total_iterations"] == 2  # initial + 1 Round 2
    assert audit["final_status"] in ("PASS", "EXHAUSTED")
    
    assert len(audit["attempts"]) == 1
    assert audit["attempts"][0]["phase"] == "ROUND2"
    assert audit["attempts"][0]["metrics"]["pI"] == 9.2


def test_rescue_final_status():
    """Test final status determination."""
    from core.humanization.rescue_engine import RescueEngine, RescueConfig, RescueResult
    
    cfg = RescueConfig()
    engine = RescueEngine(SUITE, cfg)
    
    # Simulate exhausted scenario
    from core.humanization.rescue_engine import RescuePhase
    
    engine.record_round2_attempt(1, False, None, None, reason="pI high")
    engine.record_round2_attempt(2, False, None, None, reason="pI high")
    engine.record_round2_attempt(3, False, None, None, reason="pI high")
    engine.record_option_b_attempt(
        False, None, None,
        "IGHV3-23*01", "IGKV1-39*01",
        reason="RMSD high"
    )
    
    status, msg = engine.get_final_status()
    assert status == "EXHAUSTED"
    assert "Round 2 attempts: 3/3" in msg
    assert "Total iterations: 5" in msg
    assert "manual framework redesign" in msg


def test_rescue_config_golden_backbones():
    """Verify golden backbones are well-established."""
    from core.humanization.rescue_engine import RescueConfig
    
    cfg = RescueConfig()
    
    # VH backbones
    assert len(cfg.golden_backbones_vh) >= 3
    assert cfg.golden_backbones_vh[0] == "IGHV3-23*01"  # Most common
    
    # VL backbones
    assert len(cfg.golden_backbones_vl) >= 3
    assert cfg.golden_backbones_vl[0] == "IGKV1-39*01"  # Pairs with IGHV3-23
    
    # Verify well-known clinical usage
    # IGHV3-23*01: used in Herceptin, Avastin, etc.
    # IGKV1-39*01: common pairing in 842 DB


if __name__ == "__main__":
    print("Running rescue engine tests...")
    test_rescue_config_limits()
    print("✓ test_rescue_config_limits")
    
    test_rescue_trigger_conditions()
    print("✓ test_rescue_trigger_conditions")
    
    test_rescue_iteration_limits()
    print("✓ test_rescue_iteration_limits")
    
    test_rescue_audit_log()
    print("✓ test_rescue_audit_log")
    
    test_rescue_final_status()
    print("✓ test_rescue_final_status")
    
    test_rescue_config_golden_backbones()
    print("✓ test_rescue_config_golden_backbones")
    
    print("\n✅ All rescue engine tests PASSED")
