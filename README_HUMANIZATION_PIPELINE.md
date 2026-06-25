# Antibody Humanization Pipeline & Assets 

 458 ，****、****、********。

---

## 1.  (Assets)

### 1.1  (The Brain)
*   **`docs/HUMANIZATION_DESIGN_GUIDE.md`**：** (SOP)**。、Vernier 、。
*   **`data/humanization_assay/vernier_backmutation_checklist.md`**：****。。
*   **`data/humanization_assay/vernier_correlation_report.md`**：****。 Vernier Zone 。

### 1.2  (The Data)
*   **`data/humanization_assay/vernier_index_lookup.json`**：**458 **。 CDR 、Vernier 、。
*   **`data/humanization_assay/vh_vl_pairing_matrix.csv`**：**VH/VL **。 VH  VL Germline 。
*   **`data/humanization_assay/structure_metrics_summary.json`**：****。、Packing、SASA 。

### 1.3  (The Tools)
*   **`scripts/structure_metrics_humanization.py`**：****。、Packing、SASA、North 。
*   **`scripts/validate_humanization.py`**：****。 vs （RMSD、、Packing ）。
*   **`scripts/anarci_shim.py`**：**ANARCI **。 ImmuneBuilder  ANARCII 。
*   **`scripts/qc_humanization_inputs.py`**：**/**。、。

---

## 2.  (Self-Check Mechanism)

“， (GIGO)”，** (Input QC)**  **** 。

### 2.1  (Rejection Criteria)
，****：

1.  **/**：
    *    < 80  > 150 (VH/VL)。
    *    (B, J, O, U, X, Z)。
    *    ( Cys 23, Trp 41, Cys 104)。
2.  ****：
    *   ANARCI/ANARCII  CDR 。
    *   CDR  ( H3 < 3  > 35)。
3.  **/**：
    *   VH  VL ( Germline )。
    *    Germline  (< 50%)，。

### 2.2  (Logic Validation)
，：

1.  **CDR **： CDR  CDR **100% **。
2.  **Vernier **： **Gly/Pro**  ****。
3.  ****： L1 ， VL 71 。

---

## 3.  (Quick Start)

###  1： (QC)
```bash
python scripts/qc_humanization_inputs.py --vh mouse_vh.fasta --vl mouse_vl.fasta
# ，；，。
```

###  2： (Structure Analysis)
```bash
# 
python scripts/structure_metrics_humanization.py --pdb mouse_model.pdb --out mouse_metrics.json
# 、SASA、Packing 
```

###  3： (Design & Modeling)
*    `HUMANIZATION_DESIGN_GUIDE.md` 。
*    AF2/ImmuneBuilder  `humanized.pdb`。

###  4： (Validation)
```bash
python scripts/validate_humanization.py --ref mouse_model.pdb --target humanized.pdb
#  RMSD < 0.5Å,  < 3°, Packing /
```

---
*：Antibody Engineer Suite Team*
*：2026-02-18*
