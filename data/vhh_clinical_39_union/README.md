# 39 clinical VHH — sequence, target, clinical info

## 

|  |  |
|------|------|
|  | **39** |
|  | **0** |

Ozekibart ：Thera-SAbDab（OPIG）， `ozekibart_sequence.json`。

## （CSV / JSON）

****：
- `vhh_39_sequences_clinical_validated.csv`
- `vhh_39_sequences_clinical_validated.json`

****：

|  |  |
|------|------|
| **Name** | VHH （39 ） |
| **Sequence** |  VHH （38 ，Ozekibart ） |
| **Target** | （39 ） |
| **Clinical_Phase** | （Phase 1/2/3、Approved、TBC ） |
| **CDR3_Length_aa** | CDR3 （aa， Table1  19 ） |
| **CDR2_Fold** | CDR2 （H2-9-1 / H2-10-1 ） |
| **Classification** | （Class 1/2/3） |
| **Human_Identity_pct** | （%） |
| **In_Paper_Table1** |  Table1 （Y/N） |

## CDR/FR 

|  |  |
|------|------|
| （IMGT FR1–CDR1–FR2–CDR2–FR3–CDR3–FR4） | **39** |

****：`vhh_39_cdr_fr_segments.csv`、`vhh_39_cdr_fr_segments.json`  
****：`python scripts/vhh_39_cdr_fr_segments.py`（ anarcii + core.numbering.anarcii_adapter）

## 

- `clinical_supplement_curated.json` —  Target/Phase/Note（ validated ）
- `validation_report.txt` — 
- `vhh_39_sequences_clinical.csv` / `.json` —  supplement （ validated ）

## 

1. `python scripts/build_vhh_39_union.py --out-dir data/vhh_clinical_39_union` —  40  JSON +  Table1  39   
2. `python scripts/validate_vhh_39_sequences.py` —  clinical_supplement、、 validated CSV/JSON
