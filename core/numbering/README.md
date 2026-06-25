# IMGT

IMGT，ANARCII。

## 

### 

```python
from core.numbering.imgt_anarcii import imgt_number_anarcii, build_pos_to_aa_map

# IMGT
seq = "EVQLVESGGGLVQPGGSLRLSCAASGFTFDDYAMSWVRQAPGKGLEWVSAISWNGGSTYYAESMKGRFTISRDNAKNTLYLQMNSLKPEDTAVYYC"
rows = imgt_number_anarcii(seq)

# rows: [{"pos": 1, "ins_code": " ", "aa": "E", "chain_type": "H", "scheme": "imgt"}, ...]
```

### 

```python
# {pos: aa}
pos_map = build_pos_to_aa_map(rows)

# 
aa_37 = pos_map.get(37)  # 37
aa_44 = pos_map.get(44)  # 44
aa_45 = pos_map.get(45)  # 45
aa_47 = pos_map.get(47)  # 47
```

### ：FR2 hallmark

```python
from core.numbering.imgt_anarcii import imgt_number_anarcii, build_pos_to_aa_map

seq = "QVQLVQPGAELRKPGALLKVSCKASGYTFTSYYIDWVRQAPGQGLGWVGRIDPEDGGTNYAQKFQGRVTLTADTSTSTAYVELSSLRSEDTAVCYCVR"

# IMGT
rows = imgt_number_anarcii(seq)

# 
pos_map = build_pos_to_aa_map(rows)

# FR2 hallmark
hallmark_positions = [37, 44, 45, 47]
hallmarks = {pos: pos_map.get(pos, "-") for pos in hallmark_positions}

print(f"37: {hallmarks[37]}")
print(f"44: {hallmarks[44]}")
print(f"45: {hallmarks[45]}")
print(f"47: {hallmarks[47]}")
```

## API

### `imgt_number_anarcii(seq: str) -> List[Dict[str, Any]]`

IMGT。

****:
- `seq`: 

****:
- ，：
  - `pos`: IMGT（int）
  - `ins_code`: （str），' '
  - `aa`: （str）
  - `chain_type`: （str），'H'、'L'、'K'
  - `scheme`: （str），'imgt'

****:
- `IMGTNumberingError`: 
- `ImportError`: anarcii

### `build_pos_to_aa_map(rows: List[Dict[str, Any]]) -> Dict[int, str]`

。

****:
- `rows`: `imgt_number_anarcii`

****:
- ，`{pos: aa}`

## 

- ✅ ****: ANARCIIAPI
- ✅ ****: 
- ✅ ****: ，
- ✅ ****: 
- ✅ ****: IMGT

## 

- `anarcii >= 2.0.0`
- `torch` (PyTorch)
- `numpy`
- `gemmi`

## 

1. ANARCII，
2. ，
3. （、）
4. Gap（'-'）


















