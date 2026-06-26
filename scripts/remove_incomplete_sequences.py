#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
remove_incomplete_sequences.py


"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Set


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FC_AA_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa"

# （）
SEQUENCES_TO_REMOVE = {
    "human": {
        "IGHC": [
            "Human_IGHG3_CH1_IGHG3*02_11aa",
            "Human_IGHG3_CH2_IGHG3*02_17aa",
            "Human_IGHG3_CH3_IGHG3*02_11aa",
            "Human_IGHG?_CH3_IGHGP*02_26aa",  # 
        ],
        "IGLC": [
            "Human_IGLC*04_12aa",  # 
        ]
    },
    "cat": {
        "IGHC": [],  # ，
        "IGLC": []   # ，
    }
}

# 
PLACEHOLDER_FILES = [
    "cat/IGHC_cat.fasta",
    "cat/IGLC_cat.fasta",
]


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


def save_fasta(path: Path, seqs: Dict[str, str]):
    """FASTA"""
    with path.open('w', encoding='utf-8') as f:
        for header, seq in seqs.items():
            f.write(f">{header}\n")
            for i in range(0, len(seq), 80):
                f.write(f"{seq[i:i+80]}\n")


def is_placeholder_file(path: Path) -> bool:
    """"""
    if not path.exists():
        return False
    
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        # 
        placeholder_keywords = [
            "PLACEHOLDER",
            "NEEDS_VERIFICATION",
            "NOTE: This is a placeholder",
            "# NOTE: This is a placeholder"
        ]
        
        for keyword in placeholder_keywords:
            if keyword in content:
                return True
        
        # ，
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        has_sequence = False
        for line in lines:
            if line.startswith(">") and not line.startswith("#"):
                # 
                continue
            elif not line.startswith("#") and not line.startswith(">"):
                # 、header，
                if len(line) > 10:  # 10
                    has_sequence = True
                    break
        
        return not has_sequence
    except Exception as e:
        print(f"[WARN]  {path}: {e}")
        return False


def main():
    print("=" * 80)
    print("")
    print("=" * 80)
    
    removed_count = 0
    removed_files = []
    
    # 1. 
    print(f"\n[1] ")
    print("-" * 80)
    
    for species, chains in SEQUENCES_TO_REMOVE.items():
        species_path = FC_AA_DIR / species
        if not species_path.exists():
            continue
        
        for chain_type, headers_to_remove in chains.items():
            if not headers_to_remove:
                continue
            
            chain_file = species_path / f"{chain_type}_{species}.fasta"
            if not chain_file.exists():
                continue
            
            print(f"\n  : {species}/{chain_type}")
            seqs = load_fasta(chain_file)
            original_count = len(seqs)
            
            # 
            for header in headers_to_remove:
                if header in seqs:
                    del seqs[header]
                    removed_count += 1
                    print(f"    [] {header}")
            
            # 
            if len(seqs) < original_count:
                save_fasta(chain_file, seqs)
                print(f"    []  {len(seqs)} （ {original_count - len(seqs)} ）")
    
    # 2. 
    print(f"\n[2] ")
    print("-" * 80)
    
    for file_path in PLACEHOLDER_FILES:
        full_path = FC_AA_DIR / file_path
        if full_path.exists():
            if is_placeholder_file(full_path):
                try:
                    full_path.unlink()
                    removed_files.append(str(full_path))
                    print(f"  [] {file_path}")
                except Exception as e:
                    print(f"  []  {file_path}: {e}")
            else:
                print(f"  [] {file_path} ")
        else:
            print(f"  [] {file_path} ")
    
    # 3. 
    print(f"\n[3] ")
    print("-" * 80)
    
    for species_dir in ["human", "mouse", "dog", "cat"]:
        species_path = FC_AA_DIR / species_dir
        if not species_path.exists():
            continue
        
        for chain_type in ["IGHC", "IGKC", "IGLC"]:
            chain_file = species_path / f"{chain_type}_{species_dir}.fasta"
            if chain_file.exists() and is_placeholder_file(chain_file):
                try:
                    chain_file.unlink()
                    removed_files.append(str(chain_file))
                    print(f"  [] {species_dir}/{chain_type}_{species_dir}.fasta")
                except Exception as e:
                    print(f"  []  {chain_file}: {e}")
    
    # 
    removal_log = {
        "removed_sequences": removed_count,
        "removed_files": removed_files,
        "timestamp": str(Path(__file__).stat().st_mtime)
    }
    
    log_file = FC_AA_DIR / "removal_log.json"
    log_file.write_text(
        json.dumps(removal_log, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    
    print(f"\n{'='*80}")
    print("！")
    print(f"  : {removed_count}")
    print(f"  : {len(removed_files)}")
    print(f"  : {log_file}")
    print(f"{'='*80}")
    
    return 0


if __name__ == "__main__":
    exit(main())


















