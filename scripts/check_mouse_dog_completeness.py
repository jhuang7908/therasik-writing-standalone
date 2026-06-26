#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
check_mouse_dog_completeness.py


"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FC_AA_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa"


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
        elif not line.startswith("#"):
            buf.append(line)
    
    if header is not None:
        seqs[header] = "".join(buf)
    
    return seqs


def analyze_ighc_completeness(seqs: Dict[str, str], species: str) -> Dict:
    """IGHC"""
    results = defaultdict(lambda: {
        "CH1": [],
        "Hinge": [],
        "CH2": [],
        "CH3": [],
        "C_terminal": [],
        "complete_sets": []
    })
    
    # IgG
    for header, seq in seqs.items():
        # header
        # : Mouse_IGHG1_CH1_IGHG1*01_97aa
        match = re.search(r'IGHG(\d+[A-Z]?)[_A-Z]*_(CH1|Unknown|CH2|CH3)', header)
        if match:
            igg_type = match.group(1)
            domain_type = match.group(2)
            allele_match = re.search(r'\*(\d+)', header)
            allele_id = allele_match.group(1) if allele_match else "01"
            
            key = f"IgG{igg_type}*{allele_id}"
            
            if domain_type == "CH1":
                results[key]["CH1"].append((header, len(seq)))
            elif domain_type == "Unknown":
                if len(seq) < 20:
                    results[key]["Hinge"].append((header, len(seq)))
                else:
                    results[key]["C_terminal"].append((header, len(seq)))
            elif domain_type == "CH2":
                results[key]["CH2"].append((header, len(seq)))
            elif domain_type == "CH3":
                results[key]["CH3"].append((header, len(seq)))
    
    # 
    completeness = {}
    for key, domains in results.items():
        has_ch1 = len(domains["CH1"]) > 0
        has_hinge = len(domains["Hinge"]) > 0
        has_ch2 = len(domains["CH2"]) > 0
        has_ch3 = len(domains["CH3"]) > 0
        has_c_terminal = len(domains["C_terminal"]) > 0
        
        is_complete = has_ch1 and has_hinge and has_ch2 and has_ch3
        
        completeness[key] = {
            "has_ch1": has_ch1,
            "has_hinge": has_hinge,
            "has_ch2": has_ch2,
            "has_ch3": has_ch3,
            "has_c_terminal": has_c_terminal,
            "is_complete": is_complete,
            "counts": {
                "CH1": len(domains["CH1"]),
                "Hinge": len(domains["Hinge"]),
                "CH2": len(domains["CH2"]),
                "CH3": len(domains["CH3"]),
                "C_terminal": len(domains["C_terminal"])
            }
        }
    
    return completeness


def main():
    print("=" * 80)
    print("")
    print("=" * 80)
    
    for species in ["mouse", "dog"]:
        print(f"\n{'='*80}")
        print(f": {species.upper()}")
        print(f"{'='*80}")
        
        species_path = FC_AA_DIR / species
        if not species_path.exists():
            print(f"[WARN] : {species_path}")
            continue
        
        # 1. IGHC
        print(f"\n[1] IGHC（）")
        print("-" * 80)
        
        ighc_file = species_path / f"IGHC_{species}.fasta"
        if ighc_file.exists():
            ighc_seqs = load_fasta(ighc_file)
            completeness = analyze_ighc_completeness(ighc_seqs, species)
            
            print(f"  : {len(ighc_seqs)}")
            print(f"  IgG: {len(completeness)}")
            
            complete_count = sum(1 for v in completeness.values() if v["is_complete"])
            print(f"  : {complete_count}/{len(completeness)}")
            
            print(f"\n  :")
            for igg_type, info in sorted(completeness.items()):
                status = "" if info["is_complete"] else ""
                c_term_status = "C" if info["has_c_terminal"] else "C"
                print(f"    {igg_type}: {status} ({c_term_status})")
                print(f"      CH1: {info['counts']['CH1']}, Hinge: {info['counts']['Hinge']}, "
                      f"CH2: {info['counts']['CH2']}, CH3: {info['counts']['CH3']}, "
                      f"C: {info['counts']['C_terminal']}")
        
        # 2. IGKC
        print(f"\n[2] IGKC（κ）")
        print("-" * 80)
        
        igkc_file = species_path / f"IGKC_{species}.fasta"
        if igkc_file.exists():
            igkc_seqs = load_fasta(igkc_file)
            lengths = [len(seq) for seq in igkc_seqs.values()]
            
            print(f"  : {len(igkc_seqs)}")
            print(f"  : {min(lengths)}-{max(lengths)}aa")
            print(f"  : {'' if all(107 <= l <= 111 for l in lengths) else ''}")
        
        # 3. IGLC
        print(f"\n[3] IGLC（λ）")
        print("-" * 80)
        
        iglc_file = species_path / f"IGLC_{species}.fasta"
        if iglc_file.exists():
            iglc_seqs = load_fasta(iglc_file)
            lengths = [len(seq) for seq in iglc_seqs.values()]
            
            print(f"  : {len(iglc_seqs)}")
            print(f"  : {min(lengths)}-{max(lengths)}aa")
            print(f"  : {'' if all(105 <= l <= 106 for l in lengths) else ''}")
    
    print(f"\n{'='*80}")
    print("！")
    print(f"{'='*80}")
    
    return 0


if __name__ == "__main__":
    exit(main())


















