"""
Consolidate all immunogenicity/ADA/HLA/structure evidence files
into a single canonical directory: data/immunogenicity_knowledge_base/

Strategy:
  - MOVE scattered root-level & docs-level files into KB (they have no other canonical home)
  - COPY small key CSVs / JSONs into KB/master/ and KB/model_config/ for one-stop access
  - Large bulk stores (data/structures/, data/ADA_reliable_package/) stay in place;
    their paths are documented in INDEX.md
  - Creates a comprehensive INDEX.md as the single entry point
"""
import os, shutil
from pathlib import Path

BASE = Path(".")
KB   = BASE / "data/immunogenicity_knowledge_base"

SUB = [
    "master",           # master tables (CSV)
    "clinical_metadata",# clinical confounders, route, curated 66
    "ada_evidence",     # ADA DB subsets, evidence chains, reports
    "reports",          # MD/HTML synthesis reports
    "model_config",     # V2 scorer config, calibration params
    "structures_ref",   # VHH reference PDB files (moved from docs/)
]

print("Creating directory structure...")
for s in SUB:
    (KB / s).mkdir(parents=True, exist_ok=True)

# ── MOVE: scattered root-level evidence reports ──────────────────────────────
MOVE_TASKS = [
    # (source, dest_subdir, new_name_optional)
    ("clinical_ada_full_evidence_report.md",              "reports", None),
    ("clinical_ada_engineered_evidence_report.md",        "reports", None),
    ("docs/ADA_Master_136_Evidence_Report.md",            "reports", None),
    ("docs/ADA_Review_Discussion_Notes.md",               "reports", None),
    ("docs/ADA_V2_Prediction_Results.md",                 "reports", None),
    ("docs/vhh_her2_haddock_best.pdb",                    "structures_ref", None),
    ("docs/vhh_her2_haddock_clean.pdb",                   "structures_ref", None),
    ("docs/vhh_her2_view.pdb",                            "structures_ref", None),
]

moved = []
for src_rel, subdir, newname in MOVE_TASKS:
    src = BASE / src_rel
    if not src.exists():
        print("  SKIP (not found): {}".format(src_rel))
        continue
    dst = KB / subdir / (newname or src.name)
    shutil.move(str(src), str(dst))
    moved.append((src_rel, str(dst.relative_to(BASE))))
    print("  MOVED: {} → {}".format(src_rel, dst.relative_to(BASE)))

# ── COPY: key master tables & metadata (keep originals in place) ─────────────
COPY_TASKS = [
    ("data/ada_master_136_curated.csv",                        "master"),
    ("data/immunogenicity_panel_136_master.csv",               "master"),
    ("data/ada_curation_gap_list.csv",                         "master"),
    ("data/curated_66_clinical_metadata.csv",                  "clinical_metadata"),
    ("data/reference/clinical_confounders_70.csv",             "clinical_metadata"),
    ("data/reference/route_and_context.csv",                   "clinical_metadata"),
    ("data/reference/ada_calibration/calibrated_params.json",  "model_config"),
    ("config/immunogenicity_risk_v2.json",                     "model_config"),
    ("data/ADA_reliable_package/clinical_db/clinical_ada_db_index.json",  "ada_evidence"),
    ("data/ADA_reliable_package/study_materials/confirmed_ada.md",        "ada_evidence"),
    ("data/ADA_reliable_package/qa/ada_evidence_consistency_final_report.md", "ada_evidence"),
]

copied = []
for src_rel, subdir in COPY_TASKS:
    src = BASE / src_rel
    if not src.exists():
        print("  SKIP (not found): {}".format(src_rel))
        continue
    dst = KB / subdir / src.name
    shutil.copy2(str(src), str(dst))
    copied.append((src_rel, str(dst.relative_to(BASE))))
    print("  COPIED: {} → {}".format(src_rel, dst.relative_to(BASE)))

# ── COPY immunogenicity_study.html into reports (it's public-facing) ────────
study = BASE / "docs/immunogenicity_study.html"
if study.exists():
    shutil.copy2(str(study), str(KB / "reports" / "immunogenicity_study.html"))
    print("  COPIED: docs/immunogenicity_study.html → reports/")

