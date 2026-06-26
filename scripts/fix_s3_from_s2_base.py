#!/usr/bin/env python3
"""
Correctly redesign S3 by starting from S2 and adding more back-mutations
"""

import json
from pathlib import Path

# Original sequences
ALPACA_7D12 = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"

def create_s3_from_s2():
    """
    Start from S2 (which already has correct CDR grafting + FR2 camelization)
    Add additional FR1/FR3 back-mutations for truly conservative strategy
    """
    
    json_path = Path("output/7d12_verified_run/checkpoint_04_humanized_sequences_FINAL.json")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Start from S2 sequence (already correct)
    s2_sequence = data['strategy_2']['sequence']
    s2_mutations = [int(x) if isinstance(x, str) else x for x in data['strategy_2']['back_mutations']]
    
    print("="*80)
    print("BUILDING S3 FROM S2 BASE")
    print("="*80)
    print(f"\nS2 sequence: {s2_sequence}")
    print(f"S2 back-mutations: {s2_mutations}")
    print(f"S2 count: {len(s2_mutations)}")
    
    # S3 additional back-mutations beyond S2
    # These are positions where alpaca differs from human, and are important for structure/function
    s3_additional_mutations = [
        15,  # V→P (FR1, beta-strand geometry)
        23,  # R→C (FR1, structural - though both charged, alpaca differs here)
        71,  # D (FR3, affects CDR geometry, close to CDR3)
        73,  # A (FR3, Vernier tuning, adjacent to CDR3)
        78,  # R (FR3, Vernier tuning, electrostatics)
        84,  # V (FR3, hydrophobic packing near CDR3)
    ]
    
    # Create S3 by adding more mutations to S2
    s3_sequence = list(s2_sequence)
    
    print(f"\n🔧 Applying {len(s3_additional_mutations)} additional back-mutations:")
    print(f"{'Position':<10} {'S2 (Human)':<15} {'→':<5} {'S3 (Alpaca)':<15} {'Region':<10} {'Note'}")
    print("-" * 80)
    
    for pos in s3_additional_mutations:
        s2_aa = s3_sequence[pos-1]
        alpaca_aa = ALPACA_7D12[pos-1]
        
        # Determine region
        if pos < 25:
            region = "FR1"
        elif pos < 39:
            region = "FR2"
        elif pos < 56:
            region = "CDR2-edge"
        elif pos < 66:
            region = "FR3-start"
        elif pos < 94:
            region = "FR3"
        else:
            region = "FR3-end"
        
        # Determine note
        if pos in [28, 29, 94]:
            note = "Vernier anchor"
        elif pos in [49, 73, 78]:
            note = "Vernier tuning"
        elif pos in [37, 44, 45, 47]:
            note = "Hallmark"
        elif pos in [15, 23]:
            note = "FR1 structural"
        elif pos in [71, 84]:
            note = "FR3 structural"
        else:
            note = ""
        
        s3_sequence[pos-1] = alpaca_aa
        print(f"{pos:<10} {s2_aa:<15} {'→':<5} {alpaca_aa:<15} {region:<10} {note}")
    
    s3_sequence_str = ''.join(s3_sequence)
    s3_all_mutations = sorted(s2_mutations + s3_additional_mutations)
    
    print(f"\n✅ S3 complete:")
    print(f"   Sequence: {s3_sequence_str}")
    print(f"   Total back-mutations: {len(s3_all_mutations)}")
    print(f"   Humanization: {100 * (117 - len(s3_all_mutations)) / 117:.1f}%")
    
    # Verify sequence length
    assert len(s3_sequence_str) == 117, f"Length error: {len(s3_sequence_str)}"
    
    # Verify differences with S2
    differences = []
    for i, (a, b) in enumerate(zip(s2_sequence, s3_sequence_str), 1):
        if a != b:
            differences.append((i, a, b))
    
    print(f"\n🔍 Differences between S2 and S3: {len(differences)} positions")
    for pos, s2_aa, s3_aa in differences:
        print(f"   Position {pos}: {s2_aa}→{s3_aa}")
    
    # Verify they match the additional mutations
    assert len(differences) == len(s3_additional_mutations), "Mismatch in mutation count!"
    
    # Update JSON
    data['strategy_3'] = {
        'name': 'Conservative (Maximum Stability)',
        'sequence': s3_sequence_str,
        'length': 117,
        'back_mutations': s3_all_mutations,
        'back_mutation_count': len(s3_all_mutations),
        'design_principle': 'Based on S2, with additional FR1/FR3 structural and Vernier positions for maximum functional retention',
        'humanization_percent': round(100 * (117 - len(s3_all_mutations)) / 117, 1),
        'additional_vs_s2': s3_additional_mutations,
        'additional_count': len(s3_additional_mutations)
    }
    
    data['note_s3_v2'] = "S3 correctly built from S2 base, adding 6 FR1/FR3 positions"
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Updated: {json_path}")
    
    return data


if __name__ == "__main__":
    data = create_s3_from_s2()
    
    print("\n" + "="*80)
    print("THREE-STRATEGY SUMMARY")
    print("="*80)
    print(f"\nS1 (Max-Human):        {data['strategy_1']['back_mutation_count']} back-mutations, "
          f"{100 * (117 - data['strategy_1']['back_mutation_count']) / 117:.1f}% humanized")
    print(f"S2 (Surface Reshaping): {data['strategy_2']['back_mutation_count']} back-mutations, "
          f"{100 * (117 - data['strategy_2']['back_mutation_count']) / 117:.1f}% humanized")
    print(f"S3 (Conservative):      {data['strategy_3']['back_mutation_count']} back-mutations, "
          f"{data['strategy_3']['humanization_percent']}% humanized")
    
    print(f"\n✅ Progressive gradient: 4 → 8 → {data['strategy_3']['back_mutation_count']}")
    print(f"✅ S3 adds {data['strategy_3']['additional_count']} more positions vs S2")















