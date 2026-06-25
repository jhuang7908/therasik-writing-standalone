import pandas as pd
import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv(r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\absci_benchmark_data\results.csv')
df['binder'] = df['binder'].fillna(False).astype(bool)
tools = ['evoef2_dg', 'prodigy_dg', 'thermompnn_mean_ddg', 'ablang_score']

print("=== 1. Dataset Overview ===")
for src in ['abscibind', 'abscigen']:
    sub = df[df.source == src]
    pkd_n = sub['pkd_exp'].notnull().sum()
    binder_n = sub['binder'].sum()
    print(f"  {src}: N={len(sub)}, Binders={binder_n} ({binder_n/len(sub):.1%}), pKD available={pkd_n}")

print("\n=== 2. Per-Target Summary Table ===")
targets = df['target'].unique()
rows = []
for tgt in targets:
    sub = df[df.target == tgt]
    source_val = sub['source'].iloc[0]
    binder_n = sub['binder'].sum()
    row = {
        'Target': tgt,
        'Source': source_val,
        'N': len(sub),
        'Binder_Rate': f"{sub['binder'].mean():.1%}"
    }
    pkd_sub = sub[sub['pkd_exp'].notnull()]
    for t in tools:
        valid = pkd_sub[[t, 'pkd_exp']].dropna()
        if len(valid) > 4:
            r, p = spearmanr(valid[t], valid['pkd_exp'])
            row[f'{t}_rho'] = round(r, 3)
        else:
            row[f'{t}_rho'] = 'N/A'
        bsub = sub[sub[t].notnull()]
        if len(bsub['binder'].unique()) > 1:
            try:
                score_col = bsub[t] if t == 'ablang_score' else -bsub[t]
                auc = roc_auc_score(bsub['binder'], score_col)
                row[f'{t}_auc'] = round(auc, 3)
            except:
                row[f'{t}_auc'] = 'N/A'
        else:
            row[f'{t}_auc'] = 'N/A'
    rows.append(row)

rdf = pd.DataFrame(rows)
print(rdf.to_string(index=False))

print("\n=== 3. Global Average AUC (abscibind only) ===")
bind_df = df[df.source == 'abscibind'].copy()
for t in tools:
    aucs = []
    for tgt in bind_df['target'].unique():
        sub = bind_df[bind_df.target == tgt]
        bsub = sub[sub[t].notnull()]
        if len(bsub['binder'].unique()) > 1 and len(bsub) >= 10:
            try:
                score_col = bsub[t] if t == 'ablang_score' else -bsub[t]
                auc = roc_auc_score(bsub['binder'], score_col)
                aucs.append((auc, len(bsub)))
            except:
                pass
    if aucs:
        weighted = sum(a*n for a,n in aucs) / sum(n for _,n in aucs)
        simple = np.mean([a for a,_ in aucs])
        print(f"  {t:30s}: weighted_AUC={weighted:.3f}, simple_mean={simple:.3f}")

print("\n=== 4. Binder vs Non-Binder Mean Score Comparison ===")
print(bind_df.groupby('binder')[tools].mean().round(3))

print("\n=== 5. Sequential Gating Simulation (abscibind) ===")
g0 = bind_df.dropna(subset=tools)
print(f"  Base pool: N={len(g0)}, hit_rate={g0['binder'].mean():.1%}")
g1 = g0[g0['ablang_score'] >= g0['ablang_score'].quantile(0.25)]
print(f"  Gate1 AbLang >= Q25: N={len(g1)}, hit_rate={g1['binder'].mean():.1%}")
g2 = g1[g1['thermompnn_mean_ddg'] <= g1['thermompnn_mean_ddg'].quantile(0.75)]
print(f"  Gate2 ThermoMPNN <= Q75: N={len(g2)}, hit_rate={g2['binder'].mean():.1%}")
g3_best = g2[g2['prodigy_dg'] <= g2['prodigy_dg'].quantile(0.25)]
g3_best_evo = g2[g2['evoef2_dg'] >= g2['evoef2_dg'].quantile(0.75)]
print(f"  Gate3a PRODIGY Top-25%: N={len(g3_best)}, hit_rate={g3_best['binder'].mean():.1%}")
print(f"  Gate3b EvoEF2 Top-25% (inverse): N={len(g3_best_evo)}, hit_rate={g3_best_evo['binder'].mean():.1%}")
