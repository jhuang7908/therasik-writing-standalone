# ACTES  — QA 、

## 1. QA 

### 1.1 

| QA  |  |
|-------|------|
| **design_info** |  uniprot_id / residue_range / references / verification / use_case ， |
| **status** | sequence_db  `status` ：verified / verified_vectorbuilder / mismatch_review / static |
| **UniProt ** |  uniprot_id + residue_range ， `verify_sequences.py`  UniProt  canonical_sequence  |
| **BLAST** |  `ACTES_RUN_BLAST=1`  blastp vs swissprot（ BLAST+） |

### 1.2 

- ** design_info**： 28 （CAR  SP/Hinge/TM/、5G/3G、CAR-NK、SynNotch、4-1BBL、UCOE、NFAT ）。 scFv、、linker、， design_info。
- **UniProt **：**** design_info.uniprot_id  design_info.residue_range ； 17 ， `verify_report.json`  `verify_report.md`。
- **** `status`  `sources`， `ACTES_sequences_canonical.fasta`  `ACTES_promoters.fasta` ；** UniProt **（ DNA、、 UniProt ）。

### 1.3 QA  UniProt 

|  |  |  design_info |  UniProt  |  | （ MISMATCH） |
|------|----------|----------------|-------------------|----------|---------------------------|
| CAR （SP/Hinge/TM/） | 20+ |  |  | 10 | CD8a_Short(AKP)、IgG4_SPLE |
| 5G/3G  | 2 |  uniprot_id |  | — | — |
| Binder（scFv ） | 15+ |  |  | — | / |
| /DNA | 12+ |  |  | — | — |
| SynNotch | 5 |  ref |  | — | Morsut 2016 |
| （linker、2A、OE） |  |  |  | — | — |

 **verify_report.md**；「」。

### 1.4 CAR 

 CAR （ UniProt/）：

|  |  |  |  |  |
|------|------|------|------|----------|
| **4-1BB_cyto** | EEEE | 33-36 | （UniProt Q07011 214-255）；C ， | ** canonical**（ UniProt ）； EEDE（FPEEEEGGCEL → FPEEDEGGCEL）， |
| **LAT ΔGADS**（ LINK CAR）| EEEE | 7-10 |  ΔGADS  |  LAT ；「EEQE」 EEEE （KRRRLLQEEEE… → KRRRLLQEEQE…）|
| CD3ζ、OX40、ICOS、CD8α 、CD28 TM  | RRR/GGG/SSS/TTT/VVV  |  |  |  |

****： **canonical_sequence （UniProt//）**，“”；（ 4-1BB EEDE、LAT ΔGADS EEQE）， design_info 、 canonical。

---

## 2. 

**** UniProt ， sequence_db 。

###  1： UniProt 

```bash
cd data/actes_sequences
python verify_sequences.py
```

- ****：`sequence_db.json`（ design_info.uniprot_id  residue_range ）。
- ****：`verify_report.json`、`verify_report.md`。
- ****：（ rest.uniprot.org）； `requests`  `urllib.request`。

###  2：

1.  `verify_report.md`，「UniProt 」。
2. ****： canonical_sequence  UniProt 。
3. ****：「」—— CD8a_Short（AKP ）、IgG4_SPLE_Long，； UniProt 、isoform、， BLAST 。

###  3：BLAST 

 BLAST+（blastp、swissprot ）：

```bash
set ACTES_RUN_BLAST=1
python verify_sequences.py
```

BLAST  `verify_report.json`  `blast` 。

###  4：/

- [ ]  `sources[].name/id`、`sequence`、`length`。
- [ ] ， `design_info.uniprot_id`、`residue_range`、`references`、`verification`、`use_case`。
- [ ] ， design_info  `mutations`  verification 「， MISMATCH」。
- [ ]  `ACTES_sequences_canonical.fasta`  `ACTES_promoters.fasta`  `ACTES_sequences_index.md`。
- [ ]  `verify_sequences.py`  report 。

---

## 3. 

### 3.1 CAR （SP）

