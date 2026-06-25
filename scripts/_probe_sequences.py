"""Probe TheraSAbDab for 70-drug VH/VL availability."""
import pandas as pd, re, warnings
warnings.filterwarnings('ignore')

def norm(s):
    if pd.isna(s): return ''
    return re.sub(r'[-\s]', '', str(s).lower().strip())

df70 = pd.read_csv('data/thera_sabdab/out/confirmed70_human_humanized_germline_ada.csv')
names70 = {norm(n) for n in df70['antibody_name']}
print(f'70 drugs: {len(names70)}')

df = pd.read_excel('data/thera_sabdab/TheraSAbDab_SeqStruc_OnlineDownload.xlsx')
df['_key'] = df['Therapeutic'].apply(norm)
found = df[df['_key'].isin(names70)].copy()
print(f'Rows in TheraSAbDab: {len(found)}')

def seq_len(s):
    s = str(s).strip()
    return len(s) if s not in ('', 'nan', 'NaN') else 0

rows = []
for _, row in found.iterrows():
    name  = row['Therapeutic']
    h_len = seq_len(row.get('HeavySequence', ''))
    l_len = seq_len(row.get('LightSequence', ''))
    h2_len = seq_len(row.get('HeavySequence(ifbispec)', ''))
    l2_len = seq_len(row.get('LightSequence(ifbispec)', ''))
    rows.append((name, h_len, l_len, h2_len, l2_len))
    flag = ' [bispec]' if (h2_len or l2_len) else ''
    no_h = ' [NO_VH]' if not h_len else ''
    no_l = ' [NO_VL]' if not l_len else ''
    print(f'{name:35s}  VH={h_len:4d}  VL={l_len:4d}  VH2={h2_len:4d}  VL2={l2_len:4d}{flag}{no_h}{no_l}')

no_vh = [r[0] for r in rows if r[1] == 0]
no_vl = [r[0] for r in rows if r[2] == 0]
print(f'\nMissing VH ({len(no_vh)}): {no_vh}')
print(f'Missing VL ({len(no_vl)}): {no_vl}')
