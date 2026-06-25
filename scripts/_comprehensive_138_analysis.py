"""
Comprehensive ADA 138-antibody analysis — generates all figures and stats
from ada_master_136_curated.csv. No AI-generated data; everything from CSV.
"""
import csv, os, json, warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from scipy.stats import spearmanr, mannwhitneyu, kruskal
from collections import Counter

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 200  # Increased DPI for better clarity
plt.rcParams['savefig.bbox'] = 'tight'
plt.rcParams['font.size'] = 12   # Increased base font size
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['xtick.labelsize'] = 11
plt.rcParams['ytick.labelsize'] = 11
plt.rcParams['legend.fontsize'] = 11
plt.rcParams['figure.titlesize'] = 16

CSV = 'data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv'
FIGDIR = 'data/immunogenicity_knowledge_base/reports/figures'
os.makedirs(FIGDIR, exist_ok=True)

rows = list(csv.DictReader(open(CSV, encoding='utf-8')))
print(f"Loaded {len(rows)} rows")

def parse_float(r, col):
    v = r.get(col, '').strip().replace('%','').replace('<','').replace('>','').replace('~','')
    try: return float(v)
    except: return None

def get_group(r):
    g = r.get('genetics_normalized','').strip()
    if g in ('humanised','humanised_engineered','humanized'): return 'HU'
    elif g == 'genetically_human': return 'FH'
    return 'OTHER'

# Build main dataframe-like structure
data = []
for r in rows:
    ada = parse_float(r, 'ada_first_pct')
    if ada is None: continue
    d = {'name': r['antibody_name'], 'ada': ada, 'group': get_group(r)}
    for col in ['vh_germline_identity','vl_germline_identity','half_life_days',
                'pI','GRAVY','instability_index','net_charge_pH7',
                'hydro_patch_max9','charge_patch_max7',
                'immuno_tcia_score','immuno_n_high','immuno_n_medium',
                'immuno_n_tolerated','immuno_n_clusters',
                'surf_frac_exposed_vh','surf_frac_exposed_vl','surf_hydrophilicity',
                'surf_n_patches','surf_mean_sasa_vh','surf_mean_sasa_vl',
                'vh_vl_angle_deg','interface_n_pairs','interface_mean_dist_A',
                'heavy_seq_len','light_seq_len',
                'agg_motifs','deamidation_sites','isomerization_sites',
                'ada_v2_score',
                'vh_pop_rarity_neglog10','vl_pop_rarity_global_neglog10']:
        d[col] = parse_float(r, col)
    d['fc_isotype'] = r.get('fc_isotype','').strip()
    d['route'] = 'SC' if 'SC' in r.get('route_curated','') else ('IV' if 'IV' in r.get('route_curated','') else r.get('route_curated',''))
    d['disease'] = r.get('disease_class_curated','').strip()
    d['assay'] = r.get('assay_generation','').strip()
    d['approval_year'] = parse_float(r, 'approval_year')
    data.append(d)

N = len(data)
print(f"Parsed {N} antibodies with ADA values")

# Numeric feature list for correlation
FEATURES = [
    ('vh_germline_identity', 'VH '),
    ('vl_germline_identity', 'VL '),
    ('immuno_tcia_score', 'TCIA '),
    ('immuno_n_high', 'MHC-II '),
    ('immuno_n_medium', 'MHC-II '),
    ('immuno_n_tolerated', 'MHC-II '),
    ('immuno_n_clusters', 'MHC-II '),
    ('surf_frac_exposed_vh', 'VH '),
    ('surf_frac_exposed_vl', 'VL '),
    ('surf_hydrophilicity', ''),
    ('surf_n_patches', ''),
    ('surf_mean_sasa_vh', 'VH  SASA'),
    ('surf_mean_sasa_vl', 'VL  SASA'),
    ('pI', ' (pI)'),
    ('GRAVY', 'GRAVY '),
    ('instability_index', ''),
    ('net_charge_pH7', 'pH7 '),
    ('hydro_patch_max9', ''),
    ('charge_patch_max7', ''),
    ('half_life_days', ' ()'),
    ('vh_vl_angle_deg', 'VH-VL  (°)'),
    ('interface_n_pairs', ''),
    ('interface_mean_dist_A', ' (Å)'),
    ('heavy_seq_len', ''),
    ('light_seq_len', ''),
    ('agg_motifs', ''),
    ('deamidation_sites', ''),
    ('isomerization_sites', ''),
    ('ada_v2_score', 'ADA V2 '),
    ('vh_pop_rarity_neglog10', 'VH '),
    ('vl_pop_rarity_global_neglog10', 'VL '),
]

