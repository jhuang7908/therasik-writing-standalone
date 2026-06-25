# AbEngineCore  —  ·  · 

 Cursor  PowerShell 。

---

## 、

|  |  |  |
|------|------|--------|
| **** | `fix` / `verify` | 、、 |
| **** | `package` | （、） |
| **** | `new` | （， Option A） |
| **** | `export-internal` |  `results.json`  `internal/`， |
| **** | `evaluate` |  PDB 、、 |
| **** | `dog` |  VH/VL → （CDR  + ） |
| **** | `batch` |  fix / verify / package |

---

## 、（Cursor ）

|  |  |  |
|------|------|----------|
| Cursor  | 、 |  IDE  |
|  PowerShell | / |  |

****： Cursor ，， **Python ** ：

```bash
# ：Antibody_Engineer_Suite 
python Abenginecore/abenginecore.py fix fxy_2c2 projects/fxy_2c2_Redesign
```

---

## 、

### 3.1  A：， + 

**：**

- ****：`python Abenginecore/abenginecore.py fix <ab_id> <project_dir>`
- ****：、，** + **。
- ** (V4.4-Strict)**：
  - **FAIL means FAIL**： V4.4 （CDR RMSD < 1.5Å, pI 5.5-8.5, ），。
  - **WARN **： WARN。
  - ****：`fix`  CMC （ pI>8.5  v3  pI） Vernier round2；，。
- ****：
  - ： `projects/<id>_Redesign/<id>_results.json`  PDB/FASTA，/。
  - （`structure_13param`）： `results.json` （Vernier dual numbering=22），****；/ `results.json`。
  - `internal/`：（germline）、CMC/、、、 `results.json` ****，。

** 1：fxy_2c2 ，**

```bash
python Abenginecore/abenginecore.py fix fxy_2c2 projects/fxy_2c2_Redesign
```

** 2：fxy_2h2_opta（Option A ）， + **

```bash
python Abenginecore/abenginecore.py fix fxy_2h2_opta projects/fxy_2h2_opta_Redesign
```

** 3：fxy_2e2_opta（Option A ）**

```bash
python Abenginecore/abenginecore.py fix fxy_2e2_opta projects/fxy_2e2_opta_Redesign
```

- ** PDF**： JSON/MD 。 `[fix] 1/11 …` （ pI、Vernier  PASS、）。
- ** PDF **： `--pdf`

```bash
python Abenginecore/abenginecore.py fix fxy_2c2 projects/fxy_2c2_Redesign --pdf
```

** IEDB API （，）：**

```bash
python Abenginecore/abenginecore.py fix fxy_2c2 projects/fxy_2c2_Redesign --use-iedb
```

**、：**

```bash
python Abenginecore/abenginecore.py verify fxy_2c2 projects/fxy_2c2_Redesign
```

---

### 3.2  B：（、）

 `results.json` （：， ZIP）， `package`：

```bash
# 
python Abenginecore/abenginecore.py package fxy_2c2 projects/fxy_2c2_Redesign

#  ZIP
python Abenginecore/abenginecore.py package fxy_2c2 projects/fxy_2c2_Redesign --zip
```

**：Option A **

```bash
python Abenginecore/abenginecore.py package fxy_2h2_opta projects/fxy_2h2_opta_Redesign --zip
python Abenginecore/abenginecore.py package fxy_2e2_opta projects/fxy_2e2_opta_Redesign --zip
```

****：`delivery_<id>/` ， `{id}_delivery_YYYYMMDD.zip`。

---

### 3.3  C： internal（、）

“” internal（/）， ****  / Vernier round2 ：

```bash
python Abenginecore/abenginecore.py export-internal fxy_2c2 projects/fxy_2c2_Redesign
```

**（，）**：

```bash
python Abenginecore/abenginecore.py export-internal fxy_2c2 projects/fxy_2c2_Redesign --enrich-immuno
```

---

### 3.4  D：（ `new`）

****： `abenginecore new` ， fix/verify/package 。

