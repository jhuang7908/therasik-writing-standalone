# 75  IgG-like  3-arm / 4-arm 

****：`thera_export.xlsx` + `bispecific_125_igg_like.json`  
****：`scripts/stats_igg_like_75_sequence_count.py`  
** JSON**：`data/design_rules/igg_like_75_sequence_stats.json`

---

## 1. ：IgG-like   IgG-like

- **Lunsekimig (SAR443765)**  ** TSLP/IL13/ALB  nanobody**， **5 ** ， **scFv/** ，** IgG-like**。  
- “IgG-like ” Fab  CH1/CL、， **Lunsekimig1、Lunsekimig2**  IgG-like， 3-arm/4-arm  CH1/CL  8 。

---

## 2. IgG-like ：50  4-arm，23  3-arm

|  |  |  |
|------|------|------|
| **4-arm** | **50** | 4 ：H1, L1, H2, L2， CrossMab/； CH1/CL ， **8 **。 |
| **3-arm** | **23** |  3 ：H1, H2, L（L1=L2  thera  3 ）； CH1/CL ****：H1+CH1, H2+CH1, L+CL。 |
| ** IgG-like** | **2** | Lunsekimig1, Lunsekimig2（scFv/nanobody ， Fab ）。 |

- ** (L1==L2)**：21 ，50 （ 50/23 ，23 = 21  + 2 “3_other”）。  
-  thera  4 （H1,L1,H2,L2），，“ 4 ” IgG-like 。

---

## 3.  CH1/CL 

- **23  3-arm**： 23  VH+CH1、VL+CL 。  
  - ：H1+CH1、H2+CH1、L+CL。  
  - ****：`data/design_rules/igg_like_23_three_arm_fab.json`（ `heavy_fab_1`、`heavy_fab_2`、`light_fab`）；FASTA  `data/design_rules/igg_like_23_three_arm_fab_fasta/`。  
  - ****：`python scripts/build_fab_23_three_arm.py`（CH1=Human IGHG1\*01，CL=Human IGKC\*01）。
- **50  4-arm**： CH1/CL （****：`python scripts/build_fab_50_four_arm.py`）：  
  - **CrossMab（7 ）**：2  arm。Arm1  (VH1+CH1, VL1+CL)；Arm2  (VH2+**CL**, VL2+**CH1**)。  
  - ** CrossMab（43 ）**：4  arm（H–L ）：H1L1, H1L2, H2L1, H2L2， VH+CH1、VL+CL。  
  - ****：`data/design_rules/igg_like_50_four_arm_fab.json`；FASTA  `igg_like_50_four_arm_fab_fasta/`（ 2  4  arm  heavy/light_fab）。  
- **、** 4-arm  CH1/CL ， **8 **：  
  - **2 **：(H1-L1, H2-L2)  vs (H1-L2, H2-L1) ；  
  -  ** CrossMab**（CH1/CL ）， 8 。  
  - /（ AF-Multimer） CrossMab， CH1/CL 。

---

## 4. 

- **3-arm（23 ）**：`4_two_arms_common_LC`（21）+ `3_other`（Simridarlimab, Surovatamig）。  
- **4-arm（50 ）**：`4_two_arms`（50）。  
- ** IgG-like（2 ）**：`other`（Lunsekimig1, Lunsekimig2），scFv/nanobody ， Fab CH1/CL 。

---

## 5. 50  4-arm 

****：`data/design_rules/igg_like_50_four_arm_names.txt`  
50 （chain_class = 4_two_arms，），//。

---

## 6. 23  3-arm： CH1/CL，

- ****： 23  3-arm  VH+CH1、VL+CL ， Fab （H1+CH1、H2+CH1、L+CL ）， 50  4-arm  8 。
- **、**：
  1. ****： V–C （Kabat 113/114  VH→CH1，VL →CL）； germline （ CH1  98 aa，Cκ  107 aa，Cλ  106 aa）；、。
  2. ****： **IgFold**  Fab （H+L）； **pLDDT  V  C **（ &gt; 70–80）， V–C / clash，。
  3. ****： Fab （ 6JBT）。
- **IgFold **：。（ `reports/predict_structure.py`）。：`pip install igfold`； PyTorch。 Heavy / Light （ CH1/CL）， PDB + ； CPU/GPU ， API。
- ****：3-arm  CH1/CL →  IgFold  Fab →  pLDDT ，“”。

---

## 7. 23  3-arm （QC）

 23  3-arm Fab ****， QC 。

### 

|  |  |  |
|------|------|------|
| **（build）** |  | H1、H2、L（L1  L2） thera_export。 |
| |  |  20 （ACDEFGHIKLMNPQRSTVWY）， &gt; 10。 |
| **QC ** |  |  Fab 。 |
| | **C ** | heavy_fab_1/2  CH1（IGHG1\*01）、light_fab  CL（IGKC\*01）， V–C 。 |
| | **V ** | VH 100–150 aa、VL 95–125 aa（Kabat ）。 |
| | **Fab ** | heavy_fab 200–250 aa、light_fab 200–230 aa。 |
| **** | ARANCII  V  |  VH1、VH2、VL  ARANCII （ scheme）； H/K/L、n_residues  V 、。 |

- **QC **：`python scripts/qc_fab_23_three_arm.py`  
- **QC **：`data/design_rules/igg_like_23_three_arm_fab_qc.json`（ overall: pass/warn/fail， checks）。  
- ****：`python scripts/qc_fab_23_three_arm_numbering.py`  
- ****：`data/design_rules/igg_like_23_three_arm_fab_numbering_qc.json`（ VH1/VH2/VL  numbered、chain_type、last_kabat_pos、n_residues）。  
- ****： QC 23/23 **pass**； QC 23/23 **pass**（ `pip install anarcii`）。

### IgFold 

- ****：`python scripts/run_igfold_23_three_arm_fab.py`  
- ****： `igg_like_23_three_arm_fab.json`。  
- ****：`data/design_rules/igg_like_23_three_arm_igfold/<antibody_id>_Arm1.pdb`、`<antibody_id>_Arm2.pdb`（ 2  Fab：Arm1 = H1+CH1/L+CL，Arm2 = H2+CH1/L+CL）。  
- ****：`--limit N`  N ，`--dry-run` ，`--no-refine`  OpenMM 。

### 

- ****： IgFold  Fab（H+L）， pLDDT  V–C 。

---

## 8. 

```bash
python scripts/stats_igg_like_75_sequence_count.py
```

 `igg_like_75_sequence_stats.json` 。
