# Functional Sites VL-λ Support Update Summary

## 

### 1.  `kb/10_parameters/functional_sites.yaml`

****：
- `chain_type`: VHH|VH|VL
- `light_chain_type`: kappa|lambda|null

** VHH/VH **：
-  `chain_type: "VHH"`  `light_chain_type: null`

** VL-λ **（5）：
- `VL_LAMBDA_VERNIER_29_30` (role: vernier)
- `VL_LAMBDA_VERNIER_71_73` (role: vernier)
- `VL_LAMBDA_VERNIER_94_96` (role: vernier)
- `VL_LAMBDA_BOUNDARY_CDR1_START` (role: fr_cdr_boundary)
- `VL_LAMBDA_BOUNDARY_CDR2_END` (role: fr_cdr_boundary)

**VL-λ **：
- `chain_type: "VL"`
- `light_chain_type: "lambda"`
- `imgt_anchor_positions`: 
- `needs_calibration: true`
- `scope: [vl]`

### 2.  `tools/validate_functional_sites.py`

****：
-  `chain_type` （ VHH/VH/VL ）
-  `light_chain_type` （ kappa/lambda/null ）
-  `imgt_anchor_positions` （，）
-  `needs_calibration` （，）
-  VL_LAMBDA_* 
-  λ ， `skipped_reason: no_lambda_sequences_provided`

**CLI **：
- `--has_lambda_sequences`:  λ 

****：
-  `(is_valid, errors, report)`
- `report` ：
  - `vl_lambda_sites`: VL_LAMBDA_* 
  - `skipped_sites`: （ λ ）

### 3. 

**`tests/test_functional_sites_vl_lambda.py`**：
- `test_vl_lambda_sites_allowed`:  VL_LAMBDA_* 
- `test_vl_lambda_sites_skipped_without_lambda_sequences`: 
- `test_chain_type_validation`:  chain_type 
- `test_light_chain_type_validation`:  light_chain_type 
- `test_imgt_anchor_positions_validation`:  imgt_anchor_positions 
- `test_needs_calibration_validation`:  needs_calibration 

### 4. 

**`tests/test_functional_sites_schema.py`**：
-  `(is_valid, errors, report)`

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
$ pytest tests/test_functional_sites_schema.py tests/test_functional_sites_vl_lambda.py -v
15 passed in 0.61s
```

## 

### VL-λ 

 λ ：
- VL_LAMBDA_* ****
-  `skipped_reason: no_lambda_sequences_provided`
- ** mapping_status **

### 

- `chain_type`:  "VHH", "VH",  "VL"
- `light_chain_type`:  "kappa", "lambda",  `null`
- `imgt_anchor_positions`: ，（ 1-150）
- `needs_calibration`: ，

### 

- VL-λ ：`VL_LAMBDA_*` 
- ：（ `HALLMARK_VHH_37_39`, `VERNIER_29_30`）

## 

- `kb/10_parameters/functional_sites.yaml` - （ chain_type, light_chain_type, VL-λ ）
- `tools/validate_functional_sites.py` - 
- `tests/test_functional_sites_schema.py` - 
- `tests/test_functional_sites_vl_lambda.py` - （VL-λ ）

## 

 λ ：
1.  `python tools/validate_functional_sites.py --has_lambda_sequences`
2. VL_LAMBDA_* 
3.  mapping_status 

## 

- VL-λ ****， `needs_calibration: true`
-  λ 
-  VHH MVP， VL-λ 
