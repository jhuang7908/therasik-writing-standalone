# Clinical Molecular Fingerprint Taxonomy V0

**Status:** Draft taxonomy based on current repository data  
**Scope:** Data-backed molecular fingerprint classification for AbEngineCore  
**Rule:** Active fingerprint nodes must be supported by existing files and observed cohort counts. Empty or under-specified categories remain reserved.

---

## 1. Executive Summary

The current data structure is sufficient for a first release of a **Clinical Molecular Fingerprint System**, but it is not a final all-category ontology. The first release should be data-backed and conservative:

- Use only observed cohorts as `active`, `active_reference`, or `reference`.
- Keep future categories as `reserved`.
- Do not use raw atlases directly for percentile thresholds when deduplicated or curated cohorts exist.
- Keep molecule families separated: single-domain VH/VHH, VH/VL IgG, bispecific/multispecific, ADA immunogenicity, ADC, scFv, and CAR binder should not share calibration rules.
- Treat this system as a data evidence layer for design scripts, tool development, and owner-approved threshold setting. It must not make autonomous AI judgments or write report conclusions.
- When AI develops tools, proposes rules, or prepares threshold candidates, it must query the relevant database statistics first and cite the cohort, count, release/status, and source file. AI must not invent thresholds from intuition or generic antibody knowledge.

---

## 2. Taxonomy Status Vocabulary

| Status | Meaning | Tool / Threshold Use |
| --- | --- | --- |
| `active` | Curated cohort with enough support for tool design and threshold calibration | Allowed as evidence support |
| `active_reference` | Useful cohort, but small or specialized; use with caution labels | Allowed with caveat |
| `reference` | Useful for interpretation, lookup, or qualitative comparison | No hard thresholds |
| `raw_only` | Raw atlas; may include duplicates or unreviewed records | No threshold use |
| `curation_backlog` | Known data gaps or conflicts | No threshold use |
| `reserved` | Designed category with insufficient current data | No production use |

---

## 3. Top-Level Molecule Families

```text
Clinical Molecular Fingerprint System
├── Single-Domain VH/VHH
├── VH/VL IgG
├── Bispecific / Multispecific Antibody
├── ADA Immunogenicity
├── ADC
├── scFv / scFv-like Binder
├── CAR Binder / Cell-Therapy Binder
└── Reserved / Future Families
```

Only the first four families currently have enough repository-backed structure for first-pass fingerprint organization. ADC, scFv, and CAR binder data exist in the atlas index or design files, but need separate reconciliation before activation.

---

## 4. Single-Domain VH/VHH Fingerprints

```text
Single-Domain VH/VHH
├── clinical_vhh_42
│   ├── clinical_vhh_39
│   └── sabdab_humanized_vhh_3
├── humanized_vhh_29
├── engineered_vh_24
├── single_vh_structural_nr_73
└── single_vh_raw_138
```

| Cohort ID | Count | Status | Primary Use | Source Evidence |
| --- | ---: | --- | --- | --- |
| `clinical_vhh_42` | 42 | `active` | Clinical VHH reference and CMC baseline | `vhh42_cmc_metrics.csv`, VHH reconciliation |
| `clinical_vhh_39` | 39 | `active` | Validated clinical VHH sequence cohort | `vhh_39_sequences_clinical_validated.csv` |
| `sabdab_humanized_vhh_3` | 3 | `reference` | Supplement to clinical VHH42 | VHH reconciliation |
| `humanized_vhh_29` | 29 | `active_reference` | Humanized camelid VHH design reference | `humanized_camelid_vhh_db.json`, VHH reconciliation |
| `engineered_vh_24` | 24 | `active_reference` | Engineered VH / VH-to-single-domain reference | `ENGINEERED_VH24_SITE_MAP.json` |
| `single_vh_structural_nr_73` | 73 unique PDBs | `reference` | Nonredundant structural distribution | `vhh_dbs_build_stats.json` |
| `single_vh_raw_138` | 138 entries | `raw_only` | Search pool and evidence expansion | `autonomous_human_vh_db.json` |

### Single-Domain Use Rules

- VHH clinical and humanization tasks should compare primarily against `clinical_vhh_42` and `humanized_vhh_29`.
- VH-to-VHH or engineered single-domain VH tasks should compare against `engineered_vh_24` and `single_vh_structural_nr_73`, not directly against camelid VHH thresholds.
- `single_vh_raw_138` must not be used for percentile thresholds because it contains 138 entries but only 73 unique PDBs.
- Lofacimig remains metadata-only and should not enter sequence or structural fingerprints until an authoritative sequence is added.

---

## 5. VH/VL IgG Fingerprints

```text
VH/VL IgG
├── humanized_igg_458
├── genetically_human_igg_384
├── standard_igg_overlay
├── adc_igg_overlay
├── fusion_igg_overlay
└── reserved discovery modality labels
    ├── transgenic_mouse
    ├── phage_display
    └── b_cell_sorting
```

