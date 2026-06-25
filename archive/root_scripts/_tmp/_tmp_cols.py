import pandas as pd
df = pd.read_csv(r'data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv')
print('Total cols:', len(df.columns))
print()
# Show all column names
for i, c in enumerate(df.columns):
    sample = df[c].dropna().iloc[0] if df[c].dropna().shape[0] > 0 else 'NaN'
    print(f'{i:3d}. {c:<45} sample={str(sample)[:60]}')
