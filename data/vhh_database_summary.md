# VHH 
**InSynBio AbEngineCore ·  v1.0**

---

## （Provenance）

|  |  |
|---|---|
| **** | V1.0 |
| **** | 2026-04-18 |
| **** | FROZEN — ； |
| **** | SAbDab-nano（`data/sabdab_nano/sabdab_nano_summary_all.tsv`， 2422，2026-04） |
| **** | Database A：`heavy_species`  `homo sapiens` / `synthetic construct`，；Database B：`humanized` ；Clinical VHH： |
| **** | `scripts/analyze_vhh_atlas.py`, `scripts/analyze_hallmarks_vernier.py`, `scripts/analyze_19vhh_cdr_features.py` |
| **** | `config/abenginecore_registry.json` → `tier_1_data.vhh_database_summary` |
| **** | `docs/VH_TO_VHH_CONVERSION_STANDARD_V1.0.md`（Phase 2 Hallmark、Phase 3 Stealth） |

> ⚠️ ** VH→VHH 。 Evolution Protocol 。**

---

> ：138 VH（Database A）、29 VHH（Database B）、42 VHH（Clinical VHH）、24 VH（Engineered Human VH）
>
> ：Anarcii (Kabat numbering) · IGHV3-23  · Kabat Hallmark/Vernier 

---

## 、

|  |  |  PDB |  |  |
|:---|:---:|:---:|:---|:---|
| **Database A** — Autonomous Human VH | 138 | 73 | SAbDab-nano，autonomous heavy chains | VH  |
| **Database B** — Humanized Camelid VHH | 29 | 18 | SAbDab-nano，humanized  |  |
| **Clinical VHH** | 42 | 16 | ，/ VHH |  |
| **Engineered Human VH**（Atlas ） | 24 | 24 | Database A  | VH→VHH  |

---

## 、Database A —  VH 

### 2.1 

|  |  |
|:---|:---|
|  | 138 |
|  PDB | 73 |
| CDR3  | **12.3 aa**（ 3–24aa） |
| CDR2  | **16.8 aa**（ 16–19aa） |
|  Germline | IGHV3-23：77%（106/138），IGHV3-66：15%（21/138） |

### 2.2 Hallmark （ 138 ）

| Hallmark Motif (37/44/45/47) |  |  |  CDR3 | Hallmark |  Germline |
|:---:|:---:|:---:|:---:|:---:|:---|
| **VGLW** (Naive IgG) | 80 | 58% | 13.3 aa | 2.5 | IGHV3-23 (79%) |
| **VGEL** | 10 | 7% | 15.2 aa | 6.4 | IGHV3-66 (50%) |
| **VTPW** | 8 | 6% | 10.0 aa | 6.0 | IGHV3-23 (100%) |
| **VGLR** | 7 | 5% | 7.0 aa | 2.0 | IGHV3-23 (100%) |
| **VGRW** | 6 | 4% | 3.8 aa | 4.7 | IGHV3-66 (83%) |
| **VALW** | 5 | 4% | 10.0 aa | 4.8 | IGHV3-23 (80%) |
| **FERW** | 3 | 2% | 19.0 aa | 7.0 | IGHV3-66 (100%) |
| **FERF** | 3 | 2% | 14.0 aa | 7.0 | IGHV3-23 (100%) |
| **VERW** | 1 | <1% | 15.0 aa | 4.0 | IGHV3-23 (UniDab 7vke) |

### 2.3 ：VGLW「」

**VGLW（ Naive IgG FR2）≠ **

80 VGLW ， 10（ PDB 3upc，）。 **88%  Hallmark **：

|  | IGHV3-23 |  |  |  |
|:---:|:---:|:---|:---:|:---|
| **35** | S | S→N (18), S→G (10), S→H (8) | **72%** | CDR1 ， |
| **50** | A | A→S (15), A→D (13), A→G (8) | **84%** | **CDR2 **， VL  |
| **94** | K | K→R (40), K→T (7), K→S (5) | **65%** | FR3/CDR3 ， |

**VGLW  CDR3 ：**

|  |  |  CDR3 |  |
|:---:|:---:|:---:|:---|
| 0 | 10 | 7.0 aa | ； 3upc（CDR3 ） |
| 1 | 2 | 9.0 aa | （ A50X） |
| 2 | 22 | 11.9 aa | ：A50D + K94R |
| 3 | 33 | 15.3 aa | ：**S35N + A50D + K94R** |
| 4 | 12 | 16.0 aa |  CDR3：S35N + A50D + V89L + K94R |
| 5 | 1 | 20.0 aa |  CDR3  |

** VGLW （ CDR3 ）：**

| CDR3 |  |
|:---:|:---|
| ≤ 9aa | `A50S / A50D` + `K94R` |
| 10–16aa | `S35N` + `A50D` + `K94R` |
| ≥ 17aa | `S35N` + `A50D` + `V89L` + `K94R` |

> ⚠️ ****： 50  CDR2 （Kabat CDR2 = 50–65）。 CDR2 （≥17aa） CDR2  A50， A50→D  CDR2 ，****。

