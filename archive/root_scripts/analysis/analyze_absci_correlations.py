import pandas as pd
import numpy as np
from scipy.stats import spearmanr

df = pd.read_csv(r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\absci_benchmark_data\results.csv')

# Filter rows with experimental pKD
df_pkd = df[df['pkd_exp'].notnull()].copy()

targets = df_pkd['target'].unique()
tools = ['evoef2_dg', 'prodigy_dg', 'thermompnn_mean_ddg', 'ablang_score']

results = []

for target in targets:
    target_df = df_pkd[df_pkd['target'] == target]
    if len(target_df) < 5:
        continue
    
    target_results = {'target': target, 'N': len(target_df)}
    for tool in tools:
        # Spearman correlation
        # Note: for dg/ddg, lower is usually better (stronger binding), 
        # while for pKD, higher is better. So we expect negative correlation.
        corr, p = spearmanr(target_df[tool], target_df['pkd_exp'])
        target_results[f'{tool}_corr'] = corr
        target_results[f'{tool}_p'] = p
    results.append(target_results)

res_df = pd.DataFrame(results)
print(res_df.to_string())

# Calculate overall average correlation (weighted by N)
print("\nWeighted Average Spearman Correlation per Target:")
for tool in tools:
    valid_df = res_df[res_df[f'{tool}_corr'].notnull()]
    avg_corr = (valid_df[f'{tool}_corr'] * valid_df['N']).sum() / valid_df['N'].sum()
    print(f"{tool}: {avg_corr:.3f}")
