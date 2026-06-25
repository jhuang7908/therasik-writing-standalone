# 458  —  / CMC /  /  

****：`structure_metrics_summary.json`（458 ） + `data/structures/engineered/*.pdb`  
****：`scripts/batch_458_engineered_full_assessment.py`  
****：`engineered_458_full_assessment.csv`、`engineered_458_full_assessment_summary.json`

---

## 1. （458 ， PDB ）

|  | n | p5 | p25 | p50 | p75 | p95 | mean |
|------|---|-----|-----|-----|-----|-----|------|
| **VH/VL  (deg)** | 458 | 74.6 | 78.5 | 82.3 | 84.6 | 87.4 | 81.5 |
| **** | 458 | 56 | 66 | 71 | 76 | 83 | 70.5 |
| ** (Å)** | 458 | 4.55 | 4.62 | 4.67 | 4.71 | 4.75 | 4.66 |
| ** (Å)** | 458 | 0.58 | 1.24 | 1.80 | 2.27 | 2.68 | 1.74 |
| **Vernier SASA  (Å²)** | 458 | 462 | 494 | 535 | 568 | 626 | 536 |

---

## 2. CMC / （， PDB  VH+VL ）

|  | n | p5 | p25 | p50 | p75 | p95 | mean |
|------|---|-----|-----|-----|-----|-----|------|
| **pI** | 458 | 5.18 | 6.85 | 8.30 | 8.74 | 9.09 | 7.72 |
| **GRAVY** | 458 | -0.475 | -0.397 | -0.337 | -0.280 | -0.192 | -0.337 |
| **** | 458 | 27.5 | 33.2 | 37.8 | 41.6 | 47.1 | 37.6 |
| **pH7 ** | 458 | -4.0 | -0.1 | 1.9 | 3.8 | 5.9 | 1.51 |
| ** max9** | 458 | 0.556 | 0.556 | 0.556 | 0.667 | 0.778 | 0.61 |
| ** max7** | 458 | 2.0 | 3.0 | 3.0 | 3.0 | 4.0 | 3.0 |
| ** motif ** | 458 | 0 | 0 | 0 | 1 | 2 | 0.47 |
| **** | 458 | 0 | 0 | 1 | 2 | 3 | 1.10 |
| **** | 458 | 0 | 0 | 1 | 1 | 3 | 0.97 |

：CMC （ pI&lt;5.5、instability&gt;55、hydro_patch≥0.7） CSV  `cmc_flags` 。

---

## 3. （MHC-II ， IEDB API）

|  | n | p5 | p25 | p50 | p75 | p95 | mean |
|------|---|-----|-----|-----|-----|-----|------|
| **TCIA  (0–1)** | 458 | 0.52 | 0.61 | 0.67 | 0.72 | 0.78 | 0.66 |
| **** | 458 | 7 | 13 | 19 | 26 | 37 | 20.0 |
| **** | 458 | 0 | 3 | 6 | 10 | 17 | 7.0 |
| **** | 458 | 12 | 28 | 37 | 43 | 54 | 35.3 |
| **/** | 458 | 3 | 4 | 5 | 5 | 5 | 4.5 |

****： `engineered_458_full_assessment_summary.json`  `immuno_risk_level_counts`。  

**“”**：  
- ****：`MHCII_Analyzer(use_iedb=False)` ， IEDB API， `_offline_heuristic_preds`： 15-mer  9-mer （1,4,6,9），** percent_rank**（：*This is a conservative screen only — not a validated predictor*）。  
- ** IEDB **：IEDB  27  MHC-II ；“ → rank ”，，。  
- ** 458  HIGH**： rank “”， strong binder（≥4 ）， `n_high ≥ 3`  `tcia ≥ 0.15`， `risk_level`  HIGH；****， 458 。  
- ****：TCIA、** 458 **（ TCIA  p50 /）；****。/， **IEDB **（27-allele）。

---

## 4. 

- ****： pI、GRAVY、instability、immuno_tcia ， 458  p5–p95 。
- ****： 458 「」CMC//， `evaluation_reference_stats.json` （ `humanized_458` population）。
- ****：  
  `python scripts/batch_458_engineered_full_assessment.py`  
   CSV  summary JSON。