---

## 、Database B —  VHH

### 3.1 

|  |  |
|:---|:---|
|  | 29 |
|  PDB | 18 |
| CDR3  | **12.7 aa**（ 7–20aa） |
| CDR2  | **16.8 aa** |
| FR  IGHV3-23  | **30.1 **（ 13–46） |
|  Germline | IGHV3-7 (52%)，IGHV3-23 (24%)，IGHV1-69 (24%) |

> **：** Database B  Germline  Atlas v3 ， Database B  SAbDab ，Atlas v3  Anarcii Kabat 。

### 3.2 Hallmark （Database B 29）

| Hallmark Motif |  |  |  CDR3 |  |
|:---:|:---:|:---:|:---:|:---|
| **FERA** | 8 | 28% | 16.0 aa | （F37，E44，R45，A47） |
| **VGLW** | 7 | 24% | 9.9 aa | Muyldermans — FR2 |
| **LGLW** | 3 | 10% | 7.3 aa | L37 ， FR2 |
| **FGLA** | 2 | 7% | 16.0 aa | Muyldermans FGLA  |
| **FERF** | 2 | 7% | 12.0 aa |  Hallmark |
| **FERG** | 2 | 7% | 20.0 aa | F37+E44+R45+G47， CDR3 |
| **VRLW** | 2 | 7% | 8.5 aa |  |
| **FGLW** | 1 | 3% | 15.0 aa | F37+ 44/45/47 |

### 3.3 Database B 

**CDR3 ≥ 16aa （FERA/FGLA/FERG） F37 + E44/G44 **：
-  CDR3（≥16aa）→  F37
- FR  IGHV3-23  30.1 ， VH 

**「」 Database B **（VGLW 7）：
-  retained_camelid_departures  FR （FR1/FR3 ）， VH-VL 

---

## 、Clinical VHH — / VHH 

### 4.1 （Atlas v3 Clinical_VHH，n=42）

|  |  |
|:---|:---|
|  | 42 |
|  PDB  | 16 |
| CDR3 （Kabat） | **12.1 aa**（ 3–20aa） |
| CDR2 （Kabat） | **16.8 aa**（ 15–19aa） |
| FR  IGHV3-23  | **24.2 **（ 13–46） |
| Vernier  | **9.1 ** |
|  PDB  | 38%（16/42） |

### 4.2 Germline 

| Germline |  |  |
|:---:|:---:|:---:|
| **IGHV3-23** | 23 | 55% |
| IGHV3-7 | 10 | 24% |
| IGHV3-66 | 5 | 12% |
| IGHV1-2 | 4 | 10% |

> **IGHV3-23  VHH （55%）**

### 4.3 Hallmark 

| Hallmark  |  |  |  Motif |  CDR3 |
|:---|:---:|:---:|:---:|:---:|
| **VHH_Camelid_Like** (E44+R45) | 16 | 38% | FERF (11) | **15.2 aa** |
| **Naive_IgG** (G44+L45+W47) | 16 | 38% | VGLW (9) | **10.0 aa** |
| **Mixed_Custom** | 9 | 21% |  | 9.9 aa |
| Humanized_Camelid_FGLA | 1 | 2% | FGLA | 16.0 aa |

### 4.4 Hallmark （Clinical VHH）

|  |  |  |  |  |
|:---:|:---:|:---:|:---:|:---|
| **37** | F | 18 | 43% |  |
| **37** | V（ IgG） | 12 | 29% |  |
| **37** | Y/L/I/A | 12 | 29% | / |
| **44** | G（ IgG） | 20 | 48% |  FR2  |
| **44** | E（VHH）| 16 | 38% | VHH  |
| **45** | R（VHH，） | 21 | **50%** | VHH  |
| **45** | L（ IgG） | 20 | 48% |  VH-VL  |
| **47** | W（ IgG/VHH） | 21 | **50%** | VHH |
| **47** | F | 12 | 29% |  |
| **47** | G | 1 | 2% | ； |

> **：Pos47  VHH  IgG， W  F；G47 。**

### 4.5 CDR3  × Hallmark （Clinical VHH ）

| CDR3  | VHH_Camelid_Like | Naive_IgG | Mixed |  |
|:---:|:---:|:---:|:---:|:---|
| ≥ 18aa | 4 | 0 | 0 | ** E44+R45** |
| 14–17aa | 9 | 2 | 2 |  E44+R45；FGLA  |
| 10–13aa | 1 | 7 | 6 | ；VGRW/VGEL  |
| ≤ 9aa | 2 | 7 | 1 | G44+L45  |

---

## 、Engineered Human VH — VH→VHH （Atlas ）

### 5.1 （n=24， PDB）

|  |  |
|:---|:---|
|  | 24 |
|  PDB | 24 |
| CDR3 （Kabat） | **11.0 aa**（ 3–19aa） |
| CDR2 （Kabat） | **16.9 aa**（ 16–18aa） |
| FR  IGHV3-23  | **19.8 ** |
| Vernier  | **9.1 ** |
| Germline：IGHV3-23 | 63%（15/24） |

