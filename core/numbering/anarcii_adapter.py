"""
ANARCII  - 

ANARCII，IMGTKabat。
import anarci，anarcii。
"""

from __future__ import annotations

import sys
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from anarcii import Anarcii
    HAS_ANARCII = True
except ImportError:
    HAS_ANARCII = False
    Anarcii = None

# Global ANARCII object (lazy initialization)
_anarcii_obj: Optional[Anarcii] = None


def _get_anarcii_obj() -> Anarcii:
    """Get global ANARCII object (lazy initialization)."""
    global _anarcii_obj
    
    if not HAS_ANARCII:
        raise ImportError("anarcii package is not installed. Install with: pip install anarcii")
    
    if _anarcii_obj is None:
        _anarcii_obj = Anarcii(
            seq_type="antibody",
            mode="accuracy",
            batch_size=32,
            cpu=True,
            ncpu=-1,
            verbose=False,
        )
    
    return _anarcii_obj


def get_engine_info() -> Dict[str, Any]:
    """
    
    
    Returns:
        Dict:
        - name: "anarcii"
        - version: （"unknown"）
        - schemes: ["imgt", "kabat"]
    """
    if not HAS_ANARCII:
        return {
            "name": "anarcii",
            "version": "not_installed",
            "schemes": ["imgt", "kabat"]
        }
    
    try:
        import anarcii
        version = getattr(anarcii, '__version__', 'unknown')
    except Exception:
        version = "unknown"
    
    return {
        "name": "anarcii",
        "version": version,
        "schemes": ["imgt", "kabat"]
    }


def number_sequence(seq: str, scheme: str) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    """
    
    
    Args:
        seq: 
        scheme:  ("imgt"  "kabat")
    
    Returns:
        (pos_to_aa, residue_table)
        
        pos_to_aa: Dict[str, str] -  -> 
        residue_table: List[Dict] - ，:
            - seq_idx:  (0-based)
            - aa: 
            - position_label:  (， "37", "37A",  Nonegap)
    
    Raises:
        RuntimeError: 
    """
    if not HAS_ANARCII:
        raise RuntimeError("ANARCII is not available. Install with: pip install anarcii")
    
    if scheme not in ["imgt", "kabat"]:
        raise ValueError(f"Unsupported scheme: {scheme}. Must be 'imgt' or 'kabat'")
    
    if not seq or not isinstance(seq, str):
        raise ValueError("Sequence must be a non-empty string")
    
    seq_clean = seq.strip().upper().replace(" ", "").replace("\n", "").replace("\r", "").replace("*", "")
    if not seq_clean:
        raise ValueError("Sequence is empty after cleaning")
    
    try:
        anarcii_obj = _get_anarcii_obj()
    except ImportError as e:
        raise RuntimeError(f"ANARCII is not available: {e}") from e
    
    # Run ANARCII for IMGT scheme first
    try:
        result_imgt = anarcii_obj.number(seq_clean)
    except Exception as e:
        raise RuntimeError(f"ANARCII IMGT numbering failed: {e}") from e
    
    if not isinstance(result_imgt, dict) or len(result_imgt) == 0:
        raise RuntimeError("ANARCII IMGT returned empty or invalid result")
    
    # Get the first key (usually "Sequence")
    key = next(iter(result_imgt.keys()))
    seq_info_imgt = result_imgt.get(key, {})
    
    if not isinstance(seq_info_imgt, dict):
        raise RuntimeError("ANARCII IMGT returned unexpected result format")
    
    numbering_imgt = seq_info_imgt.get("numbering", [])
    
    if not numbering_imgt:
        raise RuntimeError("ANARCII IMGT returned empty numbering")
    
    # Convert to Kabat scheme if needed
    if scheme == "kabat":
        try:
            result_kabat = anarcii_obj.to_scheme('kabat')
        except Exception as e:
            raise RuntimeError(f"ANARCII Kabat conversion failed: {e}") from e
        
        if not isinstance(result_kabat, dict) or len(result_kabat) == 0:
            raise RuntimeError("ANARCII Kabat returned empty or invalid result")
        
        seq_info_kabat = result_kabat.get(key, {})
        
        if not isinstance(seq_info_kabat, dict):
            raise RuntimeError("ANARCII Kabat returned unexpected result format")
        
        numbering = seq_info_kabat.get("numbering", [])
    else:
        numbering = numbering_imgt
    
    if not numbering:
        raise RuntimeError(f"ANARCII {scheme.upper()} returned empty numbering")
    
    # Build pos_to_aa and residue_table
    pos_to_aa: Dict[str, str] = {}
    residue_table: List[Dict[str, Any]] = []
    
    seq_pos = 0
    for num_idx, item in enumerate(numbering):
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        
        pos_info, aa = item[0], item[1]
        
        # Skip gaps
        if aa == "-" or pos_info is None:
            continue
        
        if not isinstance(pos_info, tuple) or len(pos_info) < 1:
            continue
        
        pos = pos_info[0]
        ins_code = pos_info[1] if len(pos_info) > 1 else " "
        
        if ins_code and ins_code.strip():
            pos_label = f"{pos}{ins_code.strip()}"
        else:
            pos_label = str(pos)
        
        # Match to sequence
        if seq_pos < len(seq_clean) and aa == seq_clean[seq_pos]:
            pos_to_aa[pos_label] = aa
            
            residue_table.append({
                "seq_idx": seq_pos,
                "aa": aa,
                "position_label": pos_label
            })
            
            seq_pos += 1
    
    return pos_to_aa, residue_table
