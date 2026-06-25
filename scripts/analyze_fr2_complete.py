#!/usr/bin/env python3
"""
Analyze ALL FR2 differences between Alpaca and Human
to properly design S2 (half-camel FR2) vs S3 (full-camel FR2)
"""

ALPACA_7D12 = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
HUMAN_GERMLINE = "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKWGQGTQVTVSS"

# IMGT regions (1-indexed, approximate for VHH)
FR1_END = 24
CDR1_START, CDR1_END = 25, 31
FR2_START, FR2_END = 32, 47  # FR2 proper (before CDR2)
CDR2_START, CDR2_END = 48, 56

print("="*80)
print("FR2 REGION ANALYSIS (IMGT 32-47)")
print("="*80)

print(f"\nAlpaca FR2: {ALPACA_7D12[FR2_START-1:FR2_END]}")
print(f"Human  FR2: {HUMAN_GERMLINE[FR2_START-1:FR2_END]}")

# Find all differences in FR2
fr2_differences = []
for i in range(FR2_START, FR2_END + 1):
    alpaca_aa = ALPACA_7D12[i-1]
    human_aa = HUMAN_GERMLINE[i-1] if i-1 < len(HUMAN_GERMLINE) else '-'
    
    if alpaca_aa != human_aa:
        # Categorize position
        if i in [37, 44, 45, 47]:
            category = "Hallmark"
            priority = "CRITICAL"
        elif i in [28, 29]:  # Actually FR1/FR2 border
            category = "Vernier anchor"
            priority = "CRITICAL"
        elif i == 49:  # Actually FR2/CDR2 border
            category = "Vernier tuning"
            priority = "HIGH"
        elif i in [32, 33, 34, 35, 36, 38, 39, 40, 41, 42, 43, 46]:
            # Determine if surface or buried
            if i in [34, 36, 40, 42]:
                category = "FR2 buried/structural"
                priority = "MEDIUM"
            else:
                category = "FR2 surface"
                priority = "LOW"
        else:
            category = "Other"
            priority = "LOW"
        
        fr2_differences.append((i, alpaca_aa, human_aa, category, priority))

print(f"\n{'='*80}")
print(f"FR2 DIFFERENCES (Alpaca vs Human)")
print(f"{'='*80}")
print(f"Total: {len(fr2_differences)} positions\n")
print(f"{'Position':<10} {'Alpaca':<10} {'Human':<10} {'Category':<25} {'Priority'}")
print("-" * 80)

for pos, alpaca, human, cat, pri in fr2_differences:
    print(f"{pos:<10} {alpaca:<10} {human:<10} {cat:<25} {pri}")

# Strategy design
print(f"\n{'='*80}")
print(f"STRATEGY DESIGN FOR FR2")
print(f"{'='*80}")

s1_fr2 = []
s2_fr2 = []
s3_fr2 = []

for pos, alpaca, human, cat, pri in fr2_differences:
    # S1: Only critical (Hallmarks + critical Vernier)
    if pri == "CRITICAL":
        s1_fr2.append(pos)
        s2_fr2.append(pos)
        s3_fr2.append(pos)
    # S2: Critical + HIGH + some MEDIUM (inner face)
    elif pri == "HIGH":
        s2_fr2.append(pos)
        s3_fr2.append(pos)
    elif pri == "MEDIUM":
        # S2: only if buried/structural (Face 1)
        if "buried" in cat or "structural" in cat:
            s2_fr2.append(pos)
        s3_fr2.append(pos)
    # S3: Everything
    else:
        s3_fr2.append(pos)

print(f"\nS1 (Max-Human) - FR2 back-mutations: {len(s1_fr2)}")
print(f"   Positions: {s1_fr2}")
print(f"   Rationale: Only 4 Hallmarks (37,44,45,47)")

print(f"\nS2 (Surface Reshaping) - FR2 back-mutations: {len(s2_fr2)}")
print(f"   Positions: {s2_fr2}")
print(f"   Rationale: Hallmarks + Vernier + buried structural ()")

print(f"\nS3 (Conservative) - FR2 back-mutations: {len(s3_fr2)}")
print(f"   Positions: {s3_fr2}")
print(f"   Rationale: ALL FR2 differences ()")

print(f"\n✅ FR2 gradient: {len(s1_fr2)} → {len(s2_fr2)} → {len(s3_fr2)}")















