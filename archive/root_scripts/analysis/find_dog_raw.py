import pandas as pd
import sys
import os

file_path = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\thera_export.xlsx'
if not os.path.exists(file_path):
    print("File not found")
    sys.exit(1)

df = pd.read_excel(file_path)

# Search for "dog" or "canine"
mask = df.apply(lambda x: x.astype(str).str.contains('dog|canine|canis|vetmab', case=False, na=False)).any(axis=1)
results = df[mask]

print(f"Found {len(results)} entries in raw export:")
for idx, row in results.iterrows():
    print(f"- {row.get('Name')} (INN: {row.get('INN')})")
