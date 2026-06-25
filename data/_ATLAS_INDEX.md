# AbEngineCore Data Atlas Index

**Status:** Draft governance map  
**Scope:** Data inventory, tiering, deduplication targets, and audit priority  
**Generated:** 2026-04-30  

This index is a governance aid only. It does not define new design rules, thresholds, clinical claims, or pipeline behavior. Production rules remain governed by the active standards, frozen reference manifests, and registry entries.

---

## 1. Why This Index Exists

The `data/` directory contains multiple atlas families with overlapping scope: clinical VHH references, SAbDab-derived VHH sets, therapeutic antibody baselines, immunogenicity knowledge bases, CMC references, and modality-specific atlases such as ADC, CAR, bispecific, scFv, Fc, fusion, PET, and radiolabeled antibody sets.

The current risk is not lack of data. The risk is mixing audited production references with exploratory, historical, generated, or partially overlapping datasets. This index separates data into usage tiers so downstream fingerprint work can proceed without turning noisy or duplicate datasets into frozen rules.

---

## 2. Tier Definitions

| Tier | Meaning | Treatment |
| --- | --- | --- |
| **T1 Production SSOT** | Data directly used or suitable for clinical fingerprint, humanization, CMC, immunogenicity, or report gates | Full provenance audit, schema check, deduplication, frozen statistics only after review |
| **T2 Reference Atlas** | Useful for distribution analysis, benchmarking, or method development, but not direct hard gates | Light audit plus distribution statistics; do not use as hard clinical rule without promotion |
| **T3 Scenario Atlas** | Modality-specific datasets used only when the project type requires them | Keep indexed; audit on activation |
| **T4 Historical / Exploratory** | Old, partial, pending, weak-case, or not-yet-analyzed collections | Freeze from production use; revisit only if a project needs them |

---

## 3. Recommended First-Pass Tiering

