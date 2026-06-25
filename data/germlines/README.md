# Germline Assets Library

 VH germline 。

## 

```
germlines/
├── v1_clean/                    # 
│   ├── germline_assets_clean.jsonl
│   ├── germline_assets_clean_with_canonical_proxy.jsonl
│   ├── clusters/                # CDR1/CDR2 
│   │   ├── cdr1_cluster_assignments.csv
│   │   ├── cdr1_cluster_summary.csv
│   │   ├── cdr1_representatives.fasta
│   │   ├── cdr2_cluster_assignments.csv
│   │   ├── cdr2_cluster_summary.csv
│   │   └── cdr2_representatives.fasta
│   ├── qc/                      # 
│   │   └── canonical_proxy_qc.csv
│   └── manifest.json            # 
└── README.md                    # 
```

## 

### v1_clean

****

- ****:  458  germline 
- ****: 443  clean 
- ****: IMGT + Kabat 
- ****: FR1/CDR1/FR2/CDR2/FR3 
- **Canonical Proxy**: CDR1/CDR2 

## 

### 

#### `germline_assets_clean.jsonl`
- ****: JSON Lines ( JSON )
- ****:  germline ，：
  - IMGT/Kabat 
  - FR1/CDR1/FR2/CDR2/FR3 
  - 
  - 

#### `germline_assets_clean_with_canonical_proxy.jsonl`
- ****: JSON Lines
- ****:  `germline_assets_clean.jsonl` ：
  - `canonical_proxy_cdr1`: CDR1  canonical proxy 
  - `canonical_proxy_cdr2`: CDR2  canonical proxy 

###  (clusters/)

#### `cdr1_cluster_assignments.csv`
- ****: `sequence_id`, `cluster_id`, `length`
- ****:  CDR1 cluster 

#### `cdr1_cluster_summary.csv`
- ****: `cluster_id`, `length`, `cluster_size`, `cluster_percentile`, `intra_cluster_identity`, `proxy_score`, `representative`
- ****: CDR1  cluster 

#### `cdr1_representatives.fasta`
- ****: FASTA
- ****: CDR1  cluster 

#### CDR2 
-  CDR1 ， `cdr2_`

###  (qc/)

#### `canonical_proxy_qc.csv`
- ****: `sequence_id`, `cdr1_cluster_id`, `cdr1_proxy_score`, `cdr2_cluster_id`, `cdr2_proxy_score`
- ****:  canonical proxy 

### 

#### `manifest.json`
- ****: JSON
- ****: 、、

## 

###  clean assets

```python
import json
from pathlib import Path

assets_path = Path("data/germlines/v1_clean/germline_assets_clean.jsonl")

with open(assets_path, "r", encoding="utf-8") as f:
    for line in f:
        record = json.loads(line)
        seq_id = record["sequence_id"]
        cdr1 = record["segments"]["CDR1"]
        cdr2 = record["segments"]["CDR2"]
        print(f"{seq_id}: CDR1={cdr1}, CDR2={cdr2}")
```

###  canonical proxy 

```python
import json
from pathlib import Path

proxy_path = Path("data/germlines/v1_clean/germline_assets_clean_with_canonical_proxy.jsonl")

with open(proxy_path, "r", encoding="utf-8") as f:
    for line in f:
        record = json.loads(line)
        proxy_cdr1 = record.get("canonical_proxy_cdr1")
        if proxy_cdr1:
            print(f"CDR1: {proxy_cdr1['cluster_id']}, score={proxy_cdr1['proxy_score']}")
```

###  cluster 

```python
from Bio import SeqIO
from pathlib import Path

fasta_path = Path("data/germlines/v1_clean/clusters/cdr1_representatives.fasta")

for record in SeqIO.parse(fasta_path, "fasta"):
    cluster_id = record.id
    representative = str(record.seq)
    print(f"{cluster_id}: {representative}")
```

## 

### 
- ✅ IMGT  Kabat 
- ✅ FR1/CDR1/FR2/CDR2/FR3  > 0
- ✅  20 （ X/*/-）

### 
- ****: 443
- **CDR1 clusters**: 48
- **CDR2 clusters**: 66
- **CDR1 **: 8aa (38 clusters), 10aa (5), 9aa (3), 7aa (2)
- **CDR2 **: 8aa (39 clusters), 7aa (16), 6aa (4), 10aa (4), 9aa (2)

## 

- **v1_clean** (2025-01-XX): 
  -  458  443 
  -  IMGT/Kabat 
  -  FR1-FR3 
  -  CDR1/CDR2 canonical proxy 

## 

1. ****: `v1_clean` ，
2. **output/ **: `output/` ，
3. ****:  `manifest.json` 
