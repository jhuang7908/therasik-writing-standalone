#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
translate_fc_dna_to_aa.py

Fc（）DNA

：
1. FASTAFc DNA
2. UniProtFc（DNA）

：
-  (Mus_musculus)
-  (Rattus_norvegicus)
-  (Vicugna_pacos)
-  (Oryctolagus_cuniculus)
-  (Felis_catus)
-  (Bos_taurus)
-  (Chondrichthyes)
-  (Canis_lupus_familiaris)
-  (Homo_sapiens)
"""

from __future__ import annotations

import json
import argparse
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa"

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
}

# UniProtIgG FcUniProt ID（）
# ：
UNIPROT_FC_IDS = {
    "Mus_musculus": {
        "IgG1": "P01868",  # ID，
        "IgG2a": "P01863",
        "IgG2b": "P01867",
        "IgG3": "P03987",
    },
    "Rattus_norvegicus": {
        "IgG1": "P20760",
        "IgG2a": "P20761",
        "IgG2b": "P20762",
        "IgG2c": "P20763",
    },
    "Oryctolagus_cuniculus": {
        "IgG": "P01870",
    },
    "Bos_taurus": {
        "IgG1": "P01811",
        "IgG2": "P01812",
    },
    "Canis_lupus_familiaris": {
        "IgG": "P01820",
    },
    "Felis_catus": {
        "IgG": "P01821",
    },
}


def clean_dna_sequence(dna_seq: str) -> str:
    """DNA"""
    cleaned = ''.join(dna_seq.split())
    cleaned = cleaned.replace('...', '').replace('..', '').replace('.', '')
    cleaned = cleaned.upper()
    cleaned = ''.join(c for c in cleaned if c in 'ATCGN')
    return cleaned


def translate_dna_to_aa(dna_seq: str, remove_stop: bool = True) -> str:
    """DNA"""
    dna_seq = clean_dna_sequence(dna_seq)
    
    if len(dna_seq) < 3:
        return ""
    
    aa_seq = []
    for i in range(0, len(dna_seq) - 2, 3):
        codon = dna_seq[i:i+3]
        if len(codon) == 3:
            if 'N' in codon:
                aa = 'X'
            else:
                aa = CODON_TABLE.get(codon, 'X')
            
            if aa == '*' and remove_stop:
                continue
            aa_seq.append(aa)
    
    return ''.join(aa_seq)


def is_amino_acid_sequence(seq: str) -> bool:
    """"""
    seq_clean = seq.upper().replace('-', '').replace('.', '').replace(' ', '').replace('...', '')
    if not seq_clean:
        return False
    
    has_t = 'T' in seq_clean
    aa_specific = set("EFHIKLMNPQRWY")
    has_aa_specific = any(c in seq_clean for c in aa_specific)
    
    if has_t and not has_aa_specific:
        return False
    
    if has_aa_specific:
        return True
    
    if len(seq_clean) < 50 and all(c in "ACGN" for c in seq_clean):
        return False
    
    dna_bases = set("ATCGN")
    dna_ratio = sum(1 for c in seq_clean if c in dna_bases) / len(seq_clean) if seq_clean else 0
    
    if dna_ratio > 0.9:
        return False
    
    return True


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


def get_uniprot_sequence(uniprot_id: str) -> Optional[str]:
    """UniProt"""
    try:
        url = f"https://www.uniprot.org/uniprot/{uniprot_id}.fasta"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            sequence = ''.join(lines[1:])  # header
            return sequence
    except Exception as e:
        print(f"[WARN] UniProt {uniprot_id}: {e}")
    return None


def process_fc_file(fasta_file: Path, species: str) -> Tuple[Dict[str, str], int]:
    """Fc FASTA"""
    print(f"\n[INFO] ：{fasta_file.name}")
    
    if not fasta_file.exists():
        print(f"[WARN] ：{fasta_file}")
        return {}, 0
    
    seqs = load_fasta(fasta_file)
    print(f"[INFO]  {len(seqs)} ")
    
    aa_seqs = {}
    translated_count = 0
    
    for header, seq in seqs.items():
        if is_amino_acid_sequence(seq):
            cleaned_seq = seq.upper().replace('-', '').replace('.', '').replace(' ', '')
            aa_seqs[header] = cleaned_seq
        else:
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
        description="Fc（）DNA"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        help="Fc DNAFASTA",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        help="Fc DNAFASTA",
    )
    parser.add_argument(
        "--species",
        type=str,
        help="（UniProt，）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help=f"（：{OUTPUT_DIR}）",
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_results = {}
    
    # 
    if args.input_file:
        input_file = Path(args.input_file)
        species = args.species or "unknown"
        aa_seqs, translated_count = process_fc_file(input_file, species)
        
        if aa_seqs:
            output_fasta = output_dir / f"{species}_fc_aa.fasta"
            save_fasta(output_fasta, aa_seqs)
            
            output_json = output_dir / f"{species}_fc_aa.json"
            json_data = {
                "species": species,
                "source_file": str(input_file),
                "count": len(aa_seqs),
                "translated_count": translated_count,
                "entries": [
                    {
                        "id": header.split("|")[0] if "|" in header else header,
                        "raw_header": header,
                        "sequence_aa": seq,
                    }
                    for header, seq in aa_seqs.items()
                ],
            }
            save_json(output_json, json_data)
            all_results[species] = json_data
    
    elif args.input_dir:
        input_dir = Path(args.input_dir)
        for fasta_file in input_dir.glob("*.fasta"):
            species = args.species or fasta_file.stem
            aa_seqs, translated_count = process_fc_file(fasta_file, species)
            
            if aa_seqs:
                output_fasta = output_dir / f"{species}_fc_aa.fasta"
                save_fasta(output_fasta, aa_seqs)
                
                output_json = output_dir / f"{species}_fc_aa.json"
                json_data = {
                    "species": species,
                    "source_file": str(fasta_file),
                    "count": len(aa_seqs),
                    "translated_count": translated_count,
                    "entries": [
                        {
                            "id": header.split("|")[0] if "|" in header else header,
                            "raw_header": header,
                            "sequence_aa": seq,
                        }
                        for header, seq in aa_seqs.items()
                    ],
                }
                save_json(output_json, json_data)
                all_results[species] = json_data
    
    else:
        print("[INFO] ")
        print("[INFO] ：FcIMGT")
        print("[INFO] Fc DNAFASTA，--input-dir")
        print("\n[INFO] ：")
        print("  python scripts/translate_fc_dna_to_aa.py --input-file fc_dna.fasta --species mouse")
        print("  python scripts/translate_fc_dna_to_aa.py --input-dir fc_dna_dir/ --species mouse")
        return 1
    
    # 
    if all_results:
        summary_file = output_dir / "fc_aa_summary.json"
        summary = {
            "total_species": len(all_results),
            "total_sequences": sum(r["count"] for r in all_results.values()),
            "total_translated": sum(r["translated_count"] for r in all_results.values()),
            "species": all_results,
        }
        save_json(summary_file, summary)
        
        print(f"\n[SUCCESS] ！")
        print(f"[INFO]  {len(all_results)} ")
        print(f"[INFO] ：{summary['total_sequences']}")
        print(f"[INFO] ：{summary['total_translated']}")
        print(f"[INFO] ：{summary_file}")
    
    return 0


if __name__ == "__main__":
    exit(main())


















