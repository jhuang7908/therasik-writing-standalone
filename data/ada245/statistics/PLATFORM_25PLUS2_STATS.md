# Platform 25+2 statistics (ADA245 cohort)

- ADA table: `D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada245\database\ada_master_245_curated.csv`
- Natural-384 (25 numeric developability fields): `D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\natural_380_atlas\natural384_cmc_per_antibody.csv`
- **25** = `PARAMETER_SET_25` keys; **+2** = HPR Index + AbLang2 in CMC vocabulary.
- **ADA245 row coverage:** **13/25** developability keys exist as columns in the ADA CSV (sequence/Fv metrics). Remaining keys require Natural384 merge or batch structure metrics.
- **IMGT HPR proxy** = `(vh_identity_imgt + vl_identity_imgt)/2` when VL exists; otherwise VH-only. **AbLang2**: not in CSV (pending batch).

## gene_engineered_humanization — Humanized (CDR Grafting)

- n (platform): **115** | matched to Natural384: **1**
- **HPR proxy (IMGT mean)**: n=77, mean=0.8163, median=0.8290, p25–p75=[0.7880, 0.8665]
- **AbLang2**: pending batch (not in source CSV).

### 25-parameter subset — direct from ADA245 rows (same platform)

| Parameter | n | mean | p50 | p25 | p75 |
| --- | ---: | ---: | ---: | ---: | ---: |
| pI | 94 | 6.5907 | 7.8350 | 5.4250 | 8.6275 |
| GRAVY | 94 | -0.2892 | -0.2895 | -0.3585 | -0.2225 |
| instability_index | 94 | 29.9272 | 35.6000 | 30.2000 | 40.7000 |
| net_charge_pH7 | 73 | 0.7688 | 1.0000 | -1.2000 | 3.0000 |
| charge_patch_max7 | 72 | 3.0278 | 3.0000 | 3.0000 | 3.0000 |
| hydro_patch_max9 | 73 | 0.6092 | 0.5560 | 0.5560 | 0.6670 |
| agg_motifs | 73 | 0.4932 | 0.0000 | 0.0000 | 1.0000 |
| deamidation_sites | 72 | 1.2639 | 1.0000 | 0.0000 | 2.0000 |
| isomerization_sites | 72 | 1.0278 | 1.0000 | 0.0000 | 2.0000 |
| vh_vl_angle_deg | 72 | 81.7361 | 82.2619 | 79.0802 | 85.0335 |
| interface_n_pairs | 72 | 72.1389 | 72.0000 | 69.0000 | 75.0000 |
| interface_mean_dist_A | 72 | 4.6735 | 4.6888 | 4.6370 | 4.7078 |
| interface_min_dist_A | 72 | 1.9007 | 1.9445 | 1.5439 | 2.4153 |

### 25-parameter full keys — Natural384 name match (subset of platform)

