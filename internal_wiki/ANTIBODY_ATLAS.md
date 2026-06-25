# Clinical Antibody Atlas (1142)

The **InSynBio Clinical Antibody Atlas** is a proprietary database of clinical-stage antibody sequences and their associated metadata.

## 📂 **Atlas Directory**
We have generated detailed profiles for the high-confidence clinical cohort (n=70).

### [Browse All Profiles](./atlas/)

---

## 1. Database Structure
The database is stored in `data/clinical_kb/Antibody_Atlas_1142_Aggregated.json` (Internal Only).

### Key Fields (per record):
*   **INN**: International Nonproprietary Name.
*   **Target**: Primary antigen target.
*   **Format**: IgG1, IgG4, scFv, VHH, Bispecific, etc.
*   **Sequence**: Full VH/VL or VHH amino acid sequence.
*   **Germline**: IMGT-assigned V/D/J genes.
*   **CDR Profile**: Chothia/Kabat/IMGT boundaries.
*   **CMC Profile**: pI, aggregation propensity, hydrophobicity, etc.
*   **Clinical Evidence**: Phase, indication, and ADA (Anti-Drug Antibody) risk.

## 2. Analysis Summaries (Cohort n=70)

### Germline Usage
*   **VH**: IGHV3-23, IGHV1-69, IGHV3-30 are the most frequent.
*   **VL**: IGKV1-39, IGKV3-20, IGKV1-33 are the most frequent.

### Clinical Immunogenicity
The atlas includes clinical ADA rates used to calibrate the **ADA Risk Scorer (V2.1)**.

| Risk Tier | ADA Rate (%) | Example Drugs |
|---|---|---|
| **High** | > 15% | [Adalimumab](./atlas/Adalimumab.md) (30.0%), [Atezolizumab](./atlas/Atezolizumab.md) (30.0%) |
| **Medium** | 5–15% | [Astegolimab](./atlas/Astegolimab.md) (8.0%), [Benralizumab](./atlas/Benralizumab.md) (13.0%) |
| **Low** | < 5% | [Trastuzumab](./atlas/Trastuzumab.md) (8.0% - context dependent), [Denosumab](./atlas/Denosumab.md) (1.0%) |

---
**Reference Data:** [`data/clinical_kb/Antibody_Atlas_1142_Aggregated.json`](../data/clinical_kb/Antibody_Atlas_1142_Aggregated.json)
