"""
Generate Final Publication Tables.

1. Table 1: Clinical Landscape & Classification
   - Columns: ID, Target, Phase, CDR3 Length, H2 Fold, New Class, Human Identity %.
   - Source: Publication_Source_Data.csv + Table1_slice3...csv (for Target/Phase).

2. Supplementary Table S1: Hallmark & Vernier Frequency Analysis
   - Columns: Position, Residue, Short Group Freq, Long Group Freq, Interpretation.
   - Source: TheraSAbDab_19VHH_Hallmark_Vernier_Analysis_Corrected.txt (parsed).

Outputs:
  - paper/tables/Table1_Clinical_Landscape.csv
  - paper/tables/TableS1_Residue_Frequencies.csv
"""

import pandas as pd
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_SOURCE_DATA = PROJECT_ROOT / "paper" / "raw data" / "Publication_Source_Data.csv"
IN_CLINICAL_INFO = PROJECT_ROOT / "paper" / "tables" / "Table1_slice3_19_clinical_vhh_master.csv"
IN_RESIDUE_TXT = PROJECT_ROOT / "paper" / "raw data" / "MicroAnalysis" / "TheraSAbDab_19VHH_Hallmark_Vernier_Analysis_Corrected.txt"

OUT_TABLE1 = PROJECT_ROOT / "paper" / "tables" / "Table1_Clinical_Landscape.csv"
OUT_TABLES1 = PROJECT_ROOT / "paper" / "tables" / "TableS1_Residue_Frequencies.csv"

if not OUT_TABLE1.parent.exists():
    OUT_TABLE1.parent.mkdir(parents=True)

def generate_table1():
    # Load Data
    df_data = pd.read_csv(IN_SOURCE_DATA)
    # Filter out References
    df_data = df_data[df_data["Strategy"] != "Reference"]
    
    # Load Clinical Info (Target, Phase)
    try:
        df_clinical = pd.read_csv(IN_CLINICAL_INFO)
        # Normalize names for merging
        df_clinical["join_key"] = df_clinical["Antibody Name"].str.lower().str.strip()
        df_data["join_key"] = df_data["antibody_id"].str.lower().str.strip()
        
        # Merge
        df_merged = df_data.merge(df_clinical[["join_key", "Target", "Highest Clinical Phase"]], 
                                on="join_key", how="left")
    except Exception as e:
        print(f"Warning: Could not load clinical info ({e}). Using placeholders.")
        df_merged = df_data.copy()
        df_merged["Target"] = "TBD"
        df_merged["Highest Clinical Phase"] = "TBD"

    # Select and Rename Columns
    IN_METADATA = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv"
    df_meta = pd.read_csv(IN_METADATA)
    df_merged = df_merged.merge(df_meta[["antibody_id", "global_human_identity_pct"]], on="antibody_id", how="left")

    table1 = df_merged[[
        "antibody_id", "Target", "Highest Clinical Phase", 
        "H3_Len", "H2_Fold", "New_Class", "global_human_identity_pct"
    ]].copy()
    
    table1.columns = [
        "Antibody Name", "Target", "Clinical Phase", 
        "CDR3 Length (aa)", "CDR2 Fold", "Classification", "Human Identity (%)"
    ]
    
    # Format
    table1["Human Identity (%)"] = table1["Human Identity (%)"].round(1)
    
    # Sort by Class then CDR3 Length
    table1 = table1.sort_values(["Classification", "CDR3 Length (aa)"])
    
    table1.to_csv(OUT_TABLE1, index=False)
    print(f"Generated Table 1: {OUT_TABLE1}")

def parse_residue_txt():
    """Parse the text report to create a structured CSV."""
    content = IN_RESIDUE_TXT.read_text(encoding="utf-8")
    
    data = []
    current_group = ""
    
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("Group:"):
            if "Short" in line: current_group = "Short CDR3 (<=10)" 
            elif "Long" in line: current_group = "Long CDR3 (>10)"
        
        if line.startswith("Pos"):
            parts = line.split(":")
            pos_info = parts[0].replace("Pos ", "").strip() # "37 (Hallmark)"
            residues = ":".join(parts[1:]).strip() # "S:2, Y:1"
            
            # Clean Pos Info
            pos_num = pos_info.split(" ")[0]
            region = "Hallmark (FR2)" if "Hallmark" in pos_info else "Vernier (FR3)"
            
            # Check for duplicates before adding
            # Sometimes the report might have redundant lines or we parse incorrectly
            # We will use a set or check if exists
            
            data.append({
                "Group": current_group,
                "Position": pos_num,
                "Type": region,
                "Distribution": residues
            })
            
    df = pd.DataFrame(data)
    
    # Remove duplicates if any (same group, same position)
    df = df.drop_duplicates(subset=["Group", "Position", "Type"])
    
    # Pivot to compare Short vs Long side-by-side
    if not df.empty:
        df_pivot = df.pivot(index=["Type", "Position"], columns="Group", values="Distribution").reset_index()
        
        # Add Interpretation
        def interpret(row):
            pos = int(row["Position"])
            if pos == 47: return "Solubility Switch: R (Long) vs L/P (Short)"
            if pos == 71: return "Structural Anchor: Conserved R"
            if pos == 37: return "Interface: G/A (Long) vs S (Short)"
            return ""
            
        df_pivot["Interpretation"] = df_pivot.apply(interpret, axis=1)
        df_pivot.to_csv(OUT_TABLES1, index=False)
        print(f"Generated Table S1: {OUT_TABLES1}")
    else:
        print("Warning: No residue data parsed.")

def main():
    generate_table1()
    parse_residue_txt()

if __name__ == "__main__":
    main()
