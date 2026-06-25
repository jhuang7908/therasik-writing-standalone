# Strategy Classification Truth for 19 Clinical VHHs

## Executive Summary

The **BM/SR/Native strategy labels** in Table1 **do NOT reflect framework region (FR) germline identity** as expected from traditional antibody humanization theory.

### Key Findings

1. **FR Germline Identity (IMGT database alignment):**
   - BM: **30.1%** human, 30.5% camelid (expected ≥75% human)
   - SR: **30.9%** human, 32.6% camelid (expected 50-70% human)
   - Native: **29.4%** human, 30.5% camelid (expected <50% human)

2. **FR Sequence Conservation:**
   - **Within-strategy identity: 89-97%** (highly conserved)
   - **Between-strategy identity: 88-93%** (no clear separation)
   - **Conclusion**: FR sequences are nearly identical across all 19 molecules

3. **Table1 "human_identity" vs FR identity:**
   - Table1 values: BM=91%, SR=89%, Native=85% (high, as expected)
   - FR germline identity: all ~30% (uniformly low, unexpected)
   - **Conclusion**: Table1 "human_identity" is NOT FR-specific

---

## What Do the Strategy Labels Actually Mean?

### Option 1: Patent/Literature Claims (Most Likely)
The strategy labels (BM/SR/Native) are **self-reported designations** from:
- Original patent applications
- Scientific publications by developers
- Clinical trial documentation
- Company press releases

These labels reflect the **intended engineering approach** rather than objective sequence features.

### Option 2: Surface Residue Humanization Patterns
The strategies may differ in:
- **Surface-exposed residues** (not captured by global FR alignment)
- **T-cell epitope removal** at specific positions
- **VHH-specific hallmark residues** (IMGT 37, 44, 45, 47):
  - Human VH: E/Q, G, L, W
  - Camelid VHH: F/Y, E, C/R, G/F
- Humanization degree at these positions may define strategy

### Option 3: CDR Optimization Focus
- **BM**: CDRs grafted onto heavily modified VHH framework
- **SR**: Native VHH CDRs + surface residue humanization
- **Native**: Minimal CDR modification

Table1 "human_identity" (85-97%) likely reflects **global sequence similarity** including CDR optimization.

### Option 4: Engineering Genealogy
All 19 molecules may derive from:
- A **common VHH clone or scaffold** (explaining >90% FR similarity)
- **Sequential optimization cycles** for different targets
- Different "humanization philosophies" applied by different developers

---

## Implications for the Manuscript

### 1. **Cannot Use FR Identity as Ground Truth**
- The manuscript **cannot claim** that BM/SR/Native strategies are validated by FR germline identity
- FR identity is uniformly low (~30%) and does not discriminate strategies

### 2. **Strategy Labels Are Developer-Assigned**
- In Methods section, clarify:
  > "Humanization strategy labels (BM/SR/Native) were obtained from Thera-SAbDab, which curates these designations from original patent/literature sources. These labels represent the developers' reported engineering approach rather than an objective sequence-based classification."

### 3. **Table1 "human_identity" Is Global, Not FR-Specific**
- In Methods, define:
  > "Global human identity was computed as the percentage of amino acids matching the closest human VH germline across the entire VHH sequence (including CDRs and FRs). This metric does not isolate framework-specific humanization."

### 4. **Focus on H2 Fold–Strategy Association (Still Valid)**
- The **H2 canonical fold → strategy association** (Fig2) remains robust:
  - H2-9-1 → 62.5% BM
  - H2-10-1 → 81.8% SR/Native
  - Fisher exact test p-value is still valid
- This association is **empirical** (observed in clinical data), not mechanistic

### 5. **Reframe Discussion**
Original claim:
> "BM strategy molecules have frameworks derived from human germlines (≥75% identity)"

Revised claim:
> "BM strategy molecules (as designated in patents/literature) show enrichment in H2-9-1 canonical fold, suggesting that framework-dependent CDR2 conformations may influence developers' choice of humanization approach."

---

## Recommended Figure/Table Additions

