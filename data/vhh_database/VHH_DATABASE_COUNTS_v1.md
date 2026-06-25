# VHH Database Counts v1

Generated from `data\_reconciliation\VHH_ID_RECONCILIATION.csv`.

## Headline Counts

| Metric | Count |
| --- | ---: |
| identity rows | 70 |
| rows with sequence hash | 69 |
| unique sequence hashes | 46 |
| duplicate sequence groups | 12 |
| no-sequence rows | 1 |
| duplicate excess identity rows | 23 |

## Entity Classes

| Class | Count |
| --- | ---: |
| `clinical_single_domain_vhh` | 39 |
| `database_b_engineered_or_humanized_camelid_vhh` | 29 |
| `humanized_camelid_tandem_vh_fc` | 1 |
| `transgenic_mouse_nanobody_vhh` | 1 |

## Nonredundant Sequence Classes

| Class | Count |
| --- | ---: |
| `clinical_single_domain_vhh` | 26 |
| `database_b_engineered_or_humanized_camelid_vhh` | 19 |
| `transgenic_mouse_nanobody_vhh` | 1 |

## Modality Classes

| Class | Count |
| --- | ---: |
| `single_domain_vhh_or_vh_like` | 69 |
| `tandem_vh_fc_not_single_domain` | 1 |

## Statistical Inclusion

| Class | Count |
| --- | ---: |
| `exclude_sequence_stats_not_single_domain_vhh` | 1 |
| `include_all69_exclude_camelid68_calibration` | 1 |
| `include_database_b29_and_structural_union69` | 29 |
| `include_structural_union69_not_validated39` | 1 |
| `include_validated_clinical39_and_vhh42` | 38 |

## VHH42 Roles

| Class | Count |
| --- | ---: |
| `not_in_vhh42` | 28 |
| `vhh42_clinical_side` | 39 |
| `vhh42_database_b_supplement` | 3 |

## Duplicate Reasons

| Class | Count |
| --- | ---: |
| `alias_or_reused_construct` | 20 |
| `no_sequence` | 1 |
| `pdb_chain_copy` | 15 |
| `unique_sequence` | 34 |

## Interpretation Rules

- Use `entity_class` for cohort membership and reporting.
- Use `vhh42_role` for the mixed VHH42 reference role. VHH42 is not an entity class and must not be described as “42 clinical VHH” or “42 humanized VHH”.
- Use `statistical_inclusion` for whether a row can enter clinical39, VHH42, Database-B, structural-union, or camelid-only calibration statistics.
- Use `canonical_sequence_hash` and `duplicate_group_id` for sequence-level de-duplication. Identity counts and unique-sequence counts must be reported separately.
- Use `VHH_DATABASE_NONREDUNDANT_SEQUENCES_v1.csv` for sequence-level statistics. It has one row per unique sequence hash.
- Use `VHH_DATABASE_EXCLUDED_NON_SDVHH_v1.csv` for non-single-domain molecules such as Lofacimig.
- `clinical_single_domain_vhh` includes validated clinical39 rows except separately-tagged transgenic-mouse rows, plus clinical structural-union-only VHH rows such as Erfonrilimab-VHH2.
- `humanized_camelid_tandem_vh_fc` rows, currently Lofacimig, are clinical molecules with full-chain sequence provenance but excluded from single-domain VHH sequence statistics.
- `transgenic_mouse_nanobody_vhh` rows, currently Porustobart, remain in all-69 union statistics but should be excluded from camelid-only n=68 calibration.