** 1：**

```bash
python Abenginecore/abenginecore.py new my_ab --vh "QVQLVQSGPELMKPGASVKISCKASGYSFTSYHMHWVKQSHGESLEWIGYVDPFKAAISYNPKFKGKATLTVDRSSTTAYMHFSSLTSEDSAVYFCARAYYRSDENYFDFWGQGTTLTVSS" --vl "DIQMTQSPASLSASVGDRVTITCRASQNVGSYVNWYQQKPGNAPNLLISAASTVHSGVSSRIGGSGFGTDFTLTINSLQPEDFATYYCQQTYSALGTFGQGTKVEMK"
```

** 2： FASTA **

```bash
python Abenginecore/abenginecore.py new my_ab --vh-fasta vh.fasta --vl-fasta vl.fasta
```

** 3：Option A —  IGHV3-23*01（pI>8.5 ）**

 pI>8.5 ， Option A  IGHV3-23*01 （：CDR ，RMSD < 1.5Å）：

```bash
#  Option A
python Abenginecore/abenginecore.py new fxy_2h2_opta --vh-fasta fxy_2h2_vh.fasta --vl-fasta fxy_2h2_vl.fasta --opt-a
```

** 4：**

```bash
python Abenginecore/abenginecore.py new my_ab --vh "QVQL..." --vl "DIQM..." --force-germline-vh IGHV3-23*01 --force-germline-vl IGKV1-39*01
```

****：`projects/<id>_Redesign/` ， `results.json`、、、； fix（+）。

****：`new`  `run_vhvl_v44_pipeline.py`， AbEngineCore ， `--opt-a` 。

---

## 、

### 4.1  / （ mouse ）

```bash
python Abenginecore/abenginecore.py evaluate my_ab --type fully_human --pdb path/to/antibody.pdb --modules structure_13param developability immunogenicity
```

### 4.2 （ mouse ， delta）

```bash
python Abenginecore/abenginecore.py evaluate my_ab --type humanized --pdb path/to/humanized.pdb --ref-pdb path/to/mouse.pdb --modules structure_13param delta_vs_mouse developability immunogenicity --no-strict-qa
```

### 4.3  `--modules`

|  |  |
|------|------|
| `structure_13param` | 13  |
| `tap` | TAP （PSH/PPC/PNC/SFvCSP/CDR Length） |
| `delta_vs_mouse` |  vs  |
| `developability` | pI、CMC、TAP  |
| `immunogenicity` | MHC-II  |
| `binding_site` | Ab-Ag （ `--antigen-chain`） |
| `germline` |  |
| `cdr_scan` | CDR  |

### 4.4 

|  |  |
|------|------|
| `--antigen-chain` |  ID（`binding_site` ） |
| `--cdr-json` | CDR  JSON （`tap` ） |
| `--use-iedb` |  IEDB  API |

 [docs/ABEVALUATOR_CLI_REFERENCE.md](../docs/ABEVALUATOR_CLI_REFERENCE.md)。

---

## 、

### 5.1 （ Pembrolizumab ）

```bash
python Abenginecore/abenginecore.py dog --name CLI_Dog_Demo --demo
```

### 5.2  FASTA 

```bash
python Abenginecore/abenginecore.py dog --name my_dog_proj --vh-fasta vh.fasta --vl-fasta vl.fasta
```

### 5.3  VH/VL

```bash
python Abenginecore/abenginecore.py dog --name my_dog_proj --vh "EVQLVQSG..." --vl "EIVLTQSP..."
```

### 5.4 

```bash
python Abenginecore/abenginecore.py dog --name my_proj --vh-fasta vh.fasta --vl-fasta vl.fasta --out-dir my_output
```

---

## 、

### 6.1  CSV 

 `batch_manifest.csv`（UTF-8）：

```text
ab_id,project_dir
fxy_2c2,projects/fxy_2c2_Redesign
9c1,projects/9c1_Redesign
4b12,projects/4b12_Redesign
fxy_2h2_opta,projects/fxy_2h2_opta_Redesign
fxy_2e2_opta,projects/fxy_2e2_opta_Redesign
```

