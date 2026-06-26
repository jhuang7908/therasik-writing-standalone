#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 VHH v1 FASTA 
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main():
    fasta_a = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "exports" / "vhh_special_fr_templates_v1.fasta"
    fasta_b = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "exports" / "vhh_scaffold_library_v1.fasta"
    tsv = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "exports" / "vhh_special_fr_templates_v1.tsv"
    
    print("=" * 80)
    print(" VHH v1 FASTA ")
    print("=" * 80)
    print()
    
    # 
    files_to_check = {
        "vhh_special_fr_templates_v1.fasta": fasta_a,
        "vhh_scaffold_library_v1.fasta": fasta_b,
        "vhh_special_fr_templates_v1.tsv": tsv,
    }
    
    all_exist = True
    for name, path in files_to_check.items():
        exists = path.exists()
        status = "✅" if exists else "❌"
        print(f"{status} {name}: {path}")
        if exists:
            size = path.stat().st_size
            print(f"    : {size} bytes")
        if not exists:
            all_exist = False
    
    print()
    
    # 
    if fasta_a.exists():
        with open(fasta_a, "r", encoding="utf-8") as f:
            count_a = sum(1 for line in f if line.startswith(">"))
        print(f"vhh_special_fr_templates_v1.fasta: {count_a} ")
    
    if fasta_b.exists():
        with open(fasta_b, "r", encoding="utf-8") as f:
            count_b = sum(1 for line in f if line.startswith(">"))
        print(f"vhh_scaffold_library_v1.fasta: {count_b} ")
    
    if tsv.exists():
        with open(tsv, "r", encoding="utf-8") as f:
            lines = f.readlines()
            count_tsv = len(lines) - 1  # header
        print(f"vhh_special_fr_templates_v1.tsv: {count_tsv} ")
    
    print()
    print("=" * 80)
    
    if all_exist and count_a == 82 and count_b == 264:
        print("✅ ！")
    else:
        print("❌ ！")

if __name__ == "__main__":
    main()










