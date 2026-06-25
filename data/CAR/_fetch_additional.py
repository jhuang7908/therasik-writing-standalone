"""Fetch additional sequences needed for functional_domains.json"""
import json
import time
from urllib import request

BASE = "https://rest.uniprot.org/uniprotkb/{}.fasta"

def fetch(acc):
    with request.urlopen(BASE.format(acc), timeout=15) as r:
        fasta = r.read().decode()
    lines = fasta.strip().splitlines()
    return "".join(ln for ln in lines if not ln.startswith(">"))

def seg(seq, s, e):
    return seq[s-1:e]

results = {}

print("Fetching FKBP12 (P62942)...")
fkbp12_full = fetch("P62942"); time.sleep(0.3)
results["FKBP12_full"] = fkbp12_full
results["FKBP12_108"] = fkbp12_full  # full protein is 108 aa
print(f"  FKBP12 full: {len(fkbp12_full)} aa")

print("Fetching Caspase-9 (P55211)...")
casp9_full = fetch("P55211"); time.sleep(0.3)
results["CASP9_full_len"] = len(casp9_full)
results["CASP9_deltaCard"] = seg(casp9_full, 135, 416)
print(f"  CASP9 full: {len(casp9_full)} aa | ΔCARD (135-416): {len(results['CASP9_deltaCard'])} aa")

print("Fetching IgG4 constant region (P01861)...")
igg4_full = fetch("P01861"); time.sleep(0.3)
results["IgG4_hinge_CH2_CH3"] = seg(igg4_full, 99, 327)  # Hinge+CH2+CH3 of IgG4 (EU 216-447 = ~99-327 in chain)
print(f"  IgG4 full: {len(igg4_full)} aa")

print("Fetching Granulin SP (P28799)...")
grn_full = fetch("P28799"); time.sleep(0.3)
results["Granulin_SP"] = seg(grn_full, 1, 21)
print(f"  Granulin SP (1-21): {results['Granulin_SP']}")

print("Fetching DAP12 costim (O43914)...")
dap12_full = fetch("O43914"); time.sleep(0.3)
results["DAP12_costim"] = seg(dap12_full, 76, 106)
print(f"  DAP12 costim (76-106): {len(results['DAP12_costim'])} aa = {results['DAP12_costim']}")

print("Fetching FcRg (P30273)...")
fcrg_full = fetch("P30273"); time.sleep(0.3)
results["FcRg_cyto"] = seg(fcrg_full, 45, 86)
print(f"  FcRg cyto (45-86): {len(results['FcRg_cyto'])} aa = {results['FcRg_cyto']}")

print("Fetching TGFB-RII for DNR (P37173)...")
tgfbr2_full = fetch("P37173"); time.sleep(0.3)
results["TGFB_DNR_ECD_TM"] = seg(tgfbr2_full, 1, 189)
print(f"  TGFB DNR ECD+TM (1-189): {len(results['TGFB_DNR_ECD_TM'])} aa")

with open("_additional_seqs.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("\nSaved to _additional_seqs.json")
