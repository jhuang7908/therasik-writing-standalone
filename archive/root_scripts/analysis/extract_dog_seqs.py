import pandas as pd
import sys
import os

file_path = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\thera_export.xlsx'
df = pd.read_excel(file_path)

targets = ["Lokivetmab", "Bedinvetmab", "Gilvetmab", "Landogrozumab"]
results = df[df['Therapeutic'].isin(targets)]

print(f"Found {len(results)} targets.")
for idx, row in results.iterrows():
    print(f"\n> {row['Therapeutic']}")
    print(f"VH: {row.get('HeavySequence')}")
    print(f"VL: {row.get('LightSequence')}")
