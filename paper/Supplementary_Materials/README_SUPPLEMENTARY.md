# Supplementary Materials README

**Manuscript**: CDR3 Length Dictates the Humanization Limit of VHH Framework 2  
**Date**: January 27, 2026

---

## 📂 Directory Structure

```
Supplementary_Materials/
├── Source_Data/                    # 19 VHH original sequences and metadata
├── Sequences/                      # Reference germlines, FR extractions, FASTA files
├── Analysis_Reports/               # Phylogenetic trees, statistical outputs, residue analysis
└── README_SUPPLEMENTARY.md         # This file
```

---

## 1. Source_Data/

### `Publication_Source_Data.csv`
**Complete dataset for 19 clinical VHHs**

**Columns**:
- `antibody_id`: Unique identifier (e.g., Envafolimab, Caplacizumab)
- `full_sequence`: Complete VHH variable domain sequence (amino acids)
- `source`: Database source (Thera-SAbDab)
- `clinical_status`: Approval status (Approved, Phase 1-3, Discontinued)
- `target`: Therapeutic target (PD-L1, TNF-α, vWF, etc.)
- `cdr3_length`: CDR3 loop length (amino acids, range: 5-21)
- `h2_class`: CDR2 canonical fold (H2-9-1 or H2-10-1)
- `classification`: New phylogenetic class (Class 1/2/3)
- `human_identity_pct`: Global human identity (%)
- `camelid_identity_pct`: Global camelid identity (%)

