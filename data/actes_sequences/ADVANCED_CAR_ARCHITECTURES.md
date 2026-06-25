#  CAR-T 

****， ACTES ； `sequence_db.json`、`ACTES_sequences_canonical.fasta`  `functional_domains.json`，。

---

## 1. 4-1BB_IL2Rb（5 CAR ）

****： 1 。

### 

```
[] - [] - [] - [] - [4-1BB] - [IL-2Rβ] - [CD3ζ]
```

### 

|  | sequence_db entry_id |  |  |
|------|----------------------|------|------|
|  | CD8a_SP | 20 aa | （ M）； M  MALPVTALLLPLALLLHAARP |
|  | CD8a_Short | 48 aa |  CD8a_Long（121 aa） |
|  | CD8a_TM  CD28_TM | 24 / 27 aa |  CD8a_TM |
| 4-1BB  | 4-1BB_cyto | 42 aa | Q07011 214-255 |
|  | G4S3 | 16 aa | (G4S)₃ |
| **IL-2Rβ ** | **IL2Rb_cyto** | **114 aa** | **P14784 237-350**（Box1/Box2； OX40）|
|  | (G4S)₂ | 10 aa | GGGGSGGGGS |
| CD3ζ  | CD3z_cyto | 113 aa | P20963 52-164（ MGGK**Q**RRK）|

****：`4-1BB_IL2Rb_5G_cyto`（295 aa：4-1BB + G4S3 + IL2Rb + (G4S)2 + CD3ζ）。

### 

- ：CD3ζ ITAM；：4-1BB（TRAF/NF-κB）；：IL-2Rβ（JAK1-STAT5）。
- 、；。：PMID 30076368、16477010。

---

## 2. 4-1BB_TRUCK（TRUCK ）

****： 2 。

### 

TRUCK = T cells Redirected for Universal Cytokine-mediated Killing。  
2G CAR+ （、TME ）。

### 

- **CAR **： **4-1BB_Base** （4-1BB + CD3ζ）； CD8a_SP、CD8a_Short、CD8a_TM  CD28_TM、4-1BB_cyto、CD3z_cyto。
- ****：T2A  P2A（sequence_db：T2A、P2A）。
- ****： TRE3G NFAT_Response（T ）→ （IL-12  IL-18）→ P2A → 。
- ****：5'LTR-Ψ-RRE-cPPT-EF1α-CAR-[TRE  NFAT]--P2A--WPRE-3'LTR。

 `functional_domains.json` → `scaffolds.CAR-T.4-1BB_TRUCK`；TRE3G、NFAT_Response、P2A  sequence_db。

---

## 3. SynNotch_Scaffold（SynNotch ）

****： 3 。

### 

```
[] - [] - [Notch  NRR] - [] - [NICD ] - []
```

### 

|  | entry_id |  |  |
|------|----------|------|------|
|  | Notch1_SP | 22 aa | Morsut Cell 2016 |
|  | G4S3 | 16 aa | (G4S)₃， NRR  |
| Notch  | SynNotch_NRR | 150 aa | EGF-like repeats |
|  | Notch1_TM | 21 aa | Notch1 TM |
| NICD RAM | SynNotch_RAM | 110 aa |  RAM  |
| NICD ANK | SynNotch_ANK | 65 aa |  ANK  |
|  |  | — | VP64、p65、Gal4-VP64 ， |

****： CAR（AND/OR）、、、。。：Morsut et al. Cell 2016 PMID 26830878。

---

## 4. Split CAR（Costim/Activator ）

****： 4 。

### 

Split CAR  CAR ， **AND-gate**： A  B ，T （Signal 1 + Signal 2）。

- ** A（Costimulatory）**：scFvA –  – TM – ****（CD28  4-1BB）， CD3ζ。
- ** B（Activator）**：scFvB –  – TM – **CD3ζ**，。

（PMID 37012415）：ROR1–CD8TM–ζ（Activator）+ CD19–CD28TM–CD28（Costim）；。

### 

|  | sequence_db entry_id |  |  |
|------|----------------------|------|------|
|  | CD8a_SP | 20 aa |  |
|  | CD8a_Short  CD28_Medium | 48 / 39 aa | （CD8  + CD28 TM） |
|  | CD8a_TM  CD28_TM | 24 / 27 aa | ** TM**  |
| （ A） | CD28_cyto  4-1BB_cyto | 41 / 42 aa | P10747 180-220 / Q07011 214-255 |
| （ B） | CD3z_cyto | 113 aa | P20963 52-164 |

****：（ EF1α–A–T2A–B）；T2A/P2A  sequence_db。

### （， UniProt ）

|  |  | UniProt |  |  |
|------|------|---------|------|------|
|  CD3ζ（ tonic ） | ZAP-70  | P43403 | 255-600 (346 aa) | PMID 37012415 |
| LINK CAR  A | LAT  ΔGADS | O43561 | 35-233，Y171F/Y191F | PMID 37012415 |
| LINK CAR  B | SLP-76  ΔGADS | Q13094 | 224-533， GADS  | PMID 37012415 |

### 

- ****： TM（ CD8α TM + CD28 TM）、； scFv （ KD ~10⁻⁷ M）。
- ****：（ EGFR+HER2、PSMA+STEAP1）、（CD19+CD20、BCMA+CD38）；。
- ****： IFN-γ 、；、。

：**37012415**（Nature 2023， CAR、ZAP-70、LINK CAR）、**36928345**（Tuning CARs）、**37993712**（Nature Commun 2024， Split CAR）； Split CAR：**23340339**（Kloss Nat Biotechnol 2013）。

---

## 

|  |  |  | / |
|------|------|----------|----------------|
| 1 | 4-1BB_IL2Rb 5 |  1  | ✅ IL2Rb_cyto、4-1BB_IL2Rb_5G_cyto |
| 2 | 4-1BB_TRUCK |  2  | ✅  + TRE3G/NFAT_Response/P2A |
| 3 | SynNotch_Scaffold |  3  | ✅ Notch1_SP、SynNotch_NRR、Notch1_TM、SynNotch_RAM、SynNotch_ANK |
| 4 | Split CAR（Costim/Activator） |  4  | ✅ CD3z_cyto、CD28_cyto、4-1BB_cyto、CD8a_Short、CD8a_TM、CD28_TM |

****：5「IL-2Rβ 」 **IL2Rb_cyto（114 aa，P14784 237-350）**， OX40 （40 aa，RRDQRLPP...）；CD3ζ （113 aa，P20963 52-164）。
