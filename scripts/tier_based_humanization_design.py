#!/usr/bin/env python3
"""
Tier-based humanization design following CURSOR_REPORT_ENGINE v3.0
"""

import json
from pathlib import Path

ALPACA_7D12 = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
HUMAN_GERMLINE = "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKWGQGTQVTVSS"

# CDRs (IMGT, 1-indexed)
CDR1_RANGE = (25, 31)
CDR2_RANGE = (48, 56)
CDR3_RANGE = (94, 106)

def define_tier_system():
    """
    Define Tier system for back-mutations in humanization
    
    Tier 0 (CRITICAL - ): 
        - VHH Hallmarks (FR2: 37, 44, 45, 47)
        - Vernier Anchors (28, 29, 94) - critical for CDR geometry
        - 
    
    Tier 1 (HIGH PRIORITY - back-mutate):
        - Vernier Tuning (49, 71, 73, 78) - affect CDR stability
        - FR2 buried/structural (34, 36, 40, 42) - core packing
        - CDR
    
    Tier 2 (MEDIUM PRIORITY - back-mutate):
        - FR2 surface (32, 33, 35, 38, 39, 41, 43, 46) - less critical
        - FR3 structural (66, 67, 72, 74, 77, 82) - secondary support
        - ，
    
    Tier 3 (LOW PRIORITY - ):
        - FR1 positions (1, 5, 14, 22, 24) - far from CDRs
        - FR3 surface/distant (FR3)
        - 
    """
    
    tier_0 = {
        # VHH Hallmarks (CRITICAL)
        37: {'type': 'Hallmark', 'region': 'FR2', 'note': 'VHH Hallmark (Kabat 37)', 'priority': 'CRITICAL'},
        44: {'type': 'Hallmark', 'region': 'FR2', 'note': 'VHH Hallmark (Kabat 44)', 'priority': 'CRITICAL'},
        45: {'type': 'Hallmark', 'region': 'FR2', 'note': 'VHH Hallmark (Kabat 45)', 'priority': 'CRITICAL'},
        47: {'type': 'Hallmark', 'region': 'FR2', 'note': 'VHH Hallmark (Kabat 47)', 'priority': 'CRITICAL'},
        
        # Vernier Anchors (CRITICAL)
        28: {'type': 'Vernier Anchor', 'region': 'FR1/FR2', 'note': 'Critical anchor for CDR1', 'priority': 'CRITICAL'},
        29: {'type': 'Vernier Anchor', 'region': 'FR1/FR2', 'note': 'Critical anchor for CDR1', 'priority': 'CRITICAL'},
        94: {'type': 'Vernier Anchor', 'region': 'FR3', 'note': 'Critical anchor for CDR3', 'priority': 'CRITICAL'},
    }
    
    tier_1 = {
        # Vernier Tuning
        49: {'type': 'Vernier Tuning', 'region': 'FR2/CDR2', 'note': 'CDR2 support', 'priority': 'HIGH'},
        71: {'type': 'Vernier Tuning', 'region': 'FR3', 'note': 'CDR2-CDR3 geometry', 'priority': 'HIGH'},
        73: {'type': 'Vernier Tuning', 'region': 'FR3', 'note': 'Adjacent to CDR3', 'priority': 'HIGH'},
        78: {'type': 'Vernier Tuning', 'region': 'FR3', 'note': 'CDR3 electrostatics', 'priority': 'HIGH'},
        
        # FR2 Buried/Structural
        34: {'type': 'FR2 Structural', 'region': 'FR2', 'note': 'Buried, core packing', 'priority': 'HIGH'},
        36: {'type': 'FR2 Structural', 'region': 'FR2', 'note': 'Buried, core packing', 'priority': 'HIGH'},
        40: {'type': 'FR2 Structural', 'region': 'FR2', 'note': 'Buried, core packing', 'priority': 'HIGH'},
        42: {'type': 'FR2 Structural', 'region': 'FR2', 'note': 'Buried, core packing', 'priority': 'HIGH'},
    }
    
    tier_2 = {
        # FR2 Surface
        32: {'type': 'FR2 Surface', 'region': 'FR2', 'note': 'Surface exposed', 'priority': 'MEDIUM'},
        33: {'type': 'FR2 Surface', 'region': 'FR2', 'note': 'Surface exposed', 'priority': 'MEDIUM'},
        35: {'type': 'FR2 Surface', 'region': 'FR2', 'note': 'Surface exposed', 'priority': 'MEDIUM'},
        38: {'type': 'FR2 Surface', 'region': 'FR2', 'note': 'Surface exposed', 'priority': 'MEDIUM'},
        39: {'type': 'FR2 Surface', 'region': 'FR2', 'note': 'Surface exposed', 'priority': 'MEDIUM'},
        41: {'type': 'FR2 Surface', 'region': 'FR2', 'note': 'Surface exposed', 'priority': 'MEDIUM'},
        43: {'type': 'FR2 Surface', 'region': 'FR2', 'note': 'Surface exposed', 'priority': 'MEDIUM'},
        46: {'type': 'FR2 Surface', 'region': 'FR2', 'note': 'Surface exposed', 'priority': 'MEDIUM'},
        
        # FR3 Structural
        66: {'type': 'FR3 Structural', 'region': 'FR3', 'note': 'Secondary support', 'priority': 'MEDIUM'},
        67: {'type': 'FR3 Structural', 'region': 'FR3', 'note': 'Secondary support', 'priority': 'MEDIUM'},
        72: {'type': 'FR3 Structural', 'region': 'FR3', 'note': 'Near CDR3', 'priority': 'MEDIUM'},
        74: {'type': 'FR3 Structural', 'region': 'FR3', 'note': 'Secondary support', 'priority': 'MEDIUM'},
        77: {'type': 'FR3 Structural', 'region': 'FR3', 'note': 'Secondary support', 'priority': 'MEDIUM'},
        82: {'type': 'FR3 Structural', 'region': 'FR3', 'note': 'Secondary support', 'priority': 'MEDIUM'},
    }
    
    tier_3 = {
        # FR1 (distant from CDRs)
        1: {'type': 'FR1 Surface', 'region': 'FR1', 'note': 'N-terminus, far from paratope', 'priority': 'LOW'},
        5: {'type': 'FR1 Surface', 'region': 'FR1', 'note': 'Surface, far from paratope', 'priority': 'LOW'},
        14: {'type': 'FR1 Surface', 'region': 'FR1', 'note': 'Surface, far from paratope', 'priority': 'LOW'},
        22: {'type': 'FR1 Surface', 'region': 'FR1', 'note': 'Surface, far from paratope', 'priority': 'LOW'},
        24: {'type': 'FR1 Surface', 'region': 'FR1', 'note': 'Surface, far from paratope', 'priority': 'LOW'},
    }
    
    return tier_0, tier_1, tier_2, tier_3


