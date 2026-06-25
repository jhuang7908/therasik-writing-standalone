import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import patheffects
import matplotlib.patches as mpatches
import os

# 
os.makedirs('Supplementary_Materials/Figures', exist_ok=True)

# 
df = pd.read_csv('Supplementary_Materials/Analysis_Reports/TheraSAbDab_19VHH_New_Classification_Table.csv')

# CDR2
df['cdr2_type'] = df['h2_class'].apply(lambda x: 'short_H2-9-1' if '9-1' in str(x) else 'long_H2-10-1' if '10-1' in str(x) else 'unknown')

# 
aa_colors = {
    'S': '#33A02C', 'T': '#33A02C', 'N': '#33A02C', 'Q': '#33A02C',
    'Y': '#FF7F00', 'F': '#FF7F00', 'W': '#FF7F00',
    'K': '#E31A1C', 'R': '#E31A1C', 'H': '#E31A1C',
    'D': '#6A3D9A', 'E': '#6A3D9A',
    'A': '#1F78B4', 'V': '#1F78B4', 'L': '#1F78B4', 'I': '#1F78B4', 
    'M': '#1F78B4', 'P': '#1F78B4',
    'G': '#B2DF8A', 'C': '#FDBF6F'
}

def create_logo_plot(sequences, title, output_file, max_positions=15):
    n_seqs = len(sequences)
    max_len = min(max(len(seq) for seq in sequences), max_positions)
    
    fig, ax = plt.subplots(figsize=(max_len * 0.8, 4))
    
    for pos in range(max_len):
        aa_at_pos = [seq[pos] if pos < len(seq) else '-' for seq in sequences]
        aa_counts = pd.Series(aa_at_pos).value_counts.sort_values(ascending=True)
        
        y_offset = 0
        for aa, count in aa_counts.items:
            if aa == '-':
                continue
            
            freq = count / n_seqs
            height = freq
            color = aa_colors.get(aa, '#999999')
            
            text = ax.text(pos + 0.5, y_offset + height/2, aa,
                          fontsize=int(height * 40),
                          ha='center', va='center',
                          fontweight='bold',
                          color=color,
                          family='monospace')
            
            text.set_path_effects([
                patheffects.Stroke(linewidth=1, foreground='white'),
                patheffects.Normal
            ])
            
            y_offset += height
    
    ax.set_xlim(0, max_len)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel('Position', fontsize=12, fontweight='bold')
    ax.set_ylabel('Frequency', fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    
    ax.set_xticks(range(1, max_len + 1))
    ax.set_xticklabels(range(1, max_len + 1))
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    legend_elements = [
        mpatches.Patch(color='#33A02C', label='Polar (S,T,N,Q)'),
        mpatches.Patch(color='#FF7F00', label='Aromatic (Y,F,W)'),
        mpatches.Patch(color='#E31A1C', label='Positive (K,R,H)'),
        mpatches.Patch(color='#6A3D9A', label='Negative (D,E)'),
        mpatches.Patch(color='#1F78B4', label='Hydrophobic (A,V,L,I,M,P)'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=8)
    
    plt.tight_layout
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f'✓ : {output_file}')
    plt.close

print('=' * 80)
print('FR3Logo（CDR2）')
print('=' * 80)
print

# logo
for cdr2_type in ['short_H2-9-1', 'long_H2-10-1']:
    subset = df[df['cdr2_type'] == cdr2_type]
    if len(subset) == 0:
        continue
    
    sequences = subset['fr3_sequence'].tolist
    n = len(sequences)
    
    title = f'FR3 N-terminus - {cdr2_type.replace("_", " ")} (N={n})'
    output_file = f'Supplementary_Materials/Figures/FR3_Logo_{cdr2_type}.png'
    
    create_logo_plot(sequences, title, output_file, max_positions=15)

# 
print
print('FR3...')

fig, axes = plt.subplots(2, 1, figsize=(12, 8))

for idx, cdr2_type in enumerate(['short_H2-9-1', 'long_H2-10-1']):
    subset = df[df['cdr2_type'] == cdr2_type]
    sequences = subset['fr3_sequence'].tolist
    n_seqs = len(sequences)
    max_len = 15
    
    ax = axes[idx]
    
    for pos in range(max_len):
        aa_at_pos = [seq[pos] if pos < len(seq) else '-' for seq in sequences]
        aa_counts = pd.Series(aa_at_pos).value_counts.sort_values(ascending=True)
        
        y_offset = 0
        for aa, count in aa_counts.items:
            if aa == '-':
                continue
            
            freq = count / n_seqs
            height = freq
            color = aa_colors.get(aa, '#999999')
            
            text = ax.text(pos + 0.5, y_offset + height/2, aa,
                          fontsize=int(height * 35),
                          ha='center', va='center',
                          fontweight='bold',
                          color=color,
                          family='monospace')
            
            text.set_path_effects([
                patheffects.Stroke(linewidth=1, foreground='white'),
                patheffects.Normal
            ])
            
            y_offset += height
    
    ax.set_xlim(0, max_len)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel('FR3 Position', fontsize=11, fontweight='bold')
    ax.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    
    cdr2_label = 'Short CDR2 (H2-9-1)' if 'short' in cdr2_type else 'Long CDR2 (H2-10-1)'
    ax.set_title(f'{cdr2_label}, N={n_seqs}', fontsize=12, fontweight='bold')
    
    ax.set_xticks(range(1, max_len + 1))
    ax.set_xticklabels(range(1, max_len + 1))
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # 1
    if pos == 0 and idx == 0:
        ax.axvline(x=1, color='red', linestyle='--', alpha=0.5, linewidth=2)
        ax.text(1, 1.05, '75% diff', ha='center', fontsize=10, color='red', fontweight='bold')

plt.tight_layout
output_comparison = 'Supplementary_Materials/Figures/FR3_Logo_CDR2_Comparison.png'
plt.savefig(output_comparison, dpi=300, bbox_inches='tight')
print(f'✓ : {output_comparison}')
plt.close

# FR4 logo（CDR3，）
print
print('FR4 Logo（CDR3）...')

df['cdr3_group'] = df['h3_length'].apply(lambda x: 'short_CDR3_le11' if x <= 11 else 'long_CDR3_gt11')

fig, axes = plt.subplots(2, 1, figsize=(10, 8))

for idx, cdr3_group in enumerate(['short_CDR3_le11', 'long_CDR3_gt11']):
    subset = df[df['cdr3_group'] == cdr3_group]
    sequences = subset['fr4_sequence'].tolist
    n_seqs = len(sequences)
    max_len = 11  # FR411
    
    ax = axes[idx]
    
    for pos in range(max_len):
        aa_at_pos = [seq[pos] if pos < len(seq) else '-' for seq in sequences]
        aa_counts = pd.Series(aa_at_pos).value_counts.sort_values(ascending=True)
        
        y_offset = 0
        for aa, count in aa_counts.items:
            if aa == '-':
                continue
            
            freq = count / n_seqs
            height = freq
            color = aa_colors.get(aa, '#999999')
            
            text = ax.text(pos + 0.5, y_offset + height/2, aa,
                          fontsize=int(height * 40),
                          ha='center', va='center',
                          fontweight='bold',
                          color=color,
                          family='monospace')
            
            text.set_path_effects([
                patheffects.Stroke(linewidth=1, foreground='white'),
                patheffects.Normal
            ])
            
            y_offset += height
    
    ax.set_xlim(0, max_len)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel('FR4 Position (IMGT 118-128)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    
    cdr3_label = 'Short CDR3 (≤11aa)' if 'short' in cdr3_group else 'Long CDR3 (>11aa)'
    ax.set_title(f'{cdr3_label}, N={n_seqs}', fontsize=12, fontweight='bold')
    
    # IMGT
    imgt_positions = list(range(118, 129))
    ax.set_xticks(range(1, max_len + 1))
    ax.set_xticklabels([f'{i}\n({imgt})' for i, imgt in enumerate(range(1, max_len + 1), 1)])
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # 1（IMGT 118）
    if idx == 0:
        ax.axvline(x=1, color='red', linestyle='--', alpha=0.5, linewidth=2)
        ax.text(1, 1.05, '60% diff\n(IMGT 118)', ha='center', fontsize=9, color='red', fontweight='bold')

plt.tight_layout
output_fr4 = 'Supplementary_Materials/Figures/FR4_Logo_CDR3_Comparison.png'
plt.savefig(output_fr4, dpi=300, bbox_inches='tight')
print(f'✓ FR4: {output_fr4}')
plt.close

print
print('=' * 80)
print('Logo！')
print('=' * 80)
print
print('：')
print('  1. FR3_Logo_short_H2-9-1.png')
print('  2. FR3_Logo_long_H2-10-1.png')
print('  3. FR3_Logo_CDR2_Comparison.png ')
print('  4. FR4_Logo_CDR3_Comparison.png ')