### 6.2  fix（ +  + ）

```bash
python Abenginecore/abenginecore.py batch fix --manifest batch_manifest.csv --continue-on-error
```

### 6.3  verify

```bash
python Abenginecore/abenginecore.py batch verify --manifest batch_manifest.csv --continue-on-error
```

### 6.4  package（，）

```bash
# 
python Abenginecore/abenginecore.py batch package --manifest batch_manifest.csv --continue-on-error

#  ZIP
python Abenginecore/abenginecore.py batch package --manifest batch_manifest.csv --zip --continue-on-error
```

****：， ZIP，。

---

## 、

- ****： `Antibody_Engineer_Suite` ， `projects/fxy_2c2_Redesign` 。
- ****： `D:/InSynBio-AI-Research/Antibody_Engineer_Suite/projects/fxy_2c2_Redesign`。
- Windows  `/`  `\` 。

---

## 、PowerShell 

 `abenginecore.ps1` ：

```powershell
.\abenginecore.ps1 fix fxy_2c2 projects\fxy_2c2_Redesign
```

：

```powershell
Set-Alias abenginecore .\abenginecore.ps1
abenginecore fix fxy_2c2 projects\fxy_2c2_Redesign
abenginecore package fxy_2h2_opta projects\fxy_2h2_opta_Redesign --zip
```

---

## 、

```bash
# ──  ──
python Abenginecore/abenginecore.py fix fxy_2c2 projects/fxy_2c2_Redesign
python Abenginecore/abenginecore.py fix fxy_2h2_opta projects/fxy_2h2_opta_Redesign --pdf
python Abenginecore/abenginecore.py verify fxy_2c2 projects/fxy_2c2_Redesign
python Abenginecore/abenginecore.py package fxy_2c2 projects/fxy_2c2_Redesign --zip

# ──  ──
python Abenginecore/abenginecore.py new my_ab --vh "QVQL..." --vl "DIQM..."
python Abenginecore/abenginecore.py new fxy_2h2_opta --vh-fasta vh.fasta --vl-fasta vl.fasta --opt-a

# ──  ──
python Abenginecore/abenginecore.py evaluate my_ab --type fully_human --pdb human.pdb --modules structure_13param developability
python Abenginecore/abenginecore.py evaluate my_ab --type humanized --pdb human.pdb --ref-pdb mouse.pdb --modules structure_13param delta_vs_mouse --no-strict-qa

# ──  ──
python Abenginecore/abenginecore.py dog --name CLI_Dog_Demo --demo
python Abenginecore/abenginecore.py dog --name my_proj --vh-fasta vh.fasta --vl-fasta vl.fasta

# ──  ──
python Abenginecore/abenginecore.py batch fix --manifest batch_manifest.csv --continue-on-error
python Abenginecore/abenginecore.py batch package --manifest batch_manifest.csv --zip --continue-on-error
```

---

## 、

```text
：
  abenginecore new X --vh "..." --vl "..." [--opt-a]
    →  projects/X_Redesign/  results.json， fix + 

：
  fix X projects/X_Redesign       →  +  + 
  verify X projects/X_Redesign    → 
  package X projects/X_Redesign   → 

：
  batch fix     →  +  + 
  batch verify  → 
  batch package → 

：
  dog --name Y --vh-fasta vh.fasta --vl-fasta vl.fasta
    → projects/Y/dog_caninization_auto_v1/
```

---

## 、Option A 

 **pI > 8.5** /， **Option A** （ IGHV3-23*01）：

- ****：CDR （RMSD < 1.5Å），。
- ****：`new --opt-a`  pipeline  `--force-germline-vh IGHV3-23*01`。
- ****：fxy_2h2_opta、fxy_2e2_opta。

---

## 、

- **OpenClaw Skills**： OpenClaw ，、、。
- **SaaS **： SaaS ，。