| Parameter | n | mean | p50 | p25 | p75 |
| --- | ---: | ---: | ---: | ---: | ---: |
| pI | 1 | 7.8700 | 7.8700 | 7.8700 | 7.8700 |
| GRAVY | 1 | -0.2160 | -0.2160 | -0.2160 | -0.2160 |
| instability_index | 1 | 37.1000 | 37.1000 | 37.1000 | 37.1000 |
| net_charge_pH7 | 1 | 0.8900 | 0.8900 | 0.8900 | 0.8900 |
| charge_patch_max7 | 1 | 4.0000 | 4.0000 | 4.0000 | 4.0000 |
| Fv_charge_asymmetry | 1 | 2.9910 | 2.9910 | 2.9910 | 2.9910 |
| hydro_patch_max9 | 1 | 0.5560 | 0.5560 | 0.5560 | 0.5560 |
| SAP_score | 1 | 0.5710 | 0.5710 | 0.5710 | 0.5710 |
| agg_motifs | 1 | 2.0000 | 2.0000 | 2.0000 | 2.0000 |
| hydro_cluster_count | 1 | 2.0000 | 2.0000 | 2.0000 | 2.0000 |
| glycosylation_sites | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| deamidation_sites | 1 | 2.0000 | 2.0000 | 2.0000 | 2.0000 |
| isomerization_sites | 1 | 3.0000 | 3.0000 | 3.0000 | 3.0000 |
| oxidation_sites | 1 | 8.0000 | 8.0000 | 8.0000 | 8.0000 |
| free_cys | 1 | 4.0000 | 4.0000 | 4.0000 | 4.0000 |
| total_cdr_length | 1 | 47.0000 | 47.0000 | 47.0000 | 47.0000 |
| psh | 1 | 715.9900 | 715.9900 | 715.9900 | 715.9900 |
| ppc | 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| pnc | 1 | 2.0000 | 2.0000 | 2.0000 | 2.0000 |
| sfvcsp | 1 | -1.8000 | -1.8000 | -1.8000 | -1.8000 |
| vh_vl_angle_deg | 1 | 87.7805 | 87.7805 | 87.7805 | 87.7805 |
| interface_n_pairs | 1 | 56.0000 | 56.0000 | 56.0000 | 56.0000 |
| interface_mean_dist_A | 1 | 4.6447 | 4.6447 | 4.6447 | 4.6447 |
| interface_min_dist_A | 1 | 1.9013 | 1.9013 | 1.9013 | 1.9013 |
| vernier_sasa_total | 1 | 594.8496 | 594.8496 | 594.8496 | 594.8496 |

## transgenic_mouse — Transgenic Mice

- n (platform): **68** | matched to Natural384: **63**
- **HPR proxy (IMGT mean)**: n=43, mean=0.8791, median=0.9530, p25–p75=[0.8739, 0.9667]
- **AbLang2**: pending batch (not in source CSV).

### 25-parameter subset — direct from ADA245 rows (same platform)

| Parameter | n | mean | p50 | p25 | p75 |
| --- | ---: | ---: | ---: | ---: | ---: |
| pI | 60 | 6.5588 | 7.8550 | 5.8825 | 8.7750 |
| GRAVY | 60 | -0.2491 | -0.2640 | -0.3247 | -0.1690 |
| instability_index | 60 | 30.5783 | 38.1500 | 2.8750 | 44.4750 |
| net_charge_pH7 | 43 | 1.5651 | 1.0000 | -0.1000 | 3.8000 |
| charge_patch_max7 | 43 | 3.1395 | 3.0000 | 3.0000 | 3.0000 |
| hydro_patch_max9 | 43 | 0.6438 | 0.6670 | 0.5560 | 0.6670 |
| agg_motifs | 43 | 0.1628 | 0.0000 | 0.0000 | 0.0000 |
| deamidation_sites | 43 | 1.8837 | 2.0000 | 1.0000 | 3.0000 |
| isomerization_sites | 43 | 1.3721 | 1.0000 | 0.5000 | 2.0000 |
| vh_vl_angle_deg | 43 | 83.9649 | 84.0377 | 82.1180 | 86.1817 |
| interface_n_pairs | 43 | 71.4884 | 71.0000 | 67.0000 | 74.0000 |
| interface_mean_dist_A | 43 | 4.6551 | 4.6594 | 4.6286 | 4.6941 |
| interface_min_dist_A | 43 | 1.8578 | 1.8987 | 1.6155 | 2.1608 |

### 25-parameter full keys — Natural384 name match (subset of platform)