### 5.2 Hallmark （Engineered VH）

| Hallmark Motif |  |  |  CDR3 |  PDB |
|:---:|:---:|:---:|:---:|:---|
| **VGRW** (G44+R45+W47) | 5 | 21% | 4.0 aa | BACE2 xaperone  |
| **VGEL** (G44+E45+L47) | 4 | 17% | 15.5 aa |  EphA1 JD1  |
| **VALW** | 2 | 8% | 10.0 aa | SARS-CoV-2  |
| **FERF** | 2 | 8% | 13.5 aa | DDR2/Rhodopsin  |
| **VERW** | 1 | 4% | 15.0 aa | **7vke UniDab F11A** |
| **FERW** | 1 | 4% | 19.0 aa | Beta2-microglobulin |
| **VGPW** | 2 | 8% | 11.5 aa | SARS-CoV-2/BCMA |
| **FGRL** | 1 | 4% | 19.0 aa | vWF A1  |

### 5.3 Vernier Zone 

 Clinical VHH  Engineered Human VH ， Vernier ** 100%  IGHV3-23**：

|  | IGHV3-23  |  |  |
|:---:|:---:|:---|:---|
| **67** | K |  F/L/Y/I | **VHH/sdAb ，** |
| **69** | V |  L/I |  |
| **73** | K/I |  |  |
| **93** | A |  S/G/T |  |
| **48** | M/I |  |  |
| **71** | R |  R | **；CDR3 Loop ** |
| **78** | V/L |  |  CDR3  |
| **94** | K | K→R/T/S  | 「」 |

---

## 、

### 6.1 CDR3  Hallmark 

| CDR3  |  |  |
|:---:|:---|:---|
| ≥ 18aa | ：VHH_Camelid_Like  FxRx  | **E44+R45（FERF/FERG）**； |
| 14–17aa | Clinical VHH  E44+R45 ；Database A  VGEL | E44+R45 ；VGEL  |
| 10–13aa | ；Database A VGLW  | VGRW/VGEL ； CDR2  G44E+L45R |
| ≤ 9aa | VGLW/LGLW | Naive IgG + （A50D+K94R） |

### 6.2 「 Hallmark」

|  | Hallmark |  |  |
|:---|:---:|:---|:---|
|  CDR3  | VGLW | CDR3 ≥ 15aa + S35N + A50D + K94R | 2vyr(MDM4), 7ki1(Gαs) |
|  CDR3 +  | VGLW/FxGx | CDR3 ≥ 18aa  | Caplacizumab (CDR3=19aa) |

> ⚠️ ** CDR2 = 17aa （ muMAb4D5）**： 50  CDR2 ，A50D  CDR2 Loop ，****  VGLW + 。 Hallmark  **G44E + L45R**。

### 6.3  FR  IGHV3-23 

|  |  FR  |  |
|:---:|:---:|:---|
| Engineered Human VH | **19.8** |  IgG； IGHV3-23  |
| Clinical VHH | **24.2** |  VHH  24  FR  IGHV3-23 |
| Database B (humanized camelid) | **30.1** |  VH ； |

### 6.4 Germline 

|  |  Germline |  |
|:---|:---:|:---|
|  VHH  | **IGHV3-23** (55%) | IGHV3-7 (24%) |
|  VH  | **IGHV3-23** (63%) | IGHV3-66 (29%) |
|  VHH  (DB-B) | IGHV3-7 (52%)，IGHV3-23 (24%) | IGHV1-69 (24%) |

---

## 、muMAb4D5 

|  | muMAb4D5 |  |  |
|:---|:---:|:---|:---|
| CDR2（Kabat） | **17 aa** | Database A：CDR2=17aa  pos50  CDR2  | ❌  VGLW+ |
| CDR3 | ~14–16aa | VHH_Camelid_Like  CDR3=15.2aa | ✅  **G44E + L45R** |
| Germline | IGHV3-23 | 55%  VHH  IGHV3-23 | ✅  IGHV3-23  |
| Hallmark  | VERW  | 7vke UniDab F11A：CDR2=17aa，CDR3=15aa，VERW， | ✅ **VERW**  |
| Vernier 71 | R | 71R  | ✅  71R |
| Vernier 94 | K |  G44E+L45R，94K ； VGLW  K94R | ✅  94K |

---

## 、

|  |  |  |
|:---|:---|:---:|
| `data/sabdab_vhh_atlas/autonomous_human_vh_db.json` | Database A： VH  | 138 |
| `data/sabdab_vhh_atlas/humanized_camelid_vhh_db.json` | Database B： VHH | 29 |
| `data/vhh_design_atlas_v3.json` | Atlas v3：66（Hallmark/Vernier/Germline） | 66 |
| `data/vhh_design_rules.json` | （v2.0） | — |
| `data/vhh_design_rules.md` |  | — |
| `data/sabdab_vhh_atlas/vhh_atlas_correlations.json` | CDR×Hallmark×Vernier  | — |

---

*InSynBio AbEngineCore · vhh_database_summary v1.0 · *
