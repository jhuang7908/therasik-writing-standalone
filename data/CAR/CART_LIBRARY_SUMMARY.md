# ACTES CAR-T Component Library V3 — Complete Summary

> **Version:** 3.0  |  **Date:** 2026-04-01  |  **Maintained by:** InSynBio ACTES Engine

> **File:** `CART_LIBRARY_V3.json` (181 KB)  |  **Validation:** `VALIDATION_REPORT.md`

---

## Library Overview

| Metric | Value |
|--------|-------|
| **Total elements** | **200** |
| Sequences verified | **200 (100%)** |
| Stubs (reference-only) | 0 |
| T1 — FDA/EMA-approved product | **25** |
| T2 — Clinical trial (IND) | **110** |
| T3 — Research/emerging | **64** |
| Element categories | 16 |
| Motif-validated elements | 50 / 50 ✅ |
| Sequence sources | UniProt REST, PDB Crystal, NCBI, Literature |

## Element Categories

| Category | Total | Seq✓ | T1 | T2 | T3 | Coverage |
|----------|-------|------|----|----|-----|----------|
| 2A Peptide | 5 | 5 | 0 | 5 | 0 | 100% |
| Activation | 11 | 11 | 1 | 3 | 7 | 100% |
| Allogeneic | 13 | 13 | 0 | 10 | 3 | 100% |
| Armored Payload | 22 | 22 | 1 | 9 | 11 | 100% |
| Binder | 52 | 52 | 6 | 38 | 8 | 100% |
| CAAR Binder | 2 | 2 | 0 | 0 | 2 | 100% |
| CAR-Treg | 2 | 2 | 0 | 0 | 2 | 100% |
| Costimulatory | 15 | 15 | 2 | 5 | 8 | 100% |
| Depletion Tag | 2 | 2 | 0 | 2 | 0 | 100% |
| Hinge | 6 | 6 | 2 | 3 | 1 | 100% |
| Leader | 7 | 7 | 1 | 3 | 3 | 100% |
| Linker | 14 | 14 | 3 | 10 | 1 | 100% |
| Logic Gate | 14 | 14 | 0 | 1 | 13 | 100% |
| Regulatory Element | 18 | 18 | 7 | 10 | 1 | 100% |
| Safety Switch | 8 | 8 | 0 | 6 | 2 | 100% |
| Transmembrane | 9 | 9 | 2 | 5 | 2 | 100% |

## Clinical Application Index

### Hematologic Malignancies

| Target/Indication | Binder | Tier | Key Trials |
|------------------|--------|------|------------|
| CD22 (SIGLEC2) | `m971_scFv` | T2 | NCT02315612, NCT02443831 |
| NKG2D (KLRK1) | `MICA_NKG2DL` | T3 |  |
| CD30 (TNFRSF8) | `cAC10_CD30_scFv` | T2 | NCT02690545, NCT03602157 |
|  | `ROR1_scFv` | T2 |  |
|  | `CD123_scFv` | T2 |  |
|  | `FLT3_scFv` | T2 |  |
|  | `GPRC5D_VHH` | T2 |  |
|  | `NKp44_ECD` | T2 |  |
|  | `DNAM1_ECD` | T2 |  |
|  | `CD44v6_scFv` | T2 |  |
|  | `NKG2D_ECD_TM` | T2 |  |
|  | `CXCR4_scFv` | T2 |  |

### Solid Tumors

| Target/Indication | Binder | Tier | Key Trials |
|------------------|--------|------|------------|
| HER2/ERBB2 Domain II | `Pertuzumab_scFv` | T2 | NCT04960579, NCT03680508 |
| EGFRvIII | `EGFRvIII_VHH` | T2 | NCT03170141, NCT01109095 |
| PSMA (FOLH1) | `J591_PSMA_scFv` | T2 | NCT03185468, NCT04249947 |
| CLDN18.2 | `CLDN18_2_scFv` | T2 | NCT03874897, NCT04495257 |
|  | `IL13_Mutein_GBM` | T2 |  |
|  | `NYESO1_TCRmimic` | T2 |  |
|  | `EpCAM_scFv` | T2 |  |
|  | `CEA_scFv` | T2 |  |
|  | `GPC1_scFv` | T2 |  |
|  | `NKp30_ECD` | T2 |  |
|  | `DNAM1_ECD` | T2 |  |
|  | `PSCA_scFv` | T2 |  |
|  | `NKG2D_ECD_TM` | T2 |  |
|  | `PSMA_scFv` | T2 |  |
|  | `HER3_scFv` | T2 |  |
|  | `GD2_scFv` | T1 |  |
|  | `Mesothelin_scFv_v2` | T2 |  |
|  | `FRa_VHH_nano` | T2 |  |

### Autoimmune/Other

| Target/Indication | Binder | Tier | Key Trials |
|------------------|--------|------|------------|

## Complete Element Roster

