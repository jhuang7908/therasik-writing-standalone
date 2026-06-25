# Strategy Classification Removed

**Date**: January 28, 2026

---

## Summary

All strategy-based classifications (Native/Back-Mutation/Resurfacing) have been removed from the manuscript and data files, as requested.

---

## Rationale

The original classification (Naive/BM/SR) was problematic because:

1. **Unknown Design Intent**: We do not have documentation of the actual humanization strategy used for each clinical antibody
2. **Retrospective Analysis**: Our data represents final sequences, not design choices
3. **Primary Finding**: CDR3 length—not design strategy—is the key determinant of FR2 humanization limits

---

## Changes Made

### 1. Manuscript Text
**File**: `Manuscript_VHH_Humanization.md` (and regenerated DOCX)

**Removed**:
- Detailed descriptions of CDR-grafting and resurfacing strategies
- References to "Back-Mutation" vs. "Resurfacing" classifications
- Statement about "Native" molecules

**Replaced with**:
- Brief mention that "various humanization strategies have been applied"
- Focus on structural constraints overriding design intent
- Emphasis that CDR3 length—not strategy—drives FR2 humanization

**Modified Sections**:
- Introduction: Simplified strategy discussion
- Results 3.2: Removed "did not align with traditionally assigned strategies"
- Results 3.4: Removed reference to "Native" labeling
- Discussion: Removed strategy-based classification language

---

### 2. Raw Data Files

**Modified Files**:

#### A. TheraSAbDab_19VHH_New_Classification_Table.csv
- **Location**: `Supplementary_Materials/Analysis_Reports/`
- **Removed column**: `strategy_group` (contained: Native, BM, SR)
- **Backup created**: `.csv.bak`

#### B. Publication_Source_Data.csv
- **Location**: `Supplementary_Materials/Source_Data/`
- **Removed column**: `Strategy`
- **Backup created**: `.csv.bak`

---

### 3. Regenerated Files

**Updated**:
1. `Manuscript_VHH_Humanization.docx` - Reflects all text changes
2. `Supplementary_Materials.zip` - Contains updated CSV files (without strategy columns)

**Unchanged** (strategy classification was never in these files):
- `Table1_Clinical_Landscape.csv`
- `TableS1_Residue_Frequencies.csv`
- Figure files (PNG)

---

## New Manuscript Focus

### Before:
- "Traditional classifications emphasize designer intent (Back-Mutation vs. Resurfacing)"
- "did not align with the traditionally assigned strategies"

### After:
- "Various humanization strategies have been applied"
- "structural constraints override strategic choices"
- "CDR3 loop length—not design strategy—is the primary determinant"

---

## Data Integrity

All statistical analyses remain unchanged because they were based on:
- CDR3 length groupings (≤11 vs >11 aa)
- Phylogenetic distances
- Residue frequencies at specific IMGT positions

**Strategy classification was never part of the statistical analysis.**

---

## Files with Backups

Original files (with strategy columns) backed up as:
- `TheraSAbDab_19VHH_New_Classification_Table.csv.bak`
- `Publication_Source_Data.csv.bak`

These backup files are **not** included in the ZIP archive for submission.

---

**Status**: ✅ All strategy-based classifications removed from manuscript and data files.
