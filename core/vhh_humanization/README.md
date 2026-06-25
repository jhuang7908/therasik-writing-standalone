# VHH

## 

`core/vhh_humanization.py` VHHhuman-VHH，Human VH3 VHH-SAFECDR。

## 

### `humanize_vhh()`

，VHHhuman-VHH。

```python
from core.vhh_humanization import humanize_vhh

result = humanize_vhh(
    seq="QVQLVQPGAELRKPGALLKVSCKASGYTFTSYYIDWVRQAPGQGLGWVGRIDPEDGGTNYAQKFQGRVTLTADTSTSTAYVELSSLRSEDTAVCYCVR",
    panel="A",
    top_k=3,
    species="alpaca",
    return_all_templates=False
)
```

#### 

- `seq` (str): VHH
- `panel` (str): 
  - `'A'`: （44→Q, 45→R）
  - `'B'`: （37→Y/S, 44→Q, 45→R, 47→G）
  - `'C'`: VHH（37=Y, 44=Q, 45=R, 47=G）
  - `'all'`: 
- `top_k` (int): k（3）
- `species` (str): （'alpaca'）
- `return_all_templates` (bool): （False）

#### 

dict，：

```python
{
    'success': bool,              # 
    'input': {
        'sequence': str,          # 
        'length': int,            # 
        'species': str,           # 
    },
    'best_match': {
        'alpaca_scaffold': str,   # scaffold ID
        'alpaca_identity': float, # scaffoldidentity
        'human_template': str,    # HumanID
        'humanized_sequence': str, # 
        'humanized_length': int,   # 
        'alignment_scores': {      # 
            'framework_identity': float,
            'framework_similarity': float,
            'fr1_identity': float,
            'fr2_identity': float,
            'fr3_identity': float,
            'fr2_hydrophobicity_mismatch': float,
            'vhh_hallmark_score': float,
        },
        'safe_plan': str,          # （A/B/C）
        'plan_name': str,          # 
    },
    'candidates': [               # 
        {
            'template_id': str,
            'source_scaffold': str,
            'safe_plan': str,
            'plan_name': str,
            'humanized_sequence': str,
            'humanized_length': int,
            'alignment_scores': dict,
            'mutations': dict,
        },
        ...
    ],
    'cdrs': {                     # CDR
        'CDR1': str,
        'CDR2': str,
        'CDR3': str,
    },
    'error': str,                  # （）
}
```

## 

### 

```python
from core.vhh_humanization import humanize_vhh

# VHH
vhh_seq = "QVQLVQPGAELRKPGALLKVSCKASGYTFTSYYIDWVRQAPGQGLGWVGRIDPEDGGTNYAQKFQGRVTLTADTSTSTAYVELSSLRSEDTAVCYCVR"

# （A）
result = humanize_vhh(vhh_seq, panel='A', top_k=3)

if result['success']:
    print(f": {result['best_match']['human_template']}")
    print(f": {result['best_match']['humanized_sequence']}")
    print(f"identity: {result['best_match']['alignment_scores']['framework_identity']:.1%}")
else:
    print(f": {result['error']}")
```

### 

```python
result = humanize_vhh(vhh_seq, panel='A', top_k=10, return_all_templates=True)

if result['success']:
    print(f" {len(result['candidates'])} ")
    for i, cand in enumerate(result['candidates'], 1):
        print(f"{i}. {cand['template_id']}: identity={cand['alignment_scores']['framework_identity']:.1%}")
```

### 

```python
for panel in ['A', 'B', 'C']:
    result = humanize_vhh(vhh_seq, panel=panel, top_k=1)
    if result['success']:
        best = result['best_match']
        print(f"{panel} ({best['plan_name']}): {best['human_template']}")
        print(f"  Identity: {best['alignment_scores']['framework_identity']:.1%}")
        print(f"  Hallmark: {best['alignment_scores']['vhh_hallmark_score']:.1%}")
```

## 

1. **IMGT**
   - VHHIMGT
   - FRCDR

2. **scaffold**
   - VHHscaffoldidentity
   - scaffold

3. **Human**
   - Human
   - （A/B/C）

4. **CDR**
   - VHHCDRHuman
   - ：`Human_FR1 + VHH_CDR1 + Human_FR2 + VHH_CDR2 + Human_FR3 + VHH_CDR3 + Human_FR4`

## 

：

- `data/germlines/vicugna_pacos_ig_aa/vhh_scaffolds/vhh_scaffolds.json`
  - VHH scaffold（14scaffold）

- `data/germlines/human_ig_aa/vh_scaffolds/human_vh3_vhh_safe_templates.json`
  - Human VH3 VHH-SAFE（90）

- `data/germlines/human_ig_aa/vh_scaffolds/human_vs_alpaca_scaffold_alignment.json`
  - （1260）

## 

### A（）
- ****: 44→Q, 45→R
- ****: ，
- ****: developability

### B（）
- ****: 37→Y/S, 44→Q, 45→R, 47→G
- ****: VHH
- ****: 

### C（VHH）
- ****: 37=Y, 44=Q, 45=R, 47=G
- ****: VHH
- ****: VHH

## 

：

- `IMGT`: ANARCII
- `scaffold`: VHHscaffold
- `Human`: 

## 

- **IMGT**: ANARCII，CPU，0.1-0.5
- ****: ，O(1)
- ****: 1

## 

- `core/numbering/imgt_anarcii.py`: IMGT
- `scripts/alpaca_vhh_numbering_and_split.py`: VHH
- `scripts/generate_human_vhh_safe_templates.py`: Human

## 

：

```bash
python scripts/test_vhh_humanization.py
```


















