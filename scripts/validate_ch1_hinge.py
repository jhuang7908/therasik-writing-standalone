#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
validate_ch1_hinge.py

fc_databaseCH1hinge region
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FC_DATABASE_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa" / "fc_database"


def load_fasta(path: Path) -> Dict[str, str]:
    """FASTA"""
    seqs = {}
    header = None
    buf = []
    
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
        else:
            buf.append(line)
    
    if header is not None:
        seqs[header] = "".join(buf)
    
    return seqs


def extract_ch1_and_hinge(seqs: Dict[str, str], species: str) -> Dict:
    """CH1hinge region"""
    results = defaultdict(lambda: {
        "CH1": [],
        "hinge": []
    })
    
    for header, seq in seqs.items():
        # header
        # : Human_IGHG1_CH1_IGHG1*01_98aa
        # : Human_IGHG1_Unknown_IGHG1*01_15aa (hinge region)
        
        match = re.search(r'IGHG(\d+)_(CH1|Unknown)', header)
        if match:
            igg_type = f"IgG{match.group(1)}"
            domain_type = match.group(2)
            allele = re.search(r'\*(\d+)', header)
            allele_id = allele.group(1) if allele else "01"
            
            key = f"{igg_type}*{allele_id}"
            
            if domain_type == "CH1":
                results[key]["CH1"].append((header, seq))
            elif domain_type == "Unknown":
                # Hinge regionUnknown（<20aa）
                if len(seq) < 20:
                    results[key]["hinge"].append((header, seq))
    
    return results


def validate_sequence(seq: str) -> Dict:
    """"""
    seq_clean = seq.replace("-", "").replace(" ", "").upper()
    
    valid_aa = set("ACDEFGHIKLMNPQRSTVWY*X")
    invalid_chars = [c for c in set(seq_clean) if c not in valid_aa]
    has_unknown = "X" in seq_clean
    has_stop = "*" in seq_clean
    
    return {
        "length": len(seq_clean),
        "has_unknown": has_unknown,
        "has_stop": has_stop,
        "invalid_chars": invalid_chars,
        "is_valid": len(invalid_chars) == 0 and len(seq_clean) > 0,
        "sequence": seq_clean
    }


