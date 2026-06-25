# VHH 

****: 2025-01-XX  
****: v1.0  
****: Antibody Engineer Suite

---

## 📊 

|  |  |  |  |  |
|-----------|------|---------|------|------|
| **VHH v1 ** | 264 | 781 KB | JSONL | ✅  |
| **VHH v1 FR** | 82 | 66 KB | JSONL | ✅  |
| **VHH-SAFE** | 90 | 205 KB | JSON | ✅  |
| **VHH** | 14 | 13 KB | JSON | ✅  |
| **EPS Scaffolds** | 3 | 1.8 KB | JSON | 🔶 MVP |
| **Cluster Scaffolds** | 3 | 1.7 KB | JSON | 🔶 MVP |
| **** | **456** | **1.07 MB** | - | - |

---

## 📚 

### 1. VHH Scaffold Library v1

****: `data/germlines/vhh_v1/vhh_scaffold_library_v1.jsonl`  
****: 264  
****: 781,796 bytes (781 KB)  
****: JSONL (JSON)

****:
-  stage1 scaffold ranking 
-  `--mode vhh`  scaffold 
-  native human FR 

****:
- ✅  VHH hallmark 
- ✅  CDR1/CDR2 canonical proxy 
- ✅  IMGT/Kabat 
- ✅  FR1/FR2/FR3/FR4 

****:
-  `vhh_germline_assets_clean_with_canonical_proxy.jsonl` (264) 
-  germline  scaffold 

****:
```python
from scripts.stage12_germline_selection import stage1_select_scaffold

result = stage1_select_scaffold(
    query_seq=seq,
    scaffold_library_path=None,  # None  manifest 
    germline_db="vhh_v1",
    vhh_hallmark_weight=0.15
)
```

****:
```json
{
  "scaffold_id": "VHH_FR_AM773729_IGHV1-1_01_Vicugna",
  "n_members": 1,
  "member_ids": ["AM773729|IGHV1-1*01|Vicugna"],
  "consensus": {
    "fr1": "...",
    "fr2": "...",
    "fr3": "...",
    "fr4": "",
    "framework_full": "..."
  },
  "vhh_hallmark": {...},
  "canonical_proxy_cdr1": {...},
  "canonical_proxy_cdr2": {...},
  "imgt_map": {...},
  "kabat_map": {...}
}
```

---

### 2. VHH Special FR Templates v1

****: `data/germlines/vhh_v1/vhh_special_fr_templates_v1.jsonl`  
****: 82  
****: 66,344 bytes (66 KB)  
****: JSONL (JSON)

****:
- FR-only 
-  FR /
-  stage1 scaffold ranking

****:
- `vhh_like`  (`ambiguous` AND `score >= 0.5`)
- `proxy_agg >= 0.80`
-  `fr_sequence` ，

****:
- ✅  VHH hallmark 
- ✅  canonical proxy 
- ✅ FR ，

****:
```python
result = stage1_select_scaffold(
    query_seq=seq,
    scaffold_library_path="data/germlines/vhh_v1/vhh_special_fr_templates_v1.jsonl",
    germline_db="vhh_v1",
    use_special_fr_templates=True
)
```

****:
```json
{
  "fr_id": "VHH_FR_0001",
  "template_type": "vhh_special_fr",
  "source_sequence_id": "...",
  "fr_sequence": "...",
  "segments": {
    "FR1": "...",
    "FR2": "...",
    "FR3": "..."
  },
  "vhh_hallmark": {...},
  "canonical_proxy": {...}
}
```

---

### 3. Human VH3 VHH-SAFE Templates

****: `data/germlines/human_ig_aa/vh_scaffolds/human_vh3_vhh_safe_templates.json`  
****: 90  
****: 204,982 bytes (205 KB)  
****: JSON 

****:
- VHH  pipeline
-  VHH → human-VHH 
- Developability 
- SaaS 

****:
- 30  Human VH3 scaffolds × 3  (A/B/C) = 90 

****:
- **A**: 44→Q, 45→R
- **B**: 37→Y/S, 44→Q, 45→R, 47→G
- **C（VHH）**: 37=Y, 44=Q, 45=R, 47=G

****:
- ✅  developability 
- ✅  CMC liabilities 
- ✅ 
- ✅  developability 

****:
```json
{
  "template_id": "HUMAN_VH3_SCF_01_SAFE_A",
  "source_scaffold": "HUMAN_VH3_SCF_01",
  "safe_plan": "A",
  "plan_name": "",
  "plan_description": "44→Q, 45→R",
  "consensus": {...},
  "mutations": {...},
  "n_members": 58,
  "developability": {
    "score": 0.14,
    "liabilities": [...]
  }
}
```

