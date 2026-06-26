#!/usr/bin/env python3
"""
Correctly redesign all three strategies:
S1: Max-Human (only 4 Hallmarks in FR2)
S2: Surface Reshaping (FR2  = Hallmarks + buried)
S3: Conservative (FR2  = ALL FR2 + FR1/FR3 key positions)
"""

import json
from pathlib import Path

ALPACA_7D12 = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
HUMAN_GERMLINE = "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKWGQGTQVTVSS"

# CDRs (IMGT, 1-indexed)
CDR1_START, CDR1_END = 25, 31
CDR2_START, CDR2_END = 48, 56
CDR3_START, CDR3_END = 94, 106
FR4_START = 106

def create_humanized_sequence(back_mutations):
    """Create humanized sequence from human template + back-mutations"""
    # Start from human germline
    seq = list(HUMAN_GERMLINE)
    
    # Extend to full length (preserve Alpaca CDR3+FR4)
    if len(seq) < len(ALPACA_7D12):
        seq.extend(list(ALPACA_7D12[len(seq):]))
    
    # Preserve CDRs (must be Alpaca)
    for i in range(CDR1_START-1, CDR1_END):
        seq[i] = ALPACA_7D12[i]
    for i in range(CDR2_START-1, CDR2_END):
        seq[i] = ALPACA_7D12[i]
    for i in range(CDR3_START-1, CDR3_END):
        seq[i] = ALPACA_7D12[i]
    
    # Apply back-mutations
    for pos in back_mutations:
        seq[pos-1] = ALPACA_7D12[pos-1]
    
    return ''.join(seq)

