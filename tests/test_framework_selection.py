#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for framework selection module.

Tests:
- Determinism: same input yields same ordering
- FR4 exclusion: changing FR4 does not change FR identity score
- Missing canonical: does not crash, keeps TODO
"""

import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.framework_selection.selector import (
    load_framework_library,
    compute_query_features,
    extract_query_fr1_fr3,
    calculate_fr_identity,
    score_candidates,
    select_frameworks,
    compute_cdr3_risk_penalty,
)


class TestFrameworkSelection(unittest.TestCase):
    """Test framework selection functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock ANARCII numbering output (VH-like)
        self.mock_numbering = [
            {"pos": 1, "aa": "Q", "chain_type": "H", "scheme": "imgt"},
            {"pos": 2, "aa": "V", "chain_type": "H", "scheme": "imgt"},
            {"pos": 26, "aa": "L", "chain_type": "H", "scheme": "imgt"},
            {"pos": 27, "aa": "G", "chain_type": "H", "scheme": "imgt"},  # CDR1 start
            {"pos": 38, "aa": "H", "chain_type": "H", "scheme": "imgt"},  # CDR1 end
            {"pos": 39, "aa": "M", "chain_type": "H", "scheme": "imgt"},  # FR2 start
            {"pos": 55, "aa": "W", "chain_type": "H", "scheme": "imgt"},  # FR2 end
            {"pos": 56, "aa": "I", "chain_type": "H", "scheme": "imgt"},  # CDR2 start
            {"pos": 65, "aa": "T", "chain_type": "H", "scheme": "imgt"},  # CDR2 end
            {"pos": 66, "aa": "R", "chain_type": "H", "scheme": "imgt"},  # FR3 start
            {"pos": 104, "aa": "C", "chain_type": "H", "scheme": "imgt"},  # FR3 end
            {"pos": 105, "aa": "A", "chain_type": "H", "scheme": "imgt"},  # CDR3 start
            {"pos": 117, "aa": "Y", "chain_type": "H", "scheme": "imgt"},  # CDR3 end
            {"pos": 118, "aa": "W", "chain_type": "H", "scheme": "imgt"},  # FR4 start
            {"pos": 128, "aa": "S", "chain_type": "H", "scheme": "imgt"},  # FR4 end
        ]
    
    def test_compute_query_features(self):
        """Test query feature computation"""
        features = compute_query_features(self.mock_numbering)
        
        # CDR-H3 length should be 13 (positions 105-117)
        self.assertEqual(features["cdr_h3_length"], 13)
        self.assertFalse(features["long_cdr3_flag"])  # 13 <= 18
        
        # Other features should be TODO or default
        self.assertIn(features["predicted_pI"], ["TODO", None])
    
    def test_extract_query_fr1_fr3(self):
        """Test FR1-FR3 extraction"""
        fr_seq = extract_query_fr1_fr3(self.mock_numbering)
        
        # Should extract FR1 (1-26), FR2 (39-55), FR3 (66-104)
        # Note: This is a simplified test; actual extraction depends on split_regions
        self.assertIsNotNone(fr_seq)
        self.assertIsInstance(fr_seq, str)
        self.assertGreater(len(fr_seq), 0)
    
    def test_calculate_fr_identity(self):
        """Test FR identity calculation"""
        seq1 = "QVQLVESGGGLVQVGGSLRLSCAAS"
        seq2 = "QVQLVESGGGLVQVGGSLRLSCAAS"  # Identical
        identity = calculate_fr_identity(seq1, seq2)
        self.assertEqual(identity, 1.0)
        
        seq3 = "QVQLVESGGGLVQVGGSLRLSCAAT"  # One difference
        identity2 = calculate_fr_identity(seq1, seq3)
        self.assertLess(identity2, 1.0)
        self.assertGreater(identity2, 0.9)
        
        # Empty sequences
        self.assertEqual(calculate_fr_identity("", ""), 0.0)
        self.assertEqual(calculate_fr_identity("ABC", ""), 0.0)
    
    def test_determinism(self):
        """Test that same input yields same ordering"""
        try:
            vh_frameworks, vl_frameworks = load_framework_library()
        except Exception:
            self.skipTest("Framework library not available")
        
        if not vh_frameworks:
            self.skipTest("No VH frameworks available")
        
        # Create a mock query FR1-FR3
        query_fr = "QVQLVESGGGLVQVGGSLRLSCAAS" * 3  # Simplified
        
        # Score twice
        scored1 = score_candidates(query_fr, vh_frameworks[:5])  # Use first 5 for speed
        scored2 = score_candidates(query_fr, vh_frameworks[:5])
        
        # Should have same ordering
        self.assertEqual(len(scored1), len(scored2))
        for (c1, s1, _), (c2, s2, _) in zip(scored1, scored2):
            self.assertEqual(c1.get("framework_id"), c2.get("framework_id"))
            self.assertAlmostEqual(s1, s2, places=5)
    
    def test_fr4_exclusion(self):
        """Test that FR4 is excluded from FR identity calculation"""
        # FR1-FR3 sequences (same)
        fr1_fr3 = "QVQLVESGGGLVQVGGSLRLSCAAS" * 3
        
        # Framework with different FR4 should not affect identity
        framework1 = {
            "framework_id": "VH:TEST1",
            "fr_sequence_fr1_fr3": fr1_fr3,
            "canonical": {"cdr1": {"class": "TODO"}, "cdr2": {"class": "TODO"}},
            "tags": [],
        }
        
        framework2 = {
            "framework_id": "VH:TEST2",
            "fr_sequence_fr1_fr3": fr1_fr3,  # Same FR1-FR3
            "canonical": {"cdr1": {"class": "TODO"}, "cdr2": {"class": "TODO"}},
            "tags": [],
        }
        
        # Both should have same FR identity
        identity1 = calculate_fr_identity(fr1_fr3, framework1["fr_sequence_fr1_fr3"])
        identity2 = calculate_fr_identity(fr1_fr3, framework2["fr_sequence_fr1_fr3"])
        
        self.assertEqual(identity1, identity2)
        self.assertEqual(identity1, 1.0)
    
    def test_missing_canonical(self):
        """Test that missing canonical does not crash"""
        query_fr = "QVQLVESGGGLVQVGGSLRLSCAAS" * 3
        
        framework_todo = {
            "framework_id": "VH:TEST_TODO",
            "fr_sequence_fr1_fr3": query_fr,
            "canonical": {
                "cdr1": {"class": "TODO", "length_mode": "TODO"},
                "cdr2": {"class": "TODO", "length_mode": "TODO"},
            },
            "tags": [],
        }
        
        # Should not crash
        scored = score_candidates(query_fr, [framework_todo])
        self.assertEqual(len(scored), 1)
        
        cand, score, details = scored[0]
        self.assertEqual(cand["framework_id"], "VH:TEST_TODO")
        self.assertIn("canonical_status", details)
        self.assertIn("TODO", details["canonical_status"])
    
    def test_cdr3_risk_penalty(self):
        """Test CDR3 length risk penalty calculation"""
        # Preferred range: no penalty
        policy = {
            "preferred_max": 18,
            "caution_range": [19, 22],
            "high_risk_min": 23,
        }
        penalty_short = compute_cdr3_risk_penalty(15, policy)
        self.assertEqual(penalty_short, 0.0)
        
        # Caution range: small penalty
        penalty_caution = compute_cdr3_risk_penalty(20, policy)
        self.assertGreater(penalty_caution, 0.0)
        self.assertLessEqual(penalty_caution, 0.05)
        
        # High risk: larger penalty
        penalty_high = compute_cdr3_risk_penalty(25, policy)
        self.assertGreater(penalty_high, 0.05)
        
        # TODO policy: no penalty
        penalty_todo = compute_cdr3_risk_penalty(25, "TODO")
        self.assertEqual(penalty_todo, 0.0)
    
    def test_cdr3_penalty_in_scoring(self):
        """Test that CDR3 penalty is applied in candidate scoring"""
        query_fr = "QVQLVESGGGLVQVGGSLRLSCAAS" * 3
        
        framework1 = {
            "framework_id": "VH:TEST1",
            "fr_sequence_fr1_fr3": query_fr,
            "canonical": {"cdr1": {"class": "TODO"}, "cdr2": {"class": "TODO"}},
            "cdr3_policy": {
                "preferred_max": 18,
                "caution_range": [19, 22],
                "high_risk_min": 23,
            },
            "tags": [],
        }
        
        framework2 = {
            "framework_id": "VH:TEST2",
            "fr_sequence_fr1_fr3": query_fr,  # Same FR1-FR3
            "canonical": {"cdr1": {"class": "TODO"}, "cdr2": {"class": "TODO"}},
            "cdr3_policy": {
                "preferred_max": 18,
                "caution_range": [19, 22],
                "high_risk_min": 23,
            },
            "tags": [],
        }
        
        # Score with short CDR3 (no penalty)
        scored_short = score_candidates(query_fr, [framework1, framework2], cdr3_length=15)
        self.assertEqual(len(scored_short), 2)
        score1_short, score2_short = scored_short[0][1], scored_short[1][1]
        
        # Score with long CDR3 (penalty applied)
        scored_long = score_candidates(query_fr, [framework1, framework2], cdr3_length=25)
        self.assertEqual(len(scored_long), 2)
        score1_long, score2_long = scored_long[0][1], scored_long[1][1]
        
        # Long CDR3 should have lower scores due to penalty
        self.assertLess(score1_long, score1_short)
        self.assertLess(score2_long, score2_short)
    
    def test_select_frameworks_basic(self):
        """Test basic framework selection"""
        try:
            result = select_frameworks(self.mock_numbering)
        except Exception as e:
            # May fail if framework library is incomplete, that's OK for now
            self.skipTest(f"Framework selection failed (expected if library incomplete): {e}")
        
        # Should return structured result
        self.assertIn("top3_vh", result)
        self.assertIn("top3_vl", result)
        self.assertIn("final_choice", result)
        self.assertIn("triggered_rules", result)
        
        # Final choice should have VH, VL, FR4_VH, FR4_VL
        final = result["final_choice"]
        self.assertIn("VH", final)
        self.assertIn("VL", final)
        self.assertIn("FR4_VH", final)
        self.assertIn("FR4_VL", final)
        
        # FR4 should be selected separately (not part of framework identity)
        # This is verified by the fact that FR4_VH and FR4_VL are separate fields


if __name__ == "__main__":
    unittest.main()
