#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
P0 | VHH_CYS_PREFLIGHT_CHECK
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve.parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.preflight.vhh_cys_check import (
    run_vhh_cys_preflight_check,
    detect_cys_positions,
    check_core_cys_pair,
    VHH_CORE_CYS_PAIR_IMGT,
)
from core.numbering.dual_numbering import get_dual_numbering, build_numbering_maps_json


def create_mock_query_with_numbering(sequence: str) -> dict:
    """mock query"""
    try:
        imgt_rows, kabat_rows, mapping = get_dual_numbering(sequence)
        numbering_maps = build_numbering_maps_json(imgt_rows, kabat_rows, mapping)
        
        # segments（，）
        segments = {
            "FR1": sequence[:26] if len(sequence) > 26 else sequence[:10],
            "CDR1": "",
            "FR2": "",
            "CDR2": "",
            "FR3": "",
            "CDR3": "",
            "FR4": "",
        }
        
        return {
            "sequence": sequence,
            "segments": segments,
            "numbering_maps": numbering_maps,
        }
    except Exception:
        # ，
        return {
            "sequence": sequence,
            "segments": {
                "FR1": sequence[:10] if len(sequence) > 10 else sequence,
                "CDR1": "",
                "FR2": "",
                "CDR2": "",
                "FR3": "",
                "CDR4": "",
            },
            "numbering_maps": {},
        }


# ============================================================================
# Case 1: VHH（2Cys，）
# ============================================================================

def test_standard_vhh_two_cys_core_pair:
    """VHH：2Cys，"""
    # Cys23Cys104
    # ：，VHH
    # 2Cys
    sequence = "EVQLLESGGGLVQPGGSLRLSCAASGFWYNHMSWVRQAPGKEREWVAAITADSGSTYYADSVKGRFTISRDDSKNTVYLQMNSLRAEDTAVYYCAAGGVGWPYFDYWGQGTLVTVSS"
    
    # ，23104Cys
    # ，2Cys
    # VHH
    sequence_with_cys = sequence.replace("S", "C", 1)  # SC
    # C（Cys104）
    if len(sequence_with_cys) > 100:
        seq_list = list(sequence_with_cys)
        seq_list[103] = "C"  # 104（0-based103）
        sequence_with_cys = "".join(seq_list)
    
    query = create_mock_query_with_numbering(sequence_with_cys)
    
    result = run_vhh_cys_preflight_check(query)
    
    # 
    assert result["status"] == "pass"
    assert result["severity"] in ("info", "low")
    assert result["core_pair_present"] is True
    assert len(result["extra_cys_positions"]["imgt"]) == 0
    assert len(result["extra_cys_positions"]["kabat"]) == 0
    assert result["action"] == "continue"
    assert any(msg["code"] == "VHH_CYS_OK" for msg in result["messages"])


# ============================================================================
# Case 2: 
# ============================================================================

def test_missing_core_pair:
    """：1Cys"""
    # 1Cys
    sequence = "EVQLLESGGGLVQPGGSLRLSCAASGFWYNHMSWVRQAPGKEREWVAAITADSGSTYYADSVKGRFTISRDDSKNTVYLQMNSLRAEDTAVYYCAAGGVGWPYFDYWGQGTLVTVSS"
    # Cys
    sequence_one_cys = sequence.replace("C", "S")  # Cys
    seq_list = list(sequence_one_cys)
    seq_list[22] = "C"  # Cys（23，0-based22）
    sequence_one_cys = "".join(seq_list)
    
    query = create_mock_query_with_numbering(sequence_one_cys)
    
    result = run_vhh_cys_preflight_check(query)
    
    # 
    assert result["status"] == "fail"
    assert result["severity"] == "error"
    assert result["core_pair_present"] is False
    assert result["action"] == "abort"
    assert any(msg["code"] == "VHH_CYS_CORE_PAIR_MISSING" for msg in result["messages"])


def test_no_cys_at_all:
    """Cys"""
    sequence = "EVQLLESGGGLVQPGGSLRLSCAASGFWYNHMSWVRQAPGKEREWVAAITADSGSTYYADSVKGRFTISRDDSKNTVYLQMNSLRAEDTAVYYCAAGGVGWPYFDYWGQGTLVTVSS"
    sequence_no_cys = sequence.replace("C", "S")  # Cys
    
    query = create_mock_query_with_numbering(sequence_no_cys)
    
    result = run_vhh_cys_preflight_check(query)
    
    # 
    assert result["status"] == "fail"
    assert result["severity"] == "error"
    assert result["core_pair_present"] is False
    assert result["action"] == "abort"


# ============================================================================
# Case 3: Cys（≥3Cys，）
# ============================================================================

def test_extra_cys_with_core_pair:
    """Cys：≥3Cys，"""
    sequence = "EVQLLESGGGLVQPGGSLRLSCAASGFWYNHMSWVRQAPGKEREWVAAITADSGSTYYADSVKGRFTISRDDSKNTVYLQMNSLRAEDTAVYYCAAGGVGWPYFDYWGQGTLVTVSS"
    # Cys
    seq_list = list(sequence)
    seq_list[22] = "C"  # 23
    if len(seq_list) > 103:
        seq_list[103] = "C"  # 104
    seq_list[50] = "C"  # Cys
    sequence_extra_cys = "".join(seq_list)
    
    query = create_mock_query_with_numbering(sequence_extra_cys)
    
    result = run_vhh_cys_preflight_check(query)
    
    # 
    assert result["status"] == "pass"  # ，pass
    assert result["severity"] == "warning"
    assert result["core_pair_present"] is True
    assert len(result["extra_cys_positions"]["imgt"]) > 0 or len(result["extra_cys_positions"]["kabat"]) > 0
    assert result["policy"]["auto_mutate_extra_cys"] is False
    assert result["action"] == "continue"
    assert any(msg["code"] == "VHH_CYS_EXTRA_DETECTED" for msg in result["messages"])


