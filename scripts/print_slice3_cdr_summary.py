import json

path = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\features\slice3_vhh_canonical_config.json"
with open(path, "r", encoding="utf-8") as f:
    results = json.load(f)

print(f"{'Antibody ID':<15} | {'CDR1 (L)':<10} | {'CDR2 (L)':<10} | {'CDR3 (L)':<10}")
print("-" * 55)
for r in results:
    l1 = len(r['cdr1'])
    l2 = len(r['cdr2'])
    l3 = len(r['cdr3'])
    print(f"{r['antibody_id']:<15} | {l1:<10} | {l2:<10} | {l3:<10}")
