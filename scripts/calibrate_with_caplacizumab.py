#!/usr/bin/env python3
"""
CaplacizumabIEDB
- Caplacizumab VHH（）
- IEDB
-  vs  (3-7% ADA)
- 
"""

import json
from pathlib import Path

print("="*80)
print("CaplacizumabIEDB")
print("="*80)

# =============================================================================
# Caplacizumab VHH（）
# =============================================================================

print("\n>>> Caplacizumab...")

# CaplacizumabVHH，VHHlinker
# VHH（）

CAPLACIZUMAB_VHH = """
EVQLVESGGGLVQAGGSLRLSCAASGRTFSSYAMGWFRQAPGKEREFVAAISWSGGSTY
YADSVKGRFTISRDNAKNTVYLQMNSLKPEDTAVYYCAAVRLSIDPWGQGTQVTVSS
"""

# （）
caplacizumab_seq = CAPLACIZUMAB_VHH.replace('\n', '').replace(' ', '').strip()

print(f"Caplacizumab VHH: {len(caplacizumab_seq)} aa")
print(f": {caplacizumab_seq}")

# 
if len(caplacizumab_seq) < 100 or len(caplacizumab_seq) > 130:
    print("⚠️  ：，")

# =============================================================================
# 7D12
# =============================================================================

print("\n" + "="*80)
print("Caplacizumab vs 7D12")
print("="*80)

# Load 7D12 sequence
with open("output/7d12_verified_run/checkpoint_04_humanized_sequences_CDR_GRAFTED.json") as f:
    d7d12_data = json.load(f)

d7d12_seq = d7d12_data['original_sequence']

print(f"\n7D12: {len(d7d12_seq)} aa")
print(f"Caplacizumab: {len(caplacizumab_seq)} aa")

# 
def calculate_identity(seq1, seq2):
    """"""
    min_len = min(len(seq1), len(seq2))
    matches = sum(1 for i in range(min_len) if seq1[i] == seq2[i])
    return matches / min_len * 100

identity = calculate_identity(d7d12_seq, caplacizumab_seq)
print(f"\n: {identity:.1f}%")

# =============================================================================
# 
# =============================================================================

print("\n" + "="*80)
print("VHH")
print("="*80)

def count_residues(seq, residues):
    """"""
    return sum(seq.count(r) for r in residues)

features = {
    " (M+W)": ['M', 'W'],
    " (N)": ['N'],
    " (D)": ['D'],
    " (F+Y+W)": ['F', 'Y', 'W'],
    " (I+L+V)": ['I', 'L', 'V'],
    " (R+K)": ['R', 'K'],
    " (D+E)": ['D', 'E']
}

print(f"\n{'':<20} {'7D12':<10} {'Caplacizumab':<15}")
print("-"*50)

for feature_name, residues in features.items():
    d7d12_count = count_residues(d7d12_seq, residues)
    capla_count = count_residues(caplacizumab_seq, residues)
    print(f"{feature_name:<20} {d7d12_count:<10} {capla_count:<15}")

# =============================================================================
# CaplacizumabIEDB
# =============================================================================

print("\n" + "="*80)
print("IEDB")
print("="*80)

caplacizumab_data = {
    "name": "Caplacizumab",
    "target": "von Willebrand Factor (vWF)",
    "sequence": caplacizumab_seq,
    "length": len(caplacizumab_seq),
    "humanized": False,
    "clinical_data": {
        "ada_rate": "3-7%",
        "nab_rate": "<3%",
        "approval": "FDA 2018, EMA 2018",
        "indication": "Acquired thrombotic thrombocytopenic purpura (aTTP)",
        "trial": "HERCULES Phase 3",
        "sample_size": "145 patients"
    },
    "note": "VHH (2x VHH + linker)，VHH"
}

# 
output_file = Path("output/7D12/caplacizumab_reference.json")
with open(output_file, 'w') as f:
    json.dump(caplacizumab_data, f, indent=2)

print(f"✓ Caplacizumab: {output_file}")

# =============================================================================
# 
# =============================================================================

print("\n" + "="*80)
print("：IEDB")
print("="*80)

print("""
IEDB：

1. CaplacizumabIEDB MHC-II
2. （27HLA，15-mer）
3. ：
   - ADA: 3-7% ()
   - IEDB: ? ()
   
4. ：
   - IEDBCaplacizumabX
   - ADA3-7%
   - ：IEDBY
   
5. 7D12：
   - 7D1221FR
   -  = 21 / Y
   - ADA

IEDB...
""")

print("\n✓ ，IEDB")