| Cohort ID | Count | Status | Primary Use | Source Evidence |
| --- | ---: | --- | --- | --- |
| `humanized_igg_458` | 458 | `active` | Humanized/engineered VH/VL IgG reference | `engineered_459_atlas/master_table.csv` |
| `genetically_human_igg_384` | 384 | `active` | Fully human / genetically human VH/VL IgG reference | `natural_380_atlas/master_table.csv` |
| `standard_igg_overlay` | 401 engineered + 357 natural | `active_reference` | Standard monospecific IgG context | master table `modality=standard` |
| `adc_igg_overlay` | 34 engineered + 14 natural + 5 ADA | `reference` | ADC modality overlay | master table `modality=ADC`, ADA master |
| `fusion_igg_overlay` | 7 engineered + 6 natural | `reference` | Fusion modality overlay | master table `modality=fusion` |
| `transgenic_mouse` | unknown | `reserved` | Future fully-human source stratification | no stable current field |
| `phage_display` | unknown | `reserved` | Future fully-human source stratification | no stable current field |
| `b_cell_sorting` | unknown | `reserved` | Future fully-human source stratification | no stable current field |

### VH/VL Use Rules

- Current fully human subgrouping should use `genetics_normalized=genetically_human`, not platform labels.
- Discovery modality labels such as transgenic mouse, phage display, and B-cell sorting must remain `reserved` until supported by stable metadata or source curation.
- Directory names are not authoritative counts: `natural_380_atlas` has 384 rows and `engineered_459_atlas` has 458 rows.
- Elipovimab and Zinlirvimab are known natural-cohort structural gaps and should not block sequence-level cohort use.

---

## 6. Bispecific / Multispecific Fingerprints

```text
Bispecific / Multispecific Antibody
├── bispecific_125_all
├── bispecific_igg_like_75
├── bispecific_scfv_like_50
└── ada_bispecific_overlap_6
```

| Cohort ID | Count | Status | Primary Use | Source Evidence |
| --- | ---: | --- | --- | --- |
| `bispecific_125_all` | 125 | `active_reference` | Overall bispecific engineering reference | `bispecific_125_knowledge.json` |
| `bispecific_igg_like_75` | 75 | `active_reference` | IgG-like Bi-Ab reference | `bispecific_125_igg_like.json` |
| `bispecific_scfv_like_50` | 50 | `active_reference` | scFv-like, BiTE, tandem scFv, mixed mAb+scFv reference | `bispecific_125_scfv_like.json` |
| `scfv_like_50_sequence_template` | 50 | `reference` | Sequence template support for scFv-like subset | `scfv_like_50_sequences_template.csv` |
| `ada_bispecific_overlap_6` | 6 | `reference` | ADA overlap only; not a bispecific cohort | ADA reconciliation |

### Bispecific Use Rules

- Bispecifics are a separate top-level molecule family, not a VH/VL IgG overlay.
- The currently verified split is **IgG-like 75** and **scFv-like 50**.
- `ada_bispecific_overlap_6` only means six bispecific-like entries appear in ADA data; it must not be used as the bispecific fingerprint size.
- Some records are multispecific or higher-valency formats labeled as bispecific entries; first-pass tools should treat them as bispecific engineering references, not strict two-arm antibodies.

---

## 7. ADA Immunogenicity Fingerprints

```text
ADA Immunogenicity
├── ada_panel_136
├── ada_master_154
├── ada_combined_146
├── ada_negative_312
└── ada_gap_66
```

| Cohort ID | Count | Status | Primary Use | Source Evidence |
| --- | ---: | --- | --- | --- |
| `ada_panel_136` | 136 | `active` | Frozen positive ADA panel with germline/CMC annotations | `immunogenicity_panel_136_master.csv` |
| `ada_master_154` | 154 | `active_reference` | Curated ADA master copy | IKB master `ada_master_136_curated.csv` |
| `ada_combined_146` | 146 | `reference` | Combined ADA DB; needs mismatch cleanup | `InSynBio_Combined_ADA_Database.csv` |
| `ada_negative_312` | 312 | `active_reference` | Negative/reference library | `ada_negative_library_by_phase.csv` |
| `ada_gap_66` | 66 | `curation_backlog` | Known missing metadata list | `ada_curation_gap_list.csv` |

### ADA Use Rules

- `ada_panel_136` is the default active ADA fingerprint source.
- `ada_combined_146` should remain reference until seven ADA% mismatches are corrected.
- Positive and negative cohorts currently have zero overlap, which is the expected state.
- Root-level and IKB master copies are divergent; IKB master should be treated as the future authority unless owner decides otherwise.

---

## 8. ADC, scFv, CAR, and Other Reserved Families

| Family | Current Status | Reason |
| --- | --- | --- |
| `ADC` | `reserved/reference` | ADC entries exist as modality overlays, but no dedicated reconciliation has been completed |
| `scFv` | `reference` | scFv-like bispecific data and 50 sequence templates exist, but standalone scFv fingerprint needs separate audit |
| `CAR_BINDER` | `reserved/reference` | VHH CAR-T entries exist in VHH data, but no dedicated CAR binder reconciliation yet |
| `PET / radiolabeled` | `reserved/reference` | Entries exist in VHH/VHVL modality context, but no dedicated fingerprint release |
| `pet_antibody` | `reserved` | Separate animal-antibody atlas exists; outside current clinical human antibody fingerprint scope |

