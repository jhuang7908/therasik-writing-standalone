#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Variable Domain Trimming Tool

（Variable Domain），（Constant Region）。
 anarcii 。
"""

import sys
import re
from typing import Dict, Any, Tuple, Optional
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.numbering.anarcii_adapter import _get_anarcii_obj, HAS_ANARCII


def trim_variable_domain(sequence: str) -> Tuple[str, Dict[str, Any]]:
    """
    
    
    Args:
        sequence: 
    
    Returns:
        (trimmed_sequence, metadata)
        
        trimmed_sequence: 
        metadata: Dict:
            - detected: bool - 
            - trimmed_constant_region: bool - 
            - original_length: int - 
            - variable_domain_length: int - 
            - v_start: int - （0-based）
            - v_end: int - （0-based，）
            - detection_method: str - 
    """
    if not HAS_ANARCII:
        raise RuntimeError("ANARCII is not available. Install with: pip install anarcii")
    
    if not sequence or not isinstance(sequence, str):
        raise ValueError("Sequence must be a non-empty string")
    
    seq_clean = sequence.strip.upper.replace(" ", "").replace("\n", "").replace("\r", "").replace("*", "")
    if not seq_clean:
        raise ValueError("Sequence is empty after cleaning")
    
    original_length = len(seq_clean)
    
    #  anarcii 
    try:
        anarcii_obj = _get_anarcii_obj
        result_imgt = anarcii_obj.number(seq_clean)
    except Exception as e:
        raise RuntimeError(f"ANARCII numbering failed: {e}") from e
    
    if not isinstance(result_imgt, dict) or len(result_imgt) == 0:
        raise RuntimeError("ANARCII returned empty or invalid result")
    
    # 
    key = next(iter(result_imgt.keys))
    seq_info = result_imgt.get(key, {})
    
    if not isinstance(seq_info, dict):
        raise RuntimeError("ANARCII returned unexpected result format")
    
    numbering = seq_info.get("numbering", [])
    
    if not numbering:
        # ，
        v_length = original_length
        return seq_clean, {
            "detected": False,
            "trimmed_constant_region": False,
            "original_length": original_length,
            "variable_domain_length": v_length,  # 
            "v_length": v_length,  # （ STOP ）
            "v_start": 0,
            "v_end": original_length,
            "detection_method": "anarcii_auto_trim_fallback"
        }
    
    #  IMGT 
    max_imgt_pos = 0
    last_seq_idx = -1
    last_valid_seq_idx = -1
    
    seq_pos = 0
    for item in numbering:
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        
        pos_info, aa = item[0], item[1]
        
        #  gap
        if aa == "-":
            # Gap ， seq_pos 
            continue
        
        if pos_info is None:
            continue
        
        if not isinstance(pos_info, tuple) or len(pos_info) < 1:
            continue
        
        pos = pos_info[0]
        
        # 
        if seq_pos < len(seq_clean) and aa == seq_clean[seq_pos]:
            #  IMGT 
            try:
                pos_num = int(pos)
                if pos_num > max_imgt_pos:
                    max_imgt_pos = pos_num
                    last_seq_idx = seq_pos
                # 
                last_valid_seq_idx = seq_pos
            except (ValueError, TypeError):
                pass
            
            seq_pos += 1
        elif aa != "-":
            #  gap，
            # ， last_valid_seq_idx 
            break
    
    # 
    #  IMGT  1-128
    # ：
    # 1.  max_imgt_pos >= 100  last_valid_seq_idx < original_length - 10，
    # 2.  last_valid_seq_idx + 1 
    
    if last_valid_seq_idx >= 0:
        # 
        v_end = last_valid_seq_idx + 1
        
        #  v_end 
        v_end = min(v_end, original_length)
        
        # 
        #  max_imgt_pos  128  v_end  original_length，
        if max_imgt_pos >= 100 and v_end < original_length - 10:
            trimmed_sequence = seq_clean[:v_end]
            trimmed_constant_region = True
        elif max_imgt_pos >= 100 and original_length > 130:
            # IMGT ，
            #  last_valid_seq_idx 
            trimmed_sequence = seq_clean[:v_end]
            trimmed_constant_region = (v_end < original_length - 5)
        else:
            # ，
            trimmed_sequence = seq_clean
            trimmed_constant_region = False
            v_end = original_length
    else:
        # ，
        trimmed_sequence = seq_clean
        trimmed_constant_region = False
        v_end = original_length
    
    # 
    v_length = len(trimmed_sequence)
    metadata = {
        "detected": True,
        "trimmed_constant_region": trimmed_constant_region,
        "original_length": original_length,
        "variable_domain_length": v_length,  # 
        "v_length": v_length,  # （ STOP ）
        "v_start": 0,
        "v_end": v_end,
        "detection_method": "anarcii_auto_trim"
    }
    
    return trimmed_sequence, metadata


def main:
    """"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Variable Domain Trimming Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--fasta',
        type=str,
        required=True,
        help='FASTA'
    )
    parser.add_argument(
        '--out_fasta',
        type=str,
        required=True,
        help='FASTA'
    )
    parser.add_argument(
        '--out_json',
        type=str,
        default=None,
        help='JSON（，）'
    )
    
    args = parser.parse_args
    
    # 
    fasta_path = Path(args.fasta)
    if not fasta_path.exists:
        print(f"❌ ERROR: FASTA: {fasta_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(fasta_path, 'r', encoding='utf-8') as f:
        content = f.read
    
    lines = [line.strip for line in content.splitlines if line.strip]
    if not lines:
        print(f"❌ ERROR: FASTA", file=sys.stderr)
        sys.exit(1)
    
    # （ header）
    seq_lines = [line for line in lines if not line.startswith('>')]
    sequence = ''.join(seq_lines).upper.replace(' ', '').replace('\n', '').replace('*', '')
    
    if not sequence:
        print(f"❌ ERROR: ", file=sys.stderr)
        sys.exit(1)
    
    print(f"📂 : {len(sequence)} aa")
    
    # 
    try:
        trimmed_sequence, metadata = trim_variable_domain(sequence)
    except Exception as e:
        print(f"❌ ERROR: : {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"✅ ")
    print(f"  - : {metadata['original_length']} aa")
    print(f"  - : {metadata['variable_domain_length']} aa")
    print(f"  - : {metadata['trimmed_constant_region']}")
    print(f"  - : {metadata['detection_method']}")
    
    # 
    out_fasta_path = Path(args.out_fasta)
    out_fasta_path.parent.mkdir(parents=True, exist_ok=True)
    
    #  header
    header = ""
    for line in lines:
        if line.startswith('>'):
            header = line
            break
    
    with open(out_fasta_path, 'w', encoding='utf-8') as f:
        if header:
            f.write(f"{header}\n")
        else:
            f.write(">trimmed_sequence\n")
        f.write(trimmed_sequence + "\n")
    
    print(f"✅ : {out_fasta_path}")
    
    # 
    if args.out_json:
        import json
        json_path = Path(args.out_json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ : {json_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main)








