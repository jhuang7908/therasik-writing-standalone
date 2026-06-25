# 

## 1. 

### 1.1 （Anchor Scheme）

- ****: IMGT
- ****:  IMGT （primary anchor）
- **Kabat **:  `dual_map` ，

### 1.2 

- IMGT  Kabat 
- 
-  Kabat ，：
  -  IMGT→Kabat 
  - /，
  - ""（false conflicts）

## 2. 

### 2.1 

：

- `site_id`: 
- `role`: （hallmark, vernier, fr_cdr_boundary, anchor ）
- `imgt_positions`: IMGT 
- `anchor_scheme`: （ "imgt"）
- `chain_scope`: （ [vh, vhh]  [vl_lambda]）

### 2.2 

****：

- `kabat_positions`:  Kabat 
- `kabat_range`:  Kabat 
-  `kabat_*` 

### 2.3 

- `chain_scope` 
- ：`chain_scope: [vh, vhh]`  Heavy （VH  VHH）
- ：`chain_scope: [vl_lambda]`  Lambda 

## 3. 

### 3.1 IMGT 

：

1. ** IMGT **:  `imgt_positions`  `dual_map` 
2. ** Kabat **:  `kabat_pos`， `resolved_kabat_positions`
3. ** Kabat**:  `kabat_positions`

### 3.2 

（`mapping_status`）""：

- **full**:  IMGT anchor positions ， residue  kabat_pos，
- **scheme_shift**:  IMGT anchor positions ， IMGT  Kabat （ 37→32）
- **partial**:  IMGT anchor positions
- **conflict**:  IMGT anchor position  Kabat positions，

### 3.3 

- `resolved_residues`  residue  `imgt_pos`  `site.imgt_positions`
- `resolved_residues`  residue  `kabat_pos`  `resolved_kabat_positions`（ dual_map ）
- """""" residues

## 4. （Invariants）

### 4.1 Schema 

-  `kabat_*` 
-  `anchor_scheme: "imgt"`
-  `chain_scope` 

### 4.2 

- `resolved_residues`  IMGT  `imgt_positions` 
- `resolved_kabat_positions`  `resolved_residues` ，
- ：H （chain_type="H"） `chain_scope`  `[vl_lambda]` 

## 5. 

### 5.1 

- ****:  `imgt_positions`、`notes`、`chain_scope` 
- ****: 、（ governance ）
- ****:  `kabat_*` 

### 5.2 

：

-  governance 
-  `functional_sites.yaml`  `governance.change_log`
- 

## 8. Variable Domain Trimming (Mandatory)

### 8.1 

- ****（CH1 / CL）
- ****（Variable Domain），
- ****

### 8.2 

，：

- ****（detection method）：
- **/**（start/end indices）：
- ****（whether constant regions were removed）：

### 8.3 

 JSON  `variable_domain` ，：

```json
{
  "variable_domain": {
    "detected": true,
    "trimmed_constant_region": true,
    "original_length": 223,
    "variable_domain_length": 125,
    "start_index": 0,
    "end_index": 125,
    "detection_method": "anarcii_auto_trim"
  }
}
```

### 8.4 

- **IMGT **:  IMGT  128
- ****: ， `dual_map`  `imgt_numbering` / `kabat_numbering` 
- ****: 

### 8.5 

- 
- 
- ，`trimmed_constant_region`  `false`

---

****: 1.1  
****: 2025-12-14  
****: 2025-12-14  
****: antibody_engineering  
****: computational_structures








