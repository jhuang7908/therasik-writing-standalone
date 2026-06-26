#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sequence Cleaner - 

""（、linker、、、、）
。
"""

import sys
import re
import hashlib
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from collections import Counter

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.trim_variable_domain import trim_variable_domain
from core.numbering.anarcii_adapter import get_engine_info


# 
STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")
ALLOWED_AA = STANDARD_AA | {"X"}  # X


def normalize_input_sequence(raw_input: str) -> Tuple[str, Dict[str, Any]]:
    """
    （Normalization）
    
    ：，；X  x_count。
    
    Args:
        raw_input: （FASTA、、）
    
    Returns:
        (cleaned_sequence, cleaning_log)
        
        cleaned_sequence: 
        cleaning_log: Dict
    """
    cleaning_log = {
        "original_length": len(raw_input),
        "removed_chars": [],
        "removed_count": {},
        "x_count": 0,
        "invalid_chars": [],
        "invalid_count": 0,
        "has_fasta_header": False,
        "fasta_header": None
    }
    
    # 1. FASTA
    lines = [line.strip for line in raw_input.splitlines if line.strip]
    if not lines:
        raise ValueError("Empty input")
    
    seq_lines = []
    for line in lines:
        if line.startswith('>'):
            cleaning_log["has_fasta_header"] = True
            cleaning_log["fasta_header"] = line[1:].strip
        else:
            seq_lines.append(line)
    
    # 2. 
    raw_sequence = ''.join(seq_lines)
    
    # 3. 
    raw_sequence = raw_sequence.upper
    
    # 4. ：、、、、、X
    removed_whitespace = len(raw_sequence) - len(raw_sequence.replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', ''))
    removed_stops = raw_sequence.count('*')
    
    #  X 
    x_count = raw_sequence.count('X')
    invalid_chars = []
    for char in raw_sequence:
        if char not in ALLOWED_AA and char not in [' ', '\n', '\r', '\t', '*']:
            invalid_chars.append(char)
    
    # 5. ：、、
    if removed_whitespace > 0:
        raw_sequence = raw_sequence.replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '')
        cleaning_log["removed_chars"].append("whitespace")
        cleaning_log["removed_count"]["whitespace"] = removed_whitespace
    
    # 6. 
    if removed_stops > 0:
        raw_sequence = raw_sequence.replace('*', '')
        cleaning_log["removed_chars"].append("stop_codon")
        cleaning_log["removed_count"]["stop_codon"] = removed_stops
    
    # 7. ：AAX，
    cleaned_chars = []
    invalid_chars_filtered = []
    
    for char in raw_sequence:
        if char in STANDARD_AA:
            cleaned_chars.append(char)
        elif char == 'X':
            cleaned_chars.append(char)  # X  x_count
        else:
            invalid_chars_filtered.append(char)
    
    cleaned_sequence = ''.join(cleaned_chars)
    
    # 
    cleaning_log["x_count"] = x_count
    cleaning_log["invalid_chars"] = list(set(invalid_chars_filtered))
    cleaning_log["invalid_count"] = len(invalid_chars_filtered)
    
    if invalid_chars_filtered:
        invalid_counter = Counter(invalid_chars_filtered)
        cleaning_log["removed_chars"].append("invalid_chars")
        cleaning_log["removed_count"]["invalid_chars"] = dict(invalid_counter)
    
    cleaning_log["cleaned_length"] = len(cleaned_sequence)
    cleaning_log["removed_total"] = cleaning_log["original_length"] - cleaning_log["cleaned_length"]
    
    return cleaned_sequence, cleaning_log


def perform_length_screening(cleaned_sequence: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    
    
    Returns:
        (should_continue, stop_reason, warn_reason)
    """
    length = len(cleaned_sequence)
    
    # STOP
    if length < 60:
        return False, "too_short", None
    
    # WARN
    if length > 800:
        return True, None, "too_long_suspicious_fusion"
    
    return True, None, None


