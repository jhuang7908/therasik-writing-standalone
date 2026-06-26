import pandas as pd
import numpy as np
import os

path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada245\database\ada_master_245_curated.csv'
if not os.path.exists(path):
    print(f"Error: File not found at {path}")
    exit(1)

df = pd.read_csv(path)

print("---  (Database Audit Report) ---")
print(f"Total entries: {len(df)}")

# 1. Sequence completeness
missing_vh = df['vh_seq'].isna().sum()
missing_vl = df['vl_seq'].isna().sum()
print(f"[!]  (Sequence Missing): VH={missing_vh}, VL={missing_vl}")

# 2. ADA Value Validity
def check_ada_valid(x):
    if pd.isna(x): return False
    s = str(x).lower()
    if 'percentage' in s or '%' in s: return True
    if s == 'nan' or s == '': return False
    try:
        float(str(x).replace('%','').strip())
        return True
    except:
        return False

invalid_ada = df[~df['ada_value_display'].apply(check_ada_valid)]
print(f"[!] ADA/: {len(invalid_ada)} ")
if len(invalid_ada) > 0:
    print(f"    - : {invalid_ada['antibody_name'].tolist()[:10]}")

# 3. BLA vs Tier Mismatch
# Entries with BLA should be T1-FDA
mismatch = df[df['bla_number'].notna() & (df['evidence_tier_p0'] != 'T1-FDA')]
print(f"[!] BLA  Tier  (BLA exists but not T1-FDA): {len(mismatch)} ")
if len(mismatch) > 0:
    for _, row in mismatch.head(10).iterrows():
        print(f"    - {row['antibody_name']}: BLA={row['bla_number']}, Tier={row['evidence_tier_p0']}, Note={row['verify_note']}")

# 4. T3 (Literature) Reliability
suspect_t3 = df[(df['evidence_tier_p0'] == 'T3-Lit') & 
                (df['verify_note'].str.contains('UNREACHABLE|Placeholder|SOURCE_LIVE', case=False, na=False))]
print(f"[!] T3  (): {len(suspect_t3)} ")

# 5. NAb Data Coverage
nab_filled = df['nab_pct'].notna().sum()
print(f"[*] NAb : {nab_filled}/{len(df)} ({nab_filled/len(df):.1%})")

# 6. Critical Features (VH/VL Germline Identity)
missing_vh_id = df['vh_germline_identity'].isna().sum()
missing_vl_id = df['vl_germline_identity'].isna().sum()
print(f"[!]  (Germline ID): VH={missing_vh_id}, VL={missing_vl_id}")

# 7. Duplicates
dupes = df[df['antibody_name'].str.lower().duplicated(keep=False)]
if len(dupes) > 0:
    print(f"[!] : {dupes['antibody_name'].unique().tolist()}")

# 8. Source Section check
missing_section = df['ada_source_section'].isna().sum()
print(f"[!]  (ada_source_section): {missing_section} ")
