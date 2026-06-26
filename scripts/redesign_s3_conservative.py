#!/usr/bin/env python3
"""
Redesign Strategy 3 (Conservative) with proper FR1/FR3 camelid residues
Goal: FR2 fully alpaca + key FR1/FR3 structural/functional residues
"""

import json
from pathlib import Path

# Sequences
ALPACA_7D12 = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
HUMAN_GERMLINE = "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKWGQGTQVTVSS"

# CDRs (from IMGT, 1-indexed for display, 0-indexed for actual position)
CDR1_START, CDR1_END = 25, 31  # GFWYNH
CDR2_START, CDR2_END = 48, 56  # ITADSGST
CDR3_START, CDR3_END = 94, 106  # AAGGVGWPYFDY
FR4_START, FR4_END = 106, 117  # WGQGTQVTVSS

# IMGT positions where alpaca differs from human (excluding CDRs)
# Format: (IMGT_pos, Alpaca_residue, Human_residue, Region, Type)
FR_DIFFERENCES = [
    # FR1 differences
    (3, 'V', 'V', 'FR1', 'identity'),  # Same
    (6, 'V', 'L', 'FR1', 'hydrophobic'),
    (9, 'S', 'S', 'FR1', 'identity'),
    (13, 'V', 'V', 'FR1', 'identity'),
    (14, 'Q', 'Q', 'FR1', 'identity'),
    (15, 'V', 'P', 'FR1', 'structural'),
    (17, 'G', 'G', 'FR1', 'identity'),
    (19, 'L', 'L', 'FR1', 'identity'),
    (20, 'R', 'R', 'FR1', 'identity'),
    (21, 'L', 'L', 'FR1', 'identity'),
    (22, 'S', 'S', 'FR1', 'identity'),
    (23, 'R', 'C', 'FR1', 'structural'),
    (24, 'A', 'A', 'FR1', 'identity'),
    
    # FR2 differences (Hallmarks and other)
    (28, 'M', 'Y', 'FR2', 'hallmark_related'),  # Kabat 28 (Vernier)
    (29, 'G', 'A', 'FR2', 'hallmark_related'),  # Kabat 29 (Vernier)
    (37, 'E', 'K', 'FR2', 'hallmark'),  # Kabat 37 (official VHH Hallmark)
    (44, 'E', 'W', 'FR2', 'hallmark'),  # Kabat 44 (official VHH Hallmark)
    (45, 'R', 'S', 'FR2', 'hallmark'),  # Kabat 45 (official VHH Hallmark)
    (47, 'V', 'I', 'FR2', 'hallmark'),  # Kabat 47 (official VHH Hallmark)
    (49, 'A', 'S', 'FR2', 'vernier'),   # Kabat 49 (Vernier tuning)
    
    # FR3 differences
    (71, 'D', 'N', 'FR3', 'structural'),  # Kabat 71 (affects CDR geometry)
    (73, 'A', 'S', 'FR3', 'vernier'),     # Kabat 73 (Vernier tuning)
    (78, 'R', 'K', 'FR3', 'charge'),      # Kabat 78 (Vernier tuning)
    (82, 'N', 'N', 'FR3', 'identity'),
    (83, 'T', 'T', 'FR3', 'identity'),
    (84, 'V', 'L', 'FR3', 'hydrophobic'),
    (94, 'K', 'A', 'FR3', 'vernier'),     # Kabat 94 (critical Vernier anchor)
]

def create_conservative_s3():
    """
    Create S3 with maximum conservative strategy:
    - FR2: ALL alpaca residues (5 positions: 37, 44, 45, 47, 49)
    - FR1: Additional structural positions (15, 23)
    - FR3: Additional Vernier/structural positions (71, 73, 78, 84)
    - Plus mandatory Vernier anchors (28, 29, 94)
    
    Total: ~13 back-mutations
    """
    
    # Start from human germline, extend to full length
    humanized = list(HUMAN_GERMLINE)
    
    # Extend to match alpaca length (preserve CDR3+FR4)
    if len(humanized) < len(ALPACA_7D12):
        humanized.extend(list(ALPACA_7D12[len(humanized):]))
    
    # Preserve CDRs (must be alpaca)
    for i in range(CDR1_START-1, CDR1_END):
        humanized[i] = ALPACA_7D12[i]
    for i in range(CDR2_START-1, CDR2_END):
        humanized[i] = ALPACA_7D12[i]
    for i in range(CDR3_START-1, CDR3_END):
        humanized[i] = ALPACA_7D12[i]
    
    # S3 back-mutations (Conservative strategy)
    s3_back_mutations = [
        # Mandatory Vernier anchors
        28,  # M (Vernier anchor)
        29,  # G (Vernier anchor)
        94,  # K (critical Vernier anchor)
        
        # FR2 - ALL alpaca (complete camelization)
        37,  # E (Hallmark)
        44,  # E (Hallmark)
        45,  # R (Hallmark)
        47,  # V (Hallmark)
        49,  # A (Vernier tuning)
        
        # FR1 - Structural stability
        15,  # V→P (beta-strand geometry)
        23,  # R→C (though both are charged, alpaca has R here for VHH)
        
        # FR3 - Extended Vernier network and stability
        71,  # D (affects CDR2-CDR3 geometry)
        73,  # A (Vernier tuning, close to CDR3)
        78,  # R (Vernier tuning, electrostatics)
        84,  # V (hydrophobic packing)
    ]
    
    # Apply back-mutations
    for pos in s3_back_mutations:
        humanized[pos-1] = ALPACA_7D12[pos-1]
    
    s3_sequence = ''.join(humanized)
    
    # Verify length
    assert len(s3_sequence) == 117, f"S3 length error: {len(s3_sequence)}"
    
    return {
        'sequence': s3_sequence,
        'back_mutations': sorted(s3_back_mutations),
        'back_mutation_count': len(s3_back_mutations),
        'humanization_percent': round(100 * (117 - len(s3_back_mutations)) / 117, 1),
        'design_principle': 'FR2 fully alpaca (all Hallmarks + Vernier) + FR1/FR3 structural/Vernier positions for maximum stability'
    }


