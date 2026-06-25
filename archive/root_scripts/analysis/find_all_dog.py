import pandas as pd
import sys
import os

file_path = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\humanization_assay\thera_human_igG_germline_analysis.xlsx'
df = pd.read_excel(file_path)

# Search entire dataframe for "dog" or "canine"
mask = df.apply(lambda x: x.astype(str).str.contains('dog|canine|canis', case=False, na=False)).any(axis=1)
results = df[mask]

print(f"Found {len(results)} entries:")
for idx, row in results.iterrows():
    print(f"- {row.get('Name')} (INN: {row.get('INN')})")
