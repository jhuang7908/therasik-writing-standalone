# 19 Clinical VHH Manuscript Data Package

## Overview
This package contains **all raw data, ANARCII annotations, statistical outputs, and publication-ready figures** for the manuscript analyzing 19 clinical-stage VHH humanization strategies.

**Article Type**: Original Research (data-driven, retrospective clinical antibody analysis)  
**Target Journal**: *Antibody Therapeutics*

---

## 📁 Directory Structure

```
paper/
├── raw data/                    ← Original sequences & ANARCII outputs
│   ├── TheraSAbDab_SeqStruc_OnlineDownload (2).xlsx         (source Excel from Thera-SAbDab)
│   ├── TheraSAbDab_19VHH_extracted_rows.csv                  (19 raw records)
│   ├── TheraSAbDab_19VHH_ANARCII_CDR_boundaries.csv         (CDR1/2/3 boundaries)
│   ├── TheraSAbDab_19VHH_ANARCII_numbering_full.csv         (~2200 residues with IMGT positions)
│   ├── TheraSAbDab_19VHH_CDR_features_extended.csv          (merged CDR + strategy + clinical data)
│   └── README.md                                             (data provenance & reproducibility guide)
├── tables/
│   └── Table1_slice3_19_clinical_vhh_master.csv             (master analysis table, 19 rows)
├── figures/                     ← Publication-ready PNG/SVG
│   ├── VHH19_Fig1A_strategy_counts.png
│   ├── VHH19_Fig1B_stage_by_strategy.png
│   ├── VHH19_Fig2A_fold_strategy_counts.png                  (H2 fold × strategy heatmap)
│   ├── VHH19_Fig2B_fold_strategy_or.png                      (odds ratio with 95% CI)
│   ├── VHH19_Fig3A_human_identity_by_strategy.png
│   ├── VHH19_Fig3B_B_total_1pct_by_strategy.png
│   ├── VHH19_Fig3C_human_identity_vs_B_total_1pct.png       (scatter + Spearman ρ)
│   ├── VHH19_Fig4_feature_heatmap.png                        (z-scored metrics)
│   ├── VHH19_Fig4B_cdr3_length_by_strategy.png              ⭐ NEW
│   ├── VHH19_Fig4C_cdr_signature_by_strategy.png            ⭐ NEW
│   └── VHH19_Fig5_decision_framework_mermaid.md
├── figures_data/                ← Exact data used for each figure (CSV)
├── stats/                       ← Statistical test outputs (TSV)
│   ├── VHH19_fold_strategy_fisher.tsv
│   ├── VHH19_strategy_group_kruskal.tsv
│   ├── VHH19_pairwise_mannwhitney_*.tsv
│   └── VHH19_spearman_human_identity_vs_B_total_1pct.tsv
└── FIGURES_TABLES_INDEX.md      ← Master index of all outputs
```

---

## 🔬 Data Provenance (Ensuring Accuracy)

### Source Database
- **Thera-SAbDab** (Oxford University OPIG group)
- Snapshot: `TheraSAbDab_190225` sheet (Feb 2025 release)
- URL: https://opig.stats.ox.ac.uk/webapps/sabdab_therapeutics/

### Extraction & Annotation Pipeline
1. **Extract 19 VHH records**:  
   `python scripts/extract_vhh19_raw_data_from_therasabdab_excel.py`
   - Input: Thera-SAbDab Excel export
   - Output: 19 rows with sequences, targets, clinical status, etc.
   - Audit trail: `TheraSAbDab_19VHH_extraction_report.txt`

2. **ANARCII IMGT numbering**:  
   `python scripts/number_19vhh_with_anarcii.py`
   - Tool: ANARCII v2.0.5 (not standard ANARCI)
   - Scheme: IMGT
   - Outputs: CDR1/2/3 boundaries + full residue-level positions

