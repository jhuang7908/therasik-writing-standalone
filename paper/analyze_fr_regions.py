import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr
import numpy as np

# 
df = pd.read_csv('Supplementary_Materials/Analysis_Reports/TheraSAbDab_19VHH_New_Classification_Table.csv')

# CDR3
short_cdr3 = df[df['h3_length'] <= 11]
long_cdr3 = df[df['h3_length'] > 11]

print('=' * 80)
print('Framework Regions - CDR3')
print('=' * 80)
print

# FR
for fr_name in ['FR1', 'FR2', 'FR3', 'FR4']:
    col_name = f'{fr_name.lower}_human_pct'
    
    print(f'{fr_name} ')
    print('-' * 80)
    
    # 
    print(f' (N={len(df)}):')
    print(f'  : {df[col_name].mean:.2f}%')
    print(f'  : {df[col_name].std:.2f}%')
    print(f'  : {df[col_name].min:.2f}% - {df[col_name].max:.2f}%')
    print
    
    # CDR3
    print(f'CDR3 (<=11aa, N={len(short_cdr3)}):')
    print(f'  : {short_cdr3[col_name].mean:.2f}% ± {short_cdr3[col_name].std:.2f}%')
    print(f'  : {short_cdr3[col_name].min:.2f}% - {short_cdr3[col_name].max:.2f}%')
    print
    
    print(f'CDR3 (>11aa, N={len(long_cdr3)}):')
    print(f'  : {long_cdr3[col_name].mean:.2f}% ± {long_cdr3[col_name].std:.2f}%')
    print(f'  : {long_cdr3[col_name].min:.2f}% - {long_cdr3[col_name].max:.2f}%')
    print
    
    # 
    u_stat, p_value_mw = mannwhitneyu(short_cdr3[col_name], long_cdr3[col_name])
    rho, p_value_corr = spearmanr(df['h3_length'], df[col_name])
    
    print(f':')
    print(f'  Mann-Whitney U: U={u_stat:.1f}, P={p_value_mw:.4f}')
    print(f'  Spearman: ρ={rho:.3f}, P={p_value_corr:.4f}')
    
    # 
    if p_value_mw < 0.05:
        print(f'  *** {fr_name}CDR3 ***')
    else:
        print(f'  {fr_name}CDR3')
    print
    print

# FR4
print('=' * 80)
print('FR4 ')
print('=' * 80)
print

# FR4
fr4_sequences = df.groupby('fr4_sequence').size.sort_values(ascending=False)
print(f'FR4: {len(fr4_sequences)}')
print
print('FR4:')
for seq, count in fr4_sequences.head(5).items:
    print(f'  {seq}: {count}VHH ({count/len(df)*100:.1f}%)')
print

# FR4
print('CDR3FR4:')
for idx, row in short_cdr3.iterrows:
    print(f'  {row["antibody_id"]:<20} {row["fr4_sequence"]:<15} :{row["fr4_human_pct"]:>5.1f}%')
print

print('CDR3FR4:')
for idx, row in long_cdr3.iterrows:
    print(f'  {row["antibody_id"]:<20} {row["fr4_sequence"]:<15} :{row["fr4_human_pct"]:>5.1f}%')
print

# 
print('=' * 80)
print('')
print('=' * 80)
print
print('CDR3Framework Region:')
for fr_name in ['FR1', 'FR2', 'FR3', 'FR4']:
    col_name = f'{fr_name.lower}_human_pct'
    rho, p_value = spearmanr(df['h3_length'], df[col_name])
    
    if p_value < 0.001:
        sig = '***'
    elif p_value < 0.01:
        sig = '**'
    elif p_value < 0.05:
        sig = '*'
    else:
        sig = 'ns'
    
    print(f'  {fr_name}: ρ={rho:>6.3f}, P={p_value:.4f} {sig}')

print
print(': *** P<0.001, ** P<0.01, * P<0.05, ns P>=0.05')
