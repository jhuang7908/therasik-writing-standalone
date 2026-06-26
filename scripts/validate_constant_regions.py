#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
validate_constant_regions.py

IGHC、IGKCIGLC

"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FC_AA_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa"

SPECIES_DIRS = {
    "human": "human",
    "mouse": "mouse",
    "dog": "dog",
    "cat": "cat",
}


def load_fasta(path: Path) -> Dict[str, str]:
    """FASTA"""
    seqs = {}
    header = None
    buf = []
    
    if not path.exists():
        return {}
    
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"[ERROR]  {path}: {e}")
        return {}
    
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                seqs[header] = "".join(buf)
            header = line[1:].strip()
            buf = []
        elif not line.startswith("#"):  # 
            buf.append(line)
    
    if header is not None:
        seqs[header] = "".join(buf)
    
    return seqs


def validate_sequence(seq: str) -> Dict:
    """"""
    if not seq:
        return {
            "is_valid": False,
            "length": 0,
            "has_unknown": False,
            "has_stop": False,
            "invalid_chars": [],
            "note": "Empty sequence"
        }
    
    seq_clean = seq.replace("-", "").replace(" ", "").upper()
    
    valid_aa = set("ACDEFGHIKLMNPQRSTVWY*X")
    invalid_chars = [c for c in set(seq_clean) if c not in valid_aa]
    has_unknown = "X" in seq_clean
    has_stop = "*" in seq_clean
    
    return {
        "is_valid": len(invalid_chars) == 0 and len(seq_clean) > 0,
        "length": len(seq_clean),
        "has_unknown": has_unknown,
        "has_stop": has_stop,
        "invalid_chars": invalid_chars,
        "note": "Valid" if len(invalid_chars) == 0 and len(seq_clean) > 0 else "Invalid"
    }


def analyze_ighc_structure(seqs: Dict[str, str], species: str) -> Dict:
    """IGHC"""
    structure = {
        "has_ch1": False,
        "has_hinge": False,
        "has_ch2": False,
        "has_ch3": False,
        "has_c_terminal": False,
        "ch1_count": 0,
        "hinge_count": 0,
        "ch2_count": 0,
        "ch3_count": 0,
        "c_terminal_count": 0,
        "total_sequences": len(seqs),
        "is_complete": False
    }
    
    for header in seqs.keys():
        header_upper = header.upper()
        if "_CH1_" in header_upper or "CH1" in header_upper:
            structure["has_ch1"] = True
            structure["ch1_count"] += 1
        if "_HINGE_" in header_upper or ("UNKNOWN" in header_upper and len(seqs[header]) < 20):
            structure["has_hinge"] = True
            structure["hinge_count"] += 1
        if "_CH2_" in header_upper or "CH2" in header_upper:
            structure["has_ch2"] = True
            structure["ch2_count"] += 1
        if "_CH3_" in header_upper or "CH3" in header_upper:
            structure["has_ch3"] = True
            structure["ch3_count"] += 1
        if "_UNKNOWN_" in header_upper and len(seqs[header]) > 20:
            structure["has_c_terminal"] = True
            structure["c_terminal_count"] += 1
    
    # 
    structure["is_complete"] = (
        structure["has_ch1"] and
        structure["has_hinge"] and
        structure["has_ch2"] and
        structure["has_ch3"]
    )
    
    return structure


