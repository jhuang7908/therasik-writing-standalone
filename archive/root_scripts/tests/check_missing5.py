import pandas as pd
df = pd.read_csv('data/immunogenicity_panel_136_master.csv')
missing = df[df['immuno_tcia_score'].isna()][['antibody_name','panel_source','thera_genetics_class']]
print('5 antibodies missing CMC/MHC-II (P70-only, not in atlas):')
print(missing.to_string(index=False))
print()
print('cmc_flags coverage:', df['cmc_flags'].notna().sum(), '/', len(df))
print('Note: cmc_flags is qualitative text flags, not numeric score')
