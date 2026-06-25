# ：Clinical VHH（42）+ Database B（29）— 、

**InSynBio AbEngineCore · VHH **  
****：2026-04-19  

---

## 1. 

- ****： **Clinical VHH（42）**  **Database B（ VHH，29）**  **1D ** **3D **（**39 + 29 = 68** /PDB） ****。
- ****：1D  `data/vhh_database_summary.md` ；3D  `data/vhh_structural_microenv/per_entry.json` （ `vhh_structural_union_index.json` ）。

---

## 2. 

|  |  /  |
|:---|:---|
| （42 + 29） | `data/vhh_database_summary.md` §、§、§ |
| （68） | `data/vhh_structural_union/vhh_structural_union_index.json` |
|  | `data/vhh_structural_microenv/per_entry.json` |
|  | `data/vhh_structural_microenv/aggregated.md` |
| Database B  | `data/vhh_database_b_union/database_b_manifest_29.json` |
| （39） | `data/vhh_clinical_39_union/vhh_39_sequences_clinical_validated.json` |

### 2.1 

|  |  |  |
|:---|:---:|:---|
| Clinical VHH（Atlas / ） | **42** | 「、Clinical VHH」 |
|  VHH + ImmuneBuilder  | **39** | Union  `clinical_n=39` |
| Database B | **29** |  |
| **** | **68** | 39 + 29 |

****：42  **3 **  ImmuneBuilder ； **Ozekibart**  JSON  `anarci_missing`—  JSON 。 **1D**  **42** ； **3D**  **39 / 68** 。

---

## 3. Database B — 29 （ + ）

### 3.1 （1D）

 §：

|  |  |
|:---|:---|
|  | 29 |
|  PDB | 18 |
| CDR3  | **12.7 aa**（7–20 aa） |
| CDR2  | **16.8 aa** |
| FR  IGHV3-23  | **30.1**（13–46） |
|  Germline | IGHV3-7（52%），IGHV3-23（24%），IGHV1-69（24%） |

Hallmark  **FERA、VGLW、LGLW、FGLA、FERF、FERG** （ 3.2）；：** CDR3**  **F37 + E44/G44** ；**VGLW**  DB B 「」FR 。

### 3.2 （29，NanoBodyBuilder2 ）

 `per_entry.json`  `source_set == database_b_humanized_camelid_nanobuilder`  ****（2026-04-19）：

|  |  |
|:---|:---|
| n | **29** |
| Hallmark motif  | **FERG 16**；VGLW 3；YECL 3；FGLA 2；YGRF 2；YERW 2；FGLW 1 |
| CDR3  | **15.31 aa**（min 8，max 24） |
| CDR3  FR2 （Å） | **6.78** |

****： 1D 「 CDR3 +  hallmark 」 —  **FERG **， **CDR3–FR2 ** （ §5 ），「」（，）。

---

## 4. Clinical VHH — 42  39 

### 4.1 （1D，n=42）

|  |  |
|:---|:---|
|  | 42 |
|  PDB（/） | 16（38%） |
| CDR3 （Kabat） | **12.1 aa**（3–20 aa） |
| CDR2  | **16.8 aa**（15–19 aa） |
| FR  IGHV3-23  | **24.2** |
| Vernier  | **9.1** |

**Germline**：IGHV3-23 **55%**（23/42）；IGHV3-7 24%；IGHV3-66 12%；IGHV1-2 10%。

**Hallmark **：VHH_Camelid_Like **38%**；Naive_IgG **38%**；Mixed_Custom 21%；（ 4.3）。

****：Pos **45** R（VHH）**50%**；Pos **47** W **50%**、F 29%  —  4.4。

### 4.2 （39，ImmuneBuilder）

 `per_entry.json`  `source_set == clinical_vhh_immunbuilder`  ****：

|  |  |
|:---|:---|
| n | **39** |
| Hallmark motif  | **VGLW 13**；FERF 11；FERR 3；FERS 2； 1 |
| CDR3  | **12.62 aa**（min 3，max 20） |
| CDR3–FR2 （Å） | **8.05** |

****： motif  **VGLW + FERF** ，「 VHH  Naive_IgG  VHH_Camelid_Like 」；**CDR3–FR2 **  Database B  29 （8.05 vs 6.78 Å）， **–**  **** 。

---

## 5. （39）vs Database B（29）：

|  | clinical_vhh_immunbuilder (39) | database_b_humanized_camelid_nanobuilder (29) |
|:---|:---:|:---:|
|  motif | VGLW、FERF | FERG |
| CDR3  | **12.62 aa** | **15.31 aa** |
| CDR3–FR2  | **8.05 Å** | **6.78 Å** |

****： ****（/ vs  VHH /）， ****，。

---

## 6. ：Germline · Hallmark · Vernier · CDR  · 

|  |  |
|:---|:---|
| **Germline** | 42  29  **vhh_database_summary.md** （§4.2、§3.1）。 |
| **Hallmark** |  + 68  **motif **（§3.2、§4.2、§5）。 |
| **Vernier** |  §4、§5.3（/）； JSON  ****（`neighbors_5A`），。 |
| **CDR ** |  CDR2/CDR3  +  CDR3  min/max/mean。 |
| **** | `hallmark_sasa`、`cdr3_fr2_min_dist_A`、`neighbors_5A`； `aggregated.md`  §3–§5。 |

---

## 7. 

1. **1D **：Clinical **42**  Database B **29**  ****  **`vhh_database_summary.md` V1.0** 。  
2. **3D **： **68** –； ** 39**  **DB B 29**  motif/CDR3/ **** 。  
3. ****：**42 vs 39** ，「」「」。  

---

*； 68  master CSV， `scripts/` （ config/docs）。*
