#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
v5.2 Core Gates - 

 v5.2 ， fail，、、。

Gate ：
- Gate 1: CDR3 
- Gate 2: FR4  curated IGHJ
- Gate 3: FR4  motif
- Gate 4: IMGT 
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]

#  curated FR4 （）
_CURATED_FR4_LIBRARY_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


@dataclass
class GateResult:
    """Gate """
    passed: bool  #  passed  pass（pass  Python ）
    failed_gate: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


def load_curated_fr4_library(use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
    """
     curated FR4 （）
    
    Args:
        use_cache: （ True）
    
    Returns:
        {ighj_id: {gene, allele, fr4_aa, fr4_motif_4aa, fr4_len, ...}}
    """
    global _CURATED_FR4_LIBRARY_CACHE
    
    if use_cache and _CURATED_FR4_LIBRARY_CACHE is not None:
        return _CURATED_FR4_LIBRARY_CACHE
    
    fr4_json_path = PROJECT_ROOT / "data" / "ighj_curated_fr4.json"
    
    if not fr4_json_path.exists():
        raise FileNotFoundError(
            f"Curated FR4 library not found: {fr4_json_path}\n"
            "Please run: python scripts/generate_ighj_curated_fr4.py"
        )
    
    import json
    with open(fr4_json_path, "r", encoding="utf-8") as f:
        library = json.load(f)
    
    if use_cache:
        _CURATED_FR4_LIBRARY_CACHE = library
    
    return library


def build_imgt_numbering_dict_from_rows(
    numbering_rows: list,
) -> Dict[str, Any]:
    """
     anarcii numbering rows  IMGT numbering dict（ Gate）

    Returns:
        {
          "pos_to_aa": {pos: aa, ...},   # int keys — insertions at same pos overwrite
          "raw_rows":  [...],             # original rows list — used by extract_cdr3_from_imgt
                                          # to preserve IMGT insertion codes for long CDR3
          "has_118":   bool,
        }
    """
    pos_to_aa = {}
    for row in numbering_rows:
        pos = row.get("pos")
        aa = row.get("aa")
        if pos is not None and aa is not None and aa != "-":
            pos_to_aa[pos] = aa

    return {
        "pos_to_aa": pos_to_aa,
        "raw_rows": numbering_rows,
        "has_118": 118 in pos_to_aa,
    }


def extract_cdr3_from_imgt(imgt_numbering: Dict[str, Any]) -> str:
    """
     IMGT  CDR3 （IMGT 105-117）。

    Uses the raw_rows list when available (preferred) so that IMGT insertion codes
    (e.g. 111A, 111B, 112A … for long CDR3) are preserved in the correct order.
    Falls back to the pos_to_aa dict for callers that do not supply raw_rows,
    which may undercount insertions but never raises an error.
    """
    # Preferred path: iterate raw rows to preserve insertion-code residues
    raw_rows = imgt_numbering.get("raw_rows")
    if raw_rows is not None:
        return "".join(
            r["aa"] for r in raw_rows
            if isinstance(r.get("pos"), int) and 105 <= r["pos"] <= 117
            and r.get("aa") and r["aa"] != "-"
        )

    # Fallback: pos_to_aa dict (int keys — insertions at same position are lost,
    # so CDR3 length may be underestimated for long loops).
    pos_to_aa = imgt_numbering.get("pos_to_aa", {})
    cdr3_aa_list = []
    for pos in range(105, 118):
        if pos in pos_to_aa:
            aa = pos_to_aa[pos]
            if aa and aa != "-":
                cdr3_aa_list.append(aa)
    return "".join(cdr3_aa_list)


def extract_fr4_from_imgt(imgt_numbering: Dict[str, Any]) -> str:
    """
     IMGT  FR4 （IMGT 118-128）
    
    Args:
        imgt_numbering: IMGT （ run_anarcii_imgt）
    
    Returns:
        FR4 （11 aa）
    """
    pos_to_aa = imgt_numbering.get("pos_to_aa", {})
    
    fr4_aa_list = []
    for pos in range(118, 129):  # IMGT 118-128
        if pos in pos_to_aa:
            aa = pos_to_aa[pos]
            if aa and aa != "-":
                fr4_aa_list.append(aa)
            else:
                # Gap 
                fr4_aa_list.append("-")
        else:
            # 
            fr4_aa_list.append("-")
    
    return "".join(fr4_aa_list)


def check_gate1_cdr3_immutable(
    query_cdr3: str,
    humanized_cdr3: str,
) -> GateResult:
    """
    Gate 1: CDR3 
    
     query  CDR3  humanized VH  CDR3  100% identical。
    """
    if query_cdr3 != humanized_cdr3:
        # （）
        diff_positions = []
        min_len = min(len(query_cdr3), len(humanized_cdr3))
        for i in range(min_len):
            if query_cdr3[i] != humanized_cdr3[i]:
                diff_positions.append(i)
        if len(query_cdr3) != len(humanized_cdr3):
            diff_positions.append(f"length_mismatch: query={len(query_cdr3)}, humanized={len(humanized_cdr3)}")
        
        return GateResult(
            passed=False,
            failed_gate="FAIL_GATE_CDR3_MODIFIED",
            message=(
                f"CDR3 was modified (v5.2 violation: CDR3 must be 100% identical). "
                f"Query CDR3: '{query_cdr3}' (len={len(query_cdr3)}) vs "
                f"Humanized CDR3: '{humanized_cdr3}' (len={len(humanized_cdr3)}). "
                f"Differences at positions: {diff_positions[:10]}"  # 10
            ),
            details={
                "query_cdr3": query_cdr3,
                "humanized_cdr3": humanized_cdr3,
                "query_len": len(query_cdr3),
                "humanized_len": len(humanized_cdr3),
                "diff_positions": diff_positions,
            }
        )
    
    return GateResult(
        passed=True,
        details={
            "query_cdr3": query_cdr3,
            "humanized_cdr3": humanized_cdr3,
            "cdr3_len": len(query_cdr3),
        }
    )


def check_gate2_fr4_from_curated(
    humanized_fr4: str,
    curated_fr4_library: Dict[str, Dict[str, Any]],
) -> GateResult:
    """
    Gate 2: FR4  curated IGHJ
    
    humanized VH  IMGT 118-128 
     118-128  11 aa  ∈ curated FR4 
    """
    #  FR4 （Gate 3 ，）
    if len(humanized_fr4) != 11:
        return GateResult(
            passed=False,
            failed_gate="FAIL_GATE_FR4_SOURCE",
            message=(
                f"FR4 length mismatch: expected 11 aa, got {len(humanized_fr4)} aa. "
                f"FR4 sequence: '{humanized_fr4}'. "
                f"v5.2 requires FR4 to be exactly 11 aa from curated IGHJ library."
            ),
            details={
                "humanized_fr4": humanized_fr4,
                "fr4_len": len(humanized_fr4),
                "expected_len": 11,
            }
        )
    
    #  curated 
    curated_fr4_set = {
        entry["fr4_aa"] for entry in curated_fr4_library.values()
    }
    
    if humanized_fr4 not in curated_fr4_set:
        # 
        available_fr4_list = sorted(curated_fr4_set)
        available_ighj_ids = sorted(curated_fr4_library.keys())
        
        # （）
        def hamming_distance(s1: str, s2: str) -> int:
            if len(s1) != len(s2):
                return max(len(s1), len(s2))
            return sum(c1 != c2 for c1, c2 in zip(s1, s2))
        
        closest_match = None
        min_distance = float('inf')
        for fr4_candidate in available_fr4_list:
            dist = hamming_distance(humanized_fr4, fr4_candidate)
            if dist < min_distance:
                min_distance = dist
                closest_match = fr4_candidate
        
        closest_info = ""
        if closest_match and min_distance <= 3:
            closest_info = f" Closest match in library: '{closest_match}' (distance={min_distance})"
        
        return GateResult(
            passed=False,
            failed_gate="FAIL_GATE_FR4_SOURCE",
            message=(
                f"FR4 sequence '{humanized_fr4}' not found in curated IGHJ FR4 library.{closest_info} "
                f"v5.2 requires FR4 to be from curated IGHJ1-6 (01) set. "
                f"Available IGHJ IDs: {', '.join(available_ighj_ids)}"
            ),
            details={
                "humanized_fr4": humanized_fr4,
                "curated_fr4_set": available_fr4_list,
                "available_ighj_ids": available_ighj_ids,
                "closest_match": closest_match,
                "closest_distance": min_distance if closest_match else None,
            }
        )
    
    #  IGHJ ID
    matched_ighj_id = None
    for ighj_id, entry in curated_fr4_library.items():
        if entry["fr4_aa"] == humanized_fr4:
            matched_ighj_id = ighj_id
            break
    
    return GateResult(
        passed=True,
        details={
            "humanized_fr4": humanized_fr4,
            "matched_ighj_id": matched_ighj_id,
            "provenance": "curated_functional_set",
        }
    )


def check_gate3_fr4_format(
    humanized_fr4: str,
) -> GateResult:
    """
    Gate 3: FR4  motif
    
    FR4  = 11 aa
    fr4_aa  ^WG.G (WGQG / WGRG / WGxG)
    """
    # 
    if len(humanized_fr4) != 11:
        return GateResult(
            passed=False,
            failed_gate="FAIL_GATE_FR4_FORMAT",
            message=f"FR4 length mismatch: expected 11, got {len(humanized_fr4)}",
            details={
                "humanized_fr4": humanized_fr4,
                "fr4_len": len(humanized_fr4),
            }
        )
    
    #  motif
    if not re.match(r'^WG.G', humanized_fr4):
        return GateResult(
            passed=False,
            failed_gate="FAIL_GATE_FR4_FORMAT",
            message=f"FR4 motif mismatch: expected pattern ^WG.G, got '{humanized_fr4[:4]}'",
            details={
                "humanized_fr4": humanized_fr4,
                "fr4_motif_4aa": humanized_fr4[:4],
                "expected_pattern": "^WG.G",
            }
        )
    
    return GateResult(
        passed=True,
        details={
            "humanized_fr4": humanized_fr4,
            "fr4_len": len(humanized_fr4),
            "fr4_motif_4aa": humanized_fr4[:4],
        }
    )


def check_gate4_imgt_integrity(
    imgt_numbering: Dict[str, Any],
) -> GateResult:
    """
    Gate 4: IMGT 
    
    anarcii(IMGT) 
    IMGT 118-128 
     out_of_domain / gap
    """
    # 
    if not imgt_numbering:
        return GateResult(
            passed=False,
            failed_gate="FAIL_GATE_IMGT_INTEGRITY",
            message="IMGT numbering failed: empty result",
            details={}
        )
    
    pos_to_aa = imgt_numbering.get("pos_to_aa", {})
    
    if not pos_to_aa:
        return GateResult(
            passed=False,
            failed_gate="FAIL_GATE_IMGT_INTEGRITY",
            message="IMGT numbering failed: no position-to-AA mapping",
            details={}
        )
    
    #  IMGT 118-128 
    missing_positions = []
    gap_positions = []
    
    for pos in range(118, 129):  # IMGT 118-128
        if pos not in pos_to_aa:
            missing_positions.append(pos)
        else:
            aa = pos_to_aa[pos]
            if aa == "-" or aa is None:
                gap_positions.append(pos)
    
    if missing_positions or gap_positions:
        return GateResult(
            passed=False,
            failed_gate="FAIL_GATE_IMGT_INTEGRITY",
            message=f"IMGT 118-128 incomplete: missing={missing_positions}, gaps={gap_positions}",
            details={
                "missing_positions": missing_positions,
                "gap_positions": gap_positions,
                "present_positions": [p for p in range(118, 129) if p in pos_to_aa and pos_to_aa[p] not in ("-", None)],
            }
        )
    
    #  out_of_domain （ numbering ）
    # ： anarcii 
    #  gap
    
    return GateResult(
        passed=True,
        details={
            "imgt_118_128_present": True,
            "imgt_118_128_sequence": "".join([pos_to_aa.get(pos, "-") for pos in range(118, 129)]),
        }
    )


def run_v52_core_gates(
    query_seq: str,
    humanized_seq: str,
    query_imgt_numbering: Dict[str, Any],
    humanized_imgt_numbering: Dict[str, Any],
    curated_fr4_library: Optional[Dict[str, Dict[str, Any]]] = None,
) -> GateResult:
    """
     v5.2 Core Gates 
    
    ， Gate 。
    
    Args:
        query_seq:  query 
        humanized_seq: 
        query_imgt_numbering: Query  IMGT 
        humanized_imgt_numbering: Humanized  IMGT 
        curated_fr4_library: Curated FR4 （ None，）
    
    Returns:
        GateResult:  Gate ，passed=True； passed=False 
    
    Raises:
        FileNotFoundError:  curated FR4 
    """
    #  curated FR4 （，）
    if curated_fr4_library is None:
        curated_fr4_library = load_curated_fr4_library(use_cache=True)
    
    #  CDR3
    query_cdr3 = extract_cdr3_from_imgt(query_imgt_numbering)
    humanized_cdr3 = extract_cdr3_from_imgt(humanized_imgt_numbering)
    
    #  FR4
    humanized_fr4 = extract_fr4_from_imgt(humanized_imgt_numbering)
    
    # Gate 1: CDR3 
    gate1_result = check_gate1_cdr3_immutable(query_cdr3, humanized_cdr3)
    if not gate1_result.passed:
        return gate1_result
    
    # Gate 2: FR4  curated IGHJ
    gate2_result = check_gate2_fr4_from_curated(humanized_fr4, curated_fr4_library)
    if not gate2_result.passed:
        return gate2_result
    
    # Gate 3: FR4  motif
    gate3_result = check_gate3_fr4_format(humanized_fr4)
    if not gate3_result.passed:
        return gate3_result
    
    # Gate 4: IMGT 
    gate4_result = check_gate4_imgt_integrity(humanized_imgt_numbering)
    if not gate4_result.passed:
        return gate4_result
    
    #  Gate 
    return GateResult(
        passed=True,
        details={
            "gate1": gate1_result.details,
            "gate2": gate2_result.details,
            "gate3": gate3_result.details,
            "gate4": gate4_result.details,
        }
    )

