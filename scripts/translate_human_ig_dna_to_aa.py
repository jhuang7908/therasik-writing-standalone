#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
translate_human_ig_dna_to_aa.py

IGDNA

IG：
- IGHV (V)
- IGHD (D)
- IGHJ (J)
- IGKV (κV)
- IGKJ (κJ)
- IGLV (λV)
- IGLJ (λJ)

：
- FASTA（）
- JSON
"""

from __future__ import annotations

import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMGT_BASE_DIR = PROJECT_ROOT / "data" / "germlines" / "IMGT_V-" / "IMGT_V-QUEST_reference_directory"
HUMAN_IG_DIR = IMGT_BASE_DIR / "Homo_sapiens" / "IG"
OUTPUT_DIR = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa"


# 
CODON_TABLE = {
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
    # N（）
    'NNT': 'X', 'NNC': 'X', 'NNA': 'X', 'NNG': 'X',
    'TNT': 'X', 'TNC': 'X', 'TNA': 'X', 'TNG': 'X',
    'CNT': 'X', 'CNC': 'X', 'CNA': 'X', 'CNG': 'X',
    'ANT': 'X', 'ANC': 'X', 'ANA': 'X', 'ANG': 'X',
    'GNT': 'X', 'GNC': 'X', 'GNA': 'X', 'GNG': 'X',
}


def clean_dna_sequence(dna_seq: str) -> str:
    """
    DNA，、、
    """
    # 
    cleaned = ''.join(dna_seq.split())
    # （IMGT）
    cleaned = cleaned.replace('...', '').replace('..', '').replace('.', '')
    # 
    cleaned = cleaned.upper()
    # DNA（N）
    cleaned = ''.join(c for c in cleaned if c in 'ATCGN')
    return cleaned


def translate_dna_to_aa(dna_seq: str, remove_stop: bool = True) -> str:
    """
    DNA
    
    Args:
        dna_seq: DNA
        remove_stop: 
    
    Returns:
        
    """
    dna_seq = clean_dna_sequence(dna_seq)
    
    if len(dna_seq) < 3:
        return ""
    
    aa_seq = []
    for i in range(0, len(dna_seq) - 2, 3):
        codon = dna_seq[i:i+3]
        if len(codon) == 3:
            # N
            if 'N' in codon:
                aa = 'X'  # 
            else:
                aa = CODON_TABLE.get(codon, 'X')
            
            if aa == '*' and remove_stop:
                continue  # 
            aa_seq.append(aa)
    
    return ''.join(aa_seq)


def is_amino_acid_sequence(seq: str) -> bool:
    """
    
    
    ：
    - DNA： A, T, C, G, N（）
    - ：20（ACDEFGHIKLMNPQRSTVWY）（*X）
    
    ：
    1. T（），（E, F, H, I, K, L, M, P, Q, R, S, W, Y），DNA
    2. （E, F, H, I, K, L, M, P, Q, R, W, Y），
    """
    seq_clean = seq.upper().replace('-', '').replace('.', '').replace(' ', '').replace('...', '')
    if not seq_clean:
        return False
    
    # DNA：T（）
    # ：E, F, H, I, K, L, M, P, Q, R, W, Y DNA
    has_t = 'T' in seq_clean
    aa_specific = set("EFHIKLMNPQRWY")
    has_aa_specific = any(c in seq_clean for c in aa_specific)
    
    # T，DNA
    if has_t and not has_aa_specific:
        return False
    
    # ，
    if has_aa_specific:
        return True
    
    # ACGN，DNA
    if len(seq_clean) < 50 and all(c in "ACGN" for c in seq_clean):
        return False
    
    # ：，
    # ，ATCG，DNA
    dna_bases = set("ATCGN")
    dna_ratio = sum(1 for c in seq_clean if c in dna_bases) / len(seq_clean) if seq_clean else 0
    
    # 90%DNA，DNA
    if dna_ratio > 0.9:
        return False
    
    # 
    return True


def load_fasta(path: Path) -> Dict[str, str]:
    """
    FASTA
    
    Returns:
        {header: sequence}
    """
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


def process_ig_file(fasta_file: Path, seq_type: str) -> Tuple[Dict[str, str], int]:
    """
    IG FASTA
    
    Args:
        fasta_file: FASTA
        seq_type: （IGHV, IGHD）
    
    Returns:
        (, )
    """
    print(f"\n[INFO] ：{fasta_file.name}")
    
    if not fasta_file.exists():
        print(f"[WARN] ：{fasta_file}")
        return {}, 0
    
    seqs = load_fasta(fasta_file)
    print(f"[INFO]  {len(seqs)} ")
    
    aa_seqs = {}
    translated_count = 0
    
    for header, seq in seqs.items():
        # 
        if is_amino_acid_sequence(seq):
            # 
            cleaned_seq = seq.upper().replace('-', '').replace('.', '').replace(' ', '')
            aa_seqs[header] = cleaned_seq
        else:
            # 
            aa_seq = translate_dna_to_aa(seq)
            if aa_seq:
                aa_seqs[header] = aa_seq
                translated_count += 1
    
    print(f"[INFO]  {translated_count} ， {len(aa_seqs)} ")
    
    return aa_seqs, translated_count


def save_fasta(output_path: Path, seqs: Dict[str, str]):
    """FASTA"""
    with output_path.open('w', encoding='utf-8') as f:
        for header, seq in seqs.items():
            f.write(f">{header}\n")
            # 80
            for i in range(0, len(seq), 80):
                f.write(f"{seq[i:i+80]}\n")


def save_json(output_path: Path, data: dict):
    """JSON"""
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )


def main():
    parser = argparse.ArgumentParser(
        description="IGDNA"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help=f"（：{OUTPUT_DIR}）",
    )
    parser.add_argument(
        "--types",
        nargs="+",
        choices=["IGHV", "IGHD", "IGHJ", "IGKV", "IGKJ", "IGLV", "IGLJ", "all"],
        default=["all"],
        help="（：all）",
    )
    
    args = parser.parse_args()
    
    # 
    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 
    if not HUMAN_IG_DIR.exists():
        print(f"[ERROR] IG：{HUMAN_IG_DIR}")
        return 1
    
    # 
    all_types = ["IGHV", "IGHD", "IGHJ", "IGKV", "IGKJ", "IGLV", "IGLJ"]
    if "all" in args.types:
        types_to_process = all_types
    else:
        types_to_process = [t for t in args.types if t in all_types]
    
    print(f"[INFO] IG")
    print(f"[INFO] ：{HUMAN_IG_DIR}")
    print(f"[INFO] ：{output_dir}")
    print(f"[INFO] ：{', '.join(types_to_process)}")
    
    summary = {
        "species": "Homo_sapiens",
        "source_dir": str(HUMAN_IG_DIR),
        "output_dir": str(output_dir),
        "files": {},
        "total_sequences": 0,
        "total_translated": 0,
    }
    
    # 
    for seq_type in types_to_process:
        fasta_file = HUMAN_IG_DIR / f"{seq_type}.fasta"
        
        if not fasta_file.exists():
            print(f"[WARN] ：{fasta_file}")
            continue
        
        # 
        aa_seqs, translated_count = process_ig_file(fasta_file, seq_type)
        
        if not aa_seqs:
            print(f"[WARN] {seq_type} ")
            continue
        
        # FASTA
        output_fasta = output_dir / f"{seq_type}_aa.fasta"
        save_fasta(output_fasta, aa_seqs)
        print(f"[SAVED] FASTA：{output_fasta}")
        
        # JSON
        output_json = output_dir / f"{seq_type}_aa.json"
        json_data = {
            "sequence_type": seq_type,
            "species": "Homo_sapiens",
            "source_file": str(fasta_file),
            "count": len(aa_seqs),
            "translated_count": translated_count,
            "entries": [
                {
                    "id": header.split("|")[1] if "|" in header else header,
                    "raw_header": header,
                    "sequence_aa": seq,
                }
                for header, seq in aa_seqs.items()
            ],
        }
        save_json(output_json, json_data)
        print(f"[SAVED] JSON：{output_json}")
        
        # 
        summary["files"][seq_type] = {
            "count": len(aa_seqs),
            "translated_count": translated_count,
            "fasta_file": str(output_fasta),
            "json_file": str(output_json),
        }
        summary["total_sequences"] += len(aa_seqs)
        summary["total_translated"] += translated_count
    
    # 
    summary_file = output_dir / "human_ig_aa_summary.json"
    save_json(summary_file, summary)
    
    print(f"\n[SUCCESS] ！")
    print(f"[INFO]  {len(summary['files'])} ")
    print(f"[INFO] ：{summary['total_sequences']}")
    print(f"[INFO] ：{summary['total_translated']}")
    print(f"[INFO] ：{summary_file}")
    
    return 0


if __name__ == "__main__":
    exit(main())

