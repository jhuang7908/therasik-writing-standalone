import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# IMGT Standard Lengths (average/expected without gaps)
IMGT_STANDARDS = {
    "VH": {"FR1": 26, "CDR1": 8, "FR2": 17, "CDR2": 8, "FR3": 38, "FR4": 11},
    "VL": {"FR1": 26, "CDR1": 10, "FR2": 17, "CDR2": 3, "FR3": 36, "FR4": 10} # Simplified
}

def analyze_lengths():
    file_path = PROJECT_ROOT / "data" / "humanization_assay" / "thera_human_igG_segmented.xlsx"
    df = pd.read_excel(file_path)
    
    targets = ['Calpurbatug', 'Elipovimab', 'Zinlirvimab']
    result_df = df[df['Name'].isin(targets)]
    
    print(f"{'Name':<15} | {'Region':<8} | {'Length':<6} | {'IMGT Std':<8} | {'Status'}")
    print("-" * 60)
    
    for _, row in result_df.iterrows():
        name = row['Name']
        chain = "VH" if name == "Calpurbatug" else "VL"
        std = IMGT_STANDARDS[chain]
        
        regions = ['FR1', 'CDR1', 'FR2', 'CDR2', 'FR3', 'CDR3', 'FR4']
        for r in regions:
            col = f"{chain}_{r}"
            seq = str(row.get(col, ""))
            length = len(seq) if seq != "nan" else 0
            
            standard_val = std.get(r, "N/A")
            status = "OK"
            if isinstance(standard_val, int):
                diff = abs(length - standard_val)
                if diff > 5: status = "deviation!"
                if diff > 10: status = "MAJOR deviation!"
            
            print(f"{name:<15} | {r:<8} | {length:<6} | {standard_val:<8} | {status}")
        print("-" * 60)

if __name__ == "__main__":
    analyze_lengths()
