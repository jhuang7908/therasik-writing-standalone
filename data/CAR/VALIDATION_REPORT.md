# CART_LIBRARY_V3 — Comprehensive Validation Report

> Generated: 2026-04-01 | InSynBio ACTES CAR-T Component Library

## Library Summary

| Metric | Value |
|--------|-------|
| Total elements | **237** |
| Sequence verified | **237** (100%) |
| Stubs (no sequence) | 0 (0%) |
| T1 (FDA/EMA approved) | 25 |
| T2 (Clinical trial) | 119 |
| T3 (Research) | 93 |
| Categories | 12 |
| File size | 412 KB |

## Motif Validation Results

| Result | Count |
|--------|-------|
| ✅ PASS | 30 |
| ❌ FAIL | 0 |
| ○ STUB | 0 |

### Detailed Validation

| Element | Status | Length | Checks |
|---------|--------|--------|--------|
| `4-1BB_cyto` | ✅ PASS | 42aa | All OK |
| `CD28_Medium` | ✅ PASS | 39aa | All OK |
| `CD28_TM` | ✅ PASS | 27aa | All OK |
| `CD28_cyto` | ✅ PASS | 41aa | All OK |
| `CD3z_TM` | ✅ PASS | 30aa | All OK |
| `CD3z_cyto` | ✅ PASS | 113aa | All OK |
| `CD4_TM` | ✅ PASS | 22aa | All OK |
| `CD8a_SP` | ✅ PASS | 21aa | All OK |
| `CD8a_Short` | ✅ PASS | 45aa | All OK |
| `CD8a_TM` | ✅ PASS | 24aa | All OK |
| `Daratumumab_scFv` | ✅ PASS | 242aa | All OK |
| `Dsg3_ECD_CAAR` | ✅ PASS | 566aa | All OK |
| `FKBP12` | ✅ PASS | 108aa | All OK |
| `FMC63_scFv` | ✅ PASS | 243aa | All OK |
| `FoxP3_TF` | ✅ PASS | 431aa | All OK |
| `GM-CSF_SP` | ✅ PASS | 17aa | All OK |
| `GPX4_Enhanced` | ✅ PASS | 197aa | All OK |
| `Granulin_SP` | ✅ PASS | 21aa | All OK |
| `ICOS_cyto` | ✅ PASS | 37aa | All OK |
| `IgG4_SPLE_Long` | ✅ PASS | 229aa | All OK |
| `Membrane_IL15` | ✅ PASS | 173aa | All OK |
| `OX40_cyto` | ✅ PASS | 40aa | All OK |
| `PD1_CD28_CSR` | ✅ PASS | 229aa | All OK |
| `Rituximab_scFv` | ✅ PASS | 238aa | All OK |
| `Secreted_IL12` | ✅ PASS | 518aa | All OK |
| `SynNotch_NRR` | ✅ PASS | 213aa | All OK |
| `Trastuzumab_scFv` | ✅ PASS | 242aa | All OK |
| `ch14_18_GD2_scFv` | ✅ PASS | 244aa | All OK |
| `iCasp9` | ✅ PASS | 282aa | All OK |
| `tEGFR` | ✅ PASS | 359aa | All OK |

## Category Coverage

| Category | Total | Seq✓ | Stub | T1 | T2 | T3 |
|----------|-------|------|------|----|----|----|
| Antigen Binder | 60 | 60 | 0 | 6 | 44 | 10 |
| Armored Payload | 26 | 26 | 0 | 1 | 12 | 13 |
| Costimulatory Domain | 15 | 15 | 0 | 2 | 5 | 8 |
| Engineering Module | 39 | 39 | 0 | 0 | 10 | 29 |
| Hinge & Spacer | 6 | 6 | 0 | 2 | 3 | 1 |
| Linker & Peptide | 19 | 19 | 0 | 3 | 15 | 1 |
| Logic Gate & Switch | 14 | 14 | 0 | 0 | 1 | 13 |
| Primary Signaling Domain | 13 | 13 | 0 | 1 | 3 | 9 |
| Regulatory Element | 19 | 19 | 0 | 7 | 10 | 2 |
| Safety Switch | 10 | 10 | 0 | 0 | 8 | 2 |
| Signal Peptide | 7 | 7 | 0 | 1 | 3 | 3 |
| Transmembrane Domain | 9 | 9 | 0 | 2 | 5 | 2 |

