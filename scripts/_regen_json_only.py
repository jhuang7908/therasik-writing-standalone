"""Regenerate ada_db_data.json from current CSV (no CSV modification).

Web policy: only rows passing ada_web_publish_gate (excerpt aligns with headline ADA +
verifiable http URL, Tier A/B) are written to docs/ada_db_data.json. Excluded antibodies
are listed under data/immunogenicity_knowledge_base/reports/ada_web_publish_excluded.csv
for offline manual curation.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from ada_web_publish_gate import resolve_http_citation, web_publish_eligible

ROOT = os.path.join(os.path.dirname(__file__), "..")
CSV_IN = os.path.join(ROOT, "data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv")
JSON_OUT = os.path.join(ROOT, "docs/ada_db_data.json")
EXCLUDED_CSV = os.path.join(
    ROOT, "data/immunogenicity_knowledge_base/reports/ada_web_publish_excluded.csv"
)

df = pd.read_csv(CSV_IN)
print(f"Loaded {len(df)} rows from CSV")

df["_resolved_cite"] = df.apply(lambda r: resolve_http_citation(r.to_dict()), axis=1)
df["_web_ok"] = df.apply(lambda r: web_publish_eligible(r.to_dict())[0], axis=1)
df["_web_reason"] = df.apply(lambda r: web_publish_eligible(r.to_dict())[1], axis=1)

excluded = df[~df["_web_ok"]].copy()
excluded_out = excluded[
    ["antibody_name", "_web_reason", "ada_first_pct", "ada_value_display", "evidence_tier"]
].rename(columns={"_web_reason": "exclude_reason"})
os.makedirs(os.path.dirname(EXCLUDED_CSV), exist_ok=True)
excluded_out.to_csv(EXCLUDED_CSV, index=False)
print(f"Web excluded (manual review queue): {len(excluded_out)} -> {EXCLUDED_CSV}")

df_pub = df[df["_web_ok"]].copy()
print(f"Web-publishable rows: {len(df_pub)} / {len(df)}")

df_pub["mhcii_net_clusters"] = (
    df_pub["immuno_n_high"].fillna(0) + df_pub["immuno_n_medium"].fillna(0)
).round(0).astype(int)

df_pub["surf_hydrophilic_avg"] = (
    (df_pub["surf_frac_exposed_vh"].fillna(np.nan) + df_pub["surf_frac_exposed_vl"].fillna(np.nan)) / 2
).round(4)

# Prefer amino-acid CDR3; fall back to canonical class label (e.g. H3-8)
df_pub["_cdr_h3"] = df_pub["vh_cdr3"].fillna(df_pub["canonical_H3"])

col_map = {
    "antibody_name": "name",
    "origin": "origin",
    "genetics_normalized": "genetics",
    "targets": "targets",
    "indication_text": "indication",
    "disease_class_curated": "disease_class",
    "ada_first_pct": "ada_pct",
    "ada_value_display": "ada_display",
    "evidence_tier": "tier",
    "_resolved_cite": "citation_url",
    "ada_source_pmids": "pmids",
    "fc_isotype": "fc_isotype",
    "fc_engineering": "fc_engineering",
    "fc_effector_status": "fc_effector",
    "route_curated": "route",
    "half_life_days": "half_life",
    "dose_mg": "dose_mg",
    "assay_platform": "assay_platform",
    "assay_generation": "assay_gen",
    "mtx_comedication": "mtx",
    "approval_year": "approval_year",
    "immuno_tcia_score": "tcia_score",
    "immuno_risk_level": "tcia_risk",
    "immuno_n_high": "mhcii_n_high",
    "immuno_n_medium": "mhcii_n_medium",
    "immuno_n_tolerated": "mhcii_n_tolerated",
    "immuno_n_clusters": "mhcii_clusters_total",
    "mhcii_net_clusters": "mhcii_net_clusters",
    "surf_hydrophilic_avg": "hydrophilic_frac",
    "surf_frac_exposed_vh": "hydrophilic_vh",
    "surf_frac_exposed_vl": "hydrophilic_vl",
    "surf_n_patches": "surf_patches",
    "surf_risk": "surf_risk",
    "hydro_patch_max9": "hydro_patch",
    "pI": "pI",
    "GRAVY": "gravy",
    "instability_index": "instability",
    "net_charge_pH7": "net_charge",
    "ada_v2_score": "v2_score",
    "ada_v2_risk": "v2_risk",
    "vh_germline": "vh_germline",
    "vl_germline": "vl_germline",
    "vh_germline_identity": "vh_identity",
    "vl_germline_identity": "vl_identity",
    "_cdr_h3": "cdr_h3",
    "format_type": "format_type",
    "modality": "modality",
    "immunosuppressant_context": "immuno_context",
    "ada_evidence_chain_excerpt": "evidence_excerpt",
    "moa_class": "moa_class",
    "verify_status": "verify_status",
    "verify_note": "verify_note",
    "assay_method": "assay_method",
    "trial_duration_weeks": "trial_duration",
    # Additional clinical context fields
    "dose_freq": "dose_freq",
    "oncology_indication": "oncology",
    "checkpoint_inhibitor": "checkpoint",
    "immune_depleting": "immune_depleting",
    "concomitant_immuno_likely": "concomitant_immuno",
    "fc_mutation_notes": "fc_mutation_notes",
}

# Only include columns that exist in the dataframe
available_cols = {k: v for k, v in col_map.items() if k in df_pub.columns}
sub = df_pub[list(available_cols.keys())].rename(columns=available_cols)


def clean(v):
    if isinstance(v, float) and np.isnan(v):
        return None
    if isinstance(v, (np.int64, np.int32)):
        return int(v)
    if isinstance(v, (np.float64, np.float32)):
        return None if np.isnan(v) else round(float(v), 4)
    return v


records = []
for _, row in sub.iterrows():
    r = {k: clean(v) for k, v in row.items()}
    ex = r.get("evidence_excerpt")
    if ex:
        r["evidence_text"] = ex
    records.append(r)

with open(JSON_OUT, "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, separators=(",", ":"))

print(f"JSON saved: {len(records)} records → {JSON_OUT}")

tiers = {}
for r in records:
    t = r.get("tier", "?")
    tiers[t] = tiers.get(t, 0) + 1
print("Tier distribution:", tiers)
