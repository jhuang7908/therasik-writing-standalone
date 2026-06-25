import pandas as pd
from scipy.stats import spearmanr, mannwhitneyu, kruskal
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage, fcluster
import numpy as np

# 
df = pd.read_csv('Supplementary_Materials/Analysis_Reports/TheraSAbDab_19VHH_New_Classification_Table.csv')

print('=' * 80)
print('FR2 Phylogenetic Analysis - ')
print('=' * 80)
print

# 
fr2_sequences = df['fr2_sequence'].values
antibodies = df['antibody_id'].values
cdr3_lengths = df['h3_length'].values

# 1. FR2 Hierarchical Clustering
print('1. FR2')
print('-' * 80)
print

# Hamming
def hamming_distance(seq1, seq2):
    if len(seq1) != len(seq2):
        return np.nan
    return sum(c1 != c2 for c1, c2 in zip(seq1, seq2)) / len(seq1)

n = len(fr2_sequences)
dist_matrix = np.zeros((n, n))

for i in range(n):
    for j in range(i+1, n):
        dist = hamming_distance(fr2_sequences[i], fr2_sequences[j])
        dist_matrix[i, j] = dist
        dist_matrix[j, i] = dist

# UPGMA clustering 
condensed_dist = squareform(dist_matrix)
Z = linkage(condensed_dist, method='average')

# k=2
clusters_2 = fcluster(Z, 2, criterion='maxclust')

print('FR2 (k=2):')
print

cluster_info = []
for cluster_id in [1, 2]:
    mask = clusters_2 == cluster_id
    cluster_abs = antibodies[mask]
    cluster_cdr3 = cdr3_lengths[mask]
    
    print(f'Cluster {cluster_id} (N={np.sum(mask)}):')
    print(f'  CDR3: {np.mean(cluster_cdr3):.1f} +/- {np.std(cluster_cdr3):.1f} aa')
    print(f'  CDR3: {np.min(cluster_cdr3)} - {np.max(cluster_cdr3)} aa')
    print(f'  : {", ".join(cluster_abs[:5])}{"..." if len(cluster_abs) > 5 else ""}')
    print
    
    cluster_info.append({
        'cluster': cluster_id,
        'n': np.sum(mask),
        'cdr3_mean': np.mean(cluster_cdr3),
        'cdr3_std': np.std(cluster_cdr3)
    })

# clusterCDR3
cluster1_cdr3 = cdr3_lengths[clusters_2 == 1]
cluster2_cdr3 = cdr3_lengths[clusters_2 == 2]

# Kruskal-Wallis
h_stat, p_kruskal = kruskal(cluster1_cdr3, cluster2_cdr3)
print(f'Kruskal-Wallis:')
print(f'  H = {h_stat:.2f}, P = {p_kruskal:.4f}')

if p_kruskal < 0.05:
    print('  ***  (P < 0.05) - ')
else:
    print('   (P >= 0.05) - ')
print

# Mann-Whitney U
u_stat, p_mw = mannwhitneyu(cluster1_cdr3, cluster2_cdr3)
print(f'Mann-Whitney U:')
print(f'  U = {u_stat:.1f}, P = {p_mw:.4f}')
print

# 2. Spearman
print('=' * 80)
print('2. Spearman')
print('-' * 80)
print

# A: FR2% vs CDR3
rho_pct, p_pct = spearmanr(df['h3_length'], df['fr2_human_pct'])
print(f'A. FR2% vs CDR3:')
print(f'   Spearman rho = {rho_pct:.3f}, P = {p_pct:.4f}')

# B: FR2alpaca vs CDR3
rho_alpaca, p_alpaca = spearmanr(df['h3_length'], df['fr2_vicugna_pct'])
print(f'B. FR2alpaca vs CDR3:')
print(f'   Spearman rho = {rho_alpaca:.3f}, P = {p_alpaca:.4f}')

