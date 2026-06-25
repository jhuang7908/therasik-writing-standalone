import pandas as pd

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

# Filter for antibodies with sequences
df_seq = df[df['vh_seq'].notna() & df['vl_seq'].notna()]

print(f"Total antibodies with sequences: {len(df_seq)}")

# Check missing values in key fields for these 303 antibodies
fields = ['ada_value', 'nab_pct', 'dose_mg', 'dose_freq', 'route_curated', 'assay_platform', 'pk_efficacy_impact']
missing_counts = df_seq[fields].isna().sum()

print("\nMissing values in key fields for antibodies with sequences:")
print(missing_counts)

# List some antibodies that still have missing data
missing_ada = df_seq[df_seq['ada_value'].isna()]['antibody_name'].tolist()
print(f"\nExample antibodies with missing ADA value ({len(missing_ada)} total):")
print(missing_ada[:20])
