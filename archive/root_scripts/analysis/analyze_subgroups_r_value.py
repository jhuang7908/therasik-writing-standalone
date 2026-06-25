import pandas as pd
import numpy as np
from scipy.stats import spearmanr, pearsonr

df = pd.read_csv('data/immunogenicity_panel_136_master.csv')
#  Tier A+B 
df = df[df['evidence_tier'].isin(['A','B'])].dropna(subset=['ada_v2_score', 'ada_first_pct'])

def get_metrics(sub_df, name):
    if len(sub_df) < 5: return
    x = sub_df['ada_v2_score'].values
    y = sub_df['ada_first_pct'].values
    y_log = np.log1p(y)
    
    rho, p_s = spearmanr(x, y)
    r, p_p = pearsonr(x, y_log)
    
    # 
    sig_rho = "**" if p_s < 0.05 else ("*" if p_s < 0.1 else "")
    sig_r = "**" if p_p < 0.05 else ("*" if p_p < 0.1 else "")
    
    print(f"| {name} | {len(sub_df)} | {rho:+.3f} {sig_rho} | {r:+.3f} {sig_r} |")

print("###  ADA \n")
print("|  (Subgroup) |  (n) | Spearman rho  | Pearson r (, log) |")
print("| :--- | :--- | :--- | :--- |")

get_metrics(df, "1.  CLEAN-124 (，)")

#  Fc 
get_metrics(df[df['fc_isotype'] == 'G1'], "2.  IgG1 ( Fc )")
get_metrics(df[df['fc_isotype'] == 'G4'], "3.  IgG4")

#  (、CD52ADA)
get_metrics(df[df['ada_first_pct'] <= 40], "4.  (ADA ≤ 40%)")

#  ( vs /)
oncology_targets = ['PDCD1', 'CD274', 'CTLA4', 'EGFR', 'ERBB2', 'MS4A1', 'CD19', 'CD33', 'CD38', 'CD52', 'VEGFA']
immuno_targets = ['TNF', 'IL', 'CSF', 'ITG', 'C5', 'IGE']

def classify_disease(t):
    t = str(t).upper
    if any(x in t for x in oncology_targets): return 'Oncology'
    if any(x in t for x in immuno_targets): return 'Immunology'
    return 'Other'

df['disease'] = df['targets'].apply(classify_disease)
get_metrics(df[df['disease'] == 'Oncology'], "5.   ( IV  + )")
get_metrics(df[df['disease'] == 'Immunology'], "6.  / ( SC )")

# ： +  + 
strict_immuno = df[(df['fc_isotype'] == 'G1') & (df['disease'] == 'Immunology') & (df['ada_first_pct'] <= 40)]
get_metrics(strict_immuno, "7. : IgG1 +  + ")

strict_onco = df[(df['fc_isotype'] == 'G1') & (df['disease'] == 'Oncology') & (df['ada_first_pct'] <= 40)]
get_metrics(strict_onco, "8. : IgG1 +  + ")

# 
get_metrics(df[df['origin'] == 'natural'], "9.   (Natural)")
get_metrics(df[df['origin'] == 'engineered'], "10.   (Engineered)")