# C: FR2 delta (human-alpaca) vs CDR3
rho_delta, p_delta = spearmanr(df['h3_length'], df['fr2_delta_human_minus_vicugna'])
print(f'C. FR2 delta vs CDR3:')
print(f'   Spearman rho = {rho_delta:.3f}, P = {p_delta:.4f}')

print

# 3. vs
print('=' * 80)
print('3.  vs ')
print('=' * 80)
print

print(':')
print('  \"Kruskal-Wallis test on the two natural clusters showed')
print('   highly significant differences in CDR3 length distribution')
print('   (P = 0.00175, H = 9.79)\"')
print

print(':')
print(f'  Kruskal-Wallis: P = {p_kruskal:.5f}, H = {h_stat:.2f}')
print

if abs(p_kruskal - 0.00175) < 0.001:
    print('  ✓ ！P0.00175')
elif p_kruskal < 0.05:
    print(f'  ~ ：P < 0.05，0.00175')
else:
    print(f'  ✗ ：P = {p_kruskal:.4f} ')
print

print('-' * 80)
print

print(':')
print('  \"Spearman correlation between CDR3 length and phylogenetic')
print('   distance from Human IGHV3-23 was strongly negative')
print('   (rho = -0.604, P = 0.0062)\"')
print

print(':')
print(f'  FR2%:     rho = {rho_pct:.3f}, P = {p_pct:.4f}')
print(f'  FR2 vs alpaca:  rho = {rho_alpaca:.3f}, P = {p_alpaca:.4f}')
print(f'  FR2 delta:      rho = {rho_delta:.3f}, P = {p_delta:.4f}')
print

# 
matched = False
if abs(rho_pct + 0.604) < 0.1 and abs(p_pct - 0.0062) < 0.01:
    print('  ✓ FR2%')
    matched = True
elif abs(rho_delta + 0.604) < 0.1 and abs(p_delta - 0.0062) < 0.01:
    print('  ✓ FR2 delta')
    matched = True

if not matched:
    print('  ✗ ')
print

# 4. ：CDR3 vs CDR3
print('=' * 80)
print('4. CDR3FR2')
print('=' * 80)
print

short_cdr3 = df[df['h3_length'] <= 11]
long_cdr3 = df[df['h3_length'] > 11]

print(f'CDR3 (<=11aa, N={len(short_cdr3)}):')
print(f'  FR2%: {short_cdr3["fr2_human_pct"].mean:.2f} +/- {short_cdr3["fr2_human_pct"].std:.2f}%')

print(f'CDR3 (>11aa, N={len(long_cdr3)}):')
print(f'  FR2%: {long_cdr3["fr2_human_pct"].mean:.2f} +/- {long_cdr3["fr2_human_pct"].std:.2f}%')

u, p = mannwhitneyu(short_cdr3['fr2_human_pct'], long_cdr3['fr2_human_pct'])
print(f'Mann-Whitney U: P = {p:.4f}')
print

# 5. 
print('=' * 80)
print('5. ')
print('=' * 80)
print

print('FR2CDR3:')
print

if p_kruskal < 0.05:
    print(f'✓ Clustering:  (P = {p_kruskal:.4f})')
    fr2_clustering_sig = True
else:
    print(f'✗ Clustering:  (P = {p_kruskal:.4f})')
    fr2_clustering_sig = False

if p_pct < 0.05 or p_delta < 0.05:
    print(f'✓ :  (P < 0.05)')
    fr2_corr_sig = True
else:
    print(f'✗ :  (P > 0.05)')
    fr2_corr_sig = False

print
print('-' * 80)

if fr2_clustering_sig and fr2_corr_sig:
    print(': FR2CDR3')
elif fr2_clustering_sig and not fr2_corr_sig:
    print(': FR2clusteringCDR3，')
    print('      （，clarify）')
elif not fr2_clustering_sig and not fr2_corr_sig:
    print(': FR2CDR3')

print
print('=' * 80)