---

### 4. Vicugna Pacos VHH Scaffolds

****: `data/germlines/vicugna_pacos_ig_aa/vhh_scaffolds/vhh_scaffolds.json`  
****: 14  
****: 13,159 bytes (13 KB)  
****: JSON 

****:
- 
-  VHH 
- 

****:
```
73VHH
  ↓ (IMGT)
VHH
  ↓ (，0.90)
VHH（14）
```

****:
- ✅  73  VHH 
- ✅ Identity : 0.90
- ✅  cluster: VHH_SCF_04 (33)

****:
```json
{
  "scaffold_id": "VHH_SCF_01",
  "n_members": 2,
  "member_ids": [...],
  "consensus": {
    "fr1": "...",
    "fr2": "...",
    "fr3": "...",
    "fr4": "",
    "framework_full": "..."
  }
}
```

---

### 5. EPS Scaffolds VHH

****: `core/data/eps_scaffolds_vhh.json`  
****: 3  
****: 1,809 bytes (1.8 KB)  
****: JSON

****: 🔶 MVP 

****:
- Engineered Protein Scaffold 
- VHH 

****:
-  developability 
- 
-  Human VH3/VH1

****:
```json
{
  "template_id": "EPS_VHH_001",
  "name": "Human VH3-based EPS Scaffold 1",
  "sequence_v_region": "...",
  "regions": {
    "FR1": "...",
    "FR2": "...",
    "FR3": "...",
    "FR4": "..."
  },
  "metadata": {
    "source": "human_vh3",
    "developability_score": 0.85,
    "stability_class": "high"
  }
}
```

---

### 6. Cluster Scaffolds VHH

****: `core/data/cluster_scaffolds_vhh.json`  
****: 3  
****: 1,742 bytes (1.7 KB)  
****: JSON

****: 🔶 MVP 

****:
-  scaffold medoids
- VHH 

****:
- 
- 
- 

****:
```json
{
  "cluster_id": "CLUSTER_001",
  "cluster_size": 15,
  "medoid_sequence": "...",
  "regions": {...},
  "metadata": {
    "canonical_class": "VH3",
    "cluster_diversity": 0.12,
    "representative_quality": "high"
  }
}
```

---

## 🔗 

### Germline Assets 

**`vhh_germline_assets_clean_with_canonical_proxy.jsonl`** - 264
- ****:  germline ，
- ****:  scaffold 
- ****: `data/germlines/vhh_v1/vhh_germline_assets_clean_with_canonical_proxy.jsonl`

---

## 📋 

### 

1. ****: `vhh_scaffold_library_v1.jsonl` (264)
   -  stage1 scaffold ranking
   -  VHH 

2. ****: `vhh_special_fr_templates_v1.jsonl` (82)
   -  FR-only 
   -  FR 

3. ****: `human_vh3_vhh_safe_templates.json` (90)
   - VHH  pipeline
   -  developability 

4. ****: `vicugna_pacos_vhh_scaffolds.json` (14)
   - 
   - 

### /

- `eps_scaffolds_vhh.json`  `cluster_scaffolds_vhh.json`  MVP ，

---

## 🔧 

### 

- **vhh_scaffold_library_v1.jsonl**: `scripts/generate_vhh_special_fr_library.py`
- **vhh_special_fr_templates_v1.jsonl**: `scripts/build_vhh_special_fr_library_v1.py`
- **human_vh3_vhh_safe_templates.json**: `scripts/generate_human_vhh_safe_templates.py`
- **vicugna_pacos_vhh_scaffolds.json**: `scripts/generate_vhh_scaffold_panel.py`

### 

- **vhh_v1 **: 2025-12-13
- **Manifest**: `data/germlines/vhh_v1/manifest.json`

---

## 📈 

|  |  |  |
|------|------|------|
| VHH v1  | 346 | 75.9% |
|  VHH-SAFE | 90 | 19.7% |
|  VHH | 14 | 3.1% |
|  (EPS/Cluster) | 6 | 1.3% |

****: 456 

---

## 📝 

- **2025-01-XX**: ， 6  VHH 

---

## 🔍 

- [VHH v1 Manifest](./vhh_v1/manifest.json)
- [VHH Special FR Library README](./vhh_v1/VHH_SPECIAL_FR_LIBRARY_README.md)
- [Human VH3 Scaffolds README](../human_ig_aa/vh_scaffolds/README.md)
- [VHH Analysis System Summary](../../docs/VHH_ANALYSIS_SYSTEM_SUMMARY.md)




