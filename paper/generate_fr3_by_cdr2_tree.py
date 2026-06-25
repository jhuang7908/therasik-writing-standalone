"""
CDR2FR3
FR3CDR2
"""

import pandas as pd
import numpy as np
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage, to_tree
from Bio import Phylo
from io import StringIO

def hamming_distance(seq1, seq2):
    """Hamming"""
    if len(seq1) != len(seq2):
        # ，
        max_len = max(len(seq1), len(seq2))
        seq1 = seq1.ljust(max_len, '-')
        seq2 = seq2.ljust(max_len, '-')
    return sum(c1 != c2 for c1, c2 in zip(seq1, seq2)) / len(seq1)

def sequences_to_newick(df, seq_column, id_column, group_column):
    """
    Newick
    
    """
    sequences = df[seq_column].values
    ids = df[id_column].values
    groups = df[group_column].values
    
    # 
    n = len(sequences)
    dist_matrix = np.zeros((n, n))
    
    for i in range(n):
        for j in range(i+1, n):
            dist = hamming_distance(sequences[i], sequences[j])
            dist_matrix[i, j] = dist
            dist_matrix[j, i] = dist
    
    # （UPGMA）
    condensed_dist = squareform(dist_matrix)
    Z = linkage(condensed_dist, method='average')
    
    # Newick
    def linkage_to_newick(Z, labels, groups):
        """linkageNewick"""
        n = len(labels)
        nodes = {}
        
        # 
        for i in range(n):
            nodes[i] = f"{labels[i]}_{groups[i]}"
        
        # 
        for i, row in enumerate(Z):
            left_idx = int(row[0])
            right_idx = int(row[1])
            dist = row[2]
            
            left_node = nodes[left_idx]
            right_node = nodes[right_idx]
            
            # 
            nodes[n + i] = f"({left_node}:{dist:.6f},{right_node}:{dist:.6f})"
        
        # 
        return nodes[len(nodes) - 1] + ";"
    
    newick = linkage_to_newick(Z, ids, groups)
    return newick

# 
df = pd.read_csv('Supplementary_Materials/Analysis_Reports/TheraSAbDab_19VHH_New_Classification_Table.csv')

# CDR2
df['cdr2_group'] = df['h2_class'].apply(
    lambda x: 'H2-9-1' if '9-1' in str(x) else 'H2-10-1' if '10-1' in str(x) else 'unknown'
)

# CDR3
df['cdr3_group'] = df['h3_length'].apply(lambda x: 'short' if x <= 11 else 'long')

print('=' * 80)
print('CDR2FR3')
print('=' * 80)
print

# 1. FR3CDR2
print('1. FR3（CDR2）')
print('-' * 80)

newick_fr3_by_cdr2 = sequences_to_newick(
    df, 
    seq_column='fr3_sequence',
    id_column='antibody_id',
    group_column='cdr2_group'
)

output_file_cdr2 = 'Supplementary_Materials/Analysis_Reports/FR3_by_CDR2_group.newick'
with open(output_file_cdr2, 'w') as f:
    f.write(newick_fr3_by_cdr2)

print(f': {output_file_cdr2}')
print

# 2. FR3CDR3
print('2. FR3（CDR3，）')
print('-' * 80)

newick_fr3_by_cdr3 = sequences_to_newick(
    df,
    seq_column='fr3_sequence',
    id_column='antibody_id',
    group_column='cdr3_group'
)

output_file_cdr3 = 'Supplementary_Materials/Analysis_Reports/FR3_by_CDR3_group.newick'
with open(output_file_cdr3, 'w') as f:
    f.write(newick_fr3_by_cdr3)

print(f': {output_file_cdr3}')
print

# 3. 
print('=' * 80)
print('3. FR3 N（10）CDR2')
print('=' * 80)
print

for pos in range(10):
    print(f' {pos+1}:')
    
    for cdr2_group in ['H2-9-1', 'H2-10-1']:
        subset = df[df['cdr2_group'] == cdr2_group]
        if len(subset) > 0:
            aa_counts = subset['fr3_sequence'].str[pos].value_counts
            most_common = aa_counts.index[0] if len(aa_counts) > 0 else 'N/A'
            most_freq = aa_counts.iloc[0] / len(subset) * 100 if len(aa_counts) > 0 else 0
            
            print(f'  {cdr2_group}: {most_common} ({most_freq:.0f}%)', end='')
            
            if len(aa_counts) > 1:
                others = ', '.join([f'{aa}:{c}' for aa, c in list(aa_counts.items)[1:3]])
                print(f' [{others}]')
            else:
                print(' [conserved]')
    
    print

# 4. 
print('=' * 80)
print('4. FR3')
print('=' * 80)
print

# CDR2
cdr2_h2_9_1 = df[df['cdr2_group'] == 'H2-9-1']
cdr2_h2_10_1 = df[df['cdr2_group'] == 'H2-10-1']

print('CDR2:')
print(f'  H2-9-1: N={len(cdr2_h2_9_1)}')
print(f'    FR31: {cdr2_h2_9_1["fr3_sequence"].str[0].value_counts.index[0]}')
print(f'  H2-10-1: N={len(cdr2_h2_10_1)}')
print(f'    FR31: {cdr2_h2_10_1["fr3_sequence"].str[0].value_counts.index[0]}')
print

# CDR3
cdr3_short = df[df['cdr3_group'] == 'short']
cdr3_long = df[df['cdr3_group'] == 'long']

print('CDR3:')
print(f'  CDR3: N={len(cdr3_short)}')
print(f'    FR31: {cdr3_short["fr3_sequence"].str[0].value_counts.index[0] if len(cdr3_short) > 0 else "N/A"}')
print(f'  CDR3: N={len(cdr3_long)}')
print(f'    FR31: {cdr3_long["fr3_sequence"].str[0].value_counts.index[0]}')
print

print('=' * 80)
print(':')
print('  FR3CDR2（N）')
print('  FR3CDR3')
print('=' * 80)

print
print('✓ ')