# ── Generate INDEX.md ─────────────────────────────────────────────────────────
idx_lines = [
"# Immunogenicity Knowledge Base — Index\n",
"**Path**: `data/immunogenicity_knowledge_base/`  ",
"**Last updated**: 2026-04-03  ",
"**Scope**: 136-antibody ADA panel + all associated evidence, metadata, and model files\n",
"---\n",
"## Quick Reference\n",
"| Need | File | Subdir |",
"|---|---|---|",
"| **Master table (136 antibodies, all fields)** | `ada_master_136_curated.csv` | `master/` |",
"| **ADA evidence chain + tiers** | embedded in master table | `master/` |",
"| **Clinical confounders (70)** | `clinical_confounders_70.csv` | `clinical_metadata/` |",
"| **Clinical confounders (66 new)** | `curated_66_clinical_metadata.csv` | `clinical_metadata/` |",
"| **Route + disease context flags** | `route_and_context.csv` | `clinical_metadata/` |",
"| **ADA clinical DB (index, 170 entries)** | `clinical_ada_db_index.json` | `ada_evidence/` |",
"| **Confirmed ADA evidence report (80)** | `confirmed_ada.md` | `ada_evidence/` |",
"| **ADA QA consistency audit** | `ada_evidence_consistency_final_report.md` | `ada_evidence/` |",
"| **V2 scorer config** | `immunogenicity_risk_v2.json` | `model_config/` |",
"| **V2 scorer calibration** | `calibrated_params.json` | `model_config/` |",
"| **Evidence + coverage report** | `ADA_Master_136_Evidence_Report.md` | `reports/` |",
"| **ADA confounder discussion** | `ADA_Review_Discussion_Notes.md` | `reports/` |",
"| **V2 prediction results** | `ADA_V2_Prediction_Results.md` | `reports/` |",
"| **70-antibody LOO study (HTML)** | `immunogenicity_study.html` | `reports/` |",
"| **Full evidence chains (natural)** | `clinical_ada_full_evidence_report.md` | `reports/` |",
"| **Full evidence chains (engineered)** | `clinical_ada_engineered_evidence_report.md` | `reports/` |",
"| **VHH-HER2 reference structures** | `vhh_her2_*.pdb` | `structures_ref/` |",
"\n---\n",
"## External Bulk Stores (not copied — too large)\n",
"| Store | Path | Contents |",
"|---|---|---|",
"| PDB structures (natural, 380+) | `data/structures/natural/` | ~380 homology models |",
"| PDB structures (engineered, 459+) | `data/structures/engineered/` | ~459 homology models |",
"| ADA clinical full DB | `data/ADA_reliable_package/clinical_db/clinical_ada_db_data.json` | Full evidence chains (728KB) |",
"| ADA merged multi-source | `data/ADA_reliable_package/ada_merged_multisource.json` | 427KB |",
"| 151-antibody evidence DB | `data/ADA_reliable_package/sources/151_antibody_evidence_database.json` | 513KB |",
"\n---\n",
"## Column Guide for Master Table\n",
"Key column groups in `master/ada_master_136_curated.csv`:\n",
"| Group | Key Columns |",
"|---|---|",
"| Identity | `antibody_name`, `origin`, `thera_genetics_class` |",
"| Disease | `targets`, `indication_text`, `disease_class_curated` |",
"| Fc | `fc_isotype`, `fc_engineering`, `fc_effector_status`, `fc_mutation_notes` |",
"| Dosing | `route_curated`, `dose_mg`, `dose_freq`, `half_life_days` |",
"| Assay | `assay_platform`, `assay_generation` |",
"| Co-medication | `mtx_comedication`, `immunosuppressant_context` |",
"| Clinical ADA | `ada_value_display`, `ada_first_pct`, `evidence_tier`, `ada_evidence_chain_excerpt`, `ada_source_url_primary` |",
"| Sequence | `vh_seq`, `vl_seq`, `vh_fr1..vh_fr4`, `vl_fr1..vl_fr4` |",
"| Germline | `vh_germline_identity`, `vl_germline_identity`, `vh_germline_imgt` |",
"| Structure | `pdb_path`, `vh_vl_angle_deg`, `interface_n_pairs` |",
"| CMC | `pI`, `GRAVY`, `instability_index`, `hydro_patch_max9`, `cmc_flags` |",
"| MHC-II | `immuno_tcia_score`, `immuno_n_high`, `immuno_n_clusters` |",
"| SASA/HLA | `surf_frac_exposed_vh`, `surf_n_patches`, `surf_risk` |",
"| V2 model | `ada_v2_score`, `ada_v2_risk` *(model-derived, not clinical fact)* |",
"\n---\n",
"## Evidence Tier Definitions\n",
"- **Tier A** (94/136, 69%): ADA value anchored to PMID / FDA label / ClinicalTrials.gov",
"- **Tier B** (36/136, 26%): Verified URL; ADA number confirmed; evidence narrative may be AI-paraphrased",
"- **Tier C** (6/136, 4%): Known data quality issues — exclude from quantitative analyses\n",
"---\n",
"## Scripts That Built This Table\n",
"| Script | Role |",
"|---|---|",
"| `scripts/build_ada_master_curated.py` | Steps 1-3: schema + local merge + gap audit |",
"| `scripts/curate_66_clinical_metadata.py` | Curate clinical metadata for 66 non-P70 antibodies |",
"| `scripts/merge_curated_66.py` | Merge curated 66 into master |",
"| `scripts/fill_p70_indications.py` | Fill indication/disease for P70 antibodies |",
"| `scripts/export_ada_master_final.py` | Final column ordering + evidence report |",
"| `scripts/consolidate_knowledge_base.py` | **This script** — creates this KB directory |",
"\n*Single entry point for all immunogenicity research data.*",
]

idx_path = KB / "INDEX.md"
with open(idx_path, "w", encoding="utf-8") as f:
    f.write("\n".join(idx_lines))
print("\nCreated: {}".format(idx_path))

# ── Summary ──────────────────────────────────────────────────────────────────
print("\n=== CONSOLIDATION COMPLETE ===")
print("Knowledge base root: {}".format(KB))
print("Subdirectories: {}".format(", ".join(SUB)))
print("Files moved: {}".format(len(moved)))
print("Files copied: {}".format(len(copied)))
print("\nDirectory tree:")
for sub in SUB:
    subdir = KB / sub
    files = list(subdir.iterdir()) if subdir.exists() else []
    print("  {}/  ({} files)".format(sub, len(files)))
    for f in sorted(files)[:8]:
        size = f.stat().st_size
        print("    {:50s} {:>6.0f}K".format(f.name, size/1024))
    if len(files) > 8:
        print("    ... and {} more".format(len(files)-8))
