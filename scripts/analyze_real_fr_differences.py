#!/usr/bin/env python3
"""
Real analysis of FR1/FR2/FR3 differences and strategy mutations
"""

import json
from pathlib import Path

ALPACA_7D12 = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
HUMAN_GERMLINE = "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKWGQGTQVTVSS"

# IMGT regions (1-indexed)
FR1_RANGE = (1, 24)
CDR1_RANGE = (25, 31)
FR2_RANGE = (32, 47)
CDR2_RANGE = (48, 56)
FR3_RANGE = (57, 93)
CDR3_RANGE = (94, 106)
FR4_RANGE = (106, 117)

def get_region_name(pos):
    if FR1_RANGE[0] <= pos <= FR1_RANGE[1]:
        return "FR1"
    elif CDR1_RANGE[0] <= pos <= CDR1_RANGE[1]:
        return "CDR1"
    elif FR2_RANGE[0] <= pos <= FR2_RANGE[1]:
        return "FR2"
    elif CDR2_RANGE[0] <= pos <= CDR2_RANGE[1]:
        return "CDR2"
    elif FR3_RANGE[0] <= pos <= FR3_RANGE[1]:
        return "FR3"
    elif CDR3_RANGE[0] <= pos <= CDR3_RANGE[1]:
        return "CDR3"
    elif pos >= FR4_RANGE[0]:
        return "FR4"
    return "Unknown"

def analyze_differences():
    """Find ALL differences between Alpaca and Human in each FR"""
    
    fr1_diff = []
    fr2_diff = []
    fr3_diff = []
    
    for i in range(1, len(ALPACA_7D12) + 1):
        alpaca_aa = ALPACA_7D12[i-1]
        human_aa = HUMAN_GERMLINE[i-1] if i-1 < len(HUMAN_GERMLINE) else '-'
        
        if alpaca_aa != human_aa:
            region = get_region_name(i)
            if region == "FR1":
                fr1_diff.append((i, alpaca_aa, human_aa))
            elif region == "FR2":
                fr2_diff.append((i, alpaca_aa, human_aa))
            elif region == "FR3":
                fr3_diff.append((i, alpaca_aa, human_aa))
    
    return fr1_diff, fr2_diff, fr3_diff

def analyze_strategies():
    """Analyze which FR positions are mutated in each strategy"""
    
    json_path = Path("output/7d12_verified_run/checkpoint_04_humanized_sequences_FINAL.json")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    s1_mutations = data['strategy_1']['back_mutations']
    s2_mutations = data['strategy_2']['back_mutations']
    s3_mutations = data['strategy_3']['back_mutations']
    
    def categorize_mutations(mutations):
        fr1 = [m for m in mutations if FR1_RANGE[0] <= m <= FR1_RANGE[1]]
        fr2 = [m for m in mutations if FR2_RANGE[0] <= m <= FR2_RANGE[1]]
        fr3 = [m for m in mutations if FR3_RANGE[0] <= m <= FR3_RANGE[1]]
        other = [m for m in mutations if m not in fr1 and m not in fr2 and m not in fr3]
        return fr1, fr2, fr3, other
    
    s1_fr1, s1_fr2, s1_fr3, s1_other = categorize_mutations(s1_mutations)
    s2_fr1, s2_fr2, s2_fr3, s2_other = categorize_mutations(s2_mutations)
    s3_fr1, s3_fr2, s3_fr3, s3_other = categorize_mutations(s3_mutations)
    
    return {
        'S1': {'FR1': s1_fr1, 'FR2': s1_fr2, 'FR3': s1_fr3, 'other': s1_other},
        'S2': {'FR1': s2_fr1, 'FR2': s2_fr2, 'FR3': s2_fr3, 'other': s2_other},
        'S3': {'FR1': s3_fr1, 'FR2': s3_fr2, 'FR3': s3_fr3, 'other': s3_other},
    }

