"""Audit Unknown antibodies and write reclassification map."""
import pandas as pd
import sys

CSV = "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"
df = pd.read_csv(CSV, low_memory=False)

print(f"Total rows: {len(df)}", flush=True)
print("thera_genetics_class distribution:", flush=True)
print(df["thera_genetics_class"].value_counts(dropna=False).to_dict(), flush=True)

def normalize_class(v):
    if pd.isna(v):
        return "Unknown"
    s = str(v).strip().lower()
    if s in ("", "nan", "unknown", "none"):
        return "Unknown"
    if "fully human" in s or s == "human":
        return "Fully Human"
    if "humanized" in s:
        return "Humanized"
    if "chimeric" in s:
        return "Chimeric"
    if "murine" in s or "mouse" in s:
        return "Murine"
    return "Unknown"

df["_cls"] = df["thera_genetics_class"].map(normalize_class)
unk = df[df["_cls"] == "Unknown"].copy()
print(f"\nUnknown count: {len(unk)}", flush=True)

cols_to_show = ["antibody_name", "thera_genetics_class", "ada_first_pct"]
for c in ["format_type", "modality", "origin", "discovery_platform", "fc_isotype"]:
    if c in df.columns:
        cols_to_show.append(c)

pd.set_option("display.max_rows", 200)
pd.set_option("display.max_colwidth", 40)
print(unk[cols_to_show].to_string(), flush=True)
