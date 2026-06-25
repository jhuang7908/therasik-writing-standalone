# 

（Ig），：
- **IGHC**: （CH1、Hinge、CH2、CH3、C）
- **IGKC**: κ
- **IGLC**: λ

## 

```
fc_aa/
├── human/
│   ├── IGHC_human.fasta    # （，）
│   ├── IGKC_human.fasta    # κ
│   └── IGLC_human.fasta    # λ
├── mouse/
│   ├── IGHC_mouse.fasta
│   ├── IGKC_mouse.fasta
│   └── IGLC_mouse.fasta
├── dog/
│   ├── IGHC_dog.fasta
│   ├── IGKC_dog.fasta
│   └── IGLC_dog.fasta
└── cat/
    └── IGKC_cat.fasta      # ✅  (IGHCIGLC，)
```

## 

### IMGT
- ****
- IMGT（V、D、J）
- 

### 
1. **、、**: IMGT（CH1、Hinge、CH2、CH3、C）
2. ****: 
   - IGKC: （107aa）
   - IGHCIGLC: ，NCBI

## 

### ✅ 

|  | IGHC | IGKC | IGLC |
|------|------|------|------|
| **** | ✅  (422) | ✅  (5) | ✅  (3) |
| **** | ✅  (98) | ✅  (3) | ✅  (2) |
| **** | ✅  (22)* | ✅  (2) | ✅  (1) |
| **** | ❌  | ✅  (1) | ❌  |

### IGHC

IGHC：

1. **CH1** (~98aa): 1
2. **Hinge Region** (~12-19aa): ，
3. **CH2** (~110aa): 2
4. **CH3** (~107aa): 3
5. **C** (~44-71aa): C

### IGKCIGLC

- **IGKC**: κ，107-111aa
- **IGLC**: λ，105-106aa

## 

FASTA：

```
>ID_
（80）
```

### ：IGHC

```
>Human_IGHG1_CH1_IGHG1*01_98aa
ASTKGPSVFPLAPSSKSTSGGTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSS
GLYSLSSVVTVPSSSLGTQTYICNVNHKPSNTKVDKKV
>Human_IGHG1_Unknown_IGHG1*01_15aa
EPKSCDKTHTCPPCP
...
```

## 

：

```bash
python scripts/validate_constant_regions.py
```

：
- IGHC、IGKC、IGLC
- IGHC（CH1、Hinge、CH2、CH3、C）
- ：`constant_regions_validation.json`

## 

1. ****（、、）：
2. **IGKC**：，
3. **IGHCIGLC**：：
   - NCBI Gene
   - 
   - 

## 

1. ****，DNA
2. **IGHC**（CH1 + Hinge + CH2 + CH3 + C）
3. **IGKCIGLC**
4. 

## ✅ 

（2024）。

### 

1. ****（5）：
   - IGHG3*02CH1、CH2、CH3（11-17aa）
   - IGHGP*02CH3（26aa）
   - IGLC*04（12aa）

2. ****（2）：
   - IGHC_cat.fasta
   - IGLC_cat.fasta

### 

- ✅ ****
- ✅ ****
- ⚠️ **IGHCIGLC**：，

：`removal_log.json`

### IGHC

*IGHC（CH1+Hinge+CH2+CH3），IgGC：
- **IgG2**：C（44aa+27aa）
- **IgG1、IgG3、IgG4**：CH3（109-110aa，），C

，：`DOG_IGHC_EXPLANATION.md`

## 

- 2024: ，、、
- 2024: IGKC
- : IGHCIGLC