| entry_id |  |  |
|----------|------|----------|
| **CD8a_SP** | CD8α （20 aa， Met） | CAR-T/CAR-NK/In Vivo CAR ；，。 |
| **GM-CSF_SP** | GM-CSF （P04141）| 16 aa（ M）；；A.1。 |
| **Notch1_SP** | Notch1 （22 aa） |  SynNotch ， NRR/TM/NICD 。 |
| **IL2_SP** | IL-2  |  IL-2 ， CAR 。 |
| **IgKappa_sig** |  Igκ （Igκ-sig, P01834）| 21 aa（ M）；；A.1；20 aa  M  sources。 |

### 3.2 （Hinge）

| entry_id |  |  |
|----------|------|----------|
| **CD8a_Short** | CD8α  48 aa（ VectorBuilder AKP ） | 2G/5G ；/（CD19、MSLN、GPC3）。 |
| **CD8a_Long** | CD8α stem+hinge 121 aa | （CD22、ROR1）；。 |
| **CD28_Medium** | CD28  39 aa | 、Treg CAR； CD28 TM 。 |
| **IgG4_SPLE_Long** | IgG4 Fc +CH2+CH3，S228P/L235E/P331S，232 aa | 、；SPLE  Fab-arm exchange、。 |

### 3.3 （TM）

| entry_id |  |  |
|----------|------|----------|
| **CD8a_TM** | CD8α TM 24 aa | 、； 4-1BB 。 |
| **CD28_TM** | CD28 TM 27 aa | 、；、； tonic 。 |
| **Notch1_TM** | Notch1 TM 21 aa |  SynNotch 。 |
| **DAP10_TM** | DAP10 TM | CAR-NK NKG2D-DAP10  scaffold 。 |

### 3.4 （2G / 3G / 5G）

| entry_id |  |  |
|----------|------|----------|
| **CD3z_cyto** | CD3ζ  113 aa，3×ITAM |  CAR ；。 |
| **4-1BB_cyto** | 4-1BB  42 aa | 2G ；、；、In Vivo CAR 。 |
| **CD28_cyto** | CD28  41 aa | 2G ；；、CAR-Treg。 |
| **OX40_cyto** | OX40  40 aa | 3G  ICOS+CD3ζ ； AICD 。 |
| **ICOS_cyto** | ICOS  36 aa | 3G  OX40+CD3ζ 。 |
| **IL2Rb_cyto** | IL-2Rβ  114 aa，Box1/Box2 | 5G；JAK1-STAT5，，。 |
| **4-1BB_IL2Rb_5G_cyto** | 4-1BB + (G4S)3 + IL2Rb + (G4S)2 + CD3ζ，295 aa | 5G ，。 |
| **OX40_ICOS_3G_cyto** | OX40 + (G4S)3 + ICOS + (G4S)3 + CD3ζ，218 aa | 3G 。 |
| **CAR-NK_2B4_cyto** | 2B4/CD244  125 aa | CAR-NK ； CD3ζ  DAP12 。 |

### 3.5 Binder（scFv / ）

| entry_id |  |  |
|----------|------|----------|
| **FMC63_scFv** |  CD19  scFv | B-ALL/DLBCL；Kymriah/Yescarta ； CD8a_Short。 |
| **m971_scFv** |  CD22  scFv | B-ALL/NHL；（ IgG4_SPLE_Long）。 |
| **bb2121_scFv** |  BCMA（c11D5.3） | ；ide-cel 。 |
| **OKT3_scFv / Foralumab_scFv / Teplizumab_scFv** |  CD3ε | In Vivo CAR ， T 。 |
| **SS1_scFv** |  MSLN（PDB 4F3F VL-VH 248 aa）| /；。 |
| **SS1_MSLN_hu_scFv** |  MSLN （VH-(GGGGS)3-VL 254 aa）| Amatuximab ；、、；sequence_db/FASTA； Q13421。 |
| **SS1_MSLN_CAR** | SS1 MSLN  CAR（CD8a_SP+SS1_hu+CD8a_Short+CD28_TM+4-1BB+CD3ζ 504 aa）|  CAR-T； NCT03054298、NCT02159716； MSLN 、/ PD-1  TGF-β 。 |
| **YP7_GPC3_hu_scFv** |  GPC3 （VH-(GGGGS)3-VL 245 aa； 511-560）| PMID 27667400、WO2019094482A1； HCC、；EC50 0.7 nM；sequence_db/FASTA。 |
| **YP7_GPC3_CAR** | YP7 GPC3  CAR（CD8a_SP+YP7_hu+CD8a_Short+CD28_TM+4-1BB+CD3ζ 495 aa）|  CAR-T；NCT02723942、NCT03146234；ORR 25-35%、DCR 65-75%； PD-1 、、iCasp9、。 |
| **Trastuzumab_scFv** |  HER2 | //GBM；。 |
| **Dinutuximab_scFv** |  GD2 | /DIPG；。 |

 Binder  `ACTES_sequences_index.md`  A.6。

