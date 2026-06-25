# ：73  PDB（Database A） 24  VH

****：； Atlas  **** `3dbe9e9b`  JSON（ `data/sabdab_vhh_atlas/`， `git checkout feature/vhh_qa_v3_5_ranking_stability -- Antibody_Engineer_Suite/data/sabdab_vhh_atlas` ）。  
****： `data/vhh_database_summary.md` V1.0 。

---

## 1. 「73 」「138 」

|  |  |  |
|:---|:---:|:---|
| **** | **138** | `autonomous_human_vh_db.json`  =  **PDB + chain**  VH  |
| ** PDB** | **73** |  `pdb` ； PDB  → 138 > 73 |

：**「138  / 73  PDB」**； 138 。

---

## 2. 73-PDB （Database A）

 `vhh_database_summary.md` §、§ ，：

1. **Germline**：IGHV3-23 （：**77%**），IGHV3-66 。
2. **Hallmark（Kabat 37/44/45/47）**：**VGLW（Naive IgG FR2）** ； ** VGLW  motif** ， **35 / 50 / 94**  IGHV3-23 （ **stealth / **）。
3. **CDR**：CDR3、CDR2  ** CDR3 →  E44+R45  hallmark** ， §。
4. ****： ****，「」「」。

---

## 3. 「24  VH」、 73  PDB ？

-  **`vhh_design_atlas_v3.json`** ，`category == "Engineered_Human_VH"`  ** 24 **， **`pdb_id`**。
-  **24  PDB**  **Database A / 138  VH **（/ **/ VH**），**** 73 ； **24 ⊆ 73（PDB ）**。

---

## 4. 24  VH「」——？

Atlas 「 IgG / IGHV3-23 」（****）：

### 4.1 Hallmark motif（37–44–45–47）

 **`hallmark_motif`**（ **VGRW、VGEL、FERF、VERW、FGRL** ）。  
****： **VGLW **， **/VHH **（**G44→E、L45→R、W47→F/G/L…**），「 stealth」。

**24  motif （Atlas v3）**：

| Motif |  |
|:---:|:---:|
| VGRW | 5 |
| VGEL | 4 |
| FERF | 2 |
| VGPW | 2 |
| VALW | 2 |
| （VERW、FERW、FERI、VGLR、VGEW、VTPW、VAQW、VGPV、FGRL ） |  1 |

### 4.2 `anti_aggregation_mutations`（ IGHV3-23 ）

 **`ref_IGHV3_23` → `query`**，：

- ****（ **35、50、89、93、94**）；
-  **Hallmark **（ motif  **FER* / VGEL / VERW** ，**37/44/45/47** ）。

**24  `anti_aggregation_mutations` **（ Database A 「 VGLW 」， ** FR2 hallmark**）。

### 4.3 `single_domain_strategy`

 24 ：

|  |  |
|:---|:---|
| **VHH-like camelization (E44/R45-type)** |  ** E44+R45（ 47 ）**， VHH |
| **Muyldermans-type humanization** |  ** + ** （， PDB） |
| **Custom / Unknown (motif: XXX)** |  ** motif** （ **VGRW、VGEL、VALW** ） |

---

## 5. 24  VH （PDB → Motif → ）

| pdb_id | hallmark_motif | single_domain_strategy |
|:---:|:---:|:---|
| 1ol0 | FERI | VHH-like camelization |
| 2x89 | FERW | VHH-like camelization |
| 3b9v | VGEW | Custom / Unknown |
| 3p9w | VGEL | Custom / Unknown |
| 3zhd | VGPV | Custom / Unknown |
| 5dmj | VGLR | Muyldermans-type humanization |
| 6jsz | VGRW | Custom / Unknown |
| 6j7w | VGPW | Custom / Unknown |
| 6sge | FERF | VHH-like camelization |
| 7azb | FERF | VHH-like camelization |
| 7d5b | VGRW | Custom / Unknown |
| 7d5u | VGRW | Custom / Unknown |
| 7eow | FGRL | Custom / Unknown |
| 7f1g | VGRW | Custom / Unknown |
| 7jwb | VGEL | Custom / Unknown |
| 7nfr | VGRW | Custom / Unknown |
| 7ooi | VGEL | Custom / Unknown |
| 7omn | VGEL | Custom / Unknown |
| 7vke | VERW | VHH-like camelization |
| 7vnd | VALW | Custom / Unknown |
| 7vne | VAQW | Custom / Unknown |
| 7whi | VTPW | Custom / Unknown |
| 7zf4 | VGPW | Custom / Unknown |
| 8di5 | VALW | Custom / Unknown |

* `entry_name` / `target`  Atlas JSON，（ **7vke UniDab F11A**、**BACE2 xaperone **、**caplacizumab 7eow** ）。*

---

## 6. 

- **73  PDB**： VH  ****；**138**  **** 。  
- **24  VH**：Atlas  **Engineered_Human_VH**， **`hallmark_motif`  + `anti_aggregation_mutations`（ IGHV3-23）+ `single_domain_strategy`**； ** VGLW  stealth**、**VGEL **、**VGRW  CDR3**、**FER* **、**VERW（ 7vke）** 。

---

*：Atlas  Database A JSON  git `3dbe9e9b` ；， `data/sabdab_vhh_atlas/`  `data/vhh_design_atlas_v3.json` 。*