def main():
    print("="*80)
    print("REAL FR1/FR2/FR3 DIFFERENCE ANALYSIS")
    print("="*80)
    
    # Step 1: Find all FR differences
    fr1_diff, fr2_diff, fr3_diff = analyze_differences()
    
    print(f"\n{'='*80}")
    print(f"ALPACA vs HUMAN DIFFERENCES IN EACH FR")
    print(f"{'='*80}")
    
    print(f"\n**FR1 (IMGT 1-24):**")
    print(f"Total differences: {len(fr1_diff)}")
    print(f"{'Position':<10} {'Alpaca':<10} {'Human':<10}")
    print("-" * 35)
    for pos, alpaca, human in fr1_diff:
        print(f"{pos:<10} {alpaca:<10} {human:<10}")
    
    print(f"\n**FR2 (IMGT 32-47):**")
    print(f"Total differences: {len(fr2_diff)}")
    print(f"{'Position':<10} {'Alpaca':<10} {'Human':<10}")
    print("-" * 35)
    for pos, alpaca, human in fr2_diff:
        print(f"{pos:<10} {alpaca:<10} {human:<10}")
    
    print(f"\n**FR3 (IMGT 57-93):**")
    print(f"Total differences: {len(fr3_diff)}")
    print(f"{'Position':<10} {'Alpaca':<10} {'Human':<10}")
    print("-" * 35)
    for pos, alpaca, human in fr3_diff[:15]:  # Show first 15
        print(f"{pos:<10} {alpaca:<10} {human:<10}")
    if len(fr3_diff) > 15:
        print(f"... and {len(fr3_diff) - 15} more")
    
    # Step 2: Analyze strategy mutations
    strategies = analyze_strategies()
    
    print(f"\n{'='*80}")
    print(f"STRATEGY MUTATIONS BY REGION")
    print(f"{'='*80}")
    
    print(f"\n{'Strategy':<10} {'FR1':<15} {'FR2':<15} {'FR3':<15} {'Other':<15} {'Total'}")
    print("-" * 80)
    
    for strat in ['S1', 'S2', 'S3']:
        fr1_count = len(strategies[strat]['FR1'])
        fr2_count = len(strategies[strat]['FR2'])
        fr3_count = len(strategies[strat]['FR3'])
        other_count = len(strategies[strat]['other'])
        total = fr1_count + fr2_count + fr3_count + other_count
        
        print(f"{strat:<10} {fr1_count:<15} {fr2_count:<15} {fr3_count:<15} {other_count:<15} {total}")
    
    # Step 3: Detailed breakdown
    print(f"\n{'='*80}")
    print(f"DETAILED STRATEGY BREAKDOWN")
    print(f"{'='*80}")
    
    for strat in ['S1', 'S2', 'S3']:
        print(f"\n**{strat}:**")
        print(f"  FR1: {strategies[strat]['FR1']}")
        print(f"  FR2: {strategies[strat]['FR2']}")
        print(f"  FR3: {strategies[strat]['FR3']}")
        print(f"  Other (Vernier anchors): {strategies[strat]['other']}")
    
    # Step 4: Coverage analysis
    print(f"\n{'='*80}")
    print(f"COVERAGE ANALYSIS (% of differences retained)")
    print(f"{'='*80}")
    
    print(f"\n{'Strategy':<10} {'FR1':<20} {'FR2':<20} {'FR3':<20}")
    print("-" * 70)
    
    for strat in ['S1', 'S2', 'S3']:
        fr1_coverage = f"{len(strategies[strat]['FR1'])}/{len(fr1_diff)} = {100*len(strategies[strat]['FR1'])/len(fr1_diff):.1f}%" if fr1_diff else "N/A"
        fr2_coverage = f"{len(strategies[strat]['FR2'])}/{len(fr2_diff)} = {100*len(strategies[strat]['FR2'])/len(fr2_diff):.1f}%" if fr2_diff else "N/A"
        fr3_coverage = f"{len(strategies[strat]['FR3'])}/{len(fr3_diff)} = {100*len(strategies[strat]['FR3'])/len(fr3_diff):.1f}%" if fr3_diff else "N/A"
        
        print(f"{strat:<10} {fr1_coverage:<20} {fr2_coverage:<20} {fr3_coverage:<20}")
    
    # Step 5: Strategy differences
    print(f"\n{'='*80}")
    print(f"STRATEGY DIFFERENCES (what each adds)")
    print(f"{'='*80}")
    
    s1_fr1 = set(strategies['S1']['FR1'])
    s1_fr2 = set(strategies['S1']['FR2'])
    s1_fr3 = set(strategies['S1']['FR3'])
    
    s2_fr1 = set(strategies['S2']['FR1'])
    s2_fr2 = set(strategies['S2']['FR2'])
    s2_fr3 = set(strategies['S2']['FR3'])
    
    s3_fr1 = set(strategies['S3']['FR1'])
    s3_fr2 = set(strategies['S3']['FR2'])
    s3_fr3 = set(strategies['S3']['FR3'])
    
    print(f"\n**S2 vs S1 (what S2 adds):**")
    print(f"  FR1: +{len(s2_fr1 - s1_fr1)} positions {sorted(s2_fr1 - s1_fr1)}")
    print(f"  FR2: +{len(s2_fr2 - s1_fr2)} positions {sorted(s2_fr2 - s1_fr2)}")
    print(f"  FR3: +{len(s2_fr3 - s1_fr3)} positions {sorted(s2_fr3 - s1_fr3)}")
    
    print(f"\n**S3 vs S2 (what S3 adds):**")
    print(f"  FR1: +{len(s3_fr1 - s2_fr1)} positions {sorted(s3_fr1 - s2_fr1)}")
    print(f"  FR2: +{len(s3_fr2 - s2_fr2)} positions {sorted(s3_fr2 - s2_fr2)}")
    print(f"  FR3: +{len(s3_fr3 - s2_fr3)} positions {sorted(s3_fr3 - s2_fr3)}")
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"\nTotal Alpaca-Human differences:")
    print(f"  FR1: {len(fr1_diff)} positions")
    print(f"  FR2: {len(fr2_diff)} positions")
    print(f"  FR3: {len(fr3_diff)} positions")
    print(f"\nStrategy progression:")
    print(f"  S1 is minimal (only critical positions)")
    print(f"  S2 adds FR2 structural positions")
    print(f"  S3 adds ALL remaining FR2 + FR3 structural")

if __name__ == "__main__":
    main()















