# Numbering Engine Migration to ANARCII

## 

### 1.  `core/numbering/dual_map.py`

****：
- ✅  `anarci` ( i)  `anarcii` ( i)
- ✅  `Anarcii`  `run_anarci` 
- ✅  ANARCII 
- ✅  `anarcii_obj.number(seq)`  IMGT 
- ✅  `anarcii_obj.to_scheme('kabat')`  Kabat 
- ✅ 

**API **：
```python
#  (anarci)
from anarci import run_anarci
res_imgt = run_anarci([("query", seq)], scheme="imgt")
res_kabat = run_anarci([("query", seq)], scheme="kabat")

#  (anarcii)
from anarcii import Anarcii
anarcii_obj = Anarcii(seq_type="antibody", mode="accuracy", ...)
result_imgt = anarcii_obj.number(seq)
result_kabat = anarcii_obj.to_scheme('kabat')
```

### 2.  `tools/validate_dual_map_consistency.py`

****：
- ✅ `get_numbering_engine_info`  `anarcii` 
- ✅  anarcii （ 2.0.3）

### 3.  `tools/analyze_functional_sites_mapping.py`

****：
- ✅ ， "ANARCI"  "ANARCII"
- ✅ `numbering_engine`  `anarcii` 

### 4. 

****：
- ✅ `tests/test_dual_map_conflict_insertion.py`  mock  anarcii API
- ✅ 

## 

### ✅ 

1. **ANARCII **：
   ```python
   from tools.validate_dual_map_consistency import get_numbering_engine_info
   info = get_numbering_engine_info
   # : {'name': 'anarcii', 'version': '2.0.3', ...}
   ```

2. ****：
   ```python
   from core.numbering.dual_map import build_dual_map
   dual_map, status, chain_type = build_dual_map(sequence)
   # ， anarcii 2.0.3
   ```

3. ****：
   ```bash
   python tools/validate_dual_map_consistency.py \
     --seq_fasta data/benchmarks/fasta/6jbt_mouse_vh.fasta \
     --out reports/mapping/6jbt_mouse_vh_dual_map_report_anarcii.json
   # ， numbering_engine: {name: "anarcii", version: "2.0.3"}
   ```

### ✅ 

- `test_numbering_engine_info_in_reports` - 
- `test_dual_map_status_classification` - 
- `test_functional_sites_schema` - （14 ）

## 

### 1.  ANARCII 

****： `_anarcii_obj` 

****：
- ANARCII 
-  `build_dual_map` 
- 

### 2. API 

****： `build_dual_map` 

****：
- 
- 
-  anarci  anarcii

### 3. 

****：

****：
-  "ANARCI is not available"  "ANARCII is not available"
-  "pip install anarci"  "pip install anarcii"

## 

- ✅ `core/numbering/dual_map.py` - （ anarcii）
- ✅ `tools/validate_dual_map_consistency.py` - （ anarcii ）
- ✅ `tools/analyze_functional_sites_mapping.py` - （ anarcii）
- ✅ `tools/generate_functional_sites_mapping_report.py` - （ numbering_engine）
- ✅ `tests/test_dual_map_conflict_insertion.py` - （mock anarcii）

## 

✅ ** ANARCII**：
- `core/numbering/dual_map.py`  `anarcii.Anarcii`
- `get_numbering_engine_info`  anarcii  2.0.3
-  `numbering_engine: {name: "anarcii", version: "2.0.3"}`

✅ ****：
- VH ：，dual_map_status: "partial"
- VL kappa ：，dual_map_status: "partial"
-  numbering_engine 

## 

 anarci  anarcii。 ANARCII 2.0.3 。










