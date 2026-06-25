# VHH Data Reconciliation Map

**Status:** Draft governance map  
**Scope:** VHH clinical, SAbDab, Database B, structural union, and CMC reference relationships  
**Generated:** 2026-04-30  
**Last updated:** 2026-04-30 — ANARCI clinical cohort aligned to 39 entries (Ozekibart appended); see §5.

This document is a reconciliation map only. It does not create new thresholds, design rules, clinical claims, or runtime behavior. It should be used to decide which VHH datasets are source cohorts, derived cohorts, model/structure cohorts, frozen benchmarks, report-only artifacts, or caches.

---

## 1. Executive Position

The VHH data family should not be treated as one interchangeable atlas. The current repository contains at least four different VHH count conventions:

| Count | Meaning | Current Best Interpretation |
| ---: | --- | --- |
| **29** | Database B | Humanized/engineered camelid VHH selected from SAbDab-nano and rebuilt with NanoBodyBuilder2 |
| **39** | Clinical local cohort | Clinical VHH sequence/model union used by local structural workflows |
| **40** | `master_table.csv` row count | 39 clinical VHH with sequence + **1 row without sequence** (Lofacimig); not all rows are single-domain VHH |
| **42** | VHH42 CMC benchmark | 39 clinical VHH + 3 SAbDab humanized VHH, frozen for VHH CMC benchmarking |
| **68** | Structural union | 39 clinical VHH + 29 Database B, unified for structural microenvironment analysis |

Recommended rule for discussion:

- Use **VHH42** only for VHH CMC benchmark and population comparison.
- Use **39 clinical local cohort** for clinical VHH sequence/model traceability.
- Use **68 structural union** for structural microenvironment analysis after source cohort audit.
- Use **SAbDab / Database B** as evidence and design-distribution reference, not as clinical hard-gate data.

---

## 2. Dataset Identity Map

| Dataset | Role | Count / Scope | Recommended Status | Notes |
| --- | --- | --- | --- | --- |
| `data/reference/VHH42_reference_stats_v1.json` | Frozen CMC benchmark | 42 entries | **Production benchmark** | `_meta.n = 42`; source described as 39 clinical + 3 SAbDab humanized |
| `data/vhh_clinical_39_union/` | Clinical VHH sequence/model cohort | 39 entries | **Clinical local cohort** | README says validated sequence table and CDR/FR segments are preferred |
| `data/vhh_39_clinical_atlas/master_table.csv` | Historical/source clinical table | 40 rows per manifest | **Source table candidate** | Relationship to 39 validated cohort must be explicitly mapped |
| `data/vhh_clinical_40_anarci/anarci_results.json` | ANARCII (Kabat) numbering snapshot | **count 39** (matches validated clinical 39) | **Processing artifact** | Originally 38: Ozekibart was omitted by `vhh_clinical_40_anarci.py` source JSON; appended via `scripts/reconciliation/append_ozekibart_anarci.py` using `ozekibart_sequence.json` |
| `data/vhh_database_b_union/` | Database B curated structural cohort | 29 entries | **Humanized VHH reference cohort** | Built from SAbDab-nano; includes model outputs and several debug/build scripts |
| `data/sabdab_vhh_atlas/` | SAbDab-derived VHH/VH evidence layer | Database A 138, Database B 29 in stats | **Reference/source layer** | Useful for design distributions, not a direct clinical gate |
| `data/vhh_structural_union/` | Unified structural index | 68 entries | **Structural analysis substrate** | `clinical_n=39`, `database_b_n=29`, `total_n=68` |
| `data/vhh_structural_microenv/` | Structural microenvironment analysis | Derived from structural union | **Derived analysis layer** | Promote only after source union audit |
| `data/vhh_design_atlas_v3.json` | Annotated VHH design atlas | Large annotated JSON | **Design evidence layer** | Contains CDR, hallmark, Vernier annotations; should be schema-audited before SSOT use |
| `data/vhh_database_summary.md` | Human-readable VHH database summary | Four-database summary | **Report-only / frozen summary** | Useful for discussion; should not be treated as machine-readable SSOT |
| `data/vhh_analytics_reports/` | VHH supporting reports | Multiple reports | **Evidence/report layer** | Supports rationale; not runtime input |
| `data/vh_to_vhh_casebank/` | VH-to-VHH casebank and CMC issue rows | Case/failure data | **Failure-mode reference** | Useful for adversarial checks and risk fingerprints |

---

## 3. Relationship Diagram

