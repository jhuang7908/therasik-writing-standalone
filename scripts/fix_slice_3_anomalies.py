import pandas as pd
import os

# Paths
slice_dir = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\out\slice_ids"
feature_dir = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\features"

slice3_txt = os.path.join(slice_dir, "slice_3_vhh_design.txt")
slice4_txt = os.path.join(slice_dir, "slice_4_bispecific_engineering.txt")

germline_parquet = os.path.join(feature_dir, "germline_match_slice_3_vhh_design.parquet")
numbering_parquet = os.path.join(feature_dir, "anarcii_numbering_slice_3_vhh_design.parquet")

# IDs to process
vl_only = ['Lulizumab', 'Placulumab']
vh_vl_dual = ['Gocatamig1', 'Podentamig2']
to_remove = vl_only + vh_vl_dual

print(f"Removing from Slice 3: {to_remove}")
print(f"Moving to Slice 4: {vh_vl_dual}")

# 1. Update Slice 3 TXT
if os.path.exists(slice3_txt):
    with open(slice3_txt, 'r') as f:
        ids = [line.strip() for line in f if line.strip()]
    new_ids = [i for i in ids if i not in to_remove]
    with open(slice3_txt, 'w') as f:
        for i in sorted(new_ids):
            f.write(f"{i}\n")
    print(f"Updated {slice3_txt}: {len(ids)} -> {len(new_ids)}")

# 2. Update Slice 4 TXT
if os.path.exists(slice4_txt):
    with open(slice4_txt, 'r') as f:
        ids = [line.strip() for line in f if line.strip()]
    added = []
    for i in vh_vl_dual:
        if i not in ids:
            ids.append(i)
            added.append(i)
    with open(slice4_txt, 'w') as f:
        for i in sorted(ids):
            f.write(f"{i}\n")
    print(f"Updated {slice4_txt}: added {added}")

# 3. Filter Parquet files
for p_path in [germline_parquet, numbering_parquet]:
    if os.path.exists(p_path):
        df = pd.read_parquet(p_path)
        original_len = len(df)
        df_filtered = df[~df['antibody_id'].isin(to_remove)]
        df_filtered.to_parquet(p_path)
        print(f"Filtered {p_path}: {original_len} -> {len(df_filtered)}")