def detect_multiple_vdomains(cleaned_sequence: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    V（scFv、tandem VHH、）
    
    ：V
    ：V，，V
    
    Args:
        cleaned_sequence: 
    
    Returns:
        (vdomain_list, warn_reasons)
        
        vdomain_list: V，
        warn_reasons: WARN
    """
    vdomain_list = []
    warn_reasons = []
    
    # V
    try:
        trimmed_seq1, vdomain1 = trim_variable_domain(cleaned_sequence)
        if vdomain1.get("detected", False):
            vdomain1["variable_domain_sequence"] = trimmed_seq1
            vdomain1["score"] = 1.0  # 
            vdomain_list.append(vdomain1)
            
            # V
            v_end1 = vdomain1.get("v_end", 0)
            remaining_seq = cleaned_sequence[v_end1:]
            
            # （>100aa），V
            if len(remaining_seq) > 100:
                try:
                    trimmed_seq2, vdomain2 = trim_variable_domain(remaining_seq)
                    if vdomain2.get("detected", False) and vdomain2.get("variable_domain_length", 0) >= 85:
                        # V
                        vdomain2["v_start"] = v_end1 + vdomain2.get("v_start", 0)
                        vdomain2["v_end"] = v_end1 + vdomain2.get("v_end", 0)
                        vdomain2["variable_domain_sequence"] = trimmed_seq2
                        vdomain2["score"] = 0.8  # V
                        vdomain_list.append(vdomain2)
                        warn_reasons.append("WARN_MULTI_DOMAIN")
                except Exception:
                    # V，
                    pass
    except Exception:
        pass
    
    return vdomain_list, warn_reasons


def detect_chain_type_and_vdomain(cleaned_sequence: str) -> Tuple[Dict[str, Any], Optional[str], List[str], List[Dict[str, Any]]]:
    """
    V（V）
    
    Args:
        cleaned_sequence: 
    
    Returns:
        (variable_domain_metadata, stop_reason, warn_reasons, extra_domains)
        
        variable_domain_metadata: V（score）
        stop_reason: STOP
        warn_reasons: WARN
        extra_domains: V
    """
    warn_reasons = []
    extra_domains = []
    
    # V
    vdomain_list, multi_warns = detect_multiple_vdomains(cleaned_sequence)
    warn_reasons.extend(multi_warns)
    
    if not vdomain_list:
        return {
            "detected": False
        }, "vdomain_not_detected", [], []
    
    # scoreV
    vdomain_list.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    variable_domain_metadata = vdomain_list[0]
    
    # extra_domains
    if len(vdomain_list) > 1:
        for vd in vdomain_list[1:]:
            extra_domains.append({
                "v_start": vd.get("v_start", 0),
                "v_end": vd.get("v_end", 0),
                "length": vd.get("variable_domain_length", 0),
                "chain_type": vd.get("chain_type"),  # None，
                "score": vd.get("score", 0.0),
                "sequence": vd.get("variable_domain_sequence", "")[:50] + "..." if len(vd.get("variable_domain_sequence", "")) > 50 else vd.get("variable_domain_sequence", ""),
                "detection_method": vd.get("detection_method", "anarcii_auto_trim")
            })
    
    v_length = variable_domain_metadata.get("variable_domain_length", 0)
    v_start = variable_domain_metadata.get("v_start", 0)
    v_end = variable_domain_metadata.get("v_end", 0)
    
    # V
    if v_length < 85:
        return variable_domain_metadata, "vdomain_too_short", warn_reasons, extra_domains
    
    if v_length > 150:
        return variable_domain_metadata, "vdomain_too_long", warn_reasons, extra_domains
    
    # WARN
    if v_start > 0:
        warn_reasons.append(f"upstream_residue_detected_{v_start}aa")
    
    if variable_domain_metadata.get("trimmed_constant_region", False):
        tail_length = len(cleaned_sequence) - v_end
        if tail_length > 0:
            warn_reasons.append(f"downstream_residue_detected_{tail_length}aa")
    
    return variable_domain_metadata, None, warn_reasons, extra_domains


def check_x_proportion(variable_domain_sequence: str) -> Tuple[bool, Optional[str]]:
    """
    VX
    
    Returns:
        (should_continue, stop_reason)
    """
    if not variable_domain_sequence:
        return False, "vdomain_sequence_empty"
    
    x_count = variable_domain_sequence.count('X')
    x_proportion = x_count / len(variable_domain_sequence) if len(variable_domain_sequence) > 0 else 0
    
    if x_proportion > 0.05:  # 5%
        return False, f"x_proportion_too_high_{x_proportion:.2%}"
    
    return True, None


def validate_variable_domain_consistency(
    variable_domain_metadata: Dict[str, Any],
    cleaned_sequence: str
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    V
    
    Returns:
        (is_valid, stop_reason, diagnostic_info)
    """
    v_length = variable_domain_metadata.get("v_length")
    variable_domain_length = variable_domain_metadata.get("variable_domain_length")
    v_start = variable_domain_metadata.get("v_start", 0)
    v_end = variable_domain_metadata.get("v_end", 0)
    v_seq = variable_domain_metadata.get("variable_domain_sequence", "")
    
    diagnostic_info = {
        "v_length": v_length,
        "variable_domain_length": variable_domain_length,
        "v_start": v_start,
        "v_end": v_end,
        "v_seq_length": len(v_seq),
        "calculated_length": v_end - v_start if v_end > v_start else 0
    }
    
    # 
    issues = []
    
    if v_length != variable_domain_length:
        issues.append(f"v_length ({v_length}) != variable_domain_length ({variable_domain_length})")
    
    if v_end - v_start != v_length:
        issues.append(f"v_end - v_start ({v_end - v_start}) != v_length ({v_length})")
    
    if len(v_seq) != v_length:
        issues.append(f"len(variable_domain_sequence) ({len(v_seq)}) != v_length ({v_length})")
    
    if issues:
        stop_reason = f"STOP_INCONSISTENT_BOUNDARIES: {'; '.join(issues)}"
        diagnostic_info["issues"] = issues
        return False, stop_reason, diagnostic_info
    
    return True, None, diagnostic_info


def enhance_cleaning_log_with_residues(
    cleaning_log: Dict[str, Any],
    cleaned_sequence: str,
    v_start: int,
    v_end: int
) -> None:
    """
    ：/
    
    Args:
        cleaning_log: 
        cleaned_sequence: 
        v_start: V
        v_end: V
    """
    original_length = len(cleaned_sequence)
    
    # 
    if v_start > 0:
        cleaning_log["upstream_length"] = v_start
        upstream_seq = cleaned_sequence[:v_start]
        cleaning_log["upstream_tail_15"] = upstream_seq[-15:] if len(upstream_seq) >= 15 else upstream_seq
    else:
        cleaning_log["upstream_length"] = 0
        cleaning_log["upstream_tail_15"] = None
    
    # 
    if v_end < original_length:
        downstream_length = original_length - v_end
        cleaning_log["downstream_length"] = downstream_length
        downstream_seq = cleaned_sequence[v_end:]
        cleaning_log["downstream_head_15"] = downstream_seq[:15] if len(downstream_seq) >= 15 else downstream_seq
    else:
        cleaning_log["downstream_length"] = 0
        cleaning_log["downstream_head_15"] = None


def generate_qa_flags(
    variable_domain_metadata: Dict[str, Any],
    dual_map_status: str,
    cleaning_log: Dict[str, Any],
    chain_type: Optional[str] = None,
    extra_domains: Optional[List[Dict[str, Any]]] = None
) -> Tuple[List[str], Optional[str], List[str]]:
    """
    QASTOP/WARN
    
    Args:
        variable_domain_metadata: V
        dual_map_status: dual_map（"full", "partial", "conflict", "failed"）
        cleaning_log: 
        chain_type: （"H", "K", "L"）
        extra_domains: V
    
    Returns:
        (qa_flags, stop_reason, warn_reasons)
        
        qa_flags: QA
        stop_reason: STOP
        warn_reasons: WARN
    """
    qa_flags = []
    stop_reasons = []
    warn_reasons = []
    
    # V
    if not variable_domain_metadata.get("detected", False):
        stop_reasons.append("vdomain_not_detected")
        qa_flags.append("REJECT")
        return qa_flags, "; ".join(stop_reasons), []
    
    # V
    v_length = variable_domain_metadata.get("variable_domain_length", 0)
    
    if chain_type in ["H", "VHH"]:
        if v_length < 90 or v_length > 150:
            stop_reasons.append(f"vh_length_out_of_range_{v_length}")
            qa_flags.append("REJECT")
    elif chain_type in ["K", "L"]:
        if v_length < 85 or v_length > 140:
            stop_reasons.append(f"vl_length_out_of_range_{v_length}")
            qa_flags.append("REJECT")
    else:
        # ，
        if v_length < 85 or v_length > 150:
            stop_reasons.append(f"vdomain_length_out_of_range_{v_length}")
            qa_flags.append("REJECT")
    
    # X
    v_seq = variable_domain_metadata.get("variable_domain_sequence", "")
    if v_seq:
        x_prop = v_seq.count('X') / len(v_seq) if len(v_seq) > 0 else 0
        if x_prop > 0.05:
            stop_reasons.append(f"x_proportion_too_high_{x_prop:.2%}")
            qa_flags.append("REJECT")
    
    # V
    if extra_domains and len(extra_domains) > 0:
        warn_reasons.append("WARN_MULTI_DOMAIN")
        qa_flags.append("WARN_MULTI_DOMAIN")
    
    # STOP，
    if stop_reasons:
        return qa_flags, "; ".join(stop_reasons), []
    
    # WARN
    if dual_map_status == "conflict":
        warn_reasons.append("dual_map_conflict")
        qa_flags.append("WARN_CONFLICT")
    
    if cleaning_log.get("invalid_count", 0) > 0:
        warn_reasons.append(f"invalid_chars_removed_{cleaning_log['invalid_count']}")
        qa_flags.append("WARN_INVALID_CHARS")
    
    if variable_domain_metadata.get("v_start", 0) > 10:
        warn_reasons.append(f"large_upstream_residue_{variable_domain_metadata['v_start']}aa")
        qa_flags.append("WARN_UPSTREAM")
    
    if variable_domain_metadata.get("trimmed_constant_region", False):
        tail_length = cleaning_log.get("cleaned_length", 0) - variable_domain_metadata.get("v_end", 0)
        if tail_length > 50:
            warn_reasons.append(f"large_downstream_residue_{tail_length}aa")
            qa_flags.append("WARN_DOWNSTREAM")
    
    # 
    if not qa_flags:
        qa_flags.append("CLEAN")
    elif "REJECT" not in qa_flags:
        if any("WARN" in flag for flag in qa_flags):
            qa_flags.append("USABLE_WITH_WARNINGS")
        else:
            qa_flags.append("CLEAN")
    
    return qa_flags, None, warn_reasons


def clean_sequence_comprehensive(
    raw_input: str,
    dual_map_status: str = "unknown",
    chain_type: Optional[str] = None,
    variable_domain_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    
    
    Args:
        raw_input: 
        dual_map_status: dual_map
        chain_type: 
    
    Returns:
        ，
    """
    result = {
        "raw_input_hash": hashlib.sha256(raw_input.encode).hexdigest,
        "cleaning_log": {},
        "cleaned_input_sequence": "",
        "variable_domain": {},
        "variable_domain_sequence": "",
        "extra_domains": [],  # V
        "qa_flags": [],
        "stop_reason": None,
        "warn_reason": None,  # 
        "warn_reasons": [],  # WARN
        "tool_versions": {}
    }
    
    # 1. 
    try:
        cleaned_sequence, cleaning_log = normalize_input_sequence(raw_input)
        result["cleaned_input_sequence"] = cleaned_sequence
        result["cleaning_log"] = cleaning_log
    except Exception as e:
        result["stop_reason"] = f"normalization_failed: {str(e)}"
        result["qa_flags"] = ["REJECT"]
        return result
    
    # 2. 
    should_continue, stop_reason, warn_reason = perform_length_screening(cleaned_sequence)
    if not should_continue:
        result["stop_reason"] = stop_reason
        result["qa_flags"] = ["REJECT"]
        return result
    
    if warn_reason:
        result["warn_reason"] = warn_reason
    
    # 3. V（，）
    extra_domains = []
    if variable_domain_metadata is None:
        variable_domain_metadata, stop_reason, vdomain_warns, extra_domains = detect_chain_type_and_vdomain(cleaned_sequence)
        
        if stop_reason:
            result["stop_reason"] = stop_reason
            result["qa_flags"] = ["REJECT"]
            return result
        
        # VWARN
        result["warn_reasons"].extend(vdomain_warns)
    else:
        # V，variable_domain_sequence
        if "variable_domain_sequence" not in variable_domain_metadata:
            v_start = variable_domain_metadata.get("v_start", 0)
            v_end = variable_domain_metadata.get("v_end", len(cleaned_sequence))
            variable_domain_metadata["variable_domain_sequence"] = cleaned_sequence[v_start:v_end]
    
    result["variable_domain"] = variable_domain_metadata
    result["extra_domains"] = extra_domains
    
    # 4. V
    v_seq = variable_domain_metadata.get("variable_domain_sequence", "")
    result["variable_domain_sequence"] = v_seq
    
    # 5. ：/
    v_start = variable_domain_metadata.get("v_start", 0)
    v_end = variable_domain_metadata.get("v_end", len(cleaned_sequence))
    enhance_cleaning_log_with_residues(cleaning_log, cleaned_sequence, v_start, v_end)
    
    # 6. 
    is_valid, consistency_stop_reason, diagnostic_info = validate_variable_domain_consistency(
        variable_domain_metadata, cleaned_sequence
    )
    
    if not is_valid:
        result["stop_reason"] = consistency_stop_reason
        result["qa_flags"] = ["REJECT"]
        cleaning_log["boundary_consistency_check"] = diagnostic_info
        return result
    
    # 7. X
    if v_seq:
        should_continue, stop_reason = check_x_proportion(v_seq)
        if not should_continue:
            result["stop_reason"] = stop_reason
            result["qa_flags"] = ["REJECT"]
            return result
    
    # 8. QA
    qa_flags, stop_reason, warn_reasons = generate_qa_flags(
        variable_domain_metadata,
        dual_map_status,
        cleaning_log,
        chain_type,
        extra_domains
    )
    
    result["qa_flags"] = qa_flags
    if stop_reason:
        result["stop_reason"] = stop_reason
    
    # WARN
    result["warn_reasons"].extend(warn_reasons)
    
    # ：warn_reason
    if result["warn_reasons"]:
        result["warn_reason"] = "; ".join(result["warn_reasons"])
    else:
        result["warn_reason"] = None
    
    # 7. 
    engine_info = get_engine_info
    result["tool_versions"] = {
        "anarcii": engine_info.get("version", "unknown"),
        "schemes": engine_info.get("schemes", [])
    }
    
    return result


if __name__ == "__main__":
    # 
    test_seq = ">test_sequence\nQGQLVQSGAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSSASTKGPSVFPLAPCSRSTSESTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTKTYTCNVDHKPSNTKVDKRV"
    
    result = clean_sequence_comprehensive(test_seq, dual_map_status="conflict", chain_type="H")
    
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))