def main():
    print("=" * 80)
    print("IGHC、IGKCIGLC")
    print("=" * 80)
    
    all_results = {}
    
    for species_key, species_dir in SPECIES_DIRS.items():
        print(f"\n{'='*80}")
        print(f": {species_key.upper()}")
        print(f"{'='*80}")
        
        species_path = FC_AA_DIR / species_dir
        if not species_path.exists():
            print(f"[WARN] : {species_path}")
            continue
        
        results = {
            "species": species_key,
            "IGHC": {},
            "IGKC": {},
            "IGLC": {}
        }
        
        # 1. IGHC
        print(f"\n[1] IGHC（）")
        print("-" * 80)
        
        ighc_file = species_path / f"IGHC_{species_dir}.fasta"
        if ighc_file.exists():
            ighc_seqs = load_fasta(ighc_file)
            print(f"   {len(ighc_seqs)} IGHC")
            
            if ighc_seqs:
                # 
                structure = analyze_ighc_structure(ighc_seqs, species_key)
                print(f"  :")
                print(f"    CH1: {'✓' if structure['has_ch1'] else '✗'} ({structure['ch1_count']})")
                print(f"    Hinge: {'✓' if structure['has_hinge'] else '✗'} ({structure['hinge_count']})")
                print(f"    CH2: {'✓' if structure['has_ch2'] else '✗'} ({structure['ch2_count']})")
                print(f"    CH3: {'✓' if structure['has_ch3'] else '✗'} ({structure['ch3_count']})")
                print(f"    C: {'✓' if structure['has_c_terminal'] else '✗'} ({structure['c_terminal_count']})")
                print(f"    : {'✓ ' if structure['is_complete'] else '✗ '}")
                
                # 
                valid_count = 0
                for header, seq in list(ighc_seqs.items())[:5]:
                    validation = validate_sequence(seq)
                    if validation["is_valid"]:
                        valid_count += 1
                
                results["IGHC"] = {
                    "file": str(ighc_file),
                    "count": len(ighc_seqs),
                    "structure": structure,
                    "status": "Complete" if structure["is_complete"] else "Incomplete",
                    "note": "Contains all domains" if structure["is_complete"] else "Missing some domains"
                }
            else:
                print("  [WARN] ")
                results["IGHC"] = {
                    "file": str(ighc_file),
                    "count": 0,
                    "status": "Placeholder",
                    "note": "Needs to be filled with actual sequences"
                }
        else:
            print(f"  [WARN] : {ighc_file}")
            results["IGHC"] = {
                "file": None,
                "count": 0,
                "status": "Missing"
            }
        
        # 2. IGKC
        print(f"\n[2] IGKC（κ）")
        print("-" * 80)
        
        igkc_file = species_path / f"IGKC_{species_dir}.fasta"
        if igkc_file.exists():
            igkc_seqs = load_fasta(igkc_file)
            print(f"   {len(igkc_seqs)} IGKC")
            
            if igkc_seqs:
                valid_count = 0
                lengths = []
                for header, seq in igkc_seqs.items():
                    validation = validate_sequence(seq)
                    if validation["is_valid"]:
                        valid_count += 1
                        lengths.append(validation["length"])
                
                if lengths:
                    print(f"  : {valid_count}/{len(igkc_seqs)}")
                    print(f"  : {min(lengths)}-{max(lengths)} aa")
                    print(f"  : {max(set(lengths), key=lengths.count)} aa")
                
                results["IGKC"] = {
                    "file": str(igkc_file),
                    "count": len(igkc_seqs),
                    "valid_count": valid_count,
                    "length_range": f"{min(lengths)}-{max(lengths)}" if lengths else "N/A",
                    "status": "Complete" if valid_count > 0 else "Placeholder"
                }
            else:
                print("  [WARN] ")
                results["IGKC"] = {
                    "file": str(igkc_file),
                    "count": 0,
                    "status": "Placeholder"
                }
        else:
            print(f"  [WARN] : {igkc_file}")
            results["IGKC"] = {
                "file": None,
                "count": 0,
                "status": "Missing"
            }
        
        # 3. IGLC
        print(f"\n[3] IGLC（λ）")
        print("-" * 80)
        
        iglc_file = species_path / f"IGLC_{species_dir}.fasta"
        if iglc_file.exists():
            iglc_seqs = load_fasta(iglc_file)
            print(f"   {len(iglc_seqs)} IGLC")
            
            if iglc_seqs:
                valid_count = 0
                lengths = []
                for header, seq in iglc_seqs.items():
                    validation = validate_sequence(seq)
                    if validation["is_valid"]:
                        valid_count += 1
                        lengths.append(validation["length"])
                
                if lengths:
                    print(f"  : {valid_count}/{len(iglc_seqs)}")
                    print(f"  : {min(lengths)}-{max(lengths)} aa")
                    print(f"  : {max(set(lengths), key=lengths.count)} aa")
                
                results["IGLC"] = {
                    "file": str(iglc_file),
                    "count": len(iglc_seqs),
                    "valid_count": valid_count,
                    "length_range": f"{min(lengths)}-{max(lengths)}" if lengths else "N/A",
                    "status": "Complete" if valid_count > 0 else "Placeholder"
                }
            else:
                print("  [WARN] ")
                results["IGLC"] = {
                    "file": str(iglc_file),
                    "count": 0,
                    "status": "Placeholder"
                }
        else:
            print(f"  [WARN] : {iglc_file}")
            results["IGLC"] = {
                "file": None,
                "count": 0,
                "status": "Missing"
            }
        
        all_results[species_key] = results
    
    # 
    report_file = FC_AA_DIR / "constant_regions_validation.json"
    report_file.write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    
    print(f"\n{'='*80}")
    print("！")
    print(f": {report_file}")
    print(f"{'='*80}")
    
    # 
    print("\n:")
    for species_key, results in all_results.items():
        print(f"\n{species_key.upper()}:")
        print(f"  IGHC: {results['IGHC'].get('status', 'Unknown')} ({results['IGHC'].get('count', 0)})")
        print(f"  IGKC: {results['IGKC'].get('status', 'Unknown')} ({results['IGKC'].get('count', 0)})")
        print(f"  IGLC: {results['IGLC'].get('status', 'Unknown')} ({results['IGLC'].get('count', 0)})")
    
    return 0


if __name__ == "__main__":
    exit(main())


