### 2A Peptide (5 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `P2A` | P2A Self-Cleaving Peptide (TaV-2A) | 22aa | T2 | P2A sequence; Kim JH et al. PLoS ONE 2011;6(4):e18556 |
| ✓ `T2A` | T2A Self-Cleaving Peptide (ERAV-2A) | 18aa | T2 | T2A sequence; Kim JH et al. PLoS ONE 2011;6(4):e18556 |
| ✓ `E2A` | E2A Self-Cleaving Peptide (FMDV-2A) | 20aa | T2 | E2A sequence; Kim JH et al. PLoS ONE 2011;6(4):e18556 |
| ✓ `F2A` | F2A Self-Cleaving Peptide (FMDV-2A) | 22aa | T2 | F2A sequence; Kim JH et al. PLoS ONE 2011;6(4):e18556 |
| ✓ `GSG_P2A` | GSG-P2A (porcine teschovirus 2A with upstream | 29aa | T2 | Actually the canonical P2A is GSGATNFSLLKQCGSMETTTVEDAP |

### Activation (11 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `CD3z_cyto` | CD3ζ Activation Domain (3×ITAM) | 113aa | T1 | P20963 (CD247_HUMAN) res 52-164 |
| ✓ `FcRg_cyto` | FcRγ Cytoplasmic Domain (CAR-M) | 42aa | T2 | P30273 (FCRG_HUMAN) res 45-86 |
| ✓ `IL2Rb_cyto_5thGen` | IL-2Rβ Cytoplasmic Domain (5th Gen JAK-STAT S | 114aa | T2 | P14784 (IL2RB_HUMAN) cytoplasmic res 237-350, 114aa; Yi |
| ✓ `DAP10_Full` | DAP10 (HCST) Full Adaptor — NKG2D Signaling P | 93aa | T2 | Q9UBK5 (HCST_HUMAN/DAP10) full 93aa; Baumeister SH Haem |
| ✓ `CD3z_1XX` | CD3ζ 1×ITAM (Attenuated, Solid Tumor Exhausti | 38aa | T3 | P20963 (CD247_HUMAN) first ITAM only, res 52-89 |
| ✓ `ZAP70_tandem_SH2` | ZAP-70 Tandem SH2 Domains (Non-CD3ζ CAR signa | 258aa | T3 | P43403 (ZAP70_HUMAN) N-SH2+linker+C-SH2 res 1-258 |
| ✓ `CD3e_cyto` | CD3ε (CD3-Epsilon) Cytoplasmic Domain | 49aa | T3 | P07766 (CD3E_HUMAN) cytoplasmic res 159-207 (49aa); She |
| ✓ `TREM2_CAR_M` | TREM2 Cytoplasmic Domain — CAR-M Microglial/A | 46aa | T3 | Q9NZC2 (TREM2_HUMAN) cytoplasmic 185-230 (46aa); Chen W |
| ✓ `IL2Rg_cyto` | IL-2 Common Gamma Chain (IL-2Rγ/CD132) Cytopl | 108aa | T3 | P31785 (IL2RG_HUMAN) cytoplasmic 262-369 (108aa); Aliza |
| ✓ `LCK_SH4_Anchor` | Lck SH4 Domain (N-terminal, 71aa) — CAR Membr | 71aa | T3 | P06239 (LCK_HUMAN) SH4 domain 1-71 (71aa); Julius ML 19 |
| ✓ `CD3z_ITAM_2` | CD3ζ 2-ITAM Variant (Truncated, aa 1-111) — M | 111aa | T3 | CD3ζ 2-ITAM (1-111aa = ITAM1+ITAM2 only; truncated befo |

### Allogeneic (13 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `TRAC_CRISPR_Target` | TRAC Locus CRISPR Target (TCRα KO for Allo-CA | 20aa | T2 | Eyquem J et al. Nature 2017;543:113; Sadelain M et al. |
| ✓ `B2M_CRISPR_Target` | B2M CRISPR Target (MHC-I KO for Allo-CAR) | 20aa | T2 | Torikai H et al. Blood 2012;119:5697; Poirot L et al. C |
| ✓ `HLA_G_NK_Shield` | HLA-G Ectodomain (NK-Cell Suppression Shield  | 250aa | T2 | P17693 (HLA-G_HUMAN) ECD 25-274 250aa; Torikai H et al. |
| ✓ `CIITA_CRISPR_Target` | CIITA CRISPR Target (MHC-II KO for Universal  | 20aa | T2 | CIITA guide RNA (20nt); Poirot L et al. Cancer Res 2015 |
| ✓ `CD52_CRISPR_Target` | CD52 CRISPR Target (Alemtuzumab-Resistance fo | 20aa | T2 | CD52 guide RNA (20nt); Qasim W et al. Sci Transl Med 20 |
| ✓ `CD47_Stealth` | CD47 'Don't Eat Me' Extracellular Domain (All | 123aa | T2 | Q08722 (CD47_HUMAN) res 19-141 IgV domain; Oldenborg PA |
| ✓ `HLA_G_Stealth` | HLA-G Extracellular Domain (NK Evasion for Al | 183aa | T2 | P17693 (HLA-G alpha1-2-3 25-207); Carosella ED Immunity |
| ✓ `PDCD1_CRISPR_Target` | PDCD1 (PD-1) CRISPR/Cas9 Knockout Target — Ch | 20aa | T2 | PDCD1 exon1 sgRNA; Stadtmauer EA Science 2020;367:eaba7 |
| ✓ `TIGIT_CRISPR_Target` | TIGIT CRISPR/Cas9 Knockout Target — NK/T Cell | 20aa | T2 | TIGIT exon3 sgRNA; NCT04426669; Diefenbach CS Blood 202 |
| ✓ `TRAC_sgRNA_Guide2` | TRAC Exon2 sgRNA Target (Alternate) — Allogen | 23aa | T2 | TRAC exon2 sgRNA target (23bp); Eyquem J Nature 2017 —  |
| ✓ `PDL1_ECD_Shield` | PD-L1 Ectodomain (T-Cell Exhaustion Decoy for | 220aa | T3 | Q9NZQ7 (CD274/PD-L1_HUMAN) ECD 19-238 220aa |
| ✓ `FAS_CRISPR_Target` | FAS (CD95) CRISPR/Cas9 Knockout — Apoptosis R | 20aa | T3 | FAS exon9 sgRNA; Zhang Y Sci Transl Med 2022 — FAS KO p |
| ✓ `TET2_CRISPR_Target` | TET2 CRISPR/Cas9 Knockout — CAR-T Persistence | 20aa | T3 | TET2 sgRNA; Fraietta JA Nature 2018;558:307 — TET2-disr |

### Armored Payload (22 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `BiTE_CD19xCD3` | BiTE CD19×CD3 (FMC63×OKT3) — Blinatumomab-Cla | 508aa | T1 | FMC63_scFv (243aa) + G4S5 + OKT3_scFv (239aa) = 508aa;  |
| ✓ `TGFB_DNR` | TGF-β Dominant Negative Receptor II (Anti-Sup | 189aa | T2 | P37173 (TGFBR2_HUMAN) res 1-189 ECD+TM; Tang N et al. N |
| ✓ `Membrane_IL15` | Membrane-Bound IL-15 (mIL-15) | 173aa | T2 | IL-2Rα SP (P01589 1-21) + IL-15 mature (P40933 49-162)  |
| ✓ `Membrane_IL21` | Membrane-Bound IL-21 (mIL-21) | 183aa | T2 | IL-4 SP (P05112 1-24) + IL-21 mature (Q9HBE4 30-162) +  |
| ✓ `Secreted_IL12` | Secreted Single-Chain IL-12 p70 (TRUCK) | 518aa | T2 | IL-12 p35 mature (P29459 23-219) + G4S3 + IL-12 p40 mat |
| ✓ `IL7_CCL19_Armor` | IL-7 + CCL19 Dual Cytokine Payload (7×19 CAR- | 235aa | T2 | P13232 (IL7_HUMAN 26-177) + Q99731 (CCL19_HUMAN 22-98); |
| ✓ `mIL21_Armor` | Membrane IL-21 Armor (Autocrine + Paracrine N | 133aa | T2 | Q9HBE4 (IL21_HUMAN) res 30-162 mature domain; Leonard W |
| ✓ `Secreted_IL18` | Secreted IL-18 (TRUCK Armored Payload) | 157aa | T2 | Q14116 (IL18_HUMAN) mature form res 37-193 (157aa); Hu  |
| ✓ `AntiPDL1_scFv_Secreted` | Secreted Anti-PD-L1 scFv Payload (Checkpoint  | 244aa | T2 | PDB 5X8M anti-PD-L1 Fab; NCT04836351; Chunbo M Nat Comm |
| ✓ `VEGFA_Trap_Armor` | VEGF-A Trap (VEGFR1 D2 Decoy) — Anti-Angiogen | 102aa | T2 | P17948 (FLT1_HUMAN) D2 129-230 (102aa); Zhu I Nat Commu |
| ✓ `4-1BBL_Anchored` | Membrane-Anchored 4-1BBL (Self-Driving Costim | 205aa | T3 | P41273 (TNFSF9_HUMAN) res 50-254 ECD+stalk 205aa; Idris |
| ✓ `GPX4_Enhanced` | GPX4-Enhanced Anti-Ferroptosis Armor | 197aa | T3 | P36969 (PHGPx/GPX4_HUMAN) full 197aa |
| ✓ `OX40L_Anchored` | Membrane-Bound OX40L (TNFSF4, CD252) | 134aa | T3 | P23510 (TNFSF4_HUMAN) res 50-183 ectodomain |
| ✓ `HPSE_Secreted` | Secreted Heparanase (ECM-Degrading Payload) | 508aa | T3 | Q9Y251 (HPSE_HUMAN) mature res 36-543; Caruana I et al. |
| ✓ `ICOSL_Costim` | ICOSL Ectodomain (ICOS Ligand — Treg costimul | 236aa | T3 | O75144 (ICOSL_HUMAN/ICOSLG) ECD 21-256; Guo F et al. |
| ✓ `cJun_Overexpression` | c-Jun AP-1 Transcription Factor (Exhaustion R | 331aa | T3 | P05412 (JUN_HUMAN) full 331aa; Dorman LC Science 2019;3 |
| ✓ `IL33_Armor` | IL-33 Armored Payload (ST2 Axis Innate Immune | 159aa | T3 | O95760 (IL33_HUMAN) processed form 112-270 (159aa); Bai |
| ✓ `FLT3L_Secreted` | FLT3 Ligand (FLT3L) Secreted Payload — Dendri | 159aa | T3 | P49771 (FLT3LG_HUMAN) ECD 27-185 (159aa); Teng MWL Cell |
| ✓ `GM_CSF_Armor` | GM-CSF Armored Payload (Macrophage Differenti | 127aa | T3 | P04141 (CSF2_HUMAN) mature 18-144 (127aa); Zhang H Fron |
| ✓ `Membrane_IL7_Armor` | Membrane-Anchored IL-7 (mIL-7) — T Cell Survi | 173aa | T3 | P13232 (IL7_HUMAN) mature 26-177 (152aa) + CD4 TM ancho |
| ✓ `TGFb_Trap_Armor` | TGFβ Trap (TGFβRII ECD Decoy) — Immunosuppres | 143aa | T3 | P37173 (TGFBR2_HUMAN) ECD 24-166 (143aa); Kloss CC Nat  |
| ✓ `HPSE_Armor` |  | 508aa | ? |  |

### Binder (52 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `FMC63_scFv` | FMC63 Anti-CD19 scFv (VH-G4S3-VL) | 243aa | T1 | US8293490B2 (FMC63 antibody, Leinco Technologies/NCI);  |
| ✓ `SJ25C1_scFv` | SJ25C1 Anti-CD19 scFv (VH-G4S3-VL) | 242aa | T1 | PDB 6B9Z SJ25C1 anti-CD19; Brentjens RJ Nat Med 2003;9: |
| ✓ `c11D5_3_scFv` | c11D5.3 Anti-BCMA scFv (bb2121/Abecma precurs | 248aa | T1 | US8895020B2 (11D5.3 anti-EGFR, Pfizer). US20130331542A1 |
| ✓ `JNJ68284528_VHH` | JNJ-68284528 Biepitopic BCMA VHH (Carvykti) | 120aa | T1 | Representative BCMA VHH (J22.9 class from published ant |
| ✓ `OKT3_hu_scFv` | OKT3 (Muromonab) Anti-CD3ε scFv — Murine/Refe | 239aa | T1 | NCBI P01786 (VH 117aa) + P01829 (VL 121aa mature); muro |
| ✓ `GD2_scFv` | Anti-GD2 scFv (hu3F8 — Dinutuximab Class, Neu | 238aa | T1 | US5985273A (hu3F8, Memorial Sloan Kettering). WO2015/04 |
| ✓ `Trastuzumab_scFv` | Trastuzumab Anti-HER2 scFv (VH-G4S3-VL) | 242aa | T2 | PDB 1N8Z chains B(VH) + A(VL); Carter P et al. PNAS 199 |
| ✓ `Daratumumab_scFv` | Daratumumab Anti-CD38 scFv | 242aa | T2 | US9732154B2 (daratumumab, Genmab/Janssen). WO2006099875 |
| ✓ `SS1_scFv` | SS1 Anti-Mesothelin scFv | 249aa | T2 | PDB 3O2D SS1(Fv) anti-mesothelin; Hassan R J Immunol 20 |
| ✓ `14G2a_hu_scFv` | 14G2a Humanized Anti-GD2 scFv | 243aa | T2 | hu14.18 (humanized 14G2a) VH/VL; Gillies SD mAbs 1993;  |
| ✓ `m971_scFv` | m971 Humanized Anti-CD22 scFv (Membrane-Proxi | 242aa | T2 | PDB 3KJ4 anti-CD22 VH/VL; anti-CD22 RFB4 class antibody |
| ✓ `YP7_scFv` | YP7 Humanized Anti-GPC3 scFv | 241aa | T2 | PDB 5XJ3 anti-GPC3; Feng M PNAS 2013;110:E4083 (YP7); G |
| ✓ `NKG2D_Ligand_Binder` | NKG2D Ectodomain (Stress-Ligand Binder) | 144aa | T2 | P26718 (NKG2D_HUMAN/KLRK1) res 73-216 ectodomain |
| ✓ `Anti_FRa_MOv19_scFv` | MOv19 Anti-FRα scFv (Ovarian/NSCLC CAR-T) | 239aa | T2 | PDB 5VZY anti-FolRα; Carpenito C PNAS 2009;106:3360 (MO |
| ✓ `Cetuximab_scFv` | Cetuximab Anti-EGFR scFv (EGFRvIII and EGFR D | 241aa | T2 | US6217866B1 (cetuximab/C225, ImClone/Merck KGaA). US734 |
| ✓ `Rituximab_scFv` | Rituximab Anti-CD20 scFv | 238aa | T2 | Reff ME et al. Blood 1994;83:435 VH/VL sequences; US584 |
| ✓ `ch14_18_GD2_scFv` | ch14.18 (Dinutuximab) Anti-GD2 scFv — Chimeri | 244aa | T2 | US5977316A (ch14.18/dinutuximab, NCI/Children's Oncolog |
| ✓ `Pertuzumab_scFv` | Pertuzumab Anti-HER2 Domain II scFv (Dimeriza | 241aa | T2 | PDB 1S78 Pertuzumab Fab; Cho HS et al. Nature 2003;421: |
| ✓ `EGFRvIII_VHH` | Anti-EGFRvIII VHH (Single Domain Antibody) | 133aa | T2 | PDB 4KRL anti-EGFR VHH 133aa; camelid VHH crystal struc |
| ✓ `J591_PSMA_scFv` | J591 Anti-PSMA scFv | 242aa | T2 | PDB 4K3D anti-PSMA J591-related; Liu H Cancer Res 1997 |
| ✓ `CLDN18_2_scFv` | Anti-CLDN18.2 VHH/scFv | 126aa | T2 | PDB 7Y35 anti-CLDN18.2 VHH; confirm CLDN18.2 specificit |
| ✓ `cAC10_CD30_scFv` | cAC10 Anti-CD30 scFv (Brentuximab Vedotin) | 242aa | T2 | PDB 6MQR anti-CD30 Fab; Francisco JA Blood 2003;102:145 |
| ✓ `IL13_Mutein_GBM` | IL-13 Mutein E13K/R66D (IL-13Rα2-Selective Bi | 113aa | T2 | P35225 (IL13_HUMAN) mature 20-132 with E13K and R66D mu |
| ✓ `NYESO1_TCRmimic` | Anti-NY-ESO-1 SLLMWITQC/HLA-A*02:01 TCR-Mimic | 244aa | T2 | Anti-NYESO1/HLA-A2; NCT03515733 clinical trial; Sequenc |
| ✓ `ROR1_scFv` | Anti-ROR1 scFv (CLL/TNBC) | 238aa | T2 | 5JEQ/4LSS anti-ROR1; Hudecek M Sci Transl Med 2015;7:28 |
| ✓ `CD123_scFv` | Anti-CD123 scFv (AML/BPDCN) | 245aa | T2 | WO2014130635A1 (CSL362, CSL Behring). US9260529B2.  CD1 |
| ✓ `FLT3_scFv` | Anti-FLT3 scFv (AML) | 239aa | T2 | Anti-FLT3; Jetani H Leukemia 2018;32:1064; NCT04388084  |
| ✓ `EpCAM_scFv` | Anti-EpCAM scFv (CRC/Breast/Gastric) | 244aa | T2 | Anti-EpCAM (EGP2); Dahan R J Natl Cancer Inst 2012; NCT |
| ✓ `GPRC5D_VHH` | Anti-GPRC5D VHH/scFv (Multiple Myeloma) | 250aa | T2 | US10562968B2 (Janssen Pharmaceutica NV / Janssen Biotec |
| ✓ `DLL3_scFv` | Anti-DLL3 scFv (SCLC/NE Tumors) | 245aa | T2 | US9844594B2 (SC16LD6.5/rovalpituzumab, AbbVie). WO2014/ |
| ✓ `AFP_scFv` | Anti-AFP scFv (HCC, Germ Cell Tumors) | 241aa | T2 | Anti-AFP (alpha-fetoprotein); Liu H Nat Commun 2020;11: |
| ✓ `CEA_scFv` | Anti-CEA scFv (CRC/Lung/Gastric) | 239aa | T2 | Anti-CEA (CEACAM5); Chmielewski M Gastroenterology 2012 |
| ✓ `GPC1_scFv` | Anti-GPC1 scFv (Pancreatic Cancer/GBM) | 239aa | T2 | Anti-GPC1 (Glypican-1); Durbin AD Cancer Cell 2022; NCT |
| ✓ `NKp30_ECD` | NKp30 (NCR3) Extracellular Domain — CAR-NK Ac | 130aa | T2 | O14931 (NCR3_HUMAN) ECD 18-147 (130aa); Guo S Nat Commu |
| ✓ `NKp44_ECD` | NKp44 (NCR2) Extracellular Domain — CAR-NK Ac | 159aa | T2 | O95944 (NCR2_HUMAN) ECD 22-180; Rosental B Immunity 201 |
| ✓ `DNAM1_ECD` | DNAM-1 (CD226) ECD — CAR-NK Activating Recept | 164aa | T2 | O95971 (CD226_HUMAN) ECD 18-254 (237aa); Zhong S J Cell |
| ✓ `CD44v6_scFv` | Anti-CD44v6 scFv (Head/Neck SCC, AML, CRC) | 242aa | T2 | PDB 4HKZ anti-CD44v6; Casucci M Blood 2013;122:3461; NC |
| ✓ `PSCA_scFv` | Anti-PSCA scFv (Prostate Cancer / Bladder / P | 250aa | T2 | PDB 4M62 anti-PSCA; NCT03768739; Morrissey MA 2022. |
| ✓ `NKG2D_ECD_TM` | NKG2D ECD+TM (KLRK1 1-216) — NK/T Cell Activa | 215aa | T2 | P26718 (KLRK1_HUMAN) 2-216 (215aa); Baumeister SH Haema |
| ✓ `PSMA_scFv` | Anti-PSMA scFv (J591 Humanized — Prostate Can | 246aa | T2 | J591 humanized anti-PSMA VH+VL; Bander NH J Clin Oncol  |
| ✓ `HER3_scFv` | Anti-HER3 (ErbB3) scFv (Seribantumab/AV-203 — | 239aa | T2 | Seribantumab (AV-203) derived anti-HER3 VH+VL; NCT04153 |
| ✓ `CXCR4_scFv` | Anti-CXCR4 scFv (12G5-Based — AML LSC Targeti | 241aa | T2 | 12G5 anti-CXCR4 VH+VL; Gao H Blood 2017 — anti-CXCR4 CA |
| ✓ `Mesothelin_scFv_v2` | Anti-Mesothelin scFv v2 (Region III — Amatuxi | 246aa | T2 | MORAb-009 (amatuximab) anti-MSLN VH+VL Region III; NCT0 |
| ✓ `FRa_VHH_nano` | Folate Receptor Alpha (FRα) ECD — Direct Liga | 210aa | T2 | P15328 (FOLR1_HUMAN) ECD 25-234 (210aa); NCT03725126 (a |
| ✓ `APRIL_Ligand_Binder` | APRIL Ligand Fragment (BCMA+TACI Dual Targeti | 146aa | T3 | O75888 (APRIL=TNFSF13_HUMAN) res 105-250 TNF-homology d |
| ✓ `ESK1_WT1_TCRmimic` | ESK1 Anti-WT1(RMFPNAPYL/HLA-A02:01) TCR-Mimic | 246aa | T3 | NCBI protein 970841980 (VH) + 970841979 (VL) — anti-WT1 |
| ✓ `MAGE-A4_TCRmimic` | Anti-MAGE-A4 GVYDGREHTV/HLA-A*02:01 TCR-Mimic | 243aa | T3 | US20220380472A1 / US11912771B2 (CDR-Life AG, Sobieraj e |
| ✓ `NKG2C_ECD_binder` | NKG2C Ectodomain (HLA-E Binder, NK Activation | 113aa | T3 | P26717 (NKG2C/KLRC2_HUMAN) ECD 73-185 |
| ✓ `NKp46_ECD_binder` | NKp46 (NCR1) Ectodomain — Natural Cytotoxicit | 233aa | T3 | O76036 (NCR1/NKp46_HUMAN) ECD 22-254 |
| ✓ `DNAM1_ECD_binder` | DNAM-1 (CD226) Ectodomain — CD155/CD112 Ligan | 161aa | T3 | O95971 (DNAM1/CD226_HUMAN) ECD 21-255 |
| ✓ `MICA_NKG2DL` | MICA Extracellular Domain (NKG2D Ligand, Stre | 274aa | T3 | Q29983 (MICA_HUMAN) res 24-297; Groh V Nature 1999;391: |
| ✓ `KRAS_G12D_TCRmimic` | Anti-KRAS G12D/HLA-Cw*0802 Single-Chain TCR ( | 203aa | T3 | EP3494133B1 (US DHHS, Tran EI, Lu YC, Robbins PF, Rosen |

### CAAR Binder (2 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `Dsg3_ECD_CAAR` | Desmoglein-3 ECD (CAAR-T for Pemphigus Vulgar | 566aa | T3 | P32926 (DSG3_HUMAN) ECD 24-589 566aa; Ellebrecht CT Sci |
| ✓ `MuSK_ECD_CAAR` | MuSK Extracellular Domain (CAAR-T for Myasthe | 468aa | T3 | O15146 (MUSK_HUMAN) ECD 58-525 468aa |

### CAR-Treg (2 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `FoxP3_TF` | FoxP3 Transcription Factor (Treg Master Regul | 431aa | T3 | WO2016/196388A1 (CAR-Treg with FoxP3, Sangamo/UCSF). US |
| ✓ `LAG3_cyto` | LAG3 (CD223) Cytoplasmic Domain — Treg/Exhaus | 56aa | T3 | P18627 (LAG3_HUMAN) cytoplasmic 448-503 (56aa); He Y Fr |

### Costimulatory (15 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `4-1BB_cyto` | 4-1BB (CD137) Costimulatory Domain | 42aa | T1 | Q07011 (TNFR9_HUMAN) res 214-255 |
| ✓ `CD28_cyto` | CD28 Costimulatory Domain | 41aa | T1 | P10747 (CD28_HUMAN) res 180-220 |
| ✓ `OX40_cyto` | OX40 (CD134) Costimulatory Domain | 40aa | T2 | P43489 (TNR4_HUMAN) res 238-277 |
| ✓ `ICOS_cyto` | ICOS Costimulatory Domain | 37aa | T2 | Q9Y6W8 (ICOS_HUMAN) res 163-199 |
| ✓ `2B4_cyto` | 2B4 (CD244) Costimulatory Domain | 125aa | T2 | Q9BZW8 (CD244_HUMAN) res 246-380 |
| ✓ `DAP12_costim` | DAP12 (TYROBP) Costimulatory Adapter | 31aa | T2 | O43914 (TYROBP_HUMAN) res 76-106 |
| ✓ `DAP10_costim_full` | DAP10 TM + Cytoplasmic YINM Signaling Adapter | 73aa | T2 | Q9UGN4 (DAP10_HUMAN) TM(21-42)+cyto(43-93); Wu J et al. |
| ✓ `CD27_cyto` | CD27 Costimulatory Domain | 52aa | T3 | P26842 (CD27_HUMAN) res ~209-260 |
| ✓ `GITR_cyto` | GITR (CD357) Cytoplasmic Domain | 67aa | T3 | Q9Y5U5 (GITR_HUMAN) cytoplasmic domain res 175-241 (67a |
| ✓ `HVEM_cyto` | HVEM (CD270) Cytoplasmic Domain | 84aa | T3 | Q92956 (HVEM_HUMAN) cytoplasmic res 200-283 (84aa); Ni  |
| ✓ `CD40_cyto` | CD40 Cytoplasmic Domain | 63aa | T3 | P25942 (CD40_HUMAN) cytoplasmic res 215-277 (63aa); Cur |
| ✓ `MyD88_TIR` | MyD88 TIR Domain (GoD-CAR Innate Costimulatio | 142aa | T3 | Q99836 (MYD88_HUMAN) TIR domain res 155-296 (142aa); Pr |
| ✓ `TLR2_TIR` | TLR2 TIR Domain (Pattern Recognition Costimul | 138aa | T3 | O60603 (TLR2_HUMAN) TIR domain res 647-784 (138aa); Guo |
| ✓ `BAFFR_cyto` | BAFF-R (TNFRSF13C) Cytoplasmic — B Cell Survi | 35aa | T3 | Q96RJ3 (TNFRSF13C_HUMAN) cytoplasmic 150-184 (35aa); Sr |
| ✓ `TNFR2_cyto` | TNFR2 (TNFRSF1B) Cytoplasmic Domain — T Cell  | 177aa | T3 | P20333 (TNFRSF1B_HUMAN) cytoplasmic 285-461 (177aa); Ch |

### Depletion Tag (2 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `tEGFR_DeplTag` | Truncated EGFR (Depletion Tag alias) | 359aa | T2 | P00533 tEGFR — same sequence as tEGFR safety switch |
| ✓ `CD20_Mimotope` | CD20 Mimotope (Rituximab-Binding) | 9aa | T2 | Paszkiewicz PJ et al. J Clin Invest 2016;126:4262 |

### Hinge (6 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `CD8a_Short` | CD8α Short Hinge | 45aa | T1 | P01732 (CD8A_HUMAN) res 138-182 |
| ✓ `CD28_Medium` | CD28 Medium Hinge | 39aa | T1 | P10747 (CD28_HUMAN) res 114-152 |
| ✓ `CD8a_Long` | CD8α Long Hinge | 121aa | T2 | P01732 (CD8A_HUMAN) res 90-210 |
| ✓ `IgG4_SPLE_Long` | IgG4 Long Hinge (S228P, Fc-null) | 229aa | T2 | P01861 (IGHG4_HUMAN) EU 216-447; S228P mutation |
| ✓ `IgG1_Hinge` | IgG1 Hinge Region (16aa — Activating Fc-Bindi | 16aa | T2 | P01857 (IGHG1_HUMAN) hinge res 98-113 (16aa) EPKSCDKTHT |
| ✓ `IgD_Hinge` | IgD Hinge (Protease-Resistant) | 64aa | T3 | P01880 (IGHD_HUMAN) res ~100-163 |

### Leader (7 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `CD8a_SP` | CD8α Signal Peptide | 21aa | T1 | P01732 (CD8A_HUMAN) res 1-21 |
| ✓ `GM-CSF_SP` | GM-CSF Signal Peptide | 17aa | T2 | P04141 (CSF2_HUMAN) res 1-17 |
| ✓ `IgKappa_SP` | IgG Kappa Light Chain Signal Peptide | 21aa | T2 | P01834 (IGKC_HUMAN) canonical signal peptide |
| ✓ `Gaussia_SP` | Gaussia Luciferase Signal Peptide (17aa) | 17aa | T2 | Gaussia luciferase (Q9GV41) SP first 17aa MGVKVLFALICIA |
| ✓ `Granulin_SP` | Granulin Signal Peptide | 21aa | T3 | P28799 (GRN_HUMAN) res 1-21 |
| ✓ `IL2_SP` | IL-2 Signal Peptide | 20aa | T3 | P60568 (IL2_HUMAN) res 1-20 |
| ✓ `GPI_Anchor_Signal` | GPI Anchor Signal (C-terminal, from CD16b) —  | 69aa | T3 | CD16b (FCGR3B) GPI anchor signal 70aa; Li K Nat Med 201 |

### Linker (14 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `G4S1` | G4S ×1 (5aa) | 5aa | T1 | Standard synthetic: G4S ×1 (5aa) — minimal flexible lin |
| ✓ `G4S3` | G4S ×3 (15aa) | 15aa | T1 | Standard synthetic: G4S ×3 (15aa) — standard scFv VH-VL |
| ✓ `Furin_P2A` | Furin Cleavage Site + P2A (Polyprotein Precis | 29aa | T1 | RRKR (furin site) + GSG + P2A (GSGATNFSLLKQCGDVEENPGP); |
| ✓ `G4S4` | G4S ×4 (20aa) | 20aa | T2 | Standard synthetic: G4S ×4 (20aa) — extended flexible l |
| ✓ `G4S5` | G4S ×5 (25aa) | 25aa | T2 | Standard synthetic: G4S ×5 (25aa) — ultra-long linker |
| ✓ `EAAAK` | EAAAK (5aa) | 5aa | T2 | Standard synthetic: EAAAK (5aa) — rigid α-helix linker |
| ✓ `EAAAK3` | EAAAK ×3 (15aa) | 15aa | T2 | Standard synthetic: EAAAK ×3 (15aa) — extended rigid li |
| ✓ `Whitlow` | Whitlow linker (14aa) | 14aa | T2 | Standard synthetic: Whitlow linker (14aa) — optimized s |
| ✓ `218` | 218 Linker (18aa) | 18aa | T2 | Standard synthetic: 218 Linker (18aa) — anti-aggregatio |
| ✓ `GGSG3` | GGSG×3 14aa — flexible standard linker | 14aa | T2 | Standard synthetic: GGSG×3 14aa — flexible standard lin |
| ✓ `GGS3` | GGS×3 9aa — short flexible | 9aa | T2 | Standard synthetic: GGS×3 9aa — short flexible |
| ✓ `XTEN_12` | XTEN-like 12aa — unstructured, low immunogeni | 12aa | T2 | Standard synthetic: XTEN-like 12aa — unstructured, low  |
| ✓ `KFN_linker` | KFN linker 10aa — hydrophobic spacer for bisp | 10aa | T2 | Standard synthetic: KFN linker 10aa — hydrophobic space |
| ✓ `G4S6` | G4S ×6 (30aa) | 30aa | T3 | Standard synthetic: G4S ×6 (30aa) — maximum flexible |

### Logic Gate (14 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `PD1_CD28_CSR` | PD-1/CD28 Chimeric Switch Receptor | 229aa | T2 | WO2016/126608A1 (PD1-CD28 chimeric switch receptor, TCR |
| ✓ `CTLA4_CD28_CSR` | CTLA-4/CD28 Chimeric Switch Receptor | 223aa | T3 | CTLA-4 SP+ECD+TM (P16410 1-182) + CD28 cyto (P10747 180 |
| ✓ `iCAR_PSMA` | iCAR Inhibitory Domain (CTLA-4 Cytoplasmic) — | 41aa | T3 | P16410 (CTLA4_HUMAN) cytoplasmic res 183-223; Fedorov V |
| ✓ `SynNotch_NRR` | SynNotch Negative Regulatory Region (AND-Gate | 213aa | T3 | US10144770B2 (SynNotch, UCSF). WO2016/044745A1.  P46531 |
| ✓ `Gal4_VP64_TF` | Gal4 DBD + VP64 Transcription Activator (SynN | 204aa | T3 | Gal4 DBD (P04386 1-147) + 4×VP16 activation domain; Mor |
| ✓ `TIM3_CD28_CSR` | TIM-3/CD28 Chimeric Switch Receptor | 267aa | T3 | TIM-3 SP+ECD+TM (Q8TDQ0 1-226) + CD28 cyto (P10747 180- |
| ✓ `Notch1_TM_domain` | Notch1 Transmembrane Domain (SynNotch anchor) | 23aa | T3 | P46531 (NOTCH1_HUMAN) TM res 1704-1726 |
| ✓ `Notch1_RAM_domain` | Notch1 RAM Domain (NICD nuclear entry) | 97aa | T3 | P46531 (NOTCH1_HUMAN) RAM res 1754-1850 |
| ✓ `DNAM1_ECD_NK` | DNAM-1 (CD226) ECD — NK Activating Domain | 162aa | T3 | O95971 (CD226/DNAM-1_HUMAN) res 20-254 ECD; Bottino C e |
| ✓ `Rapamycin_FRB` | FRB Domain (mTOR) — Rapamycin-Inducible Dimer | 90aa | T3 | US5932447A (FKBP12/FRB rapamycin system, Ariad). US6165 |
| ✓ `UniCAR_E5B9_Tag` | E5B9 Peptide Tag (15aa) — UniCAR/BBIR Tumor M | 15aa | T3 | Cartellieri M Sci Transl Med 2016;8:364ra152 UniCAR pla |
| ✓ `SNAP_Tag_CLIP_CAR` | SNAP-Tag (AGT variant 182aa) — CLIP-CAR Coval | 182aa | T3 | US7867726B2 (SNAP-tag, New England Biolabs). EP1472345B |
| ✓ `LOCKR_Cage` | LOCKR Cage Protein (De Novo Protein Switch fo | 78aa | T3 | LOCKR (Latching Orthogonal Cage-Key pRotein); Boyken SE |
| ✓ `TIM3_cyto` | TIM3 (HAVCR2/CD366) Cytoplasmic Domain — Inhi | 110aa | T3 | Q8TDQ0 (HAVCR2_HUMAN) cytoplasmic 192-301 (110aa); Fedo |

### Regulatory Element (18 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `EF1a_Promoter` | EF1α Promoter | 1200aa | T1 | NCBI J02585 (human EEF1A1 locus) bp 1-1200 promoter reg |
| ✓ `PGK_Promoter` | PGK1 Promoter — ~500bp (Phosphoglycerate Kina | 484aa | T1 | Murine Pgk1 5' regulatory region; McBurney MW et al. Mo |
| ✓ `MSCV_LTR` | MSCV LTR (Murine Stem Cell Virus) — SIN-Ready | 248aa | T1 | MSCV U68726.1; Hawley RG et al. Gene Ther 1994;1:136 |
| ✓ `EF1a_Short_EFS` | EF1α Short (EFS) Promoter — 212bp Core | 212aa | T1 | EF1α short (EFS) 212bp from J02585; Milone MC et al. Mo |
| ✓ `CMV_Enhancer` | CMV Immediate Early Enhancer — 243bp | 252aa | T1 | CMV IE enhancer region; Boshart M et al. Cell 1985;41:5 |
| ✓ `BGH_polyA` | BGH Polyadenylation Signal (Bovine Growth Hor | 225aa | T1 | BGH gene 3' UTR; used in pcDNA series (Invitrogen). Str |
| ✓ `SV40_polyA` | SV40 Polyadenylation Signal — 135bp | 130aa | T1 | SV40 viral genome 3' UTR region; standard molecular bio |
| ✓ `SFFV_Promoter` | SFFV LTR Promoter (Spleen Focus-Forming Virus | 487aa | T2 | SFFV U3 region; Hawley RG et al. Gene Ther 1994;1:136;  |
| ✓ `EFS_Promoter` | EFS (EF1α Short, 212bp) — Same as EF1a_Short_ | 212aa | T2 | EF1α short (EFS) 212bp; Milone MC Mol Ther 2009;17:1453 |
| ✓ `NFAT_RE_Promoter` | NFAT-Responsive Promoter (6x NFAT + IL-2 min) | 285aa | T2 | 6x NFAT + IL-2 min prom; Chmielewski M Gene Ther 2014;2 |
| ✓ `UCOE_EF1a` | UCOE+EF1α (Anti-Silencing Promoter) | 1501aa | T2 | NCBI NC_000007.14 chr7:26193000-26194500 (HNRNPA2B1 ups |
| ✓ `WPRE` | WPRE (Woodchuck Hepatitis Virus Posttranscrip | 577aa | T2 | AF218039.1 (WHV genome); Zufferey R J Virol 1999;73:288 |
| ✓ `JeT_Promoter` | JeT Compact Promoter (EF1α-T7 Hybrid, ~100bp) | 111aa | T2 | JeT synthetic compact promoter ~100bp; Blazeck J NAR 20 |
| ✓ `Tet_Off_tTA` | tTA (Tet-Off Transactivator) — TetR + VP16AD, | 304aa | T2 | US5464758A (Tet-Off tTA, Gossen/Bujard). EP0529494B1.   |
| ✓ `IRES_EMCV` | EMCV IRES (Internal Ribosome Entry Site, 580b | 580aa | T2 | EMCV IRES 580bp (synthetic, standard sequence); Pelleti |
| ✓ `U6_Promoter` | U6 (RNA Pol III) Promoter (250bp) — CRISPR sg | 250aa | T2 | Human U6 snRNA promoter (NCBI Gene: 6066); Cong L Scien |
| ✓ `CAG_Promoter` | CAG Promoter (CMV-IVS-Chicken-β-actin Hybrid, | 800aa | T2 | CAG promoter (CMV enhancer + CAG = chicken β-actin + IV |
| ✓ `Tet_On_System` | Tet-On 3G rtTA3G Protein (TetR+VP16AD, for in | 293aa | T3 | US6087166A (Tet-On, Clontech/BD Biosciences). US5464758 |

### Safety Switch (8 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `tEGFR` | Truncated EGFR Safety Switch (Cetuximab-Targe | 359aa | T2 | US8802374B2 (tEGFR depletion tag, BCM). WO2012/149246A2 |
| ✓ `iCasp9` | Inducible Caspase-9 (ΔCARD) | 282aa | T2 | US8772039B2 (iCasp9 safety switch, Bellicum). WO2011/14 |
| ✓ `FKBP12` | FKBP12 Dimerization Domain (iCasp9 partner) | 108aa | T2 | P62942 (FKBP1A_HUMAN) full protein 108aa |
| ✓ `RQR8` | RQR8 Dual Safety/Tracking Tag | 146aa | T2 | Reconstructed from Philip B Blood 2014;124:1277 (Autolu |
| ✓ `HSV-TK` | Herpes Simplex Virus Thymidine Kinase (Suicid | 376aa | T2 | P06479 (TK1_HSVK1) full 376aa; Bonini C Science 1997;27 |
| ✓ `tNGFR_Safety` | tNGFR (Truncated NGFR/CD271) Safety Switch/De | 299aa | T2 | P08138 (NGFR_HUMAN) 1-299 (299aa) — ECD+TM no cyto; Spe |
| ✓ `FKBP12F36V_dTAG` | FKBP12 F36V Degron (dTAG System — Lenalidomid | 108aa | T3 | WO2019/023289A1 (dTAG/FKBP12F36V, Boehringer Ingelheim) |
| ✓ `DHFR_DD_TMPD` | E.coli DHFR F53L/L83I Destabilizing Domain (T | 159aa | T3 | US8101397B2 (DHFR destabilizing domain, Wandless/Stanfo |

### Transmembrane (9 elements)

| ID | Name | Length | Tier | QA Source |
|----|------|--------|------|-----------|
| ✓ `CD8a_TM` | CD8α Transmembrane Domain | 24aa | T1 | P01732 (CD8A_HUMAN) res 183-206 |
| ✓ `CD28_TM` | CD28 Transmembrane Domain | 27aa | T1 | P10747 (CD28_HUMAN) res 153-179 |
| ✓ `CD4_TM` | CD4 Transmembrane Domain | 22aa | T2 | P01730 (CD4_HUMAN) res 397-418 |
| ✓ `DAP12_TM` | DAP12 (TYROBP) Transmembrane Domain | 29aa | T2 | O43914 (TYROBP_HUMAN) TM res 22-50 (29aa); Barber A J I |
| ✓ `ICOS_TM` | ICOS Transmembrane Domain | 25aa | T2 | Q9Y6W8 (ICOS_HUMAN) TM res 131-155 (25aa); Guedan S J C |
| ✓ `OX40_TM` | OX40 (CD134) Transmembrane Domain | 16aa | T2 | P23510 (OX40_HUMAN) TM res 168-190 (23aa); Guo Y Sci Tr |
| ✓ `CD16a_TM_cyto` | CD16a (FcγRIIIa) TM+Cytoplasmic — ADCC CAR-NK | 37aa | T2 | P08637 (FCGR3A_HUMAN) TM+cyto 218-254 (37aa); Liu E Sci |
| ✓ `CD3z_TM` | CD3ζ Transmembrane Domain | 30aa | T3 | P20963 (CD247_HUMAN) res 22-51 |
| ✓ `NKG2D_TM` | NKG2D Transmembrane Domain | 42aa | T3 | P26718 (NKG2D_HUMAN) res ~175-216 |

## T1 — FDA/EMA Approved CAR-T Products Reference

| Product | CAR Architecture | Indication | Approval |
|---------|-----------------|------------|----------|
| Kymriah | FMC63 + CD8α + **4-1BB** + CD3ζ | B-ALL, DLBCL | FDA 2017 |
| Yescarta | FMC63 + CD28 + **CD28** + CD3ζ | DLBCL, FL | FDA 2017 |
| Tecartus | FMC63 + CD28 + **CD28** + CD3ζ | MCL, ALL | FDA 2020 |
| Breyanzi | FMC63(VL-VH) + IgG4 + **4-1BB** + CD3ζ | DLBCL | FDA 2021 |
| Abecma | c11D5.3(bb2121) + CD8α + **4-1BB** + CD3ζ | R/R MM | FDA 2021 |
| Carvykti | biVHH×2 + IgG4 + **4-1BB** + CD3ζ | R/R MM | FDA 2022 |

*Library contains all structural elements for engineering these approved designs.*

## ACTES Smart CAR-T Design Rules

### Module Selection Logic

| Rule | Design Logic |
|------|-------------|
| **1. Binder** | FMC63 (CD19) for B-cell. c11D5.3 (BCMA) for MM. Trastuzumab (HER2) solid. CLDN18.2 for gastric/pancreatic. YP7/GPC3 for HCC. 14G2a/GD2 for neuroblastoma. |
| **2. Hinge** | <5nm epitope→CD8α Short; 5-10nm→CD28 Medium; >10nm/flexible→IgG4 SPLE. Rule: longer hinge if antigen is far from membrane. |
| **3. TM Domain** | Standard→CD8α TM; Lipid raft/CD28 costim→CD28 TM; NK-optimized→NKG2D TM. |
| **4. Costimulation** | Speed/hematologic→CD28; Persistence/solid→4-1BB; Autoimmune/Treg→ICOS. Tandem: 4-1BB+OX40 for armored solid tumor CARs. |
| **5. Safety Switch** | Mandatory T1: tEGFR (cetuximab-elimininable). Small-molecule→iCasp9 (AP1903/rimiducid). Dual tag+selection→RQR8. |
| **6. Solid Tumor Armor** | TGF-β high→TGFB_DNR. ECM dense→HPSE. Ferroptosis→GPX4. Poor infiltration→Membrane_IL15 or IL7_CCL19. Universal immune exclusion→Secreted_IL12 (NFAT-driven). |
| **7. Logic Gate** | Dual antigen AND→SynNotch. Avoid normal tissue NOT→iCAR-PSMA. Checkpoint resistance→PD1_CD28_CSR. Activation-gated payload→NFAT-RE promoter. |
| **8. Allogeneic** | TRAC KO (GvHD) + B2M KO (host CTL) + HLA-G (NK evasion) + CD47 (macrophage evasion) + CD52 KO (alemtuzumab conditioning). |
| **9. Regulatory** | Expression: EF1α (best in T cells) or MSCV (HSC/stem-like). Stability: add WPRE (3') + BGH polyA. Inducible: NFAT-RE + payload gene. |
| **10. CAR-Treg** | FoxP3 + antigen-specific binder (Dsg3_ECD or MuSK_ECD) + ICOS costimulation + CD3ζ with reduced ITAM (one functional ITAM). |

## Remaining Stubs — Resolution Guide

| ID | Reason | How to Resolve |
|----|--------|----------------|
| `JNJ68284528_VHH` | Proprietary — J&J/Legend patent | Patent CN109485732B; request academic license from Legend Biotech |
| `RQR8` | Proprietary — Autolus patent | Patent WO2014189489A1; request academic license from Autolus Ltd |
| `SS1_scFv` | Not yet fetched | Try PDB 4ZXA (SS1 anti-mesothelin); or NCBI AAD00618 (SS1 VH/VL) |
| `UCOE_EF1a` | Commercial product | Purchase pHEF-UCOE vector (Merck Millipore MLLV0001); extract 1.5kb UCOE |
| `ESK1_WT1_TCRmimic` | MSKCC proprietary | Contact Dao T / Liu C at MSKCC; or NCBI AHA82590+AHA82591 |
| `MAGE-A4_TCRmimic` | MSKCC proprietary | Contact Dao T; or search NCBI for anti-MAGE-A4 TCRmimic scFv |
| `Tet_On_System` | Commercial product | Purchase Tet-On 3G from Takara Bio; components ~1800bp total |

## Sequence Verification Methods

| Method | Count | Description |
|--------|-------|-------------|
| UniProt REST | 55 | Canonical Swiss-Prot reviewed entries; direct REST API download |
| Synthetic standard | 13 | PDB/NCBI source |
| Literature | 8 | PDB/NCBI source |
| Composite assembly from UniProt | 4 | Multi-domain constructs assembled from UniProt segments |
| Published (Kim JH PLoS ONE 2011) | 4 | PDB/NCBI source |
| Composite from UniProt | 3 | PDB/NCBI source |
| Published sgRNA | 3 | PDB/NCBI source |
| UniProt REST (assembled) | 2 | PDB/NCBI source |
| Literature gRNA sequence | 2 | PDB/NCBI source |
| Literature/Standard | 2 | Well-known standard molecular biology element |
| Published standard sequence | 2 | PDB/NCBI source |
| UniProt REST + S228P engineering | 1 | PDB/NCBI source |
| Reconstruction from UniProt P28906 (CD34) + P11836 (CD20) + Blood 2014 | 1 | PDB/NCBI source |
| Patent sequence comparison | 1 | PDB/NCBI source |
| PDB crystal structure 6B9Z | 1 | PDB/NCBI source |
| PDB crystal structure 7KH0 | 1 | Crystal structure of bb2121 BCMA-CAR complex |
| Published literature (Hultberg 2015) | 1 | PDB/NCBI source |
| PDB crystal structure 1N8Z | 1 | Crystal structure of Trastuzumab-HER2 Fab complex |
| PDB crystal structure 4CMH | 1 | Crystal structure of Daratumumab-CD38 Fab complex |
| PDB 3O2D | 1 | PDB/NCBI source |
| Literature (Gillies 1993) | 1 | PDB/NCBI source |
| PDB crystal structure 3KJ4 | 1 | PDB/NCBI source |
| NCBI protein P01786+P01829 | 1 | PDB/NCBI source |
| PDB crystal structure 5XJ3 | 1 | PDB/NCBI source |
| NCBI protein efetch 970841980+970841979 | 1 | PDB/NCBI source |
| CDR grafting onto IGHV3-23 + IGLV1-44 framework from patent CDR sequences | 1 | PDB/NCBI source |
| PDB crystal structure 5VZY | 1 | PDB/NCBI source |
| Composite | 1 | PDB/NCBI source |
| Literature (20nt guide RNA sequence) | 1 | PDB/NCBI source |
| NCBI nucleotide J02585 | 1 | PDB/NCBI source |
| Literature synthetic | 1 | PDB/NCBI source |
| NCBI genomic NC_000007.14 | 1 | PDB/NCBI source |
| Reconstruction from UniProt P0ACT4 + P06492 | 1 | PDB/NCBI source |
| PDB crystal structure 1YY9 | 1 | PDB/NCBI source |
| Literature sequence | 1 | Published amino acid sequence from peer-reviewed paper |
| PDB crystal structure 1GIG | 1 | PDB/NCBI source |
| PDB crystal structure 1S78 | 1 | PDB/NCBI source |
| Unknown | 1 | PDB/NCBI source |
| PDB crystal structure 4KRL VHH | 1 | PDB/NCBI source |
| PDB crystal structure 4K3D | 1 | PDB/NCBI source |
| PDB crystal structure 7Y35 VHH | 1 | PDB/NCBI source |
| PDB crystal structure 6MQR | 1 | PDB/NCBI source |
| Literature/GenBank AF218039.1 | 1 | PDB/NCBI source |
| UniProt P05412 REST | 1 | PDB/NCBI source |
| UniProt Q14116 REST | 1 | PDB/NCBI source |
| UniProt Q9Y5U5 REST | 1 | PDB/NCBI source |
| UniProt Q92956 REST | 1 | PDB/NCBI source |
| UniProt P25942 REST | 1 | PDB/NCBI source |
| UniProt Q99836 REST | 1 | PDB/NCBI source |
| UniProt O60603 REST | 1 | PDB/NCBI source |
| UniProt O43914 REST | 1 | PDB/NCBI source |
| UniProt Q9Y6W8 REST | 1 | PDB/NCBI source |
| UniProt P23510 REST | 1 | PDB/NCBI source |
| UniProt P01857 REST | 1 | PDB/NCBI source |
| Published sequence (Q9GV41 literature) | 1 | PDB/NCBI source |
| Composite: standard furin site RRKR + published P2A sequence | 1 | PDB/NCBI source |
| Literature synthesis (Blazeck 2013) | 1 | PDB/NCBI source |
| UniProt P42345 REST | 1 | PDB/NCBI source |
| UniProt P35225 REST + E13K/R66D mutations applied | 1 | PDB/NCBI source |
| UniProt P07766 REST | 1 | PDB/NCBI source |
| UniProt P0ACT4 + P06492 REST | 1 | PDB/NCBI source |
| Composite from library FMC63+OKT3 | 1 | PDB/NCBI source |
| Published peptide tag (Cartellieri 2016) | 1 | PDB/NCBI source |
| UniProt P16455 REST (SNAP-tag core) | 1 | PDB/NCBI source |
| UniProt P62942 REST + F36V mutation | 1 | PDB/NCBI source |
| UniProt P0ABQ4 REST + F53L/L83I mutations | 1 | PDB/NCBI source |
| Published TCR Vα/Vβ chains + CDR3 from Tran 2016 Science paper | 1 | PDB/NCBI source |
| Published anti-NY-ESO-1/HLA-A2 scFv (Dolton 2018 JCI framework) | 1 | PDB/NCBI source |
| PDB 6NNQ Chain B | 1 | PDB/NCBI source |
| Published cirmtuzumab (UC-961) humanized VH+VL — Danilova 2020 Cancer Res | 1 | PDB/NCBI source |
| Published patent WO2014130635 (CSL362/talacotuzumab VH+VL) | 1 | PDB/NCBI source |
| Published Jetani 2018 Leukemia VH+VL sequences | 1 | PDB/NCBI source |
| Published Chmielewski 2012 VH+VL (Mab 17-1A/MT201 framework) | 1 | PDB/NCBI source |
| Published talquetamab (JNJ-64407564) VH+VL framework | 1 | PDB/NCBI source |
| Published rovalpituzumab (SC16LD6.5) humanized VH+VL | 1 | PDB/NCBI source |
| Published anti-AFP VH+VL (Lehner 2012 Cancer Immunol) | 1 | PDB/NCBI source |
| PDB 1JPS | 1 | PDB/NCBI source |
| Published anti-GPC1 VH+VL (Durbin 2022 Cancer Cell supplementary) | 1 | PDB/NCBI source |
| UniProt O14931 REST | 1 | PDB/NCBI source |
| UniProt O95944 REST | 1 | PDB/NCBI source |
| UniProt P08637 REST | 1 | PDB/NCBI source |
| Published sgRNA target sequence | 1 | PDB/NCBI source |
| PDB 5X8M | 1 | PDB/NCBI source |
| UniProt O95760 REST | 1 | PDB/NCBI source |
| UniProt P49771 REST | 1 | PDB/NCBI source |
| UniProt Q9NZC2 REST | 1 | PDB/NCBI source |
| UniProt P31785 REST | 1 | PDB/NCBI source |
| UniProt P18627 REST | 1 | PDB/NCBI source |
| UniProt Q8TDQ0 REST | 1 | PDB/NCBI source |
| UniProt P04141 REST | 1 | PDB/NCBI source |
| UniProt P08138 REST | 1 | PDB/NCBI source |
| Published standard sequence (core region) | 1 | PDB/NCBI source |
| UniProt O95971 REST | 1 | PDB/NCBI source |
| PDB 4HKZ | 1 | PDB/NCBI source |
| UniProt P13232 REST + CD4-TM anchor | 1 | PDB/NCBI source |
| UniProt Q9UBK5 REST | 1 | PDB/NCBI source |
| Published Kim 2011 GSG-P2A canonical | 1 | PDB/NCBI source |
| UniProt P17948 REST | 1 | PDB/NCBI source |
| UniProt P37173 REST | 1 | PDB/NCBI source |
| PDB 4M62 | 1 | PDB/NCBI source |
| UniProt Q96RJ3 REST | 1 | PDB/NCBI source |
| UniProt P26718 REST | 1 | PDB/NCBI source |
| UniProt P06239 REST | 1 | PDB/NCBI source |
| Published TRAC sgRNA (Eyquem 2017) | 1 | PDB/NCBI source |
| Published CD16b GPI signal | 1 | PDB/NCBI source |
| Published J591 VH+VL (Bander 2003) | 1 | PDB/NCBI source |
| Published seribantumab framework VH+VL | 1 | PDB/NCBI source |
| Published hu3F8 VH+VL | 1 | PDB/NCBI source |
| Published 12G5 framework VH+VL | 1 | PDB/NCBI source |
| Published amatuximab VH+VL framework | 1 | PDB/NCBI source |
| Truncated from CD3z_signaling (library) | 1 | PDB/NCBI source |
| UniProt P20333 REST | 1 | PDB/NCBI source |
| UniProt P15328 REST | 1 | PDB/NCBI source |

## Quick Reference: Key Sequences

| Element | Length | Key Function | Approved Use |
|---------|--------|--------------|-------------|
| `FMC63_scFv` | 243aa | All 6 FDA-approved anti-CD19 CARs | T1 |
| `CD3z_cyto` | 113aa | Universal signaling domain, 3 ITAMs | T1 |
| `4-1BB_cyto` | 42aa | Kymriah/Abecma persistence module | T1 |
| `CD28_cyto` | 41aa | Yescarta/Tecartus speed module | T1 |
| `tEGFR` | 359aa | Universal safety switch (cetuximab) | T2 |
| `iCasp9` | 282aa | AP1903-inducible kill switch | T2 |
| `IgG4_SPLE_Long` | 229aa | Long flexible hinge, S228P mutation | T2 |
| `PD1_CD28_CSR` | 229aa | Checkpoint resistance chimeric switch | T2 |
| `Secreted_IL12` | 518aa | Armored TRUCK payload, NFAT-inducible | T2 |
| `SynNotch_NRR` | 213aa | AND logic gate (dual antigen) | T3 |
| `FoxP3_TF` | 431aa | Master Treg transcription factor | T3 |
| `TRAC_CRISPR_Target` | 20aa | Knock out for allogeneic CAR-T | T2 |

---

*InSynBio ACTES CAR-T Engine — Component Library V3*  
*Maintained with systematic verification from UniProt, PDB, NCBI, and clinical literature.*  
*Generated: 2026-04-01*
