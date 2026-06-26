"""
Build fully sourced ADA Master Table (136-panel base).
Steps 1-3: Schema + local merge + gap audit.

Source hierarchy:
  1. data/immunogenicity_panel_136_master.csv  (spine)
  2. data/ADA_reliable_package/clinical_db/     (ADA evidence)
  3. data/reference/clinical_confounders_70.csv (curated clinical metadata)
  4. data/reference/route_and_context.csv       (route + disease flags)
"""
import pandas as pd
import numpy as np
import json
import re
from pathlib import Path

BASE = Path(".")

# ════════════════════════════════════════════════════════════════════════════════
# STEP 1: Load all sources
# ════════════════════════════════════════════════════════════════════════════════
print("Loading sources...")
panel = pd.read_csv(BASE / "data/immunogenicity_panel_136_master.csv")
panel["_key"] = panel["antibody_name"].str.strip().str.lower()
n = len(panel)
print("  136-panel: {} rows".format(n))

# ADA evidence DB
with open(BASE / "data/ADA_reliable_package/clinical_db/clinical_ada_db_index.json", "r", encoding="utf-8") as f:
    ada_idx_list = json.load(f)["index"]
ada_idx = {item["antibody_name"].lower().strip(): item for item in ada_idx_list}

with open(BASE / "data/ADA_reliable_package/clinical_db/clinical_ada_db_data.json", "r", encoding="utf-8") as f:
    ada_data = json.load(f)["records"]
print("  ADA clinical DB: {} index entries, {} data records".format(len(ada_idx), len(ada_data)))

# Confounders (70)
conf70 = pd.read_csv(BASE / "data/reference/clinical_confounders_70.csv")
conf70["_key"] = conf70["antibody_name"].str.strip().str.lower()
conf70_dict = {row["_key"]: row for _, row in conf70.iterrows()}
print("  Confounders 70: {} rows".format(len(conf70)))

# Route and context
route_ctx = pd.read_csv(BASE / "data/reference/route_and_context.csv")
route_ctx["_key"] = route_ctx["antibody_name"].str.strip().str.lower()
route_dict = {row["_key"]: row for _, row in route_ctx.iterrows()}
print("  Route/context: {} rows".format(len(route_ctx)))

# ════════════════════════════════════════════════════════════════════════════════
# STEP 2: Define new columns and merge
# ════════════════════════════════════════════════════════════════════════════════
NEW_COLS = [
    # Clinical confounder fields (curated)
    "indication_text",
    "disease_class_curated",
    "route_curated",
    "dose_mg",
    "dose_freq",
    "half_life_days",
    "fc_engineering",
    "fc_effector_status",
    "fc_mutation_notes",
    "assay_platform",
    "assay_generation",
    "approval_year",
    "mtx_comedication",
    "immunosuppressant_context",
    # Route/context flags
    "oncology_indication",
    "checkpoint_inhibitor",
    "immune_depleting",
    "concomitant_immuno_likely",
    # ADA evidence chain fields
    "ada_evidence_chain_excerpt",
    "ada_source_url_primary",
    "ada_source_pmids",
    "ada_source_type_curated",
    "ada_has_text_evidence",
    # Provenance tracking
    "confounder_source",
]

for col in NEW_COLS:
    if col not in panel.columns:
        panel[col] = None

print("\nMerging local sources...")

for i, row in panel.iterrows():
    key = row["_key"]

    # ── Merge ADA evidence chain ──────────────────────────────────────────
    if key in ada_idx:
        idx_rec = ada_idx[key]
        data_key = idx_rec.get("data_record_key", "")
        full_rec = ada_data.get(data_key, {}).get("primary_record", {})

        chain = full_rec.get("evidence_chain", "")
        if chain and len(chain) > 50:
            excerpt = chain[:800].replace("\n", " ").strip()
            if len(chain) > 800:
                excerpt += "..."
            panel.at[i, "ada_evidence_chain_excerpt"] = excerpt

        panel.at[i, "ada_source_url_primary"] = full_rec.get("source_url", "")
        panel.at[i, "ada_source_type_curated"] = full_rec.get("source_type", "")
        panel.at[i, "ada_has_text_evidence"] = bool(full_rec.get("has_text_evidence", False))

        pmids = idx_rec.get("pmids_extracted", [])
        if pmids:
            panel.at[i, "ada_source_pmids"] = "; ".join(str(p) for p in pmids)

    # ── Merge confounders (70-row curated table) ──────────────────────────
    if key in conf70_dict:
        cr = conf70_dict[key]
        panel.at[i, "dose_mg"] = cr.get("dose_mg")
        panel.at[i, "dose_freq"] = cr.get("dose_freq")
        panel.at[i, "route_curated"] = cr.get("dose_route_detail")
        panel.at[i, "fc_engineering"] = cr.get("fc_engineering")
        panel.at[i, "fc_effector_status"] = cr.get("fc_effector_status")
        panel.at[i, "half_life_days"] = cr.get("half_life_days")
        panel.at[i, "assay_platform"] = cr.get("assay_platform")
        panel.at[i, "assay_generation"] = cr.get("assay_generation")
        panel.at[i, "approval_year"] = cr.get("approval_year")
        panel.at[i, "mtx_comedication"] = cr.get("mtx_comedication")
        panel.at[i, "immunosuppressant_context"] = cr.get("immunosuppressant_context")
        panel.at[i, "fc_mutation_notes"] = cr.get("notes")
        panel.at[i, "confounder_source"] = "clinical_confounders_70.csv"

    # ── Merge route/context flags ─────────────────────────────────────────
    if key in route_dict:
        rc = route_dict[key]
        if pd.isna(panel.at[i, "route_curated"]) or not panel.at[i, "route_curated"]:
            panel.at[i, "route_curated"] = rc.get("route")
        panel.at[i, "oncology_indication"] = rc.get("oncology_indication")
        panel.at[i, "checkpoint_inhibitor"] = rc.get("checkpoint_inhibitor")
        panel.at[i, "immune_depleting"] = rc.get("immune_depleting")
        panel.at[i, "concomitant_immuno_likely"] = rc.get("concomitant_immuno_likely")
        if pd.isna(panel.at[i, "confounder_source"]):
            panel.at[i, "confounder_source"] = "route_and_context.csv"
        else:
            panel.at[i, "confounder_source"] = str(panel.at[i, "confounder_source"]) + " + route_and_context.csv"

