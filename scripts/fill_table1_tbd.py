"""
Update Table 1 with Clinical Information (Target & Phase).
Manually filling in TBD values based on known clinical data for these 19 VHHs.

Source of Truth: Table1_slice3_19_clinical_vhh_master.csv (or internal knowledge base).
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_TABLE1 = PROJECT_ROOT / "paper" / "tables" / "Table1_Clinical_Landscape.csv"
OUT_TABLE1 = PROJECT_ROOT / "paper" / "tables" / "Table1_Clinical_Landscape_Filled.csv"

# Manual Clinical Data Map (ID -> (Target, Phase))
# Based on Thera-SAbDab and public knowledge
CLINICAL_DATA = {
    "Brivekimig1": ("IL-17A/F", "Phase 2"), # Bimekizumab-like? No, Brivekimig is bispecific?
    # Actually, let's use the Table1_slice3 file if possible, or fill manually.
    # Brivekimig is ALX-0761? No.
    # Let's map carefully.
    
    "Brivekimig": ("IL-17A/F", "Phase 2"), # Correct name might be Bimekizumab (IgG) vs Sonelokimab (VHH)
    # Wait, Brivekimig might be a misnomer or internal ID. 
    # Let's check the original list.
    
    "Caplacizumab": ("vWF", "Approved"),
    "Enristomig": ("PD-1/LAG-3", "Phase 1/2"), # Bispecific?
    "Envafolimab": ("PD-L1", "Approved"),
    "Erfonrilimab": ("PD-L1/CTLA-4", "Phase 2"),
    "Gefurulimab": ("Albumin", "Phase 3"), # Nanobody against Albumin (half-life extension)
    "Gocatamig": ("?", "Phase 1"), # Gocatamig?
    "Isecarosmab": ("?", "Phase 1"),
    "Letolizumab": ("?", "Phase 1"),
    "Ozekibart": ("?", "Phase 1"),
    "Ozoralizumab": ("TNF-alpha", "Approved"),
    "Podentamig": ("?", "Phase 1"),
    "Porustobart": ("PD-L1", "Phase 1"),
    "Rimteravimab": ("SARS-CoV-2", "Phase 1/2"),
    "Sonelokimab": ("IL-17A/F", "Phase 2/3"),
    "Tarperprumig": ("?", "Phase 1"),
    "Vobarilizumab": ("IL-6R", "Phase 2")
}

# Mapping for specific IDs in the file (handling suffixes)
ID_MAP = {
    "Brivekimig1": ("IL-13/IL-17", "Phase 2"), # Brivekimig is bispecific
    "Brivekimig2": ("IL-13/IL-17", "Phase 2"),
    "Caplacizumab": ("vWF", "Approved"),
    "Enristomig": ("PD-1/LAG-3", "Phase 1"), # Bispecific
    "Envafolimab": ("PD-L1", "Approved"),
    "Erfonrilimab": ("PD-L1/CTLA-4", "Phase 2"),
    "Gefurulimab": ("Complement C5", "Phase 3"), # ALXN1210? No, Gefurulimab is ALXN1720 (C5)
    "Gocatamig2": ("?", "Phase 1"), # Gocatamig
    "Isecarosmab": ("?", "Phase 1"),
    "Letolizumab": ("IL-6", "Phase 1"), # ALX-0061 is Vobarilizumab. Letolizumab is?
    "Ozekibart": ("?", "Phase 1"),
    "Ozoralizumab": ("TNF-alpha", "Approved"),
    "Podentamig1": ("?", "Phase 1"),
    "Porustobart": ("PD-L1", "Phase 1"),
    "Rimteravimab": ("SARS-CoV-2", "Phase 1"),
    "Sonelokimab1": ("IL-17A/F", "Phase 2"),
    "Sonelokimab2": ("IL-17A/F", "Phase 2"),
    "Tarperprumig": ("?", "Phase 1"),
    "Vobarilizumab": ("IL-6R", "Phase 2")
}

# Better approach: Read the original Table1_slice3 file directly to get the exact data
IN_MASTER = PROJECT_ROOT / "paper" / "tables" / "Table1_slice3_19_clinical_vhh_master.csv"

def main():
    df_table1 = pd.read_csv(IN_TABLE1)
    
    try:
        df_master = pd.read_csv(IN_MASTER)
        # Create a lookup dictionary from master
        # Normalize keys: lowercase, remove spaces
        lookup = {}
        for _, row in df_master.iterrows():
            key = row["Antibody Name"].lower().strip()
            lookup[key] = (row["Target"], row["Highest Clinical Phase"])
            
        # Fill TBDs
        for idx, row in df_table1.iterrows():
            if row["Target"] == "TBD":
                # Try to find match
                # Handle suffixes like '1', '2' in ID
                raw_id = row["Antibody Name"].lower().strip()
                
                # Try exact match first
                if raw_id in lookup:
                    df_table1.at[idx, "Target"] = lookup[raw_id][0]
                    df_table1.at[idx, "Clinical Phase"] = lookup[raw_id][1]
                else:
                    # Try stripping suffix (last char if digit)
                    base_id = raw_id[:-1] if raw_id[-1].isdigit() else raw_id
                    if base_id in lookup:
                        df_table1.at[idx, "Target"] = lookup[base_id][0]
                        df_table1.at[idx, "Clinical Phase"] = lookup[base_id][1]
                        
    except Exception as e:
        print(f"Error reading master file: {e}")
        
    df_table1.to_csv(OUT_TABLE1, index=False)
    print(f"Updated Table 1 saved to: {OUT_TABLE1}")

if __name__ == "__main__":
    main()
