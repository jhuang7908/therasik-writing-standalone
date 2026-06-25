# Llamanade 

## 1. ：

### 1.1 ：CDR 

 **AbM  + Martin ** CDR ：

| CDR | Martin  |  |
|-----|-------------|------|
| CDR1 | 26–36 | AbM ， VHH  loop |
| CDR2 | 50–59 | AbM  |
| CDR3 | 95–103 | AbM ；VHH  CDR3  Kabat （100A/100B…）， |

**， human frequency 。**

---

### 1.2 ：（ Fig 3–4 ）

（190  VHH PDB + 621  human IgG），：

#### (a) FR2:FR4 

```
FR2 Pos 37 (F/Y) : W103 (FR4)  → π-π ， 4.1 Å /  31°
FR2 Pos 45 (R)   : W103 (FR4)  → cation-π ， 3.9 Å /  65.7°
```

 human IgG  **L45:W103 ** ， VHH  R45 ****，paper "****"。

#### (b) FR2:CDR3 

```
FR2 Pos 37 (F/Y) : CDR3 → （CDR3 > 15aa  > 80% ）
FR2 Pos 47 (F/L) : CDR3 → CDR3  helix 
```

 CDR3  CDR3 。** Figure 4D**  CDR3  37/47  CDR3 。

#### (c) CDR3 

```
~10%  VHH  CDR3  CDR1/CDR2 （Fig S2B）
，
```

→ ： CDR3 Cys （≥2  Cys ）

#### (d) Protinter （， absent）

 Llamanade  `protinter` ****：
- `ionic`：
- `catpi`：-π（R/K + F/W/Y/H）
- `aroaro`：-（F/W/Y ）

 FR2 37/45/47 （ 5–15%）。****—— Llamanade  FR3 。

---

### 1.3 ：

 **`ANARCI_Hum_H.json`**（ 22,450  human VH NGS ）：

```
freq = f(donor_aa, position)   #  aa  human VH 
if freq < threshold (default 0.10):
     → top-frequency human residue at this position
else:
     aa
```

**threshold = 0.10** ： aa  human VH  10% → 。

---

## 2. console VHH Demo 

### （ `alpaca-vhh` demo ：7D12 / PDB 4KRL，**124 aa**）
```
QVKLEESGGGSVQTGGSLRLTCAASGRTSRSYGMGWFRQAPGKEREFVSGISWRGDSTGYADSVKGRFTISRDNAKNTVDLQMNSLKPEDTAIYYCAAAAGSAWYGTLYEYDYWGQGTQVTVSS
```

`llamanade_alpaca_result.json`  `alpaca_vhh_console.fasta` **** `run_llamanade_seq_only.py` ；`per_position`  `mutations` （：Martin/AbM  **20** 、**38**  CDR  —  JSON ）。

### （， `llamanade_alpaca_result.json`）
|  |  |
|------|-----|
|  |  JSON `n_positions_numbered` （7D12 WT  IMGT/ 124） |
| CDR  |  JSON `n_cdr_locked`  |
|  |  JSON `n_struct_protected`  |
| **，** |  JSON `n_substituted` / `mutations`  |

### （ demo  18 ）

 **freq < 0.1** ； **`llamanade_alpaca_result.json`**  `mutations`  `per_position`，（ `…SLRLSRAL…` ， 7D12 ）。

> ****：Llamanade seq-only / Tier  **Cys / hallmark** ； AbEngineCore 。

### 18 

****：， 7D12 demo 。 JSON  `per_position`  `mutations` 。

---

## 3. 

### 3.1 ：profile  human VH 

`ANARCI_Hum_H.json`  **22,450  human VH NGS **（EMBL-Ig）。：

- "" human VH 
-  human VH ，，
- ****  profile 

### 3.2 

#### 🐇  (Rabbit)

|  |  |
|------|------|
| VH  | IGHV1 / IGHV3（ VH ，） |
| FR2 hallmarks |  VH pattern（ VHH ），37/45/47  |
| CDR3 |  CDR3（10–18 aa）， Cys pair → cdr3_cys_protect=True |
|  freq_threshold | **0.15**（ FR  FR  15–20%  FR3） |
|  | FR3 ， |
|  | ANARCI Kabat  |

****:
```bash
python run_llamanade_seq_only.py --fasta rabbit.fasta --species rabbit
```

#### 🐔  (Chicken)

|  |  |
|------|------|
| VH  | IgY  VH： VH （IGHV1 chicken）， CDR3  |
| FR  VH | FR1/FR2/FR4 ；**FR3 ** |
| CDR3 | （ 24+ aa）， Cys pair |
|  freq_threshold | **0.20**（FR ，，） |
| ANARCI  | **** — ANARCI  VH  heavy chain HMM ， MISSING_PROFILE |
|  |  FR2  residues（ Trp36 ）； STRUCT  |

****:
- ， `--extra-protect 37 45 47` 
- - FR2 hallmarks  SPECIES_NOTES["chicken"]["extra_protect_martin"]

#### 🐄  (Bovine)

|  |  |
|------|------|
| VH  |  IGHV： CDR3（knob domain，50–70 aa），β-strand stalk |
| stalk  | CDR3 stalk  10 aa， VH domain；**Kabat 93/94  stalk anchor** |
| FR  VH | FR1/FR2/FR4 ；FR3 ；stalk  |
|  freq_threshold | **0.20** |
|  | **pos 93/94（Kabat） extra-protect**， stalk  |
| ANARCI  |  CDR3  Kabat  |

