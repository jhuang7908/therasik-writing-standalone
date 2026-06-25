#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
P0 | VHH_CYS_PREFLIGHT_CHECK (Non-bypassable)

VHH//，：
- Cys（）→ 
- Cys → WARNING（），Cys
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum


class PreflightStatus(str, Enum):
    """"""
    PASS = "pass"
    FAIL = "fail"


class Severity(str, Enum):
    """"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Action(str, Enum):
    """"""
    CONTINUE = "continue"
    ABORT = "abort"


# VHH（IMGT）
VHH_CORE_CYS_PAIR_IMGT = [23, 104]


def detect_cys_positions(
    sequence: str,
    numbering_maps: Dict[str, Any],
) -> Tuple[List[Optional[int]], List[Optional[int]], List[Optional[int]]]:
    """
    Cys，IMGT/Kabat/AHo
    
    Args:
        sequence: 
        numbering_maps: ，residue_index_map, imgt, kabat
    
    Returns:
        (imgt_positions, kabat_positions, aho_positions)
        ，None
    """
    imgt_positions = []
    kabat_positions = []
    aho_positions = []
    
    # Cys（0-based）
    cys_indices = [i for i, aa in enumerate(sequence) if aa == 'C']
    
    # residue_index_map（）
    residue_index_map = numbering_maps.get("residue_index_map", {})
    
    if residue_index_map:
        # 1: residue_index_map（）
        for cys_idx in cys_indices:
            residue_info = residue_index_map.get(cys_idx, {})
            if not residue_info:
                # residue_index_map，imgt/kabat
                imgt_pos = None
                kabat_pos = None
                aho_pos = None
            else:
                # imgt_labelkabat_label
                imgt_label = residue_info.get("imgt_label", "")
                kabat_label = residue_info.get("kabat_label", "")
                
                # IMGT（）
                imgt_pos = None
                if imgt_label:
                    try:
                        # ，"27A" -> 27, "104" -> 104
                        imgt_pos = int(''.join(filter(str.isdigit, str(imgt_label))))
                    except (ValueError, TypeError):
                        pass
                
                # Kabat（）
                kabat_pos = None
                if kabat_label:
                    try:
                        kabat_pos = int(''.join(filter(str.isdigit, str(kabat_label))))
                    except (ValueError, TypeError):
                        pass
                
                # AHo（）
                aho_pos = residue_info.get("aho_pos")
            
            imgt_positions.append(imgt_pos)
            kabat_positions.append(kabat_pos)
            aho_positions.append(aho_pos)
    else:
        # 2: imgtkabat
        imgt_list = numbering_maps.get("imgt", [])
        kabat_list = numbering_maps.get("kabat", [])
        
        # 
        imgt_pos_to_idx = {}
        kabat_pos_to_idx = {}
        
        for idx, item in enumerate(imgt_list):
            if isinstance(item, dict) and item.get("aa") == "C":
                pos_str = str(item.get("pos", ""))
                try:
                    pos_num = int(''.join(filter(str.isdigit, pos_str)))
                    imgt_pos_to_idx[pos_num] = idx
                except (ValueError, TypeError):
                    pass
        
        for idx, item in enumerate(kabat_list):
            if isinstance(item, dict) and item.get("aa") == "C":
                pos_str = str(item.get("pos", ""))
                try:
                    pos_num = int(''.join(filter(str.isdigit, pos_str)))
                    kabat_pos_to_idx[pos_num] = idx
                except (ValueError, TypeError):
                    pass
        
        # Cys，
        for cys_idx in cys_indices:
            # imgt_list
            imgt_pos = None
            if cys_idx < len(imgt_list):
                item = imgt_list[cys_idx]
                if isinstance(item, dict) and item.get("aa") == "C":
                    pos_str = str(item.get("pos", ""))
                    try:
                        imgt_pos = int(''.join(filter(str.isdigit, pos_str)))
                    except (ValueError, TypeError):
                        pass
            
            # kabat_list
            kabat_pos = None
            if cys_idx < len(kabat_list):
                item = kabat_list[cys_idx]
                if isinstance(item, dict) and item.get("aa") == "C":
                    pos_str = str(item.get("pos", ""))
                    try:
                        kabat_pos = int(''.join(filter(str.isdigit, pos_str)))
                    except (ValueError, TypeError):
                        pass
            
            imgt_positions.append(imgt_pos)
            kabat_positions.append(kabat_pos)
            aho_positions.append(None)  # AHo
    
    return imgt_positions, kabat_positions, aho_positions


def check_core_cys_pair(
    imgt_positions: List[Optional[int]],
    kabat_positions: List[Optional[int]],
    aho_positions: List[Optional[int]],
) -> Tuple[bool, Dict[str, Any]]:
    """
    
    
    Args:
        imgt_positions: IMGT
        kabat_positions: Kabat
        aho_positions: AHo
    
    Returns:
        (is_present, core_pair_info)
    """
    # None
    imgt_valid = [p for p in imgt_positions if p is not None]
    kabat_valid = [p for p in kabat_positions if p is not None]
    aho_valid = [p for p in aho_positions if p is not None]
    
    # IMGT（）
    core_pair_present = False
    core_pair_imgt = [None, None]
    core_pair_kabat = [None, None]
    core_pair_aho = [None, None]
    
    # （23104）
    if VHH_CORE_CYS_PAIR_IMGT[0] in imgt_valid and VHH_CORE_CYS_PAIR_IMGT[1] in imgt_valid:
        core_pair_present = True
        core_pair_imgt = VHH_CORE_CYS_PAIR_IMGT.copy()
        
        # KabatAHo
        # numbering_maps，
        # None，
        core_pair_kabat = [None, None]
        core_pair_aho = [None, None]
    
    # IMGT，Kabat（）
    # Kabat23104，
    if not core_pair_present:
        # Kabat（）
        if 23 in kabat_valid and 104 in kabat_valid:
            # ：Kabat，IMGT，""
            core_pair_present = True  # 
            core_pair_kabat = [23, 104]
            # IMGT，None
            core_pair_imgt = [None, None]
    
    core_pair_info = {
        "imgt": core_pair_imgt,
        "kabat": core_pair_kabat,
        "aho": core_pair_aho,
    }
    
    return core_pair_present, core_pair_info


def run_vhh_cys_preflight_check(
    query: Dict[str, Any],
    numbering_maps: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    VHH Cys（P0，）
    
    Args:
        query: query，sequencesegments
        numbering_maps: （）
    
    Returns:
        preflight_checks.vhh_cys_check 
    """
    # 
    sequence = None
    if "sequence" in query:
        sequence = query["sequence"]
    elif "segments" in query:
        segments = query["segments"]
        sequence = "".join([
            segments.get("FR1", ""),
            segments.get("CDR1", ""),
            segments.get("FR2", ""),
            segments.get("CDR2", ""),
            segments.get("FR3", ""),
            segments.get("CDR3", ""),
            segments.get("FR4", ""),
        ])
    elif "v_region" in query:
        sequence = query["v_region"]
    else:
        # ，
        return {
            "status": PreflightStatus.FAIL.value,
            "severity": Severity.ERROR.value,
            "core_pair_required": True,
            "core_pair_present": False,
            "core_pair_positions": {
                "imgt": [None, None],
                "kabat": [None, None],
                "aho": [None, None],
            },
            "detected_cys_positions": {
                "imgt": [],
                "kabat": [],
                "aho": [],
            },
            "extra_cys_positions": {
                "imgt": [],
                "kabat": [],
                "aho": [],
            },
            "action": Action.ABORT.value,
            "policy": {
                "extra_cys_handling": "warn_only",
                "auto_mutate_extra_cys": False,
            },
            "messages": [
                {
                    "code": "VHH_CYS_SEQUENCE_EXTRACTION_FAILED",
                    "text_en": "Failed to extract sequence from query",
                    "text_zh": "query",
                }
            ],
        }
    
    if not sequence:
        return {
            "status": PreflightStatus.FAIL.value,
            "severity": Severity.ERROR.value,
            "core_pair_required": True,
            "core_pair_present": False,
            "core_pair_positions": {
                "imgt": [None, None],
                "kabat": [None, None],
                "aho": [None, None],
            },
            "detected_cys_positions": {
                "imgt": [],
                "kabat": [],
                "aho": [],
            },
            "extra_cys_positions": {
                "imgt": [],
                "kabat": [],
                "aho": [],
            },
            "action": Action.ABORT.value,
            "policy": {
                "extra_cys_handling": "warn_only",
                "auto_mutate_extra_cys": False,
            },
            "messages": [
                {
                    "code": "VHH_CYS_SEQUENCE_EMPTY",
                    "text_en": "Sequence is empty",
                    "text_zh": "",
                }
            ],
        }
    
    # numbering_maps，query
    if numbering_maps is None:
        numbering_maps = query.get("numbering_maps", {})
    
    # Cys
    imgt_positions, kabat_positions, aho_positions = detect_cys_positions(
        sequence, numbering_maps
    )
    
    # numbering_maps，
    if not numbering_maps or not numbering_maps.get("residue_index_map"):
        try:
            from core.numbering.dual_numbering import get_dual_numbering, build_numbering_maps_json
            imgt_rows, kabat_rows, mapping = get_dual_numbering(sequence)
            numbering_maps = build_numbering_maps_json(imgt_rows, kabat_rows, mapping)
            # Cys
            imgt_positions, kabat_positions, aho_positions = detect_cys_positions(
                sequence, numbering_maps
            )
        except Exception:
            # ，
            pass
    
    # 
    core_pair_present, core_pair_info = check_core_cys_pair(
        imgt_positions, kabat_positions, aho_positions
    )
    
    # IMGT，Kabat
    if not core_pair_present and numbering_maps:
        # Kabat（）
        # Kabat23104
        kabat_valid = [p for p in kabat_positions if p is not None]
        if 23 in kabat_valid and 104 in kabat_valid:
            # ，IMGT
            core_pair_present = True
            core_pair_info["kabat"] = [23, 104]
            # kabat_to_imgtIMGT
            kabat_to_imgt = numbering_maps.get("kabat_to_imgt", {})
            imgt_pos_23 = None
            imgt_pos_104 = None
            if "kabat_23" in kabat_to_imgt:
                imgt_label = kabat_to_imgt["kabat_23"].replace("imgt_", "")
                try:
                    imgt_pos_23 = int(''.join(filter(str.isdigit, imgt_label)))
                except (ValueError, TypeError):
                    pass
            if "kabat_104" in kabat_to_imgt:
                imgt_label = kabat_to_imgt["kabat_104"].replace("imgt_", "")
                try:
                    imgt_pos_104 = int(''.join(filter(str.isdigit, imgt_label)))
                except (ValueError, TypeError):
                    pass
            core_pair_info["imgt"] = [imgt_pos_23, imgt_pos_104]
    
    # Cys（）
    extra_cys_imgt = []
    extra_cys_kabat = []
    extra_cys_aho = []
    
    core_pair_imgt_set = set([p for p in core_pair_info["imgt"] if p is not None])
    core_pair_kabat_set = set([p for p in core_pair_info["kabat"] if p is not None])
    
    for i, (imgt_pos, kabat_pos, aho_pos) in enumerate(zip(imgt_positions, kabat_positions, aho_positions)):
        # 
        is_core = False
        if imgt_pos is not None and imgt_pos in core_pair_imgt_set:
            is_core = True
        elif kabat_pos is not None and kabat_pos in core_pair_kabat_set:
            is_core = True
        
        if not is_core:
            if imgt_pos is not None:
                extra_cys_imgt.append(imgt_pos)
            if kabat_pos is not None:
                extra_cys_kabat.append(kabat_pos)
            if aho_pos is not None:
                extra_cys_aho.append(aho_pos)
    
    # 
    status = PreflightStatus.PASS.value
    severity = Severity.INFO.value
    action = Action.CONTINUE.value
    messages = []
    
    if not core_pair_present:
        #  → 
        status = PreflightStatus.FAIL.value
        severity = Severity.ERROR.value
        action = Action.ABORT.value
        messages.append({
            "code": "VHH_CYS_CORE_PAIR_MISSING",
            "text_en": "Core disulfide pair (Cys23-Cys104) is missing. This is required for VHH structure.",
            "text_zh": "（Cys23-Cys104）。VHH。",
        })
    elif len(extra_cys_imgt) > 0 or len(extra_cys_kabat) > 0:
        # Cys → 
        severity = Severity.WARNING.value
        messages.append({
            "code": "VHH_CYS_EXTRA_DETECTED",
            "text_en": f"Extra cysteines detected at positions: IMGT {extra_cys_imgt}, Kabat {extra_cys_kabat}",
            "text_zh": f"，：IMGT {extra_cys_imgt}, Kabat {extra_cys_kabat}",
        })
    else:
        # VHH（2Cys，）
        messages.append({
            "code": "VHH_CYS_OK",
            "text_en": "Core disulfide pair present, no extra cysteines detected.",
            "text_zh": "，。",
        })
    
    # 
    result = {
        "status": status,
        "severity": severity,
        "core_pair_required": True,
        "core_pair_present": core_pair_present,
        "core_pair_positions": core_pair_info,
        "detected_cys_positions": {
            "imgt": [p for p in imgt_positions if p is not None],
            "kabat": [p for p in kabat_positions if p is not None],
            "aho": [p for p in aho_positions if p is not None],
        },
        "extra_cys_positions": {
            "imgt": extra_cys_imgt,
            "kabat": extra_cys_kabat,
            "aho": extra_cys_aho,
        },
        "action": action,
        "policy": {
            "extra_cys_handling": "warn_only",
            "auto_mutate_extra_cys": False,  # ，""
        },
        "messages": messages,
    }
    
    return result

