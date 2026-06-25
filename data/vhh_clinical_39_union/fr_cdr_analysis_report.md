# VHH  CDR （39  VHH）

## 1. 

- ****：39  VHH，IMGT （vhh_39_cdr_fr_segments.json + validated ）。
- ****：
  - `paper/Submission_Package/FR3_CDR2_ANALYSIS_SUPPLEMENT.md`：FR3 N  **CDR2 ** （ CDR2→Tyr， CDR2→Thr），CDR2-FR3 junction 。
  - `paper/Submission_Package/MANUSCRIPT_ADDITIONS_REQUIRED.md`：FR4 N （IMGT 118） **CDR3 ** （ CDR3→Trp 100%）。
  - `paper/raw data/_.md`：FR  BM/SR/Native；H2 。

## 2. 

|  |  |  |  |
|------|------|--------|--------|
| FR1 | 25.0 | 25 | 25 |
| FR2 | 17.0 | 17 | 17 |
| FR3 | 38.0 | 38 | 38 |
| FR4 | 11.0 | 11 | 11 |
|  FR | 91.0 | 91 | 91 |
| CDR1 | 7.97 | 6 | 9 |
| CDR2 | 7.97 | 6 | 10 |
| CDR3 | 14.62 | 5 | 22 |
|  CDR | 30.56 | 20 | 38 |

## 3.  CDR （Spearman）

****：FR1–FR4  39 ****（FR1=25, FR2=17, FR3=38, FR4=11）， CDR （nan）。 **junction **， FR 。

|  | ρ | P |
|--------|---|---|
| CDR2_len vs CDR3_len | 0.208 | 0.204 |
| FR3_len vs CDR3_len | — | FR3  |
| FR4_len vs CDR3_len | — | FR4  |
| FR1_len vs CDR1_len | — | FR1  |

## 4.  CDR2 （ H2-9-1 / H2-10-1）

| CDR2  | N |  CDR3  |  FR3  |
|------------|---|----------------|----------------|
| 8 | 27 | 15.0 | 38.0 |
| 10 | 4 | 16.0 | 38.0 |

| CDR3  | N |  FR4  |  FR3  |
|------------|---|----------------|----------------|
| ≤11 aa | 8 | 11.0 | 38.0 |
| >11 aa | 31 | 11.0 | 38.0 |

## 5.  19 

- **FR **：39  FR1–FR4 ， VHH ****； ML  **CDR **、**junction **（ one-hot/embedding）， FR 。
- **FR3–CDR2**： FR3 N ****（Tyr/Thr） CDR2 canonical class （P=0.013）。****， FR3 。
- **FR4–CDR3**： FR4 N （IMGT 118） CDR3 （ CDR3→Trp 100%）。。
- **CDR2–CDR3**： CDR2_len  CDR3_len （ρ=0.21, P=0.20），「 CDR2 +  CDR3 」。

## 6. 

|  |  |  |
|------|------|------|
| **** |  | n=39，；/。 |
| **** |  | FR1–4 、CDR1–3 、CDR2_fold， 8–10 。 |
| **** |  | (1)  FR/CDR  CDR2_fold；(2)  CDR2/CDR3  FR ；(3) /。 |
| **** |  | （CDR2→FR3 ，CDR3→FR4 ）****，。 |
| **** |  +  ML |  junction （FR3-1  CDR2 ，IMGT 118  CDR3 ）； ML，/ + ， Spearman 。 |

---
：`scripts/analyze_vhh39_fr_cdr_relationship.py`
