#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
validate_fc_database.py

fc_databaseIGHG、IGKCIGLC
UniProt，
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FC_DATABASE_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa" / "fc_database"
UNIPROT_FC_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa"


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


def load_uniprot_fc(species: str) -> Dict[str, str]:
    """UniProtFc"""
    json_file = UNIPROT_FC_DIR / f"{species.lower()}_fc_aa.json"
    
    if not json_file.exists():
        return {}
    
    try:
        data = json.loads(json_file.read_text(encoding="utf-8"))
        fc_seqs = {}
        for entry in data.get("entries", []):
            ig_type = entry.get("ig_type", "")
            fc_seq = entry.get("fc_sequence", "")
            if fc_seq:
                fc_seqs[ig_type] = fc_seq
        return fc_seqs
    except Exception as e:
        print(f"[WARN] UniProt Fc {json_file}: {e}")
        return {}


def extract_fc_from_ighg(seqs: Dict[str, str], species: str) -> Dict[str, str]:
    """
    IGHGFc（CH2 + CH3 + C）
    
    Fc：
    - CH2（）
    - CH3
    - C（Unknown，CH3）
    """
    fc_seqs = {}
    
    # IgG
    igg_groups = defaultdict(lambda: defaultdict(dict))
    
    for header, seq in seqs.items():
        # header，IgG
        # : Human_IGHG1_CH2_IGHG1*01_110aa
        match = re.search(r'IGHG(\d+)_(CH\d+|Unknown)', header)
        if match:
            igg_type = f"IgG{match.group(1)}"
            domain_type = match.group(2)
            allele = re.search(r'\*(\d+)', header)
            allele_id = allele.group(1) if allele else "01"
            
            igg_groups[igg_type][allele_id][domain_type] = seq
    
    # Fc（CH2 + CH3 + C）
    for igg_type, alleles in igg_groups.items():
        # （*01）
        if "01" in alleles:
            domains = alleles["01"]
        else:
            # *01，
            domains = list(alleles.values())[0]
        
        ch2 = domains.get("CH2", "")
        ch3 = domains.get("CH3", "")
        
        # C（Unknown，CH3）
        # Unknown：（），（C）
        c_terminal_parts = []
        for domain_type, seq in domains.items():
            if domain_type == "Unknown":
                if len(seq) > 20:  # C（44aa27aa）
                    c_terminal_parts.append(seq)
        
        # Fc
        # FcCH2（CH2）
        # UniProtFcCH2
        fc_parts = []
        
        if ch2:
            # CH2（APELL...）
            # UniProtFcCH2（KAKG...）
            # UniProt Fc
            # IgG1，Fc"KAKG"，CH2
            # CH2，CH2
            
            # CH2
            # CH2APELL，
            # UniProtFc
            
            # IgG1，UniProt Fc"KAKG"，CH2
            # UniProtFcCH2，
            # CH2（）
            fc_parts.append(ch2)
        
        if ch3:
            fc_parts.append(ch3)
        
        # C（，）
        c_terminal_parts.sort(key=len, reverse=True)
        fc_parts.extend(c_terminal_parts)
        
        fc_seq = "".join(fc_parts)
        
        if fc_seq:
            fc_seqs[igg_type] = fc_seq
    
    return fc_seqs


def compare_sequences(seq1: str, seq2: str, name1: str, name2: str) -> Dict:
    """"""
    seq1_clean = seq1.replace("-", "").replace(" ", "").upper()
    seq2_clean = seq2.replace("-", "").replace(" ", "").upper()
    
    # 
    min_len = min(len(seq1_clean), len(seq2_clean))
    max_len = max(len(seq1_clean), len(seq2_clean))
    
    if min_len == 0:
        return {
            "match": False,
            "similarity": 0.0,
            "length_diff": max_len,
            "note": "One sequence is empty"
        }
    
    # 
    matches = sum(1 for i in range(min_len) if seq1_clean[i] == seq2_clean[i])
    similarity = matches / max_len if max_len > 0 else 0.0
    
    # 
    is_match = seq1_clean == seq2_clean
    
    # 
    differences = []
    for i in range(min_len):
        if seq1_clean[i] != seq2_clean[i]:
            differences.append({
                "position": i + 1,
                "fc_database": seq1_clean[i],
                "uniprot": seq2_clean[i] if i < len(seq2_clean) else "N/A"
            })
            if len(differences) >= 10:  # 10
                break
    
    return {
        "match": is_match,
        "similarity": similarity,
        "length_fc_database": len(seq1_clean),
        "length_uniprot": len(seq2_clean),
        "length_diff": abs(len(seq1_clean) - len(seq2_clean)),
        "matches": matches,
        "differences": differences[:10],
        "note": "" if is_match else f": {similarity:.2%}"
    }


