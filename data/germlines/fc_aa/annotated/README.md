# 

，CH1、Hinge、CH2、CH3C。

## 

### JSON

- `{species}_IGHC_annotated.json`: 
  - IgG：
    - `full_sequence`: 
    - `regions`: ，：
      - `region`: （CH1、Hinge、CH2、CH3、C_terminal）
      - `start`: （1-based）
      - `end`: （1-based）
      - `length`: 
      - `header`: header

### FASTA

- `{species}_IGHC_annotated.fasta`: FASTA
  - 
  - Header: `{IgG}|{}|{}|{-}|{}aa`

## 

### IGHC

IgG：

1. **CH1** (Constant Heavy 1)
   - ：1
   - ：~97-98aa
   - ：CL

2. **Hinge Region** 
   - ：CH1CH2
   - ：~12-19aa
   - ：，

3. **CH2** (Constant Heavy 2)
   - ：2
   - ：~107-110aa
   - ：Fc，

4. **CH3** (Constant Heavy 3)
   - ：3
   - ：~107-110aa
   - ：Fc，

5. **C_terminal** (C)
   - ：CH3
   - ：~27-71aa（IgG）
   - ：（IgG）

### CH4

**❌ CH4**

- IgGCH1、CH2、CH3
- CH4：
  - **IgM****IgE**：CH4
  - **IgA**：CH4
  - **IgG**：**CH4**

，IgGCH4，。

## 

### Python

```python
import json
from pathlib import Path

# 
with open('human_IGHC_annotated.json', 'r', encoding='utf-8') as f:
    annotated = json.load(f)

# IgG1*01
igg1_01 = annotated['IgG1*01']

# 
full_seq = igg1_01['full_sequence']

# 
for region in igg1_01['regions']:
    region_name = region['region']
    start = region['start'] - 1  # 0-based
    end = region['end']
    region_seq = full_seq[start:end]
    
    print(f"{region_name}: {region_seq[:20]}... ({region['length']}aa)")
```

### 

```python
def extract_region(annotated_data, igg_type, region_name):
    """"""
    if igg_type not in annotated_data:
        return None
    
    igg_data = annotated_data[igg_type]
    full_seq = igg_data['full_sequence']
    
    for region in igg_data['regions']:
        if region['region'] == region_name:
            start = region['start'] - 1
            end = region['end']
            return full_seq[start:end]
    
    return None

# CH2
ch2_seq = extract_region(annotated, 'IgG1*01', 'CH2')
```

## 

### 

- **CH1**: 98aa
- **Hinge**: 12-17aa（IgG）
- **CH2**: 110aa
- **CH3**: 107aa
- **C_terminal**: 44aa + 27aa

### 

- **CH1**: 97aa
- **Hinge**: 13-16aa
- **CH2**: 107-110aa
- **CH3**: 107-109aa
- **C_terminal**: 27-44aa

### 

- **CH1**: 97aa
- **Hinge**: 14-19aa
- **CH2**: 110aa
- **CH3**: 109-110aa
- **C_terminal**: 44aa + 27aa（IgG2）

## 

1. **1-based**：JSON，startend1-based（1）
2. **Python0-based**：1
3. **C**：IgGC，
4. **CH4**：IgGCH4，CH1-CH3

## 

- ：`../{species}/IGHC_{species}.fasta`
- ：`../../scripts/annotate_constant_regions.py`
- ：`annotation_summary.json`


