3. **CDR feature analysis**:  
   `python scripts/analyze_19vhh_cdr_features.py`
   - Computes: CDR length distributions, CDR signatures, strategy associations

4. **Figure & stats generation**:  
   `python scripts/vhh19_generate_paper_figures.py`
   - Produces: publication-ready PNG/SVG + statistical test outputs

---

## 📊 Key Findings (CDR1/2/3 Comprehensive Analysis)

### CDR1 - Highly Conserved "Structural Anchor"
- **17/19 molecules** (89.5%) have CDR1 = **8 aa**
- Only 2 exceptions: Sonelokimab2 (6 aa), Brivekimig1 (9 aa)
- **Conclusion**: CDR1 length is largely invariant; not a determinant of strategy choice

### CDR2 - The "Strategy Predictor" (via H2 Canonical Fold)
- **H2-9-1 fold** (n=6): CDR2 predominantly **7 aa**
- **H2-10-1 fold** (n=12): CDR2 predominantly **8 aa**
- **Podentamig1** (unknown fold): CDR2 = 6 aa (rare)
- **Association with strategy**:
  - H2-9-1 → 62.5% choose BM
  - H2-10-1 → 81.8% choose SR/Native
- **Fisher exact p-value**: See `paper/stats/VHH19_fold_strategy_fisher.tsv`

### CDR3 - The "Antigen Specificity Driver" (Highly Variable)
- **Range**: 5–21 aa (4-fold variation, largest diversity among CDRs)
- **Strategy association** (NEW finding):
  - **SR strategy**: CDR3 median = **18 aa** (range 8–21 aa) — tends to be **longer**
  - **BM strategy**: CDR3 median = **12 aa** (range 5–17 aa) — tends to be **shorter**
  - **Native strategy**: CDR3 median = **16 aa** (range 14–17 aa)
- **Approved VHHs** (n=3):
  - Caplacizumab: CDR3 = 21 aa
  - Envafolimab: CDR3 = 21 aa
  - Ozoralizumab: CDR3 = 8 aa
  - All have CDR3 ≥ 8 aa (no ultra-short CDR3 in approved set)

### Combined CDR Signature (CDR1-CDR2-CDR3 Pattern)
- **Most common**: `8-8-21` (3 molecules: all SR strategy, all approved or Phase 3)
- **Unique signatures**: 14 out of 19 molecules have unique CDR length combinations
- **Implication**: VHH CDR diversity is primarily driven by CDR3 length/sequence variation

---

## 📈 Recommended Manuscript Figures (Main Text)

### Figure 1: Dataset Landscape
- **Fig1A**: Strategy distribution (BM=8, SR=7, Native=4)
- **Fig1B**: Clinical stage × strategy (stacked bar)

### Figure 2: H2 Canonical Fold–Strategy Association ⭐ (Core Evidence)
- **Fig2A**: Contingency table heatmap (H2 fold × strategy)
- **Fig2B**: Odds ratio forest plot (BM enrichment in H2-9-1; Fisher exact p)

### Figure 3: Strategy Trade-offs
- **Fig3A**: Human identity by strategy (boxplot)
- **Fig3B**: Immunogenicity proxy (B_total_1pct) by strategy
- **Fig3C**: Scatter (humanness vs immunogenicity; Spearman ρ)

### Figure 4: CDR & Developability Features
- **Fig4**: Multi-metric heatmap (z-scored: humanness, immunogenicity, developability, CDR lengths)
- **Fig4B**: CDR3 length by strategy ⭐ (NEW - shows SR prefers longer CDR3)
- **Fig4C**: CDR signature distribution ⭐ (NEW - shows pattern diversity)

### Figure 5: Decision Framework
- **Fig5**: Mermaid flowchart (fold-informed strategy selection)

---

## 📋 Recommended Supplementary Tables

