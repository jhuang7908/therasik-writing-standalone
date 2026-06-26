"""
Update Table 1 with Clinical Information (Target & Phase).
Source of Truth: Table1_slice3_19_clinical_vhh_master.csv.

Updates:
1. Load master clinical table.
2. Create precise mapping for ID -> Target/Phase.
3. Update Table1_Clinical_Landscape.csv.
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_TABLE1 = PROJECT_ROOT / "paper" / "tables" / "Table1_Clinical_Landscape.csv"
IN_MASTER = PROJECT_ROOT / "paper" / "tables" / "Table1_slice3_19_clinical_vhh_master.csv"
OUT_TABLE1 = PROJECT_ROOT / "paper" / "tables" / "Table1_Clinical_Landscape_Filled.csv"

def main():
    df_table1 = pd.read_csv(IN_TABLE1)
    df_master = pd.read_csv(IN_MASTER)
    
    # Create Lookup Dictionary
    # Handle the suffixes in Table1 (e.g. Brivekimig1, Brivekimig2)
    # Master table has:
    # Brivekimig2 -> TNF x OX40L
    # Brivekimig1 -> TNF x OX40L
    # So we can map directly if ID exists, or fallback to base name.
    
    lookup = {}
    for _, row in df_master.iterrows():
        key = row["antibody_id"].strip()
        target = row["target"]
        phase = row["clinical_status"]
        lookup[key] = (target, phase)
        
    # Fill Table 1
    for idx, row in df_table1.iterrows():
        ab_id = row["Antibody Name"]
        
        if ab_id in lookup:
            df_table1.at[idx, "Target"] = lookup[ab_id][0]
            df_table1.at[idx, "Clinical Phase"] = lookup[ab_id][1]
        else:
            # Try fuzzy match?
            # Most should match directly based on previous file inspection
            # Letolizumab might be tricky if not in master?
            # Master has Letolizumab.
            print(f"Warning: No match for {ab_id}")

    df_table1.to_csv(OUT_TABLE1, index=False)
    print(f"Updated Table 1 saved to: {OUT_TABLE1}")

if __name__ == "__main__":
    main()
