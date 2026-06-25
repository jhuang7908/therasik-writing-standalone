# VHHIMGTFR/CDR

## 

73VHHIMGTFR/CDR。

## 

- **VHH**: 73
- ****: 73（100%）
- ****: 0

## 

### 1. `vhh_numbered_and_split.json`

JSON，：
- 
- IMGT
- FR/CDR
- FR2 hallmark（37/44/45/47）
- VHH

****:
```json
{
  "total_vhh": 73,
  "success_count": 73,
  "failed_count": 0,
  "results": [
    {
      "id": "ID",
      "original_sequence": "",
      "length": 98,
      "numbering": [
        {"pos": 1, "ins_code": " ", "aa": "Q", "chain_type": "H", "scheme": "imgt"},
        ...
      ],
      "pos_map": {37: "Y", 44: "Q", 45: "A", 47: "G", ...},
      "regions": {
        "FR1": "QVQLVQPGAELRKPGALLKVSCKAS",
        "CDR1": "GYTFTSYY",
        "FR2": "IDWVRQAPGQGLGWVGR",
        "CDR2": "IDPEDGGT",
        "FR3": "NYAQKFQGRVTLTADTSTSTAYVELSSLRSEDTAVCYC",
        "CDR3": "VR",
        "FR4": ""
      },
      "hallmarks": {
        "aa37": "Y",
        "aa44": "Q",
        "aa45": "A",
        "aa47": "G"
      },
      "vhh_score": 2.5
    }
  ]
}
```

### 2. `vhh_numbered.fasta`

FASTA，：
- 
- （FR1, CDR1, FR2, CDR2, FR3, CDR3, FR4）

****:
```
>ID|VHH|Full
...

>ID|VHH|FR1|25aa
FR1...

>ID|VHH|CDR1|8aa
CDR1...
```

### 3. `vhh_summary.tsv`

TSV，：

|  |  |
|------|------|
| id | ID |
| length |  |
| vhh_score | VHH |
| aa37, aa44, aa45, aa47 | FR2 hallmark |
| FR1_len ~ FR4_len |  |

## 

### 

|  |  |  |  |
|------|---------|---------|---------|
| FR1 | 24aa | 25aa | 25.0aa |
| CDR1 | 8aa | 10aa | 8.3aa |
| FR2 | 16aa | 17aa | 17.0aa |
| CDR2 | 6aa | 8aa | 7.7aa |
| FR3 | 36aa | 38aa | 38.0aa |
| CDR3 | 0aa | 2aa | 0.2aa |
| FR4 | 0aa | 0aa | 0.0aa |

****: partial，CDR3FR4。

### FR2 Hallmark

|  |  |  |
|------|---------|------|
| 37 | Y | 65/73 (89%) |
| 44 | Q | 73/73 (100%) |
| 45 | A | 60/73 (82%) |
| 47 | G | 73/73 (100%) |

****:
- 44（Q）47（G）VHH
- 37Y
- 45A（R，VHH）

## 

### Python

```python
import json
from pathlib import Path

# 
json_file = Path("vhh_numbered_and_split.json")
with open(json_file, encoding='utf-8') as f:
    data = json.load(f)

# VHH
vhh = data['results'][0]

# 
fr2 = vhh['regions']['FR2']
cdr3 = vhh['regions']['CDR3']

# hallmark
aa44 = vhh['hallmarks']['aa44']  # 'Q'

# 
pos_map = vhh['pos_map']
aa_37 = pos_map.get(37)  # 'Y'
```

### FR2

```python
import json

with open("vhh_numbered_and_split.json", encoding='utf-8') as f:
    data = json.load(f)

fr2_sequences = [r['regions']['FR2'] for r in data['results']]
```

## 

- ****: ANARCII ( `core/numbering/imgt_anarcii.py`)
- ****: IMGT
- ****: IMGT
- ****: `scripts/alpaca_vhh_numbering_and_split.py`

## 

- : `../alpaca_ighv_vhh_label.tsv`
- : `../IGHV_aa.fasta`
- : `../../../../core/numbering/imgt_anarcii.py`


















