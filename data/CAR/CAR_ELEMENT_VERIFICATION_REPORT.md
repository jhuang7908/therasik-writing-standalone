# CAR — 

****: 2026-04-01  
****: InSynBio AI Research  
****: `data/CAR/`  
****: ，

---

## 、

|  |  |  |  |  |
|----------|----------|----------|----------|--------|
| `car_fully_annotated/_v1.0.json` | 51 | 26 | 4 | 21 |
| `car_integrated_results/1_enhanced.json` | 5 | 1 | 4 | 0 |
| `car_integrated_results/1_.json` | 51 | 26 | 4 | 21 |
| `car_integrated_results/2.json` | 44 | 5 | 39 | 0 |
| `car_integrated_results/3.json` | 41 | 41* | 0 | 0 |
| `car_integrated_results/.json` | 184 | 9 | 0 | 175 |
| `car_integrated_results/.json` | 269 | 55 | 39 | 175 |

*：341""，22（III）

---

## 、

###  I： — His-tag

****: iCasp9、EGFRt (Extended)、RQR8、CD20 Mimotope（1）；239/44

****（45 aa）:
```
MGSSHHHHHHSSGLVPRGSHMASMTGGQQMGRDLYDDDDKDRWGS
```

****: **6×His-tag + ** (pDEST™ / pET-28 )，CAR。  
AI，。

****: 。

---

###  II：tEGFR——EGFR

****: `P1_002 | tEGFR | `  
****: 1211 aa  
****: ~335 aa

****:  
- **EGFR**（UniProt P00533， + 4domain +  + 1210 aa）
- tEGFR（**EGFR**）Jensen，：
  - EGFR（1-24）
  - III（334-504）IV（505-645），~312 aa
  - （646-668）
  - ****（669-1210）
- : Wang X, et al. *Blood* 2011;118(5):1255-1263 (NCT01109095)
- （Cetuximab）tEGFRADCC/CDC
- EGFRTKI，****

****: domains III+IV+TM（~335 aa），UniProt P00533 residues 334-668。

---

###  III：——22Binder

****（241 aa，）:

| ID |  |  |
|--------|------|---------|
| AUTOIMMUNE_004 | IL-17A scFv | IL-17A (Secukinumab) |
| AUTOIMMUNE_005 | TNF-α scFv | TNF-α (Adalimumab) |
| INFECTIOUS_001 | HIV gp120 scFv | HIV-1 gp120 |
| INFECTIOUS_002 | HBV HBsAg scFv | HBV |
| INFECTIOUS_003 | HCV E2 scFv | HCV E2 |
| INFECTIOUS_004 | HIV gp41 MPER scFv | HIV-1 gp41 MPER |
| INFECTIOUS_005 | SARS-CoV-2 Spike RBD scFv | SARS-CoV-2 RBD |
| INFECTIOUS_006 | HCV NS3 protease scFv | HCV NS3 |
| INFECTIOUS_007 | SARS-CoV-2 Spike RBD scFv | SARS-CoV-2 RBD|
| INFECTIOUS_008 | Influenza HA scFv | HA |
| NEURO_001 | Aβ oligomer scFv | Aβ |
| NEURO_002 | Tau protein scFv | Tau |
| IL-17A scFv_3e34f3c2 | IL-17A scFv | IL-17A|
| TNF-α scFv_3e34f3c2 | TNF-α scFv | TNF-α|
| HIV gp120 scFv_3e34f3c2 | HIV gp120 scFv | HIV-1 gp120|
| HBV HBsAg scFv_3e34f3c2 | HBV HBsAg scFv | HBV|
| _3e34f3c2... | | |

****（241 aa，scFvVH+G4S4+VL，）:
```
EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRD
NSKNTLYLQMNSLRAEDTAVYYCAAKYPHYYGMDYWGQGTLVTVSSGGGGSGGGGSGGGGSDIQMTQSPSSLSA
SVGDRVTITCRASQDVNTAVAWYQQKPGKAPKLLIYSASFLYSGVPSRFSGSGSGTDFTLTISSLQPEDFATYY
CQQHYTTPPTFGQGTKVEIK
```

****: **scFv**（VHSecukinumab/IL-17A，VLκ），AIBinder。scFv CDR，。

****: scFvCDR。。

---

###  IV：Dsg3 = MuSK

****: AUTOIMMUNE_001 (Dsg3)  AUTOIMMUNE_002 (MuSK)  
****: （394 aa），scFv，。  
- Desmoglein-3 (DSG3)：，UniProt P32926，~550 aa
- MuSK：，UniProt O15146，~460 aa  
，。  
****: CAAR****，scFv（CDR），。

---

###  V：β2GP1 — β2GP1

****: AUTOIMMUNE_003 (β2GP1，395 aa)  
****: Beta-2-glycoprotein 1 (B2GPI，UniProt P02749) 326 aa。  
（395 aa）scFv（G4S linker + VH + VL），scFvB2GPI。

---

###  VI：FMC63 scFv——Fc

