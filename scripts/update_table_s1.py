"""
Update Table S1 with Extended Vernier Data (FR1, FR2, FR3).

Updates:
1. Include FR1 Vernier (Pos 27-30).
2. Include FR2 Vernier (Pos 48-49).
3. Include FR3 Vernier (Pos 71, 93-94).
4. Merge with existing Hallmark data.

Inputs:
  - paper/tables/TableS1_Residue_Frequencies.csv (Existing Hallmark data)
  - paper/raw data/MicroAnalysis/TheraSAbDab_19VHH_Extended_Vernier_Analysis.txt (FR1/FR3 data)
  - paper/raw data/MicroAnalysis/TheraSAbDab_19VHH_FR2_Vernier_Analysis.txt (FR2 data)

Outputs:
  - paper/tables/TableS1_Residue_Frequencies_Extended.csv
"""

import pandas as pd
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_EXISTING_S1 = PROJECT_ROOT / "paper" / "tables" / "TableS1_Residue_Frequencies.csv"
IN_FR1_FR3_TXT = PROJECT_ROOT / "paper" / "raw data" / "MicroAnalysis" / "TheraSAbDab_19VHH_Extended_Vernier_Analysis.txt"
IN_FR2_TXT = PROJECT_ROOT / "paper" / "raw data" / "MicroAnalysis" / "TheraSAbDab_19VHH_FR2_Vernier_Analysis.txt"
OUT_TABLES1 = PROJECT_ROOT / "paper" / "tables" / "TableS1_Residue_Frequencies_Extended.csv"

def parse_txt(file_path, region_type):
    content = file_path.read_text(encoding="utf-8")
    data = []
    
    # Simple parser: Look for "Pos XX" headers and subsequent "Short:" / "Long:" lines
    current_pos = ""
    
    lines = content.splitlines()
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("## Pos") or line.startswith("Pos"):
            # Extract Pos number
            # Format: "## Pos 48 Analysis" or "Pos 27:"
            match = re.search(r"Pos (\d+)", line)
            if match:
                current_pos = match.group(1)
        
        if "Short" in line and ":" in line:
            # Short: {'S': 4, ...} or Short: C:5
            val = line.split(":", 1)[1].strip()
            data.append({
                "Type": region_type,
                "Position": current_pos,
                "Group": "Short CDR3 (<=11)",
                "Distribution": val
            })
            
        if "Long" in line and ":" in line:
            val = line.split(":", 1)[1].strip()
            data.append({
                "Type": region_type,
                "Position": current_pos,
                "Group": "Long CDR3 (>11)",
                "Distribution": val
            })
            
    return pd.DataFrame(data)

def main():
    # 1. Load Existing (Hallmark + Pos 71)
    df_base = pd.read_csv(IN_EXISTING_S1)
    # Melt it back to long format for merging
    df_base_long = df_base.melt(id_vars=["Type", "Position", "Interpretation"], 
                                value_vars=["Short CDR3 (<=10)", "Long CDR3 (>10)"], # Note: Old labels
                                var_name="Group", value_name="Distribution")
    
    # Normalize Group Names (Old file had <=10, new is <=11)
    # We will just map them to standard names
    df_base_long["Group"] = df_base_long["Group"].apply(lambda x: "Short CDR3 (<=11)" if "Short" in x else "Long CDR3 (>11)")
    
    # 2. Parse New Data
    df_fr1_fr3 = parse_txt(IN_FR1_FR3_TXT, "Vernier")
    # Determine Type more specifically
    df_fr1_fr3["Type"] = df_fr1_fr3["Position"].apply(lambda x: "Vernier (FR1)" if int(x) < 40 else "Vernier (FR3)")
    
    df_fr2 = parse_txt(IN_FR2_TXT, "Vernier (FR2)")
    
    # 3. Combine
    df_combined = pd.concat([df_base_long, df_fr1_fr3, df_fr2], ignore_index=True)
    
    # Remove duplicates (Pos 71 might be in both base and new)
    # Base has Pos 71. New FR3 txt doesn't have 71 (it has 93, 94).
    # So we are safe.
    
    # 4. Pivot
    df_pivot = df_combined.pivot(index=["Type", "Position"], columns="Group", values="Distribution").reset_index()
    
    # 5. Sort
    # Custom sort order: Hallmark -> Vernier FR1 -> FR2 -> FR3
    # Inside type: by Position
    df_pivot["Position"] = df_pivot["Position"].astype(int)
    df_pivot = df_pivot.sort_values(["Type", "Position"])
    
    # 6. Update Interpretations
    def interpret(row):
        pos = row["Position"]
        if pos == 47: return "Solubility Switch: R (Long) vs L/P (Short)"
        if pos == 71: return "Structural Anchor: Conserved R"
        if pos == 37: return "Interface: G/A (Long) vs S (Short)"
        if pos in [27, 28, 29, 30]: return "FR1 Vernier: Highly Conserved"
        if pos in [48, 49]: return "FR2 Vernier: Co-evolves with Hallmark 47"
        if pos in [93, 94]: return "FR3 Vernier: Highly Conserved"
        return ""
    
    df_pivot["Interpretation"] = df_pivot.apply(interpret, axis=1)
    
    df_pivot.to_csv(OUT_TABLES1, index=False)
    print(f"Updated Table S1 saved to: {OUT_TABLES1}")

if __name__ == "__main__":
    main()
