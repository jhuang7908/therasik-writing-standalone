# Engineered Human VH Atlas-24 Site-Level Fingerprint

## Scope

- Dataset: `data/vhh_design_atlas_v3.json`, `category == "Engineered_Human_VH"`.
- Entries analyzed: 24; ANARCI Kabat success: 24/24.
- Purpose: evidence for VH->VHH algorithm optimization, not a standard/config change.

## 1. CDR Envelope

| Metric | Mean | P25 | Median | P75 | Range |
|---|---:|---:|---:|---:|---:|
| CDR-H3 length | 11.042 | 9.5 | 10.5 | 15.0 | 3…19 |
| CDR-H3 net charge | -0.417 | -2.0 | -1.0 | 1.0 | -2…3 |
| CDR-H3 GRAVY | -0.885 | -1.097 | -1.033 | -0.565 | -2.03…0.05 |
| All-CDR GRAVY | -0.592 | -0.829 | -0.6 | -0.492 | -1.297…0.028 |
| CDR-H3 D/E density | 0.123 | 0.046 | 0.125 | 0.191 | 0.0…0.3 |
| CDR-H3 F/W/Y density | 0.178 | 0.094 | 0.183 | 0.259 | 0.0…0.438 |

## 2. CDR-H3 Length Buckets

| Bucket | Count | Fraction | Mean stealth departures |
|---|---:|---:|---:|
| `mid10-16` | 16 | 66.7% | 2.688 |
| `short<=9` | 6 | 25.0% | 2.333 |
| `long>=17` | 2 | 8.3% | 3.0 |

## 3. Hallmark Motif Distribution

| Motif 37/44/45/47 | Count | Fraction |
|---|---:|---:|
| `VGRW` | 5 | 20.8% |
| `VGEL` | 4 | 16.7% |
| `VALW` | 2 | 8.3% |
| `FERF` | 2 | 8.3% |
| `VGPW` | 2 | 8.3% |
| `VERW` | 1 | 4.2% |
| `FERW` | 1 | 4.2% |
| `FERI` | 1 | 4.2% |
| `VGLR` | 1 | 4.2% |
| `VTPW` | 1 | 4.2% |
| `VGEW` | 1 | 4.2% |
| `VGPV` | 1 | 4.2% |
| `VAQW` | 1 | 4.2% |
| `FGRL` | 1 | 4.2% |

| Hallmark type | Count | Fraction |
|---|---:|---:|
| `Mixed_Custom` | 19 | 79.2% |
| `VHH_Camelid_Like` | 5 | 20.8% |

## 4. Focus Kabat Position Frequencies

| Position | IGHV3-23 ref | Top residues in Atlas-24 | Departure rate |
|---:|---:|---|---:|
| 35 | `S` | G:8, S:7, T:4, H:2, A:1, Y:1, W:1 | 70.8% |
| 37 | `V` | V:19, F:5 | 20.8% |
| 44 | `G` | G:15, E:5, A:3, T:1 | 37.5% |
| 45 | `L` | R:11, E:5, P:4, L:3, Q:1 | 87.5% |
| 47 | `W` | W:14, L:5, F:2, I:1, R:1, V:1 | 41.7% |
| 50 | `A` | S:5, R:5, A:5, T:4, V:2, N:1, G:1, L:1 | 79.2% |
| 89 | `V` | V:17, T:4, M:3 | 29.2% |
| 94 | `K` | S:8, R:7, K:4, P:2, T:1, Y:1, A:1 | 83.3% |

## 5. Stealth Departure Distribution

| Number of departures at 35/50/89/94 | Count | Fraction |
|---:|---:|---:|
| 1 | 4 | 16.7% |
| 2 | 2 | 8.3% |
| 3 | 17 | 70.8% |
| 4 | 1 | 4.2% |

## 6. Liability Flags

| Flag | Rate |
|---|---:|
| `any_cdr_nglyc` | 4.2% |
| `any_cdr_deamid` | 12.5% |
| `cdr3_anchor_risk` | 8.3% |

## 7. Proposed Engineered VH Similarity Score (Draft)

This is a proposed evidence layer for V1.6, not yet an approved standard.

| Component | Draft scoring rule from Atlas-24 | Rationale |
|---|---|---|
| CDR-H3 charge | Full credit if net charge is within Atlas-24 P25-P75; partial if within min-max; penalty if < -2 | Successful engineered VH cases avoid strongly acidic CDR-H3. |
| CDR hydrophilicity | Reward CDR-H3 GRAVY <= Atlas-24 P75 and All-CDR GRAVY <= Atlas-24 P75 | Atlas-24 is strongly CDR-hydrophilic. |
| Hallmark motif | Reward motif observed in Atlas-24; extra credit for common motifs | Preserves real engineered single-domain solutions. |
| Stealth departures | Reward 2-4 departures at 35/50/89/94, gated by CDR2 length | Matches known interface reshaping without over-mutating CDR2. |
| Liability veto | Penalize CDR N-X-S/T, NG/NS, and CDR3 P/D anchor | These are enriched failure-risk features for expression or heterogeneity. |
| Long CDR3 anchor check | If CDR3 >= 16, require FR2 anchor compatibility / structure QC | Aligns with V1.5 conformational mismatch warning. |

