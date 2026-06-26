#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 IGHJ （raw， FR4）

 FASTA  IGHJ ， JSON 。
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 
GENETIC_CODE = {
    'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L',
    'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
    'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*',
    'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W',
    'CTT': 'L', 'CTC': 'L', 'CTA': 'L', 'CTG': 'L',
    'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
    'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q',
    'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
    'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M',
    'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',
    'AAT': 'N', 'AAC': 'N', 'AAA': 'K', 'AAG': 'K',
    'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
    'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V',
    'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',
    'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
    'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G',
}


def translate_dna_to_aa(dna_seq: str) -> str:
    """
     DNA （）
    
    Args:
        dna_seq: DNA （）
    
    Returns:
        
    """
    dna_clean = dna_seq.upper().replace(" ", "").replace("\n", "").replace("\r", "")
    aa_seq = ""
    
    for i in range(0, len(dna_clean) - 2, 3):
        codon = dna_clean[i:i+3]
        if len(codon) == 3:
            aa = GENETIC_CODE.get(codon, 'X')
            if aa == '*':  # 
                break
            aa_seq += aa
    
    return aa_seq


def is_dna_sequence(seq: str) -> bool:
    """
     DNA（）
    
    ： A, T, G, C, N  3 ， DNA
    """
    seq_clean = seq.upper().replace(" ", "").replace("\n", "").replace("\r", "")
    dna_chars = set('ATGCUN')
    aa_chars = set('ACDEFGHIKLMNPQRSTVWYXZ*')
    
    # ， DNA
    if any(c in aa_chars for c in seq_clean):
        return False
    
    #  DNA  3 ， DNA
    if all(c in dna_chars for c in seq_clean) and len(seq_clean) % 3 == 0:
        return True
    
    return False


def parse_ighj_id(header: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
     header  IGHJ ID
    
    ：
    - IGHJ4*01
    - J00256|IGHJ4*01|Homo sapiens|...
    - >IGHJ4*01
    
    Returns:
        (full_id, gene, allele)
    """
    #  > 
    header_clean = header.lstrip(">").strip()
    
    #  IGHJ* 
    match = re.search(r'IGHJ(\d+)\*(\d+)', header_clean)
    if match:
        gene = f"IGHJ{match.group(1)}"
        allele = match.group(2)
        full_id = f"{gene}*{allele}"
        return full_id, gene, allele
    
    #  header ，
    if '|' in header_clean:
        parts = header_clean.split('|')
        for part in parts:
            match = re.search(r'IGHJ(\d+)\*(\d+)', part)
            if match:
                gene = f"IGHJ{match.group(1)}"
                allele = match.group(2)
                full_id = f"{gene}*{allele}"
                return full_id, gene, allele
    
    return None, None, None


def load_fasta(fasta_path: Path) -> Dict[str, str]:
    """
     FASTA 
    
    Returns:
        {sequence_id: sequence}
    """
    sequences = {}
    current_id = None
    current_seq = []
    
    with open(fasta_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith(">"):
                # 
                if current_id is not None:
                    sequences[current_id] = "".join(current_seq)
                
                #  ID
                header = line[1:]
                full_id, gene, allele = parse_ighj_id(header)
                
                if full_id:
                    current_id = full_id
                else:
                    # ， header  50  ID
                    current_id = header.split()[0] if header.split() else header[:50]
                    print(f"  ⚠️  :  ID，: {current_id}")
                
                current_seq = []
            else:
                current_seq.append(line)
        
        # 
        if current_id is not None:
            sequences[current_id] = "".join(current_seq)
    
    return sequences


def process_sequences(sequences: Dict[str, str]) -> Dict[str, Dict[str, str]]:
    """
    ： DNA ， AA 
    
    Returns:
        {sequence_id: {"gene": ..., "allele": ..., "aa": ...}}
    """
    result = {}
    
    for seq_id, seq in sequences.items():
        #  gene  allele
        match = re.match(r'IGHJ(\d+)\*(\d+)', seq_id)
        if match:
            gene = f"IGHJ{match.group(1)}"
            allele = match.group(2)
        else:
            # ， ID 
            gene = "IGHJ"
            allele = "unknown"
            print(f"  ⚠️  :  {seq_id}  gene/allele")
        
        #  DNA 
        if is_dna_sequence(seq):
            aa_seq = translate_dna_to_aa(seq)
            if not aa_seq:
                print(f"  ⚠️  : {seq_id} DNA ，")
                continue
        else:
            # 
            aa_seq = seq.upper().replace(" ", "").replace("\n", "").replace("\r", "")
        
        result[seq_id] = {
            "gene": gene,
            "allele": allele,
            "aa": aa_seq,
        }
    
    return result


def check_non_standard_aa(aa_seq: str) -> bool:
    """
    （ X、*）
    
    Returns:
        True if contains non-standard characters
    """
    standard_aa = set('ACDEFGHIKLMNPQRSTVWY')
    return any(c not in standard_aa for c in aa_seq.upper())


def main():
    parser = argparse.ArgumentParser(
        description=" IGHJ （raw， FR4）"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "IGHJ_aa.fasta",
        help=" FASTA （: data/germlines/human_ig_aa/IGHJ_aa.fasta）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "ighj_aa_raw.json",
        help=" JSON （: data/ighj_aa_raw.json）",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" IGHJ （raw）")
    print("=" * 80)
    print()
    
    # 
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path
    
    if not input_path.exists():
        print(f"❌ : {input_path}")
        return
    
    print(f"[1/4]  FASTA : {input_path}")
    sequences = load_fasta(input_path)
    print(f"  ✅  {len(sequences)} ")
    print()
    
    print(f"[2/4] （DNA  / AA ）...")
    processed = process_sequences(sequences)
    print(f"  ✅ : {len(processed)} ")
    print()
    
    print(f"[3/4] ...")
    aa_lengths = [len(entry["aa"]) for entry in processed.values()]
    
    if aa_lengths:
        min_len = min(aa_lengths)
        max_len = max(aa_lengths)
        median_len = statistics.median(aa_lengths)
        
        print(f"  : {len(processed)}")
        print(f"  AA : min={min_len}, median={median_len:.1f}, max={max_len}")
        
        # 
        non_standard_count = 0
        non_standard_ids = []
        for seq_id, entry in processed.items():
            if check_non_standard_aa(entry["aa"]):
                non_standard_count += 1
                non_standard_ids.append(seq_id)
        
        if non_standard_count > 0:
            print(f"  ⚠️  : {non_standard_count} ")
            print(f"     : {', '.join(non_standard_ids[:5])}")
        else:
            print(f"  ✅ ")
    else:
        print("  ⚠️  ")
    
    print()
    
    print(f"[4/4]  JSON : {args.output}")
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)
    
    print(f"  ✅ : {output_path}")
    print()
    
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()













