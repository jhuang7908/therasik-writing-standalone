import pandas as pd
df = pd.read_csv(r'data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv')
print('columns:', list(df.columns[:20]))
print('shape:', df.shape)
target_col = [c for c in df.columns if 'target' in c.lower()]
print('target cols:', target_col)
print(df[target_col[:1]+['antibody_name','ada_first_pct']].head(30).to_string())
