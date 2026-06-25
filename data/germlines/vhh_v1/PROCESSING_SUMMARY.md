# VHH v1 

: 2025-12-13

## ✅ 

### Step 1: VHH Hallmark 

****: `scripts/add_vhh_hallmark_to_existing_records.py`

****:
- ✅ : 264
- ✅ PASS : 264 (100%)
- ✅  `vhh_hallmark` 

**Hallmark **:
- `vhh_like`: 17  (6.4%)
- `vh_like`: 70  (26.5%)
- `ambiguous`: 177  (67.0%)

****:
- `data/germlines/vhh_v1/vhh_germline_assets_clean.jsonl` (， vhh_hallmark )
- `data/germlines/vhh_v1/qc/vhh_hallmark_distribution.csv`

### Step 2: Canonical Proxy 

****: `scripts/build_vhh_v1_canonical_proxy.py`

****:
- ✅ : 264
- ✅ CDR1 : 264  (100%)
- ✅ CDR2 : 264  (100%)
- ✅ PASS : 264 (100%)

****:
- CDR1: 30  clusters
- CDR2: 46  clusters

****:
- `data/germlines/vhh_v1/vhh_germline_assets_clean_with_canonical_proxy.jsonl` (264 )
- `data/germlines/vhh_v1/clusters/cdr1_cluster_assignments.csv` (264 )
- `data/germlines/vhh_v1/clusters/cdr1_cluster_summary.csv` (30  clusters)
- `data/germlines/vhh_v1/clusters/cdr1_representatives.fasta` (30 )
- `data/germlines/vhh_v1/clusters/cdr2_cluster_assignments.csv` (264 )
- `data/germlines/vhh_v1/clusters/cdr2_cluster_summary.csv` (46  clusters)
- `data/germlines/vhh_v1/clusters/cdr2_representatives.fasta` (46 )
- `data/germlines/vhh_v1/qc/canonical_proxy_qc_vhh.csv` (264 )

## ✅ 

****: `scripts/verify_vhh_v1_output.py`

****:
- ✅ : 264 = 264 ✓
- ✅  vhh_hallmark: 264 / 264 ✓
- ✅  canonical_proxy_cdr1: 264 / 264 ✓
- ✅  canonical_proxy_cdr2: 264 / 264 ✓
- ✅  (PASS): 264 / 264 ✓

## 📋 

：

```json
{
  "sequence_id": "...",
  "imgt_map": {...},
  "kabat_map": {...},
  "segments": {...},
  "vhh_hallmark": {
    "kabat_positions": {"37": "...", "44": "...", "45": "...", "47": "..."},
    "score": 0.0-1.0,
    "label": "vhh_like" | "vh_like" | "ambiguous"
  },
  "canonical_proxy_cdr1": {
    "cdr": "CDR1",
    "length": 8,
    "cluster_id": "...",
    "cluster_size": 6,
    "cluster_percentile": 0.5909,
    "rep_identity": 1.0,
    "proxy_score": 0.7545
  },
  "canonical_proxy_cdr2": {
    "cdr": "CDR2",
    "length": 8,
    "cluster_id": "...",
    "cluster_size": 6,
    "cluster_percentile": 0.6667,
    "rep_identity": 1.0,
    "proxy_score": 0.8
  },
  "qa_status": "PASS_CLEAN"
}
```

## 📊 

### Hallmark 
- **vhh_like**: 17  (6.4%) -  VHH 
- **vh_like**: 70  (26.5%) -  VH
- **ambiguous**: 177  (67.0%) - 

### Canonical Proxy
- **CDR1 **: 30  clusters， 7 
- **CDR2 **: 46  clusters， 9 
- **100% **:  264  CDR1  CDR2  cluster

## ✅ 

- ✅ VHH clean : **PASS** (264 )
- ✅ Hallmark : **PASS** (264/264)
- ✅ Canonical proxy : **PASS** (264/264, 100% )
- ✅ QC CSV : **PASS** ( QC )
- ✅ PASS  = 264: **PASS** ✓

## 📂 

### 
1. `vhh_germline_assets_clean.jsonl` -  vhh_hallmark  clean 
2. `vhh_germline_assets_clean_with_canonical_proxy.jsonl` - （ hallmark + proxy）

### Cluster 
1. `clusters/cdr1_cluster_assignments.csv`
2. `clusters/cdr1_cluster_summary.csv`
3. `clusters/cdr1_representatives.fasta`
4. `clusters/cdr2_cluster_assignments.csv`
5. `clusters/cdr2_cluster_summary.csv`
6. `clusters/cdr2_representatives.fasta`

### QC 
1. `qc/vhh_hallmark_distribution.csv` - Hallmark 
2. `qc/canonical_proxy_qc_vhh.csv` - Canonical proxy QC

## 🎯 

****:
- ✅ 
- ✅  record 
- ✅ PASS  = 264










