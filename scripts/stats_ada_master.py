import pandas as pd
import os

csv_path = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada245\database\ada_master_245_curated.csv"

if not os.path.exists(csv_path):
    raise FileNotFoundError(f"CSV not found: {csv_path}")

df = pd.read_csv(csv_path)

# Total entries
total_entries = len(df)

# Evidence tier counts (assuming column name 'evidence_tier')
if 'evidence_tier' in df.columns:
    tier_counts = df['evidence_tier'].value_counts().to_dict()
else:
    tier_counts = {}

# Reliable sources (exclude placeholder or unreachable)
if 'evidence_source' in df.columns:
    reliable_mask = ~df['evidence_source'].astype(str).str.contains('UNREACHABLE|PLACEHOLDER', case=False, na=False)
    reliable_entries = df[reliable_mask]
    reliable_count = len(reliable_entries)
else:
    reliable_count = 0

# Entries with ADA incidence data (non-null ada_value_display)
if 'ada_value_display' in df.columns:
    ada_data_count = df['ada_value_display'].notna().sum()
else:
    ada_data_count = 0

print("=== ADA Master Database Statistics ===")
print(f"Total entries: {total_entries}")
print("Evidence tier distribution:")
for tier, cnt in tier_counts.items():
    print(f"  {tier}: {cnt}")
print(f"Reliable source entries: {reliable_count}")
print(f"Entries with ADA incidence data: {ada_data_count}")
