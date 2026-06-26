"""
Merge the curated 66-antibody clinical metadata into the master table.
Also backfill indication_text and disease_class for the 70-panel antibodies
using route_and_context.csv + ADA evidence chains where available.
"""
import pandas as pd
import numpy as np
from pathlib import Path

BASE = Path(".")

master = pd.read_csv(BASE / "data/ada_master_136_curated.csv")
curated = pd.read_csv(BASE / "data/curated_66_clinical_metadata.csv")
curated["_key"] = curated["antibody_name"].str.strip().str.lower()
cdict = {r["_key"]: r for _, r in curated.iterrows()}

MERGE_FIELDS = [
    "indication_text", "disease_class_curated", "route_curated",
    "dose_mg", "dose_freq", "half_life_days",
    "fc_engineering", "fc_effector_status", "fc_mutation_notes",
    "assay_platform", "assay_generation",
]

updated = 0
for i, row in master.iterrows():
    key = row["antibody_name"].strip().lower()
    if key in cdict:
        cr = cdict[key]
        for field in MERGE_FIELDS:
            val = cr.get(field)
            existing = master.at[i, field] if field in master.columns else None
            if val and str(val).strip() and str(val).strip() != "nan":
                if pd.isna(existing) or not str(existing).strip() or str(existing).strip() == "nan":
                    master.at[i, field] = val
        src = master.at[i, "confounder_source"]
        cite = cr.get("source_citation", "")
        if pd.isna(src) or not str(src).strip():
            master.at[i, "confounder_source"] = "curated_66_clinical_metadata.csv ({})".format(cite[:80])
        else:
            master.at[i, "confounder_source"] = str(src) + " + curated_66 ({})".format(cite[:60])
        updated += 1

print("Updated {} rows from curated 66 metadata".format(updated))

# Also infer disease_class for the remaining 70-panel antibodies that already have route
# but may lack disease_class_curated and indication_text
target_map = {
    "pd1": "oncology", "pd-1": "oncology", "pdl1": "oncology", "pd-l1": "oncology",
    "ctla4": "oncology", "ctla-4": "oncology", "her2": "oncology",
    "egfr": "oncology", "cd20": "oncology", "vegf": "oncology",
    "vegfr": "oncology", "cd19": "oncology", "cd22": "oncology",
    "cd30": "oncology", "cd38": "oncology", "cd79": "oncology",
    "tnf": "autoimmune", "il-6": "autoimmune", "il6": "autoimmune",
    "il6r": "autoimmune", "il-17": "autoimmune", "il17": "autoimmune",
    "il-23": "autoimmune", "il23": "autoimmune", "il-1": "autoimmune",
    "il-4": "autoimmune_allergic", "il4r": "autoimmune_allergic",
    "il-5": "autoimmune_allergic", "il5": "autoimmune_allergic",
    "il-13": "autoimmune_allergic", "il13": "autoimmune_allergic",
    "ige": "autoimmune_allergic",
    "pcsk9": "metabolic",
    "rankl": "metabolic_musculoskeletal", "sclerostin": "metabolic_musculoskeletal",
    "cgrp": "neurology", "amyloid": "neurology",
    "c5": "hematology_immunology", "complement": "hematology_immunology",
    "rsv": "infectious", "sars-cov": "infectious", "spike": "infectious",
    "ebola": "infectious",
}

n_inferred = 0
for i, row in master.iterrows():
    if pd.notna(row.get("disease_class_curated")) and str(row["disease_class_curated"]).strip():
        continue
    targets_str = str(row.get("targets", "")).lower()
    for k, cls in target_map.items():
        if k in targets_str:
            master.at[i, "disease_class_curated"] = cls + " (inferred from target)"
            n_inferred += 1
            break

print("Inferred disease_class for {} more antibodies from target names".format(n_inferred))

# Re-audit coverage
n = len(master)
print("\n=== UPDATED COVERAGE (n={}) ===".format(n))
for col in MERGE_FIELDS + ["confounder_source", "ada_evidence_chain_excerpt", "ada_source_url_primary"]:
    if col in master.columns:
        if master[col].dtype == object:
            nn = master[col].apply(lambda x: bool(x) and str(x).strip() not in ("", "nan", "None")).sum()
        else:
            nn = master[col].notna().sum()
        print("  {:40s} {:3d}/{} ({:5.1f}%)".format(col, nn, n, nn / n * 100))

master.to_csv(BASE / "data/ada_master_136_curated.csv", index=False, encoding="utf-8")
print("\nSaved updated: data/ada_master_136_curated.csv")
