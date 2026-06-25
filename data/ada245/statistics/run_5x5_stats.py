import pandas as pd
import numpy as np
from scipy import stats
import json

df = pd.read_csv('data/ada245/database/ada_master_245_curated.csv')

def map_platform(row):
    p = str(row.get('discovery_platform', ''))
    t = str(row.get('thera_genetics_class', '')).upper()
    if t == 'VHH': return 'VHH'
    if 'B-cell' in p: return 'B-cell Sorting'
    if 'Transgenic Mice' in p: return 'Transgenic Mice'
    if 'Phage' in p: return 'Phage Display'
    if 'CDR Grafting' in p or 'Humanized' in p: return 'Humanized'
    return None

df['platform_group'] = df.apply(map_platform, axis=1)
df['high_ada'] = (df['ada_first_pct'] >= 10).astype(int)
df['hpr'] = df['vh_identity_imgt'].fillna(df['vl_identity_imgt'])

platforms = ['B-cell Sorting', 'Transgenic Mice', 'Phage Display', 'Humanized', 'VHH']
metrics = {
    'HPR': 'hpr',
    'GRAVY': 'GRAVY',
    'Instability': 'instability_index',
    'pI': 'pI'
}

def best_threshold(values, labels):
    """Youden's J optimal threshold."""
    thresholds = np.percentile(values, np.arange(10, 90, 5))
    best_j, best_t = -1, None
    for t in thresholds:
        pred = (values >= t).astype(int)
        tp = ((pred == 1) & (labels == 1)).sum()
        fp = ((pred == 1) & (labels == 0)).sum()
        tn = ((pred == 0) & (labels == 0)).sum()
        fn = ((pred == 0) & (labels == 1)).sum()
        if (tp + fn) == 0 or (tn + fp) == 0:
            continue
        sens = tp / (tp + fn)
        spec = tn / (tn + fp)
        j = sens + spec - 1
        if j > best_j:
            best_j, best_t = j, t
    return best_t, best_j

results = []
print("=" * 100)
print(f"{'Platform':<22} {'Metric':<14} {'R':>7} {'p(Pearson)':>11} {'MW_p':>8} {'Threshold':>11} {'Youden_J':>9} {'N':>5} {'N_high':>7}")
print("=" * 100)

for p_name in platforms:
    sub = df[df.platform_group == p_name].copy()
    n_total = len(sub)
    n_high = int(sub.high_ada.sum())
    row = {'platform': p_name, 'N': n_total, 'N_high_ADA': n_high}

    for m_name, col in metrics.items():
        if col not in sub.columns:
            row[m_name] = {'status': 'column_missing'}
            print(f"  {p_name:<22} {m_name:<14} {'N/A':>7} {'N/A':>11} {'N/A':>8} {'N/A':>11} {'N/A':>9} {n_total:>5} {n_high:>7}")
            continue

        valid = sub[['ada_first_pct', 'high_ada', col]].dropna()
        n_valid = len(valid)

        if n_valid < 6:
            row[m_name] = {'status': f'n={n_valid}<6', 'n_valid': n_valid}
            print(f"  {p_name:<22} {m_name:<14} {'N/A':>7} {'N/A':>11} {'N/A':>8} {'N/A':>11} {'N/A':>9} {n_valid:>5} {n_high:>7}")
            continue

        # Pearson R vs continuous ADA
        r, p_val = stats.pearsonr(valid[col], valid['ada_first_pct'])

        # Mann-Whitney high vs low ADA groups
        hi = valid[valid.high_ada == 1][col]
        lo = valid[valid.high_ada == 0][col]
        if len(hi) >= 2 and len(lo) >= 2:
            _, mw_p = stats.mannwhitneyu(hi, lo, alternative='two-sided')
            mw_p_str = f"{mw_p:.4f}"
            sig = "**" if mw_p < 0.05 else ""
        else:
            mw_p_str = "N/A"
            sig = ""

        # Youden's J threshold
        thr, j = best_threshold(valid[col].values, valid['high_ada'].values)
        thr_str = f"{thr:.3f}" if thr is not None else "N/A"
        j_str = f"{j:.3f}" if j > -1 else "N/A"

        row[m_name] = {
            'R': round(float(r), 3),
            'pearson_p': round(float(p_val), 4),
            'MW_p': mw_p_str,
            'threshold': thr_str,
            'Youden_J': j_str,
            'n_valid': n_valid,
            'sig_MW': sig != ""
        }

        sig_flag = "(*)" if float(p_val) < 0.05 else "   "
        print(f"  {p_name:<22} {m_name:<14} {r:>7.3f} {p_val:>11.4f}{sig_flag} {mw_p_str:>8} {thr_str:>11} {j_str:>9} {n_valid:>5} {n_high:>7}")

    results.append(row)
    print()

print("=" * 100)
print("(*) = Pearson p < 0.05 (statistically significant correlation)")
print()
print("NOTES:")
print("  AbLang, TCAI: Not yet computed from sequences. Require pipeline integration.")
print("  HPR proxy = vh_identity_imgt (VH only for IgG; unavailable for many VHH entries)")

# Save JSON
with open('data/ada245/statistics/5x5_correlation_matrix.json', 'w') as f:
    json.dump(results, f, indent=2)
print("\nSaved: data/ada245/statistics/5x5_correlation_matrix.json")
