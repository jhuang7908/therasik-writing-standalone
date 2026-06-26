"""
Detailed threshold analysis by VHH category.
"""
import csv, json
import sys
from pathlib import Path

ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.insert(0, str(ROOT))

try:
    from Bio.SeqUtils.ProtParam import ProteinAnalysis
    HAS_BIO = True
except ImportError:
    HAS_BIO = False

def pi_gravy(seq):
    if not seq or not HAS_BIO: return None, None
    try:
        a = ProteinAnalysis(seq.replace("-","").replace("X",""))
        return round(a.isoelectric_point(), 2), round(a.gravy(), 3)
    except: return None, None

def stats(vals, label=""):
    vals = sorted([v for v in vals if v is not None])
    if not vals: return f"n=0"
    n = len(vals)
    p10 = vals[max(0,int(n*0.10))]
    p25 = vals[max(0,int(n*0.25))]
    p75 = vals[max(0,int(n*0.75))]
    p90 = vals[min(n-1,int(n*0.90))]
    return (f"n={n}  range [{vals[0]:.2f}, {vals[-1]:.2f}]  "
            f"p10={p10:.2f} p25={p25:.2f} median={vals[n//2]:.2f} "
            f"p75={p75:.2f} p90={p90:.2f}")

# Load VHH benchmarks
rows = list(csv.DictReader((ROOT / "data/vhh_master_benchmarks_v3.csv").open(encoding="utf-8")))

# Group by category
from collections import defaultdict
cats = defaultdict(list)
for r in rows:
    cats[r.get("category","?")].append(r)

print("=== VHH Master Benchmarks v3 — by Category ===\n")
for cat, rrows in sorted(cats.items()):
    pis     = [float(r["pI"]) for r in rrows if r.get("pI")]
    gravys  = [float(r["GRAVY"]) for r in rrows if r.get("GRAVY")]
    deltas  = [float(r["abnativ_delta"]) for r in rrows if r.get("abnativ_delta")]
    rgs     = [float(r["compactness_A"]) for r in rrows if r.get("compactness_A")]
    print(f"[{cat}]  n={len(rrows)}")
    if pis:    print(f"  pI:         {stats(pis)}")
    if gravys: print(f"  GRAVY:      {stats(gravys)}")
    if deltas: print(f"  AbNatiV Δ:  {stats(deltas)}")
    if rgs:    print(f"  CDR3 Rg:    {stats(rgs)}")
    print()

# Overall
print("=== ALL (n=160) ===")
all_pi     = [float(r["pI"]) for r in rows if r.get("pI")]
all_gravy  = [float(r["GRAVY"]) for r in rows if r.get("GRAVY")]
all_delta  = [float(r["abnativ_delta"]) for r in rows if r.get("abnativ_delta")]
all_rg     = [float(r["compactness_A"]) for r in rows if r.get("compactness_A")]
print(f"  pI:         {stats(all_pi)}")
print(f"  GRAVY:      {stats(all_gravy)}")
print(f"  AbNatiV Δ:  {stats(all_delta)}")
print(f"  CDR3 Rg:    {stats(all_rg)}")

# What fraction of clinical VHH would FAIL our 5.5-8.5 pI threshold?
fail_pi = [p for p in all_pi if p > 8.5 or p < 5.5]
print(f"\n  pI > 8.5 or < 5.5 (fail current threshold): {len(fail_pi)}/{len(all_pi)} = {100*len(fail_pi)/len(all_pi):.1f}%")
fail_hi = [p for p in all_pi if p > 8.5]
print(f"  pI > 8.5 only: {len(fail_hi)}/{len(all_pi)} = {100*len(fail_hi)/len(all_pi):.1f}%")

# AbNatiV threshold analysis
fail_delta = [d for d in all_delta if d < -0.074]
print(f"  AbNatiV Δ < -0.074 (fail current threshold): {len(fail_delta)}/{len(all_delta)} = {100*len(fail_delta)/len(all_delta):.1f}%")
fail_delta2 = [d for d in all_delta if d < -0.050]
print(f"  AbNatiV Δ < -0.050 (fail PASS grade): {len(fail_delta2)}/{len(all_delta)} = {100*len(fail_delta2)/len(all_delta):.1f}%")

# CDR3 Rg
if all_rg:
    fail_rg = [r for r in all_rg if r > 6.5]
    print(f"  CDR3 Rg > 6.5 (fail current threshold): {len(fail_rg)}/{len(all_rg)} = {100*len(fail_rg)/len(all_rg):.1f}%")

print("\n=== Source breakdown ===")
from collections import Counter
src_c = Counter(r.get("source","?") for r in rows)
for s, n in sorted(src_c.items(), key=lambda x: -x[1]):
    src_rows = [r for r in rows if r.get("source") == s]
    src_pis = [float(r["pI"]) for r in src_rows if r.get("pI")]
    if src_pis:
        mn, mx = min(src_pis), max(src_pis)
        med = sorted(src_pis)[len(src_pis)//2]
        print(f"  {s:<30} n={n}  pI [{mn:.2f}–{mx:.2f}] median={med:.2f}")