### 3.6 CAR-NK、4-1BBL、SynNotch

| entry_id /  |  |  |
|-----------------|------|----------|
| **NKG2D_ectodomain** | NKG2D  73-216 | ； DAP10  CAR-NK。 |
| **DAP10_cyto / DAP10_TM** | DAP10 +TM | CAR-NK NKG2D-DAP10 。 |
| **CAR-NK_NKG2D** | NKG2D+G4S3+CD8a_Short+DAP10 |  CAR-NK 。 |
| **4-1BBL_ectodomain / 4-1BBL_Anchored** | 4-1BBL / |  4-1BB （ CAR-T ）。 |
| **Notch1_SP, SynNotch_NRR, Notch1_TM, SynNotch_RAM, SynNotch_ANK** | SynNotch  |  CAR、；→→NICD→（VP64/p65/Gal4 ）。 ADVANCED_CAR_ARCHITECTURES.md。 |
| **CD3z_cyto, CD28_cyto, 4-1BB_cyto + CD8a_Short, CD8a_TM, CD28_TM** | Split CAR  | Costim （scFvA–TM–CD28/4-1BB） Activator （scFvB–TM–CD3ζ） AND-gate；、。 ADVANCED_CAR_ARCHITECTURES.md §4。 |
| **MOG_ectodomain / MOG_CAAR** | MOG-CAAR（ MOG B ）| Q16653  1-125； CAAR = CD8a_SP + MOG_ecto + CD8a_Short + CD28_TM + CD3ζ。/EAE； iCasp9、Split-CAAR  AND-gate 。 |
| **ESK1_WT1_scFv / ESK1_WT1_CAR** | ESK1 WT1 TCRm（pMHC）|  WT1 RMFPNAPYL / HLA-A*02:01；scFv VL-(G4S)3-VH； CAR = CD8a_SP + scFv + CD8a_Short + CD28_TM + CD28_cyto + CD3ζ（497 aa）。AML、； HLA-A*02:01； AND-gate/iCAR、4-1BB 。 |
| **MAGE-A4_TCRm_scFv / MAGE-A4_TCRm_CAR** | MAGE-A4 TCRm（pMHC）|  MAGE-A4 GVYDGREHTV (230-239) / HLA-A*02:01；scFv 239 aa； CAR = CD8a_SP + scFv + CD8a_Short + CD28_TM + 4-1BB_cyto + CD3ζ（489 aa）。（NSCLC、、）； KD ~10-100 nM；（NY-ESO-1）、iCAR、SynNotch。 |
| **NY-ESO1_TCRm_scFv / NY-ESO1_TCRm_CAR** | NY-ESO-1 TCRm（pMHC）|  NY-ESO-1 SLLMWITQC (157-165) / HLA-A*02:01；scFv 248 aa； CAR = CD8a_SP + scFv + CD8a_Short + CD28_TM + 4-1BB_cyto + CD3ζ（498 aa）。；、、；（MAGE-A4）、 CAR、iCAR。 |

### 3.7 （SynNotch  / CRISPRa / Gal4-VP64）

| entry_id |  |  |
|----------|------|----------|
| **VP16_AD** | HSV VP16  P04486 413-490 (78 aa) | ；4×  + (GGGGS)₃  = VP64；SynNotch 、dCas9-VP64、Gal4-VP64。 |
| **p65_TAD** | NF-κB p65 (RelA) TAD Q04206 521-551 (31 aa) | ，； VP64 ；VPR 。 |
| **Gal4_AD** |  Gal4  P04386 768-881 (114 aa) |  Gal4 DBD  UAS ；/。 |
| **Rta_AD** | EBV Rta  P03211 1-60 (60 aa) | dCas9-VPR （VP64+p65+Rta）；。 |

：VPR > VP64 > p65 > Gal4。 REFERENCES.md §8。

### 3.8 （DNA）

