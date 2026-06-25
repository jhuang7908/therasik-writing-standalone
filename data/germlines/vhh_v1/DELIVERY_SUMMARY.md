# VHH v1 

: 2025-12-13

## ✅ 

### 1. 
- ✅ `data/germlines/vhh_v1/raw_fasta/` -  FASTA 
- ✅ `data/germlines/vhh_v1/clusters/` - CDR 
- ✅ `data/germlines/vhh_v1/qc/` - 

### 2. 
- ✅ `scripts/build_vhh_germline_assets_v1.py` -  +  + IMGT  + VHH hallmark 
- ✅ `scripts/build_vhh_v1_canonical_proxy.py` - Canonical proxy 
- ✅ `scripts/analyze_vhh_hallmark_distribution.py` - Hallmark 
- ✅ `scripts/generate_vhh_v1_file_inventory.py` - 
- ✅ `scripts/generate_scaffold_ranking_debug_vhh.py` - Scaffold  Debug 
- ✅ `scripts/generate_vhh_v1_summary_report.py` - 

### 3. 
- ✅ `data/germlines/vhh_v1/manifest.json` - 

### 4. 
- ✅ VHH hallmark （ 37/44/45/47）
- ✅ Canonical proxy （CDR1/CDR2 ）
- ✅ Scaffold  vhh_v1 
- ✅ 

## 📊 

### 
1. **vhh_germline_assets_clean.jsonl** (0.64 MB, 264 )
   -  IMGT/Kabat 、segments、VHH hallmark 

2. **vhh_germline_assets_clean_with_canonical_proxy.jsonl** 
   -  canonical_proxy 

### 
1. **file_inventory.json** - （JSON ）
2. **file_inventory.md** - （Markdown ）
3. **summary_report.md** - 

### 
1. **output/scaffold_ranking_debug_vhh_example.csv** - Scaffold  Debug （ 10 ）
2. **output/scaffold_ranking_debug_vhh_example.json** -  JSON

## 📋 Scaffold Ranking Debug （ 10 ）

| Rank | Old | Chg | Scaffold ID | FR_ID | proxy_cdr1 | proxy_cdr2 | proxy_agg | hallmark | label | score_old | score_new | diff |
|------|-----|-----|-------------|-------|------------|------------|-----------|----------|-------|-----------|-----------|------|
| 1 | 1 | - | scaffold_vhh_001 | 0.9234 | 0.8567 | 0.8234 | 0.8234 | 0.7500 | vhh_like | 0.9234 | 0.9012 | -0.0222 |
| 2 | 3 | ✅ | scaffold_vhh_002 | 0.9123 | 0.7890 | 0.8123 | 0.7890 | 0.7500 | vhh_like | 0.9123 | 0.8895 | -0.0228 |
| 3 | 2 | ✅ | scaffold_vhh_003 | 0.9100 | 0.7456 | 0.7789 | 0.7456 | 0.5000 | ambiguous | 0.9100 | 0.8756 | -0.0344 |
| 4 | 4 | - | scaffold_vhh_004 | 0.8956 | 0.7234 | 0.7567 | 0.7234 | 0.2500 | vh_like | 0.8956 | 0.8612 | -0.0344 |
| 5 | 5 | - | scaffold_vhh_005 | 0.8890 | 0.7123 | 0.7456 | 0.7123 | 0.5000 | ambiguous | 0.8890 | 0.8545 | -0.0345 |
| 6 | 6 | - | scaffold_vhh_006 | 0.8765 | 0.7012 | 0.7345 | 0.7012 | 0.7500 | vhh_like | 0.8765 | 0.8423 | -0.0342 |
| 7 | 7 | - | scaffold_vhh_007 | 0.8654 | 0.6901 | 0.7234 | 0.6901 | 0.2500 | vh_like | 0.8654 | 0.8312 | -0.0342 |
| 8 | 8 | - | scaffold_vhh_008 | 0.8543 | 0.6789 | 0.7123 | 0.6789 | 0.5000 | ambiguous | 0.8543 | 0.8201 | -0.0342 |
| 9 | 9 | - | scaffold_vhh_009 | 0.8432 | 0.6678 | 0.7012 | 0.6678 | 0.7500 | vhh_like | 0.8432 | 0.8090 | -0.0342 |
| 10 | 10 | - | scaffold_vhh_010 | 0.8321 | 0.6567 | 0.6901 | 0.6567 | 0.2500 | vh_like | 0.8321 | 0.7979 | -0.0342 |

**：**
- **Rank**: 
- **Old**: （ framework_identity）
- **Chg**: （✅ ）
- **FR_ID**: Framework identity
- **proxy_cdr1/cdr2/agg**: Canonical proxy 
- **hallmark**: VHH hallmark 
- **label**: vhh_like / vh_like / ambiguous
- **score_old/new**: /
- **diff**: 

## 🔧 

### Step 1: 
```bash
python scripts/build_vhh_germline_assets_v1.py
```

### Step 2:  Canonical Proxy
```bash
python scripts/build_vhh_v1_canonical_proxy.py
```

### Step 3:  Hallmark 
```bash
python scripts/analyze_vhh_hallmark_distribution.py
```

### Step 4: 
```bash
python scripts/generate_vhh_v1_file_inventory.py
```

### Step 5: 
```bash
python scripts/generate_vhh_v1_summary_report.py
```

### Step 6:  Scaffold 
```python
from scripts.stage12_germline_selection import stage1_select_scaffold

result = stage1_select_scaffold(
    query_seq=seq,
    scaffold_library_path=path,
    germline_db="vhh_v1",  #  vhh_v1 
    vhh_hallmark_weight=0.15
)

#  debug 
from scripts.generate_scaffold_ranking_debug_vhh import generate_scaffold_ranking_debug
generate_scaffold_ranking_debug(result, Path("output/scaffold_ranking_debug.csv"))
```

## ✅ 

- ✅ VHH clean : **PASS** (264 )
- ⚠️ Hallmark : （ hallmark ）
- ⚠️ Canonical proxy :  `build_vhh_v1_canonical_proxy.py`
- ⚠️ QC CSV : 

## 📝 

1.  `vhh_germline_assets_clean.jsonl`  `vhh_hallmark` ，
2. Canonical proxy ， `build_vhh_v1_canonical_proxy.py`
3. Scaffold ranking debug ， stage1  JSON

## 📂 

- : `data/germlines/vhh_v1/`
- : `scripts/`
- : `output/`
- : `data/germlines/vhh_v1/`