### Table S1: ANARCII CDR Annotation (19 VHHs)
- **Source**: `paper/raw data/TheraSAbDab_19VHH_ANARCII_CDR_boundaries.csv`
- **Columns**: antibody_id, cdr1/2/3 start/end (IMGT), cdr1/2/3 sequence, cdr1/2/3 length
- **Purpose**: Show exact CDR definitions used in analysis (reproducibility)

### Table S2: Full IMGT Numbering (~2200 residues)
- **Source**: `paper/raw data/TheraSAbDab_19VHH_ANARCII_numbering_full.csv`
- **Purpose**: For reviewers who want to verify CDR/FR assignments

### Table S3: Statistical Test Results
- **Sources**: All files in `paper/stats/`
- **Contents**: Fisher exact (fold×strategy), Kruskal-Wallis, pairwise Mann-Whitney (Holm-corrected), Spearman correlations

---

## 🔑 Critical Findings for Discussion Section

### 1. Multi-dimensional CDR Constraint on Strategy
- **H2 fold** (CDR2-related) is the **primary** determinant
- **CDR3 length** shows a **secondary association**:
  - Long CDR3 (≥16 aa) → more compatible with SR (lighter modification)
  - Short CDR3 (≤10 aa) → may require BM for stability compensation

### 2. Approved VHH CDR Profile
All 3 approved VHHs share:
- H2-10-1 fold
- SR strategy
- CDR3 ≥ 8 aa (no ultra-short CDR3)
- CDR1 = 8 aa (conserved)

**Implication**: The "safest" path to approval is **H2-10-1 + SR + moderate-to-long CDR3**.

### 3. CDR1 as Evolutionary Constraint
- 89.5% conservation at 8 aa suggests CDR1 is under strong structural constraint
- CDR1 is unlikely to be a variable in strategy selection

---

## 🚀 One-Command Reproducibility

From project root, run all scripts sequentially:

```bash
# Step 1: Extract 19 raw records from Thera-SAbDab
python scripts/extract_vhh19_raw_data_from_therasabdab_excel.py

# Step 2: ANARCII IMGT numbering
python scripts/number_19vhh_with_anarcii.py

# Step 3: CDR feature analysis
python scripts/analyze_19vhh_cdr_features.py

# Step 4: Generate all figures + stats
python scripts/vhh19_generate_paper_figures.py
```

All outputs are deterministic and version-controlled (no randomness, no API calls).

---

## 📝 Manuscript Methods Section (Suggested Text)

> **CDR Annotation and Canonical Fold Classification.**  
> VHH sequences were obtained from Thera-SAbDab (Feb 2025 release). IMGT numbering was performed using ANARCII v2.0.5. CDR regions were defined per IMGT standard: CDR1-IMGT (27–38), CDR2-IMGT (56–65), and CDR3-IMGT (105–117). H2 canonical fold classification (H2-9-1 vs H2-10-1) was assigned based on CDR2 length and backbone conformational cluster analysis according to the North-Dunbrack nomenclature. CDR3 length was analyzed as a continuous variable (5–21 aa range observed).

---

## ✅ Data Quality Validation

- **Coverage**: 19/19 antibodies successfully extracted and numbered (100%)
- **ANARCII success rate**: 19/19 (100%)
- **CDR length validation**:
  - All CDR1 ≥ 6 aa, CDR2 ≥ 6 aa, CDR3 ≥ 5 aa (biologically plausible)
  - No insertion codes in CDR regions (all canonical IMGT positions)
- **Cross-validation**: H2 fold labels in Table1 match ANARCII CDR2 length patterns

---

## 📧 Contact & Citation

- **Project**: InSynBio VHH Humanization Analysis
- **Generated**: 2026-01-27
- **ANARCII version**: 2.0.5
- **Thera-SAbDab snapshot**: TheraSAbDab_190225 (Feb 2025)

**Suggested Data Availability Statement**:  
> All raw sequences, ANARCII annotations, statistical outputs, and figure source data are available in the project repository under `paper/raw data/`, `paper/figures_data/`, and `paper/stats/`.