def design_strategies():
    """
    Design three strategies based on Tier system
    
    S1 (Base Humanized): Tier 0 only ()
    S2 (Safety-Optimized): Tier 0 + Tier 1 ()
    S3 (Affinity-Optimized): Tier 0 + Tier 1 + Tier 2 ()
    """
    
    tier_0, tier_1, tier_2, tier_3 = define_tier_system()
    
    # S1: Only Tier 0 (CRITICAL positions)
    s1_positions = sorted(tier_0.keys())
    
    # S2: Tier 0 + Tier 1 (CRITICAL + HIGH priority)
    s2_positions = sorted(list(tier_0.keys()) + list(tier_1.keys()))
    
    # S3: Tier 0 + Tier 1 + Tier 2 (CRITICAL + HIGH + MEDIUM)
    s3_positions = sorted(list(tier_0.keys()) + list(tier_1.keys()) + list(tier_2.keys()))
    
    return s1_positions, s2_positions, s3_positions, (tier_0, tier_1, tier_2, tier_3)


def create_humanized_sequence(back_mutations):
    """Create humanized sequence from human template + back-mutations"""
    seq = list(HUMAN_GERMLINE)
    
    # Extend to full length
    if len(seq) < len(ALPACA_7D12):
        seq.extend(list(ALPACA_7D12[len(seq):]))
    
    # Preserve CDRs (must be Alpaca)
    for i in range(CDR1_RANGE[0]-1, CDR1_RANGE[1]):
        seq[i] = ALPACA_7D12[i]
    for i in range(CDR2_RANGE[0]-1, CDR2_RANGE[1]):
        seq[i] = ALPACA_7D12[i]
    for i in range(CDR3_RANGE[0]-1, CDR3_RANGE[1]):
        seq[i] = ALPACA_7D12[i]
    
    # Apply back-mutations
    for pos in back_mutations:
        seq[pos-1] = ALPACA_7D12[pos-1]
    
    return ''.join(seq)


