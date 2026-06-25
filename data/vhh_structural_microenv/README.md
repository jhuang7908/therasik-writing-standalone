#  (Structural Microenvironment)

## 1. 
-  **39  VHH** (ImmuneBuilder ) + **29  Database B** (NanoBodyBuilder2 )。
-  **68**  PDB  VHH 。
-  Kabat  Hallmark  (37, 44, 45, 47)  SASA、5Å ， CDR3 (95-102)  FR2 (36-49)  Cα 。

## 2. Hallmark  CDR3 

| Hallmark  |  |  CDR3  | CDR3-FR2  (Å) | 45 SASA (Å²) |
|---------------|--------|----------------|-----------------------|------------------------|
| **FERx ** | 35 | 15.8 aa | **6.24 Å** | 97.1 |
| **VGLW (Naive IgG)** | 16 | 10.6 aa | **9.19 Å** | 106.5 |
| **FGLx **| 6 | 11.5 aa | 7.53 Å | 91.9 |
| **Other ** | 11 | 13.2 aa | 9.08 Å | 89.8 |

### ：
1. **CDR3 **：
   -  **FERx**（ FERA, FERF, FERG），CDR3  15.8 aa， CDR3  FR2  **6.24 Å**， CDR3  FR2 。
   -  **VGLW** ，CDR3 （ 10.6 aa），CDR3  FR2  **9.19 Å**，FR2 （45 SASA  106.5 Å²）。
2. ****：
   -  VGLW ，**35 ** (100%)  **50 **  5Å ， `vhh_database_summary.md`  VGLW  35/50 （ VGLW ）。

## 3. 
- `data/vhh_structural_microenv/per_entry.json` (68 )
- `data/vhh_structural_microenv/aggregated.md` ( Motif )

## 4. 
 `AbEvaluator`  `structural_microenv_check` ：
- ****： `VGLW`， CDR3  35/50 ， `WARN`  `FAIL`。
- ****： CDR3-FR2  > 10 Å， Hallmark，。