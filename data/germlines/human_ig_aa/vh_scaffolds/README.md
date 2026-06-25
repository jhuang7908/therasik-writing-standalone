# Human VH3 → VHH-SAFE Scaffold Panel

## 

Human VH3 → Human VHH-SAFE Scaffold Panel，VHH。

## 

### 1. 

**`vh_numbered/human_vh_numbered_and_split.json`**
- 198Human VH3IMGTFR/CDR
- VHHIMGT
- FR2 hallmark

### 2. Human VH3 Scaffold

**`human_vh3_scaffolds.json`** / **`human_vh3_scaffolds.fasta`**
- 30Human VH3 scaffold cluster
- （identity=0.90）
- scaffoldFR1/FR2/FR3/FR4

****:
- scaffold: 30
- Cluster: 1，58，6.6
- cluster: HUMAN_VH3_SCF_01 (58)

### 3. VHH-SAFE

**`human_vh3_vhh_safe_templates.json`** / **`human_vh3_vhh_safe_templates.fasta`**
- 90VHH-SAFE（30 scaffolds × 3）
- ：
  - **A**: 44→Q, 45→R
  - **B**: 37→Y/S, 44→Q, 45→R, 47→G
  - **C（VHH）**: 37=Y, 44=Q, 45=R, 47=G

****:
- VHHpipeline
- VHH → human-VHH
- Developability
- SaaS

### 4. 

**`human_vs_alpaca_scaffold_alignment.tsv`** / **`human_vs_alpaca_scaffold_alignment.json`**
- 1260（90human × 14scaffold）
- ：
  - FR1/FR2/FR3 identity
  - Framework identity/similarity
  - FR2 hydrophobicity mismatch
  - VHH hallmark

****:
- identity: HUMAN_VH3_SCF_01_SAFE_A vs VHH_SCF_04 (92.5%)
- similarity: HUMAN_VH3_SCF_01_SAFE_A vs VHH_SCF_04 (95.0%)
- hallmark: HUMAN_VH3_SCF_01_SAFE_A vs VHH_SCF_01 (100.0%)

## 

```
vh_scaffolds/
├── human_vh3_scaffolds.json          # Human VH3 scaffold（JSON）
├── human_vh3_scaffolds.fasta          # Human VH3 scaffold（FASTA）
├── human_vh3_vhh_safe_templates.json # VHH-SAFE（JSON）
├── human_vh3_vhh_safe_templates.fasta # VHH-SAFE（FASTA）
├── human_vs_alpaca_scaffold_alignment.tsv  # （TSV）
├── human_vs_alpaca_scaffold_alignment.json # （JSON）
└── README.md                          # 
```

## 

### Python

#### 1. Human VH3 Scaffold

```python
import json
from pathlib import Path

scaffolds_file = Path("human_vh3_scaffolds.json")
with open(scaffolds_file, encoding='utf-8') as f:
    scaffolds = json.load(f)

# scaffold
largest = max(scaffolds, key=lambda x: x['n_members'])
print(f"scaffold: {largest['scaffold_id']}")
print(f": {largest['consensus']['framework_full']}")
```

#### 2. VHH-SAFE

```python
templates_file = Path("human_vh3_vhh_safe_templates.json")
with open(templates_file, encoding='utf-8') as f:
    templates = json.load(f)

# 
plan_a_templates = [t for t in templates if t['safe_plan'] == 'A']
print(f"A: {len(plan_a_templates)}")
```

#### 3. 

```python
import pandas as pd

alignment_file = Path("human_vs_alpaca_scaffold_alignment.tsv")
df = pd.read_csv(alignment_file, sep='\t')

# 
best = df.nlargest(10, 'framework_identity')
print(best[['human_template', 'alpaca_scaffold', 'framework_identity', 'vhh_hallmark_score']])
```

## 

### 
- ****: （Greedy Clustering）
- ****: identity ≥ 0.90
- ****: 

### VHH-SAFE
- **A**: ，4445
- **B**: ，37/44/45/47，SS
- **C**: VHH，scaffold

### 
- **Identity**: 
- **Similarity**: （BLOSUM62）
- **Hydrophobicity mismatch**: FR2
- **VHH hallmark**: 37/44/45/47VHH

## 

- : `../vh_numbered/human_vh_numbered_and_split.json`
- VHH scaffolds: `../../vicugna_pacos_ig_aa/vhh_scaffolds/vhh_scaffolds.json`
- : `scripts/generate_human_vh3_scaffold_panel.py`, `scripts/generate_human_vhh_safe_templates.py`, `scripts/align_human_vs_alpaca_scaffolds.py`

## 

1. **HUMAN_VH3_SCF_01cluster**（58），VHH_SCF_04（95%）
2. **Ascaffold**，
3. **90VHH-SAFE30Human VH3 scaffold**，
4. ****，VHH

## 

1. **VHH**: VHHCDRHuman VH3 VHH-SAFE
2. ****: Human
3. **Developability**: 
4. **SaaS**: 


















