# InSynBio VHH - 

****: IMGTVHH7D12  
****:  +   
****: 2024

---

## 📄 

### 
- ****: `paper/VHH7D12_InSynBio.md` ⭐
  - 📊 : Markdown (PDF/Word/HTML)
  - 📏 : 343，33.77 KB
  - 📝 : 10 +  + Mermaid
  - 🎯 : InSynBio
  - ✅ : ，AI

### 
- ****: `paper/VHH_Humanization_Analysis_Manuscript_Draft.md`
  - 📊 : Markdown 
  - 📏 : 432
  - : 

---

## 📊 

### 

|  |  |  |
|------|------|------|
| `paper/tables/Table1_slice3_19_clinical_vhh_master.md` | 19VHH | 19 + ，17 |
| `paper/tables/Table1_slice3_19_clinical_vhh_master.csv` | Table 1 CSV |  |
| `paper/tables/Table2_7D12_native_sr_bm_summary.md` | 7D12 | 3 + ，14 |
| `paper/tables/Table2_7D12_native_sr_bm_summary.csv` | Table 2 CSV |  |

### 

|  |  |
|------|------|
| `reports/slice3_vhh_comprehensive_functional_library.csv` | 19VHH +  |
| `reports/slice3_vhh_immunogenicity_features.csv` | 19VHHIEDB MHC-II |
| `reports/slice3_vhh_developability_features_native_sr_bm.csv` | 19VHH(Native/SR/BM) |
| `output/7D12/7d12_4krl_eval_table.csv` | 7D12 |

---

## 📈 

### 

|  |  |  |  |
|------|------|------|------|
| **Figure 1** | `paper/figures/Fig1_pipeline_mermaid.md` | Mermaid |  |
| **Figure 2** | `paper/figures/Fig2_fr23_delta_by_strategy.png`<br>`paper/figures/Fig2_fr23_delta_by_strategy.svg` | PNG/SVG | FR2/FR3 |
| **Figure 3** | `paper/figures/Fig3_B_total_1pct_by_strategy.png`<br>`paper/figures/Fig3_B_total_1pct_by_strategy.svg` | PNG/SVG | MHC-II |
| **Figure 4A** | `paper/figures/Fig4A_dev_score_by_strategy.png`<br>`paper/figures/Fig4A_dev_score_by_strategy.svg` | PNG/SVG |  |
| **Figure 4B** | `paper/figures/Fig4B_hp_max9_by_strategy.png`<br>`paper/figures/Fig4B_hp_max9_by_strategy.svg` | PNG/SVG |  |
| **Figure 5** | `paper/figures/Fig5_7D12_surface_hydrophilicity_scatter.png`<br>`paper/figures/Fig5_7D12_surface_hydrophilicity_scatter.svg` | PNG/SVG | 7D12 |

### 
- `paper/FIGURES_TABLES_INDEX.md` - 

---

## 🔬 

### (SSOT - Single Source of Truth)

|  |  |
|------|------|
| `core/data/position_sets/imgt_position_sets.yaml` | SSOT(、Vernier、、ND、) |
| `data/germlines/vhh_v1/vhh_germline_assets_clean.jsonl` | VH |
| `data/germlines/vicugna_pacos_ig_aa/vhh_scaffolds/vhh_scaffolds.json` | VHH |

### 

|  |  |
|------|------|
| `output/developability_audit.md` | CMC/(、、) |
| `output/position_sets_generation_audit.md` |  |

### 7D12

|  |  |
|------|------|
| `output/7D12/7d12_4krl_variant_mutations.jsonl` | 7D12 Native/SR/BM |
| `output/7D12/7d12_4krl_per_residue_surface_metrics.csv` | 7D12 |
| `output/7D12/7d12_sr_vs_slice3_clinical_by_strategy.md` | 7D12-SR19VHH |
| `output/7D12/7d12_sr_cmc_optimization.md` | 7D12-SRCMC |

### IEDB

|  |  |
|------|------|
| `output/iedb_mhcii_audit.md` | 19VHHIEDB API(、、、) |
| `output/7D12/7d12_4krl_eval_audit.md` | 7D12IEDB |

---

## 🔧 

### 

