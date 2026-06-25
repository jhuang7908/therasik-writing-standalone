import pandas as pd
import numpy as np

df = pd.read_csv(r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\absci_benchmark_data\results.csv')
df = df[df.source == 'abscibind'].copy()
df['binder'] = df['binder'].fillna(False).astype(bool)

print("=== Mean Scores: Binders vs Non-Binders ===")
print(df.groupby('binder')[['evoef2_dg', 'prodigy_dg', 'thermompnn_mean_ddg', 'ablang_score']].mean())

print("\n=== Sequential Gating with EvoEF2 ===")
g1 = df[df['ablang_score'] >= df['ablang_score'].quantile(0.25)]
g2 = g1[g1['thermompnn_mean_ddg'] <= g1['thermompnn_mean_ddg'].quantile(0.75)]
# If tools are backwards, maybe we should take the WORST scores?
g3_evo_best = g2[g2['evoef2_dg'] <= g2['evoef2_dg'].quantile(0.20)]
g3_evo_worst = g2[g2['evoef2_dg'] >= g2['evoef2_dg'].quantile(0.80)]

print(f"Base: {df['binder'].mean():.1%}")
print(f"Gate 1+2: {g2['binder'].mean():.1%}")
print(f"Gate 3 (EvoEF2 Best 20%): {g3_evo_best['binder'].mean():.1%}")
print(f"Gate 3 (EvoEF2 Worst 20%): {g3_evo_worst['binder'].mean():.1%}")
