import pandas as pd
from scipy.stats import spearmanr, mannwhitneyu, chi2_contingency
import numpy as np

# 
df = pd.read_csv('Supplementary_Materials/Analysis_Reports/TheraSAbDab_19VHH_New_Classification_Table.csv')

# CDR2
df['cdr2_type'] = df['h2_class'].apply(lambda x: 'short' if '9-1' in str(x) else 'long' if '10-1' in str(x) else 'unknown')
df['cdr2_length'] = df['h2_class'].apply(lambda x: 9 if '9-1' in str(x) else 10 if '10-1' in str(x) else np.nan)
df['fr3_n_aa'] = df['fr3_sequence'].str[0]
df['cdr3_group'] = df['h3_length'].apply(lambda x: 'short' if x <= 11 else 'long')

print('=' * 80)
print('FR3 NCDR2 - ')
print('=' * 80)
print

# 1. CDR2 Canonical Class
print('1. CDR2 Canonical Class')
print('-' * 80)
print

print('H2-9-1 (CDR2):')
print('  - : ~9')
print('  - : loop')
print('  - : Beta-turn，')
print

print('H2-10-1 (CDR2):')
print('  - : ~10')
print('  - : loop，')
print('  - : ，')
print

# 2. FR3 N
print('=' * 80)
print('2. FR3 N（CDR2）')
print('-' * 80)
print

for cdr2_type in ['short', 'long']:
    subset = df[df['cdr2_type'] == cdr2_type]
    if len(subset) > 0:
        h2_class = subset['h2_class'].iloc[0]
        print(f'{cdr2_type.upper} CDR2 ({h2_class}, N={len(subset)}):')
        aa_counts = subset['fr3_n_aa'].value_counts.sort_index
        for aa, count in aa_counts.items:
            freq = count / len(subset) * 100
            print(f'  {aa}: {count:2d}/{len(subset)} ({freq:5.1f}%)')
        print

# 3. 
print('=' * 80)
print('3. ')
print('-' * 80)
print

def aa_property(aa):
    properties = {
        'Y': ('aromatic', 'polar', 'large', 'pi-stacking'),
        'T': ('polar', 'small', 'flexible', 'H-bond'),
        'S': ('polar', 'small', 'flexible', 'H-bond'),
        'N': ('polar', 'small', 'H-bond', 'amide'),
        'V': ('hydrophobic', 'small', 'branched'),
        'L': ('hydrophobic', 'medium', 'aliphatic'),
        'K': ('positive', 'long', 'charged', 'flexible'),
    }
    return properties.get(aa, ('unknown',))

print(':')
print

for aa in ['Y', 'T', 'S', 'N', 'V', 'L', 'K']:
    props = aa_property(aa)
    # 
    short_count = len(df[(df['cdr2_type'] == 'short') & (df['fr3_n_aa'] == aa)])
    long_count = len(df[(df['cdr2_type'] == 'long') & (df['fr3_n_aa'] == aa)])
    total_short = len(df[df['cdr2_type'] == 'short'])
    total_long = len(df[df['cdr2_type'] == 'long'])
    
    if short_count > 0 or long_count > 0:
        print(f'{aa} ({", ".join(props)}):')
        print(f'  CDR2: {short_count}/{total_short} ({short_count/total_short*100:5.1f}%)')
        print(f'  CDR2: {long_count}/{total_long} ({long_count/total_long*100:5.1f}%)')
        print

# 4. 
print('=' * 80)
print('4. CDR2 × CDR3 ')
print('-' * 80)
print

interaction_table = pd.crosstab([df['cdr2_type'], df['cdr3_group']], df['fr3_n_aa'])
print(':')
print(interaction_table)
print

print(':')
print

for cdr2 in ['short', 'long']:
    for cdr3 in ['short', 'long']:
        subset = df[(df['cdr2_type'] == cdr2) & (df['cdr3_group'] == cdr3)]
        if len(subset) > 0:
            print(f'CDR2={cdr2:5s}, CDR3={cdr3:5s} (N={len(subset)}):')
            
            aa_freq = subset['fr3_n_aa'].value_counts
            for aa, count in aa_freq.items:
                print(f'  {aa}: {count}/{len(subset)} ({count/len(subset)*100:.1f}%)')
            
            # 
            antibodies = ', '.join(subset['antibody_id'].tolist)
            print(f'  : {antibodies}')
            print

# 5. 
print('=' * 80)
print('5. Tyr vs Thr')
print('-' * 80)
print

print('Tyr (Tyrosine):')
print('  - :  (MW 181)')
print('  - :  ( + OH)')
print('  - π-π stacking: ')
print('  - :  +  (OH)')
print('  - : ')
print('  - :  ')
print('  - : ，')
print

print('Thr (Threonine):')
print('  - :  (MW 119)')
print('  - : ')
print('  - π-π stacking: ')
print('  - :  +  (OH)')
print('  - : ')
print('  - :  ')
print('  - : ，')
print

# 6. 
print('=' * 80)
print('6. ')
print('-' * 80)
print

# Tyr
tyr_cdr2_contingency = pd.crosstab(df['fr3_n_aa'] == 'Y', df['cdr2_type'])
if tyr_cdr2_contingency.shape == (2, 2):
    chi2, p_val, dof, expected = chi2_contingency(tyr_cdr2_contingency)
    print(f'Tyr (Chi-square):')
    print(f'  χ² = {chi2:.2f}, P = {p_val:.4f}')
    if p_val < 0.05:
        print(f'  ***  (P < 0.05)')
    else:
        print(f'   (P >= 0.05)')
    print

# 
contingency = pd.crosstab(df['fr3_n_aa'], df['cdr2_type'])
chi2, p_val, dof, expected = chi2_contingency(contingency)
print(f'FR3 N vs CDR2 (Chi-square):')
print(f'  χ² = {chi2:.2f}, P = {p_val:.4f}')
if p_val < 0.05:
    print(f'  ***  (P < 0.05)')
print

# 7. 
print('=' * 80)
print('7. FR3 NCDR2')
print('=' * 80)
print

print('CDR2 (H2-10-1, 10aa) → TyrFR3 N (75%):')
print
print('  1: ')
print('    - loop')
print('    - Tyr')
print('    - CDR2 CFR3 Nπ-π stacking')
print
print('  2: ')
print('    - loop')
print('    - Tyr')
print('    - loop')
print
print('  3: ')
print('    - 10aa loopC')
print('    - Tyr')
print('    - ')
print

print('-' * 80)
print

print('CDR2 (H2-9-1, 9aa) → Thr/FR3 N:')
print
print('  1: ')
print('    - loop，')
print('    - Thr/Ser/Asn')
print('    - steric clash')
print
print('  2: ')
print('    - loopbeta-turn')
print('    - turn')
print('    - Thr/SerOH')
print
print('  3: ')
print('    - 9aa loopC')
print('    - （Tyr）steric clash')
print('    - ')
print

# 8. 
print('=' * 80)
print('8. ')
print('=' * 80)
print

print('FR3 NCDR2:')
print
print('1. CDR2/:')
print('   - H2-10-1 : Tyr 75%')
print('   - H2-9-1 : Thr 50%, Tyr')
print
print('2. :')
print('   - CDR2:  (Tyr) - ')
print('   - CDR2:  (Thr) - ')
print
print('3. CDR3:')
print('   - CDR3Tyr (88.9%)')
print('   - CDR2 (P=0.013 vs P=0.066)')
print
print('4. :')
print('   - CDR2-FR3')
print('   - CDR2')
print('   - ""')
print

print('=' * 80)
print(': FR3 NCDR2 canonical classloop')
print('=' * 80)
