# ACTES  — 

**、、**，。

---

## 1. 

 ACTES ，** `sequence_db.json`  `ACTES_sequences_canonical.fasta` **。

|  |  entry_id |  |  |
|------|----------------|------|----------|
| **** | VP16_AD, p65_TAD, Gal4_AD, Rta_AD | 78, 31, 114, 60 aa | SynNotch 、CRISPRa/VPR、Gal4-VP64 |
| **Split CAR** | （； CD3z/CD28/4-1BB/CD8a） | — |  Costim/Activator； ADVANCED_CAR_ARCHITECTURES §4 |
| **** | Membrane_IL4_Inverted, Secreted_IL12 | 191, 537 aa |  IL-4、 p35-G4S3-p40；TME/TRUCK |
| **** | RQR8, DmrA, DmrC, ERT2 | 103, 126, 112, 282 aa | CD20/CD34 、AP21967 CID、 |
| **CAAR** | MOG_ectodomain, MOG_CAAR | 125, 333 aa | MOG  1-125； MOG B （MS/EAE）|
| **Treg-CAR** | BCMA_Treg_scFv, BCMA_Treg_CAR | 248, 384 aa | BCMA  Treg-CAR（MM）|
| **TCRm（pMHC）** | ESK1_WT1_scFv, ESK1_WT1_CAR | 248, 497 aa | WT1 RMFPNAPYL / HLA-A*02:01；AML、 |
| **TCRm（pMHC）** | MAGE-A4_TCRm_scFv, MAGE-A4_TCRm_CAR | 239, 489 aa | MAGE-A4 GVYDGREHTV / HLA-A*02:01； |
| **TCRm（pMHC）** | NY-ESO1_TCRm_scFv, NY-ESO1_TCRm_CAR | 248, 498 aa | NY-ESO-1 SLLMWITQC / HLA-A*02:01；、 |
| ** MSLN** | SS1_MSLN_hu_scFv, SS1_MSLN_CAR | 254, 504 aa |  MSLN (Q13421)； SS1（Amatuximab ）；、、；NCT03054298、NCT02159716 |
| ** GPC3** | YP7_GPC3_hu_scFv, YP7_GPC3_CAR | 245, 495 aa |  GPC3 (P51654)； YP7（ 511-560）；PMID 27667400、WO2019094482A1；NCT02723942、NCT03146234 |

---

## 2. 

### 2.1 

|  |  |  |
|------|------|----------|
| `sequence_db.json` |  entry 、sources、design_info | ✅  |
| `ACTES_sequences_canonical.fasta` |  FASTA（ entry_id）| ✅  sequence_db  |
| `ACTES_sequences_index.md` |  ↔ entry_id ↔  ↔  | ✅  |

### 2.2 

|  |  |  |
|------|------|----------|
| `SEQUENCE_QA_AND_APPLICATION.md` | QA 、、 | ✅ §3.6/3.7/3.10  |
| `REFERENCES.md` | §8 ；§9 ；§10 ；§11 CAAR/MOG；§12 Treg；§13 TCRm | ✅  |
| `ADVANCED_CAR_ARCHITECTURES.md` | §4 Split CAR（Costim/Activator）| ✅  |
| `ACTES_WHITE_PAPER.md` |  → sequence_db/FASTA | ✅  |

### 2.3 

|  |  |  |
|------|------|----------|
| `functional_domains.json` | SynNotch tf_domain、TF_Gal4_VP64  VP16_AD/p65_TAD/Gal4_AD/Rta_AD | ✅  seq_ref |

---

## 3. 

### 3.1 

- **sequence_db.json** ↔ **ACTES_sequences_canonical.fasta**： entry_id  `canonical_sequence`  FASTA ****，。
- **ACTES_sequences_index.md**：， status  sequence_db 。

### 3.2 

| / |  |  |
|-----------|------|------|
| CD3ζ |  P20963 52-164、MGGK**Q**RRK（113 aa）|  MGGKPRRK  verify_report |
| RQR8 |  89 aa， 103 aa |  DB/FASTA 103 aa ； 89 aa  |
| Membrane_IL4_Inverted |  173 aa， 191 aa |  191 aa  |
| ESK1 / BCMA_Treg scFv |  ESK1/bb2121  | design_info “/ bb2121 ” |
| MAGE-A4_TCRm_scFv | VL  FSGSGSGTD（ FSGSGSGSGTD）|  |
| FKBP_F36V |  321 bp DNA；TGA  Trp，107 aa； Met |  sequence_db/FASTA ；Ref: Chem Rev. 110:3315; Sci Rep. 4:6127 |
| DD_FKBP | （DD）；321 bp；TGA→W，107 aa； FKBP_F36V ：53 S、106–107 PE；Shield-1  | Ref: Bioorg Med Chem Lett. 18:5941; PLoS One. 4:e6529 |
| S4D | SALL4 degron；84 bp → 28 aa；IMiD/CRBN neosubstrate | Ref: Commun Biol. 3:515 (2020) |
| GM-CSF_SP | P04141  1-16；16 aa（ M）； | UniProt P04141 |
| IgKappa_sig |  Igκ  P01834；A.1  21 aa（ M）；20 aa  M  sources | J Immunol Methods. 152:89 (1992); UniProt P01834 |
| G4S1/G4S5/G4S6/EAAAK3 | ； §9.3；5/25/30/15 aa | PMID 12837772, 15225637, 19397431 |
| Membrane_IL15 |  IL-15；195 aa（ 200）；IL2_SP+IL15++CD8a TM+KRKRK |  §9.4；PMID 25642771, 26876175, 28439030 |

