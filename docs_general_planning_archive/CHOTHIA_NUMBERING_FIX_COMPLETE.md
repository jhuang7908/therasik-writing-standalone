# 

## 

****: 2026-03-27  
****: AbEngineCore v4.5.1   
****: ✅ ****

---

## 

### ✅ 1.  Chothia CDR ranges
- ****: `core/humanization/kabat_utils.py` ( 161-177 )
- ****:
  - `CDR_RANGES_VH_CHOTHIA = [(26, 32), (52, 56), (95, 102)]`
  - `CDR_RANGES_VL_CHOTHIA = [(26, 32), (50, 56), (89, 97)]`
  -  IMGT ranges 
- ****: ✓ 

### ✅ 2.  Kabat ↔ Chothia 
- ****: `core/humanization/kabat_utils.py` ( 188-232 )
- ****:
  - `KABAT_TO_CHOTHIA_VH/VL`: 
  - `CHOTHIA_TO_KABAT_VH/VL`: 
  - `kabat_to_chothia`: 
  - `chothia_to_kabat`: 
- ****: ✓ ，

### ✅ 3.  Kabat ↔ IMGT CDR range 
- ****: `core/humanization/kabat_utils.py` ( 234-248 )
- ****:
  - `get_cdr_ranges(scheme, chain)`: ， "kabat", "chothia", "imgt"
  -  ("VH"  "VL")
- ****: ✓  ranges

### ✅ 4.  cdr_span 
- ****: `core/humanization/kabat_utils.py` ( 369-397 )
- ****:  `scheme: str = "kabat"` 
- ****: `get_cdr_by_scheme`  ( 400-416 )
- ****:  Kabat， Chothia
- ****: ✓ 

### ✅ 5.  engine.py 
- ****: `core/humanization/engine.py`
- ****:
  
  **** :
  ```python
  "cdr_identification": "IMGT+Kabat+Chothia Union applied",
  "union_ranges_vh": {"CDR1": [26,38], "CDR2": [55,65], "CDR3": [105,117]},
  ```
  
  **** :
  ```python
  "cdr_identification": "Chothia structural definition (v4.5.1+); Kabat ranges used internally",
  "cdr_definition_scheme": "Chothia (HDX-derived, structural)",
  "back_mutation_framework": "CDR preservation: Chothia strict. Back-mutations: Chothia-FR only",
  ```

- ****:
  - Phase 1.1  (VH/VL ) -  591-595 
  - Phase 1.1   -  1313-1320 
  -  -  1-50 

- ****: ✓ 

### ✅ 6.  verify_cdr_preservation  Chothia 
- ****: `core/humanization/kabat_utils.py` ( 447-478 )
- ****:
  -  `scheme: str = "chothia"`  (v4.5.1+ )
  -  `get_cdr_ranges`  ranges
  -  Chothia  CDR

- **** (`core/humanization/engine.py`):
  - VH/VL  Phase 4.8 ( 2668, 2670 ):  `scheme="chothia"`
  -  ( 1573, 1585 ):  `scheme="chothia"`

- ****: ✓  Chothia CDR 

### ✅ 7.  is_in_cdr 
- ****: `core/humanization/kabat_utils.py` ( 323-337 )
- ****:  `scheme: str = "chothia"` ， Chothia
- ****:  CDR 
- ****: ✓  CDR 

---

## 

```
╔════════════════════════════════════════════════════════════════╗
║ Test: Chothia CDR Numbering Scheme Implementation (v4.5.1)    ║
╚════════════════════════════════════════════════════════════════╝

✓ Test 1: CDR Range Definitions
  - Kabat VH: [(26, 35), (50, 65), (95, 102)]
  - Chothia VH: [(26, 32), (52, 56), (95, 102)]
  - IMGT VH: [(27, 38), (56, 65), (104, 117)]
  ✓ All ranges correctly defined

✓ Test 2: get_cdr_ranges Function
  - Kabat VH: correct
  - Chothia VH: correct
  - IMGT VH: correct
  ✓ Multi-scheme support works

✓ Test 3: Kabat ↔ Chothia Conversion
  - Kabat 26 → Chothia 26
  - Kabat 32 → Chothia 32
  - Kabat 52 → Chothia 52
  - Kabat 56 → Chothia 56
  - Kabat 95 → Chothia 95
  ✓ All mappings functional

✓ Test 4: Chothia CDR Preservation Enforcement
  - Successfully numbered mouse VH (83 positions)
  - Chothia CDR verification: 0 errors
  ✓ Verification works correctly

════════════════════════════════════════════════════════════════
✓ ALL TESTS PASSED (4/4)
════════════════════════════════════════════════════════════════
```

---

## 

### ❓ Q1: CDR  Chothia ？

