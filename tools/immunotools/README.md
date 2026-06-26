# ImmunogenNN + HuMAtch — 

## 

|  |  |  | conda env |
|------|------|------|-----------|
| **ImmunogenNN** | Novo Nordisk / DTU 2025 | MHC-II  | `anarcii` |
| **HuMAtch** | OPIG / Deane 2024, MAbs | CNN gene-specific （VH + VL + ） | `humatch`（，Python **3.9**）|

---

## Step 1 — 

```powershell
#  Antibody_Engineer_Suite 
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_immunotools.ps1
```

：
-  `ImmunoGeNN`  `Humatch`  `tools/immunotools/`
-  ImmunogenNN  `anarcii` 
-  `humatch` conda env（**Python 3.9**，Humatch ） ANARCI + TensorFlow + HuMAtch

> **（HuMAtch CNN ）**： `Humatch-classify`  `zenodo.org/records/13764770`  3  `.h5`  24  `.npy` germline likeness （ 50 MB）。：`tools/immunotools/Humatch/Humatch/trained_models/`  `.../germline_likeness_lookup_arrays/`。， `pip install -e .`。

---

## Step 2 — 

```powershell
conda activate anarcii
cd d:\InSynBio-AI-Research\Antibody_Engineer_Suite
python projects\clinical_ref_mAbs_smart_cmc\run_triple_immunotools.py
```

 ImmunogenNN（HuMAtch ）：
```powershell
python projects\clinical_ref_mAbs_smart_cmc\run_triple_immunotools.py --skip-humatch
```

---

## Step 3 — 

，`projects/clinical_ref_mAbs_smart_cmc/` ：

|  |  |
|------|------|
| `immunotools_triple_results.json` | （ raw ） |
| `immunotools_triple_report.md` | Console  Markdown （§1 ImmunoGeNN, §2 HuMAtch, §3 ） |
| `immunotools_triple_summary.csv` |  |

---

## 

- `input_three_mabs.fasta` — FASTA  VH/VL
- `input_three_mabs.csv` — CSV （`VH`,`VL`,`name` ， `Humatch-humanise --input` ）

---

## HuMAtch 

| CNN  |  |
|----------|------|
| ≥ 0.6 |  |
| 0.4–0.6 |  |
| < 0.4 |  |

> ：Chinery et al., MAbs 2024

---

## ImmunogenNN 

（ ImmunoGeNN ； screening / deimmunization / immunization ）。

---

## 

**Q: HuMAtch CNN **  
A:  `https://zenodo.org/records/13764770` ， `tools/immunotools/Humatch/trained_models/`  `tools/immunotools/Humatch/germline_likeness_lookup_arrays/`。

**Q: `setup_immunotools.ps1`  hmmer （Windows bioconda）**  
A:  WSL Ubuntu  HuMAtch；ImmunogenNN  anarcii ，。