| entry_id |  |  |
|----------|------|----------|
| **EF1a / EFS / PGK / SFFV / MSCV_LTR** |  | CAR 。 |
| **TRE3G** | （3rd gen） | /rtTA ；TRUCK 。 |
| **NFAT_Response** | 4×NFAT  | T ；TRUCK 。 |
| **UCOE_A2UCOE** |  |  CAR  5' 。 |

### 3.9  2A

| entry_id |  |  |
|----------|------|----------|
| **G4S1** | GGGGS  5 aa | 、；CAR-T_NK §9.3。 |
| **G4S3** | (G4S)3  16 aa | scFv VH-VL、（ 4-1BB–IL2Rb–CD3ζ）、SynNotch 。 |
| **G4S5** | (G4S)5  25 aa | scFv 、； §9.3。 |
| **G4S6** | (G4S)6  30 aa | ； §9.3。 |
| **EAAAK3** | EAAAK×3  15 aa | ；/； §9.3。 |
| **T2A / P2A** |  2A  | （ CAR + 、CAR + ）。 |

### 3.10 （、iCAR、）

| entry_id |  |  |
|----------|------|----------|
| **PDCD1_cyto** | PD-1  | Split iCAR 。 |
| **SLC7A11_OE / FSP1_OE / PGC1a_OE** | / | TME 、。 |
| **Membrane_IL7 / Membrane_IL21** |  | 。 |
| **Membrane_IL4_Inverted** | IL-4 | P05112 25-153 + IgG1  + CD8a TM + KRKRK； IL-4R+ 、TME ； Secreted_IL12 （-IL4-P2A-IL12-WPRE）。 |
| **Membrane_IL15** |  IL-15（195 aa）| IL2_SP +  IL-15 P40933 30-162 + IgG1  + CD8a TM + KRKRK； IL-15 、T/NK ；CAR-T/NK ； §9.4；PMID 25642771/26876175/28439030。 |
| **Secreted_IL12** |  IL-12（p35-G4S3-p40）| P29459 p35 23-219 + P29460 p40 23-328； Th1/NK/DC ； NFAT/TRE3G/SynNotch  Membrane_IL4_Inverted 。 |
| **BCMA_Treg_scFv / BCMA_Treg_CAR** | BCMA Treg-CAR| scFv VL-(G4S)3-VH； CAR = CD8a_SP + scFv + CD8a_Short + CD28_TM + CD28_cyto（384 aa）。 Treg； FOXP3 、iCasp9、AND-gate； bb2121 。 |
| **IL2RA_CD25 / FoxP3_Induction** | Treg/Stat5  |  T 。 |
| **FKBP12 / FRB_mTOR** | / | 。 |
| **FKBP_F36V** | AP20187  | F36V ；107 aa（ Met）； AP20187 ；DNA 321 bp  TGA  Trp。 |
| **DD_FKBP** | （degron）| FKBP12 ； Shield-1 ， Shield-1 ；107 aa； FKBP_F36V ：53 S、106–107 PE。 |
| **S4D** | SALL4  | SALL4  degron；28 aa；IMiD  CRBN/cullin E3 ，。 |
| **RQR8** | CD20/CD34  |  CD34 、； P2A-CAR 。 |
| **DmrA / DmrC** | AP21967  |  CAR ； FKBP-FRB  rapalogue AP21967。 |
| **ERT2** |  | ER LBD （G521R/C530S/M543A/L544A）；Gal4-ERT2-VP64 + UAS 。 |

---

## 4. 

|  |  |
|------|------|
| **sequence_db.json** | ； sources、alignment、status、design_info。 |
| **ACTES_sequences_canonical.fasta** |  FASTA。 |
| **ACTES_promoters.fasta** | DNA/ FASTA。 |
| **ACTES_sequences_index.md** |  entry_id 。 |
| **verify_sequences.py** | UniProt （+  BLAST）；。 |
| **verify_report.json / verify_report.md** | 。 |
| **SEQUENCE_DESIGN_INFO.md** | design_info 、、。 |
| **REFERENCES.md** |  PMID 。 |
| **ADVANCED_CAR_ARCHITECTURES.md** | 5G、TRUCK、SynNotch 。 |

---

****： `status` ；**UniProt ** design_info.uniprot_id  residue_range 。；， sequence_db  design_info 。