def main():
    print("="*80)
    print("REDESIGNING ALL THREE STRATEGIES")
    print("="*80)
    
    # S1: Max-Human (4Hallmarks)
    s1_mutations = [
        37, 44, 45, 47,  # FR2 Hallmarks (CRITICAL)
        # Note: Vernier anchors 28, 29, 94？
        # "Max-Human"，
    ]
    
    # Actually, let's check if 28,29,94 are also critical
    # 28,29 are Vernier anchors (critical for CDR support)
    # 94 is also critical Vernier anchor
    s1_mutations_full = sorted([28, 29, 37, 44, 45, 47, 94])
    
    # S2: Surface Reshaping (FR2 = Hallmarks + buried structural)
    s2_mutations = sorted([
        28, 29,  # Vernier anchors
        34, 36, 37, 40, 42, 44, 45, 47,  # FR2: Hallmarks + buried
        49,  # Vernier tuning
        94,  # Vernier anchor
    ])
    
    # S3: Conservative (FR2 = ALL FR2 + FR1/FR3 key positions)
    s3_mutations = sorted([
        28, 29,  # Vernier anchors
        # FR2: ALL 16 differences
        32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47,
        49,  # Vernier tuning
        # FR3: key structural positions
        72, 73, 74, 77,
        94,  # Vernier anchor critical
    ])
    
    # Generate sequences
    s1_seq = create_humanized_sequence(s1_mutations_full)
    s2_seq = create_humanized_sequence(s2_mutations)
    s3_seq = create_humanized_sequence(s3_mutations)
    
    # Verify lengths
    assert len(s1_seq) == 117
    assert len(s2_seq) == 117
    assert len(s3_seq) == 117
    
    print(f"\n{'='*80}")
    print(f"THREE STRATEGIES SUMMARY")
    print(f"{'='*80}")
    
    print(f"\nS1 (Max-Human):")
    print(f"   Back-mutations: {s1_mutations_full}")
    print(f"   Count: {len(s1_mutations_full)}")
    print(f"   Humanization: {100 * (117 - len(s1_mutations_full)) / 117:.1f}%")
    print(f"   Rationale: 4 Hallmarks + 3 critical Vernier anchors (28,29,94)")
    print(f"   Sequence: {s1_seq}")
    
    print(f"\nS2 (Surface Reshaping) - FR2 :")
    print(f"   Back-mutations: {s2_mutations}")
    print(f"   Count: {len(s2_mutations)}")
    print(f"   Humanization: {100 * (117 - len(s2_mutations)) / 117:.1f}%")
    print(f"   Rationale: S1 + FR2 buried/structural (34,36,40,42) + Vernier 49")
    print(f"   FR2 coverage: 8/16 positions ( ✓)")
    print(f"   Sequence: {s2_seq}")
    
    print(f"\nS3 (Conservative) - FR2 :")
    print(f"   Back-mutations: {s3_mutations}")
    print(f"   Count: {len(s3_mutations)}")
    print(f"   Humanization: {100 * (117 - len(s3_mutations)) / 117:.1f}%")
    print(f"   Rationale: S2 + ALL FR2 surface (8 more) + FR3 key positions (4)")
    print(f"   FR2 coverage: 16/16 positions ( ✓)")
    print(f"   Sequence: {s3_seq}")
    
    print(f"\n{'='*80}")
    print(f"GRADIENT CHECK")
    print(f"{'='*80}")
    print(f"S1: {len(s1_mutations_full)} mutations")
    print(f"S2: {len(s2_mutations)} mutations (+{len(s2_mutations) - len(s1_mutations_full)} vs S1)")
    print(f"S3: {len(s3_mutations)} mutations (+{len(s3_mutations) - len(s2_mutations)} vs S2)")
    print(f"\n✅ Progressive gradient: {len(s1_mutations_full)} → {len(s2_mutations)} → {len(s3_mutations)}")
    
    # Check FR2 differences
    fr2_range = range(32, 48)
    s1_fr2 = [m for m in s1_mutations_full if m in fr2_range]
    s2_fr2 = [m for m in s2_mutations if m in fr2_range]
    s3_fr2 = [m for m in s3_mutations if m in fr2_range]
    
    print(f"\nFR2 (32-47) back-mutations:")
    print(f"  S1: {len(s1_fr2)} positions - {s1_fr2}")
    print(f"  S2: {len(s2_fr2)} positions - {s2_fr2} ( ✓)")
    print(f"  S3: {len(s3_fr2)} positions - {s3_fr2} ( ✓)")
    
    # Save to JSON
    json_path = Path("output/7d12_verified_run/checkpoint_04_humanized_sequences_FINAL.json")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    data['strategy_1'] = {
        'name': 'Max-Human (Minimal Camelization)',
        'sequence': s1_seq,
        'length': 117,
        'back_mutations': s1_mutations_full,
        'back_mutation_count': len(s1_mutations_full),
        'humanization_percent': round(100 * (117 - len(s1_mutations_full)) / 117, 1),
        'fr2_strategy': 'Only 4 Hallmarks (37,44,45,47)'
    }
    
    data['strategy_2'] = {
        'name': 'Surface Reshaping (FR2 Half-Camel)',
        'sequence': s2_seq,
        'length': 117,
        'back_mutations': s2_mutations,
        'back_mutation_count': len(s2_mutations),
        'humanization_percent': round(100 * (117 - len(s2_mutations)) / 117, 1),
        'fr2_strategy': 'Hallmarks + buried/structural (8/16 positions = )'
    }
    
    data['strategy_3'] = {
        'name': 'Conservative (FR2 Full-Camel)',
        'sequence': s3_seq,
        'length': 117,
        'back_mutations': s3_mutations,
        'back_mutation_count': len(s3_mutations),
        'humanization_percent': round(100 * (117 - len(s3_mutations)) / 117, 1),
        'fr2_strategy': 'ALL FR2 differences (16/16 positions = ) + FR3 key positions'
    }
    
    data['note_final_correction'] = "All three strategies redesigned with correct FR2 logic: S2=, S3="
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved to: {json_path}")

if __name__ == "__main__":
    main()















