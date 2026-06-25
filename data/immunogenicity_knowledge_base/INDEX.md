# Immunogenicity Knowledge Base — Index

**Path**: `data/immunogenicity_knowledge_base/`  
**Last updated**: 2026-04-04  
**Scope**: 138-antibody ADA panel + all associated evidence, metadata, and model files

---

## Query Tools (Recommended Entry Points)

### Web Interface (interactive)
Open in browser: `docs/ada_database.html`  
Requires `docs/ada_db_data.json` in the same directory.  
Features: live search, filter by origin/disease/route/MHC-II risk, sortable table, click-to-expand detail panel with MHC-II cluster stack bar, SASA hydrophilic gauge, CMC parameters, evidence text, and citation links.

### Python API (programmatic)
```python
from core.immunogenicity.ada_reference_query import ADAReference
db = ADAReference()

# Client brings new anti-IL-17 SC antibody → look up comparators
db.full_report("IL17", route="SC", disease="autoimmune")

# Simple target search
db.query_target("VEGF")

# Compare by Fc type
db.compare_fc("IgG4")
```

> **Purpose**: local clinical reference only — not a predictive algorithm.
> Outputs same-target ADA comparators, disease-class benchmarks, and interpretation caveats.

---

## Quick Reference

| Need | File | Subdir |
|---|---|---|
| **Master table (138 antibodies, all fields)** | `ada_master_136_curated.csv` | `master/` |
| **ADA evidence chain + tiers** | embedded in master table | `master/` |
| **Clinical confounders (70)** | `clinical_confounders_70.csv` | `clinical_metadata/` |
| **Clinical confounders (66 new)** | `curated_66_clinical_metadata.csv` | `clinical_metadata/` |
| **Route + disease context flags** | `route_and_context.csv` | `clinical_metadata/` |
| **ADA clinical DB — index (170 entries)** | `clinical_ada_db_index.json` | `ada_evidence/` |
| **ADA clinical DB — full evidence chains** | `clinical_ada_db_data.json` | `ada_evidence/` |
| **Confirmed ADA evidence report (80)** | `confirmed_ada.md` | `ada_evidence/` |
| **ADA QA consistency audit** | `ada_evidence_consistency_final_report.md` | `ada_evidence/` |
| **V2 scorer config** | `immunogenicity_risk_v2.json` | `model_config/` |
| **V2 scorer calibration** | `calibrated_params.json` | `model_config/` |
| **Evidence + coverage report** | `ADA_Master_136_Evidence_Report.md` | `reports/` |
| **ADA confounder discussion** | `ADA_Review_Discussion_Notes.md` | `reports/` |
| **V2 prediction results** | `ADA_V2_Prediction_Results.md` | `reports/` |
| **70-antibody LOO study (HTML)** | `immunogenicity_study.html` | `reports/` |
| **Full evidence chains (natural)** | `clinical_ada_full_evidence_report.md` | `reports/` |
| **Full evidence chains (engineered)** | `clinical_ada_engineered_evidence_report.md` | `reports/` |
| **136-panel PDB structures (131)** | `<AntibodyName>.pdb` | `structures/` |

---

## External Bulk Stores (atlas-level, not copied here)

| Store | Path | Contents |
|---|---|---|
| PDB atlas — natural (380+) | `data/structures/natural/` | Full natural antibody atlas |
| PDB atlas — engineered (459+) | `data/structures/engineered/` | Full engineered antibody atlas |
| ADA merged multi-source | `data/ADA_reliable_package/ada_merged_multisource.json` | 427KB |
| 151-antibody evidence DB | `data/ADA_reliable_package/sources/151_antibody_evidence_database.json` | 513KB |

---

## Column Guide for Master Table

Key column groups in `master/ada_master_136_curated.csv`:

| Group | Key Columns |
|---|---|
| Identity | `antibody_name`, `origin`, `thera_genetics_class` |
| Disease | `targets`, `indication_text`, `disease_class_curated` |
| Fc | `fc_isotype`, `fc_engineering`, `fc_effector_status`, `fc_mutation_notes` |
| Dosing | `route_curated`, `dose_mg`, `dose_freq`, `half_life_days` |
| Assay | `assay_platform`, `assay_generation` |
| Co-medication | `mtx_comedication`, `immunosuppressant_context` |
| Clinical ADA | `ada_value_display`, `ada_first_pct`, `evidence_tier`, `ada_evidence_chain_excerpt`, `ada_source_url_primary` |
| Sequence | `vh_seq`, `vl_seq`, `vh_fr1..vh_fr4`, `vl_fr1..vl_fr4` |
| Germline | `vh_germline_identity`, `vl_germline_identity`, `vh_germline_imgt` |
| Structure | `pdb_path`, `vh_vl_angle_deg`, `interface_n_pairs` |
| CMC | `pI`, `GRAVY`, `instability_index`, `hydro_patch_max9`, `cmc_flags` |
| MHC-II | `immuno_tcia_score`, `immuno_n_high`, `immuno_n_clusters` |
| SASA/HLA | `surf_frac_exposed_vh`, `surf_n_patches`, `surf_risk` |
| V2 model | `ada_v2_score`, `ada_v2_risk` *(model-derived, not clinical fact)* |

---

## Evidence Tier Definitions

- **Tier A** (101/138, 73%): ADA value anchored to PMID / FDA label / ClinicalTrials.gov
- **Tier B** (37/138, 27%): Verified URL; ADA number confirmed; evidence narrative may be AI-paraphrased
- **Tier C**: 0 — all formerly-Tier-C entries were upgraded (Tier A/B) or removed (Etesevimab, revoked EUA)

---

## Scripts That Built This Table

| Script | Role |
|---|---|
| `scripts/build_ada_master_curated.py` | Steps 1-3: schema + local merge + gap audit |
| `scripts/curate_66_clinical_metadata.py` | Curate clinical metadata for 66 non-P70 antibodies |
| `scripts/merge_curated_66.py` | Merge curated 66 into master |
| `scripts/fill_p70_indications.py` | Fill indication/disease for P70 antibodies |
| `scripts/export_ada_master_final.py` | Final column ordering + evidence report |
| `scripts/consolidate_knowledge_base.py` | **This script** — creates this KB directory |

*Single entry point for all immunogenicity research data.*