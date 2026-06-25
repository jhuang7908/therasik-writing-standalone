# ACTES CAR-T Component Library V3 — Status Report

> Generated: 2026-04-01 | Total elements: 85

## Tier Definitions

| Tier | Definition |
|------|------------|
| **T1** | FDA/EMA-approved in CAR-T product; sequence clinically validated |
| **T2** | Published in peer-reviewed clinical trial; IND-filed or Phase I/II |
| **T3** | Research-stage; published in peer-reviewed literature only |

## Summary by Tier

| Tier | Count | With Sequence | Stubs |
|------|-------|--------------|-------|
| **T1** | 17 | 11 ✓ | 6 |
| **T2** | 49 | 31 ✓ | 18 |
| **T3** | 19 | 8 ✓ | 11 |

## Summary by Category

| Category | Total | T1 | T2 | T3 | Seq✓ | Stub |
|----------|-------|----|----|-----|------|------|
| 2A Peptide | 4 | 0 | 4 | 0 | 4 | 0 |
| Activation | 2 | 1 | 1 | 0 | 2 | 0 |
| Allogeneic | 2 | 0 | 2 | 0 | 2 | 0 |
| Armored Payload | 6 | 0 | 4 | 2 | 2 | 4 |
| Binder | 16 | 4 | 9 | 3 | 2 | 14 |
| CAAR Binder | 2 | 0 | 0 | 2 | 0 | 2 |
| Costimulatory | 7 | 2 | 4 | 1 | 7 | 0 |
| Depletion Tag | 4 | 0 | 4 | 0 | 4 | 0 |
| Hinge | 5 | 2 | 2 | 1 | 5 | 0 |
| Leader | 5 | 1 | 2 | 2 | 5 | 0 |
| Linker | 9 | 2 | 6 | 1 | 9 | 0 |
| Logic Gate | 5 | 0 | 1 | 4 | 0 | 5 |
| Regulatory Element | 8 | 3 | 4 | 1 | 0 | 8 |
| Safety Switch | 5 | 0 | 5 | 0 | 3 | 2 |
| Transmembrane | 5 | 2 | 1 | 2 | 5 | 0 |

## Element Detail by Category

### 2A Peptide

| ID | Name | Tier | Seq | Length | QA Source | Products/Trials |
|----|------|------|-----|--------|-----------|------------------|
| `P2A` | P2A Self-Cleaving Peptide (TaV-2A) | T2 | ✓ | 22aa | P2A sequence; Kim JH et al. PLoS ONE 2011;6(4):e18 |  |
| `T2A` | T2A Self-Cleaving Peptide (ERAV-2A) | T2 | ✓ | 18aa | T2A sequence; Kim JH et al. PLoS ONE 2011;6(4):e18 |  |
| `E2A` | E2A Self-Cleaving Peptide (FMDV-2A) | T2 | ✓ | 20aa | E2A sequence; Kim JH et al. PLoS ONE 2011;6(4):e18 |  |
| `F2A` | F2A Self-Cleaving Peptide (FMDV-2A) | T2 | ✓ | 22aa | F2A sequence; Kim JH et al. PLoS ONE 2011;6(4):e18 |  |

### Activation

| ID | Name | Tier | Seq | Length | QA Source | Products/Trials |
|----|------|------|-----|--------|-----------|------------------|
| `CD3z_cyto` | CD3ζ Activation Domain (3×ITAM) | T1 | ✓ | 113aa | P20963 (CD247_HUMAN) res 52-164 | Kymriah, Yescarta |
| `FcRg_cyto` | FcRγ Cytoplasmic Domain (CAR-M) | T2 | ✓ | 42aa | P30273 (FCRG_HUMAN) res 45-86 | NCT04660929 |

### Allogeneic

