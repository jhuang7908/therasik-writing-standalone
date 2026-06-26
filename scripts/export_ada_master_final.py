"""
Export final curated ADA master CSV and generate the companion evidence report.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

BASE = Path(".")
m = pd.read_csv(BASE / "data/ada_master_136_curated.csv")

# ════════════════════════════════════════════════════════════════════════════════
# Column ordering for the final deliverable
# ════════════════════════════════════════════════════════════════════════════════
FINAL_ORDER = [
    # ── Identity ──
    "antibody_name",
    "origin",
    "genetics_normalized",
    "thera_genetics_class",
    # ── Target & Disease ──
    "targets",
    "indication_text",
    "disease_class_curated",
    # ── Fc & Engineering ──
    "fc_isotype",
    "fc_engineering",
    "fc_effector_status",
    "fc_mutation_notes",
    # ── Dosing & Route ──
    "route_curated",
    "dose_mg",
    "dose_freq",
    "half_life_days",
    # ── Assay & Co-medication ──
    "assay_platform",
    "assay_generation",
    "mtx_comedication",
    "immunosuppressant_context",
    "approval_year",
    # ── Route/context flags ──
    "oncology_indication",
    "checkpoint_inhibitor",
    "immune_depleting",
    "concomitant_immuno_likely",
    # ── Clinical ADA (evidence-backed) ──
    "ada_value_display",
    "ada_first_pct",
    "evidence_tier",
    "evidence_source",
    "citation_urls",
    "ada_source_url_primary",
    "ada_source_pmids",
    "ada_source_type_curated",
    "ada_has_text_evidence",
    "ada_evidence_chain_excerpt",
    # ── Sequence ──
    "vh_seq",
    "vl_seq",
    "vh_fr1", "vh_cdr1", "vh_fr2", "vh_cdr2", "vh_fr3", "vh_cdr3", "vh_fr4",
    "vl_fr1", "vl_cdr1", "vl_fr2", "vl_cdr2", "vl_fr3", "vl_cdr3", "vl_fr4",
    "heavy_seq_len",
    "light_seq_len",
    # ── Germline ──
    "vh_germline",
    "vl_germline",
    "vh_family",
    "vl_family",
    "vh_germline_identity",
    "vl_germline_identity",
    "vh_germline_imgt",
    "vl_germline_imgt",
    "vh_identity_imgt",
    "vl_identity_imgt",
    "germline_source",
    # ── Structure ──
    "pdb_path",
    "vh_vl_angle_deg",
    "interface_n_pairs",
    "interface_mean_dist_A",
    "interface_min_dist_A",
    "canonical_H1", "canonical_H2", "canonical_H3",
    "canonical_L1", "canonical_L2", "canonical_L3",
    # ── CMC / Developability ──
    "pI",
    "GRAVY",
    "instability_index",
    "net_charge_pH7",
    "hydro_patch_max9",
    "charge_patch_max7",
    "cmc_flags",
    "agg_motifs",
    "deamidation_sites",
    "isomerization_sites",
    # ── MHC-II / T-cell epitope ──
    "immuno_tcia_score",
    "immuno_risk_level",
    "immuno_n_high",
    "immuno_n_medium",
    "immuno_n_tolerated",
    "immuno_n_clusters",
    # ── SASA-based surface immunogenicity ──
    "surf_mode",
    "surf_risk",
    "surf_n_patches",
    "surf_mean_sasa_vh",
    "surf_mean_sasa_vl",
    "surf_frac_exposed_vh",
    "surf_frac_exposed_vl",
    "surf_hydrophilicity",
    # ── V2 model predictions (clearly labeled as model-derived) ──
    "ada_v2_score",
    "ada_v2_risk",
    "ada_profile_disease",
    "ada_profile_route",
    "ada_profile_half_life",
    # ── Provenance ──
    "panel_source",
    "confounder_source",
    "format_type",
    "modality",
    "phase_bucket",
]

present = [c for c in FINAL_ORDER if c in m.columns]
extra = [c for c in m.columns if c not in FINAL_ORDER]
if extra:
    print("Extra columns not in FINAL_ORDER (appended at end): {}".format(extra))
    present += extra

out = m[present].copy()

OUT_CSV = BASE / "data/ada_master_136_curated.csv"
out.to_csv(OUT_CSV, index=False, encoding="utf-8")
print("Saved final master CSV: {} ({} rows × {} cols)".format(OUT_CSV, len(out), len(out.columns)))

# ════════════════════════════════════════════════════════════════════════════════
# Generate companion evidence report
# ════════════════════════════════════════════════════════════════════════════════
n = len(out)
ts = datetime.now().strftime("%Y-%m-%d %H:%M")

lines = []
lines.append("# ADA Master Table — Companion Evidence Report\n")
lines.append("**Generated**: {}  ".format(ts))
lines.append("**Panel size**: {} antibodies  ".format(n))
lines.append("**File**: `data/ada_master_136_curated.csv`\n")
lines.append("---\n")

# Tier breakdown
lines.append("## 1. ADA Evidence Tier Breakdown\n")
tier_vc = out["evidence_tier"].value_counts()
for t in ["A", "B", "C"]:
    cnt = tier_vc.get(t, 0)
    pct = cnt / n * 100
    lines.append("- **Tier {}**: {} ({:.0f}%)".format(t, cnt, pct))

lines.append("\n**Tier definitions:**\n")
lines.append("- *Tier A*: ADA value anchored by PMID, FDA label, or ClinicalTrials.gov. Evidence chain from primary source.")
lines.append("- *Tier B*: Real URL verified; ADA value confirmed by automated text matching. Evidence narrative may be AI-paraphrased (not verbatim).")
lines.append("- *Tier C*: Unverified or known data quality issues. Excluded from CLEAN-129 analysis.\n")

# Column coverage
lines.append("## 2. Column Coverage Summary\n")
lines.append("| Column Group | Representative Field | Present | Coverage |")
lines.append("|---|---|---|---|")

coverage_groups = [
    ("Identity", "antibody_name"),
    ("Target & Indication", "indication_text"),
    ("Disease Class", "disease_class_curated"),
    ("Fc Engineering", "fc_engineering"),
    ("Fc Effector Status", "fc_effector_status"),
    ("Fc Mutation Notes", "fc_mutation_notes"),
    ("Route", "route_curated"),
    ("Dose (mg)", "dose_mg"),
    ("Dose Frequency", "dose_freq"),
    ("Half-life (days)", "half_life_days"),
    ("Assay Platform", "assay_platform"),
    ("Assay Generation", "assay_generation"),
    ("Clinical ADA (%)", "ada_first_pct"),
    ("ADA Evidence Chain", "ada_evidence_chain_excerpt"),
    ("ADA Source URL", "ada_source_url_primary"),
    ("ADA Evidence Tier", "evidence_tier"),
    ("VH Sequence", "vh_seq"),
    ("VL Sequence", "vl_seq"),
    ("VH Germline Identity", "vh_germline_identity"),
    ("VL Germline Identity", "vl_germline_identity"),
    ("PDB Structure", "pdb_path"),
    ("CMC pI", "pI"),
    ("MHC-II TCIA Score", "immuno_tcia_score"),
    ("SASA Surface Patches", "surf_n_patches"),
    ("V2 Model Score", "ada_v2_score"),
    ("Confounder Source", "confounder_source"),
]

for label, col in coverage_groups:
    if col in out.columns:
        if out[col].dtype == object:
            nn = out[col].apply(lambda x: bool(x) and str(x).strip() not in ("", "nan", "None")).sum()
        else:
            nn = out[col].notna().sum()
        pct = nn / n * 100
        lines.append("| {} | `{}` | {}/{} | {:.0f}% |".format(label, col, nn, n, pct))
    else:
        lines.append("| {} | `{}` | — | MISSING |".format(label, col))

# Source provenance
lines.append("\n## 3. Source Provenance\n")
lines.append("| Source | File | Fields Contributed |")
lines.append("|---|---|---|")
lines.append("| 136-panel spine | `data/immunogenicity_panel_136_master.csv` | Sequence, germline, CMC, MHC-II, SASA, structure, V2 model scores |")
lines.append("| ADA Clinical DB | `data/ADA_reliable_package/clinical_db/` | `ada_evidence_chain_excerpt`, `ada_source_url_primary`, `ada_source_pmids`, evidence tier |")
lines.append("| Curated Confounders (70) | `data/reference/clinical_confounders_70.csv` | `dose_mg`, `dose_freq`, `route_curated`, `fc_engineering`, `fc_effector_status`, `half_life_days`, `assay_*`, `mtx_comedication`, `immunosuppressant_context` |")
lines.append("| Route & Context | `data/reference/route_and_context.csv` | `route_curated` (where not in 70), `oncology_indication`, `checkpoint_inhibitor`, `immune_depleting` |")
lines.append("| Curated 66 Metadata | `data/curated_66_clinical_metadata.csv` | `indication_text`, `disease_class_curated`, `route_curated`, `dose_mg`, `dose_freq`, `half_life_days`, `fc_engineering`, `fc_effector_status`, `fc_mutation_notes`, `assay_*` for antibodies not in 70-panel |")
lines.append("| P70 Indications | Script-curated from FDA labels | `indication_text`, `disease_class_curated` for 70-panel antibodies |")

# Known gaps
lines.append("\n## 4. Known Gaps & Caveats\n")

url_missing = out[out["ada_source_url_primary"].isna() | (out["ada_source_url_primary"].astype(str).str.strip().isin(["", "nan", "None"]))]["antibody_name"].tolist()
if url_missing:
    lines.append("### Missing Primary ADA Source URLs ({} antibodies)\n".format(len(url_missing)))
    for ab in url_missing:
        lines.append("- {}".format(ab))
    lines.append("")

ada_missing = out[out["ada_first_pct"].isna()]["antibody_name"].tolist()
if ada_missing:
    lines.append("### Missing Numeric ADA Value ({} antibodies)\n".format(len(ada_missing)))
    for ab in ada_missing:
        lines.append("- {}".format(ab))
    lines.append("")

seq_missing = out[out["vh_seq"].isna() | (out["vh_seq"].astype(str).str.strip().isin(["", "nan", "None"]))]["antibody_name"].tolist()
if seq_missing:
    lines.append("### Missing VH Sequence ({} antibodies)\n".format(len(seq_missing)))
    for ab in seq_missing:
        lines.append("- {}".format(ab))
    lines.append("")

tier_c = out[out["evidence_tier"] == "C"]["antibody_name"].tolist()
if tier_c:
    lines.append("### Tier C Entries (Recommended Exclusion from Quantitative Analysis)\n")
    for ab in tier_c:
        ada = out.loc[out["antibody_name"] == ab, "ada_value_display"].values[0]
        lines.append("- {} (reported: {})".format(ab, ada))
    lines.append("")

# Model-derived vs curated distinction
lines.append("## 5. Model-Derived vs Curated Fields\n")
lines.append("**CURATED (evidence-backed):**\n")
lines.append("- All `ada_*` fields (clinical ADA value, evidence chain, source URL, tier)")
lines.append("- `route_curated`, `dose_mg`, `dose_freq`, `half_life_days`")
lines.append("- `fc_engineering`, `fc_effector_status`, `fc_mutation_notes`")
lines.append("- `indication_text`, `disease_class_curated`")
lines.append("- `assay_platform`, `assay_generation`\n")
lines.append("**MODEL-DERIVED (computational predictions, not clinical facts):**\n")
lines.append("- `ada_v2_score`, `ada_v2_risk` — V2 scorer output, Spearman rho = 0.19 vs clinical ADA")
lines.append("- `ada_profile_disease`, `ada_profile_route`, `ada_profile_half_life` — inferred metadata for V2 auto-routing")
lines.append("- `immuno_tcia_score`, `immuno_risk_level`, `immuno_n_*` — MHC-II epitope predictions")
lines.append("- `surf_*` — SASA-based surface immunogenicity features\n")
lines.append("**NEVER** conflate model-derived immunogenicity scores with curated clinical ADA incidence.\n")

# Interpretation
lines.append("## 6. Interpretation Guidelines\n")
lines.append("1. **Clinical ADA rates are not directly comparable across antibodies** due to differences in assay platforms, cut-points, follow-up durations, and patient populations.")
lines.append("2. **Tier A evidence** is the most reliable; Tier B is confirmed but paraphrased; Tier C should be treated as unverified.")
lines.append("3. **V2 model predictions** are relative risk rankings, not absolute ADA rate estimates. Use for within-project candidate prioritization.")
lines.append("4. **Subgroup analysis** (natural vs engineered) is essential — the two groups have different ADA mechanisms and confounder profiles.")
lines.append("5. For full discussion of confounders and limitations, see `docs/ADA_Review_Discussion_Notes.md`.\n")
lines.append("---\n")
lines.append("*Generated by `scripts/export_ada_master_final.py` — {ts}*\n".format(ts=ts))

report_path = BASE / "docs/ADA_Master_136_Evidence_Report.md"
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("Saved evidence report: {}".format(report_path))
