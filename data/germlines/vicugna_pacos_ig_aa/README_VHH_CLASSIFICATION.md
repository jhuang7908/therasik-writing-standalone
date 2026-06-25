# IGHVVHH/VH

## 

IGHVVHH/VH。FR2hallmark（37、44、45、47）。

## 

### FR2 Hallmark

VHHFR2：

- **37**: （Y, S, N, T, H, Q）
- **44**: QE- **VHH**
- **45**: R- **VHH**
- **47**: GL- **VHH**

### 

- 44QE: +1.0
- 45R: +1.0
- 47GL: +1.0
- 37: +0.5

****: score >= 2.0 VHH，VH

## 

### 

- `IGHV_aa.fasta`: IGHV（84）

### 

- `alpaca_ighv_vhh_label.tsv`: TSV

#### TSV

|  |  |
|------|------|
| id | ID（FASTA header） |
| length |  |
| label | （VHH/VH/UNKNOWN） |
| vhh_score | VHH（0.0-3.5） |
| aa37 | 37 |
| aa44 | 44 |
| aa45 | 45 |
| aa47 | 47 |

## 

### 1. 

```bash
# ANARCI
pip install anarci

# abnumber
pip install abnumber
```

### 2. 

```bash
python scripts/alpaca_vhh_classifier.py
```

### 3. 

：
```
data/germlines/vicugna_pacos_ig_aa/alpaca_ighv_vhh_label.tsv
```

## 

: `scripts/alpaca_vhh_classifier.py`

### 

1. **FASTA**: `IGHV_aa.fasta`
2. **IMGT**: ANARCIabnumberIMGT
3. **hallmark**: 37、44、45、47
4. ****: VHHVH
5. **TSV**: TSV

### 

- `anarci_abnumber_adapter`（abnumberANARCI fallback）
- ，ANARCI
- ANARCIAPI（`run_anarci``anarci`）

## 

FR2 hallmark，VHH，FR2VHH。

## 

1. **IMGT**: IMGT，UNKNOWN
2. ****: （score >= 2.0）
3. ****: hallmark，"-"

## 

- : `scripts/alpaca_vhh_classifier.py`
- : `scripts/anarci_abnumber_adapter.py`
- : `data/germlines/vicugna_pacos_ig_aa/IGHV_aa.fasta`


