---

## 9. Proposed Release Manifest Shape

```json
{
  "release_id": "clinical_molecular_fingerprint_v0.1.0",
  "status": "draft",
  "families": {
    "single_domain_vh_vhh": {
      "active": ["clinical_vhh_42"],
      "active_reference": ["humanized_vhh_29", "engineered_vh_24"],
      "reference": ["single_vh_structural_nr_73"],
      "raw_only": ["single_vh_raw_138"]
    },
    "vhvl_igg": {
      "active": ["humanized_igg_458", "genetically_human_igg_384"],
      "active_reference": ["standard_igg_overlay"],
      "reference": ["adc_igg_overlay", "fusion_igg_overlay"]
    },
    "bispecific_multispecific": {
      "active_reference": ["bispecific_125_all", "bispecific_igg_like_75", "bispecific_scfv_like_50"],
      "reference": ["scfv_like_50_sequence_template", "ada_bispecific_overlap_6"]
    },
    "ada_immunogenicity": {
      "active": ["ada_panel_136"],
      "active_reference": ["ada_master_154", "ada_negative_312"],
      "reference": ["ada_combined_146"],
      "curation_backlog": ["ada_gap_66"]
    }
  }
}
```

---

## 10. Implementation Implications

The first API should expose family-aware lookup and avoid cross-family calibration:

```python
profile = store.get_profile(
    molecule_family="single_domain_vh_vhh",
    cohort_id="engineered_vh_24"
)
```

For fallback behavior:

```json
{
  "requested": "single_domain_vh_vhh/engineered_vh_24",
  "matched": "single_domain_vh_vhh/engineered_vh_24",
  "fallback_used": false,
  "profile_status": "active_reference",
  "n": 24
}
```

When a requested category is empty or reserved:

```json
{
  "requested": "vhvl_igg/phage_display",
  "matched": "vhvl_igg/genetically_human_igg_384",
  "fallback_used": true,
  "profile_status": "active",
  "warning": "Requested discovery modality is reserved because current data lacks stable platform labels."
}
```

---

## Verification Status

- `[verified]` Single-domain VHH counts were taken from `VHH_ID_RECONCILIATION_SUMMARY.json`, `vhh42_cmc_metrics.csv`, `ENGINEERED_VH24_SITE_MAP.json`, and `vhh_dbs_build_stats.json`.
- `[verified]` VH/VL IgG counts were taken from `VHVL_IGG_ID_RECONCILIATION.csv` and direct row counts of `natural_380_atlas/master_table.csv` and `engineered_459_atlas/master_table.csv`.
- `[verified]` Bispecific counts were taken from `bispecific_125_knowledge.json`, `bispecific_125_igg_like.json`, and `bispecific_125_scfv_like.json`.
- `[verified]` ADA counts were taken from `ADA_ID_RECONCILIATION_SUMMARY.json` and `ADA_RECON_README.md`.
- `[inferred]` ADC, standalone scFv, CAR binder, PET/radiolabeled, and pet antibody families are reserved because supporting files exist but family-level reconciliation is not complete.

## Adversarial Checks

- **Alternative explanation:** Some `bispecific_125` records include tri-/tetra-/pentaspecific formats but are labeled as bispecific entries. `WARN` — keep them in the engineering reference family, but do not treat all records as strict two-arm bispecifics.
- **Failure mode:** Using raw `single_vh_raw_138` for thresholds would overrepresent repeated PDBs and scaffold families. `PASS` — taxonomy marks it `raw_only`.
- **Boundary condition:** VH/VL fully human source labels such as transgenic mouse, phage display, and B-cell sorting are biologically meaningful but not currently represented by stable fields. `PASS` — taxonomy keeps them `reserved`.
- **Data evolution risk:** Future imported datasets may change counts or activate reserved nodes. `PASS` — release manifest requires versioned cohort IDs and status labels.

## Sources

- `data/_reconciliation/VHH_ID_RECONCILIATION_SUMMARY.json`
- `data/_reconciliation/VHVL_IGG_ID_RECONCILIATION.csv`
- `data/_reconciliation/ADA_ID_RECONCILIATION_SUMMARY.json`
- `data/design_rules/bispecific_125_knowledge.json`
- `data/design_rules/bispecific_125_igg_like.json`
- `data/design_rules/bispecific_125_scfv_like.json`
- `data/vhh_analytics_reports/ENGINEERED_VH24_SITE_MAP.json`
- `data/sabdab_vhh_atlas/vhh_dbs_build_stats.json`
- Local evidence URI: <file:///d:/InSynBio-AI-Research/Antibody_Engineer_Suite/data/_reconciliation/VHH_ID_RECONCILIATION_SUMMARY.json>
- Local evidence URI: <file:///d:/InSynBio-AI-Research/Antibody_Engineer_Suite/data/design_rules/bispecific_125_knowledge.json>
- Upstream structural source reference for SAbDab-derived data: <https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/sabdab>
- Upstream structural source reference for PDB-derived records: <https://www.rcsb.org/>