✅ ****。：
-  Chothia CDR ranges (VH: 26-32, 52-56, 95-102)
- `verify_cdr_preservation`  Chothia (v4.5.1+)
-  100%  CDR 
- 

---

### ❓ Q2: Vernier zone  Kabat ？

✅ **，**。：
- Vernier zone  Kabat 
- `VERNIER_KABAT_TO_IMGT_VH/VL` 
- Vernier  back-mutations， Chothia-FR 
-  Vernier  CDR 

---

### ❓ Q3: Anarcii  IMGT ？

✅ **， Kabat **。：
- `engine.py`  `anarcii.to_scheme("kabat")`  Kabat
-  Kabat 
- IMGT  Vernier zone 
- 

---

### ❓ Q4: ？

✅ **。**：

|  |  |  |
|-----|------|------|
| `get_cdr_ranges(scheme, chain)` | kabat_utils.py:234 |  CDR ranges |
| `kabat_to_chothia(pos, chain)` | kabat_utils.py:215 | Kabat  → Chothia |
| `chothia_to_kabat(pos, chain)` | kabat_utils.py:220 | Chothia  → Kabat |
| `get_cdr_by_scheme(...)` | kabat_utils.py:400 |  CDR |
| `is_in_cdr(pos, chain, scheme)` | kabat_utils.py:323 |  CDR  |
| `verify_cdr_preservation(..., scheme)` | kabat_utils.py:447 |  CDR  |

、、。

---

## 

### 

```
┌─────────────────────────────────────────────────────┐
│  (QA /  / )                           │
│  └─→  Chothia                          │
│      100%  CDR                             │
│      Back-mutations  Chothia-FR                 │
└─────────────────────────────────────────────────────┘
           ↓  (get_cdr_ranges, convert)
┌─────────────────────────────────────────────────────┐
│  (KabatDict)                               │
│  └─→  Kabat (pos, ins_code)        │
│       (52A, 82B )                     │
│      ，                         │
└─────────────────────────────────────────────────────┘
           ↓  (Anarcii)
┌─────────────────────────────────────────────────────┐
│                                   │
│  1. Kabat: 26-35, 50-65, 95-102         │
│  2. Chothia: 26-32, 52-56, 95-102       │
│  3. IMGT: 27-38, 56-65, 104-117        │
└─────────────────────────────────────────────────────┘
```

---

## 

|  |  |  |  |
|-----|-------|-------|------|
| **CDR ** |  Kabat | Kabat+Chothia+IMGT | ✓  |
| **Chothia ranges** |  |  | ✓  |
| **Kabat ↔ Chothia** |  |  | ✓  |
| **verify_cdr_preservation** | Kabat only |  | ✓  |
| **** |  |  | ✓  |
| **Back-mutation ** |  | Chothia-FR  | ✓  |
| **** |  |  | ✓  |

---

## 

### 

|  |  |  |
|-----|--------|------|
| `core/humanization/kabat_utils.py` | 161-478 | ：Chothia ranges, ,  |
| `core/humanization/engine.py` | 1-50, 591-595, 1313-1320, 1573, 1585, 2668, 2670 | , , verify_cdr  |

### 

|  |  |
|-----|------|
| `scripts/_test_chothia_numbering.py` | ： Chothia  |

### 

|  |  |
|-----|------|
| `projects/mumab4d5_spliced_Redesign/NUMBERING_SCHEME_FIX_v451_SUMMARY.md` | ： |

---

## 

✅ ****

，：

```python
# 
errors = verify_cdr_preservation(humanized_kd, mouse_kd, "VH")

# （， Chothia）
errors = verify_cdr_preservation(humanized_kd, mouse_kd, "VH", scheme="chothia")

# ： Kabat
errors = verify_cdr_preservation(humanized_kd, mouse_kd, "VH", scheme="kabat")
```

---

## 

1. **🔄 **
   - `docs/VH_VL_HUMANIZATION_STANDARD_V4.5.md`:  CDR 
   - `docs/ABENGINECORE_GOVERNANCE.md`:  v4.5.1 

2. **📋 **
   - `config/vh_vl_humanization_v44.json` → `v45.json`
   -  "cdr_scheme": "chothia"

3. **🧪 **
   -  muMAb4D5  Phase 4.8 
   -  Chothia CDR 

4. **📊 **
   -  muMAb4D5 
   - 

---

##  - ✅ 

- ✅ CDR  Chothia 
- ✅  (Kabat, Chothia, IMGT) 
- ✅ 
- ✅ verify_cdr_preservation  Chothia 
- ✅ ，
- ✅ 
- ✅ 
- ✅ 

---

****: 2026-03-27  
****: AbEngineCore v4.5.1  
****: ✅ 