****: `P2_001 | FMC63 scFv`（2）  
****: ~456 aa，VH + **IgG1 CH1+hinge+CH2+CH3**（Fc）  
****: FMC63 scFv = VH（~120 aa）+ (GGGGS)₃ linker（15 aa）+ VL（~108 aa）≈ **243 aa**  
****: AI（VH+CH1+CH2+CH3）scFv，FcCAR-TFc，。

---

## 、（/）

###  VII：INFECTIOUS_007 
`SARS-CoV-2 Spike RBD scFv` INFECTIOUS_005INFECTIOUS_007，，。

###  VIII：
：
- "" vs "Safety Switch"
- "Binder" vs "Binder/Targeting Domain"
- "" vs "Costimulatory Domain"  
。

###  IX：iCasp9tEGFR
，iCasp9、EGFRt`application_scenarios`（NCT01865617 B），iCasp9 **NCT01494286**（DiGiusto DL，haploidentical HSCTGvHD）NCT02050971（HER2+ ）。

---

## 、

### 4.1 

#### tEGFR（EGFR）
- ****: Wang X et al. *Blood* 2011;118(5):1255-63
- **UniProt**: P00533， residues 1-24+ 334-668（DIII/DIV + TM）
- ****: ~335 aa
- ****: ，domain III
- ****: ✅ ，UniProt

#### EGFRt (Extended)
- ****: Jensen，EGFR
- ****: Scarfò I, Maus MV. *Nat Rev Clin Oncol* 2017
- ****: tEGFR（domain I/II）
- ****: ⚠️ protocol

#### iCasp9（Caspase-9）
- ****: Di Stasi A et al. *NEJM* 2011;365(18):1673-83
- ****: FKBP12-F36V（89 aa，F36V）+ Casp9ΔCARD（135-416，282 aa）
- ****: ~455 aa
- ****: F36VFKBP12AP1903（rimiducid）；CARD
- **UniProt**: FKBP1A P62942（F36V）+ CASP9 P55211（135-416）
- ****: NCT01494286（GvHD）, NCT02051257
- ****: ✅ ，UniProt

#### RQR8
- ****: Philip B et al. *Blood* 2014;124(8):1277-87
- ****: ，CD34（QBEnd10，）+ CD20（，）+ CD34
- ****: ~136 aa
- ****（Philip et al.）:  
  `MALPVTALLLPLALLLHAARP-[CD34 SP]-CPEPQESDQPPVAEETLHCGS-[spacer]-CPPPCCEPEPELMLMLSL-[CD34 stalk-TM]`
- ****: ✅ ，Philip et al. 2014 Figure 1

#### CD20 Mimotope
- ****: Paszkiewicz PJ et al. *J Clin Invest* 2016;126(11):4262-72
- ****: rituximab，
- ****: RQR8CD20，rituximab（CPAPCSTLPEPTK ）
- ****: 10-20 aa，
- ****: ⚠️ 

---

### 4.2 Binder

#### FMC63 scFv（CD19）
- ****: Nicholson IC et al. *Mol Immunol* 1997;34(16-17):1157-65；FDAKymriah
- ****: VH（120 aa）+ (GGGGS)₃（15 aa）+ VL（108 aa）= **243 aa**
- **CDR**: VH-CDR3: STYYGGDWYFNV，VL-CDR3: QQHYTTPPT
- ****: ✅ Addgene #119010 ，WO2016164731

#### J6M0 / bb2121 scFv（BCMA，Abecmabinder）
- ****: Frieberg et al. *Nat Med* 2021；FDAAbecma (idecabtagene vicleucel)
- **scFv**，BCMA（TNFRSF17）
- ****: ✅ WO2016/014565，Addgene #92,389

#### SJ25C1 scFv（CD19，FMC63）
- ****: Bejcek BE et al. *Cancer Res* 1995；CD19 CAR-T
- **FMC63**: CD19
- ****: ✅ 

#### m971 scFv（CD22）
- ****: Bhatt DL et al.；NIH/NCI，scFv
- ****: CD22，
- ****: NCT02315612 (Singh N et al., *NEJM* 2018)
- ****: ✅ Haso W et al. *Blood* 2013

---

### 4.3 

#### CD3ζ（3×ITAM，）
- ****: UniProt P20963，CD247_HUMAN
- ****: 52-164（，113 aa）
- ****: 3ITAM（Y83/Y94, Y111/Y123, Y142/Y153），CAR
- ****: ✅（ACTES verify_report）

#### 4-1BB（CD137，TNFRSF9）
- ****: UniProt Q07011，TNFR9_HUMAN
- ****: 214-255（，42 aa）
- ****: TRAF，T，（Kymriah/Breyanzi）
- ****: ✅（ACTES verify_report）

#### CD28
- ****: UniProt P10747，CD28_HUMAN
- ****: 180-220（，41 aa）
- ****: PI3K，；YMNMPYAP motifs（Yescarta/Tecartus）
- ****: ✅（ACTES verify_report）

