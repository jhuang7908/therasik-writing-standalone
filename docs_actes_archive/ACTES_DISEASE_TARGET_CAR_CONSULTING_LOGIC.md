# ACTES --CAR 

****（ /  / ）→ ****（、、、）→ ****（CAR-T / CAR-M / CAR-NK）→ **CAR ** → ** Biomarker /  / ** ，**、、**。

 [ACTES_WHITE_PAPER.md](ACTES_WHITE_PAPER.md) Ch.4、 A.14  [data/actes_sequences/](data/actes_sequences/) ； `sequence_db.json`  `ACTES_sequences_canonical.fasta` 。****：→→→  [ACTES_KNOWLEDGE_BASE_LINKS.md](ACTES_KNOWLEDGE_BASE_LINKS.md)。

---

## 1. 

|  |  |  |  |
|----------|----------|---------------------|----------|
| **** | 、、GBM/DIPG、、、NSCLC、 | CAR-T + CAR-M ；CAR-NK  MHC-I  | TME 、、 |
| **** | AML、B-ALL、DLBCL、 | CAR-T（αβ T） | 、（ AML）|
| **** | SLE、、 | CAR-Treg / CAAR-Treg | 、Treg 、 |

---

## 2. 

### 2.1 （、）

|  |  | / | / |  | sequence_db  Binder |
|------|----------|----------------|---------------|---------------|--------------------------|
| **** | HER2 (ERBB2) | –（IHC 2+/3+）； |  IV； | CAR-T（CD28  + / Hinge）| Trastuzumab_scFv；CD28_Medium Hinge |
| **** | CLDN18.2 | ； | ； | CAR-T +  CAR-NK | / scFv|
| **** | GPC3 | （HCC  70%）； | ； | CAR-T（CD8a_Short + CD28 + ）| YP7_GPC3_hu_scFv；YP7_GPC3_CAR |
| **//** | MSLN | ； |  GPI ； | CAR-T + CAR-M  | SS1_MSLN_hu_scFv；SS1_MSLN_CAR |
| **GBM/DIPG** | GD2 / B7-H3 | ；CNS  | /； | CAR-T（4-1BB + ）|  GD2/B7-H3 scFv（Enoblituzumab_scFv  B7-H3）|
| **** | GD2 |  | ； | CAR-T（4-1BB；）| / GD2 scFv |

****： → **** **SynNotch AND **；TME  → ****（TGFB_DNR、Membrane_IL15、GPX4_Enhanced）； → **CAR-M** 。

### 2.2 （ AML、B-ALL、）

|  |  | / | / |  | sequence_db  Binder |
|------|----------|----------------|---------------|---------------|--------------------------|
| **AML** | CD33 / CLL-1 / FLT3 / CD123 | CD33 >90%； | ； | CAR-T ****（CLL-1+CD33）；iCasp9  |  CD33/CLL-1（ CD123/CLL1）|
| **AML** | WT1 (pMHC) | ；HLA-A*02:01 | -MHC；TCRm | CAR-T（TCRm ）| ESK1_WT1_scFv；ESK1_WT1_CAR |
| **B-ALL** | CD19 / CD22 | CD19 ； CD22 | ； | CAR-T（4-1BB）；Tandem  | FMC63_scFv（CD19）；CD22  scFv |
| **DLBCL** | CD19 / CD79b |  | BCR ； | CAR-T（CD28  4-1BB）| FMC63_scFv；CD79b  |
| **** | BCMA / CD38 | BCMA ；CD38  | ； | CAR-T ****；4-1BB | bb2121_scFv / BCMA_Treg；Daratumumab  CD38 |

****： → **** **Tandem CAR**；AML  → **** **CD33 KO HSCT **； → **4-1BB**（ Treg ）。

### 2.3 （ SLE ）

|  |  | / | / |  | sequence_db  Binder |
|------|----------|----------------|---------------|---------------|--------------------------|
| **SLE** | CD19 / CD20 / BAFF-R | B ； CD19  | ； | **CAR-Treg**（CD28 ； 4-1BB）| CD19→FMC63；CD20→RQR8 /；BAFF-R  |
| **** | Dsg3 | ； |  | **CAAR-Treg**（Dsg3  Binder）| MOG_CAAR ；Dsg3  |

****： CAR（Treg/CAAR）→ **CD28 ** + **FoxP3 **； **tEGFR**； B/T 。

---

## 3.  CAR 

|  |  |  |  Hinge |  Binder  | / |
|------|----------|------------|------------|------------------|-----------|
| **CAR-T（αβ T）** | 、、 | 4-1BB+CD3ζ（/）；CD28+CD3ζ（/）| CD8a_Short / CD28_Medium / IgG4_SPLE_Long | scFv / VHH / TCRm | ：TGFB_DNR、Membrane_IL15、GPX4；PD-1 KO  |
| **CAR-M** | | FcR-γ（ITAM）| / |  scFv |  MMP； CAR-T  |
| **CAR-NK** | 、（MHC-I ）| NKG2D-DAP10 / 2B4+CD3ζ | CD8a_Short | scFv  NKG2D  | Membrane_IL15 ；CAR-NK_NKG2D |
| **CAR-Treg** | （SLE、RA、）| **CD28+CD3ζ**（ 4-1BB）| CD8a_Short | CD19/CD20/BAFF-R / CAAR | FoxP3_Induction；tEGFR  |

**Linker **： → G4S1/G4S3；scFv VH-VL → G4S3/G4S5；/ → EAAAK3。 sequence_db：G4S1、G4S3、G4S5、G4S6、EAAAK3。

**Hinge **： → CD8a_Short；/ → CD28_Medium  IgG4_SPLE_Long。 A.2。

---

