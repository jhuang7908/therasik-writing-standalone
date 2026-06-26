#!/usr/bin/env python3
"""
S3：FR1/FR3
FR2alpaca + Vernier positions
"""

import json
from pathlib import Path

# Load data
with open("output/7d12_verified_run/checkpoint_03_mutation_classification.json") as f:
    classification = json.load(f)

with open("output/7d12_verified_run/checkpoint_04_humanized_sequences_CDR_GRAFTED.json") as f:
    sequences = json.load(f)

print("="*80)
print("S3")
print("="*80)

# S3：
# - FR1: （Human germline）
# - FR2: alpaca（Hallmarks + Vernier）
# - CDR1/CDR2: alpaca（）
# - FR3: ，Vernier Anchor (94)
# - CDR3+FR4: alpaca（）

print("\nS3：")
print("-"*80)
print("FR1 (Kabat 1-24):  Human germline")
print("FR2 (Kabat 32-47): Alpaca (，5Hallmarks)")
print("CDR1 (25-31):      Alpaca ()")
print("CDR2 (48-56):      Alpaca ()")
print("FR3 (57-93):       Human germline + Vernier Anchor 94")
print("CDR3 (94-117):     Alpaca ()")

# Correct S3 back-mutations
correct_s3_backmuts = []

for mut in classification["classified_mutations"]:
    pos = mut["kabat_position"]
    region = mut["region"]
    
    # FR2：（HallmarksVernier）
    if pos in ["28", "29", "30", "37", "44", "45", "47", "49"]:
        correct_s3_backmuts.append(pos)
    
    # FR3Vernier Anchor
    elif pos in ["94"]:
        correct_s3_backmuts.append(pos)

print(f"\nS3 back-mutations: {len(correct_s3_backmuts)}")
print(f": {correct_s3_backmuts}")

# 
print("\n" + "="*80)
print("S3 Back-mutations")
print("="*80)

for pos in correct_s3_backmuts:
    mut = next((m for m in classification["classified_mutations"] if m["kabat_position"] == pos), None)
    if mut:
        print(f"Kabat {pos:>3}: {mut['alpaca_aa']} (Alpaca) ← {mut['human_aa']} (Human) | "
              f"{mut['mutation_type']:<20} | {mut['rationale']}")

# S3
# human base，FR2+Vernier 94
alpaca_seq = sequences["original_sequence"]
human_base_template = "EVQLLESGGGLVQPGGSLRLSCAASGFWYNHSYAWVRQAPGKEREWVSAISGSGGSTYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"

# S3
# FR1 (1-24): Human
s3_corrected = list(human_base_template)

# CDR
cdr_positions = sequences["cdr_positions"]
for cdr_name, cdr_info in cdr_positions.items():
    start = cdr_info['start']
    end = cdr_info['end']
    cdr_seq = cdr_info['sequence']
    for i, aa in enumerate(cdr_seq):
        if start + i < len(s3_corrected):
            s3_corrected[start + i] = aa

# FR2 back-mutations (Kabat 28/29/30/37/44/45/47/49)
# alpaca
backmut_mapping = {
    28: 'W',  # Vernier-Anchor
    29: 'Y',  # Vernier-Anchor  
    30: 'N',  # Vernier-Tuning
    37: 'F',  # Hallmark
    44: 'E',  # Hallmark
    45: 'R',  # Hallmark
    47: 'G',  # Hallmark
    49: 'A',  # Vernier-Tuning
    94: 'A',  # Vernier-Anchor
}

# back-mutations（Kabatindex）
# ：
kabat_to_seqidx = {
    1: 0, 5: 4, 14: 13, 22: 21, 24: 23,
    28: 27, 29: 28, 30: 29,
    37: 36, 44: 43, 45: 44, 47: 46, 49: 48,
    73: 72, 74: 73, 75: 74, 78: 77,
    83: 82, 84: 83, 94: 93
}

for kabat_pos, alpaca_aa in backmut_mapping.items():
    if kabat_pos in kabat_to_seqidx:
        seq_idx = kabat_to_seqidx[kabat_pos]
        if seq_idx < len(s3_corrected):
            s3_corrected[seq_idx] = alpaca_aa

s3_corrected_seq = "".join(s3_corrected)

print("\n" + "="*80)
print("S3")
print("="*80)
print(f": {len(s3_corrected_seq)} aa")
print(f": {s3_corrected_seq}")

# CDR
print("\nCDR:")
for cdr_name, cdr_info in cdr_positions.items():
    start = cdr_info['start']
    end = cdr_info['end']
    expected = cdr_info['sequence']
    actual = s3_corrected_seq[start:end]
    status = "✓" if actual == expected else "✗"
    print(f"  {cdr_name}: {status} {actual}")

# 
corrected_data = {
    "timestamp": "2026-01-02",
    "note": "Corrected S3 strategy: FR1/FR3 humanized, FR2 fully alpaca, key Vernier retained",
    "strategy_3_corrected": {
        "name": "Conservative (FR2 Fully Alpaca)",
        "sequence": s3_corrected_seq,
        "length": len(s3_corrected_seq),
        "back_mutations": correct_s3_backmuts,
        "back_mutation_count": len(correct_s3_backmuts),
        "design_principle": {
            "FR1": "Human germline (fully humanized)",
            "FR2": "Alpaca (all Hallmarks + Vernier retained)",
            "CDR1": "Alpaca (preserved)",
            "CDR2": "Alpaca (preserved)",
            "FR3": "Human germline + Vernier Anchor 94",
            "CDR3": "Alpaca (preserved)"
        }
    }
}

output_file = Path("output/7d12_verified_run/checkpoint_04_S3_CORRECTED.json")
with open(output_file, 'w') as f:
    json.dump(corrected_data, f, indent=2)

print(f"\n✓ S3: {output_file}")

print("\n" + "="*80)
print("")
print("="*80)
print(f"S3: 20back-mutations (FR1/FR3)")
print(f"S3: {len(correct_s3_backmuts)}back-mutations (FR2+Vernier 94)")
print(f"\n：FR1/FR3，FR2alpaca")















