"""
ThermoMPNN × EvoEF2 
 EvoEF2 L1  ThermoMPNN 
VAM Standard Scenario C MANDATORY: ddG_fold > +0.5 → 
"""
import csv
from pathlib import Path

THRESHOLD = 0.5
BASE = Path("projects/mumab4d5_VGRW_SR_R2/affinity_maturation_v2")

# ThermoMPNN SSM 
thermo = {}
with open(BASE / "ThermoMPNN_inference_vhh_chainA_only.csv") as f:
    for row in csv.DictReader(f):
        pos = int(row["position"])
        wt  = row["wildtype"]
        mut = row["mutation"]
        ddg = float(row["ddG_pred"])
        thermo[(pos, wt, mut)] = ddg

# EvoEF2 （ddg_bind < 0.5）
passed, vetoed, unknown = [], [], []
with open(BASE / "evoef2_scan_results.csv") as f:
    for row in csv.DictReader(f):
        if row["error"]:
            continue
        try:
            ddg_bind = float(row["ddg_bind"])
        except ValueError:
            continue
        if ddg_bind >= 0.5:
            continue

        site   = int(row["site"])
        wt_aa  = row["wt_aa"]
        mut_aa = row["mut_aa"]
        label  = row["mutation"]

        # ThermoMPNN position = Kabat number - 1 (verified from PDB residue numbering)
        thermo_pos = site - 1
        ddg_fold = thermo.get((thermo_pos, wt_aa, mut_aa))
        entry = dict(mutation=label, site=site, wt_aa=wt_aa, mut_aa=mut_aa,
                     evoef2_ddg=round(ddg_bind, 3),
                     ddg_fold=round(ddg_fold, 4) if ddg_fold is not None else None)

        if ddg_fold is None:
            unknown.append(entry)
        elif ddg_fold > THRESHOLD:
            entry["verdict"] = "VETO"
            vetoed.append(entry)
        else:
            entry["verdict"] = "PASS"
            passed.append(entry)

# 
out_csv = BASE / "thermompnn_cross_results.csv"
fields  = ["mutation","site","wt_aa","mut_aa"," eucef2_ddg","ddg_fold","verdict"]
rows    = [{**e, "evoef2_ddg": e["evoef2_ddg"],
            "verdict": e.get("verdict","UNKNOWN")} for e in passed+vetoed+unknown]
with open(out_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["mutation","site","wt_aa","mut_aa",
                                       "evoef2_ddg","ddg_fold","verdict"])
    w.writeheader()
    for e in sorted(rows, key=lambda x: (x["site"], x["mut_aa"])):
        w.writerow({k: e.get(k, "") for k in
                    ["mutation","site","wt_aa","mut_aa","evoef2_ddg","ddg_fold","verdict"]})

# 
total_l1 = len(passed) + len(vetoed) + len(unknown)
print("=" * 60)
print("ThermoMPNN ")
print(f"  EvoEF2 L1    : {total_l1}")
print(f"  ThermoMPNN VETO     : {len(vetoed)}")
print(f"  （）   : {len(unknown)}")
print(f"   (L1+L2a)   : {len(passed)}")
print("=" * 60)

if vetoed:
    print("\n───  (ddG_fold > +0.5) ───")
    for e in sorted(vetoed, key=lambda x: -x["ddg_fold"]):
        print(f"  {e['mutation']:<12s}  EvoEF2={e['evoef2_ddg']:+.3f}  "
              f"ddG_fold={e['ddg_fold']:+.4f}  VETO")

print("\n─── L1+L2a （ EvoEF2 ΔΔG ）───")
print(f"{'Mutation':<12s}  {'EvoEF2':>9s}  {'ddG_fold':>10s}")
print("-" * 38)
for e in sorted(passed, key=lambda x: x["evoef2_ddg"]):
    fold_str = f"{e['ddg_fold']:+.4f}" if e["ddg_fold"] is not None else "  N/A"
    print(f"{e['mutation']:<12s}  {e['evoef2_ddg']:>+9.3f}  {fold_str:>10s}")

print(f"\n: {out_csv}")
