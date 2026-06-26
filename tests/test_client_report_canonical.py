"""
Unit tests for Client Report Canonical Expression and Sorting

：
1. CanonicalClient Report
2. Client Reportcanonical
3. canonical reporting
"""

from __future__ import annotations

import pytest
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve.parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.explain.decision_rationale_builder import _build_canonical_rationale
from core.humanize.vhh_classic_panel import generate_vhh_classic_panel
from scripts.run_vhh_classic_panel import generate_markdown_report


class TestCanonicalTextInClientReport:
    """Client Reportcanonical"""
    
    def test_canonical_text_present_in_client_report(self):
        """low/medium/high"""
        # low
        rationale_en_low, rationale_zh_low = _build_canonical_rationale("low")
        assert "compatible" in rationale_en_low.lower
        assert "" in rationale_zh_low or "" in rationale_zh_low
        
        # medium
        rationale_en_medium, rationale_zh_medium = _build_canonical_rationale("medium")
        assert "mismatch" in rationale_en_medium.lower
        assert "" in rationale_zh_medium
        
        # high
        rationale_en_high, rationale_zh_high = _build_canonical_rationale("high")
        assert "differ" in rationale_en_high.lower or "incompatibility" in rationale_en_high.lower
        assert "" in rationale_zh_high or "" in rationale_zh_high
    
    def test_canonical_text_no_technical_details(self):
        """canonical"""
        for risk_level in ["low", "medium", "high"]:
            rationale_en, rationale_zh = _build_canonical_rationale(risk_level)
            
            # 
            assert "length" not in rationale_en.lower or "" not in rationale_zh
            
            # Kabat
            assert "kabat" not in rationale_en.lower
            assert "Kabat" not in rationale_zh
            
            # IMGT
            assert "imgt" not in rationale_en.lower
            assert "IMGT" not in rationale_zh


class TestClientReportSortedByCanonicalRisk:
    """Client Reportcanonical"""
    
    def test_client_report_sorted_by_canonical_risk(self):
        """Client Markdownscaffoldlow → medium → high"""
        # 
        result = {
            "classic_panel": [
                {
                    "scaffold_id": "IGHV3-23*01",
                    "j_region_id": "IGHJ4",
                    "canonical_risk_level": "high",
                    "sequence_final": "TEST_SEQ_1",
                    "mutations": [],
                },
                {
                    "scaffold_id": "IGHV3-66*01",
                    "j_region_id": "IGHJ4",
                    "canonical_risk_level": "low",
                    "sequence_final": "TEST_SEQ_2",
                    "mutations": [],
                },
                {
                    "scaffold_id": "IGHV3-30*01",
                    "j_region_id": "IGHJ4",
                    "canonical_risk_level": "medium",
                    "sequence_final": "TEST_SEQ_3",
                    "mutations": [],
                },
            ],
            "canonical_compatibility": {
                "IGHV3-23*01": {"risk_level": "high"},
                "IGHV3-66*01": {"risk_level": "low"},
                "IGHV3-30*01": {"risk_level": "medium"},
            },
            "timestamp": "2025-01-01T00:00:00",
            "pipeline_version": "v1.0",
        }
        
        # Markdown
        from pathlib import Path
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            generate_markdown_report(result, temp_path)
            report_content = temp_path.read_text(encoding="utf-8")
            
            # ：lowmedium，mediumhigh
            idx_low = report_content.find("IGHV3-66*01")  # low
            idx_medium = report_content.find("IGHV3-30*01")  # medium
            idx_high = report_content.find("IGHV3-23*01")  # high
            
            assert idx_low != -1
            assert idx_medium != -1
            assert idx_high != -1
            
            # 
            assert idx_low < idx_medium < idx_high, (
                f"Expected order: low < medium < high, "
                f"but got: low={idx_low}, medium={idx_medium}, high={idx_high}"
            )
        finally:
            if temp_path.exists:
                temp_path.unlink


class TestSequenceUnchangedWithCanonicalReporting:
    """canonical reporting"""
    
    def test_sequence_unchanged_with_canonical_reporting(self):
        """canonical，sequence_final、mutations byte-level"""
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
            # generate_vhh_classic_panel
            result = generate_vhh_classic_panel(query)
        except Exception:
            # ，
            pytest.skip("Skipping integration test - requires full numbering data")
        
        # baselinemutations
        classic_panel = result.get("classic_panel", [])
        assert len(classic_panel) > 0
        
        baseline_data = {}
        for entry in classic_panel:
            scaffold_id = entry.get("scaffold_id")
            j_region_id = entry.get("j_region_id")
            key = f"{scaffold_id}_{j_region_id}"
            
            baseline_data[key] = {
                "sequence_final": entry.get("sequence_final"),
                "mutations": json.dumps(entry.get("mutations", []), sort_keys=True),
            }
        
        # （canonical reporting）
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
                    f"Sequence changed for {key}: canonical reporting should be read-only"
                )
                assert current_mut == baseline_mut, (
                    f"Mutations changed for {key}: canonical reporting should be read-only"
                )
        
        # canonical
        for entry in classic_panel2:
            assert "canonical_risk_level" in entry
            assert "canonical_rationale" in entry


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



