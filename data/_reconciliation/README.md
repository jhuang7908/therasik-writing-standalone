# VHH ID Reconciliation Outputs

**Status:** Read-only governance artifact
**Generator:** `scripts/reconciliation/build_vhh_id_reconciliation.py`
**Scope:** Cross-walk of VHH identifiers across clinical, ANARCI, VHH42, Database B, and structural-union datasets
**Last updated:** 2026-04-30 — `anarci_results.json` now has **39** clinical Kabat summaries (Ozekibart appended). Reconciliation `rows_with_anomalies` is **0**. Lofacimig remains **metadata-only** (no sequence in master table); see `LOFACIMIG_STATUS.md`.

This folder contains derived reconciliation tables only. It does not introduce new design rules, thresholds, or pipeline behavior. All production logic remains governed by the active standards, frozen reference manifests, and registry entries.

---

## Files

| File | Format | Purpose |
| --- | --- | --- |
| `VHH_ID_RECONCILIATION.csv` | CSV | One row per canonical VHH identity, with source-membership flags |
| `VHH_ID_RECONCILIATION.json` | JSON | Same content with full metadata for tooling |
| `VHH_ID_RECONCILIATION_SUMMARY.json` | JSON | Source counts, expected counts, anomaly totals |

---

## CSV Columns

| Column | Meaning |
| --- | --- |
| `canonical_id` | Slug derived from antibody name |
| `display_name` | First non-empty display name observed across sources |
| `origin_tags` | Cohort tags such as `clinical_vhh`, `database_b_humanized_camelid`, `sabdab_humanized_vhh`, `master_table_only_no_seq` |
| `in_clinical_39` | Present in `vhh_39_sequences_clinical_validated.csv` |
| `in_master_table_40` | Present in `vhh_39_clinical_atlas/master_table.csv` |
| `in_anarci_38` | Present in `vhh_clinical_40_anarci/anarci_results.json` (column name is legacy; file holds **39** clinical numbering rows after Ozekibart was appended) |
| `in_vhh42_cmc` | Present in `vhh42_cmc_metrics.csv` |
| `in_vhh42_germline` | Present in `vhh42_germline_assignments.json` |
| `in_database_b_29` | Present in `vhh_database_b_union/database_b_manifest_29.json` |
| `in_structural_union_69` | Present in `vhh_structural_union_index.json` (69-model union: 40 clinical bucket + 29 Database-B) |
| `canonical_sequence_hash` | First-12 SHA1 over the upper-case sequence |
| `sequence_consistent_across_sources` | True when every source either omits the sequence or yields the same hash |
| `anomalies` | Semicolon-separated set of automated checks that failed |
| `vhh42_cmc_origin` | `clinical` or `SAbDab_humanized` from VHH42 CMC table |
| `germline_top_match` | Top human germline assignment for ADA risk lookup |
| `ada_majority_risk` | ADA risk label from VHH42 germline assignments |
| `structural_pdb_model` | Path to ImmuneBuilder/NanoBodyBuilder2 model where available |
| `cohort_platform_tag` | From `data/vhh_structural_union/vhh_platform_labels_v1.json` — e.g. `transgenic_mouse_nanobody` (Porustobart), `humanized_camelid_tandem_vh_fc` (Lofacimig); empty if unlabeled |

---

## Source Counts (current state)

**Unified glossary:** `VHH_COHORT_DEFINITIONS.md`. **File-derived counts:** `python scripts/audit_vhh_cohort_counts.py --json-out data/_reconciliation/vhh_cohort_counts_snapshot.json`.

| Source | Count | Notes |
| --- | --- | --- |
| `clinical_39` | 39 | Validated clinical VHH cohort with sequence |
| `master_table_40` | 40 | 39 clinical with sequence + 1 sequence-less entry (Lofacimig) |
| `anarci_38` | **39** | Aligns with validated clinical 39; Ozekibart was missing from the original `vhh_clinical_40_anarci.py` source JSON and was appended via `scripts/reconciliation/append_ozekibart_anarci.py` |
| `vhh42_cmc` | 42 | 39 clinical + 3 SAbDab humanized supplement |
| `vhh42_germline` | 42 | Same composition as VHH42 CMC |
| `database_b_29` | 29 | Humanized/engineered camelid VHH from SAbDab-nano |
| `structural_union_69` | **69** | **40** clinical-bucket + **29** Database-B models (`vhh_structural_union_index.json` `_meta`; matches `vhh68_special_cmc_results.json`) |

The **69-row** structural/CMC union is **40 + 29**, not 39 + 29. Validated clinical **sequences** remain **39**; **Lofacimig** is an extra atlas row without a production sequence row.

The 3 SAbDab entries used to extend VHH42 (`1yzz_A`, `3eak_A`, `6rnk_B`) lie **inside** the 29 Database-B identities — they do not increase the union beyond **69**.

---

## Anomaly Categories

The script raises only conservative, deterministic anomalies. **Current run:** zero anomalies after Ozekibart was added to `anarci_results.json`. Reference categories:

| Anomaly | Meaning | Action |
| --- | --- | --- |
| `missing_in_anarci` | Clinical entry exists in the validated 39 cohort but is absent from `anarci_results.json` | Investigate ANARCI run to recover the missing entry |
| `clinical_missing_in_vhh42_cmc` | Clinical entry not in VHH42 CMC table | Confirm CMC extraction coverage |
| `vhh42_cmc_only_no_source_cohort` | Entry appears in VHH42 CMC but not in clinical or Database B | Confirm supplement provenance |
| `db_b_missing_in_structural_union` | Database B entry not in structural union | Confirm structural pipeline |
| `sequence_hash_mismatch_across_sources` | Same canonical ID has different sequence hashes in different sources | Resolve source-of-truth conflict |
| `master_table_only_no_seq` (origin tag) | Identity exists only in master_table without sequence (e.g. Lofacimig) | Decide whether to seek sequence or accept as sequence-less reference |

---

## Regeneration

```powershell
python scripts/reconciliation/build_vhh_id_reconciliation.py
```

Outputs are overwritten in place. The script does not write outside `data/_reconciliation/`.

---

## Intended Use

This reconciliation table should be consulted before any future fingerprint extraction, statistical aggregation, or registry promotion that mixes VHH datasets. It enables:

- Choosing the correct source cohort per use case (CMC benchmark, clinical sequence fingerprint, structural microenvironment).
- Detecting silent identifier drift between historical CSV/JSON files.
- Surfacing data-quality anomalies before they propagate into design or reporting logic.

It does not replace the governing standards or frozen reference manifests.
