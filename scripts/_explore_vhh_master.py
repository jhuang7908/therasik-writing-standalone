import pandas as pd
df = pd.read_csv('data/vhh_master_benchmarks_v3.csv')
print(df['category'].value_counts())
print()
print('with pdb_path:', df['pdb_path'].notna().sum())
print()
print('first 5 with pdb_path:')
print(df[df['pdb_path'].notna()].head(5)[['id', 'category', 'source', 'pdb_path']].to_string())