## Sequence Verification Sources

| Verification Method | Count |
|-------------------|-------|
| UniProt REST | 67 |
| Synthetic standard | 13 |
| Published sgRNA | 11 |
| Literature | 8 |
| Published VH/VL + G4S3 linker | 6 |
| Composite assembly from UniProt | 4 |
| Published (Kim JH PLoS ONE 2011) | 4 |
| Composite from UniProt | 3 |
| UniProt REST (assembled) | 2 |
| Literature gRNA sequence | 2 |
| Literature/Standard | 2 |
| Published standard sequence | 2 |
| UniProt REST + truncation | 2 |
| UniProt REST (mature form) | 2 |
| UniProt REST + S228P engineering | 1 |
| Patent | 1 |
| Patent sequence comparison | 1 |
| PDB crystal structure 6B9Z | 1 |
| PDB crystal structure 7KH0 | 1 |
| Published literature (Hultberg 2015) | 1 |
| PDB crystal structure 1N8Z | 1 |
| PDB crystal structure 4CMH | 1 |
| PDB 3O2D | 1 |
| Literature (Gillies 1993) | 1 |
| PDB crystal structure 3KJ4 | 1 |
| NCBI protein P01786+P01829 | 1 |
| PDB crystal structure 5XJ3 | 1 |
| NCBI protein efetch 970841980+970841979 | 1 |
| CDR grafting onto IGHV3-23 + IGLV1-44 framework from patent CDR sequences | 1 |
| PDB crystal structure 5VZY | 1 |
| Composite | 1 |
| Literature (20nt guide RNA sequence) | 1 |
| NCBI nucleotide J02585 | 1 |
| Literature synthetic | 1 |
| NCBI genomic NC_000007.14 | 1 |
| Reconstruction from UniProt P0ACT4 + P06492 | 1 |
| PDB crystal structure 1YY9 | 1 |
| Literature sequence | 1 |
| PDB crystal structure 1GIG | 1 |
| PDB crystal structure 1S78 | 1 |
| PDB crystal structure 4KRL VHH | 1 |
| PDB crystal structure 4K3D | 1 |
| PDB crystal structure 7Y35 VHH | 1 |
| PDB crystal structure 6MQR | 1 |
| Literature/GenBank AF218039.1 | 1 |
| UniProt P05412 REST | 1 |
| UniProt Q14116 REST | 1 |
| UniProt Q9Y5U5 REST | 1 |
| UniProt Q92956 REST | 1 |
| UniProt P25942 REST | 1 |
| UniProt Q99836 REST | 1 |
| UniProt O60603 REST | 1 |
| UniProt O43914 REST | 1 |
| UniProt Q9Y6W8 REST | 1 |
| UniProt P23510 REST | 1 |
| UniProt P01857 REST | 1 |
| Published sequence (Q9GV41 literature) | 1 |
| Composite: standard furin site RRKR + published P2A sequence | 1 |
| Literature synthesis (Blazeck 2013) | 1 |
| UniProt P42345 REST | 1 |
| UniProt P35225 REST + E13K/R66D mutations applied | 1 |
| UniProt P07766 REST | 1 |
| UniProt P0ACT4 + P06492 REST | 1 |
| Composite from library FMC63+OKT3 | 1 |
| Published peptide tag (Cartellieri 2016) | 1 |
| UniProt P16455 REST (SNAP-tag core) | 1 |
| UniProt P62942 REST + F36V mutation | 1 |
| UniProt P0ABQ4 REST + F53L/L83I mutations | 1 |
| Published TCR Vα/Vβ chains + CDR3 from Tran 2016 Science paper | 1 |
| Published anti-NY-ESO-1/HLA-A2 scFv (Dolton 2018 JCI framework) | 1 |
| PDB 6NNQ Chain B | 1 |
| Published cirmtuzumab (UC-961) humanized VH+VL — Danilova 2020 Cancer Res | 1 |
| Published patent WO2014130635 (CSL362/talacotuzumab VH+VL) | 1 |
| Published Jetani 2018 Leukemia VH+VL sequences | 1 |
| Published Chmielewski 2012 VH+VL (Mab 17-1A/MT201 framework) | 1 |
| Published talquetamab (JNJ-64407564) VH+VL framework | 1 |
| Published rovalpituzumab (SC16LD6.5) humanized VH+VL | 1 |
| Published anti-AFP VH+VL (Lehner 2012 Cancer Immunol) | 1 |
| PDB 1JPS | 1 |
| Published anti-GPC1 VH+VL (Durbin 2022 Cancer Cell supplementary) | 1 |
| UniProt O14931 REST | 1 |
| UniProt O95944 REST | 1 |
| UniProt P08637 REST | 1 |
| Published sgRNA target sequence | 1 |
| PDB 5X8M | 1 |
| UniProt O95760 REST | 1 |
| UniProt P49771 REST | 1 |
| UniProt Q9NZC2 REST | 1 |
| UniProt P31785 REST | 1 |
| UniProt P18627 REST | 1 |
| UniProt Q8TDQ0 REST | 1 |
| UniProt P04141 REST | 1 |
| UniProt P08138 REST | 1 |
| Published standard sequence (core region) | 1 |
| UniProt O95971 REST | 1 |
| PDB 4HKZ | 1 |
| UniProt P13232 REST + CD4-TM anchor | 1 |
| UniProt Q9UBK5 REST | 1 |
| Published Kim 2011 GSG-P2A canonical | 1 |
| UniProt P17948 REST | 1 |
| UniProt P37173 REST | 1 |
| PDB 4M62 | 1 |
| UniProt Q96RJ3 REST | 1 |
| UniProt P26718 REST | 1 |
| UniProt P06239 REST | 1 |
| Published TRAC sgRNA (Eyquem 2017) | 1 |
| Published CD16b GPI signal | 1 |
| Published J591 VH+VL (Bander 2003) | 1 |
| Published seribantumab framework VH+VL | 1 |
| Published hu3F8 VH+VL | 1 |
| Published 12G5 framework VH+VL | 1 |
| Published amatuximab VH+VL framework | 1 |
| Truncated from CD3z_signaling (library) | 1 |
| UniProt P20333 REST | 1 |
| UniProt P15328 REST | 1 |
| UniProt Q16520 isoform 2 (125aa) + N-terminal 38aa from NP_055142.1 isoform 1 | 1 |
| Published VH/VL + G4S3 linker (VH-linker-VL) | 1 |
| UniProt REST (Tc1 scaffold) + published mutations | 1 |
| UniProt REST + domain fusion (IL15Ra sushi + IL15 mature) | 1 |
| Published canonical CDR3 + germline framework | 1 |
| UniProt REST + domain extraction | 1 |
| Published promoter sequence | 1 |
| UniProt REST + kinase domain deletion | 1 |

