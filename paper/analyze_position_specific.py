import pandas as pd
import numpy as np
from scipy.stats import chi2_contingency, fisher_exact

# 
df = pd.read_csv('Supplementary_Materials/Analysis_Reports/TheraSAbDab_19VHH_New_Classification_Table.csv')

# CDR3
short_cdr3 = df[df['h3_length'] <= 11]
long_cdr3 = df[df['h3_length'] > 11]

print('=' * 80)
print('FR4FR3CDR3')
print('=' * 80)
print

# ============================================================================
# FR4
# ============================================================================
print('FR4 ')
print('=' * 80)
print

# FR4 IMGT118-128
fr4_imgt_start = 118

for pos in range(11):  # FR411
    imgt_pos = fr4_imgt_start + pos
    
    short_aa = short_cdr3['fr4_sequence'].str[pos].value_counts
    long_aa = long_cdr3['fr4_sequence'].str[pos].value_counts
    
    # 
    all_aa = sorted(set(short_aa.index) | set(long_aa.index))
    
    # 
    max_diff = 0
    for aa in all_aa:
        short_freq = short_aa.get(aa, 0) / len(short_cdr3) * 100
        long_freq = long_aa.get(aa, 0) / len(long_cdr3) * 100
        max_diff = max(max_diff, abs(short_freq - long_freq))
    
    if max_diff > 15:  # 
        print(f'IMGT {imgt_pos} (FR4{pos+1}):  {max_diff:.1f}%')
        print(f'  CDR3 (N={len(short_cdr3)}):')
        for aa in all_aa:
            count = short_aa.get(aa, 0)
            freq = count / len(short_cdr3) * 100
            if freq > 0:
                print(f'    {aa}: {count}/{len(short_cdr3)} ({freq:.1f}%)')
        
        print(f'  CDR3 (N={len(long_cdr3)}):')
        for aa in all_aa:
            count = long_aa.get(aa, 0)
            freq = count / len(long_cdr3) * 100
            if freq > 0:
                print(f'    {aa}: {count}/{len(long_cdr3)} ({freq:.1f}%)')
        
        # Fisher（2x2）
        if len(all_aa) == 2:
            aa1, aa2 = all_aa
            table = [
                [short_aa.get(aa1, 0), short_aa.get(aa2, 0)],
                [long_aa.get(aa1, 0), long_aa.get(aa2, 0)]
            ]
            try:
                odds_ratio, p_value = fisher_exact(table)
                print(f'  Fisher: P = {p_value:.4f}')
                if p_value < 0.05:
                    print(f'  ***  ***')
            except:
                pass
        
        print

# ============================================================================
# FR3
# ============================================================================
print
print('=' * 80)
print('FR3 ')
print('=' * 80)
print

# FR3IMGT，CDR2C
# FR3CDR2，CDR3（Cys104）
# fr3_sequence

fr3_length = df['fr3_sequence'].str.len.max

# FR3 N（CDR2，CDR）
print('FR3 N（CDR2，10）:')
print('-' * 80)

for pos in range(min(10, fr3_length)):
    short_aa = short_cdr3['fr3_sequence'].str[pos].value_counts
    long_aa = long_cdr3['fr3_sequence'].str[pos].value_counts
    
    all_aa = sorted(set(short_aa.index) | set(long_aa.index))
    
    # 
    max_diff = 0
    for aa in all_aa:
        short_freq = short_aa.get(aa, 0) / len(short_cdr3) * 100
        long_freq = long_aa.get(aa, 0) / len(long_cdr3) * 100
        max_diff = max(max_diff, abs(short_freq - long_freq))
    
    if max_diff > 20:  # 
        print(f'\nFR3 {pos+1}: ***  {max_diff:.1f}% ***')
        print(f'  CDR3:')
        for aa in all_aa:
            count = short_aa.get(aa, 0)
            freq = count / len(short_cdr3) * 100
            if freq > 0:
                print(f'    {aa}: {count}/{len(short_cdr3)} ({freq:.1f}%)')
        
        print(f'  CDR3:')
        for aa in all_aa:
            count = long_aa.get(aa, 0)
            freq = count / len(long_cdr3) * 100
            if freq > 0:
                print(f'    {aa}: {count}/{len(long_cdr3)} ({freq:.1f}%)')

