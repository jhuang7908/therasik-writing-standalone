# 

## 

，。

## 

### IGHC

```
[V] - [CH1] - [Hinge] - [CH2] - [CH3] - [C_terminal]
         ↓        ↓        ↓       ↓          ↓
       ~98aa   ~12-19aa  ~110aa  ~107aa   ~27-71aa
```

### 

#### 1. CH1（Constant Heavy 1）
- ****：1
- ****：97-98aa（IgG）
- ****：
  - CL
  - 
- ****：

#### 2. Hinge Region
- ****：CH1CH2
- ****：12-19aa（IgG）
- ****：
  - FabFc
  - （C），
  - 
- ****：C

#### 3. CH2（Constant Heavy 2）
- ****：2
- ****：107-110aa
- ****：
  - Fc（FcγR）
  - （C1q）
  - 
- ****：N-（N-X-S/T）

#### 4. CH3（Constant Heavy 3）
- ****：3
- ****：107-110aa
- ****：
  - Fc
  - 
  - 
- ****：

#### 5. C_terminal（C）
- ****：CH3
- ****：27-71aa（IgG）
- ****：
  - （IgG）
  - （IgG）
  - 
- ****：

## CH4

### ❌ IgGCH4

****：IgGCH1、CH2、CH3，**CH4**。

### CH4？

1. **IgM**：CH4（5：CH1-CH4）
2. **IgE**：CH4（4：CH1-CH4）
3. **IgA**：CH4
4. **IgG**：**CH1-CH3，CH4**

### IgGCH4？

- IgG
- CH1-CH3IgG
- CH4IgMIgE

## 

### JSON

```json
{
  "IgG1*01": {
    "species": "human",
    "igg_type": "IgG1*01",
    "full_sequence": "...",
    "total_length": 401,
    "has_ch4": false,
    "regions": [
      {
        "region": "CH1",
        "start": 1,
        "end": 98,
        "length": 98,
        "header": "Human_IGHG1_CH1_IGHG1*01_98aa"
      },
      {
        "region": "Hinge",
        "start": 99,
        "end": 113,
        "length": 15,
        "header": "Human_IGHG1_Unknown_IGHG1*01_15aa"
      },
      ...
    ],
    "structure": {
      "has_ch1": true,
      "has_hinge": true,
      "has_ch2": true,
      "has_ch3": true,
      "has_ch4": false,
      "has_c_terminal": true
    }
  }
}
```

### FASTA

```
>IgG1*01|human|Full|401aa
...

>IgG1*01|human|CH1|1-98|98aa
CH1...

>IgG1*01|human|Hinge|99-113|15aa
Hinge...

>IgG1*01|human|CH2|114-223|110aa
CH2...

>IgG1*01|human|CH3|224-330|107aa
CH3...

>IgG1*01|human|C_terminal|331-401|71aa
C...
```

## 

### 

```python
import json

# 
with open('human_IGHC_annotated.json', 'r', encoding='utf-8') as f:
    annotated = json.load(f)

# IgG1*01CH2
igg1_01 = annotated['IgG1*01']
full_seq = igg1_01['full_sequence']

for region in igg1_01['regions']:
    if region['region'] == 'CH2':
        start = region['start'] - 1  # 0-based
        end = region['end']
        ch2_seq = full_seq[start:end]
        print(f"CH2: {ch2_seq}")
        break
```

### 

```python
def get_all_regions(annotated_data, igg_type):
    """IgG"""
    if igg_type not in annotated_data:
        return None
    
    igg_data = annotated_data[igg_type]
    full_seq = igg_data['full_sequence']
    regions = {}
    
    for region in igg_data['regions']:
        region_name = region['region']
        start = region['start'] - 1
        end = region['end']
        regions[region_name] = {
            'sequence': full_seq[start:end],
            'start': region['start'],
            'end': region['end'],
            'length': region['length']
        }
    
    return regions

# 
regions = get_all_regions(annotated, 'IgG1*01')
print(f"CH1: {regions['CH1']['sequence'][:20]}...")
print(f"Hinge: {regions['Hinge']['sequence']}")
print(f"CH2: {regions['CH2']['sequence'][:20]}...")
```

## 

### 

|  |  |  |
|------|---------|------|
| CH1 | 98aa | 98aa |
| Hinge | 15aa | 12-17aa |
| CH2 | 110aa | 110aa |
| CH3 | 107aa | 107aa |
| C_terminal | 71aa | 44aa+27aa |

### 

|  |  |  |
|------|---------|------|
| CH1 | 97aa | 97aa |
| Hinge | 13aa | 13-16aa |
| CH2 | 107aa | 107-110aa |
| CH3 | 107aa | 107-109aa |
| C_terminal | 71aa | 27-44aa |

### 

|  |  |  |
|------|---------|------|
| CH1 | 97aa | 97aa |
| Hinge | 14aa | 14-19aa |
| CH2 | 110aa | 110aa |
| CH3 | 110aa | 109-110aa |
| C_terminal | 71aa | 44aa+27aa（IgG2） |

## 

- `{species}_IGHC_annotated.json`: JSON
- `{species}_IGHC_annotated.fasta`: FASTA
- `annotation_summary.json`: 

## 

1. **1-based**：JSONstartend1-based（1）
2. **Python0-based**：1
3. **C**：IgGC
4. **CH4**：IgGCH4，
5. ****：CH1 → Hinge → CH2 → CH3 → C_terminal


















