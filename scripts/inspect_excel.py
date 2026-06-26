import pandas as pd

files = [
    r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\media-1.xlsx",
    r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\media-2.xlsx"
]

for file in files:
    print(f"\nInspecting {file.split('\\')[-1]}:")
    try:
        xl = pd.ExcelFile(file)
        print("Sheet names:", xl.sheet_names)
        
        for sheet in xl.sheet_names:
            print(f"  Sheet: {sheet}")
            # Try reading skipping the first row in case it's a disclaimer
            df = pd.read_excel(file, sheet_name=sheet, skiprows=1)
            print("  Columns (skip 1):", df.columns.tolist()[:10])
            if 'Unnamed: 0' in df.columns or len(df.columns) < 3:
                # Maybe skip 2 rows
                df2 = pd.read_excel(file, sheet_name=sheet, skiprows=2)
                print("  Columns (skip 2):", df2.columns.tolist()[:10])
    except Exception as e:
        print(f"Error reading {file}: {e}")
