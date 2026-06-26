#!/usr/bin/env python3
"""
Create correct S3 based on real S2 vs Alpaca differences
"""

import json
from pathlib import Path

ALPACA_7D12 = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"

def create_s3():
    json_path = Path("output/7d12_verified_run/checkpoint_04_humanized_sequences_FINAL.json")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    s2_sequence = data['strategy_2']['sequence']
    s2_mutations = [int(x) if isinstance(x, str) else x for x in data['strategy_2']['back_mutations']]
    
    print("="*80)
    print("CREATING S3 (CONSERVATIVE) FROM S2")
    print("="*80)
    
    # S3 additional mutations based on analysis:
    # - Position 73: High priority (Vernier-like, close to CDR3)
    # - Positions 72, 74, 77, 85: Medium priority (FR3 structural)
    s3_additional = [
        73,  # A (Vernier tuning, FR3)
        72,  # D (FR3 structural, near CDR3)
        74,  # R (FR3 structural)
        77,  # V (FR3 structural)
        85,  # K (FR3 structural)
    ]
    
    # Create S3 sequence
    s3_sequence = list(s2_sequence)
    
    print(f"\nS2: {s2_sequence}")
    print(f"S2 mutations: {s2_mutations} (count: {len(s2_mutations)})\n")
    
    print("Applying S3 additional back-mutations:")
    print(f"{'Position':<10} {'S2':<10} {'→':<5} {'Alpaca':<10} {'Note'}")
    print("-" * 60)
    
    for pos in s3_additional:
        s2_aa = s3_sequence[pos-1]
        alpaca_aa = ALPACA_7D12[pos-1]
        s3_sequence[pos-1] = alpaca_aa
        
        if pos == 73:
            note = "Vernier tuning (HIGH priority)"
        else:
            note = "FR3 structural (MEDIUM priority)"
        
        print(f"{pos:<10} {s2_aa:<10} {'→':<5} {alpaca_aa:<10} {note}")
    
    s3_sequence_str = ''.join(s3_sequence)
    s3_all_mutations = sorted(s2_mutations + s3_additional)
    
    print(f"\n✅ S3 COMPLETE:")
    print(f"   Sequence: {s3_sequence_str}")
    print(f"   Total mutations: {len(s3_all_mutations)}")
    print(f"   Humanization: {100 * (117 - len(s3_all_mutations)) / 117:.1f}%")
    
    # Verify
    assert len(s3_sequence_str) == 117
    
    differences = sum(1 for a, b in zip(s2_sequence, s3_sequence_str) if a != b)
    print(f"   Differences from S2: {differences}")
    assert differences == len(s3_additional)
    
    # Update JSON
    data['strategy_3'] = {
        'name': 'Conservative (Maximum Stability)',
        'sequence': s3_sequence_str,
        'length': 117,
        'back_mutations': s3_all_mutations,
        'back_mutation_count': len(s3_all_mutations),
        'design_principle': 'S2 + additional FR3 structural/Vernier positions (72,73,74,77,85) for maximum functional retention',
        'humanization_percent': round(100 * (117 - len(s3_all_mutations)) / 117, 1),
        'additional_vs_s2': s3_additional
    }
    
    data['note_s3_v3'] = "S3 correctly built: S2 + 5 FR3 positions (1 Vernier-like + 4 structural)"
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved to: {json_path}")
    
    # Print summary
    print("\n" + "="*80)
    print("THREE-STRATEGY GRADIENT")
    print("="*80)
    print(f"S1: {data['strategy_1']['back_mutation_count']} mutations → "
          f"{100 * (117 - data['strategy_1']['back_mutation_count']) / 117:.1f}% humanized (Max-Human)")
    print(f"S2: {data['strategy_2']['back_mutation_count']} mutations → "
          f"{100 * (117 - data['strategy_2']['back_mutation_count']) / 117:.1f}% humanized (Surface Reshaping)")
    print(f"S3: {len(s3_all_mutations)} mutations → "
          f"{100 * (117 - len(s3_all_mutations)) / 117:.1f}% humanized (Conservative)")
    
    print(f"\n✅ Gradient: 4 → 8 → {len(s3_all_mutations)}")
    print(f"✅ S3 adds {len(s3_additional)} FR3 positions beyond S2")
    
    return data

if __name__ == "__main__":
    create_s3()