```text
SAbDab-nano / RCSB
    |
    +-- data/sabdab_vhh_atlas/
    |       +-- autonomous_human_vh_db.json       -> Database A / human autonomous VH evidence
    |       +-- humanized_camelid_vhh_db.json     -> Database B evidence layer
    |       +-- vhh_dbs_build_stats.json          -> Database A/B summary statistics
    |
    +-- data/vhh_database_b_union/
            +-- database_b_manifest_29.json       -> curated 29-entry manifest
            +-- database_b_sequences.json         -> sequence + model path layer
            +-- immunebuilder_models/             -> NanoBodyBuilder2 model outputs

Clinical / literature VHH collection
    |
    +-- data/vhh_39_clinical_atlas/master_table.csv
    |       -> historical/source clinical table, currently described as 40 rows in reference manifest
    |
    +-- data/vhh_clinical_39_union/
            +-- vhh_39_sequences_clinical_validated.csv/json
            +-- vhh_39_cdr_fr_segments.csv/json
            +-- vhh42_cmc_metrics.csv             -> 42-row CMC extraction artifact
            +-- vhh42_germline_assignments.json   -> 42-entry germline assignment artifact
            +-- VHH42_ENHANCEMENT_VERIFICATION.md -> 42-row verification memo

Frozen benchmark layer
    |
    +-- data/reference/VHH42_reference_stats_v1.json
            -> frozen 42-entry VHH CMC benchmark

Structural union layer
    |
    +-- data/vhh_structural_union/vhh_structural_union_index.json
            -> 39 clinical model entries + 29 Database B model entries = 68
    |
    +-- data/vhh_structural_microenv/
            -> derived structural microenvironment analysis
```

---

## 4. Reconciled Usage Matrix

| Use Case | Preferred Dataset | Secondary Evidence | Avoid |
| --- | --- | --- | --- |
| VHH CMC gate / percentile comparison | `data/reference/VHH42_reference_stats_v1.json` | `data/vhh_clinical_39_union/VHH42_ENHANCEMENT_VERIFICATION.md` | Directly using raw 39/40/68 cohorts as CMC benchmarks |
| VHH clinical sequence identity and target traceability | `data/vhh_clinical_39_union/vhh_39_sequences_clinical_validated.*` | `clinical_supplement_curated.json`, `validation_report.txt` | Unvalidated preliminary sequence table |
| VHH CDR/FR clinical segmentation | `data/vhh_clinical_39_union/vhh_39_cdr_fr_segments.*` | ANARCI processing artifacts after reconciliation | Hand-copied or report-only segment tables |
| VHH structural microenvironment analysis | `data/vhh_structural_union/vhh_structural_union_index.json` | `data/vhh_structural_microenv/` | Mixing raw model directories without source cohort IDs |
| Humanized camelid VHH distribution analysis | `data/vhh_database_b_union/database_b_manifest_29.json` and `database_b_sequences.json` | `data/sabdab_vhh_atlas/humanized_camelid_vhh_db.json` | Treating Database B as clinical VHH |
| Autonomous human VH / VH-to-VHH evidence | `data/sabdab_vhh_atlas/autonomous_human_vh_db.json` | `data/vhh_database_summary.md`, `data/vhh_analytics_reports/` | Mixing human VH evidence with camelid VHH CMC gates |
| VH-to-VHH failure mode review | `data/vh_to_vhh_casebank/` | `data/vhh_weak_cases/` | Using weak cases as positive clinical fingerprints |
| Report narrative evidence | `data/vhh_database_summary.md`, `data/vhh_analytics_reports/` | Frozen reference manifest | Report-derived tables as runtime SSOT |

---

## 5. Open Reconciliation Questions

1. **Why does `vhh_39_clinical_atlas/master_table.csv` have 40 rows while `vhh_clinical_39_union` validated sequences list 39?**
   - **Resolved:** Row **Lofacimig** has metadata but **no heavy-chain sequence** in the master table; it does not appear in `vhh_39_sequences_clinical_validated.csv`. See `data/_reconciliation/LOFACIMIG_STATUS.md` for externally verified modality metadata and sequence retrieval guidance.

2. **Why did `vhh_clinical_40_anarci/anarci_results.json` previously report `count: 38`?**
   - **Resolved:** The generator `scripts/vhh_clinical_40_anarci.py` reads `vhh_clinical_antibodies_complete_v2.json`, which **did not include Ozekibart**. Ozekibart’s sequence lives in `data/vhh_clinical_39_union/ozekibart_sequence.json` (Thera-SAbDab/OPIG). **Ozekibart was appended** with `scripts/reconciliation/append_ozekibart_anarci.py`; file now has **39** results, aligned with the validated clinical 39.

