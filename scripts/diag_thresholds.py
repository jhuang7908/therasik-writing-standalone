"""
Check pI / GRAVY / AbNatiV statistics from all available reference cohorts.
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
    if not seq or not HAS_BIO:
        return None, None
    try:
        a = ProteinAnalysis(seq.replace("-","").replace("X",""))
        return round(a.isoelectric_point(), 2), round(a.gravy(), 3)
    except:
        return None, None

def stats(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "n=0"
    vals.sort()
    n = len(vals)
    mn, mx = vals[0], vals[-1]
    med = vals[n//2]
    avg = round(sum(vals)/n, 3)
    p10 = vals[int(n*0.10)]
    p90 = vals[int(n*0.90)]
    return f"n={n} min={mn} max={mx} median={med} mean={avg} p10={p10} p90={p90}"

print("=" * 70)

# 1. AutonomousHumanVH Cohort (EngVH, n=36)
print("\n=== 1. AutonomousHumanVH_Cohort_v1 (Engineered Human VH, n=36) ===")
rows = list(csv.DictReader((ROOT / "data/reference/AutonomousHumanVH_Cohort_v1.csv").open(encoding="utf-8")))
# No sequences in CSV... check JSON
d = json.loads((ROOT / "data/reference/AutonomousHumanVH_Cohort_v1.json").read_text())
entries = d.get("entries", [])
pis, gravys = [], []
for e in entries:
    seq = e.get("sequence") or e.get("vh_sequence") or e.get("aa_sequence")
    if seq:
        p, g = pi_gravy(seq)
        if p: pis.append(p)
        if g: gravys.append(g)
print(f"  Has sequences: {len(pis)} entries with seq")
if pis:
    print(f"  pI:    {stats(pis)}")
    print(f"  GRAVY: {stats(gravys)}")
else:
    print("  No sequences in JSON — checking CSV for seq column")
    if rows and "sequence" in rows[0]:
        for r in rows:
            p, g = pi_gravy(r.get("sequence",""))
            if p: pis.append(p)
            if g: gravys.append(g)
        print(f"  pI:    {stats(pis)}")
        print(f"  GRAVY: {stats(gravys)}")
    else:
        print(f"  Columns available: {list(rows[0].keys()) if rows else 'none'}")

# 2. VHH Master Benchmarks
print("\n=== 2. VHH Master Benchmarks v3 (Clinical VHH) ===")
for fname in ["vhh_master_benchmarks_v3.csv", "vhh_master_benchmarks_v1.csv"]:
    fp = ROOT / "data" / fname
    if fp.exists():
        vhh_rows = list(csv.DictReader(fp.open(encoding="utf-8")))
        print(f"  File: {fname}  n={len(vhh_rows)}")
        print(f"  Columns: {list(vhh_rows[0].keys())[:15]}")
        pis, gravys, deltas, rgs = [], [], [], []
        for r in vhh_rows:
            for col in ["pI","pi","isoelectric_point","calc_pi"]:
                v = r.get(col)
                if v:
                    try: pis.append(float(v))
                    except: pass
                    break
            for col in ["GRAVY","gravy","grand_avg_hydro"]:
                v = r.get(col)
                if v:
                    try: gravys.append(float(v))
                    except: pass
                    break
            for col in ["abnativ_delta","abnativ_d","delta_abnativ"]:
                v = r.get(col)
                if v:
                    try: deltas.append(float(v))
                    except: pass
                    break
            for col in ["cdr3_compactness","rg","cdr3_rg","compactness"]:
                v = r.get(col)
                if v:
                    try: rgs.append(float(v))
                    except: pass
                    break
        if pis:   print(f"  pI:         {stats(pis)}")
        if gravys: print(f"  GRAVY:      {stats(gravys)}")
        if deltas: print(f"  AbNatiV Δ:  {stats(deltas)}")
        if rgs:   print(f"  CDR3 Rg:    {stats(rgs)}")
        break

# 3. VHH sequences
print("\n=== 3. VHH Master Sequence List ===")
vhh_seq_f = ROOT / "data/vhh_master_seq_list.csv"
if vhh_seq_f.exists():
    vrows = list(csv.DictReader(vhh_seq_f.open(encoding="utf-8")))
    print(f"  n={len(vrows)}  cols={list(vrows[0].keys())[:10]}")
    pis2 = []
    for r in vrows:
        seq = r.get("sequence") or r.get("aa_sequence") or r.get("vh_seq")
        if seq:
            p, _ = pi_gravy(seq)
            if p: pis2.append(p)
    if pis2:
        print(f"  pI: {stats(pis2)}")

# 4. AbNatiV threshold documentation
print("\n=== 4. AbNatiV Threshold Source (abenginecore_registry.json) ===")
reg = json.loads((ROOT / "config/abenginecore_registry.json").read_text())
for k, v in reg.items():
    if "abnativ" in k.lower() or "naturalness" in k.lower() or "threshold" in k.lower():
        print(f"  {k}: {v}")

# Also check tier_system_config.json
print("\n=== 5. tier_system_config.json (VHH thresholds) ===")
ts = json.loads((ROOT / "config/tier_system_config.json").read_text())
for k, v in ts.items():
    if isinstance(v, dict) and ("pi" in str(v).lower() or "abnativ" in str(v).lower() or "threshold" in str(v).lower()):
        print(f"  {k}: {v}")