### 3.3 

-  `python verify_sequences.py`（ `ACTES_RUN_BLAST=1`） UniProt ； `verify_report.json` / `verify_report.md`。
-  `design_info.uniprot_id`  `residue_range`  UniProt ；（ MOG_CAAR、 TCRm_CAR）， UniProt 。
- ****： UniProt  MISMATCH（ VP16_AD、p65_TAD、Gal4_AD、Rta_AD、MOG_ectodomain、Membrane_IL4_Inverted ）， linker/、； `sequence_db`  FASTA  **canonical_sequence** ， `verify_report.md`。

---

## 4. 

### 4.1 

- [ ] `sequence_db.json`  JSON 
- [ ] `ACTES_sequences_canonical.fasta`  entry_id  len=  sequence_db  length 
- [ ] `ACTES_sequences_index.md` “ A ”“sequence_db entry_id”
- [ ] `REFERENCES.md`  PMID/UniProt  design_info  references 
- [ ] `ACTES_WHITE_PAPER.md` “✅”“sequence_db / ACTES_sequences_canonical.fasta”

### 4.2 

|  |  |
|------|----------|
|  CAR（5G、TRUCK、SynNotch、Split CAR）| `ADVANCED_CAR_ARCHITECTURES.md` |
| （VP64、p65、Gal4、Rta）| `sequence_db` VP16_AD, p65_TAD, Gal4_AD, Rta_AD；`REFERENCES.md` §8 |
| （RQR8、DmrA/DmrC、ERT2）| `sequence_db`  entry_id；`REFERENCES.md` §10 |
| CAAR（MOG）| MOG_ectodomain, MOG_CAAR；`REFERENCES.md` §11 |
| Treg-CAR（BCMA）| BCMA_Treg_scFv, BCMA_Treg_CAR；`REFERENCES.md` §12 |
| TCRm（WT1、MAGE-A4、NY-ESO-1）| ESK1_WT1_*, MAGE-A4_TCRm_*, NY-ESO1_TCRm_*；`REFERENCES.md` §13 |
| （IL-4 、 IL-12）| Membrane_IL4_Inverted, Secreted_IL12；`REFERENCES.md` §9 |
|  QA | `SEQUENCE_QA_AND_APPLICATION.md`；`verify_report.md` |

### 4.2.1 「CAR-T_NK」（§9.1–9.4）

：`projects/humanized_mice/CAR/CAR-T_NK.md`。。

|  | / | ACTES entry_id /  |  |
|------------|-----------------|------------------------|------|
| **9.1 GM-CSF_SP** | MAPARSPSPSTQPWEHVNA（19 aa）； P04141 aa 1-17 | **GM-CSF_SP**：MTPLLLQLLLWLQLLL（16 aa），P04141 1-16 |  UniProt P04141  N （P04141  MTPLLL…）；** ACTES/UniProt **。 |
| **9.2 IgKappa_SP** | METDTLLLWVLLLWVPGSTG（20 aa）； P01834 aa 1-20 | **IgKappa_sig**：METDTLLLWVLLLWVPGSTGD（21 aa）， Asp |  Gly20–Asp21；ACTES  A.1  21 aa（ D）。 |
| **9.3 Linkers** | G4S1(5aa)、G4S5(25aa)、G4S6(30aa)、EAAAK3(15aa)  DNA | **G4S1、G4S5、G4S6、EAAAK3**  | sequence_db + FASTA； §9.3 。 |
| **9.4 Membrane_IL15** | IL2_SP +  IL-15 +  + CD8a TM + KRKRK（195 aa）| **Membrane_IL15**  | sequence_db + FASTA； §9.4； 195 aa（ 200 aa）。 |

****： **ACTES sequence_db + FASTA** （GM-CSF  P04141 1-16；Igκ  21 aa  M）； GM-CSF 19 aa  Igκ 20 aa /，“ ACTES ”“”。

### 4.3 

- ****： `sequence_db.json`  `version` 。
- ****：，。

---

****：，、、； §4.1 。