# ════════════════════════════════════════════════════════════════════════════════
# STEP 3: Gap audit
# ════════════════════════════════════════════════════════════════════════════════
print("\n=== GAP AUDIT (n={}) ===\n".format(n))

audit_cols = [
    ("vh_seq", "Sequence VH"),
    ("vl_seq", "Sequence VL"),
    ("pdb_path", "Structure PDB"),
    ("vh_vl_angle_deg", "Structure VH-VL angle"),
    ("pI", "CMC pI"),
    ("immuno_tcia_score", "MHC-II TCIA"),
    ("immuno_n_high", "MHC-II n_high"),
    ("surf_frac_exposed_vh", "SASA frac_exposed VH"),
    ("surf_n_patches", "SASA n_patches"),
    ("ada_first_pct", "Clinical ADA numeric"),
    ("ada_evidence_chain_excerpt", "ADA evidence chain"),
    ("ada_source_url_primary", "ADA source URL"),
    ("evidence_tier", "ADA evidence tier"),
    ("route_curated", "Route (curated)"),
    ("half_life_days", "Half-life (curated)"),
    ("dose_mg", "Dose mg (curated)"),
    ("dose_freq", "Dose frequency (curated)"),
    ("fc_engineering", "Fc engineering (curated)"),
    ("fc_effector_status", "Fc effector status (curated)"),
    ("assay_platform", "Assay platform (curated)"),
    ("assay_generation", "Assay generation (curated)"),
    ("targets", "Targets"),
    ("fc_isotype", "Fc isotype"),
    ("origin", "Origin (natural/engineered)"),
    ("oncology_indication", "Oncology flag"),
]

gap_rows = []
for col, label in audit_cols:
    if col in panel.columns:
        nn = panel[col].notna().sum()
        # also count empty strings
        if panel[col].dtype == object:
            nn = panel[col].apply(lambda x: bool(x) and str(x).strip() not in ("", "nan", "None")).sum()
        pct = nn / n * 100
        status = "FULL" if pct == 100 else ("HIGH" if pct >= 90 else ("PARTIAL" if pct >= 50 else "LOW"))
        gap_rows.append({"field": col, "label": label, "present": nn, "total": n, "pct": pct, "status": status})
        print("  {:40} {:3}/{} ({:5.1f}%) [{}]".format(label, nn, n, pct, status))
    else:
        gap_rows.append({"field": col, "label": label, "present": 0, "total": n, "pct": 0, "status": "MISSING"})
        print("  {:40} COLUMN MISSING".format(label))

# Identify antibodies missing Fc/route/half-life
needs_curation = []
for i, row in panel.iterrows():
    missing = []
    if pd.isna(row.get("route_curated")) or not str(row.get("route_curated","")).strip():
        missing.append("route")
    if pd.isna(row.get("half_life_days")) or not str(row.get("half_life_days","")).strip():
        missing.append("half_life")
    if pd.isna(row.get("fc_engineering")) or not str(row.get("fc_engineering","")).strip():
        missing.append("fc_engineering")
    if pd.isna(row.get("dose_mg")) or not str(row.get("dose_mg","")).strip():
        missing.append("dose")
    if pd.isna(row.get("assay_platform")) or not str(row.get("assay_platform","")).strip():
        missing.append("assay")
    if missing:
        needs_curation.append({
            "antibody": row["antibody_name"],
            "missing_fields": missing,
            "n_missing": len(missing),
            "origin": row.get("origin"),
            "evidence_tier": row.get("evidence_tier"),
        })

needs_df = pd.DataFrame(needs_curation)
print("\n=== ANTIBODIES NEEDING CLINICAL METADATA CURATION ===")
print("Total needing curation: {}/{}".format(len(needs_df), n))
if len(needs_df) > 0:
    by_n = needs_df["n_missing"].value_counts().sort_index()
    for nm, cnt in by_n.items():
        print("  {} missing fields: {} antibodies".format(nm, cnt))

# Save intermediate + gap list
panel.drop(columns=["_key"], inplace=True)
panel.to_csv(BASE / "data/ada_master_136_curated.csv", index=False, encoding="utf-8")
needs_df.to_csv(BASE / "data/ada_curation_gap_list.csv", index=False, encoding="utf-8")

print("\nSaved: data/ada_master_136_curated.csv")
print("Saved: data/ada_curation_gap_list.csv")
print("Done steps 1-3.")