****:
```bash
python run_llamanade_seq_only.py --fasta bovine.fasta --species bovine
# --extra-protect 93 94  species="bovine" 
```

#### 🦈  IgNAR (VNAR) — 

VNAR（Variable domain of New Antigen Receptor）（、）IgNAR ， 12 kDa，， VHH 。

**VNAR **

|  |  | （Kabat） |  |
|------|-----------|--------------|---------|
| Type I | （ canonical C22-C92）| C22, C92 | `protect_all_fr_cys=True` → STRUCT_PROTECT |
| Type II | CDR1 Cys + CDR3 Cys extra disulfide | CDR1 ~C33（AbM CDR1 ），CDR3 C99/C100x | **CDR lock **（AbM CDR1=26–36，CDR3=95–103）|
| Type III/IV | （germline ，）| C22, C92 | `protect_all_fr_cys=True` |

****：Type II VNAR  Kabat CDR1  26–36  C33， CDR lock ，。 VNAR  CDR1 Cys  Kabat 23–25（FR1 ）， `--extra-protect 23`  `24`  `25`。

**Type I  HV2 **

Type I VNAR  HV2（hypervariable loop 2，Kabat ~56–64）， CDR3  CDR3 。 CDR （AbM CDR2=50–59） HV2 ； Type I ， `--extra-protect 60 61 62 63 64`  HV2 。

**ANARCI **

（`anarcii` Kabat ）：
- VNAR  `chain_type='H'`， HMM ，score  30（ VHH  200+）
- Kabat  FR1–FR3 ；CDR3  FR4 （100A/100B ）
- FR3 （82A/82B/82C ） `MISSING_PROFILE` （ VH ）， KEEP，

****

|  | Type I VNAR | Type II VNAR |
|------|-------------|--------------|
|  | 103 | 122 |
| CDR lock | 27 | 36 |
| STRUCT_PROTECT | 5 | 5 |
| Substitutions | 11 | 15 |
| ΔAA | 10.7% | 12.3% |

|  |  |
|------|------|
|  | ；W36（FR2， VHH W37） Y108/L108（FR4） π–π/；`extra_protect_martin={36,108}`  |
|  | Type II  CDR1-CDR3 Cys  AbM CDR lock ； FR Cys（ canonical C22/C92） `protect_all_fr_cys=True`  |
|  VH  | FR3 （Kabat 75–82C），substitution ；FR1/FR2/FR4  |
|  freq_threshold | **0.10**（ VHH ） |
| ANARCI  |  score ；CDR3 （>20 aa） |
| HV2 Type I | AbM CDR2  HV2 ；（pos 60–64）， `--extra-protect 60 61 62 63 64` |

****:
```bash
# Type I VNAR（，--extra-protect  HV2 ）
conda run -n anarcii python run_llamanade_seq_only.py \
    --fasta shark_vnar_type1.fasta --species shark \
    --out llamanade_shark_t1.json

# Type II VNAR（CDR1-CDR3 ，）
conda run -n anarcii python run_llamanade_seq_only.py \
    --fasta shark_vnar_type2.fasta --species shark \
    --out llamanade_shark_t2.json

#  CDR1 Cys  Kabat 23–25，
conda run -n anarcii python run_llamanade_seq_only.py \
    --fasta shark_vnar_type2_rare.fasta --species shark \
    --extra-protect 23 \
    --out llamanade_shark_t2_rare.json
```

---

### 3.3 

```
 → VHH（alpaca/llama）、 VH、 VH
 → Shark VNAR Type I/II（ANARCI score ，CDR3 ）
   → Chicken（CDR3 diversityVH）、Bovine ultralong CDR3
   →  non-Ig （affibody、DARPin ）
```

### 3.4  AbEngineCore 

|  | Llamanade | AbEngineCore |
|--------|---------------------|--------------|
|  | protinter  | Tier 0/1 + IMGT  |
| VHH FR2 |  37/45/47 |  Hallmark （44→Q, 45→R, 47→G）|
| CDR3 Cys | ， | CDR3 len + Cys-pair （P2-8） |
|  | human VH NGS  | VHH42  + VH3 SAFE  |
| FR3  | （ 22R→C） | Tier  +  Cys |
|  | （threshold, extra_protect） | （//） |

---

## 4. 

```bash
# （alpaca VHH， examples/ ）
python run_llamanade_seq_only.py \
    --fasta alpaca_vhh_console.fasta \
    --species alpaca \
    --out llamanade_alpaca_result.json

#  VH
python run_llamanade_seq_only.py \
    --fasta rabbit_vh.fasta \
    --species rabbit \
    --freq-threshold 0.15 \
    --out llamanade_rabbit_result.json

#  CDR3（stalk anchor  extra-protect）
python run_llamanade_seq_only.py \
    --fasta bovine_vh.fasta \
    --species bovine \
    --out llamanade_bovine_result.json

# ，
python run_llamanade_seq_only.py \
    --fasta chicken_vh.fasta \
    --species chicken \
    --extra-protect 37 45 47 \
    --out llamanade_chicken_result.json

#  VNAR Type I
python run_llamanade_seq_only.py \
    --fasta shark_vnar_type1.fasta \
    --species shark \
    --out llamanade_shark_t1.json

#  VNAR Type II（CDR1-CDR3 ，）
python run_llamanade_seq_only.py \
    --fasta shark_vnar_type2.fasta \
    --species shark \
    --out llamanade_shark_t2.json
```

>  `anarcii` conda ：  
> `conda run -n anarcii python run_llamanade_seq_only.py ...`  
>  IDE terminal  anarcii 。
