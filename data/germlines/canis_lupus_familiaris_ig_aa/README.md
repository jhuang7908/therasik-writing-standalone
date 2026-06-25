# IG

IMGT（Canis lupus familiaris）（Ig）。

## 

- ****: `data/germlines/IMGT_V-/IMGT_V-QUEST_reference_directory/Canis_lupus_familiaris/IG/`
- ****: Canis_lupus_familiaris 
- ****: DNA（FASTA）
- ****: `scripts/translate_ig_dna_to_aa.py`

## 

### FASTA

|  |  |  |  |
|------|---------|------|------|
| `IGHV_aa.fasta` | V | 54 |  |
| `IGHD_aa.fasta` | D | 6 |  |
| `IGHJ_aa.fasta` | J | 6 |  |
| `IGKV_aa.fasta` | κV | 61 | κ |
| `IGKJ_aa.fasta` | κJ | 5 | κ |
| `IGLV_aa.fasta` | λV | 122 | λ |
| `IGLJ_aa.fasta` | λJ | 9 | λ |

### JSON

JSON，：
- ID
- header
- 
- 

### 

- `canis_lupus_familiaris_ig_aa_summary.json`: 

## 

- ****: 263
- ****: 263
- ****: 7

## 

### FASTA

```python
from pathlib import Path

fasta_file = Path("data/germlines/canis_lupus_familiaris_ig_aa/IGHV_aa.fasta")
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

json_file = Path("data/germlines/canis_lupus_familiaris_ig_aa/IGHV_aa.json")
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


















