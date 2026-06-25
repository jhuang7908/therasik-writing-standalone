import pandas as pd

nat = pd.read_csv('data/natural_380_atlas/master_table.csv')
eng = pd.read_csv('data/engineered_459_atlas/master_table.csv')
master = pd.read_csv('data/immunogenicity_panel_136_master.csv')

print("=== ALL natural_380 columns ({}) ===".format(len(nat.columns)))
for c in nat.columns:
    nn = nat[c].notna().sum()
    in_master = '[IN_MASTER]' if c in master.columns else '[MISSING_FROM_MASTER]'
    print("  {:50} {:4}/{} {}".format(c, nn, len(nat), in_master))

print("\n=== Columns in engineered_459 but not in natural_380 ===")
for c in eng.columns:
    if c not in nat.columns:
        print("  ", c)

print("\n=== Columns in 136-master but NOT in either atlas ===")
for c in master.columns:
    if c not in nat.columns and c not in eng.columns:
        print("  ", c)
