# fc_database

## 
2024

## 
- ****:  (human)、 (mouse)、 (dog)
- ****: IGHG、IGKC（κ）、IGLC（λ）

## 

### 1. IGHG

####  (Human)
- ****: 426IGHG
- **IgG**: IgG1, IgG2, IgG3, IgG4
- ****: ✓ 
  - CH2: 110aa（IgG1-3） 109aa（IgG2）
  - CH3: 107aa
  - C: 44aa（27aaC）
- **UniProt**:
  - ✓ C（44aa）UniProt Fc（108-151）
  - ⚠️ UniProtFc：
    - UniProt Fc: CH2（`KAKG`），CH3C，179-226aa
    - fc_database: CH2 + CH3 + C，260-261aa
  - ****: fc_database****，Fc

####  (Mouse)
- ****: 98IGHG
- **IgG**: IgG1, IgG2a, IgG2b, IgG3
- ****: ✓ 
  - CH2: 107-110aa
  - CH3: 107-109aa
  - C: 44aa
- **UniProt**:
  - ⚠️ UniProtIgG1IgG3Fc
  - ⚠️ UniProt Fc（104-178aa），Fc
  - ****: fc_database****，IgG

####  (Dog)
- ****: 22IGHG
- **IgG**: IgG1, IgG2, IgG3, IgG4
- ****: ✓ 
  - CH2: 110aa
  - CH3: 109-110aa
  - C: 0-44aa（IgG）
- **UniProt**:
  - ⚠️ UniProt1IgGFc
  - ****: fc_database****，4IgG

### 2. IGKC（κ）

####  (Human)
- ****: 5
- ****: 107aa
- ****: ✓ 
- ****: ✓ ****

####  (Mouse)
- ****: 3
- ****: 107-111aa
- ****: ✓ 
- ****: ✓ ****

####  (Dog)
- ****: 2
- ****: 110aa
- ****: ✓ 
- ****: ✓ ****

### 3. IGLC（λ）

####  (Human)
- ****: 4
- ****: 12-106aa（106aa，112aa）
- ****: ✓ 
- ****: ✓ ****

####  (Mouse)
- ****: 2
- ****: 105-106aa
- ****: ✓ 
- ****: ✓ ****

####  (Dog)
- ****: 1
- ****: 106aa
- ****: ✓ 
- ****: ✓ ****

## 

### ✅ 
- **IGHG**: IGHGCH2、CH3C
- **IGKC**: κ
- **IGLC**: λ

### ✅ 
- ****: 
- ****: 
- ****: 

### ⚠️ UniProt
1. **Fc**:
   - UniProtFc，CH2、CH3C
   - fc_databaseCH2、CH3C，
   - ****，

2. **IgG**:
   - fc_databaseIgG（IgG2a、IgG2b，IgG1-4）
   - UniProtIgG

### 📊 

|  | IGHG | IGKC | IGLC |  |
|------|-----------|-----------|-----------|------|
|  | 426 | 5 | 4 | ✅  |
|  | 98 | 3 | 2 | ✅  |
|  | 22 | 2 | 1 | ✅  |

## 

1. **fc_database**
2. UniProtFc，Fc
3. fc_databaseIgG，

## 

：
- `scripts/validate_fc_database.py` - 
- `scripts/validate_fc_database_detailed.py` - 

：
- `validation_report_detailed.json` - JSON


















