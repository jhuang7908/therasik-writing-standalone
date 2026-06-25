import json
from collections import Counter
with open('CART_LIBRARY_V3.json', encoding='utf-8') as f:
    lib = json.load(f)
elements = lib['elements']

total = len(elements)
seq_ok = sum(1 for e in elements if e.get("sequence"))
t1 = sum(1 for e in elements if e.get("regulatory_tier")=="T1")
t2 = sum(1 for e in elements if e.get("regulatory_tier")=="T2")
t3 = sum(1 for e in elements if e.get("regulatory_tier")=="T3")

print("=== CART_LIBRARY_V3 FINAL STATUS ===")
print(f"Total elements:       {total}")
print(f"With sequence:        {seq_ok} ({100*seq_ok//total}%)")
print(f"Remaining stub:       {total-seq_ok}")
print(f"T1 (FDA/EMA approved): {t1}")
print(f"T2 (Clinical trial):   {t2}")
print(f"T3 (Research):         {t3}")
print()

cats = Counter(e.get("category","?") for e in elements)
print(f"{'Category':<26} {'Total':>5} {'Seq':>5}")
print("-"*38)
for cat in sorted(cats.keys()):
    es = [e for e in elements if e.get("category")==cat]
    ns = sum(1 for e in es if e.get("sequence"))
    print(f"  {cat:<24} {len(es):>5} {ns:>5}")

print()
print("=== Newly added in this session ===")
new_ids = ["SS1_scFv","SJ25C1_scFv","14G2a_hu_scFv","YP7_scFv","Anti_FRa_MOv19_scFv",
           "cAC10_CD30_scFv","HSV-TK","APRIL_Ligand_Binder","iCAR_PSMA",
           "ESK1_WT1_TCRmimic","RQR8","WPRE","BGH_polyA","SV40_polyA",
           "SFFV_Promoter","NFAT_RE_Promoter","EF1a_Promoter","EFS_Promoter",
           "Tet_On_System","JNJ68284528_VHH"]
v3m = {e["id"]: e for e in elements}
for eid in new_ids:
    e = v3m.get(eid, {})
    if e:
        seq = e.get("sequence", "")
        lng = len(seq) if seq else "STUB"
        status = e.get("sequence_status","?")
        print(f"  {eid:<30} {lng:>5}  {status}")