| ID | Name | Tier | Seq | Length | QA Source | Products/Trials |
|----|------|------|-----|--------|-----------|------------------|
| `TRAC_CRISPR_Target` | TRAC Locus CRISPR Target (TCRα KO for Allo-CA | T2 | ✓ | 20aa | Eyquem J et al. Nature 2017;543:113; Sadelain M et | NCT04150497 |
| `B2M_CRISPR_Target` | B2M CRISPR Target (MHC-I KO for Allo-CAR) | T2 | ✓ | 20aa | Torikai H et al. Blood 2012;119:5697; Poirot L et  | NCT04150497 |

### Armored Payload

| ID | Name | Tier | Seq | Length | QA Source | Products/Trials |
|----|------|------|-----|--------|-----------|------------------|
| `TGFB_DNR` | TGF-β Dominant Negative Receptor II (Anti-Sup | T2 | ✓ | 189aa | P37173 (TGFBR2_HUMAN) res 1-189 ECD+TM; Tang N et  | NCT03089780 |
| `Membrane_IL15` | Membrane-Bound IL-15 (mIL-15) | T2 | ○ | 162aa | Sequence: IL-2Rα signal + IL-15 mature + IL-2Rβ tr | NCT03870698 |
| `Membrane_IL21` | Membrane-Bound IL-21 (mIL-21) | T2 | ○ | 170aa | Hurton LV et al. PNAS 2016 (mbIL-21 for NK expansi | NCT04901299 |
| `Secreted_IL12` | Secreted Single-Chain IL-12 p70 (TRUCK) | T2 | ○ | 330aa | Koneru M et al. PNAS 2015;112:E6526; Zhang L et al | NCT02498912 |
| `4-1BBL_Anchored` | Membrane-Anchored 4-1BBL (Self-Driving Costim | T3 | ✓ | 205aa | P41273 (4-1BBL_HUMAN) res 50-255 ectodomain; Pegra | NCT03617731 |
| `GPX4_Enhanced` | GPX4-Enhanced Anti-Ferroptosis Armor | T3 | ○ | 197aa | Drijvers JM et al. Cell 2021;187:5541; Stockwell B |  |

### Binder

| ID | Name | Tier | Seq | Length | QA Source | Products/Trials |
|----|------|------|-----|--------|-----------|------------------|
| `FMC63_scFv` | FMC63 Anti-CD19 scFv (VH-G4S3-VL) | T1 | ✓ | 243aa | USPTO 9,701,758 B2 (Tisagenlecleucel); Nicholson I | Kymriah, Breyanzi |
| `SJ25C1_scFv` | SJ25C1 Anti-CD19 scFv (VH-G4S3-VL) | T1 | ○ | 245aa | Brentjens RJ et al. Nat Med 2003;9:279. Morgan RA  | NCT01044069 |
| `c11D5_3_scFv` | c11D5.3 Anti-BCMA scFv (bb2121/Abecma precurs | T1 | ○ | 244aa | US20200261501A1 (BMS/bluebird bio patent); Carpent | Abecma |
| `JNJ68284528_VHH` | JNJ-68284528 Biepitopic BCMA VHH (Carvykti) | T1 | ○ | 240aa | WO2019219031A1 (Janssen/Legend Biotech); Berdeja J | Carvykti |
| `Trastuzumab_scFv` | Trastuzumab Anti-HER2 scFv (VH-G4S3-VL) | T2 | ○ | 242aa | US5821337 (Genentech trastuzumab); Carter P et al. | NCT01935843 |
| `Daratumumab_scFv` | Daratumumab Anti-CD38 scFv | T2 | ○ | 240aa | US9603927B2 (Janssen daratumumab patent); de Weers | NCT03464916 |
| `SS1_scFv` | SS1 Anti-Mesothelin scFv | T2 | ○ | 236aa | Hassan R et al. J Immunol 2002;169:5956; Chang K P | NCT01355965 |
| `14G2a_hu_scFv` | 14G2a Humanized Anti-GD2 scFv | T2 | ○ | 246aa | Heczey A et al. JCI 2017;127:2277; Louis CU et al. | NCT02107963 |
| `m971_scFv` | m971 Humanized Anti-CD22 scFv (Membrane-Proxi | T2 | ○ | 242aa | Haso W et al. Blood 2013;121:1165 | NCT03448393 |
| `OKT3_hu_scFv` | OKT3 Humanized Anti-CD3ε scFv | T2 | ○ | 240aa | Bhatt DL et al.; Shalaby MR et al. J Exp Med 1992; | NCT03030001 |
| `YP7_scFv` | YP7 Humanized Anti-GPC3 scFv | T2 | ○ | 237aa | Feng M et al. PNAS 2013;110:E4083 | NCT02395250 |
| `NKG2D_Ligand_Binder` | NKG2D Ectodomain (Stress-Ligand Binder) | T2 | ✓ | 144aa | P26718 (NKG2D_HUMAN/KLRK1) res 73-216 ectodomain | NCT03310008 |
| `APRIL_Ligand_Binder` | APRIL Ligand Fragment (BCMA+TACI Dual Targeti | T3 | ○ | 150aa | Guo B et al. JCI 2016;126:4295; Schmidts A et al.  |  |
| `ESK1_WT1_TCRmimic` | ESK1 Anti-WT1(RMFPNAPYL/HLA-A02:01) TCR-Mimic | T3 | ○ | 246aa | Dao T et al. Sci Transl Med 2013;5:176ra33; MSKCC  | NCT02830854 |
| `MAGE-A4_TCRmimic` | MAGE-A4 (GVYDGREHTV/HLA-A*02:01) TCR-Mimic sc | T3 | ○ | 243aa | Dao T et al. Sci Transl Med 2015; multiple MAGE-A4 |  |
| `Anti_FRa_MOv19_scFv` | MOv19 Anti-FRα scFv (Ovarian/NSCLC CAR-T) | T2 | ○ | 241aa | Kandalaft LE et al. Clin Cancer Res 2012; Carpenit | NCT01583686 |

### CAAR Binder

| ID | Name | Tier | Seq | Length | QA Source | Products/Trials |
|----|------|------|-----|--------|-----------|------------------|
| `Dsg3_ECD_CAAR` | Desmoglein-3 ECD (CAAR-T for Pemphigus Vulgar | T3 | ○ | 566aa | Ellebrecht CT et al. Science 2016;353:179; CAART ( | NCT04422912 |
| `MuSK_ECD_CAAR` | MuSK Extracellular Domain (CAAR-T for Myasthe | T3 | ○ | 468aa | Ellebrecht CT et al. Science 2016 (concept); Bhatt |  |

### Costimulatory

| ID | Name | Tier | Seq | Length | QA Source | Products/Trials |
|----|------|------|-----|--------|-----------|------------------|
| `4-1BB_cyto` | 4-1BB (CD137) Costimulatory Domain | T1 | ✓ | 42aa | Q07011 (TNFR9_HUMAN) res 214-255 | Kymriah, Abecma |
| `CD28_cyto` | CD28 Costimulatory Domain | T1 | ✓ | 41aa | P10747 (CD28_HUMAN) res 180-220 | Yescarta, Tecartus |
| `OX40_cyto` | OX40 (CD134) Costimulatory Domain | T2 | ✓ | 40aa | P43489 (TNR4_HUMAN) res 238-277 | NCT03778346 |
| `ICOS_cyto` | ICOS Costimulatory Domain | T2 | ✓ | 37aa | Q9Y6W8 (ICOS_HUMAN) res 163-199 | NCT03101631 |
| `2B4_cyto` | 2B4 (CD244) Costimulatory Domain | T2 | ✓ | 125aa | Q9BZW8 (CD244_HUMAN) res 246-380 | NCT03690882 |
| `DAP12_costim` | DAP12 (TYROBP) Costimulatory Adapter | T2 | ✓ | 31aa | O43914 (TYROBP_HUMAN) res 76-106 | NCT04847466 |
| `CD27_cyto` | CD27 Costimulatory Domain | T3 | ✓ | 52aa | P26842 (CD27_HUMAN) res ~209-260 |  |

### Depletion Tag

| ID | Name | Tier | Seq | Length | QA Source | Products/Trials |
|----|------|------|-----|--------|-----------|------------------|
| `tEGFR_DeplTag` | Truncated EGFR (Depletion Tag alias) | T2 | ✓ | 359aa | P00533 tEGFR — same sequence as tEGFR safety switc | NCT01840566 |
| `CD20_Mimotope` | CD20 Mimotope (Rituximab-Binding) | T2 | ✓ | 9aa | Paszkiewicz PJ et al. J Clin Invest 2016;126:4262 |  |
| `Myc_Tag` | c-Myc Epitope Tag (Detection) | T2 | ✓ | 10aa | Standard 10aa c-Myc epitope; anti-Myc antibody 9E1 |  |
| `FLAG_Tag` | FLAG Octapeptide (Detection Tag) | T2 | ✓ | 8aa | Hopp TP et al. BioTechnology 1988;6:1204 |  |

### Hinge

| ID | Name | Tier | Seq | Length | QA Source | Products/Trials |
|----|------|------|-----|--------|-----------|------------------|
| `CD8a_Short` | CD8α Short Hinge | T1 | ✓ | 45aa | P01732 (CD8A_HUMAN) res 138-182 | Kymriah, Abecma |
| `CD8a_Long` | CD8α Long Hinge | T2 | ✓ | 121aa | P01732 (CD8A_HUMAN) res 90-210 | NCT04637763 |
| `CD28_Medium` | CD28 Medium Hinge | T1 | ✓ | 39aa | P10747 (CD28_HUMAN) res 114-152 | Yescarta, Tecartus |
| `IgG4_SPLE_Long` | IgG4 Long Hinge (S228P, Fc-null) | T2 | ✓ | 229aa | P01861 (IGHG4_HUMAN) EU 216-447; S228P mutation | NCT02546167 |
| `IgD_Hinge` | IgD Hinge (Protease-Resistant) | T3 | ✓ | 64aa | P01880 (IGHD_HUMAN) res ~100-163 |  |

### Leader

| ID | Name | Tier | Seq | Length | QA Source | Products/Trials |
|----|------|------|-----|--------|-----------|------------------|
| `CD8a_SP` | CD8α Signal Peptide | T1 | ✓ | 21aa | P01732 (CD8A_HUMAN) res 1-21 | Kymriah, Yescarta |
| `GM-CSF_SP` | GM-CSF Signal Peptide | T2 | ✓ | 17aa | P04141 (CSF2_HUMAN) res 1-17 | NCT01029366 |
| `Granulin_SP` | Granulin Signal Peptide | T3 | ✓ | 21aa | P28799 (GRN_HUMAN) res 1-21 |  |
| `IgKappa_SP` | IgG Kappa Light Chain Signal Peptide | T2 | ✓ | 21aa | P01834 (IGKC_HUMAN) canonical signal peptide |  |
| `IL2_SP` | IL-2 Signal Peptide | T3 | ✓ | 20aa | P60568 (IL2_HUMAN) res 1-20 |  |

### Linker

| ID | Name | Tier | Seq | Length | QA Source | Products/Trials |
|----|------|------|-----|--------|-----------|------------------|
| `G4S1` | G4S ×1 (5aa) | T1 | ✓ | 5aa | Standard synthetic: G4S ×1 (5aa) — minimal flexibl |  |
| `G4S3` | G4S ×3 (15aa) | T1 | ✓ | 15aa | Standard synthetic: G4S ×3 (15aa) — standard scFv  |  |
| `G4S4` | G4S ×4 (20aa) | T2 | ✓ | 20aa | Standard synthetic: G4S ×4 (20aa) — extended flexi |  |
| `G4S5` | G4S ×5 (25aa) | T2 | ✓ | 25aa | Standard synthetic: G4S ×5 (25aa) — ultra-long lin |  |
| `G4S6` | G4S ×6 (30aa) | T3 | ✓ | 30aa | Standard synthetic: G4S ×6 (30aa) — maximum flexib |  |
| `EAAAK` | EAAAK (5aa) | T2 | ✓ | 5aa | Standard synthetic: EAAAK (5aa) — rigid α-helix li |  |
| `EAAAK3` | EAAAK ×3 (15aa) | T2 | ✓ | 15aa | Standard synthetic: EAAAK ×3 (15aa) — extended rig |  |
| `Whitlow` | Whitlow linker (14aa) | T2 | ✓ | 14aa | Standard synthetic: Whitlow linker (14aa) — optimi |  |
| `218` | 218 Linker (18aa) | T2 | ✓ | 18aa | Standard synthetic: 218 Linker (18aa) — anti-aggre |  |

### Logic Gate

| ID | Name | Tier | Seq | Length | QA Source | Products/Trials |
|----|------|------|-----|--------|-----------|------------------|
| `PD1_CD28_CSR` | PD-1/CD28 Chimeric Switch Receptor | T2 | ○ | 289aa | Liu X et al. Cancer Res 2016;76:1578; Ankri C et a | NCT04213430 |
| `CTLA4_CD28_CSR` | CTLA-4/CD28 Chimeric Switch Receptor | T3 | ○ | 234aa | Leen AM et al; multiple immune checkpoint switch p |  |
| `iCAR_PSMA` | iCAR with PSMA Inhibitory Signal (Prostate Sp | T3 | ○ | 395aa | Fedorov VD et al. Sci Transl Med 2013;5:215ra172 |  |
| `SynNotch_NRR` | SynNotch Negative Regulatory Region (AND-Gate | T3 | ○ | 182aa | Morsut L et al. Cell 2016;164:780; Roybal KT et al |  |
| `Gal4_VP64_TF` | Gal4 DBD + VP64 Transcription Activator (SynN | T3 | ○ | 201aa | Morsut L et al. Cell 2016;164:780; Roybal KT et al |  |

### Regulatory Element

| ID | Name | Tier | Seq | Length | QA Source | Products/Trials |
|----|------|------|-----|--------|-----------|------------------|
| `EF1a_Promoter` | EF1α Promoter | T1 | ○ | 0aa | Standard lentiviral vector design; 1200bp | Kymriah |
| `PGK_Promoter` | PGK1 Promoter | T1 | ○ | 0aa | Standard lentiviral vector design; 500bp | Kymriah |
| `MSCV_LTR` | MSCV LTR Promoter (Murine Stem Cell Virus) | T1 | ○ | 0aa | Standard lentiviral vector design; 590bp | Kymriah |
| `SFFV_Promoter` | SFFV Promoter (Spleen Focus-Forming Virus) | T2 | ○ | 0aa | Standard lentiviral vector design; 560bp |  |
| `EFS_Promoter` | EFS Compact Promoter | T2 | ○ | 0aa | Standard lentiviral vector design; 250bp |  |
| `NFAT_RE_Promoter` | NFAT Response Element (Inducible Promoter) | T2 | ○ | 0aa | Standard lentiviral vector design; 300bp |  |
| `UCOE_EF1a` | UCOE+EF1α (Anti-Silencing Promoter) | T2 | ○ | 0aa | Standard lentiviral vector design; 1500bp |  |
| `Tet_On_System` | Tet-On Inducible System (Dox-Regulated) | T3 | ○ | 0aa | Standard lentiviral vector design; 1800bp |  |

### Safety Switch

| ID | Name | Tier | Seq | Length | QA Source | Products/Trials |
|----|------|------|-----|--------|-----------|------------------|
| `tEGFR` | Truncated EGFR Safety Switch (Cetuximab-Targe | T2 | ✓ | 359aa | P00533 (EGFR_HUMAN) SP(1-24)+DomIII(334-504)+DomIV | NCT01840566 |
| `iCasp9` | Inducible Caspase-9 (ΔCARD) | T2 | ✓ | 282aa | P55211 (CASP9_HUMAN) res 135-416 (ΔCARD, without C | NCT01494286 |
| `FKBP12` | FKBP12 Dimerization Domain (iCasp9 partner) | T2 | ✓ | 108aa | P62942 (FKBP1A_HUMAN) full protein 108aa | NCT01494286 |
| `RQR8` | RQR8 Dual Safety/Tracking Tag | T2 | ○ | 73aa | Synthetic fusion: CD34 QBEnd10 epitope (N-term) +  | NCT02735083 |
| `HSV-TK` | Herpes Simplex Virus Thymidine Kinase (Suicid | T2 | ○ | 376aa | M57671.1 HSV-1 TK gene; Bonini C et al. Science 19 | NCT00001479 |

### Transmembrane

| ID | Name | Tier | Seq | Length | QA Source | Products/Trials |
|----|------|------|-----|--------|-----------|------------------|
| `CD8a_TM` | CD8α Transmembrane Domain | T1 | ✓ | 24aa | P01732 (CD8A_HUMAN) res 183-206 | Kymriah, Abecma |
| `CD28_TM` | CD28 Transmembrane Domain | T1 | ✓ | 27aa | P10747 (CD28_HUMAN) res 153-179 | Yescarta, Tecartus |
| `CD4_TM` | CD4 Transmembrane Domain | T2 | ✓ | 22aa | P01730 (CD4_HUMAN) res 397-418 | NCT03692767 |
| `CD3z_TM` | CD3ζ Transmembrane Domain | T3 | ✓ | 30aa | P20963 (CD247_HUMAN) res 22-51 |  |
| `NKG2D_TM` | NKG2D Transmembrane Domain | T3 | ✓ | 42aa | P26718 (NKG2D_HUMAN) res ~175-216 | NCT03310008 |

## Stubs — Sequences Needed

These elements have complete metadata and references but no sequence loaded yet.

| ID | Category | Tier | Source for Fetch | Expected Length |
|----|----------|------|-------------------|----------------|
| `RQR8` | Safety Switch | T2 | Synthetic fusion: CD34 QBEnd10 epitope (N-term) + CD20 rituximab epito | 73aa |
| `HSV-TK` | Safety Switch | T2 | M57671.1 HSV-1 TK gene; Bonini C et al. Science 1997;295:2041 | 376aa |
| `SJ25C1_scFv` | Binder | T1 | Brentjens RJ et al. Nat Med 2003;9:279. Morgan RA et al. Mol Ther 2010 | 245aa |
| `c11D5_3_scFv` | Binder | T1 | US20200261501A1 (BMS/bluebird bio patent); Carpenter RO et al. Clin Ca | 244aa |
| `JNJ68284528_VHH` | Binder | T1 | WO2019219031A1 (Janssen/Legend Biotech); Berdeja JG et al. Lancet 2021 | 240aa |
| `Trastuzumab_scFv` | Binder | T2 | US5821337 (Genentech trastuzumab); Carter P et al. PNAS 1992;89:4285;  | 242aa |
| `Daratumumab_scFv` | Binder | T2 | US9603927B2 (Janssen daratumumab patent); de Weers M et al. J Immunol  | 240aa |
| `SS1_scFv` | Binder | T2 | Hassan R et al. J Immunol 2002;169:5956; Chang K Pastan I J Biol Chem  | 236aa |
| `14G2a_hu_scFv` | Binder | T2 | Heczey A et al. JCI 2017;127:2277; Louis CU et al. Blood 2011;118:6050 | 246aa |
| `m971_scFv` | Binder | T2 | Haso W et al. Blood 2013;121:1165 | 242aa |
| `OKT3_hu_scFv` | Binder | T2 | Bhatt DL et al.; Shalaby MR et al. J Exp Med 1992;175:217; USAN: murom | 240aa |
| `YP7_scFv` | Binder | T2 | Feng M et al. PNAS 2013;110:E4083 | 237aa |
| `APRIL_Ligand_Binder` | Binder | T3 | Guo B et al. JCI 2016;126:4295; Schmidts A et al. Nat Med 2023 | 150aa |
| `ESK1_WT1_TCRmimic` | Binder | T3 | Dao T et al. Sci Transl Med 2013;5:176ra33; MSKCC ESK1 antibody | 246aa |
| `MAGE-A4_TCRmimic` | Binder | T3 | Dao T et al. Sci Transl Med 2015; multiple MAGE-A4 TCR papers | 243aa |
| `Anti_FRa_MOv19_scFv` | Binder | T2 | Kandalaft LE et al. Clin Cancer Res 2012; Carpenito C et al. PNAS 2009 | 241aa |
| `Membrane_IL15` | Armored Payload | T2 | Sequence: IL-2Rα signal + IL-15 mature + IL-2Rβ transmembrane (Hurton  | 162aa |
| `Membrane_IL21` | Armored Payload | T2 | Hurton LV et al. PNAS 2016 (mbIL-21 for NK expansion); Liu E et al. NE | 170aa |
| `Secreted_IL12` | Armored Payload | T2 | Koneru M et al. PNAS 2015;112:E6526; Zhang L et al. Clin Cancer Res 20 | 330aa |
| `GPX4_Enhanced` | Armored Payload | T3 | Drijvers JM et al. Cell 2021;187:5541; Stockwell BR et al. Cell 2017;1 | 197aa |
| `PD1_CD28_CSR` | Logic Gate | T2 | Liu X et al. Cancer Res 2016;76:1578; Ankri C et al. J Immunol 2013 | 289aa |
| `CTLA4_CD28_CSR` | Logic Gate | T3 | Leen AM et al; multiple immune checkpoint switch publications | 234aa |
| `iCAR_PSMA` | Logic Gate | T3 | Fedorov VD et al. Sci Transl Med 2013;5:215ra172 | 395aa |
| `SynNotch_NRR` | Logic Gate | T3 | Morsut L et al. Cell 2016;164:780; Roybal KT et al. Cell 2016;164:770 | 182aa |
| `Gal4_VP64_TF` | Logic Gate | T3 | Morsut L et al. Cell 2016;164:780; Roybal KT et al. Cell 2016;164:770 | 201aa |
| `Dsg3_ECD_CAAR` | CAAR Binder | T3 | Ellebrecht CT et al. Science 2016;353:179; CAART (Cabaletta Bio) | 566aa |
| `MuSK_ECD_CAAR` | CAAR Binder | T3 | Ellebrecht CT et al. Science 2016 (concept); Bhatt DL et al. multiple  | 468aa |
| `EF1a_Promoter` | Regulatory Element | T1 | Standard lentiviral vector design; 1200bp | 1200aa |
| `PGK_Promoter` | Regulatory Element | T1 | Standard lentiviral vector design; 500bp | 500aa |
| `MSCV_LTR` | Regulatory Element | T1 | Standard lentiviral vector design; 590bp | 590aa |
| `SFFV_Promoter` | Regulatory Element | T2 | Standard lentiviral vector design; 560bp | 560aa |
| `EFS_Promoter` | Regulatory Element | T2 | Standard lentiviral vector design; 250bp | 250aa |
| `NFAT_RE_Promoter` | Regulatory Element | T2 | Standard lentiviral vector design; 300bp | 300aa |
| `UCOE_EF1a` | Regulatory Element | T2 | Standard lentiviral vector design; 1500bp | 1500aa |
| `Tet_On_System` | Regulatory Element | T3 | Standard lentiviral vector design; 1800bp | 1800aa |

## Comparison vs InSynBio Website Claims

| Website Category | Website Examples | V3 Coverage | Status |
|-----------------|------------------|-------------|--------|
| Binders | FMC63, Trastuzumab, 14G2a, SS1, TCR-mimic, VHH | 16 elements (1 with seq, 15 stubs) | ⚠️ Metadata complete, sequences needed |
| Hinge | CD8α Short, IgG4 Long, CD28 Medium, IgD | 5 elements (5 with seq) | ✅ Complete |
| Transmembrane | CD8α, CD28, CD4, NKG2D | 5 elements (5 with seq) | ✅ Complete |
| Co-stimulatory | 4-1BB, CD28, OX40, ICOS, 2B4, DAP12 | 7 elements (7 with seq) | ✅ Complete |
| Activation | CD3ζ, FcRγ, DAP12 | 2 elements (2 with seq) | ✅ Complete |
| Armored Payloads | TGFB_DNR, IL-15, IL-12, GPX4, 4-1BBL | 6 elements (2 with seq) | ⚠️ TGFB_DNR/4-1BBL done; cytokines stub |
| Safety Switches | tEGFR, iCasp9, RQR8, HSV-TK | 5 elements (3 with seq) | ✅ Core complete (RQR8/HSV-TK stub) |
| Logic Gates | SynNotch, iCAR, CSR-PD1 | 5 elements (0 with seq) | ⚠️ Architecture defined, sequences needed |
| Regulatory Elements | EF1α, PGK, NFAT, UCOE | 8 elements (DNA, 0 seq) | ⚠️ Metadata only (DNA sequences) |
| Leaders & Linkers | CD8α SP, G4S, P2A, T2A | 14 elements (14 with seq) | ✅ Complete |
| CAAR Constructs | Dsg3-CAAR, MuSK-CAAR | 2 elements (0 with seq) | ⚠️ Architecture defined |
| Allogeneic | TRAC KO, B2M KO (guide RNAs) | 2 elements (2 seq - gRNA) | ✅ Guide RNA sequences defined |

## Priority Fetch List (Sequences Needed)

Ordered by clinical importance:

| ID | Element | Primary Source | Tier |
|----|---------|--------------|----- |
| `c11D5_3_scFv` | BCMA scFv | Patent US20200261501A1 VH/VL sequences | T1 |
| `Trastuzumab_scFv` | HER2 scFv | US5821337 or PDB 1N8Z VH/VL | T2 |
| `Daratumumab_scFv` | CD38 scFv | Patent US9603927B2 | T2 |
| `SS1_scFv` | Mesothelin scFv | Hassan R J Immunol 2002 (NCBI) | T2 |
| `14G2a_hu_scFv` | GD2 scFv | Heczey JCI 2017 / PDB structure | T2 |
| `m971_scFv` | CD22 scFv | Haso W Blood 2013 supplementary | T2 |
| `OKT3_hu_scFv` | CD3ε scFv | Shalaby MR J Exp Med 1992 | T2 |
| `RQR8` | CD34+CD20 safety tag | Philip B Blood 2014 supplementary | T2 |
| `PD1_CD28_CSR` | Checkpoint switch | Liu X Cancer Res 2016 | T2 |
| `Membrane_IL15` | mIL-15 payload | Hurton LV PNAS 2016 supplementary | T2 |
| `SynNotch_NRR` | AND-gate logic | Morsut L Cell 2016 supplementary | T3 |

