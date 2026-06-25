# VHH42 

****：2026-04-19  
****：2026-04-19 —  42  + 

---

## 1. 

|  |  |  |  |
|:---|:---|:---|:---|
| `vhh42_cmc_metrics.csv` | 42  | **42** （39 `clinical` + 3 `SAbDab_humanized`） | OK |
| `vhh42_germline_assignments.json` | 42  | **`_meta.n` = 42** | OK |
| `VHH42_reference_stats_v1.json` | `per_antibody`  `_meta`  | **`per_antibody_count`: 42**，`n`: 42 | OK |
| `vhh_fr3_packing_rule.json` / `vhh_fr3_packing_percentiles.json` |  +  | （ 39  FR3  VHH） | OK |
| `vhh42_sabdab_supplement.json` | 3  Database B  | **1yzz_A, 3eak_A, 6rnk_B**（ `vhh_structural_union_index.json`） | OK |

---

## 2.  SAbDab 

-  **`data/vhh_structural_union/vhh_structural_union_index.json`**  `database_b_humanized_camelid_nanobuilder`， **NanoBodyBuilder2 / ImmuneBuilder** 。
- ****， 39  **VHH42 **； CMC/ `metrics` （`metrics` ，）。

---

## 3. 

- **`core/vhh/vhh42_reference_loader.py`**：`annotate_input_vs_vhh42_population(seq)` —  pI/GRAVY/instability/net_charge  `VHH42_reference_stats_v1.json`  p5–p95 ；****。
- **`humanize_vhh`**  **`vhh42_benchmark`**（ `available: false`）。

---

## 4. 

-  **`scripts/workstream_1_vhh42_germline_assignment.py`**  `core`（ `sys.path.insert`）； `Antibody_Engineer_Suite` ：`conda run -n anarcii python scripts/workstream_1_vhh42_germline_assignment.py`。
-  CMC：`conda run -n anarcii python scripts/workstream_2_vhh42_cmc_extraction.py`。

---

*。*