|  |  |
|------|------|
| `scripts/run_slice3_complete_analysis.py` | Slice-3(19VHH) |
| `scripts/evaluate_7d12_4krl_variants.py` | 7D12 |
| `scripts/compare_7d12_sr_to_slice3_clinical.py` | 7D12-SRVHH |
| `scripts/optimize_7d12_sr_cmc.py` | 7D12-SRCMC |
| `scripts/paper_generate_figures_tables.py` |  |

### 

|  |  |
|------|------|
| `scripts/anarci_recompute_all_sequences.py` | VHHANARCI IMGT |
| `scripts/setup_position_sets_ssot.py` | SSOT |

---

## 📚 

### 

|  |  |
|------|------|
| `docs/vhh_humanization_methods_assets_index.md` | 、、 |
| `docs/paper_methods_snippets_vhh_humanization.md` | Methods |

### 

|  |  |
|------|------|
| `PAPER_FINALIZATION_REPORT.md` |  ⭐ |
| `FINAL_PROJECT_INDEX.md` |  ⭐ |

---

## 🎯 

### Slice-3VHH

- ****: 19VHH
- ****:
  - SR : 7
  - BM (+): 8
  - Native : 4
- ****:
  - : 3 (Ozoralizumab-JP, Caplacizumab-EU/US, Envafolimab-CN)
  - : 2
  - : 4
  - : 6
  - : 2
  - : 2

### 7D12

- ****: SR 
- ****: (23, 41, 104)、Vernier(28, 29, 94)、(37, 44, 45, 47)、CDR3
- ****: IMGT101 V→S (hp_max9: 0.889 → 0.778)
- ****: B_total_1pct=6 (SR)
- ****: dev_score=78 (，)

---

## 📖 

### 1. 
```bash
# 
open paper/VHH7D12_InSynBio.md
```

### 2. 
```bash
# 
python scripts/run_slice3_complete_analysis.py

# 
python scripts/paper_generate_figures_tables.py
```

### 3. 
```bash
# 7D12
cat output/7D12/7d12_sr_vs_slice3_clinical_by_strategy.md

# CMC
cat output/7D12/7d12_sr_cmc_optimization.md
```

### 4. 
```bash
# PDF (pandocwkhtmltopdf)
pandoc paper/VHH7D12_InSynBio.md --pdf-engine=wkhtmltopdf -o paper.pdf

# Word
pandoc paper/VHH7D12_InSynBio.md -o paper.docx
```

---

## 🔍 

### 

#### ?
→ `paper/VHH7D12_InSynBio.md` 

#### 19VHH?
→ `paper/tables/Table1_slice3_19_clinical_vhh_master.csv`  `.md`

#### 7D12?
→ `paper/tables/Table2_7D12_native_sr_bm_summary.csv` + `output/7D12/7d12_sr_vs_slice3_clinical_by_strategy.md`

#### ?
→ `docs/paper_methods_snippets_vhh_humanization.md` (Methods)

#### ?
→ `core/data/position_sets/imgt_position_sets.yaml`

#### IEDB?
→ `output/iedb_mhcii_audit.md`

#### ?
→ `scripts/run_slice3_complete_analysis.py`

---

## 📊 

- [x] 19VHH
- [x] ANARCI IMGT
- [x] (SR/BM/Native)
- [x] IEDB MHC-II
- [x] CMC/
- [x] 7D12
- [x] 7D12(PDB 4KRL)
- [x] 
- [x] **** ✅
- [x] 
- [x] 
- [x] 

---

## 🚀 

### 
1. (VHH、MHC-II)
2. Jupyter Notebook
3. web(HTML + )
4. VHH

### 
1. (arXiv)
2. GitHub/
3. 
4. 

---

## 📞 

****: `d:\InSynBio-AI-Research\Antibody_Engineer_Suite`

****:
- VHH, , 
- , , 
- IMGT, ANARCI
- MHC-II, CMC
- 7D12, , 

****:
- ANARCI (anarcii Python)
- IEDB MHC-IIAPI
- AlphaFold2 
- Matplotlib/Seaborn 

---

## 📝 

|  |  |  |
|------|------|------|
| 1.0 | 2024 |  +  |
| - | - | PAPER_FINALIZATION_REPORT  |
| - | - | FINAL_PROJECT_INDEX   |

---

****: ✅ ****

、、。Markdown，、。

---

*: 2024*  
*: InSynBio*  
*: *
