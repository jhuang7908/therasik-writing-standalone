import pandas as pd
import numpy as np

df = pd.read_csv(r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\absci_benchmark_data\results.csv')
df = df[df.source == 'abscibind'].copy()
df['binder'] = df['binder'].fillna(False).astype(bool)
features = ['evoef2_dg', 'prodigy_dg', 'thermompnn_mean_ddg', 'ablang_score']
df = df.dropna(subset=features)

print("=== Sequential Gating Analysis ===")
print(f"Initial Pool: {len(df)} variants, Binders: {df['binder'].sum()} ({df['binder'].mean():.1%})")

# Gate 1: AbLang (Naturalness) - drop bottom 25%
ablang_thresh = df['ablang_score'].quantile(0.25)
g1 = df[df['ablang_score'] >= ablang_thresh]
print(f"Gate 1 (AbLang >= {ablang_thresh:.3f}): {len(g1)} variants, Binders: {g1['binder'].sum()} ({g1['binder'].mean():.1%})")

# Gate 2: ThermoMPNN (Stability) - drop top 25% (highest ddg = worst stability)
thermo_thresh = g1['thermompnn_mean_ddg'].quantile(0.75)
g2 = g1[g1['thermompnn_mean_ddg'] <= thermo_thresh]
print(f"Gate 2 (ThermoMPNN <= {thermo_thresh:.3f}): {len(g2)} variants, Binders: {g2['binder'].sum()} ({g2['binder'].mean():.1%})")

# Gate 3: PRODIGY (Binding) - take top 20% of remaining
prod_thresh = g2['prodigy_dg'].quantile(0.20)
g3 = g2[g2['prodigy_dg'] <= prod_thresh]
print(f"Gate 3 (PRODIGY <= {prod_thresh:.3f}): {len(g3)} variants, Binders: {g3['binder'].sum()} ({g3['binder'].mean():.1%})")

print("\nEnrichment Factor:")
print(f"Final Hit Rate: {g3['binder'].mean():.1%} vs Base Hit Rate: {df['binder'].mean():.1%}")