## 4. 、Binder、Linker、Hinge、

- ****：/、mRNA  CAR、γδ CAR-T、SynNotch/Split CAR、iCAR、CAAR。
- **Binder**：scFv（FMC63、SS1、YP7、Trastuzumab、Enoblituzumab ）、VHH、TCRm（ESK1 WT1、MAGE-A4、NY-ESO-1）、CAAR （MOG、Dsg3）。
- **Linker**：G4S1(5aa)、G4S3(16aa)、G4S5(25aa)、G4S6(30aa)、EAAAK3(15aa)； sequence_db。
- **Hinge**：CD8a_Short、CD28_Medium、IgG4_SPLE_Long、CD8a_Long； A.2。
- ****：CD3ζ； 4-1BB / CD28 / OX40 / ICOS；5G（4-1BB_IL2Rb_5G_cyto）；CAR-NK 2B4/DAP10。
- **/**：TGFB_DNR、Membrane_IL15、GPX4_Enhanced、4-1BBL_Anchored、Secreted_IL12（TRUCK）、PD-1 KO、FoxP3_Induction（Treg）、iCasp9/tEGFR/RQR8 。

 [ACTES_sequences_index.md](data/actes_sequences/ACTES_sequences_index.md)  [ACTES_WHITE_PAPER.md](ACTES_WHITE_PAPER.md)  A  entry_id 。

---

## 5.  Biomarker、、

### 5.1 Biomarker

|  |  |  |
|------|------|------|
| **** | （ MFI）、IHC 、（ BCMA、MSLN）| ； |
| **** | HLA （TCRm  HLA-A*02:01）、 WGS、、 | - |
| **** | Tscm （>5% ）、CD4:CD8、 |  PD-1 KO |
| **/** | 、CRS 、ICANS、CR/PR、PFS/OS、 |  CR； PFS/OS |

### 5.2 

- ****：CRS/ICANS 、iCasp9/tEGFR 、RQR8 、/。
- ****： CR 、MRD ； ORR、PFS、OS；（ BILAG、SLEDAI）。

### 5.3 

|  |  |  |
|------|------|------|
| **** | /IF ； ELISA | — |
| **CAR ** | 、、； | /； |
| **** | ；CRS | ；CRS |
| **/** | ； | ； |
| **/Treg** | ；FoxP3 ； | （ SLE ）|

---

## 6. （ +  +  + ）

（「 HER2 CAR-T」「AML 」「SLE CAR-Treg」），，。

### 6.1 

1. **--**： → （//）→ （CAR-T / CAR-M / CAR-NK / CAR-Treg）。
2. **CAR **： Binder（ sequence_db entry_id）、Linker、Hinge、TM、、/。
3. ****：`ACTES_sequences_canonical.fasta`  `sequence_db.json`  entry_id ；，（ CD8a_SP + Binder + CD8a_Short + CD28_TM + 4-1BB_cyto + CD3z_cyto）。
4. ** Biomarker**： Biomarker、。
5. ****：、/、、（、qPCR、）。
6. ****：（、、）；（、、）；，Treg 。

### 6.2 ： HER2 CAR-T

- ****： → HER2（–）→ CAR-T；CD28  + / Hinge。
- ****：Binder Trastuzumab_scFv；Linker G4S3；Hinge CD28_Medium；TM CD28_TM；4-1BB_cyto + CD3z_cyto； TGFB_DNR + Membrane_IL15。
- ****： sequence_db Trastuzumab_scFv、CD28_Medium、CD28_TM、4-1BB_cyto、CD3z_cyto； CAR 。
- **Biomarker**：HER2 IHC/；Tscm；。
- ****：；T ； CAR 。
- ****：HER2+ /；； HER2+ 。

### 6.3 ：AML  CAR-T

- ****： → CLL-1 + CD33  → CAR-T；4-1BB + CD3ζ；iCasp9 。
- ****：Binder （CLL-1 VHH + CD33 scFv，G4S5 ）；Hinge CD8a_Short；4-1BB_cyto + CD3z_cyto；iCasp9 ； PD-1 KO。
- ****：CLL-1/CD33 /； CD8a_SP、CD8a_Short、CD8a_TM、4-1BB_cyto、CD3z_cyto  sequence_db。
- **Biomarker**：CD33/CLL-1 ；；MRD。
- ****：；iCasp9 。
- ****：AML /； CD34+ ； AML ；。

### 6.4 ：SLE CAR-Treg

- ****： → CD19  CD20 → CAR-Treg；**CD28** （ 4-1BB）；FoxP3 。
- ****：Binder FMC63（CD19） CD20 scFv；CD28_cyto + CD3z_cyto（ 4-1BB）；FoxP3_Induction ；tEGFR 。
- ****：BCMA_Treg_CAR （CD28 ）；FoxP3_Induction、tEGFR  sequence_db。
- **Biomarker**：B ；（BILAG/SLEDAI）；。
- ****：Treg  CAR ；FoxP3 。
- ****：（Teff ）；SLE ；。

---

## 7. 、

- **-**： [ACTES_WHITE_PAPER.md](ACTES_WHITE_PAPER.md) §4.3、§4.5（AML）、§4.6、 A.14。
- ** entry_id**： [ACTES_sequences_index.md](data/actes_sequences/ACTES_sequences_index.md)、[sequence_db.json](data/actes_sequences/sequence_db.json)、[ACTES_sequences_canonical.fasta](data/actes_sequences/ACTES_sequences_canonical.fasta)。
- ****： Ch.3、 A.9；functional_domains.json。
- ****： `design_car_t.py --disease <context>`， A.14 。

---

****：，「 →  →  → CAR  → Biomarker/ → 」， §6 、、， ACTES 。