| Parameter | n | mean | p50 | p25 | p75 |
| --- | ---: | ---: | ---: | ---: | ---: |
| pI | 63 | 7.7254 | 7.8800 | 6.7750 | 8.6400 |
| GRAVY | 63 | -0.2920 | -0.2930 | -0.3350 | -0.2540 |
| instability_index | 63 | 40.6349 | 41.9000 | 35.1000 | 45.2500 |
| net_charge_pH7 | 63 | 1.4619 | 0.9800 | -0.1850 | 2.9000 |
| charge_patch_max7 | 63 | 3.1778 | 3.0000 | 3.0000 | 4.0000 |
| Fv_charge_asymmetry | 63 | 2.3750 | 1.9220 | 0.9980 | 3.1455 |
| hydro_patch_max9 | 63 | 0.6423 | 0.6670 | 0.5560 | 0.6670 |
| SAP_score | 63 | 0.7117 | 0.7140 | 0.7140 | 0.7140 |
| agg_motifs | 63 | 4.1270 | 4.0000 | 2.0000 | 5.5000 |
| hydro_cluster_count | 63 | 3.1587 | 3.0000 | 2.0000 | 4.0000 |
| glycosylation_sites | 63 | 0.0952 | 0.0000 | 0.0000 | 0.0000 |
| deamidation_sites | 63 | 1.7302 | 2.0000 | 1.0000 | 3.0000 |
| isomerization_sites | 63 | 1.3492 | 1.0000 | 1.0000 | 2.0000 |
| oxidation_sites | 63 | 8.8413 | 9.0000 | 8.0000 | 10.0000 |
| free_cys | 63 | 4.0317 | 4.0000 | 4.0000 | 4.0000 |
| total_cdr_length | 63 | 49.5079 | 49.0000 | 46.0000 | 53.0000 |
| psh | 63 | 491.5297 | 405.0000 | 267.6150 | 658.3350 |
| ppc | 63 | 1.7667 | 2.0000 | 1.0000 | 2.0000 |
| pnc | 63 | 2.2381 | 2.0000 | 1.0000 | 3.0000 |
| sfvcsp | 63 | 2.6311 | 3.0000 | 0.0000 | 6.1500 |
| vh_vl_angle_deg | 63 | 83.7760 | 83.8652 | 82.0022 | 86.1680 |
| interface_n_pairs | 63 | 70.8730 | 71.0000 | 67.0000 | 74.0000 |
| interface_mean_dist_A | 63 | 4.6566 | 4.6572 | 4.6286 | 4.6955 |
| interface_min_dist_A | 63 | 1.8058 | 1.7851 | 1.5083 | 2.2159 |
| vernier_sasa_total | 63 | 538.5749 | 526.7987 | 508.8750 | 564.9604 |

## phage_display — Phage Display

- n (platform): **7** | matched to Natural384: **5**
- **HPR proxy (IMGT mean)**: n=7, mean=0.8827, median=0.9212, p25–p75=[0.8882, 0.9458]
- **AbLang2**: pending batch (not in source CSV).

### 25-parameter subset — direct from ADA245 rows (same platform)

| Parameter | n | mean | p50 | p25 | p75 |
| --- | ---: | ---: | ---: | ---: | ---: |
| pI | 7 | 7.7514 | 7.8100 | 7.3900 | 8.2450 |
| GRAVY | 7 | -0.2344 | -0.2000 | -0.2885 | -0.1675 |
| instability_index | 7 | 39.5000 | 38.4000 | 37.7000 | 40.9500 |
| net_charge_pH7 | 7 | 1.1857 | 0.8000 | 0.4000 | 1.8500 |
| charge_patch_max7 | 7 | 3.1429 | 3.0000 | 3.0000 | 3.0000 |
| hydro_patch_max9 | 7 | 0.6194 | 0.5560 | 0.5560 | 0.6670 |
| agg_motifs | 7 | 0.5714 | 0.0000 | 0.0000 | 1.0000 |
| deamidation_sites | 7 | 1.1429 | 1.0000 | 0.5000 | 2.0000 |
| isomerization_sites | 7 | 0.8571 | 1.0000 | 0.0000 | 1.5000 |
| vh_vl_angle_deg | 7 | 84.8251 | 85.6769 | 83.2881 | 86.6169 |
| interface_n_pairs | 7 | 66.0000 | 67.0000 | 62.0000 | 70.0000 |
| interface_mean_dist_A | 7 | 4.6766 | 4.6802 | 4.6389 | 4.7105 |
| interface_min_dist_A | 7 | 1.9119 | 1.9110 | 1.4220 | 2.3481 |