#### OX40（CD134，TNFRSF4）
- ****: UniProt P43489，TNR4_HUMAN
- ****: 238-277（，40 aa）
- ****: ❌ ACTES verify_report""，

#### ICOS
- ****: UniProt Q9Y6W8，ICOS_HUMAN
- ****: （36 aa）
- ****: ⚠️ ACTES verify_reportUniProt，

#### 2B4（CD244，CAR-NK）
- ****: UniProt Q9BZW8，CD244_HUMAN
- ****: 246-380（，135 aa）
- ****: ✅（ACTES verify_report）

---

### 4.4 Hinge / 

#### CD8α Short（45 aa）
- ****: UniProt P01732，CD8A_HUMAN，138-185
- ****: ❌ ACTES verify_report""，

#### CD8α Long（119 aa）
- ****: UniProt P01732，CD8A_HUMAN，90-210
- ****: ✅（ACTES verify_report）

#### CD28 Medium（39 aa）
- ****: UniProt P10747，CD28_HUMAN，114-152
- ****: ✅（ACTES verify_report）

#### IgG4 Long/SPLE
- ****: UniProt P01861，IGHG4_HUMAN（S228PFab-arm）
- ****: ❌ ACTES verify_report""，

---

### 4.5 

#### CD8α TM（24 aa）
- ****: UniProt P01732，CD8A_HUMAN，183-206
- ****: ✅（ACTES verify_report）

#### CD28 TM（27 aa）
- ****: UniProt P10747，CD28_HUMAN，153-179
- ****: ✅（ACTES verify_report）

#### CD4 TM
- ****: UniProt P01730，CD4_HUMAN
- ****: ⚠️ ACTES，UniProt

---

### 4.6  / Linker

#### CD8α SP（20 aa）
- ****: UniProt P01732，CD8A_HUMAN，2-21
- ****: ✅（ACTES verify_report）

#### GM-CSF SP（16 aa）
- ****: UniProt P04141，CSF2_HUMAN，1-16
- ****: ⚠️ verify_report

#### IgK Leader SP（21 aaM）
- ****: UniProt P01834，IGKC_HUMAN，
- ****: ⚠️ verify_report

#### (GGGGS)n Linker
- ****: G4S₁=GGGGS, G4S₃=GGGGSGGGGSGGGGSGGGGS (20 aa), G4S₄=GGGGSGGGGSGGGGSGGGGSGGGGS (25 aa)
- ****: ✅ ，UniProt

#### P2A / T2A
- **P2A**（20 aa）: GSGATNFSLLKQCGDVEENPGP（Thosea asigna2A）
- **T2A**（20 aa）: EGRGSLLTCGDVEENPGP（2A）
- ****: ✅ （Kim JH et al. *PLoS ONE* 2011）

---

## 、

### :
- PMID 27365313: Ellebrecht CT et al. *Science* 2016 — CAAR-T， ✅
- PMID 24590059: Porter DL et al. *Sci Transl Med* 2014 — CD19 CAR-T， ✅

### :
- **PMID 28439030**: "bb2121 CAR-T""FMC63"——PMID Brudno JN et al. *J Clin Oncol* 2018，BCMA CAR-T，FMC63 ⚠️
- **PMID 30559409**: "Abecma"——Abecma20213，PMID 305594092019， ⚠️
- **PMID 33264556**: （IL-17A、TNF-α）——PMIDscFv，，AI ❌

---

## 、

### P1 — 

|  |  |  |
|------|------|------|
| tEGFR | EGFR | UniProt P005331-24+334-668 |
| iCasp9 | His-tag | FKBP1A(P62942,F36V)+CASP9(P55211,135-416) |
| EGFRt (Extended) | His-tag |  |
| RQR8 | His-tag | Philip et al. Blood 2014 Fig.1 |
| CD20 Mimotope | His-tag | ，Paszkiewicz et al. 2016 |
| FMC63 scFv（2）| Fc | VH+G4S3+VL（243 aa）|
| J6M0/bb2121 scFv | His-tag | WO2016/014565 |

### P2 — 

|  |  |
|------|------|
| CD3ζ（3×ITAM）| UniProt P20963，52-164 |
| 4-1BB | UniProt Q07011，214-255 |
| CD28 | UniProt P10747，180-220 |
| CD8α Short hinge |  |
| CD8α Long hinge | UniProt P01732，90-210 |
| CD28 Medium hinge | UniProt P10747，114-152 |
| IgG4-SPLE hinge | （S228P）|
| CD8α TM | UniProt P01732，183-206 |
| CD28 TM | UniProt P10747，153-179 |
| CD8α SP | UniProt P01732，2-21 |

### P3 — （Binder，）

|  |  |
|------|------|
| 22scFv Binder | /CDR |
| OX40、ICOS | UniProt |
|  | Dsg3/MuSK/β2GP1 |

---

## 、

****，AI：
1. ****：His-tag
2. ****：
3. **/**：（tEGFR）

****: ， CD3ζ、4-1BB、CD28、CD8α（ACTES），**CAR-T**。

---

*: v1.0 | 2026-04-01 | InSynBio AI Research*
