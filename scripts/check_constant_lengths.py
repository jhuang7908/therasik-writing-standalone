#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
check_constant_lengths.py

，
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FC_AA_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa"

# 
EXPECTED_LENGTHS = {
    "IGHC": {
        "CH1": (97, 98),      # CH1
        "Hinge": (12, 19),    # Hinge
        "CH2": (107, 110),    # CH2
        "CH3": (107, 110),    # CH3
        "C_terminal": (27, 71),  # C
        "Full": (370, 415),   # （CH1+Hinge+CH2+CH3+C）
    },
    "IGKC": {
        "Full": (107, 111),   # κ
    },
    "IGLC": {
        "Full": (105, 106),   # λ
    },
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


def analyze_ighc_lengths(seqs: Dict[str, str], species: str) -> Dict:
    """IGHC"""
    results = {
        "CH1": [],
        "Hinge": [],
        "CH2": [],
        "CH3": [],
        "C_terminal": [],
        "suspicious": []
    }
    
    for header, seq in seqs.items():
        header_upper = header.upper()
        seq_len = len(seq.replace("-", "").replace(" ", ""))
        
        if "_CH1_" in header_upper or ("CH1" in header_upper and "CH2" not in header_upper and "CH3" not in header_upper):
            results["CH1"].append((header, seq_len))
            if not (EXPECTED_LENGTHS["IGHC"]["CH1"][0] <= seq_len <= EXPECTED_LENGTHS["IGHC"]["CH1"][1]):
                results["suspicious"].append({
                    "header": header,
                    "type": "CH1",
                    "length": seq_len,
                    "expected": EXPECTED_LENGTHS["IGHC"]["CH1"],
                    "issue": f"CH1: {seq_len}aa ({EXPECTED_LENGTHS['IGHC']['CH1'][0]}-{EXPECTED_LENGTHS['IGHC']['CH1'][1]}aa)"
                })
        
        elif "_HINGE_" in header_upper or ("UNKNOWN" in header_upper and seq_len < 20):
            results["Hinge"].append((header, seq_len))
            if not (EXPECTED_LENGTHS["IGHC"]["Hinge"][0] <= seq_len <= EXPECTED_LENGTHS["IGHC"]["Hinge"][1]):
                results["suspicious"].append({
                    "header": header,
                    "type": "Hinge",
                    "length": seq_len,
                    "expected": EXPECTED_LENGTHS["IGHC"]["Hinge"],
                    "issue": f"Hinge: {seq_len}aa ({EXPECTED_LENGTHS['IGHC']['Hinge'][0]}-{EXPECTED_LENGTHS['IGHC']['Hinge'][1]}aa)"
                })
        
        elif "_CH2_" in header_upper or ("CH2" in header_upper and "CH3" not in header_upper):
            results["CH2"].append((header, seq_len))
            if not (EXPECTED_LENGTHS["IGHC"]["CH2"][0] <= seq_len <= EXPECTED_LENGTHS["IGHC"]["CH2"][1]):
                results["suspicious"].append({
                    "header": header,
                    "type": "CH2",
                    "length": seq_len,
                    "expected": EXPECTED_LENGTHS["IGHC"]["CH2"],
                    "issue": f"CH2: {seq_len}aa ({EXPECTED_LENGTHS['IGHC']['CH2'][0]}-{EXPECTED_LENGTHS['IGHC']['CH2'][1]}aa)"
                })
        
        elif "_CH3_" in header_upper or ("CH3" in header_upper and "CH2" not in header_upper):
            results["CH3"].append((header, seq_len))
            if not (EXPECTED_LENGTHS["IGHC"]["CH3"][0] <= seq_len <= EXPECTED_LENGTHS["IGHC"]["CH3"][1]):
                results["suspicious"].append({
                    "header": header,
                    "length": seq_len,
                    "type": "CH3",
                    "expected": EXPECTED_LENGTHS["IGHC"]["CH3"],
                    "issue": f"CH3: {seq_len}aa ({EXPECTED_LENGTHS['IGHC']['CH3'][0]}-{EXPECTED_LENGTHS['IGHC']['CH3'][1]}aa)"
                })
        
        elif "_UNKNOWN_" in header_upper and seq_len > 20:
            results["C_terminal"].append((header, seq_len))
            if seq_len < EXPECTED_LENGTHS["IGHC"]["C_terminal"][0]:
                results["suspicious"].append({
                    "header": header,
                    "type": "C_terminal",
                    "length": seq_len,
                    "expected": EXPECTED_LENGTHS["IGHC"]["C_terminal"],
                    "issue": f"C: {seq_len}aa ({EXPECTED_LENGTHS['IGHC']['C_terminal'][0]}aa)"
                })
    
    return results


def analyze_light_chain_lengths(seqs: Dict[str, str], chain_type: str) -> Dict:
    """"""
    results = {
        "lengths": [],
        "suspicious": []
    }
    
    expected = EXPECTED_LENGTHS[chain_type]["Full"]
    
    for header, seq in seqs.items():
        seq_len = len(seq.replace("-", "").replace(" ", ""))
        results["lengths"].append((header, seq_len))
        
        if not (expected[0] <= seq_len <= expected[1]):
            results["suspicious"].append({
                "header": header,
                "length": seq_len,
                "expected": expected,
                "issue": f"{chain_type}: {seq_len}aa ({expected[0]}-{expected[1]}aa)"
            })
    
    return results


def main():
    print("=" * 80)
    print("，")
    print("=" * 80)
    
    all_results = {}
    
    species_list = ["human", "mouse", "dog", "cat"]
    
    for species in species_list:
        print(f"\n{'='*80}")
        print(f": {species.upper()}")
        print(f"{'='*80}")
        
        species_path = FC_AA_DIR / species
        if not species_path.exists():
            print(f"[WARN] : {species_path}")
            continue
        
        results = {
            "species": species,
            "IGHC": {},
            "IGKC": {},
            "IGLC": {}
        }
        
        # 1. IGHC
        print(f"\n[1] IGHC（）")
        print("-" * 80)
        
        ighc_file = species_path / f"IGHC_{species}.fasta"
        if ighc_file.exists():
            ighc_seqs = load_fasta(ighc_file)
            
            if ighc_seqs:
                ighc_analysis = analyze_ighc_lengths(ighc_seqs, species)
                
                print(f"  :")
                print(f"    CH1: {len(ighc_analysis['CH1'])}")
                if ighc_analysis['CH1']:
                    ch1_lengths = [l for _, l in ighc_analysis['CH1']]
                    print(f"     : {min(ch1_lengths)}-{max(ch1_lengths)}aa")
                
                print(f"    Hinge: {len(ighc_analysis['Hinge'])}")
                if ighc_analysis['Hinge']:
                    hinge_lengths = [l for _, l in ighc_analysis['Hinge']]
                    print(f"     : {min(hinge_lengths)}-{max(hinge_lengths)}aa")
                
                print(f"    CH2: {len(ighc_analysis['CH2'])}")
                if ighc_analysis['CH2']:
                    ch2_lengths = [l for _, l in ighc_analysis['CH2']]
                    print(f"     : {min(ch2_lengths)}-{max(ch2_lengths)}aa")
                
                print(f"    CH3: {len(ighc_analysis['CH3'])}")
                if ighc_analysis['CH3']:
                    ch3_lengths = [l for _, l in ighc_analysis['CH3']]
                    print(f"     : {min(ch3_lengths)}-{max(ch3_lengths)}aa")
                
                print(f"    C: {len(ighc_analysis['C_terminal'])}")
                if ighc_analysis['C_terminal']:
                    c_lengths = [l for _, l in ighc_analysis['C_terminal']]
                    print(f"     : {min(c_lengths)}-{max(c_lengths)}aa")
                
                if ighc_analysis['suspicious']:
                    print(f"\n  ⚠️  {len(ighc_analysis['suspicious'])} :")
                    for item in ighc_analysis['suspicious'][:10]:  # 10
                        print(f"    - {item['header'][:60]}...")
                        print(f"      {item['issue']}")
                else:
                    print(f"\n  ✅ ")
                
                results["IGHC"] = {
                    "count": len(ighc_seqs),
                    "suspicious_count": len(ighc_analysis['suspicious']),
                    "suspicious": ighc_analysis['suspicious']
                }
        
        # 2. IGKC
        print(f"\n[2] IGKC（κ）")
        print("-" * 80)
        
        igkc_file = species_path / f"IGKC_{species}.fasta"
        if igkc_file.exists():
            igkc_seqs = load_fasta(igkc_file)
            
            if igkc_seqs:
                igkc_analysis = analyze_light_chain_lengths(igkc_seqs, "IGKC")
                
                lengths = [l for _, l in igkc_analysis['lengths']]
                print(f"  : {len(igkc_seqs)}")
                print(f"  : {min(lengths)}-{max(lengths)}aa")
                
                if igkc_analysis['suspicious']:
                    print(f"\n  ⚠️  {len(igkc_analysis['suspicious'])} :")
                    for item in igkc_analysis['suspicious']:
                        print(f"    - {item['header'][:60]}...")
                        print(f"      {item['issue']}")
                else:
                    print(f"\n  ✅ ")
                
                results["IGKC"] = {
                    "count": len(igkc_seqs),
                    "suspicious_count": len(igkc_analysis['suspicious']),
                    "suspicious": igkc_analysis['suspicious']
                }
        
        # 3. IGLC
        print(f"\n[3] IGLC（λ）")
        print("-" * 80)
        
        iglc_file = species_path / f"IGLC_{species}.fasta"
        if iglc_file.exists():
            iglc_seqs = load_fasta(iglc_file)
            
            if iglc_seqs:
                iglc_analysis = analyze_light_chain_lengths(iglc_seqs, "IGLC")
                
                lengths = [l for _, l in iglc_analysis['lengths']]
                print(f"  : {len(iglc_seqs)}")
                if lengths:
                    print(f"  : {min(lengths)}-{max(lengths)}aa")
                
                if iglc_analysis['suspicious']:
                    print(f"\n  ⚠️  {len(iglc_analysis['suspicious'])} :")
                    for item in iglc_analysis['suspicious']:
                        print(f"    - {item['header'][:60]}...")
                        print(f"      {item['issue']}")
                else:
                    print(f"\n  ✅ ")
                
                results["IGLC"] = {
                    "count": len(iglc_seqs),
                    "suspicious_count": len(iglc_analysis['suspicious']),
                    "suspicious": iglc_analysis['suspicious']
                }
        
        all_results[species] = results
    
    # 
    report_file = FC_AA_DIR / "length_validation_report.json"
    report_file.write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    
    print(f"\n{'='*80}")
    print("！")
    print(f": {report_file}")
    print(f"{'='*80}")
    
    # 
    total_suspicious = sum(
        r.get("IGHC", {}).get("suspicious_count", 0) +
        r.get("IGKC", {}).get("suspicious_count", 0) +
        r.get("IGLC", {}).get("suspicious_count", 0)
        for r in all_results.values()
    )
    
    print(f"\n {total_suspicious} ")
    
    return 0


if __name__ == "__main__":
    exit(main())


















