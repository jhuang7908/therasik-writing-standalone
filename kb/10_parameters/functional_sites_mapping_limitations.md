# Functional Sites Mapping 

## ：ANARCI 

### 

**， ANARCI ，。**

### 

1. ****：`core/numbering/dual_map.py`  `build_dual_map` **** ANARCI （IMGT + Kabat） residue 。

2. ****：`resolve_functional_sites_on_sequence`  `dual_map` ， `dual_map`  ANARCI 。

3. ****：
   -  ANARCI  → `DualMapError` → `dual_map_status: "failed"`
   -  ANARCI  → `DualMapError` → `dual_map_status: "failed"`
   -  `dual_map_status == "failed"` → 

### 

```python
# core/numbering/dual_map.py
def build_dual_map(sequence: str) -> Tuple[List[Dict[str, Any]], str]:
    if not HAS_ANARCI:
        raise DualMapError("ANARCI is not available. Install with: pip install anarci")
    
    #  ANARCI 
    res_imgt = run_anarci([("query", seq_clean)], scheme="imgt")
    res_kabat = run_anarci([("query", seq_clean)], scheme="kabat")
    
    #  ANARCI  dual_map
    # ...
```

```python
# tools/analyze_functional_sites_mapping.py
def analyze_functional_sites_mapping(sites_file: Path, sequence: str) -> Dict:
    try:
        dual_map, dual_map_status = build_dual_map(sequence)
    except DualMapError as e:
        return {
            "error": str(e),
            "dual_map_status": "failed",  # ← 
            "scheme_source": "anarci"
        }
    
    #  dual_map，
    resolved_sites, conflicts = resolve_functional_sites_on_sequence(dual_map, functional_sites)
```

## 

### 

1. **ANARCI **：`pip install anarci` 
2. **ANARCI **： ANARCI /VHH
3. **/**：ANARCI  HMM 

### 

- `dual_map_status: "failed"`
- `resolved_sites: {}`
- `conflicts: []`
-  0 

##  YAML ？

### 

""（ YAML  `imgt_positions`  `kabat_positions` ）****，：

1. **YAML **：
2. **/**： IMGT  Kabat 
3. ****："IMGT 37  gap， Kabat 37 "

### 

：
- ✅ **** ANARCI
- ✅  ANARCI  `dual_map`
- ✅  `dual_map` 
- ✅ （gap、）

## 

###  1： ANARCI 

```bash
#  ANARCI
pip install anarci

# 
python -c "from anarci import run_anarci; print('ANARCI OK')"
```

###  2： Fallback 

 fallback，****，：

1. ****： fallback 
2. ****： IMGT/Kabat 
3. ****：

 fallback，：

```python
def build_dual_map_with_fallback(sequence: str) -> Tuple[List[Dict[str, Any]], str]:
    try:
        return build_dual_map(sequence)
    except DualMapError:
        # Fallback: ，
        return [], "failed"
        # ： YAML （，）
```

###  3：

：

```python
# tools/analyze_functional_sites_mapping.py
try:
    dual_map, dual_map_status = build_dual_map(sequence)
except DualMapError as e:
    return {
        "error": str(e),
        "dual_map_status": "failed",
        "scheme_source": "anarci"
    }
```

****：， ANARCI 。

## 

，：

- [ ] ANARCI ：`pip install anarci`
- [ ] ANARCI ：`python -c "from anarci import run_anarci"`
- [ ] /VHH 
- [ ] （ > 50 ）

## 

****：， ANARCI ，。

****：
1.  `dual_map`
2. `dual_map`  ANARCI 
3.  `dual_map`，

****：
- ✅  ANARCI 
- ✅ 
- ✅  `dual_map_status`  "failed"
- ❌  YAML 










