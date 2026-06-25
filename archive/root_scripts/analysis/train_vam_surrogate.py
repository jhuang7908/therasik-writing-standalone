import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from scipy.stats import spearmanr
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv(r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\absci_benchmark_data\results.csv')
df = df[(df.source == 'abscibind') & df.pkd_exp.notnull()].copy()
features = ['evoef2_dg', 'prodigy_dg', 'thermompnn_mean_ddg', 'ablang_score']
df = df.dropna(subset=features + ['pkd_exp'])

results = []
for target in df['target'].unique():
    tdf = df[df['target'] == target]
    if len(tdf) < 30: continue
    
    # Zero shot baseline (using prodigy as best single tool, negative because lower energy = higher pKD)
    r_zs, _ = spearmanr(-tdf['prodigy_dg'], tdf['pkd_exp'])
    
    # Few shot
    fs_corrs = []
    for _ in range(100):
        train = tdf.sample(n=15, random_state=None)
        test = tdf.drop(train.index)
        
        model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
        model.fit(train[features], train['pkd_exp'])
        preds = model.predict(test[features])
        
        r_fs, _ = spearmanr(preds, test['pkd_exp'])
        fs_corrs.append(r_fs)
        
    results.append({
        'Target': target,
        'ZeroShot_Rho': r_zs,
        'FewShot_15_Rho_Mean': np.nanmean(fs_corrs),
        'FewShot_15_Rho_Max': np.nanmax(fs_corrs)
    })

res_df = pd.DataFrame(results)
print("=== Few-Shot Surrogate Model (15 samples) ===")
print(res_df.to_string(index=False))
