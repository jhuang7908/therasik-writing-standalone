import json
import pandas as pd
from pathlib import Path

# Load IgG-like IDs
with open("data/design_rules/bispecific_125_igg_like.json", "r") as f:
    igg_like_data = json.load(f)
igg_ids = set(igg_like_data["antibody_ids"])

# Load Excel
try:
    df = pd.read_excel("data/humanization_assay/thera_human_igG_germline_analysis.xlsx")
    # Check columns
    print("Columns:", df.columns.tolist())
    
    # Check overlap
    # Assuming 'Name' or 'INN' holds the ID
    df_ids = set(df['Name'].astype(str)).union(set(df['INN'].astype(str)))
    
    overlap = igg_ids.intersection(df_ids)
    print(f"Found {len(overlap)} of {len(igg_ids)} IgG-like antibodies in Excel.")
    print("Missing:", igg_ids - df_ids)
except Exception as e:
    print(f"Error reading Excel: {e}")
