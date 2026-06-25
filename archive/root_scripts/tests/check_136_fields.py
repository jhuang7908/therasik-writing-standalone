import pandas as pd
import json

df = pd.read_csv('data/immunogenicity_panel_136_master.csv')
n = len(df)
print("Total rows:", n)
print("\n=== ALL COLUMNS ===")
for c in df.columns:
    nn = df[c].notna().sum()
    print("  {:40} {}/{}".format(c, nn, n))

# Check natural_380 and engineered_459 for MHC-II columns
nat = pd.read_csv('data/natural_380_atlas/master_table.csv')
eng = pd.read_csv('data/engineered_459_atlas/master_table.csv')

print("\n=== natural_380 immuno-related columns ===")
immuno_cols = [c for c in nat.columns if 'immuno' in c.lower() or 'mhc' in c.lower() or 'tcia' in c.lower() or 'epitope' in c.lower() or 'allele' in c.lower()]
for c in immuno_cols:
    nn = nat[c].notna().sum()
    print("  {:45} {}/{}".format(c, nn, len(nat)))

print("\n=== engineered_459 immuno-related columns ===")
immuno_cols_eng = [c for c in eng.columns if 'immuno' in c.lower() or 'mhc' in c.lower() or 'tcia' in c.lower() or 'epitope' in c.lower() or 'allele' in c.lower()]
for c in immuno_cols_eng:
    nn = eng[c].notna().sum()
    print("  {:45} {}/{}".format(c, nn, len(eng)))

print("\n=== natural_380 CMC columns ===")
cmc_cols = [c for c in nat.columns if any(k in c.lower() for k in ['pi','gravy','instab','patch','charge','cmc','adi','hydro','net_'])]
for c in cmc_cols:
    nn = nat[c].notna().sum()
    print("  {:45} {}/{}".format(c, nn, len(nat)))

# Check if TCIA is per-allele or aggregate
print("\n=== Sample TCIA values in atlas (first 5) ===")
if 'immuno_tcia_score' in nat.columns:
    print(nat[['antibody_id','immuno_tcia_score','immuno_risk_level']].dropna().head(5).to_string())