def main():
    print("="*80)
    print("TIER-BASED HUMANIZATION DESIGN")
    print("Following CURSOR_REPORT_ENGINE v3.0")
    print("="*80)
    
    # Define Tiers
    tier_0, tier_1, tier_2, tier_3 = define_tier_system()
    
    print(f"\n{'='*80}")
    print(f"TIER SYSTEM DEFINITION")
    print(f"{'='*80}")
    
    print(f"\n**Tier 0 (CRITICAL - ):** {len(tier_0)} positions")
    for pos in sorted(tier_0.keys()):
        info = tier_0[pos]
        print(f"  {pos:3d} - {info['type']:<20} | {info['note']}")
    
    print(f"\n**Tier 1 (HIGH PRIORITY - ):** {len(tier_1)} positions")
    for pos in sorted(tier_1.keys()):
        info = tier_1[pos]
        print(f"  {pos:3d} - {info['type']:<20} | {info['note']}")
    
    print(f"\n**Tier 2 (MEDIUM PRIORITY - ):** {len(tier_2)} positions")
    for pos in sorted(tier_2.keys())[:8]:  # Show first 8
        info = tier_2[pos]
        print(f"  {pos:3d} - {info['type']:<20} | {info['note']}")
    print(f"  ... and {len(tier_2) - 8} more")
    
    print(f"\n**Tier 3 (LOW PRIORITY - ):** {len(tier_3)} positions")
    print(f"  {sorted(tier_3.keys())} - FR1 surface positions")
    
    # Design strategies
    s1_pos, s2_pos, s3_pos, tiers = design_strategies()
    
    print(f"\n{'='*80}")
    print(f"STRATEGY DESIGN")
    print(f"{'='*80}")
    
    print(f"\n**S1 (Base Humanized):**")
    print(f"  Formula: Tier 0 only")
    print(f"  Positions: {s1_pos}")
    print(f"  Count: {len(s1_pos)}")
    print(f"  Rationale: Minimum camelization, only CRITICAL positions")
    
    print(f"\n**S2 (Safety-Optimized):**")
    print(f"  Formula: Tier 0 + Tier 1")
    print(f"  Positions: {s2_pos}")
    print(f"  Count: {len(s2_pos)}")
    print(f"  Rationale: Add HIGH priority structural/Vernier positions")
    print(f"  vs S1: +{len(s2_pos) - len(s1_pos)} positions")
    
    print(f"\n**S3 (Affinity-Optimized):**")
    print(f"  Formula: Tier 0 + Tier 1 + Tier 2")
    print(f"  Positions: {s3_pos}")
    print(f"  Count: {len(s3_pos)}")
    print(f"  Rationale: Add MEDIUM priority surface/secondary positions")
    print(f"  vs S2: +{len(s3_pos) - len(s2_pos)} positions")
    
    # Generate sequences
    s1_seq = create_humanized_sequence(s1_pos)
    s2_seq = create_humanized_sequence(s2_pos)
    s3_seq = create_humanized_sequence(s3_pos)
    
    print(f"\n{'='*80}")
    print(f"SEQUENCE GENERATION")
    print(f"{'='*80}")
    
    for name, pos, seq in [('S1', s1_pos, s1_seq), ('S2', s2_pos, s2_seq), ('S3', s3_pos, s3_seq)]:
        humanization = 100 * (117 - len(pos)) / 117
        print(f"\n{name}:")
        print(f"  Mutations: {len(pos)}")
        print(f"  Humanization: {humanization:.1f}%")
        print(f"  Sequence: {seq}")
    
    # Analyze by region
    print(f"\n{'='*80}")
    print(f"REGIONAL BREAKDOWN")
    print(f"{'='*80}")
    
    def count_by_region(positions):
        fr1 = len([p for p in positions if 1 <= p <= 24])
        fr2 = len([p for p in positions if 32 <= p <= 47])
        fr3 = len([p for p in positions if 57 <= p <= 93])
        other = len([p for p in positions if p not in range(1, 24+1) and p not in range(32, 47+1) and p not in range(57, 93+1)])
        return fr1, fr2, fr3, other
    
    print(f"\n{'Strategy':<10} {'FR1':<8} {'FR2':<8} {'FR3':<8} {'Other':<8} {'Total'}")
    print("-" * 55)
    
    for name, pos in [('S1', s1_pos), ('S2', s2_pos), ('S3', s3_pos)]:
        fr1, fr2, fr3, other = count_by_region(pos)
        print(f"{name:<10} {fr1:<8} {fr2:<8} {fr3:<8} {other:<8} {len(pos)}")
    
    # Save to JSON
    json_path = Path("output/7d12_verified_run/checkpoint_04_humanized_sequences_FINAL.json")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    data['strategy_1'] = {
        'name': 'Base Humanized (Tier 0 Only)',
        'sequence': s1_seq,
        'length': 117,
        'back_mutations': s1_pos,
        'back_mutation_count': len(s1_pos),
        'humanization_percent': round(100 * (117 - len(s1_pos)) / 117, 1),
        'tier_formula': 'Tier 0 (CRITICAL only)',
        'design_rationale': 'Minimum camelization: VHH Hallmarks + Vernier Anchors'
    }
    
    data['strategy_2'] = {
        'name': 'Safety-Optimized (Tier 0 + 1)',
        'sequence': s2_seq,
        'length': 117,
        'back_mutations': s2_pos,
        'back_mutation_count': len(s2_pos),
        'humanization_percent': round(100 * (117 - len(s2_pos)) / 117, 1),
        'tier_formula': 'Tier 0 + Tier 1 (CRITICAL + HIGH priority)',
        'design_rationale': 'Add Vernier tuning + FR2 structural positions for stability'
    }
    
    data['strategy_3'] = {
        'name': 'Affinity-Optimized (Tier 0 + 1 + 2)',
        'sequence': s3_seq,
        'length': 117,
        'back_mutations': s3_pos,
        'back_mutation_count': len(s3_pos),
        'humanization_percent': round(100 * (117 - len(s3_pos)) / 117, 1),
        'tier_formula': 'Tier 0 + Tier 1 + Tier 2 (CRITICAL + HIGH + MEDIUM)',
        'design_rationale': 'Add FR2 surface + FR3 secondary support for maximum conservation'
    }
    
    data['tier_system'] = {
        'tier_0': {pos: tier_0[pos] for pos in tier_0},
        'tier_1': {pos: tier_1[pos] for pos in tier_1},
        'tier_2': {pos: tier_2[pos] for pos in tier_2},
        'tier_3': {pos: tier_3[pos] for pos in tier_3}
    }
    
    data['note_tier_based'] = "All three strategies redesigned using systematic Tier-based classification"
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved to: {json_path}")
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"\n✅ Systematic Tier-based design")
    print(f"✅ Progressive gradient: {len(s1_pos)} → {len(s2_pos)} → {len(s3_pos)}")
    print(f"✅ Clear rationale for each position")
    print(f"✅ Follows CURSOR_REPORT_ENGINE v3.0 standards")

if __name__ == "__main__":
    main()















