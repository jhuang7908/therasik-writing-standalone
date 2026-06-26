#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" build_vhh_variants """

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh.vhh_scaffold_match_and_craft import match_vhh_to_human_fr, build_vhh_variants
import json

# EGFR 7D12 VHH 
seq = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"

print("=" * 80)
print("Testing build_vhh_variants function")
print("=" * 80)

# 1. 
print("\n[Step 1] Running match_vhh_to_human_fr...")
result = match_vhh_to_human_fr(
    seq,
    index_path="core/scaffolds/human_vhh_fr_index.json",
    fr_identity_min=0.60,
    hallmark_min=0.50
)

print(f"  Success: {result['success']}")
print(f"  Candidates: {len(result.get('candidates', []))}")

# 2.  variants
print("\n[Step 2] Building variants...")
variants = build_vhh_variants(seq, result)

print(f"\n✅ Generated {len(variants)} variants:")
for i, v in enumerate(variants, 1):
    print(f"\n  Variant {i}:")
    print(f"    ID: {v['variant_id']}")
    print(f"    Kind: {v['kind']}")
    print(f"    Label: {v['label']}")
    print(f"    Sequence length: {len(v['sequence'])} aa")
    print(f"    Scaffold ID: {v['scaffold_id']}")
    if v['matching_scores']:
        print(f"    Total Score: {v['matching_scores'].get('total_score', 0):.3f}")

# 3. 
output_file = PROJECT_ROOT / "projects" / "EGFR_7D12_VHH" / "vhh_variants.json"
output_file.parent.mkdir(parents=True, exist_ok=True)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump({
        "input_sequence": seq,
        "variants": variants
    }, f, indent=2, ensure_ascii=False)

print(f"\n[INFO] Variants saved to: {output_file}")
print("=" * 80)
