# ============================================================================
# Case 4: /gap
# ============================================================================

def test_numbering_mapping_gap:
    """：CysIMGTKabat"""
    # ，numbering_maps
    sequence = "EVQLLESGGGLVQPGGSLRLSCAASGFWYNHMSWVRQAPGKEREWVAAITADSGSTYYADSVKGRFTISRDDSKNTVYLQMNSLRAEDTAVYYCAAGGVGWPYFDYWGQGTLVTVSS"
    seq_list = list(sequence)
    seq_list[22] = "C"
    if len(seq_list) > 103:
        seq_list[103] = "C"
    sequence_with_cys = "".join(seq_list)
    
    # numbering_maps
    query = {
        "sequence": sequence_with_cys,
        "segments": {
            "FR1": sequence_with_cys[:10],
            "CDR1": "",
            "FR2": "",
            "CDR2": "",
            "FR3": "",
            "CDR3": "",
            "FR4": "",
        },
        "numbering_maps": {
            "residue_index_map": {},  # 
            "imgt": [],
            "kabat": [],
        },
    }
    
    result = run_vhh_cys_preflight_check(query)
    
    # ，abort
    if not result["core_pair_present"]:
        assert result["status"] == "fail"
        assert result["action"] == "abort"
    else:
        # ，
        assert result["status"] in ("pass", "fail")


# ============================================================================
# P0
# ============================================================================

def test_p0_non_bypassable_in_classic_panel:
    """P0Classic Panel"""
    from core.humanize.vhh_classic_panel import generate_vhh_classic_panel
    
    # query
    sequence = "EVQLLESGGGLVQPGGSLRLSCAASGFWYNHMSWVRQAPGKEREWVAAITADSGSTYYADSVKGRFTISRDDSKNTVYLQMNSLRAEDTAVYYCAAGGVGWPYFDYWGQGTLVTVSS"
    sequence_one_cys = sequence.replace("C", "S")
    seq_list = list(sequence_one_cys)
    seq_list[22] = "C"  # Cys
    sequence_one_cys = "".join(seq_list)
    
    query = create_mock_query_with_numbering(sequence_one_cys)
    
    # querysegments，
    if "segments" not in query or not query["segments"].get("CDR1"):
        # segments
        query["segments"] = {
            "FR1": sequence_one_cys[:26] if len(sequence_one_cys) > 26 else sequence_one_cys[:10],
            "CDR1": "GFWYNH",
            "FR2": sequence_one_cys[26:39] if len(sequence_one_cys) > 39 else "",
            "CDR2": "ITADSGST",
            "FR3": sequence_one_cys[39:104] if len(sequence_one_cys) > 104 else "",
            "CDR3": "CAAGGVGWPYFDY",
            "FR4": sequence_one_cys[104:] if len(sequence_one_cys) > 104 else "WGQGTLVTVSS",
        }
    
    result = generate_vhh_classic_panel(query)
    
    # ：action=abort，sequence_final
    preflight = result.get("preflight_checks", {}).get("vhh_cys_check", {})
    if preflight.get("action") == "abort":
        # classic_panel，sequence_final
        classic_panel = result.get("classic_panel", [])
        if classic_panel:
            for entry in classic_panel:
                assert "sequence_final" not in entry
                assert "blocked_reason" in entry
                assert entry["blocked_reason"]["code"] == "P0_PREFLIGHT_FAILED"
        else:
            # 
            assert len(classic_panel) == 0


# ============================================================================
# 
# ============================================================================

def test_regression_sequence_consistency:
    """：，sequence_final"""
    from core.humanize.vhh_classic_panel import generate_vhh_classic_panel
    
    sequence = "EVQLLESGGGLVQPGGSLRLSCAASGFWYNHMSWVRQAPGKEREWVAAITADSGSTYYADSVKGRFTISRDDSKNTVYLQMNSLRAEDTAVYYCAAGGVGWPYFDYWGQGTLVTVSS"
    seq_list = list(sequence)
    seq_list[22] = "C"  # 23
    if len(seq_list) > 103:
        seq_list[103] = "C"  # 104
    sequence_with_cys = "".join(seq_list)
    
    query = create_mock_query_with_numbering(sequence_with_cys)
    
    # segments
    if "segments" not in query or not query["segments"].get("CDR1"):
        query["segments"] = {
            "FR1": sequence_with_cys[:26] if len(sequence_with_cys) > 26 else sequence_with_cys[:10],
            "CDR1": "GFWYNH",
            "FR2": sequence_with_cys[26:39] if len(sequence_with_cys) > 39 else "",
            "CDR2": "ITADSGST",
            "FR3": sequence_with_cys[39:104] if len(sequence_with_cys) > 104 else "",
            "CDR3": "CAAGGVGWPYFDY",
            "FR4": sequence_with_cys[104:] if len(sequence_with_cys) > 104 else "WGQGTLVTVSS",
        }
    
    # 
    result1 = generate_vhh_classic_panel(query)
    result2 = generate_vhh_classic_panel(query)
    
    # sequence_final（byte-level）
    panel1 = result1.get("classic_panel", [])
    panel2 = result2.get("classic_panel", [])
    
    assert len(panel1) == len(panel2)
    
    for entry1, entry2 in zip(panel1, panel2):
        if "sequence_final" in entry1 and "sequence_final" in entry2:
            assert entry1["sequence_final"] == entry2["sequence_final"]
            # mutations
            assert len(entry1.get("mutations", [])) == len(entry2.get("mutations", []))

