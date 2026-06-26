import pandas as pd

try:
    df = pd.read_excel("data/thera_sabdab/thera_export.xlsx")
    print("Columns:", df.columns.tolist())
    
    # Check if we have sequence columns
    possible_seq_cols = [c for c in df.columns if 'seq' in c.lower() or 'vh' in c.lower() or 'vl' in c.lower() or 'heavy' in c.lower() or 'light' in c.lower()]
    print("Possible sequence columns:", possible_seq_cols)
    
    # Check for Acasunlimab
    row = df[df['Therapeutic'] == 'Acasunlimab']
    if not row.empty:
        print("Acasunlimab found.")
        # Print non-null columns for this row to see where sequence might be
        print(row.dropna(axis=1).iloc[0])
    else:
        print("Acasunlimab NOT found in thera_export.xlsx")

except Exception as e:
    print(f"Error: {e}")
