import pandas as pd
import sys
import os

# Load the database
file_path = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\humanization_assay\thera_human_igG_germline_analysis.xlsx'
if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    sys.exit(1)

try:
    df = pd.read_excel(file_path)
except Exception as e:
    print(f"Error reading excel: {e}")
    sys.exit(1)

# Search for broader keywords
keywords = ["dog", "canine", "canin", "vetmab", "lokivetmab", "bedinvetmab", "gilvetmab"]
columns_to_search = ['Name', 'INN', 'format_raw', 'human_origin_mode']

found_indices = set()

for col in columns_to_search:
    if col in df.columns:
        for keyword in keywords:
            # Case insensitive search
            matches = df[df[col].astype(str).str.contains(keyword, case=False, na=False)]
            for idx in matches.index:
                found_indices.add(idx)

if not found_indices:
    print("No obvious 'dog' or 'canine' entries found in metadata columns.")
else:
    print(f"Found {len(found_indices)} entries:")
    results = df.loc[list(found_indices)]
    for idx, row in results.iterrows():
        print(f"\n--- Entry {idx} ---")
        print(f"Name: {row.get('Name')}")
        print(f"INN: {row.get('INN')}")
        print(f"Origin Mode: {row.get('human_origin_mode')}")
        print(f"VH: {row.get('VH')}")
        print(f"VL: {row.get('VL')}")
