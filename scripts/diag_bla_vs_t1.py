import pandas as pd
df = pd.read_csv(r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada245\database\ada_master_245_curated.csv')

has_bla = df['bla_number'].str.startswith('BLA', na=False)
is_t1   = df['evidence_tier_p0'] == 'T1-FDA'

t1_total      = is_t1.sum()
t1_with_bla   = (is_t1 & has_bla).sum()
t1_without_bla = (is_t1 & ~has_bla).sum()
bla_not_t1    = (~is_t1 & has_bla).sum()

print(f"=== BLA vs T1 Discrepancy Analysis ===")
print(f"T1-FDA entries total:              {t1_total}")
print(f"  - T1 WITH real BLA (BLA*):       {t1_with_bla}")
print(f"  - T1 WITHOUT real BLA:           {t1_without_bla}  <-- These are the gap")
print(f"Has BLA* but NOT T1-FDA:           {bla_not_t1}")
print(f"Total entries with BLA*:           {has_bla.sum()}")
print()

# Show T1 entries that DON'T have a real BLA number
print("--- T1-FDA entries WITHOUT a real BLA number ---")
t1_no_bla = df[is_t1 & ~has_bla][['antibody_name','bla_number','evidence_tier_p0']]
print(t1_no_bla.to_string())
print()

# Show BLA entries that are NOT T1
print("--- Has real BLA but NOT classified T1-FDA ---")
bla_non_t1 = df[~is_t1 & has_bla][['antibody_name','bla_number','evidence_tier_p0']]
print(bla_non_t1.to_string())
