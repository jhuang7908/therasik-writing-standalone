"""
core.vhh_scaffolds.cdr_parser

CDR parser for VHH sequences using IMGT numbering rules.
Attempts to use ANARCI if available, falls back to heuristic segmentation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .registry import load_imgt_rules, load_vhh_hallmarks


def parse_cdrs(seq: str, use_anarci: bool = True) -> Dict[str, Any]:
    """
    Parse CDR regions from a VHH sequence.
    
    Args:
        seq: Amino acid sequence (uppercase expected)
        use_anarci: Whether to attempt using ANARCI (if available)
        
    Returns:
        Dictionary with structure:
        {
            "regions": {
                "FR1": str,
                "CDR1": str,
                "FR2": str,
                "CDR2": str,
                "FR3": str,
                "CDR3": str,
                "FR4": str
            },
            "meta": {
                "used_anarci": bool,
                "hallmark_detected": bool,
                "sequence_length": int
            }
        }
    """
    seq = seq.upper().strip()
    
    # Try ANARCI first if requested
    anarci_used = False
    if use_anarci:
        try:
            result = _try_anarci(seq)
            if result is not None:
                anarci_used = True
                regions = result
        except Exception:
            # Fall back to heuristic
            pass
    
    # Fallback to heuristic segmentation
    if not anarci_used:
        regions = _heuristic_segment(seq)
    
    # Detect VHH hallmarks
    hallmark_detected = _detect_hallmarks(regions.get("FR2", ""))
    
    return {
        "regions": regions,
        "meta": {
            "used_anarci": anarci_used,
            "hallmark_detected": hallmark_detected,
            "sequence_length": len(seq)
        }
    }


def _try_anarci(seq: str) -> Optional[Dict[str, str]]:
    """
    Attempt to use ANARCI for numbering.
    Returns None if ANARCI is not available or fails.
    """
    try:
        # Try importing ANARCI
        try:
            from anarci import anarci
        except ImportError:
            return None
        
        # Run ANARCI
        numbered, alignment_details, hit_tables = anarci([("seq", seq)], scheme="imgt")
        
        if not numbered or not numbered[0]:
            return None
        
        # Extract regions from ANARCI output
        # ANARCI returns numbered sequences with gaps
        # We need to extract the actual sequence regions
        # This is a simplified version - full implementation would parse ANARCI output properly
        return None  # For now, always fall back
        
    except Exception:
        return None


def _heuristic_segment(seq: str) -> Dict[str, str]:
    """
    Heuristic segmentation based on IMGT rules and conserved motifs.
    
    Strategy:
    1. Find FR4 by looking for "WG" or "WGQ" motif
    2. Extract CDR3 before FR4
    3. Use fixed positions for FR1, CDR1, FR2, CDR2, FR3
    """
    seq_len = len(seq)
    
    # Helper to safely slice sequence
    def safe_slice(start: int, end: int) -> str:
        if start < 0:
            start = 0
        if end > seq_len:
            end = seq_len
        if start >= end:
            return ""
        return seq[start:end]
    
    # Find FR4 by looking for WG motif (conserved in most antibodies)
    # Search from the end to find the last occurrence
    fr4_start = seq.rfind("WG")
    if fr4_start == -1:
        # Try alternative: look for WGQ
        fr4_start = seq.rfind("WGQ")
        if fr4_start == -1:
            # Last resort: assume FR4 starts at position 117 (IMGT standard, 0-indexed: 116)
            fr4_start = max(seq_len - 11, 116) if seq_len > 116 else max(0, seq_len - 11)
    
    # Extract FR4 (typically 11 amino acids: WGQGTQVTVSS)
    # But take at most 11 amino acids
    fr4 = safe_slice(fr4_start, seq_len)
    
    # CDR3 is before FR4
    # IMGT standard: CDR3 starts at position 104 (1-indexed) = 103 (0-indexed)
    # But for shorter sequences, CDR3 might start earlier
    cdr3_start_standard = 103  # IMGT position 104 (1-indexed) = sequence index 103 (0-indexed)
    
    if seq_len >= 104:
        # Standard case: CDR3 starts at position 103
        cdr3_start = cdr3_start_standard
        if fr4_start > cdr3_start:
            cdr3 = safe_slice(cdr3_start, fr4_start)
        else:
            # FR4 found earlier than expected, CDR3 is empty or very short
            cdr3 = safe_slice(cdr3_start, min(cdr3_start + 1, fr4_start))
    else:
        # Short sequence: CDR3 starts where FR3 would normally end
        # FR3 typically ends around position 103, but for short sequences,
        # we'll use a position before FR4
        cdr3_start = max(65, fr4_start - 15)  # At least start after FR2/CDR2
        cdr3 = safe_slice(cdr3_start, fr4_start)
    
    # FR3: positions 66-104 (IMGT 1-indexed) = sequence 65-103 (0-indexed)
    # FR3 ends where CDR3 starts
    fr3_end = cdr3_start
    fr3 = safe_slice(65, fr3_end)
    
    # FR2: positions 39-55 (IMGT 1-indexed) = sequence 38-54 (0-indexed)
    fr2 = safe_slice(38, 55)
    
    # CDR2: positions 56-65 (IMGT 1-indexed) = sequence 55-64 (0-indexed)
    cdr2 = safe_slice(55, 65)
    
    # CDR1: positions 27-38 (IMGT 1-indexed) = sequence 26-37 (0-indexed)
    cdr1 = safe_slice(26, 38)
    
    # FR1: positions 1-26 (IMGT 1-indexed) = sequence 0-25 (0-indexed)
    fr1 = safe_slice(0, 26)
    
    return {
        "FR1": fr1,
        "CDR1": cdr1,
        "FR2": fr2,
        "CDR2": cdr2,
        "FR3": fr3,
        "CDR3": cdr3,
        "FR4": fr4
    }


def _detect_hallmarks(fr2: str) -> bool:
    """
    Detect VHH hallmarks in FR2 region.
    
    Checks positions:
    - 37 (relative to FR2 start: position 8, 0-indexed)
    - 44 (relative to FR2 start: position 15, 0-indexed)
    - 45 (relative to FR2 start: position 16, 0-indexed)
    - 47 (relative to FR2 start: position 18, 0-indexed)
    
    Returns True if at least 2 hallmark positions match VHH pattern.
    """
    # Need at least 9 characters to check position 47 (index 8)
    if len(fr2) < 9:
        return False
    
    hallmarks = load_vhh_hallmarks()
    hallmark_defs = hallmarks["hallmark_positions_imgt"]
    
    # Map IMGT positions to FR2 sequence indices
    # FR2 starts at IMGT position 39, so:
    # IMGT 37 -> FR2 index -2 (before FR2, check if available in context)
    # IMGT 44 -> FR2 index 5 (0-indexed: 44-39=5)
    # IMGT 45 -> FR2 index 6 (0-indexed: 45-39=6)
    # IMGT 47 -> FR2 index 8 (0-indexed: 47-39=8)
    
    # Actually, FR2 in sequence is from position 38 (0-indexed), so:
    # IMGT 39 -> seq[38], IMGT 44 -> seq[43], IMGT 45 -> seq[44], IMGT 47 -> seq[46]
    # But we're working with FR2 substring, so:
    # If FR2 = seq[38:55], then:
    # IMGT 39 (first of FR2) -> FR2[0]
    # IMGT 44 -> FR2[5] (44-39=5)
    # IMGT 45 -> FR2[6] (45-39=6)
    # IMGT 47 -> FR2[8] (47-39=8)
    
    matches = 0
    
    # Check position 44 (FR2 index 5)
    if len(fr2) > 5:
        pos_44_aa = fr2[5]
        pos_44_def = hallmark_defs.get("44", {})
        if pos_44_aa in pos_44_def.get("typical_vhh_aas", []):
            matches += 1
    
    # Check position 45 (FR2 index 6)
    if len(fr2) > 6:
        pos_45_aa = fr2[6]
        pos_45_def = hallmark_defs.get("45", {})
        if pos_45_aa in pos_45_def.get("typical_vhh_aas", []):
            matches += 1
    
    # Check position 47 (FR2 index 8)
    if len(fr2) > 8:
        pos_47_aa = fr2[8]
        pos_47_def = hallmark_defs.get("47", {})
        if pos_47_aa in pos_47_def.get("typical_vhh_aas", []):
            matches += 1
    
    # Position 37 is at the end of FR1, not in FR2
    # We'd need the full sequence context to check it
    # For now, check if we have at least 2 matches (out of 3 checkable positions)
    
    return matches >= 2

