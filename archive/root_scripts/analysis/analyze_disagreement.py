import pandas as pd
import numpy as np
from scipy.stats import zscore

df = pd.read_csv(r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\absci_benchmark_data\results.csv')
tasks = pd.read_csv(r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\absci_benchmark_data\tasks.csv')[['design_id', 'mutation']]
df = df.merge(tasks, on='design_id', how='left')
df = df[df.source == 'abscibind'].copy()
df['binder'] = df['binder'].fillna(False).astype(bool)
df = df.dropna(subset=['evoef2_dg', 'prodigy_dg'])

# Z-scores per target to normalize baseline differences
df['z_evo'] = df.groupby('target')['evoef2_dg'].transform(lambda x: zscore(-x))
df['z_prod'] = df.groupby('target')['prodigy_dg'].transform(lambda x: zscore(-x))

evo_likes = df[(df['z_evo'] > 0.5) & (df['z_prod'] < -0.5)]
prod_likes = df[(df['z_prod'] > 0.5) & (df['z_evo'] < -0.5)]
both_like = df[(df['z_evo'] > 0.5) & (df['z_prod'] > 0.5)]
both_hate = df[(df['z_evo'] < -0.5) & (df['z_prod'] < -0.5)]

print("=== Disagreement Analysis (Z-score > 0.5 vs < -0.5) ===")
print(f"EvoEF2 likes but PRODIGY hates (N={len(evo_likes)}): Hit Rate = {evo_likes['binder'].mean():.1%}")
print(f"PRODIGY likes but EvoEF2 hates (N={len(prod_likes)}): Hit Rate = {prod_likes['binder'].mean():.1%}")
print(f"Both like (N={len(both_like)}): Hit Rate = {both_like['binder'].mean():.1%}")
print(f"Both hate (N={len(both_hate)}): Hit Rate = {both_hate['binder'].mean():.1%}")

print("\nLet's look at the mutations where EvoEF2 likes but PRODIGY hates:")
print(evo_likes[['target', 'mutation', 'binder', 'evoef2_dg', 'prodigy_dg']].head(10).to_string(index=False))

print("\nLet's look at the mutations where PRODIGY likes but EvoEF2 hates:")
print(prod_likes[['target', 'mutation', 'binder', 'evoef2_dg', 'prodigy_dg']].head(10).to_string(index=False))
