import json
from pathlib import Path
from collections import defaultdict

lib = json.loads(Path('CART_LIBRARY_V3.json').read_text(encoding='utf-8'))
elements = lib['elements']
total = len(elements)

print(f"Total elements: {total}\n")

new_ids = [
    'DAP12_signaling','mbIL15_Armor','NKG2D_Full_CAR_NK',
    'FcgRI_TM_cyto_CARM','CD68_Promoter_CARM','BCMA_scFv_AutoImmune',
    'GPC3_scFv','PTPN2_KO_guide','CD39_KO_guide','CIITA_KO_guide',
    'REGNASE1_KO_guide','c_Jun_OE','BATF_OE','NR4A1_DN','TOX2_DN',
    'CCR2b','CXCR3','CLDN18_2_scFv','CD5_scFv_InVivo_Targeting',
    'SleepingBeauty_SB100X','iNKT_TCR_Va24Vb11','CD1d_Lipid_Loading_Signal',
    'Helios_OE','HLA_E_NK_Evasion','CD47_DontEatMe','BCL11B_T_lineage','RUNX3_OE'
]

idx = {e['id']: e for e in elements}
print(f"{'ID':<35} {'Category':<30} {'Tier':<5} {'Len':>5}")
print("-"*80)
for nid in new_ids:
    e = idx.get(nid)
    if e:
        cat = e.get('category', '?')[:28]
        tier = e.get('regulatory_tier','?')
        length = e.get('length', 0)
        print(f"{nid:<35} {cat:<30} {tier:<5} {length:>5}")
    else:
        print(f"{nid:<35} NOT FOUND")

# All categories now
print("\n--- All categories ---")
cats = defaultdict(int)
for e in elements:
    cats[e.get('category','?')] += 1
for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {cnt:3d}  {cat}")