def update_sequences_json():
    """Update the checkpoint file with corrected S3"""
    json_path = Path("output/7d12_verified_run/checkpoint_04_humanized_sequences_FINAL.json")
    
    if not json_path.exists():
        print(f"❌ File not found: {json_path}")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get new S3
    new_s3 = create_conservative_s3()
    
    # Show comparison
    print("\n" + "="*80)
    print("S2 vs S3 COMPARISON")
    print("="*80)
    
    s2_seq = data['strategy_2']['sequence']
    s3_seq = new_s3['sequence']
    
    print(f"\nS2 (Surface Reshaping):")
    print(f"  Sequence: {s2_seq}")
    print(f"  Back-mutations: {data['strategy_2']['back_mutations']}")
    print(f"  Count: {data['strategy_2']['back_mutation_count']}")
    
    print(f"\nS3 (Conservative) - NEW:")
    print(f"  Sequence: {s3_seq}")
    print(f"  Back-mutations: {new_s3['back_mutations']}")
    print(f"  Count: {new_s3['back_mutation_count']}")
    print(f"  Humanization: {new_s3['humanization_percent']}%")
    
    # Find differences
    differences = []
    for i, (a, b) in enumerate(zip(s2_seq, s3_seq), 1):
        if a != b:
            differences.append((i, a, b, ALPACA_7D12[i-1]))
    
    print(f"\n🔍 Sequence differences (S2→S3):")
    print(f"{'Position':<10} {'S2':<5} {'S3':<5} {'Alpaca':<8} {'Note'}")
    print("-" * 60)
    for pos, s2_aa, s3_aa, alpaca_aa in differences:
        note = ""
        if pos == 15:
            note = "FR1 structural"
        elif pos == 23:
            note = "FR1 structural"
        elif pos == 71:
            note = "FR3 Vernier-related"
        elif pos == 73:
            note = "FR3 Vernier tuning"
        elif pos == 78:
            note = "FR3 Vernier tuning"
        elif pos == 84:
            note = "FR3 hydrophobic"
        print(f"{pos:<10} {s2_aa:<5} {s3_aa:<5} {alpaca_aa:<8} {note}")
    
    print(f"\n✅ Total: {len(differences)} additional back-mutations in S3")
    
    # Update data
    data['strategy_3'] = {
        'name': 'Conservative (Maximum Stability)',
        'sequence': new_s3['sequence'],
        'length': 117,
        'back_mutations': new_s3['back_mutations'],
        'back_mutation_count': new_s3['back_mutation_count'],
        'design_principle': new_s3['design_principle'],
        'humanization_percent': new_s3['humanization_percent']
    }
    
    data['note_s3_corrected'] = "S3 redesigned with additional FR1/FR3 back-mutations for true conservative strategy"
    
    # Save
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Updated: {json_path}")
    
    return new_s3, differences


if __name__ == "__main__":
    print("="*80)
    print("REDESIGNING STRATEGY 3 (CONSERVATIVE)")
    print("="*80)
    
    new_s3, differences = update_sequences_json()
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"S1: 4 back-mutations (Max-Human)")
    print(f"S2: 8 back-mutations (Surface Reshaping)")
    print(f"S3: {new_s3['back_mutation_count']} back-mutations (Conservative) ✅")
    print(f"\nS3 Humanization: {new_s3['humanization_percent']}%")
    print(f"S3 adds {len(differences)} more camelid residues vs S2")
    print("\n✅ S3 is now truly different from S2!")