def main():
    print("=" * 80)
    print("fc_databaseCH1Hinge Region")
    print("=" * 80)
    
    species_list = ["human", "mouse", "dog"]
    species_map = {
        "human": "Human",
        "mouse": "Mouse",
        "dog": "Dog"
    }
    
    all_results = {}
    
    for species in species_list:
        print(f"\n{'='*80}")
        print(f": {species.upper()}")
        print(f"{'='*80}")
        
        species_dir = FC_DATABASE_DIR / species
        if not species_dir.exists():
            print(f"[WARN] : {species_dir}")
            continue
        
        ighg_file = species_dir / f"IGHC_{species}.fasta"
        if not ighg_file.exists():
            print(f"[WARN] : {ighg_file}")
            continue
        
        ighg_seqs = load_fasta(ighg_file)
        print(f" {len(ighg_seqs)} IGHG")
        
        # CH1hinge
        ch1_hinge_data = extract_ch1_and_hinge(ighg_seqs, species_map[species])
        
        results = {
            "species": species,
            "igg_types": {}
        }
        
        # IgG
        igg_summary = defaultdict(lambda: {
            "CH1": {
                "count": 0,
                "lengths": [],
                "unique_sequences": set(),
                "alleles": []
            },
            "hinge": {
                "count": 0,
                "lengths": [],
                "unique_sequences": set(),
                "alleles": []
            }
        })
        
        for key, domains in ch1_hinge_data.items():
            igg_type = key.split("*")[0]
            allele_id = key.split("*")[1] if "*" in key else "01"
            
            # CH1
            for header, seq in domains["CH1"]:
                validation = validate_sequence(seq)
                igg_summary[igg_type]["CH1"]["count"] += 1
                igg_summary[igg_type]["CH1"]["lengths"].append(validation["length"])
                igg_summary[igg_type]["CH1"]["unique_sequences"].add(seq)
                if allele_id not in igg_summary[igg_type]["CH1"]["alleles"]:
                    igg_summary[igg_type]["CH1"]["alleles"].append(allele_id)
            
            # Hinge
            for header, seq in domains["hinge"]:
                validation = validate_sequence(seq)
                igg_summary[igg_type]["hinge"]["count"] += 1
                igg_summary[igg_type]["hinge"]["lengths"].append(validation["length"])
                igg_summary[igg_type]["hinge"]["unique_sequences"].add(seq)
                if allele_id not in igg_summary[igg_type]["hinge"]["alleles"]:
                    igg_summary[igg_type]["hinge"]["alleles"].append(allele_id)
        
        # 
        for igg_type in sorted(igg_summary.keys()):
            print(f"\n{igg_type}:")
            
            ch1_info = igg_summary[igg_type]["CH1"]
            if ch1_info["count"] > 0:
                print(f"  CH1:")
                print(f"    : {ch1_info['count']}")
                print(f"    : {len(ch1_info['alleles'])}")
                print(f"    : {len(ch1_info['unique_sequences'])}")
                print(f"    : {min(ch1_info['lengths'])}-{max(ch1_info['lengths'])} aa")
                print(f"    : {max(set(ch1_info['lengths']), key=ch1_info['lengths'].count)} aa")
                
                # 30aa
                if ch1_info["unique_sequences"]:
                    first_seq = sorted(ch1_info["unique_sequences"])[0]
                    print(f"    （30aa）: {first_seq[:30]}...")
                
                results["igg_types"][igg_type] = {
                    "CH1": {
                        "count": ch1_info["count"],
                        "allele_count": len(ch1_info["alleles"]),
                        "unique_count": len(ch1_info["unique_sequences"]),
                        "length_range": f"{min(ch1_info['lengths'])}-{max(ch1_info['lengths'])}",
                        "typical_length": max(set(ch1_info['lengths']), key=ch1_info['lengths'].count),
                        "sequences": list(ch1_info["unique_sequences"])
                    }
                }
            
            hinge_info = igg_summary[igg_type]["hinge"]
            if hinge_info["count"] > 0:
                print(f"  Hinge Region:")
                print(f"    : {hinge_info['count']}")
                print(f"    : {len(hinge_info['alleles'])}")
                print(f"    : {len(hinge_info['unique_sequences'])}")
                print(f"    : {min(hinge_info['lengths'])}-{max(hinge_info['lengths'])} aa")
                print(f"    : {max(set(hinge_info['lengths']), key=hinge_info['lengths'].count)} aa")
                
                # 
                print(f"    :")
                for i, seq in enumerate(sorted(hinge_info["unique_sequences"]), 1):
                    print(f"      {i}. {seq} ({len(seq)}aa)")
                
                if igg_type not in results["igg_types"]:
                    results["igg_types"][igg_type] = {}
                results["igg_types"][igg_type]["hinge"] = {
                    "count": hinge_info["count"],
                    "allele_count": len(hinge_info["alleles"]),
                    "unique_count": len(hinge_info["unique_sequences"]),
                    "length_range": f"{min(hinge_info['lengths'])}-{max(hinge_info['lengths'])}",
                    "typical_length": max(set(hinge_info['lengths']), key=hinge_info['lengths'].count),
                    "sequences": list(hinge_info["unique_sequences"])
                }
        
        all_results[species] = results
    
    # 
    report_file = FC_DATABASE_DIR / "ch1_hinge_validation.json"
    report_file.write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    
    print(f"\n{'='*80}")
    print("！")
    print(f": {report_file}")
    print(f"{'='*80}")
    
    return 0


if __name__ == "__main__":
    exit(main())


