3. **Which three SAbDab humanized entries are included in VHH42?**
   - Verification memo lists `1yzz_A`, `3eak_A`, and `6rnk_B`.
   - Required action: ensure these three are present in structural union and CMC extraction metadata.

4. **Is `data/vhh_design_atlas_v3.json` a derived annotation of the 39/42/Database A/B families or an independent mixed atlas?**
   - Required action: schema audit and source-set tagging per entry.

5. **Which files are runtime inputs versus report artifacts?**
   - Required action: map all current code references before promoting any dataset to SSOT.

---

## 6. Proposed Canonical Roles

| Canonical Role | Recommended File / Directory | Promotion Status |
| --- | --- | --- |
| VHH CMC benchmark | `data/reference/VHH42_reference_stats_v1.json` | Already frozen production benchmark |
| VHH clinical validated sequence table | `data/vhh_clinical_39_union/vhh_39_sequences_clinical_validated.csv/json` | Candidate SSOT after ID reconciliation |
| VHH clinical CDR/FR segmentation | `data/vhh_clinical_39_union/vhh_39_cdr_fr_segments.csv/json` | Candidate SSOT after numbering audit |
| VHH42 CMC per-antibody extraction | `data/vhh_clinical_39_union/vhh42_cmc_metrics.csv` | Candidate supporting table, not primary benchmark |
| VHH42 germline assignments | `data/vhh_clinical_39_union/vhh42_germline_assignments.json` | Candidate supporting table |
| Database B manifest | `data/vhh_database_b_union/database_b_manifest_29.json` | Candidate reference cohort |
| Database B sequences and models | `data/vhh_database_b_union/database_b_sequences.json` | Candidate structural evidence layer |
| VHH structural union | `data/vhh_structural_union/vhh_structural_union_index.json` | Structural analysis substrate |
| VHH source/evidence reports | `data/vhh_database_summary.md`, `data/vhh_analytics_reports/` | Report-only evidence layer |

---

## 7. Next Audit Steps

### Step 1 — Identifier Reconciliation

Create a table with one row per VHH identity and these fields:

- `canonical_id`
- `display_name`
- `source_family`: clinical_39, clinical_40_source, vhh42_supplement, database_b, sabdab_atlas
- `sequence_hash`
- `has_validated_sequence`
- `has_anarci`
- `has_cdr_fr_segments`
- `has_cmc_metrics`
- `has_model`
- `included_in_vhh42`
- `included_in_structural_union`

### Step 2 — Count Reconciliation

Resolve:

- 39 validated clinical local entries (with sequence)
- 40 `master_table.csv` rows (39 + Lofacimig without sequence)
- **39** ANARCII-processed clinical entries in `anarci_results.json` (was 38 before Ozekibart append)
- 42 VHH CMC reference entries
- 68 structural union entries

### Step 3 — Source Tagging

Every VHH row used by downstream fingerprint logic should carry one explicit source tag:

- `clinical_vhh`
- `sabdab_humanized_vhh`
- `database_b_humanized_camelid`
- `autonomous_human_vh`
- `engineered_human_vh`
- `weak_or_failure_case`

### Step 4 — Fingerprint Eligibility

Only datasets that pass identifier and source tagging should be eligible for fingerprint extraction:

- CMC fingerprint: VHH42 only.
- Clinical sequence fingerprint: validated 39 clinical cohort.
- Structural microenvironment fingerprint: structural union 68, with source tags preserved.
- Humanized VHH design-distribution fingerprint: Database B plus SAbDab evidence, clearly marked non-clinical unless independently verified.

---

## 8. Recommendation For Discussion

Do not merge all VHH atlases into one master JSON yet. First create an identifier-level reconciliation table. Once counts and source tags are resolved, the project can safely build a read-only `VHHFingerprintSource` layer that loads only approved cohorts by use case.

The immediate priority is therefore:

1. ~~Resolve the 39 / 40 / 38 / 42 / 68 count relationships.~~ **Done** for clinical numbering (39); Lofacimig remains sequence-pending per `LOFACIMIG_STATUS.md`.
2. Mark `VHH42_reference_stats_v1.json` as the only current VHH CMC benchmark.
3. Mark `vhh_structural_union_index.json` as structural-analysis-only until source IDs are reconciled.
4. Keep SAbDab/Database B as reference evidence, not clinical truth.