| Dataset / Directory | Proposed Tier | Primary Use | Governance Note |
| --- | ---: | --- | --- |
| `data/reference/` | T1 | Frozen CMC and numbering references | Already has `MANIFEST.md`; treat as locked production reference family |
| `data/humanization_assay/` | T1 | AbRef-458 / therapeutic antibody CMC baseline source | Read-only data source; avoid ad hoc edits |
| `data/germlines/` | T1 | Human / species germline references and Kabat caches | Must remain versioned and cache-aware |
| `data/vernier_zones/` | T1 | VH/VL framework and CDR-supporting residue logic | Directly relevant to back-mutation decisions |
| `data/immunogenicity_knowledge_base/` | T1 | ADA and immunogenicity evidence base | Needs provenance and duplicate control before clinical reporting |
| `data/cmc_rules/` / `data/rules/` | T1 | CMC rule inputs and rule snapshots | Must not diverge from standards and registry |
| `data/vhh_clinical_39_union/` | T1 | Clinical VHH structure/model cohort | Needs reconciliation with VHH42 nomenclature |
| `data/vhh_39_clinical_atlas/` | T1 candidate | Historical/source clinical VHH table | Candidate source for VHH42; needs relationship mapping |
| `data/vhh_database_b_union/` | T1 candidate | Humanized camelid VHH Database B, 29 entries | Strong candidate for VHH fingerprint source, but currently includes build/debug scripts |
| `data/vhh_structural_union/` | T1 candidate | 39 clinical + 29 Database B structural union | Good structural analysis substrate; should depend on audited source cohorts |
| `data/vhh_structural_microenv/` | T2 | VHH structural microenvironment analysis | Promote only after source union is audited |
| `data/sabdab_vhh_atlas/` | T2 | SAbDab-derived VHH/VH source, humanized VHH, cached FASTA | High-value source/reference, not itself a clinical hard gate |
| `data/sabdab_nano/` | T2 | SAbDab-nano source material | Use for reproducibility and source tracing |
| `data/vhh_database_summary.md` | T2 / frozen report | Human-readable VHH database summary | Report states frozen; should be linked to authoritative machine-readable source |
| `data/vhh_design_atlas_v3.json` | T2 candidate | VHH design atlas summary | Needs schema and source reconciliation before SSOT use |
| `data/vhh_analytics_reports/` | T2 | Analysis reports supporting VHH rules | Evidence layer; not direct runtime input |
| `data/vh_to_vhh_casebank/` | T2 | VH-to-VHH conversion casebank and CMC issues | Useful for failure-mode fingerprints |
| `data/thera_sabdab/` | T2 | Therapeutic antibody structure/reference material | Useful for benchmarking and validation |
| `data/natural_380_atlas/` | T2 / T1 reference source | Natural IgG baseline source | Already referenced by `data/reference/`; source should remain traceable |
| `data/engineered_459_atlas/` | T2 / T1 reference source | Engineered therapeutic antibody baseline source | Used for AbRef-type distributions; avoid direct hard gates unless frozen |
| `data/ADA_antibody_database_package/`, `data/ADA_reliable_package/` | T2 | ADA evidence packages | Needs reconciliation with master ADA files |
| `data/adc_atlas/` | T3 | ADC-specific antibody design / immunogenicity context | Audit only when ADC workflow is active |
| `data/CAR/` | T3 | CAR-T library and traceability | Separate CAR standard governs use |
| `data/bispecific_75_atlas/` | T3 | Bispecific antibody/VHH design references | Audit when bispecific workflow is active |
| `data/scfv_52_atlas/` | T3 | scFv design and developability references | Audit before scFv fingerprint use |
| `data/fc_atlas/` | T3 | Fc engineering and constant-region references | Keep separate from Fv humanization fingerprints |
| `data/fab_fusion_atlas/` | T3 | Fab fusion modality references | Scenario-specific |
| `data/fusion_protein_atlas/` | T3 / T4 | Fusion protein references | Classify by active project demand |
| `data/radiolabeled_atlas/` | T3 | Radiolabeled antibody references | Scenario-specific |
| `data/pet_antibody_atlas/` | T3 | PET antibody references | Scenario-specific |
| `data/multispecific_scfv_atlas/` | T3 | Multispecific scFv references | Scenario-specific |
| `data/whole_mab_chimeric_atlas/` | T4 | Chimeric whole-mAb historical or exploratory set | Freeze unless a project requests it |
| `data/other_thera_ab/` | T4 | Miscellaneous therapeutic antibody material | Needs source and purpose review |
| `data/thera_not_analyzed/` | T4 | Pending therapeutic antibodies | Not production-ready |
| `data/vhh_weak_cases/` | T4 | Weak/failure cases | Valuable for adversarial checks, not positive fingerprint source |
| `data/input sequence/` | T4 | User/project inputs | Do not mix into reference fingerprints |
| `data/sequence_cache/` | T4 | Runtime/cache material | Not a reference atlas |
| `data/structures/` | T4 / cache | Structure files and generated models | Use only with provenance records |
| `data/templates/` | T2/T3 | Structural or report templates | Classify by consuming workflow |
| `data/features/` | T2/T4 | Extracted features | Needs source mapping |
| `data/design_rules/` | T1 candidate | Design-rule data | Must match standards and registry before production use |
| `data/clinical_kb/` | T1 candidate | Clinical knowledge base | Needs schema/provenance audit |
| `data/knowledge/` | T2/T4 | General knowledge artifacts | Needs source status review |
| `data/species_profiles/` | T2/T3 | Species-specific profiles | Useful for non-human or veterinary workflows |
| `data/actes_sequences/` | T4 | Sequence collection | Needs project/source review |
| `data/benchmarks/` | T2 | Benchmarking data | Keep separate from clinical reference fingerprints |
| `data/repertoire/` | T2 | Repertoire references | Useful for background distributions, not clinical hard gates |

---

## 4. Immediate Deduplication Targets

### VHH Clinical / VHH42 Family

The following names likely represent overlapping views of the same VHH clinical and humanized-reference universe:

- `data/vhh_39_clinical_atlas/`
- `data/vhh_clinical_39_union/`
- `data/vhh_clinical_40_anarci/`
- `data/reference/VHH42_reference_stats_v1.json`
- `data/vhh_structural_union/`
- `data/vhh_design_atlas_v3.json`

Recommended decision:

- Treat `data/reference/VHH42_reference_stats_v1.json` as the frozen CMC benchmark until replaced by an approved standard upgrade.
- Treat `data/vhh_clinical_39_union/` and `data/vhh_structural_union/` as structural/model substrates, not independent clinical-count authorities.
- Preserve the distinction between **39 clinical local structures** and **42 VHH CMC reference entries**.

### VHH Database A / B / SAbDab Family

The following form a second overlapping VHH evidence family:

- `data/sabdab_vhh_atlas/`
- `data/sabdab_nano/`
- `data/vhh_database_b_union/`
- `data/vhh_database_summary.md`
- `data/vhh_analytics_reports/`

Recommended decision:

- Keep `sabdab_nano` and `sabdab_vhh_atlas` as source/reference layers.
- Keep `vhh_database_b_union` as the curated Database B structural cohort, pending audit.
- Keep `vhh_database_summary.md` as a human-readable report, not the machine-readable SSOT.

### Therapeutic IgG / CMC Family

The following datasets are related but not interchangeable:

- `data/humanization_assay/`
- `data/engineered_459_atlas/`
- `data/natural_380_atlas/`
- `data/reference/AbRef458_stats_v1.json`
- `data/reference/Natural384_IgG_stats_v1.json`

Recommended decision:

- Use `data/reference/` frozen files for runtime gates.
- Use source atlases only for traceability or regeneration under approved governance.
- Do not compare VHH42 ADI directly against AbRef-458 or Natural384 ADI without format-specific scoring context.

### ADA / Immunogenicity Family

The following require reconciliation before being used as a unified immunogenicity fingerprint source:

- `data/ada_master_136_curated.csv`
- `data/immunogenicity_knowledge_base/`
- `data/ADA_antibody_database_package/`
- `data/ADA_reliable_package/`
- `data/immunogenicity/`

Recommended decision:

- Identify one master table for reportable ADA evidence.
- Keep raw packages and processing scripts traceable but out of runtime decision logic unless validated.

---

## 5. Audit Checklist By Tier

### T1 Full Audit

- Source provenance and license/status.
- Unique identifier normalization.
- Duplicate sequence and duplicate antibody detection.
- Sequence alphabet and chain-type validation.
- Kabat / IMGT numbering consistency where applicable.
- CDR boundary reproducibility.
- Germline assignment reproducibility.
- Structural artifact provenance for PDB/model entries.
- CMC metric definition and version alignment.
- Reported cohort count consistency across docs, JSON, CSV, and registry.

### T2 Light Audit

- File presence and schema readability.
- Required identifiers and sequence fields.
- Cohort count and source consistency.
- Distribution statistics only after basic validation.
- Clear label: reference-only, not production gate.

### T3 Activation Audit

- Confirm active standard and workflow.
- Confirm modality-specific schema.
- Confirm which data can influence design and which data is informational.
- Promote only the required subset to T1/T2 after review.

### T4 Freeze Review

- Confirm no production code depends on the dataset.
- Preserve only if it supports traceability, adversarial analysis, or future project demand.
- Never use as a positive clinical fingerprint source without re-audit.

---

## 6. Recommended Work Plan

1. **Phase 0 — Inventory Freeze**
   - Keep this file as the working map.
   - Do not move or delete datasets during the first pass.

2. **Phase 1 — VHH Reconciliation**
   - Map VHH39, VHH40, VHH42, Database B29, structural union 68, and SAbDab-derived files.
   - Produce one relationship table: source cohort, derived cohort, generated model, frozen reference, report-only artifact.

3. **Phase 2 — Production Fingerprint Candidates**
   - Promote only audited VHH and IgG CMC references into a fingerprint candidate schema.
   - Keep VHH, VH/VL, scFv, ADC, bispecific, Fc, CAR, and fusion fingerprints separated by antibody format and use case.

4. **Phase 3 — API Design**
   - Add a read-only fingerprint resolver conceptually shaped as:
     `antibody_type + task + target_class + modality -> allowed reference families`.
   - Do not let pipelines load arbitrary atlas files by path.

5. **Phase 4 — Reporting**
   - Surface only audited fingerprint alignment in reports.
   - Label non-audited comparisons as exploratory.

---

## 7. Immediate Recommendation

Start with VHH because it has the highest overlap and highest commercial value:

- Reconcile `vhh_39_clinical_atlas`, `vhh_clinical_39_union`, `vhh_clinical_40_anarci`, `VHH42_reference_stats_v1.json`, `vhh_database_b_union`, and `vhh_structural_union`.
- Produce a single VHH source-of-truth relationship diagram before calculating new fingerprints.
- Only then compute Hallmark, CDR, Vernier, CMC, and structural microenvironment distributions.

This prevents duplicated VHH datasets from becoming contradictory fingerprints.
