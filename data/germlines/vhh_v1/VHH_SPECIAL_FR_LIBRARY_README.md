# VHH Scaffold/FR Libraries v1

## 

VHH v1 ：

1. **`vhh_scaffold_library_v1.jsonl`** (264 ):  stage1 scaffold ranking 
2. **`vhh_special_fr_templates_v1.jsonl`** (82 ): FR-only ， FR /， stage1

## vhh_scaffold_library_v1.jsonl

****:
-  native human FR 
-  `--mode vhh`  scaffold 
-  264  scaffold （ germline ）

## 

****: JSONL（ JSON ）

****:
```json
{
  "scaffold_id": "VHH_FR_AM773729_IGHV1-1_01_Vicugna",
  "n_members": 1,
  "member_ids": ["AM773729|IGHV1-1*01|Vicugna"],
  "consensus": {
    "fr1": "QVQLVQPGAELRKPGALLKVSCKAS",
    "fr2": "IDWVRQAPGQGLGWVGR",
    "fr3": "NYAQKFQGRVTLTADTSTSTAYVELSSLRSEDTAVCYC",
    "fr4": "",
    "framework_full": "QVQLVQPGAELRKPGALLKVSCKASIDWVRQAPGQGLGWVGRNYAQKFQGRVTLTADTSTSTAYVELSSLRSEDTAVCYC"
  },
  "vhh_hallmark": {
    "kabat_positions": {"37": "V", "44": "G", "45": "L", "47": "W"},
    "score": 0.5,
    "label": "ambiguous"
  },
  "canonical_proxy_cdr1": {
    "cdr": "CDR1",
    "length": 8,
    "cluster_id": "cdr1_L8_C1",
    "cluster_size": 6,
    "cluster_percentile": 0.5909,
    "rep_identity": 1.0,
    "proxy_score": 0.7545
  },
  "canonical_proxy_cdr2": {
    "cdr": "CDR2",
    "length": 8,
    "cluster_id": "cdr2_L8_C1",
    "cluster_size": 6,
    "cluster_percentile": 0.6667,
    "rep_identity": 1.0,
    "proxy_score": 0.8
  },
  "imgt_map": {...},
  "kabat_map": {...}
}
```

## 

### （ scaffold ）
- `scaffold_id`: Scaffold 
- `n_members`: （ 1）
- `member_ids`:  ID 
- `consensus`: 
  - `fr1`, `fr2`, `fr3`, `fr4`:  FR 
  - `framework_full`: （FR1+FR2+FR3+FR4）

### VHH 
- `vhh_hallmark`: VHH hallmark 
- `canonical_proxy_cdr1`: CDR1  canonical proxy 
- `canonical_proxy_cdr2`: CDR2  canonical proxy 

### 
- `imgt_map`: IMGT 
- `kabat_map`: Kabat 

## 

###  stage1_select_scaffold 

** scaffold_library (264)**:
```python
from scripts.stage12_germline_selection import stage1_select_scaffold

#  vhh_scaffold_library_v1.jsonl ( manifest )
result = stage1_select_scaffold(
    query_seq=seq,
    scaffold_library_path=None,  # None  manifest 
    germline_db="vhh_v1",
    vhh_hallmark_weight=0.15
)
```

** special_fr_templates (82)**:
```python
#  FR 
result = stage1_select_scaffold(
    query_seq=seq,
    scaffold_library_path="data/germlines/vhh_v1/vhh_special_fr_templates_v1.jsonl",
    germline_db="vhh_v1",
    vhh_hallmark_weight=0.15,
    use_special_fr_templates=True  # 
)
```

### 

1. ** JSONL **: `stage1_select_scaffold` ， JSONL  scaffold 
2. ** VHH **:  scaffold  `vhh_hallmark`  `canonical_proxy`，， germline_assets 
3. ** native human FR **:  `human_vh3_scaffolds.json` ，

## 

### vhh_scaffold_library_v1.jsonl

****: `scripts/generate_vhh_special_fr_library.py`

****: `vhh_germline_assets_clean_with_canonical_proxy.jsonl`

****:
1.  264  germline 
2.  scaffold 
3.  VHH hallmark  canonical_proxy 
4.  JSONL 

### vhh_special_fr_templates_v1.jsonl

****: `scripts/build_vhh_special_fr_library_v1.py`

****: `vhh_germline_assets_clean_with_canonical_proxy.jsonl`

****:
1.  `proxy_agg = min(proxy_cdr1, proxy_cdr2)`
2. : `vhh_like`  (`ambiguous` AND `score >= 0.5`) AND `proxy_agg >= 0.80`
3.  `fr_sequence` ，
4.  `fr_id`: VHH_FR_0001, VHH_FR_0002, ...

## vhh_special_fr_templates_v1.jsonl

****:
- FR-only 
-  FR /
-  stage1 scaffold ranking

****:
- : `scripts/build_vhh_special_fr_library_v1.py`
- : `vhh_like`  (`ambiguous` AND `score >= 0.5`) AND `proxy_agg >= 0.80`
- :  `fr_sequence` ，
- : 82  FR 

## 

### vhh_scaffold_library_v1.jsonl
- ✅  scaffold : 264
- ✅  consensus: 264/264
- ✅  framework_full: 264/264
- ✅  vhh_hallmark: 264/264
- ✅  canonical_proxy: 264/264

### vhh_special_fr_templates_v1.jsonl
- ✅  FR : 82
- ✅ : 82/82

##  native human FR 

 `human_vh3_scaffolds.json` ：
-  scaffold 
-  `stage1_select_scaffold`
-  `--mode vhh` ，

## 

1. **JSONL vs JSON**:  JSONL ， `human_vh3_scaffolds.json`  JSON 。`stage1_select_scaffold` 。

2. **VHH **:  scaffold  VHH （hallmark、canonical_proxy），， germline_assets 。

3. ****:  vhh_v1 ，：
   - Framework Identity (: 1.0 - 0.10 - 0.15 = 0.75)
   - Canonical Proxy (: 0.10)
   - VHH Hallmark (: 0.15)