C_TEAL = '#0d9488'
C_BLUE = '#2563eb'
C_ORANGE = '#f59e0b'
C_RED = '#dc2626'
C_GREEN = '#16a34a'
C_PURPLE = '#7c3aed'

# ═══════════════════════════════════════════════════════════
# FIGURE 1: ADA Distribution Histogram
# ═══════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
ada_all = [d['ada'] for d in data]
ada_hu = [d['ada'] for d in data if d['group']=='HU']
ada_fh = [d['ada'] for d in data if d['group']=='FH']

for ax, vals, title, color in [
    (axes[0], ada_all, f' (n={len(ada_all)})', C_TEAL),
    (axes[1], ada_hu, f' (n={len(ada_hu)})', C_BLUE),
    (axes[2], ada_fh, f' (n={len(ada_fh)})', C_PURPLE)]:
    ax.hist(vals, bins=np.arange(0, 95, 5), color=color, alpha=0.75, edgecolor='white')
    ax.axvline(np.mean(vals), color=C_RED, ls='--', lw=1.5, label=f'Mean={np.mean(vals):.1f}%')
    ax.axvline(np.median(vals), color=C_ORANGE, ls='-.', lw=1.5, label=f'Median={np.median(vals):.1f}%')
    ax.set_xlabel('ADA  (%)', fontsize=13)
    ax.set_ylabel('', fontsize=13)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.set_xlim(0, 92)

