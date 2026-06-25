# Functional Sites Mapping Implementation Summary

## 

### 1. 

****: `core/numbering/dual_map.py`

****:
- `build_dual_map(sequence)`:  ANARCI （scheme=imgt  scheme=kabat）， residue 
- `resolve_functional_sites_on_sequence(dual_map, functional_sites)`:  dual_map 

****:
```python
dual_map = [
    {
        "seq_idx": 0,  # 0-based index
        "aa": "E",
        "imgt_pos": "1",  #  "37A"  None
        "kabat_pos": "1",  #  "52A"  None
        "flags": ["imgt_gap", "kabat_insertion", ...]
    },
    ...
]

status = "full" | "partial" | "conflict" | "failed"
```

### 2. 

****: `tools/analyze_functional_sites_mapping.py`

****:
- ❌ ""（ YAML  imgt_positions  kabat_positions ）
- ✅  →  ANARCI  →  → 
- ✅  CLI ：`--seq`  `--seq_fasta`
- ✅  `scheme_source: "anarci"`  `dual_map_status`（full/partial/conflict/failed）

### 3. 

****: `tests/test_dual_map_conflict_insertion.py`

****:
- `test_dual_map_with_insertion_conflict`: （ monkeypatch  ANARCI ）
- `test_functional_sites_conflict_detection`: 
- `test_dual_map_status_classification`: 
- `test_resolve_sites_with_real_sequence`: 

### 4. 

****: `tools/generate_functional_sites_mapping_report.py`

****:
-  YAML 
-  `sequence_id`, `sequence_hash`, `scheme_source`, `dual_map_status`
-  `resolved_sites`  `conflicts`

## 

### Dual Map Status 

- **full**: （>70%）
- **partial**: / None（30-70%）
- **conflict**: " gap/None，"
- **failed**: IMGT  >50% 

### Conflict 

：
- `site_id`:  ID
- `missing_scheme`: "imgt"  "kabat"
- `missing_pos`: 
- `present_scheme`: 
- `present_pos`: 
- `description`: 

### 

1.  `imgt_positions`  `dual_map`  residue
2.  `dual_map`  `kabat_pos`
3.  `mapping_status`:
   - **full**:  IMGT  residue， kabat_pos
   - **partial**: IMGT  residue， kabat_pos 
   - **conflict**:  IMGT  gap/None， Kabat 

## 

### 

```bash
# 
python tools/analyze_functional_sites_mapping.py --seq "EVQLVESGGGLVQPGGSLRLSCAAS..."

#  FASTA 
python tools/analyze_functional_sites_mapping.py --seq_fasta path/to/sequence.fasta

# 
python tools/generate_functional_sites_mapping_report.py --seq "..." --output report.yaml
```

### 

```
================================================================================
Functional Sites Mapping Analysis (Sequence-based)
================================================================================

Sequence ID: seq_a1b2c3d4e5f6
Sequence hash: a1b2c3d4e5f6...
Scheme source: anarci
Sequence length: 118

📊 Dual Map Status (IMGT ↔ Kabat):
--------------------------------------------------------------------------------
Status: CONFLICT
Total sequence positions: 118
Positions with both IMGT and Kabat: 110 (93.2%)
IMGT gaps: 2
Kabat gaps: 6
Insertions detected: 1

🏷️  Hallmark Sites Mapping Statistics:
--------------------------------------------------------------------------------
Total hallmark sites: 3
Full matches: 2
Partial matches: 1
Conflicts: 0
...

⚠️  Conflict Examples:
--------------------------------------------------------------------------------
Conflict #1:
  Site ID: HALLMARK_VHH_37_39
  Missing scheme: imgt
  Missing position: 37
  Present scheme: kabat
  Present position: 37
  Description: IMGT position 37 is gap/None but exists in Kabat
```

## 

### ✅ 

1. ✅ ""
2. ✅ （`core/numbering/dual_map.py`）
3. ✅  ANARCI 
4. ✅ （ dual_map）
5. ✅ 
6. ✅ （ sequence_id, scheme_source, dual_map_status）

### ⚠️ （ ANARCI ）

1. ⚠️ `python tools/analyze_functional_sites_mapping.py --seq_fasta <one_vhh.fasta>` -  ANARCI
2. ⚠️  `scheme_source: anarci` - 
3. ⚠️ `dual_map_status != "CONSISTENT"` -  full/partial/conflict/failed
4. ⚠️  conflicts - ， ANARCI 

## 

1. **ANARCI **:  `pip install anarci` 
2. ****: ANARCI  numbering ， AA 
3. ****:  Kabat （ 52A）， `[A-Z]$` 
4. ****:  IMGT  dual_map  None， Kabat ， conflict

## 

- `core/numbering/dual_map.py` - 
- `tools/analyze_functional_sites_mapping.py` - 
- `tools/generate_functional_sites_mapping_report.py` - 
- `tests/test_dual_map_conflict_insertion.py` - 
- `kb/10_parameters/functional_sites.yaml` - 
- `kb/10_parameters/functional_sites_mapping_report.yaml` - 










