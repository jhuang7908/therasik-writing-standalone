# Paper Raw Data (19 Clinical VHHs)

This folder contains the **auditable raw data** for the 19 clinical-stage VHH molecules analyzed in the manuscript.

## Data Provenance

### Source: Thera-SAbDab Database
- **Original Excel export**: `TheraSAbDab_SeqStruc_OnlineDownload (2).xlsx`
  - Downloaded from: [Thera-SAbDab](https://opig.stats.ox.ac.uk/webapps/sabdab_therapeutics/)
  - Date: 2025-01 (sheet name: `TheraSAbDab_190225`)
  - Contains: Therapeutic antibody sequences, targets, clinical status, structures, etc.

### Extraction Scripts (for reproducibility)
- **Extractor**: `scripts/extract_vhh19_raw_data_from_therasabdab_excel.py`
  - Matches the 19 `antibody_id` values from `paper/tables/Table1_slice3_19_clinical_vhh_master.csv`
  - Generates audit trail with sheet name, row index, matched column/value
- **ANARCII Numbering**: `scripts/number_19vhh_with_anarcii.py`
  - Uses `anarcii` package (v2.0.5) with IMGT scheme
  - Extracts CDR1/2/3 boundaries and full residue-level IMGT positions

## Files in This Folder

### 1. Extracted Thera-SAbDab Records (19 rows, exact)
- **`TheraSAbDab_19VHH_extracted_rows.csv`**
  - The 19 rows from Thera-SAbDab Excel matching the master Table1 `antibody_id` values
  - Columns: `_sheet`, `_match_type`, `Therapeutic`, `Format`, `HeavySequence`, `Target`, `Highest_Clin_Trial`, etc.
  - **Auditable**: Each row includes `_table1_antibody_id` for cross-reference
- **`TheraSAbDab_19VHH_extracted_rows.md`**
  - Markdown version (if tabulate available; fallback message otherwise)
- **`TheraSAbDab_19VHH_extracted_rows_all_hits.csv`**
  - Pre-deduplication table (21 rows; includes 2 base-name hits that were later reduced to canonical IDs)
- **`TheraSAbDab_19VHH_extraction_report.txt`**
  - Audit report: source files, match details (sheet/row/column/match_type), coverage summary

### 2. ANARCII IMGT Numbering Outputs
- **`TheraSAbDab_19VHH_ANARCII_numbering_full.csv`**
  - All residues (∼2200 rows) with columns:
    - `antibody_id`, `seq_idx` (0-based), `imgt_position` (e.g., "37A"), `aa`, `region` (FR/CDR1/CDR2/CDR3)
  - **Use case**: Join with `Table1` on `antibody_id`; filter by `region` for CDR-specific analysis
- **`TheraSAbDab_19VHH_ANARCII_CDR_boundaries.csv`**
  - CDR summary (19 rows, one per antibody):
    - `cdr1_start_imgt`, `cdr1_end_imgt`, `cdr1_length`, `cdr1_sequence`
    - `cdr2_start_imgt`, `cdr2_end_imgt`, `cdr2_length`, `cdr2_sequence`
    - `cdr3_start_imgt`, `cdr3_end_imgt`, `cdr3_length`, `cdr3_sequence`
  - **Use case**: Quick lookup of CDR sequences/lengths for manuscript figures/tables
- **`TheraSAbDab_19VHH_ANARCII_summary.txt`**
  - Human-readable summary (UTF-8 plain text)
  - Shows CDR sequences/lengths for each antibody with IMGT position ranges

## IMGT CDR Definitions (VHH / Single-Domain Heavy Chain)
Per IMGT standard for VHH:
- **CDR1-IMGT**: positions 27–38 (variable length, typically 8 aa)
- **CDR2-IMGT**: positions 56–65 (variable length, typically 7–8 aa)
- **CDR3-IMGT**: positions 105–117 (highly variable, 5–21 aa in this dataset)

**Note on H2 Canonical Fold Labels**:
- `H2-9-1` and `H2-10-1` in `Table1.h2_class` refer to **North-Dunbrack canonical fold types**, not literal CDR2 lengths.
- Example: `H2-9-1` molecules in this dataset have CDR2 lengths of 7 aa (not 9).
- The fold type is determined by backbone torsion angles and key residue interactions, not just loop length.

## Reproducibility

To regenerate these files (from project root):

```bash
# Step 1: Extract 19 rows from Thera-SAbDab Excel
python scripts/extract_vhh19_raw_data_from_therasabdab_excel.py

# Step 2: Run ANARCII numbering on extracted sequences
python scripts/number_19vhh_with_anarcii.py
```

Both scripts validate input/output consistency and write audit reports.

## Integration with Manuscript

### Main Table (Table 1)
- **Master table**: `paper/tables/Table1_slice3_19_clinical_vhh_master.csv`
- Joins `raw data/TheraSAbDab_19VHH_extracted_rows.csv` (source provenance) with computed metrics (humanness, immunogenicity, developability)

### Supplementary Materials
- **Recommended Table S1**: Use `TheraSAbDab_19VHH_ANARCII_CDR_boundaries.csv` as-is or merged with Table1
- **Recommended Table S2**: Full IMGT numbering (`TheraSAbDab_19VHH_ANARCII_numbering_full.csv`) for reviewers

### Figure Data
- CDR length distributions, canonical fold associations: derived from `ANARCII_CDR_boundaries.csv`
- See `paper/figures_data/VHH19_Fig2_fold_strategy_table.csv` for fold×strategy contingency table

## Data Quality Notes

### Coverage
- **19/19 antibodies** successfully extracted from Thera-SAbDab (100% coverage)
- **19/19 antibodies** successfully numbered by ANARCII IMGT scheme (100% success)

### Known Ambiguities
- **Podentamig1**: `h2_class=unknown` in Table1; ANARCII shows CDR2 length = 6 aa (shorter than typical)
- **Gocatamig2** & **Podentamig2**: Base-name matched in Thera-SAbDab but deduplicated to canonical Table1 IDs

### Validation Checks (audit trail)
- All `HeavySequence` values are non-empty and ≥111 aa (shortest: Enristomig, 111 aa)
- CDR3 lengths range from 5 aa (Enristomig) to 21 aa (Caplacizumab, Envafolimab, Erfonrilimab)
- No insertion codes observed in CDR regions for these 19 molecules (all positions are canonical IMGT numbers)

## Contact & Version

- **Generated**: 2026-01-27 (UTC)
- **ANARCII version**: 2.0.5
- **Thera-SAbDab snapshot**: TheraSAbDab_190225 sheet (Feb 2025 release)
- **Project**: InSynBio VHH Humanization Analysis