fig.suptitle(' 1: ADA ', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
fig.savefig(f'{FIGDIR}/fig1_ada_distribution.png')
plt.close()
print("Fig 1 done")

# ═══════════════════════════════════════════════════════════
# FIGURE 2: Boxplot by Group, Route, Disease, Isotype
# ═══════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 2a: By group
grp_data = {'HU': ada_hu, 'FH': ada_fh}
bp = axes[0,0].boxplot([ada_hu, ada_fh], labels=[' (HU)', ' (FH)'],
                        patch_artist=True, widths=0.5)
bp['boxes'][0].set_facecolor(C_BLUE + '80')
bp['boxes'][1].set_facecolor(C_PURPLE + '80')
stat_u, p_u = mannwhitneyu(ada_hu, ada_fh, alternative='two-sided')
axes[0,0].set_title(f'(a) \nMann-Whitney p = {p_u:.4f}', fontsize=13, fontweight='bold')
axes[0,0].set_ylabel('ADA (%)', fontsize=12)

# 2b: By route
route_groups = {}
for d in data:
    r = d['route']
    if r in ('IV','SC'):
        route_groups.setdefault(r, []).append(d['ada'])
bp2 = axes[0,1].boxplot([route_groups.get('IV',[]), route_groups.get('SC',[])],
                          labels=[f"IV (n={len(route_groups.get('IV',[]))})", f"SC (n={len(route_groups.get('SC',[]))})"],
                          patch_artist=True, widths=0.5)
bp2['boxes'][0].set_facecolor('#93c5fd80')
bp2['boxes'][1].set_facecolor('#fcd34d80')
if route_groups.get('IV') and route_groups.get('SC'):
    _, p_rt = mannwhitneyu(route_groups['IV'], route_groups['SC'], alternative='two-sided')
    axes[0,1].set_title(f'(b) \nMann-Whitney p = {p_rt:.4f}', fontsize=13, fontweight='bold')
axes[0,1].set_ylabel('ADA (%)', fontsize=12)

# 2c: By disease (top 6)
disease_groups = {}
for d in data:
    disease_groups.setdefault(d['disease'], []).append(d['ada'])
top_diseases = sorted(disease_groups.items(), key=lambda x: -len(x[1]))[:6]
disease_labels = [f"{k}\n(n={len(v)})" for k,v in top_diseases]
disease_vals = [v for _,v in top_diseases]
bp3 = axes[1,0].boxplot(disease_vals, labels=disease_labels, patch_artist=True, widths=0.6)
colors_d = [C_TEAL, C_BLUE, C_GREEN, C_ORANGE, C_RED, C_PURPLE]
for patch, c in zip(bp3['boxes'], colors_d):
    patch.set_facecolor(c + '60')
axes[1,0].set_title('(c) （ 6 ）', fontsize=13, fontweight='bold')
axes[1,0].set_ylabel('ADA (%)', fontsize=12)
axes[1,0].tick_params(axis='x', labelsize=10)

# 2d: By Fc isotype
iso_groups = {}
for d in data:
    iso = d['fc_isotype']
    if iso in ('G1','G2','G4'):
        iso_groups.setdefault(iso, []).append(d['ada'])
iso_labels = [f"IgG{k}\n(n={len(v)})" for k,v in sorted(iso_groups.items())]
iso_vals = [v for _,v in sorted(iso_groups.items())]
bp4 = axes[1,1].boxplot(iso_vals, labels=iso_labels, patch_artist=True, widths=0.5)
iso_colors = ['#60a5fa80', '#34d39980', '#f97316a0']
for patch, c in zip(bp4['boxes'], iso_colors):
    patch.set_facecolor(c)
if len(iso_vals) >= 2:
    _, p_iso = kruskal(*[v for v in iso_vals if len(v)>=3])
    axes[1,1].set_title(f'(d)  Fc \nKruskal-Wallis p = {p_iso:.4f}', fontsize=13, fontweight='bold')
axes[1,1].set_ylabel('ADA (%)', fontsize=12)

fig.suptitle(' 2: ADA ', fontsize=14, fontweight='bold', y=1.01)
plt.tight_layout()
fig.savefig(f'{FIGDIR}/fig2_ada_boxplots.png')
plt.close()
print("Fig 2 done")

# ═══════════════════════════════════════════════════════════
# FIGURE 3: Correlation heatmap — ALL features vs ADA
# ═══════════════════════════════════════════════════════════
corr_results = {}
for group_name, group_filter in [('', None), ('HU', 'HU'), ('FH', 'FH')]:
    corrs = []
    for col, label in FEATURES:
        pairs = []
        for d in data:
            if group_filter and d['group'] != group_filter: continue
            v = d.get(col)
            if v is not None:
                pairs.append((v, d['ada']))
        if len(pairs) >= 15:
            x, y = zip(*pairs)
            rho, p = spearmanr(x, y)
            corrs.append({'feature': col, 'label': label, 'rho': round(rho,3), 'p': round(p,4), 'n': len(pairs)})
        else:
            corrs.append({'feature': col, 'label': label, 'rho': 0, 'p': 1, 'n': len(pairs)})
    corr_results[group_name] = corrs

fig, ax = plt.subplots(figsize=(14, 12))
labels = [c['label'] for c in corr_results['']]
rho_all = [c['rho'] for c in corr_results['']]
rho_hu = [c['rho'] for c in corr_results['HU']]
rho_fh = [c['rho'] for c in corr_results['FH']]

matrix = np.array([rho_all, rho_hu, rho_fh]).T
im = ax.imshow(matrix, cmap='RdBu_r', vmin=-0.4, vmax=0.4, aspect='auto')
ax.set_yticks(range(len(labels)))
ax.set_yticklabels(labels, fontsize=10)
ax.set_xticks([0, 1, 2])
ax.set_xticklabels(['\n(n≈130)', '\n(n≈76)', '\n(n=54)'], fontsize=11, fontweight='bold')
for i in range(len(labels)):
    for j in range(3):
        v = matrix[i, j]
        p_val = [corr_results[''], corr_results['HU'], corr_results['FH']][j][i]['p']
        star = '**' if p_val < 0.01 else ('*' if p_val < 0.05 else '')
        color = 'white' if abs(v) > 0.2 else 'black'
        ax.text(j, i, f'{v:.2f}{star}', ha='center', va='center', fontsize=8.5, color=color, fontweight='bold')

cbar = fig.colorbar(im, ax=ax, shrink=0.7, label='Spearman rho')
ax.set_title(' 3: 31  ADA  Spearman \n(* p<0.05, ** p<0.01)', fontsize=13, fontweight='bold')
plt.tight_layout()
fig.savefig(f'{FIGDIR}/fig3_correlation_heatmap.png')
plt.close()
print("Fig 3 done")

# ═══════════════════════════════════════════════════════════
# FIGURE 4: Top scatter plots for key features
# ═══════════════════════════════════════════════════════════
scatter_features = [
    ('vl_germline_identity', 'VL ', 'FH'),
    ('vh_germline_identity', 'VH ', 'FH'),
    ('immuno_n_high', 'MHC-II ', 'FH'),
    ('surf_frac_exposed_vl', 'VL ', 'HU'),
    ('surf_frac_exposed_vh', 'VH ', None),
    ('ada_v2_score', 'ADA V2 ', None),
]

fig, axes = plt.subplots(2, 3, figsize=(18, 11))
for idx, (col, label, grp) in enumerate(scatter_features):
    ax = axes[idx//3, idx%3]
    for d in data:
        if grp and d['group'] != grp: continue
        v = d.get(col)
        if v is None: continue
        color = C_BLUE if d['group']=='HU' else C_PURPLE
        ax.scatter(v, d['ada'], c=color, alpha=0.5, s=30, edgecolors='white', linewidth=0.3)
    
    pairs = [(d[col], d['ada']) for d in data if d.get(col) is not None and (not grp or d['group']==grp)]
    if len(pairs) >= 10:
        x, y = zip(*pairs)
        rho, p = spearmanr(x, y)
        z = np.polyfit(x, y, 1)
        xline = np.linspace(min(x), max(x), 100)
        ax.plot(xline, np.polyval(z, xline), color=C_RED, lw=1.5, ls='--', alpha=0.7)
        grp_label = f" ({grp})" if grp else ""
        ax.set_title(f'{label}{grp_label}\nrho={rho:.3f}, p={p:.4f}, n={len(pairs)}', fontsize=10, fontweight='bold')
    ax.set_xlabel(label, fontsize=9)
    ax.set_ylabel('ADA (%)', fontsize=9)

fig.suptitle(' 4:  ADA （）', fontsize=14, fontweight='bold', y=1.01)
plt.tight_layout()
fig.savefig(f'{FIGDIR}/fig4_scatter_key_features.png')
plt.close()
print("Fig 4 done")

# ═══════════════════════════════════════════════════════════
# FIGURE 5: Feature distribution violin plots
# ═══════════════════════════════════════════════════════════
violin_features = [
    ('immuno_n_high', 'MHC-II '),
    ('immuno_n_clusters', ''),
    ('vh_germline_identity', 'VH '),
    ('vl_germline_identity', 'VL '),
    ('pI', ''),
    ('hydro_patch_max9', ''),
    ('surf_hydrophilicity', ''),
    ('instability_index', ''),
]

fig, axes = plt.subplots(2, 4, figsize=(20, 10))
for idx, (col, label) in enumerate(violin_features):
    ax = axes[idx//4, idx%4]
    hu_vals = [d[col] for d in data if d['group']=='HU' and d.get(col) is not None]
    fh_vals = [d[col] for d in data if d['group']=='FH' and d.get(col) is not None]
    if hu_vals and fh_vals:
        parts = ax.violinplot([hu_vals, fh_vals], positions=[1,2], showmeans=True, showmedians=True)
        for i, pc in enumerate(parts['bodies']):
            pc.set_facecolor([C_BLUE, C_PURPLE][i])
            pc.set_alpha(0.5)
        ax.set_xticks([1,2])
        ax.set_xticklabels([f'HU\n(n={len(hu_vals)})', f'FH\n(n={len(fh_vals)})'], fontsize=9)
        _, p_mw = mannwhitneyu(hu_vals, fh_vals, alternative='two-sided')
        ax.set_title(f'{label}\np={p_mw:.4f}', fontsize=10, fontweight='bold')

fig.suptitle(' 5:  vs （）', fontsize=14, fontweight='bold', y=1.01)
plt.tight_layout()
fig.savefig(f'{FIGDIR}/fig5_violin_hu_vs_fh.png')
plt.close()
print("Fig 5 done")

# ═══════════════════════════════════════════════════════════
# FIGURE 6: ADA vs Approval Year (temporal trend)
# ═══════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(12, 6))
for d in data:
    yr = d.get('approval_year')
    if yr is None or yr < 1990: continue
    color = C_BLUE if d['group']=='HU' else C_PURPLE
    marker = 'o' if d['group']=='HU' else 's'
    ax.scatter(yr, d['ada'], c=color, alpha=0.5, s=40, marker=marker, edgecolors='white', linewidth=0.3)

# Add trend
yr_ada = [(d['approval_year'], d['ada']) for d in data if d.get('approval_year') and d['approval_year'] >= 1990]
if yr_ada:
    x, y = zip(*yr_ada)
    rho, p = spearmanr(x, y)
    z = np.polyfit(x, y, 1)
    xline = np.linspace(min(x), max(x), 100)
    ax.plot(xline, np.polyval(z, xline), color=C_RED, lw=2, ls='--', alpha=0.7)
    ax.text(0.02, 0.95, f'Spearman rho={rho:.3f}, p={p:.4f}, n={len(yr_ada)}',
            transform=ax.transAxes, fontsize=10, va='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

ax.set_xlabel('/', fontsize=12)
ax.set_ylabel('ADA  (%)', fontsize=12)
ax.set_title(' 6: ADA （=, =）', fontsize=13, fontweight='bold')
from matplotlib.lines import Line2D
legend_elements = [Line2D([0],[0], marker='o', color='w', markerfacecolor=C_BLUE, markersize=8, label='HU'),
                   Line2D([0],[0], marker='s', color='w', markerfacecolor=C_PURPLE, markersize=8, label='FH')]
ax.legend(handles=legend_elements, fontsize=10)
plt.tight_layout()
fig.savefig(f'{FIGDIR}/fig6_ada_vs_year.png')
plt.close()
print("Fig 6 done")

# ═══════════════════════════════════════════════════════════
# FIGURE 7: Feature-feature correlation matrix (top features)
# ═══════════════════════════════════════════════════════════
top_cols = ['ada', 'vh_germline_identity', 'vl_germline_identity',
            'immuno_n_high', 'immuno_n_clusters', 'immuno_tcia_score',
            'surf_frac_exposed_vh', 'surf_frac_exposed_vl', 'surf_hydrophilicity',
            'pI', 'GRAVY', 'hydro_patch_max9', 'half_life_days',
            'ada_v2_score', 'vh_pop_rarity_neglog10']
top_labels = ['ADA%', 'VH_id', 'VL_id', 'n_high', 'n_cluster', 'TCIA',
              'exp_VH', 'exp_VL', 'hydrophil', 'pI', 'GRAVY', 'hydro_max',
              'HL_days', 'V2_score', 'VH_rare']

n_top = len(top_cols)
corr_matrix = np.full((n_top, n_top), np.nan)
for i in range(n_top):
    for j in range(n_top):
        pairs = [(d.get(top_cols[i]), d.get(top_cols[j])) for d in data
                 if d.get(top_cols[i]) is not None and d.get(top_cols[j]) is not None]
        if len(pairs) >= 20:
            x, y = zip(*pairs)
            rho, _ = spearmanr(x, y)
            corr_matrix[i,j] = rho

fig, ax = plt.subplots(figsize=(14, 12))
mask = np.isnan(corr_matrix)
corr_display = np.where(mask, 0, corr_matrix)
im = ax.imshow(corr_display, cmap='RdBu_r', vmin=-1, vmax=1, aspect='equal')
ax.set_xticks(range(n_top))
ax.set_xticklabels(top_labels, rotation=45, ha='right', fontsize=9)
ax.set_yticks(range(n_top))
ax.set_yticklabels(top_labels, fontsize=9)
for i in range(n_top):
    for j in range(n_top):
        if not mask[i,j]:
            v = corr_matrix[i,j]
            color = 'white' if abs(v) > 0.5 else 'black'
            ax.text(j, i, f'{v:.2f}', ha='center', va='center', fontsize=7.5, color=color)

fig.colorbar(im, ax=ax, shrink=0.7, label='Spearman rho')
ax.set_title(' 7: 15  Spearman ', fontsize=13, fontweight='bold')
plt.tight_layout()
fig.savefig(f'{FIGDIR}/fig7_feature_correlation_matrix.png')
plt.close()
print("Fig 7 done")

# ═══════════════════════════════════════════════════════════
# FIGURE 8: CMC features vs ADA
# ═══════════════════════════════════════════════════════════
cmc_features = [
    ('agg_motifs', ''),
    ('deamidation_sites', ''),
    ('isomerization_sites', ''),
    ('charge_patch_max7', ''),
]
fig, axes = plt.subplots(1, 4, figsize=(20, 5))
for idx, (col, label) in enumerate(cmc_features):
    ax = axes[idx]
    pairs = [(d[col], d['ada']) for d in data if d.get(col) is not None]
    if pairs:
        x, y = zip(*pairs)
        ax.scatter(x, y, c=C_TEAL, alpha=0.5, s=30, edgecolors='white', linewidth=0.3)
        rho, p = spearmanr(x, y)
        ax.set_title(f'{label}\nrho={rho:.3f}, p={p:.4f}', fontsize=10, fontweight='bold')
        ax.set_xlabel(label, fontsize=9)
        ax.set_ylabel('ADA (%)', fontsize=9)

fig.suptitle(' 8: CMC  ADA ', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
fig.savefig(f'{FIGDIR}/fig8_cmc_vs_ada.png')
plt.close()
print("Fig 8 done")

# ═══════════════════════════════════════════════════════════
# Save full correlation table to JSON
# ═══════════════════════════════════════════════════════════
json.dump(corr_results, open(f'{FIGDIR}/../_138_full_correlations.json', 'w'),
          indent=2, ensure_ascii=False)

# ═══════════════════════════════════════════════════════════
# Print summary stats for report
# ═══════════════════════════════════════════════════════════
print("\n=== SUMMARY FOR REPORT ===")
print(f"Total: {N}, HU: {len(ada_hu)}, FH: {len(ada_fh)}")
print(f"Features analyzed: {len(FEATURES)}")

# Significant correlations
print("\n--- Significant (p<0.05) correlations ---")
for gn, corrs in corr_results.items():
    sig = [c for c in corrs if c['p'] < 0.05 and c['n'] >= 15]
    if sig:
        print(f"\n  {gn}:")
        for c in sorted(sig, key=lambda x: x['p']):
            print(f"    {c['label']}: rho={c['rho']:.3f}, p={c['p']:.4f}, n={c['n']}")

print("\n✅ All 8 figures generated.")
