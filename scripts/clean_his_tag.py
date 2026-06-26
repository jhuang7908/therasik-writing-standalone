#!/usr/bin/env python3
"""
VHHHis
"""
from pathlib import Path
import re

def clean_his_tag(sequence: str) -> str:
    """His"""
    # His
    patterns = [
        r'SHHHHHH$',  # 8Z8V
        r'HHHHHH$',
        r'HHHHHHH$',
        r'SHHHHH$',
        r'LEHHHHHH$',  # 
    ]
    
    cleaned = sequence
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    return cleaned

def clean_fasta_file(input_file: str, output_file: str):
    """FASTA"""
    input_path = Path(input_file)
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(input_path, 'r', encoding='utf-8') as f_in:
        with open(output_path, 'w', encoding='utf-8') as f_out:
            current_header = ""
            for line in f_in:
                if line.startswith('>'):
                    current_header = line.strip()
                    f_out.write(f"{current_header}\n")
                else:
                    sequence = line.strip()
                    cleaned = clean_his_tag(sequence)
                    if cleaned != sequence:
                        print(f": {len(sequence)} -> {len(cleaned)} aa")
                    f_out.write(f"{cleaned}\n")
    
    print(f"✅ : {output_path}")

if __name__ == '__main__':
    input_file = "projects/anti_HSA_VHH/input/anti_hsa_vhh_from_pdb.fasta"
    output_file = "projects/anti_HSA_VHH/input/anti_hsa_vhh_from_pdb_cleaned.fasta"
    
    clean_fasta_file(input_file, output_file)
    print("\n！。")
