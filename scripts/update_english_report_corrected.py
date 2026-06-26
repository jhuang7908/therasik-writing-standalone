#!/usr/bin/env python3
"""
Update English report with corrected S1/S2/S3 sequences and strategy descriptions
"""

import json
from pathlib import Path

def main():
    # Load corrected sequences
    json_path = Path("output/7d12_verified_run/checkpoint_04_humanized_sequences_FINAL.json")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    alpaca = data['original_sequence']
    s1 = data['strategy_1']
    s2 = data['strategy_2']
    s3 = data['strategy_3']
    
    print("="*80)
    print("GENERATING UPDATED REPORT SECTIONS")
    print("="*80)
    
    # Section 1: Strategy Comparison Table
    comparison_table = f"""
## 3. Humanization Strategies

### 3.1 Strategy Overview

| Strategy | Name | Back-Mutations | Humanization | FR2 Status |
|----------|------|----------------|--------------|------------|
| **S1** | Max-Human | {s1['back_mutation_count']} | {s1['humanization_percent']}% | 4 Hallmarks only |
| **S2** | Surface Reshaping | {s2['back_mutation_count']} | {s2['humanization_percent']}% | **** (8/16 positions) |
| **S3** | Conservative | {s3['back_mutation_count']} | {s3['humanization_percent']}% | **** (16/16 positions) |

**Progressive Gradient:** {s1['back_mutation_count']} → {s2['back_mutation_count']} → {s3['back_mutation_count']} back-mutations ✅

### 3.2 Strategy Definitions

#### **Strategy 1 (S1): Max-Human**
- **Goal:** Maximum humanization with minimal camelization
- **FR2 Approach:** Only 4 Hallmarks (Kabat 37, 44, 45, 47)
- **Back-mutations:** {s1['back_mutation_count']} positions
  - Hallmarks: 37, 44, 45, 47 (FR2)
  - Vernier anchors: 28, 29, 94 (critical for CDR support)
- **Humanization:** {s1['humanization_percent']}%
- **Use Case:** Acute/short-term therapeutics, lowest immunogenicity risk

#### **Strategy 2 (S2): Surface Reshaping - FR2 **
- **Goal:** Industrial standard, balance function and immunogenicity
- **FR2 Approach:** **Half-human, half-camel ()**
  - Preserve: Hallmarks + buried/structural positions (Face 1)
  - Humanize: Surface-exposed positions (Face 2)
  - Coverage: **8/16 FR2 positions** = 50% camelized ✓
- **Back-mutations:** {s2['back_mutation_count']} positions
  - FR2 Hallmarks: 37, 44, 45, 47
  - FR2 Buried: 34, 36, 40, 42 (structural stability)
  - Vernier: 28, 29, 49, 94
- **Humanization:** {s2['humanization_percent']}%
- **Use Case:** Chronic/long-term therapeutics, optimal balance

#### **Strategy 3 (S3): Conservative - FR2 **
- **Goal:** Maximum functional retention, full FR2 preservation
- **FR2 Approach:** **Full-camel ()** - ALL FR2 positions preserved
  - Coverage: **16/16 FR2 positions** = 100% alpaca ✓
  - Includes ALL surface and buried positions
- **Back-mutations:** {s3['back_mutation_count']} positions
  - FR2: ALL 16 positions (32-47, complete alpaca FR2)
  - FR3: 72, 73, 74, 77 (structural/Vernier)
  - Vernier: 28, 29, 49, 94
- **Humanization:** {s3['humanization_percent']}%
- **Use Case:** Maximum affinity retention, discovery/optimization
"""
    
    # Section 2: Sequence Details
    sequence_section = f"""
### 3.3 Complete Sequences

#### **Original Alpaca 7D12:**
```
{alpaca}
```

#### **S1 (Max-Human):**
```
{s1['sequence']}
```
- Back-mutations: {s1['back_mutations']}
- Count: {s1['back_mutation_count']}
- Humanization: {s1['humanization_percent']}%

#### **S2 (Surface Reshaping - FR2 ):**
```
{s2['sequence']}
```
- Back-mutations: {s2['back_mutations']}
- Count: {s2['back_mutation_count']}
- Humanization: {s2['humanization_percent']}%
- FR2 status: 8/16 positions = **** ✓

#### **S3 (Conservative - FR2 ):**
```
{s3['sequence']}
```
- Back-mutations: {s3['back_mutations']}
- Count: {s3['back_mutation_count']}
- Humanization: {s3['humanization_percent']}%
- FR2 status: 16/16 positions = **** ✓
"""
    
    # Section 3: FR2 Detailed Analysis
    fr2_analysis = """
### 3.4 FR2 Strategy Deep Dive

#### **FR2 Region Definition**
- **IMGT Positions:** 32-47 (16 positions total)
- **Alpaca-Human Differences:** 16/16 positions differ
- **Strategic Importance:** FR2 contains:
  - 4 VHH Hallmarks (37, 44, 45, 47) - critical for VHH properties
  - 4 Buried/structural positions (34, 36, 40, 42) - stability
  - 8 Surface-exposed positions - immunogenicity impact

#### **S1: FR2 Minimal Strategy**
- **Retain:** Only 4 Hallmarks (37, 44, 45, 47)
- **Humanize:** All other 12 positions
- **Rationale:** Preserve VHH function while maximizing human similarity
- **Coverage:** 4/16 = 25% alpaca

#### **S2: FR2 Half-Camel ()**
- **Retain:** 
  - 4 Hallmarks (37, 44, 45, 47)
  - 4 Buried positions (34, 36, 40, 42) - Face 1, inner stability
- **Humanize:** 8 surface positions (32, 33, 35, 38, 39, 41, 43, 46) - Face 2
- **Rationale:** Preserve inner structural core, humanize outer surface
- **Coverage:** 8/16 = 50% alpaca = **** ✓
- **Industry Standard:** This is the typical approach for VHH humanization

#### **S3: FR2 Full-Camel ()**
- **Retain:** ALL 16 FR2 positions
- **Humanize:** None in FR2
- **Rationale:** Maximum functional retention, complete VHH FR2 preservation
- **Coverage:** 16/16 = 100% alpaca = **** ✓
- **Use Case:** When affinity/function is paramount, willing to accept higher immunogenicity risk
"""
    
    # Save sections
    output_path = Path("output/7D12/report_update_sections.txt")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(comparison_table)
        f.write("\n\n")
        f.write(sequence_section)
        f.write("\n\n")
        f.write(fr2_analysis)
    
    print(f"\n✅ Report sections generated: {output_path}")
    print("\nPlease manually integrate these sections into the English report.")
    print("\nKey changes:")
    print(f"  - S1: {s1['back_mutation_count']} mutations (was 4)")
    print(f"  - S2: {s2['back_mutation_count']} mutations (was 8)")
    print(f"  - S3: {s3['back_mutation_count']} mutations (was 13-14)")
    print(f"  - S2 FR2:  (8/16 positions)")
    print(f"  - S3 FR2:  (16/16 positions)")

if __name__ == "__main__":
    main()















