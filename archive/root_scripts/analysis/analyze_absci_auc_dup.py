import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score

df = pd.read_csv(r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\absci_benchmark_data\results.csv')

# Filter rows with binder label
df_binder = df[df['binder'].notnull()].copy()
df_binder['binder'] = df_binder['binder'].astype(bool)

targets = df_binder['target'].unique()
tools = ['evoef2_dg', 'prodigy_dg', 'thermompnn_mean_ddg', 'ablang_score']

results = []

for target in targets:
    target_df = df_binder[df_binder['target'] == target]
    # Need both classes to calculate AUC
    if len(target_df['binder'].unique()) < 2:
        continue
    
    target_results = {'target': target, 'N': len(target_df)}
    for tool in tools:
        # For dg/ddg, lower is better (more likely to be binder)
        # roc_auc_score expects higher values for positive class
        # So we use -tool_value
        try:
            auc = roc_auc_score(target_df['binder'], -target_df[tool])
            target_results[f'{tool}_auc'] = auc
        except:
            target_results[f'{tool}_auc'] = np.nan
            
    results.append(target_results)

res_df = pd.DataFrame(results)
print(res_df.to_string())

print("\nWeighted Average AUC per Target:")
for tool in tools:
    valid_df = res_df[res_df[f'{tool}_auc'].notnull()]
    avg_auc = (valid_df[f'{tool}_auc'] * valid_df['N']).sum() / valid_df['N'].sum()
    print(f"{tool}: {avg_auc:.3f}")
