# VHH Scaffold

## 

73VHH，（identity=0.90）14scaffold。

## 

- **VHH**: 73
- **Scaffold**: 14
- **Cluster**: 1，33，5.2

## 

### 1. `vhh_scaffolds.json`

JSON，scaffold：
- `scaffold_id`: scaffold（VHH_SCF_01）
- `n_members`: scaffoldVHH
- `member_ids`: ID
- `consensus`: 
  - `fr1`, `fr2`, `fr3`, `fr4`: FR
  - `framework_full`: （FR1+FR2+FR3+FR4）

****:
```json
{
  "scaffold_id": "VHH_SCF_04",
  "n_members": 33,
  "member_ids": ["ID1", "ID2", ...],
  "consensus": {
    "fr1": "EVQLVESGGGLVQPGGSLRLSCAAS",
    "fr2": "MSWVRQAPGKGLEWVSA",
    "fr3": "YYADSVKGRFTISRDNAKNTLYLQMNSLKPEGTAVYYC",
    "fr4": "",
    "framework_full": "EVQLVESGGGLVQPGGSLRLSCAASMSWVRQAPGKGLEWVSAYYADSVKGRFTISRDNAKNTLYLQMNSLKPEGTAVYYC"
  }
}
```

### 2. `vhh_scaffolds.fasta`

FASTA，：
- 
- BLAST
- 

****:
```
>VHH_SCF_04 | n_members=33 | fr_len=(25,17,38,0)
EVQLVESGGGLVQPGGSLRLSCAASMSWVRQAPGKGLEWVSAYYADSVKGRFTISRDNAK
NTLYLQMNSLKPEGTAVYYC
```

## Scaffold

| Scaffold ID |  |  |  |
|-------------|--------|---------|------|
| VHH_SCF_01 | 2 | 80aa | IGHV1 |
| VHH_SCF_02 | 3 | 80aa | IGHV1 |
| VHH_SCF_03 | 1 | 79aa | IGHV1 |
| **VHH_SCF_04** | **33** | **80aa** | **IGHV3（cluster）** |
| VHH_SCF_05 | 14 | 80aa | IGHV3 |
| VHH_SCF_06 | 5 | 80aa | IGHV3 |
| VHH_SCF_07 | 1 | 80aa |  |
| VHH_SCF_08 | 1 | 80aa |  |
| VHH_SCF_09 | 1 | 80aa |  |
| VHH_SCF_10 | 1 | 80aa |  |
| VHH_SCF_11 | 1 | 80aa |  |
| VHH_SCF_12 | 1 | 80aa |  |
| VHH_SCF_13 | 1 | 80aa |  |
| VHH_SCF_14 | 8 | 80aa | IGHV3 |

## 

### （Greedy Clustering）

1. cluster 1seed
2. ：
   - seedidentity ≥ 0.90，cluster
   - cluster

### 

clusterFR""：
- 
- gap（'-'）
- consensus
- 

## 

### Python

```python
import json
from pathlib import Path

# scaffold
json_file = Path("vhh_scaffolds.json")
with open(json_file, encoding='utf-8') as f:
    scaffolds = json.load(f)

# scaffold
largest = max(scaffolds, key=lambda x: x['n_members'])
print(f"scaffold: {largest['scaffold_id']}")
print(f": {largest['n_members']}")
print(f": {largest['consensus']['framework_full']}")

# FR2
fr2_seqs = [s['consensus']['fr2'] for s in scaffolds]
```

### scaffold

```python
# ID
scaffold = next(s for s in scaffolds if s['scaffold_id'] == 'VHH_SCF_04')
fr1 = scaffold['consensus']['fr1']
fr2 = scaffold['consensus']['fr2']
```

## 

- ****: `../vhh_numbered/vhh_numbered_and_split.json`
- ****: 0.90 (identity)
- ****: `scripts/generate_vhh_scaffold_panel.py`
- ****: 

## 

1. **VHH_SCF_04cluster**（33），IGHV3
2. **scaffold**（8），
3. **scaffoldFR4**，partial
4. **80aa**，VHH

## 

- : `../vhh_numbered/vhh_numbered_and_split.json`
- : `../alpaca_ighv_vhh_label.tsv`
- : `../IGHV_aa.fasta`


