## Verification Status

- [verified] Dataset size is 24 because entries were filtered from `data/vhh_design_atlas_v3.json` where `category == "Engineered_Human_VH"`.
- [verified] Kabat CDRs and focus residues were recomputed by ANARCI during this run; success rate was 24/24.
- [verified] Reported site frequencies, CDR metrics, and liability rates are calculated from the generated JSON payload.
- [inferred] The proposed Engineered VH Similarity Score is a draft evidence layer for V1.6 and is not an approved production threshold.

## Adversarial Checks

- Alternative explanation: Atlas-24 may overrepresent solved structural references rather than high-expression production winners; use as algorithm prior, not a definitive developability threshold. PASS
- Failure mode: Some PDB entries are related clones or duplicate target families, so frequency counts can overweight one engineering campaign. WARN
- Boundary condition: Site-map rules do not replace structure QC for long CDR3 or antigen-contact preservation; they should trigger candidate ranking or warnings only. PASS

## Sources

- `data/vhh_design_atlas_v3.json` — Atlas v3, `Engineered_Human_VH` subset.
- `docs/VH_TO_VHH_CONVERSION_STANDARD_V1.5.md` — governing VH→VHH conversion standard.
- `data/vhh_database_summary.md` — frozen four-database summary and hallmark/stealth provenance.

## 8. Per-Entry Site Map

| PDB | Motif | CDR3 len | CDR3 charge | CDR3 GRAVY | Stealth departures | Liability | Target |
|---|---|---:|---:|---:|---|---|---|
| `6jsz` | `VGRW` | 3 | 1 | -1.033 | 35,50,94 | - | beta-secretase 2 |
| `7d5b` | `VGRW` | 3 | 1 | -1.033 | 35,50,94 | - | beta-secretase 2 |
| `7d5u` | `VGRW` | 3 | 1 | -1.033 | 35,50,94 | - | beta-secretase 2 |
| `7f1g` | `VGRW` | 3 | 1 | -1.033 | 35,50,94 | - | beta-secretase 2 |
| `5dmj` | `VGLR` | 7 | -2 | 0.014 | 35 | - | tumor necrosis factor receptor superfamily member 5 |
| `7nfr` | `VGRW` | 8 | -1 | -1.938 | 50 | - | polymerase basic protein 2 |
| `3zhd` | `VGPV` | 10 | -1 | -1.26 | 35,50,94 | - | NA |
| `6j7w` | `VGPW` | 10 | -2 | -2.03 | 50 | - | tumor necrosis factor receptor superfamily member 17 |
| `7vnd` | `VALW` | 10 | -1 | -1.05 | 50,89,94 | - | spike glycoprotein |
| `7vne` | `VAQW` | 10 | -1 | -1.05 | 50,89,94 | - | spike glycoprotein |
| `7whi` | `VTPW` | 10 | -1 | -1.05 | 50,89,94 | - | spike glycoprotein |
| `8di5` | `VALW` | 10 | -2 | 0.05 | 50,89,94 | - | spike glycoprotein |
| `3b9v` | `VGEW` | 11 | -2 | -0.473 | 35,50,94 | deamid | NA |
| `1ol0` | `FERI` | 12 | 0 | -1.433 | 94 | - | NA |
| `7azb` | `FERF` | 12 | 3 | -1.283 | 35,89,94 | - | discoidin domain-containing receptor 2 |
| `7zf4` | `VGPW` | 13 | -2 | -0.354 | 35,50,94 | - | spike protein s1 |
| `3p9w` | `VGEL` | 14 | 2 | -0.936 | 35,50,94 | deamid | vascular endothelial growth factor a |
| `6sge` | `FERF` | 15 | 0 | -0.72 | 35,89,94 | N-glyc | rho-related gtp-binding protein rhob |
| `7vke` | `VERW` | 15 | -1 | 0.013 | 35,50 | P/D-anchor | adp-ribosyl cyclase/cyclic adp-ribose hydrolase 1 |
| `7jwb` | `VGEL` | 16 | -2 | -0.613 | 35,50,94 | - | spike glycoprotein | spike glycoprotein |
| `7omn` | `VGEL` | 16 | -2 | -1.238 | 35,50,94 | - | NA |
| `7ooi` | `VGEL` | 16 | 0 | -0.744 | 35,50,94 | - | NA |
| `2x89` | `FERW` | 19 | 1 | -0.416 | 35,50,89,94 | deamid,P/D-anchor | beta-2-microglobulin |
| `7eow` | `FGRL` | 19 | 0 | -0.595 | 35,94 | - | von willebrand factor |
