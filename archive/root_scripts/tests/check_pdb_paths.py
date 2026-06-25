import pandas as pd
import os

df = pd.read_csv('data/immunogenicity_panel_136_master.csv')
sub = df[df['pdb_path'].notna()][['antibody_name','pdb_path']].head(8)
print(sub.to_string(index=False))
first_pdb = df['pdb_path'].dropna().iloc[0]
print('\nFirst pdb_path:', first_pdb)
print('Exists (abs):', os.path.isfile(str(first_pdb)))
print('Exists (rel):', os.path.isfile(str(first_pdb).lstrip('/')))