## Stubs — Priority Fetch List

| ID | Category | Tier | Source | Expected Length |
|----|----------|------|--------|-----------------|

## Known Issues & Action Items

### Validation Failures

No failures detected in validated elements. ✅

## Design Rules Index

Key ACTES decision rules encoded in element design_notes:

| Rule | Logic |
|------|-------|
| **Hinge selection** | Epitope-to-membrane distance: Short (<5nm)→CD8α Short; Medium (5-10nm)→CD28; Long (>10nm)→IgG4 SPLE |
| **TM selection** | Low tonic signal→CD8α TM; Lipid raft+costim→CD28 TM; NK-optimized→NKG2D TM |
| **Costim selection** | Rapid response/hematologic→CD28; Persistence/solid tumor→4-1BB; Autoimmune/Treg→ICOS or OX40 |
| **Safety switch** | Hematologic high-risk→tEGFR mandatory; Small-molecule control→iCasp9; GMP enrichment→RQR8 |
| **Solid tumor armor** | TGF-β high TME→add TGFB_DNR; ECM dense→add HPSE; Ferroptosis risk→add GPX4; Infiltration→IL7_CCL19 |
| **Allogeneic** | TRAC KO (GvHD) + B2M KO (host CTL escape) + HLA-G (NK evasion) + CD52 KO (alemtuzumab resistance) |
| **Logic gating** | Dual antigen required→SynNotch AND; Normal tissue risk→iCAR NOT; Checkpoint→PD1-CD28 CSR |

