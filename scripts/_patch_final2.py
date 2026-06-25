import pandas as pd
df = pd.read_csv('data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv', low_memory=False)
patches = {'Abelacimab': 'fully_human', 'Bermekimab': 'fully_human'}
for name, cls in patches.items():
    mask = df['antibody_name'] == name
    df.loc[mask, 'thera_genetics_class'] = cls
df.to_csv('data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv', index=False)
result = f"Done. NaN remaining: {df['thera_genetics_class'].isna().sum()}\n"
result += str(df['thera_genetics_class'].value_counts(dropna=False).to_dict())
with open('scripts/_patch_result.txt', 'w') as f:
    f.write(result)
print(result)
