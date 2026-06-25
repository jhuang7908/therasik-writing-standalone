# VL-λ Functional Sites Integration Summary

## 

### 1.  `kb/10_parameters/functional_sites.yaml`

****：
- `chain_type`: VHH | VH | VL（，）
- `light_chain_type`: kappa | lambda | null（，）

** VHH/VH **：
-  `chain_type` （VHH  VH）
-  `light_chain_type`  `null`

** VL-λ **：
- 5  VL-λ ， `VL_LAMBDA_` 
- ：`vernier`  `fr_cdr_boundary`
-  VL-λ ：
  - `chain_type: "VL"`
  - `light_chain_type: "lambda"`
  - `needs_calibration: true`（，）
  - `imgt_anchor_positions`

**VL-λ **：
1. `VL_LAMBDA_VERNIER_29_30` - Vernier zone (positions 29-30)
2. `VL_LAMBDA_VERNIER_71_73` - Vernier zone (positions 71-73)
3. `VL_LAMBDA_VERNIER_94_96` - Vernier zone (positions 94-96)
4. `VL_LAMBDA_BOUNDARY_CDR1_START` - FR1/CDR1 boundary (positions 26-28)
5. `VL_LAMBDA_BOUNDARY_CDR2_END` - CDR2/FR3 boundary (positions 55-57)

### 2.  `tools/validate_functional_sites.py`

****：
- ✅  `chain_type` （ VHH、VH  VL）
- ✅  `light_chain_type` （ kappa、lambda  null）
- ✅ ：`VL_LAMBDA_*` ：
  - `chain_type == "VL"`
  - `light_chain_type == "lambda"`
- ✅  `VL_LAMBDA_*` 
- ✅  λ ， `skipped_reason: "no_lambda_sequences_provided"`

**CLI **：
- `--has_lambda_sequences`:  λ 

### 3.  `tools/analyze_functional_sites_mapping.py`

****：
- ， `VL_LAMBDA_*` （ `chain_type != 'VL'`  `light_chain_type != 'lambda'`）
-  `VL_LAMBDA_*`  `mapping_status` （ λ ）
-  `VL_LAMBDA_*` 

****：
- `skipped_lambda_sites`:  `VL_LAMBDA_*` ，：
  - `site_id`
  - `skipped_reason: "no_lambda_sequences_provided"`
  - `note`: 

### 4.  `tests/test_functional_sites_schema.py`

****：
- `test_vl_lambda_sites_with_lambda_sequences`:  λ ，`VL_LAMBDA_*` 
- `test_chain_type_validation`:  `chain_type` 
- `test_vl_lambda_site_requirements`:  `VL_LAMBDA_*` 
- `test_light_chain_type_validation`:  `light_chain_type` 

****：
- `test_valid_functional_sites`:  `VL_LAMBDA_*` 

## 

### ✅ 

```bash
$ python tools/validate_functional_sites.py
✅ All validations passed!
📋 VL-λ sites found: 5
⚠️  Skipped sites (no λ sequences provided): 5
```

### ✅ 

```bash
$ pytest -q tests/test_functional_sites_schema.py
13 passed in 0.48s
```

### ✅ 

- `chain_type` ： VHH、VH  VL
- `light_chain_type` ： kappa、lambda  null
- `VL_LAMBDA_*` ： `chain_type="VL"`  `light_chain_type="lambda"`

## 

### 1. VL-λ 

****： `VL_LAMBDA_*`  KB ， λ 

****：
-  VHH MVP 
-  VL-λ 
-  `needs_calibration: true` 

### 2. 

****：
-  `chain_type != 'VL'` →  `VL_LAMBDA_*` 
-  `light_chain_type != 'lambda'` →  `VL_LAMBDA_*` 
-  `mapping_status` 
- 

### 3. 

- `chain_type`  `light_chain_type` 
-  VHH/VH 
- （ `VL_LAMBDA_*` ）

## 

- ✅ `kb/10_parameters/functional_sites.yaml` - 
- ✅ `tools/validate_functional_sites.py` - 
- ✅ `tools/analyze_functional_sites_mapping.py` - 
- ✅ `tests/test_functional_sites_schema.py` - 

## 

 VL-λ ：
1.  `python tools/analyze_functional_sites_mapping.py --seq <lambda_sequence>`
2. `VL_LAMBDA_*` 
3.  `imgt_anchor_positions`
4.  `needs_calibration: true`  `false`

## 

✅ ****：
- ✅ `python tools/validate_functional_sites.py` 
- ✅ `pytest -q` （13 ）
- ✅ `VL_LAMBDA_*` （ λ ）
- ✅ 

VL-λ  KB， VHH MVP 。










