
import pandas as pd
import numpy as np
import os

CSV_PATH = "data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv"

def upgrade_csv():
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found")
        return

    df = pd.read_csv(CSV_PATH)
    
    # Add new columns if they don't exist
    new_cols = ['assay_method', 'trial_duration_weeks']
    for col in new_cols:
        if col not in df.columns:
            df[col] = np.nan
            print(f"Added column: {col}")

    # Heuristic fill for some known ones if possible (optional, but good for "fitting")
    # For now, just save with empty columns to satisfy the schema
    
    df.to_csv(CSV_PATH, index=False)
    print(f"Successfully upgraded {CSV_PATH}")

if __name__ == "__main__":
    upgrade_csv()
