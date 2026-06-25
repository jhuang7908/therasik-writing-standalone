#!/usr/bin/env python3
"""
Find all positions where S2 differs from Alpaca (potential candidates for S3)
"""

import json
from pathlib import Path

# Original Alpaca
ALPACA_7D12 = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"

# CDR regions (1-indexed, inclusive)
CDR1 = (25, 31)
CDR2 = (48, 56)
CDR3 = (94, 106)

def is_in_cdr(pos):
    """Check if position is in CDR"""
    return (CDR1[0] <= pos <= CDR1[1]) or \
           (CDR2[0] <= pos <= CDR2[1]) or \
           (CDR3[0] <= pos <= CDR3[1])

def get_region(pos):
    """Get region name"""
    if pos < CDR1[0]:
        return "FR1"
    elif CDR1[0] <= pos <= CDR1[1]:
        return "CDR1"
    elif pos < CDR2[0]:
        return "FR2"
    elif CDR2[0] <= pos <= CDR2[1]:
        return "CDR2"
    elif pos < CDR3[0]:
        return "FR3"
    elif CDR3[0] <= pos <= CDR3[1]:
        return "CDR3"
    else:
        return "FR4"

def main():
    json_path = Path("output/7d12_verified_run/checkpoint_04_humanized_sequences_FINAL.json")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    s2_sequence = data['strategy_2']['sequence']
    
    print("="*80)
    print("S2 vs ALPACA DIFFERENCE ANALYSIS")
    print("="*80)
    print(f"\nAlpaca: {ALPACA_7D12}")
    print(f"S2:     {s2_sequence}")
    print(f"\nLength: Alpaca={len(ALPACA_7D12)}, S2={len(s2_sequence)}")
    
    # Find all differences
    fr_differences = []
    cdr_differences = []
    
    for i, (alpaca_aa, s2_aa) in enumerate(zip(ALPACA_7D12, s2_sequence), 1):
        if alpaca_aa != s2_aa:
            region = get_region(i)
            if 'CDR' in region:
                cdr_differences.append((i, alpaca_aa, s2_aa, region))
            else:
                fr_differences.append((i, alpaca_aa, s2_aa, region))
    
    print(f"\n{'='*80}")
    print(f"FR REGION DIFFERENCES (S2 ≠ Alpaca)")
    print(f"{'='*80}")
    print(f"Total: {len(fr_differences)} positions\n")
    print(f"{'Position':<10} {'Alpaca':<10} {'S2':<10} {'Region':<10} {'Note'}")
    print("-" * 60)
    
    for pos, alpaca_aa, s2_aa, region in fr_differences:
        # Categorize
        if pos in [37, 44, 45, 47]:
            note = "⚠️ Hallmark"
        elif pos in [28, 29, 94]:
            note = "⚠️ Vernier anchor"
        elif pos in [49, 73, 78]:
            note = "Vernier tuning"
        elif region == "FR1":
            note = "FR1 structural/surface"
        elif region == "FR3":
            note = "FR3 structural/surface"
        elif region == "FR4":
            note = "FR4 J-region"
        else:
            note = "Other"
        
        print(f"{pos:<10} {alpaca_aa:<10} {s2_aa:<10} {region:<10} {note}")
    
    # Check CDR differences (should be 0 if CDR grafting worked)
    if cdr_differences:
        print(f"\n⚠️ WARNING: CDR DIFFERENCES FOUND (should be 0!)")
        print(f"{'Position':<10} {'Alpaca':<10} {'S2':<10} {'Region':<10}")
        print("-" * 50)
        for pos, alpaca_aa, s2_aa, region in cdr_differences:
            print(f"{pos:<10} {alpaca_aa:<10} {s2_aa:<10} {region:<10}")
    else:
        print(f"\n✅ CDRs are identical (CDR grafting successful)")
    
    # Suggest S3 candidates
    print(f"\n{'='*80}")
    print(f"SUGGESTED S3 ADDITIONAL BACK-MUTATIONS")
    print(f"{'='*80}")
    print("\nCriteria: FR positions where S2≠Alpaca, and likely important for structure/function\n")
    
    # Priority ranking
    high_priority = []
    medium_priority = []
    low_priority = []
    
    for pos, alpaca_aa, s2_aa, region in fr_differences:
        if pos in [28, 29, 37, 44, 45, 47, 49, 94]:
            # Already in S2
            continue
        
        # FR1 positions
        if region == "FR1":
            if pos in [6, 15, 23]:  # structural
                high_priority.append((pos, alpaca_aa, s2_aa, region, "FR1 structural"))
            else:
                low_priority.append((pos, alpaca_aa, s2_aa, region, "FR1 surface"))
        
        # FR3 positions
        elif region == "FR3":
            if pos in [66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93]:
                # Close to CDR3, more important
                if pos in [71, 73, 76, 78, 82, 83]:
                    high_priority.append((pos, alpaca_aa, s2_aa, region, "FR3 Vernier-like"))
                else:
                    medium_priority.append((pos, alpaca_aa, s2_aa, region, "FR3 structural"))
            else:
                medium_priority.append((pos, alpaca_aa, s2_aa, region, "FR3 other"))
        
        # FR4 positions
        elif region == "FR4":
            medium_priority.append((pos, alpaca_aa, s2_aa, region, "FR4 J-region"))
    
    print("HIGH PRIORITY (structural/Vernier-adjacent):")
    for pos, alpaca_aa, s2_aa, region, note in high_priority:
        print(f"  {pos}: {s2_aa}→{alpaca_aa} ({note})")
    
    print(f"\nMEDIUM PRIORITY (FR3/FR4 structural):")
    for pos, alpaca_aa, s2_aa, region, note in medium_priority[:10]:  # Limit output
        print(f"  {pos}: {s2_aa}→{alpaca_aa} ({note})")
    if len(medium_priority) > 10:
        print(f"  ... and {len(medium_priority) - 10} more")
    
    print(f"\nLOW PRIORITY (FR1 surface):")
    for pos, alpaca_aa, s2_aa, region, note in low_priority[:5]:
        print(f"  {pos}: {s2_aa}→{alpaca_aa} ({note})")
    
    print(f"\n{'='*80}")
    print(f"RECOMMENDATION FOR S3")
    print(f"{'='*80}")
    print(f"S2 has {data['strategy_2']['back_mutation_count']} back-mutations")
    print(f"S3 should add: {len(high_priority)} high-priority + 2-4 medium-priority")
    print(f"Suggested S3 total: {data['strategy_2']['back_mutation_count'] + len(high_priority) + 3} back-mutations")
    
    return high_priority, medium_priority, low_priority

if __name__ == "__main__":
    main()















