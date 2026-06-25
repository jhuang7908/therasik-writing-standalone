import pandas as pd
import sys
import os

file_path = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\thera_export.xlsx'
df = pd.read_excel(file_path)

mask = df.apply(lambda x: x.astype(str).str.contains('dog|canine|canis|vetmab', case=False, na=False)).any(axis=1)
results = df[mask]

print(f"Found {len(results)} entries:")
for idx, row in results.iterrows():
    # Try to find a name column
    name = row.get('Therapeutic') or row.get('Name') or row.get('INN') or "Unknown"
    print(f"Index {idx}: {name}")
    # Print a few non-null columns to see what's there
    print(row.dropna().head(5).to_dict())
    print("-" * 20)
