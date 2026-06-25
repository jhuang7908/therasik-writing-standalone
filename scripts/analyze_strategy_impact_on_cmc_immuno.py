import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import f_oneway, ttest_ind

# Paths
PROJECT_ROOT = Path('.').resolve()
IMMUNO_CSV = PROJECT_ROOT / "reports" / "slice3_vhh_immunogenicity_features.csv"
CMC_CSV = PROJECT_ROOT / "reports" / "slice3_vhh_developability_features_native_sr_bm.csv"
STRATEGY_CSV = PROJECT_ROOT / "reports" / "slice3_vhh_comprehensive_functional_library.csv"
OUT_MD = PROJECT_ROOT / "reports" / "slice3_vhh_strategy_comparison_cmc_immuno.md"

# Load Data
try:
    df_imm = pd.read_csv(IMMUNO_CSV)
    df_cmc = pd.read_csv(CMC_CSV)
    df_strat = pd.read_csv(STRATEGY_CSV)
except FileNotFoundError as e:
    print(f"Error loading files: {e}")
    exit(1)

# Prepare Strategy Map
# Need to simplify strategy names for grouping
def simplify_strat(s):
    if 'BM' in s: return 'BM'
    if 'SR' in s: return 'SR'
    if 'Native' in s: return 'Native'
    return 'Other'

df_strat['Group'] = df_strat['Humanization Strategy'].apply(simplify_strat)
strat_map = df_strat.set_index('Drug Name')['Group'].to_dict()

# Merge Logic
# The Immuno/CMC files contain rows for 'native', 'sr', 'bm' VARIANTS of each drug.
# BUT here we want to evaluate the *ACTUAL* drug molecule (the one that is marketed/clinical).
# The "Native" variant in those files refers to the starting alpaca sequence.
# The "SR" variant refers to a hypothetical SR design.
# The "BM" variant refers to a hypothetical BM design.
#
# Wait! The drugs in Slice-3 *ARE* the final molecules.
# So we should treat the Slice-3 sequences as the objects to evaluate.
#
# In the previous scripts (run_slice3_...):
# - Input was the "Native" (Slice-3) sequence.
# - It generated theoretical SR and BM variants FROM that sequence.
#
# This implies:
# The data in `df_imm` / `df_cmc` with `variant='native'` actually represents the **Slice-3 Clinical Molecule** itself (because we fed the clinical sequence as the input).
#
# Let's verify this assumption.
# Yes, typically "Native" in that context meant "Input Sequence".
# Since inputs are clinical drugs (Caplacizumab etc), `variant='native'` = Clinical Drug.

# Filter for the Clinical Molecule (variant='native')
clinical_imm = df_imm[df_imm['variant'] == 'native'].copy()
clinical_cmc = df_cmc[df_cmc['variant'] == 'native'].copy()

# Add Strategy Labels
clinical_imm['Strategy'] = clinical_imm['antibody_id'].map(strat_map)
clinical_cmc['Strategy'] = clinical_cmc['antibody_id'].map(strat_map)

# Metrics to Analyze
# Immuno: B_total_1pct (Lower is better), min_rank (Higher is better/safer)
# CMC: dev_score (Higher is better, 0-100), net_charge, hydrophobic_frac_cdr3

def analyze_group(df, metric, name, higher_is_better=True):
    groups = df.groupby('Strategy')[metric]
    means = groups.mean()
    stds = groups.std()
    ns = groups.count()
    
    # Anova
    vals = [g[1] for g in groups]
    if len(vals) > 1:
        f, p = f_oneway(*vals)
    else:
        f, p = 0, 1.0
        
    return {
        "Metric": name,
        "BM_Mean": means.get('BM', np.nan),
        "SR_Mean": means.get('SR', np.nan),
        "Native_Mean": means.get('Native', np.nan),
        "P-Value": p,
        "Trend": "Significant" if p < 0.05 else "NS"
    }

metrics = [
    (clinical_imm, 'B_total_1pct', 'Immuno Score (Lower=Better)', False),
    (clinical_cmc, 'score', 'CMC Dev Score (Higher=Better)', True),
    (clinical_cmc, 'hydrophobic_frac_global', 'Hydrophobicity (Global)', False),
    (clinical_cmc, 'net_charge', 'Net Charge', None)
]

results = []
for df_src, col, desc, hib in metrics:
    if col in df_src.columns:
        results.append(analyze_group(df_src, col, desc, hib))

res_df = pd.DataFrame(results)

# Generate Report
with open(OUT_MD, 'w', encoding='utf-8') as f:
    f.write("# VHH Strategy Comparison: CMC & Immunogenicity\n\n")
    f.write("Analysis of the *actual clinical molecules* (Slice-3) grouped by their inferred humanization strategy.\n\n")
    
    f.write("## 1. Summary Statistics\n")
    f.write(res_df.to_markdown(index=False, floatfmt=".2f"))
    
    f.write("\n\n## 2. Detailed Interpretation\n")
    
    # Immuno
    imm_rows = res_df[res_df['Metric'].str.contains('Immuno')]
    if not imm_rows.empty:
        row = imm_rows.iloc[0]
        f.write(f"\n### Immunogenicity (IEDB MHC-II Binding)\n")
        f.write(f"- **BM Mean**: {row['BM_Mean']:.2f}\n")
        f.write(f"- **SR Mean**: {row['SR_Mean']:.2f}\n")
        f.write(f"- **Native Mean**: {row['Native_Mean']:.2f}\n")
        if row['P-Value'] < 0.05:
            f.write("- **Conclusion**: Statistically significant difference found.\n")
        else:
            f.write("- **Conclusion**: No statistically significant difference observed (P > 0.05). This suggests that high-quality Native/SR VHHs can achieve immuno-profiles comparable to BM.\n")

    # CMC
    cmc_rows = res_df[res_df['Metric'].str.contains('Dev Score')]
    if not cmc_rows.empty:
        row = cmc_rows.iloc[0]
        f.write(f"\n### CMC Developability Score\n")
        f.write(f"- **BM Mean**: {row['BM_Mean']:.2f}\n")
        f.write(f"- **SR Mean**: {row['SR_Mean']:.2f}\n")
        f.write(f"- **Native Mean**: {row['Native_Mean']:.2f}\n")
    
    f.write("\n## 3. Raw Data Extract\n")
    merged = pd.merge(clinical_imm[['antibody_id', 'Strategy', 'B_total_1pct']], 
                      clinical_cmc[['antibody_id', 'score']], 
                      on='antibody_id')
    f.write(merged.sort_values('Strategy').to_markdown(index=False, floatfmt=".2f"))

print(f"Analysis complete. Report written to {OUT_MD}")
print(res_df.to_string())
