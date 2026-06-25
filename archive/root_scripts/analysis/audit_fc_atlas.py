import json, os
import csv

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data'

# Check engineered atlas for Fc engineering columns
print("=== engineered_459_atlas master_table ===")
with open(ROOT + r'\engineered_459_atlas\master_table.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
print(f"Rows: {len(rows)}")
if rows:
    print(f"Columns: {list(rows[0].keys())}")
    # Find Fc-related columns
    fc_cols = [c for c in rows[0].keys() if any(k in c.lower() for k in ['fc','isotype','igg','mutation','engineering','adcc','cdc','fcrn','neonatal'])]
    print(f"Fc-related cols: {fc_cols}")
    if fc_cols:
        fc_rows = [r for r in rows if any(r.get(c) for c in fc_cols[:3])]
        print(f"Rows with Fc data: {len(fc_rows)}")
        # Sample
        if fc_rows:
            print(f"Sample Fc row: { {c: fc_rows[0].get(c,'') for c in fc_cols[:6]} }")

print("\n=== natural_380_atlas master_table ===")
with open(ROOT + r'\natural_380_atlas\master_table.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    nat_rows = list(reader)
print(f"Rows: {len(nat_rows)}")
if nat_rows:
    cols = list(nat_rows[0].keys())
    print(f"All columns ({len(cols)}): {cols}")

# Check if there's any fc-specific data anywhere
print("\n=== Searching for Fc mutation data ===")
for dirpath, dirs, files in os.walk(ROOT):
    for f in files:
        if 'fc' in f.lower() and (f.endswith('.csv') or f.endswith('.json')):
            fp = os.path.join(dirpath, f)
            size = os.path.getsize(fp)
            print(f"  {fp.replace(ROOT,'')} ({size:,} bytes)")

# Check data/immunogenicity for Fc info
immuno_dir = ROOT + r'\immunogenicity'
if os.path.exists(immuno_dir):
    print(f"\nimmunogenicity dir: {os.listdir(immuno_dir)[:10]}")

# Check ADA master for Fc columns
with open(ROOT + r'\ada_master_136_curated.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    ada_rows = list(reader)
print(f"\nADA master cols: {list(ada_rows[0].keys()) if ada_rows else 'empty'}")
fc_ada = [c for c in (ada_rows[0].keys() if ada_rows else []) if 'fc' in c.lower() or 'isotype' in c.lower() or 'adcc' in c.lower()]
print(f"Fc-related in ADA: {fc_ada}")