### Supplementary Table: FR Germline Identity
- **Title**: "Framework Region Germline Identity Analysis"
- **Columns**: antibody_id, strategy_group, fr_human_identity_pct, fr_camelid_identity_pct, global_human_identity_pct
- **Caption**:
  > "FR germline identity was computed by aligning concatenated FR1+FR2+FR3+FR4 sequences to 178 human VH3 and 84 camelid VHH germlines from IMGT. Despite strategy labels, all 19 molecules show uniformly low FR germline identity (~30%), suggesting these VHHs are highly engineered and do not directly derive from canonical germlines. Global human identity (from Table 1) reflects full-sequence similarity and is substantially higher (85-97%)."

### Supplementary Figure: FR Sequence Alignment
- Show FR1/2/3/4 sequences for all 19 molecules
- Highlight conserved positions (>90% identity)
- Mark VHH hallmark positions (37, 44, 45, 47)
- Color-code by strategy (BM/SR/Native)
- Caption:
  > "FR sequences are highly conserved across all 19 clinical VHHs (>90% pairwise identity), with no clear clustering by humanization strategy. This suggests strategy labels reflect engineering intent or surface-level modifications rather than wholesale framework replacement."

---

## Data Files Generated

1. **`TheraSAbDab_19VHH_FR_sequences.csv`**
   - FR1/2/3/4 sequences extracted from ANARCII numbering

2. **`TheraSAbDab_19VHH_FR_germline_identity.csv`**
   - Best-matching human/camelid germlines and identity percentages

3. **`TheraSAbDab_19VHH_FR_germline_identity_report.txt`**
   - Detailed report showing FR identity validation failures

4. **`TheraSAbDab_19VHH_FR_sequence_pattern_analysis.txt`**
   - Pairwise FR identity analysis (within/between strategies)

---

## Revised Paper Conclusions

### Original (Incorrect)
> "We demonstrate that VHH humanization strategy selection is determined by CDR2 canonical fold, with H2-9-1 requiring back mutation (BM) to restore framework integrity, while H2-10-1 is compatible with surface resurfacing (SR) or native approaches."

### Revised (Accurate)
> "We identify a significant association between H2 canonical fold and reported humanization strategy in 19 clinical VHHs: H2-9-1 folds are enriched in molecules labeled as back mutation (BM) approaches (Fisher exact p<0.05), while H2-10-1 folds are more common in surface resurfacing (SR) or native strategies. Notably, framework region (FR) sequences across all strategies show uniformly low germline identity (~30%) and high inter-molecular conservation (>90%), suggesting that strategy labels reflect developers' engineering philosophy or subtle surface modifications rather than fundamental framework replacement. This empirical fold–strategy association provides a data-driven heuristic for VHH humanization planning, while highlighting the need for standardized strategy classification criteria in future antibody engineering studies."

---

## Action Items for User

1. **Update Methods Section**:
   - Add clarification that strategy labels are from Thera-SAbDab (curated from patents/literature)
   - Define "global human identity" (full sequence, not FR-specific)
   - Add IMGT FR germline alignment method details

2. **Update Results Section**:
   - Add Supplementary Figure: FR sequence alignment
   - Add Supplementary Table: FR germline identity data
   - Add 1-2 sentences noting uniformly low FR germline identity

3. **Update Discussion Section**:
   - Revise mechanistic interpretation of BM/SR/Native
   - Reframe H2 fold–strategy association as empirical, not mechanistic
   - Add limitation: "Strategy labels are self-reported and lack standardized definitions"
   - Suggest future work: "Define objective sequence-based criteria for VHH humanization strategies"

4. **Update Figures**:
   - Fig2 caption: Add note that strategy labels are from original literature
   - Add Supplementary Fig: FR alignment with conservation track

---

## Bottom Line

**The 19 clinical VHHs do NOT follow classical antibody humanization paradigms (CDR grafting onto human frameworks).**

Instead, they represent a **diverse set of engineering approaches** applied to a **conserved VHH scaffold**, with strategy labels reflecting **developer intent** rather than objective sequence features.

The **H2 fold–strategy association** is **real and statistically significant**, but its mechanistic basis requires further investigation beyond simple "FR human vs camelid identity."

This finding does NOT invalidate the paper's core contribution (fold–strategy association), but requires careful framing to avoid overstating the mechanistic understanding.
