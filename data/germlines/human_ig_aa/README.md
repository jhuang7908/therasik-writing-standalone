# IG

IMGT（Ig）。

## 

- ****: `data/germlines/IMGT_V-/IMGT_V-QUEST_reference_directory/Homo_sapiens/IG/`
- ****: Homo_sapiens 
- ****: DNA（FASTA）
- ****: `scripts/translate_human_ig_dna_to_aa.py`

## 

### FASTA

|  |  |  |  |
|------|---------|------|------|
| `IGHV_aa.fasta` | V | 458 |  |
| `IGHD_aa.fasta` | D | 47 |  |
| `IGHJ_aa.fasta` | J | 15 |  |
| `IGKV_aa.fasta` | κV | 129 | κ |
| `IGKJ_aa.fasta` | κJ | 9 | κ |
| `IGLV_aa.fasta` | λV | 118 | λ |
| `IGLJ_aa.fasta` | λJ | 10 | λ |

### JSON

JSON，：
- ID
- header
- 
- 

### 

- `human_ig_aa_summary.json`: 

## 

- ****: 786
- ****: 780
- ****: 7

## 

### FASTA

```python
from pathlib import Path

fasta_file = Path("data/germlines/human_ig_aa/IGHV_aa.fasta")
with open(fasta_file) as f:
    header = None
    for line in f:
        if line.startswith(">"):
            header = line.strip[1:]
        else:
            sequence = line.strip
            # 
```

### JSON

```python
import json
from pathlib import Path

json_file = Path("data/germlines/human_ig_aa/IGHV_aa.json")
data = json.loads(json_file.read_text(encoding="utf-8"))

for entry in data["entries"]:
    seq_id = entry["id"]
    sequence = entry["sequence_aa"]
    # 
```

## 

1. DNA，
2. （*）
3. gap（-）（...）
4. （X），DNAN

## 

- ：IMGT DNA


