**Data Source**: Retrieved from Thera-SAbDab (http://opig.stats.ox.ac.uk/webapps/newsabdab/therasabdab/) in January 2026.

---

## 2. Sequences/

### `Reference_Germlines.fasta`
**Germline sequences used as phylogenetic anchors**

Includes:
- Human IGHV3-23\*01 (most common humanization template)
- Human IGHV3-13\*01 (alternative human reference)
- Alpaca IGHV3-3\*01 (typical VHH germline)
- Mouse IGHV1-72\*01 (phylogenetic outgroup)

**Source**: IMGT/GENE-DB (http://www.imgt.org/genedb/)  
**Numbering**: IMGT unique numbering for V-DOMAIN

---

### `TheraSAbDab_19VHH_ANARCII_numbering_full.csv`
**IMGT-numbered sequences for all 19 VHHs**

**Purpose**: Standardized residue numbering for accurate FR/CDR boundary definition.

**Tool Used**: ANARCI (Antibody Numbering and Receptor ClassIfication)  
Reference: Dunbar, J. & Deane, C.M. (2016). ANARCI: antigen receptor numbering and receptor classification. *Bioinformatics*, 32(2), 298-300.

---

### `TheraSAbDab_19VHH_FR_sequences.csv`
**Extracted framework region sequences (FR1, FR2, FR3, FR4)**

**IMGT Position Ranges**:
- FR1: Positions 1-26
- FR2: Positions 39-55 (17 amino acids)
- FR3: Positions 66-104 (38 amino acids in our dataset, includes CDR2 C-terminal tail)
- FR4: Conserved J-region sequence (WGQGTLVTVSS)

**Columns**:
- `antibody_id`
- `fr1_sequence`, `fr2_sequence`, `fr3_sequence`, `fr4_sequence`
- `fr1_human_identity`, `fr2_human_identity`, etc. (% identity to Human IGHV3-23)
- `fr1_camelid_identity`, `fr2_camelid_identity`, etc. (% identity to Alpaca IGHV3-3)

---

### FASTA Files for Sequence Logos

**FR1**:
- `FR1_Short_CDR3_lt11.fasta` (N=5 VHHs)
- `FR1_Long_CDR3_ge11.fasta` (N=14 VHHs)

**FR2**:
- `FR2_Short_CDR3_lt11.fasta` (N=5 VHHs)
- `FR2_long_CDR3_lt11.fasta` (N=14 VHHs) *[Note: filename typo]*

**FR3** (first 20 amino acids, for logo clarity):
- `FR3_Start_Long_CDR3_ge11.fasta` (N=14 VHHs)

**FR4** (if needed):
- To be generated using `generate_logo_data_fr1_fr4.py`

**Usage**: Upload to WebLogo (http://weblogo.threeplusone.com/) to generate sequence conservation plots.

---

## 3. Analysis_Reports/

### Phylogenetic Analysis

#### Newick Tree Files:
- `TheraSAbDab_19VHH_FR2_anchored.newick` → FR2 region tree
- `TheraSAbDab_19VHH_FR3_anchored.newick` → FR3 region tree
- `TheraSAbDab_19VHH_FR2_FR3_anchored.newick` → Combined FR2+FR3 tree
- `Tree_FR2_Detailed.newick` → Enhanced FR2 tree with metadata
- `Tree_Combined_Detailed.newick` → Enhanced combined tree

**Viewing**: Open in phylogenetic tree viewers (e.g., FigTree, iTOL, or Python ETE3)

---

#### Statistical Reports:

### `TheraSAbDab_19VHH_phylogeny_discrimination_analysis.txt`
**Tests which factors (Strategy, CDR2 fold, CDR3 length) drive phylogenetic clustering**

**Key Results**:
- **FR2 Region**:
  - Strategy discrimination: P = 0.0251 ✅
  - CDR3 length correlation: ρ = -0.604, P = 0.0062 ✅✅
  - CDR2 fold discrimination: P = 0.0734 (not significant)
  
- **FR3 Region**:
  - No significant discrimination by any factor (P > 0.05)

- **FR2+FR3 Combined**:
  - Strategy discrimination: P = 0.0106 ✅
  - CDR3 length correlation: ρ = -0.486, P = 0.0350 ✅

**Interpretation**: FR2 evolution is driven by CDR3 length, not CDR2 structure.

---

### `TheraSAbDab_19VHH_clustering_comparison.txt`
**Compares CDR3 length vs CDR2 fold as clustering drivers**

**Key Results**:
- **FR2 Region**:
  - CDR3 Length Association: **P = 0.00175** (Kruskal-Wallis H = 9.79) ✅✅
  - CDR2 Fold Association: P = 0.77096 (Chi-square = 0.52) ❌

**Conclusion**: CDR3 length is the **dominant driver** of FR2 clustering.

---

### `TheraSAbDab_19VHH_New_Classification.txt`
**Data-driven 3-class system based on FR2+FR3 phylogenetic clustering**

**Classes**:
1. **Class 1 (N=5)**: Short CDR3 (mean 9.0 aa), High humanization (93.2% human)
   - Members: Brivekimig2, Enristomig, Letolizumab, Ozoralizumab, Porustobart

2. **Class 2 (N=10)**: Long CDR3 (mean 17.6 aa), Moderate humanization (87.9% human)
   - Members: Envafolimab, Sonelokimab1/2, Gefurulimab, Erfonrilimab, etc.

3. **Class 3 (N=4)**: Intermediate CDR3 (mean 15.2 aa), Moderate humanization (87.2% human)
   - Members: Caplacizumab, Gocatamig2, Podentamig1, Vobarilizumab

**Key Finding**: Even "Native" VHHs have only ~32-34% camelid identity (far from 100%), indicating **all clinical VHHs are heavily engineered**.

---

### Residue-Level Analysis

### `TheraSAbDab_19VHH_Hallmark_Vernier_Analysis_Corrected.txt`
**Amino acid frequencies at VHH Hallmark and Vernier zone positions**

**Stratified by CDR3 Length**:
- Short CDR3 (≤11 aa, N=5)
- Long CDR3 (>11 aa, N=14)

**Critical Findings**:

**Hallmark Position 47 (FR2)**:
- Long CDR3: **Arg (R)** in 13/14 (93%) → Hydrophilic, VHH-typical
- Short CDR3: **Leu (L)** or **Pro (P)** in 2/5 (40%) → Hydrophobic, human-like

**Interpretation**: Position 47 acts as a **"solubility switch"**. Long CDR3 VHHs must retain Arg47 to prevent aggregation, while short CDR3 VHHs can tolerate humanization to Leu/Pro.

**Vernier Position 71 (FR3)**:
- **Arg (R)** in 19/19 (100%) → Universally conserved
- Identical to Human IGHV3-23 germline
- Structural anchor for CDR3 loop

**Interpretation**: FR3 is a **"pre-humanized" scaffold** where camelid and human sequences naturally converge.

---

### `TheraSAbDab_19VHH_Extended_Vernier_Analysis.txt`
**Extended analysis of FR1 and FR3 Vernier zones**

**FR1 Vernier (Pos 27-30)**:
- Sequence: **Cys-Ala-Ala-Ser**
- Conservation: 100% across both CDR3 length groups
- Function: Anchor CDR1, include Cys23-Cys104 disulfide precursor

**FR3 Vernier (Pos 93-94)**:
- Sequence: **Tyr-Cys**
- Conservation: 100% across both groups
- Function: Cys94 forms CDR1-CDR3 disulfide bond

**Conclusion**: FR1 and FR3 Vernier zones are evolutionarily "frozen," maintaining structural integrity regardless of CDR3 constraints.

---

### `TheraSAbDab_19VHH_FR2_Vernier_Analysis.txt`
**FR2 Vernier zone residues (Pos 48-49)**

**Long CDR3 Group**:
- Pos 48: **Ala (64%)**, Ser (29%)
- Pos 49: **Ala (57%)**, Lys (14%)
- Pattern: Ala-Ala motif (typical VHH)

**Short CDR3 Group**:
- Pos 48: **Ser (80%)**, Ala (20%)
- Pos 49: **Gly/Ser (50%)**, Thr/Glu (50%)
- Pattern: Ser-Gly/Ser motif (human-like variability)

**Conclusion**: FR2 Vernier residues co-evolve with Hallmark 47, adapting to CDR3 constraints.

---

## 🔬 Methods Summary

### Sequence Acquisition
- Source: Thera-SAbDab (http://opig.stats.ox.ac.uk/webapps/newsabdab/therasabdab/)
- Date: January 2026
- Criteria: Clinical status ≥ Phase 1, single-domain VHH format

### IMGT Numbering
- Tool: ANARCI v1.3
- Scheme: IMGT (International ImMunoGeneTics)
- Reference: Lefranc, M.P., et al. (2015). IMGT. *Nucleic Acids Research*, 43(D1), D413-D422.

### Phylogenetic Analysis
- Distance metric: Normalized Hamming distance (p-distance)
- Clustering method: UPGMA (Unweighted Pair Group Method with Arithmetic mean)
- Software: SciPy v1.11 (Python)
- Tree format: Newick

### Statistical Tests
- **Kruskal-Wallis H-test**: Non-parametric test for differences in CDR3 length across clusters
- **Chi-square test**: Association between clusters and CDR2 canonical folds
- **Spearman correlation**: Monotonic relationship between CDR3 length and phylogenetic distance
- **Significance threshold**: P < 0.05

### Residue Analysis
- Hallmark positions: IMGT 37, 44, 45, 47 (Muyldermans, S. 2013)
- Vernier positions: IMGT 2, 4, 27, 28, 30, 48, 49, 66, 67, 68, 71, 78, 82, 83, 84, 87, 89, 91, 93, 94 (Foote & Winter, 1992)
- Extraction: Motif-based alignment to correct for boundary ambiguities

---

## 📊 Data Transparency Commitment

All data, analysis scripts, and results are provided for full reproducibility. Any researcher can:

1. **Verify sequences**: Download 19 VHHs from Thera-SAbDab using provided antibody IDs
2. **Reproduce IMGT numbering**: Run ANARCI on provided sequences
3. **Reproduce phylogenetic trees**: Use provided FR sequences and reference germlines
4. **Verify statistics**: Re-run tests on provided CSV data

---

## 📧 Data Requests

For questions about the data or analysis methods, contact:  
[Corresponding Author Email - TO BE FILLED]

---

## 📜 Data Availability Statement

All data generated or analyzed during this study are included in this Supplementary Materials package. The 19 VHH sequences are publicly available from Thera-SAbDab (http://opig.stats.ox.ac.uk/webapps/newsabdab/therasabdab/). Reference germline sequences are from IMGT/GENE-DB (http://www.imgt.org/genedb/).

---

**Prepared**: January 27, 2026  
**Last Updated**: January 27, 2026