### 25-parameter full keys — Natural384 name match (subset of platform)

| Parameter | n | mean | p50 | p25 | p75 |
| --- | ---: | ---: | ---: | ---: | ---: |
| pI | 5 | 8.0140 | 7.8100 | 7.7800 | 8.6400 |
| GRAVY | 5 | -0.2298 | -0.2000 | -0.2520 | -0.1680 |
| instability_index | 5 | 40.2000 | 40.6000 | 38.3000 | 41.3000 |
| net_charge_pH7 | 5 | 1.6820 | 0.9100 | 0.8100 | 2.8000 |
| charge_patch_max7 | 5 | 3.2000 | 3.0000 | 3.0000 | 3.0000 |
| Fv_charge_asymmetry | 5 | 2.2908 | 1.0760 | 0.8280 | 2.9920 |
| hydro_patch_max9 | 5 | 0.6448 | 0.6670 | 0.5560 | 0.6670 |
| SAP_score | 5 | 0.6568 | 0.7140 | 0.5710 | 0.7140 |
| agg_motifs | 5 | 4.8000 | 5.0000 | 4.0000 | 6.0000 |
| hydro_cluster_count | 5 | 3.6000 | 4.0000 | 3.0000 | 4.0000 |
| glycosylation_sites | 5 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| deamidation_sites | 5 | 1.0000 | 1.0000 | 0.0000 | 2.0000 |
| isomerization_sites | 5 | 0.8000 | 1.0000 | 0.0000 | 1.0000 |
| oxidation_sites | 5 | 9.0000 | 9.0000 | 9.0000 | 9.0000 |
| free_cys | 5 | 4.0000 | 4.0000 | 4.0000 | 4.0000 |
| total_cdr_length | 5 | 47.6000 | 48.0000 | 47.0000 | 48.0000 |
| psh | 5 | 771.0340 | 774.8000 | 585.7100 | 1007.2500 |
| ppc | 5 | 2.2600 | 1.0000 | 1.0000 | 4.0000 |
| pnc | 5 | 2.2000 | 2.0000 | 2.0000 | 2.0000 |
| sfvcsp | 5 | 1.6420 | 2.0000 | -2.7900 | 4.0000 |
| vh_vl_angle_deg | 5 | 84.2668 | 83.5154 | 83.0609 | 86.4691 |
| interface_n_pairs | 5 | 64.8000 | 63.0000 | 61.0000 | 69.0000 |
| interface_mean_dist_A | 5 | 4.6917 | 4.7100 | 4.6802 | 4.7109 |
| interface_min_dist_A | 5 | 2.1079 | 2.2254 | 1.9110 | 2.4709 |
| vernier_sasa_total | 5 | 530.3250 | 507.4918 | 502.0647 | 546.4934 |

## vhh — VHH

- n (platform): **47** | matched to Natural384: **0**
- **AbLang2**: pending batch (not in source CSV).

### 25-parameter subset — direct from ADA245 rows (same platform)

| Parameter | n | mean | p50 | p25 | p75 |
| --- | ---: | ---: | ---: | ---: | ---: |
| pI | 42 | 7.4905 | 8.6450 | 5.0175 | 9.0100 |
| GRAVY | 42 | -0.2817 | -0.2887 | -0.3664 | -0.2062 |
| instability_index | 42 | 37.8198 | 37.1600 | 33.6700 | 43.9200 |
| net_charge_pH7 | 42 | 0.8886 | 1.8200 | -2.1775 | 2.8300 |
| hydro_patch_max9 | 18 | 0.6284 | 0.0000 | 0.0000 | 1.7412 |
| agg_motifs | 18 | 1.7222 | 2.0000 | 2.0000 | 2.0000 |

### 25-parameter full keys — Natural384 name match (subset of platform)

| Parameter | n | mean | p50 | p25 | p75 |
| --- | ---: | ---: | ---: | ---: | ---: |

---
_Descriptive stats only; not production reference ranges._
