# ：

**** PDB  `scripts/structure_metrics_humanization.py` 。

## 1. North / Canonical 

- ****：CDR  canonical class（H1/H2/H3, L1/L2/L3）， Kabat  CDR （ VH 71）。
- ****：`canonical.H1`, `H2`, `H3`, `L1`, `L2`, `L3`（ `H1-13-1`, `H2-10-1`）。
- ****： canonical ， CDR 。

## 2. VH/VL 

- ****：， CA 。
- ****：`vh_vl_angle_deg`。
- ****：， CDR 。

## 3. Vernier Zone Packing

- ****： Vernier （Kabat VH 2,27–30,48,49,67,69,71,73,78,93,94；VL 2,4,36,46,49,69,71,98） 4.5 Å （Contact Number），/。
- ****：`vernier_packing.VH_71`, `VH_94`, …。
- ****： Vernier ，。

## 4. Vernier Zone ↔ CDR 

- ****：Vernier  CDR （H1/H2/H3, L1/L2/L3）****（Å）。
- ****：`vernier_cdr_distances.Vernier_to_H1`, `Vernier_to_H2`, … , `Vernier_to_any_CDR`。
- ****： CDR “”， Vernier ，。

## 5. VH/VL 

- ****：VH  VL （ ≤ 5.5 Å）、。
- ****：`interface_n_pairs`, `interface_mean_dist_A`, `interface_min_dist_A`。
- ****：，。

## 6. Vernier Zone 

- ****：Vernier  SASA（Å²）； SASA 。
- ****：`vernier_sasa_total`（Vernier  SASA）、`vernier_sasa_per_residue.VH_71` 。
- ****： Vernier “/”，。

---

## 

**（ ANARCI/IMGT ， PDB  ANARCI）**  
 ANARCI、 Vernier zone  IMGT/Kabat ，：

```bash
# 1)  Excel  Vernier/Kabat （ANARCI ，）
python scripts/build_vernier_index_lookup.py --excel data/humanization_assay/thera_human_igG_germline_analysis.xlsx --out data/humanization_assay/vernier_index_lookup.json

# 2) ， lookup  PDB  ANARCI
python scripts/structure_metrics_humanization.py --dir data/structures/engineered --out data/humanization_assay/structure_metrics_summary.json --vernier-lookup data/humanization_assay/vernier_index_lookup.json
```

** lookup（ PDB  ANARCI）**  
：

```bash
#  PDB， stdout
python scripts/structure_metrics_humanization.py --pdb path/to/fab.pdb

#  ID  JSON
python scripts/structure_metrics_humanization.py --pdb fab.pdb --vh H --vl L --out metrics.json

#  PDB （ ANARCI）
python scripts/structure_metrics_humanization.py --dir data/structures/engineered --out data/humanization_assay/structure_metrics_summary.json
```

****：BioPython、numpy；Kabat  `anarci` shim（ANARCII）。SASA  `Bio.PDB.SASA.ShrakeRupley`（BioPython ）。

---

## （CDR North  + VH/VL  + ）

 JSON ，****（ CDR North 、VH/VL /、）：

```bash
python scripts/analyze_vernier_framework_patterns.py --metrics data/humanization_assay/structure_metrics_summary.json
```

- ****：`vernier_framework_patterns.json`、`vernier_framework_patterns_report.md`。
- ****：CDR North 、VH/VL  (H1|H2|L1) 、****（ H1|H2|L1 ）、Vernier /、。

---

* `vernier_zone_weights.md`、`calc_vernier_energy.py`、`compute_vernier_zone_distances_from_pdb.py` 。*