def validate_sequence(seq: str, seq_type: str) -> Dict:
    """"""
    seq_clean = seq.replace("-", "").replace(" ", "").upper()
    
    # 
    valid_aa = set("ACDEFGHIKLMNPQRSTVWY*X")
    invalid_chars = [c for c in set(seq_clean) if c not in valid_aa]
    
    # 
    length = len(seq_clean)
    
    # 
    has_unknown = "X" in seq_clean
    
    # 
    has_stop = "*" in seq_clean
    
    return {
        "length": length,
        "has_unknown": has_unknown,
        "has_stop": has_stop,
        "invalid_chars": invalid_chars,
        "is_valid": len(invalid_chars) == 0 and length > 0
    }


def main():
    print("=" * 80)
    print("fc_databaseIGHG、IGKCIGLC")
    print("=" * 80)
    
    species_list = ["human", "mouse", "dog"]
    species_map = {
        "human": "Homo_sapiens",
        "mouse": "Mus_musculus",
        "dog": "Canis_lupus_familiaris"
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
        
        results = {
            "species": species,
            "ighg": {},
            "igkc": {},
            "iglc": {}
        }
        
        # 1. IGHG
        print(f"\n[1] IGHG（）")
        print("-" * 80)
        
        ighg_file = species_dir / f"IGHC_{species}.fasta"
        if ighg_file.exists():
            ighg_seqs = load_fasta(ighg_file)
            print(f"   {len(ighg_seqs)} IGHG")
            
            # Fc
            fc_seqs = extract_fc_from_ighg(ighg_seqs, species)
            print(f"   {len(fc_seqs)} IgGFc")
            
            # UniProt
            uniprot_fc = load_uniprot_fc(species_map[species])
            print(f"  UniProt {len(uniprot_fc)} IgGFc")
            
            for igg_type, fc_seq in fc_seqs.items():
                print(f"\n  IgG: {igg_type}")
                validation = validate_sequence(fc_seq, "IGHG")
                print(f"    : {validation['length']} aa")
                print(f"    : {'OK' if validation['is_valid'] else 'FAIL'}")
                if validation['has_unknown']:
                    print(f"    :  (X)")
                if validation['has_stop']:
                    print(f"    :  (*)")
                
                # UniProt
                uniprot_key = igg_type.replace("IgG", "IgG")
                if uniprot_key in uniprot_fc:
                    comparison = compare_sequences(
                        fc_seq, uniprot_fc[uniprot_key],
                        f"fc_database_{igg_type}", f"uniprot_{uniprot_key}"
                    )
                    print(f"    UniProt:")
                    print(f"      : {'YES - ' if comparison['match'] else 'NO - '}")
                    print(f"      : {comparison['similarity']:.2%}")
                    print(f"      : {comparison['length_diff']} aa")
                    if comparison['differences']:
                        print(f"      （5）:")
                        for diff in comparison['differences'][:5]:
                            print(f"         {diff['position']}: {diff['fc_database']} vs {diff['uniprot']}")
                    
                    results["ighg"][igg_type] = {
                        "validation": validation,
                        "comparison": comparison
                    }
                else:
                    print(f"    : UniProt {uniprot_key} ")
                    results["ighg"][igg_type] = {
                        "validation": validation,
                        "comparison": None
                    }
        else:
            print(f"  [WARN] : {ighg_file}")
        
        # 2. IGKC
        print(f"\n[2] IGKC（κ）")
        print("-" * 80)
        
        igkc_file = species_dir / f"IGKC_{species}.fasta"
        if igkc_file.exists():
            igkc_seqs = load_fasta(igkc_file)
            print(f"   {len(igkc_seqs)} IGKC")
            
            for header, seq in list(igkc_seqs.items())[:5]:  # 5
                validation = validate_sequence(seq, "IGKC")
                print(f"  {header[:50]}...")
                print(f"    : {validation['length']} aa")
                print(f"    : {'OK' if validation['is_valid'] else 'FAIL'}")
                
                results["igkc"][header] = validation
        else:
            print(f"  [WARN] : {igkc_file}")
        
        # 3. IGLC
        print(f"\n[3] IGLC（λ）")
        print("-" * 80)
        
        iglc_file = species_dir / f"IGLC_{species}.fasta"
        if iglc_file.exists():
            iglc_seqs = load_fasta(iglc_file)
            print(f"   {len(iglc_seqs)} IGLC")
            
            for header, seq in list(iglc_seqs.items())[:5]:  # 5
                validation = validate_sequence(seq, "IGLC")
                print(f"  {header[:50]}...")
                print(f"    : {validation['length']} aa")
                print(f"    : {'OK' if validation['is_valid'] else 'FAIL'}")
                
                results["iglc"][header] = validation
        else:
            print(f"  [WARN] : {iglc_file}")
        
        all_results[species] = results
    
    # 
    report_file = FC_DATABASE_DIR / "validation_report.json"
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