# FR3 C（CDR3）
print
print('FR3 C（CDR3，10）:')
print('-' * 80)

for pos in range(max(0, fr3_length-10), fr3_length):
    short_aa = short_cdr3['fr3_sequence'].str[pos].value_counts
    long_aa = long_cdr3['fr3_sequence'].str[pos].value_counts
    
    all_aa = sorted(set(short_aa.index) | set(long_aa.index))
    
    max_diff = 0
    for aa in all_aa:
        short_freq = short_aa.get(aa, 0) / len(short_cdr3) * 100
        long_freq = long_aa.get(aa, 0) / len(long_cdr3) * 100
        max_diff = max(max_diff, abs(short_freq - long_freq))
    
    if max_diff > 20:
        print(f'\nFR3 {pos+1} ({fr3_length-pos-1}): ***  {max_diff:.1f}% ***')
        print(f'  CDR3:')
        for aa in all_aa:
            count = short_aa.get(aa, 0)
            freq = count / len(short_cdr3) * 100
            if freq > 0:
                print(f'    {aa}: {count}/{len(short_cdr3)} ({freq:.1f}%)')
        
        print(f'  CDR3:')
        for aa in all_aa:
            count = long_aa.get(aa, 0)
            freq = count / len(long_cdr3) * 100
            if freq > 0:
                print(f'    {aa}: {count}/{len(long_cdr3)} ({freq:.1f}%)')

# ============================================================================
# 
# ============================================================================
print
print('=' * 80)
print('')
print('=' * 80)
print

print('CDR3:')
print

# FR4
print('FR4 (IMGT 118-128):')
fr4_significant_positions = []
for pos in range(11):
    imgt_pos = 118 + pos
    short_aa = short_cdr3['fr4_sequence'].str[pos].value_counts
    long_aa = long_cdr3['fr4_sequence'].str[pos].value_counts
    all_aa = set(short_aa.index) | set(long_aa.index)
    
    max_diff = 0
    for aa in all_aa:
        short_freq = short_aa.get(aa, 0) / len(short_cdr3) * 100
        long_freq = long_aa.get(aa, 0) / len(long_cdr3) * 100
        max_diff = max(max_diff, abs(short_freq - long_freq))
    
    if max_diff > 15:
        fr4_significant_positions.append(f'IMGT {imgt_pos} ({max_diff:.1f}%)')

print(f'  : {", ".join(fr4_significant_positions)}')

# FR3
print
print('FR3:')
fr3_significant_positions = []
for pos in range(fr3_length):
    short_aa = short_cdr3['fr3_sequence'].str[pos].value_counts
    long_aa = long_cdr3['fr3_sequence'].str[pos].value_counts
    all_aa = set(short_aa.index) | set(long_aa.index)
    
    max_diff = 0
    for aa in all_aa:
        short_freq = short_aa.get(aa, 0) / len(short_cdr3) * 100
        long_freq = long_aa.get(aa, 0) / len(long_cdr3) * 100
        max_diff = max(max_diff, abs(short_freq - long_freq))
    
    if max_diff > 20:
        location = f'N' if pos < 10 else f'C' if pos >= fr3_length - 10 else ''
        fr3_significant_positions.append(f'{pos+1}({location}, {max_diff:.1f}%)')

if fr3_significant_positions:
    print(f'  : {", ".join(fr3_significant_positions)}')
else:
    print(f'  （>20%）')

print
print('=' * 80)
print(':')
print('  1. FR4N（IMGT 118）CDR3')
print('  2. FR3N（CDR2）CDR3')
print('  3. CDR3')
print('=' * 80)
