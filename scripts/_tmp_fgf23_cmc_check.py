import sys
sys.path.insert(0, ".")
from core.cmc.cmc_metrics import CMCMetricEngine

VH_WT = "EVQLQQSGPELVKPGASVKMSCKASGYTFTTYVMHWVKQKPGQGLEWIGYSNPYNDGTKYNEKFKGKATLTSAKSSSTAYMELSSLTSEDSAVYYCARGSLGMDYWGQGTSVTVSS"
VL_WT = "QIVLTQSPAIMSASPGEKVTMTCSASSSISYMHWYQQKPGTSPKRLMYDTSKLASGVPARFSGSGSGTAYSLTISSMEAEDAATYYCHQRNTYTFGGGTKLEIK"

# Verify mutation positions
assert VL_WT[90] == "N", f"VL pos 90 = {VL_WT[90]}, expected N"
assert VL_WT[92] == "Y", f"VL pos 92 = {VL_WT[92]}, expected Y"
assert VH_WT[54] == "N", f"VH pos 54 = {VH_WT[54]}, expected N"
print("Mutation positions verified: VL[90]=N (N91), VL[92]=Y (Y93), VH[54]=N (N55)")

variants = [
    ("WT",   VH_WT, VL_WT),
    ("N91F", VH_WT, VL_WT[:90]+"F"+VL_WT[91:]),
    ("Y93K", VH_WT, VL_WT[:92]+"K"+VL_WT[93:]),
    ("N91Y", VH_WT, VL_WT[:90]+"Y"+VL_WT[91:]),
    ("N91L", VH_WT, VL_WT[:90]+"L"+VL_WT[91:]),
    ("N91M", VH_WT, VL_WT[:90]+"M"+VL_WT[91:]),
    ("N55I", VH_WT[:54]+"I"+VH_WT[55:], VL_WT),
]

hdr = f"{'Variant':<10}  {'pI':>5}  {'GRAVY':>6}  {'Instab':>6}  {'ChrgPH7':>7}  {'DeamN':>5}  {'GlycN':>5}  {'OxSit':>5}  {'FCys':>4}  {'CMC7'}"
print(hdr)
print("-" * len(hdr))
results = []
for name, vh, vl in variants:
    r = CMCMetricEngine.compute_metrics(vh_seq=vh, vl_seq=vl)
    pi    = r.get("pI", "?")
    gravy = r.get("GRAVY", "?")
    inst  = r.get("instability_index", "?")
    chrg  = r.get("net_charge_pH7", "?")
    deam  = len(r.get("deamidation_sites") or [])
    glyc  = len(r.get("glycosylation_sites") or [])
    ox    = len(r.get("oxidation_sites") or [])
    fc    = len(r.get("free_cys") or [])
    # CMC verdict: FAIL if pI < 5 or > 9, GRAVY > 0.5, glyc > 0
    fails = []
    if isinstance(pi, float) and (pi < 5.0 or pi > 9.5):
        fails.append(f"pI={pi}")
    if isinstance(gravy, float) and gravy > 0.5:
        fails.append(f"GRAVY={gravy}")
    if glyc > 0:
        fails.append(f"N-glyc={glyc}")
    verdict = "FAIL:" + ",".join(fails) if fails else "PASS"
    print(f"{name:<10}  {str(pi):>5}  {str(gravy):>6}  {str(inst):>6}  {str(chrg):>7}  {deam:>5}  {glyc:>5}  {ox:>5}  {fc:>4}  {verdict}")
    results.append({"variant": name, "pI": pi, "GRAVY": gravy, "instability_index": inst,
                    "net_charge_pH7": chrg, "deamidation_n": deam, "glycosylation_n": glyc,
                    "oxidation_n": ox, "free_cys_n": fc, "cmc7_verdict": verdict,
                    "deamidation_sites": r.get("deamidation_sites"),
                    "glycosylation_sites": r.get("glycosylation_sites"),
                    "oxidation_sites": r.get("oxidation_sites"),
                    "free_cys": r.get("free_cys")})

import json
out = "projects/fgf 23/vam_boltz_scan/FGF23/stage4_postfilter/stage4_cmc7_supplement.json"
with open(out, "w") as f:
    json.dump({"generated_by": "_tmp_fgf23_cmc_check.py", "results": results}, f, indent=2)
print(f"\nSaved to {out}")
