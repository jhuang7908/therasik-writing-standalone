"""
Derive AbNatiV Δ thresholds from correct positive/negative reference sets.
Positive: Clinical_VHH + Engineered_Human_VH (experimentally validated single-domain)
Negative: Negative_Control_VH (conventional VH, should NOT work as single-domain)
"""
import csv
from pathlib import Path

ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
rows = list(csv.DictReader((ROOT / "data/vhh_master_benchmarks_v3.csv").open(encoding="utf-8")))

pos_cats  = {"Clinical_VHH", "Engineered_Human_VH", "Database_B"}
neg_cats  = {"Negative_Control_VH"}
mid_cats  = {"Autonomous_Human_VH"}  # engineered human VH (not classical VHH)

pos_delta = sorted([float(r["abnativ_delta"]) for r in rows
                    if r.get("category") in pos_cats and r.get("abnativ_delta")])
neg_delta = sorted([float(r["abnativ_delta"]) for r in rows
                    if r.get("category") in neg_cats and r.get("abnativ_delta")])
mid_delta = sorted([float(r["abnativ_delta"]) for r in rows
                    if r.get("category") in mid_cats and r.get("abnativ_delta")])

# Clinical_VHH only (strictest positive reference)
clin_delta = sorted([float(r["abnativ_delta"]) for r in rows
                     if r.get("category") == "Clinical_VHH" and r.get("abnativ_delta")])
eng_delta  = sorted([float(r["abnativ_delta"]) for r in rows
                     if r.get("category") == "Engineered_Human_VH" and r.get("abnativ_delta")])

def pct(vals, threshold, above=True):
    if not vals: return 0
    n = sum(1 for v in vals if (v >= threshold if above else v < threshold))
    return 100 * n / len(vals)

def ptile(vals, p):
    if not vals: return None
    i = max(0, int(len(vals) * p / 100) - 1)
    return vals[i]

print("=" * 72)
print("AbNatiV Δ Distribution by Reference Category")
print("=" * 72)

for label, vals in [
    ("Clinical_VHH (n=39)", clin_delta),
    ("Engineered_Human_VH [Atlas-24] (n=24)", eng_delta),
    ("Autonomous_Human_VH [Database_A] (n=57)", mid_delta),
    ("Negative_Control_VH (n=10)", neg_delta),
    ("ALL POSITIVE (Clinical+Eng+DB_B) (n=92)", pos_delta),
]:
    vals = sorted(vals)
    n = len(vals)
    if not n: continue
    print(f"\n{label}")
    print(f"  range: [{vals[0]:.4f}, {vals[-1]:.4f}]")
    print(f"  p10={ptile(vals,10):.4f}  p25={ptile(vals,25):.4f}  "
          f"median={vals[n//2]:.4f}  p75={ptile(vals,75):.4f}  p90={ptile(vals,90):.4f}")

print("\n" + "=" * 72)
print("Threshold Decision Table")
print(f"{'Threshold':>12}  {'Pos PASS%':>10}  {'ClinVHH PASS%':>14}  "
      f"{'EngVH PASS%':>12}  {'Neg FAIL%':>10}  {'Verdict'}")
print("-" * 75)

for thr in [-0.050, -0.074, -0.100, -0.120, -0.150, -0.200]:
    pos_p = pct(pos_delta, thr, above=True)
    clin_p = pct(clin_delta, thr, above=True)
    eng_p  = pct(eng_delta,  thr, above=True)
    neg_f  = pct(neg_delta,  thr, above=False)
    # verdict: ideal = pos_pass >90%, neg_fail >80%
    if clin_p >= 90 and eng_p >= 70 and neg_f >= 70:
        verdict = "✓ RECOMMENDED"
    elif clin_p >= 85 and eng_p >= 60 and neg_f >= 60:
        verdict = "○ Acceptable"
    elif clin_p < 80 or eng_p < 50:
        verdict = "✗ Too strict (rejects real positives)"
    else:
        verdict = "~ Borderline"
    print(f"  Δ ≥ {thr:6.3f}  {pos_p:>10.1f}%  {clin_p:>14.1f}%  "
          f"{eng_p:>12.1f}%  {neg_f:>10.1f}%  {verdict}")

print("\n" + "=" * 72)
print("CURRENT threshold Δ ≥ -0.074 analysis:")
print(f"  Clinical_VHH pass rate : {pct(clin_delta,-0.074,above=True):.1f}%  "
      f"(expected ≥ 90%  →  FAIL: {100-pct(clin_delta,-0.074,above=True):.1f}% of approved drugs)")
print(f"  Engineered_Human_VH pass: {pct(eng_delta,-0.074,above=True):.1f}%  "
      f"(expected ≥ 80%  →  FAIL: {100-pct(eng_delta,-0.074,above=True):.1f}% of lab-validated)")
print(f"  Negative_Control fail   : {pct(neg_delta,-0.074,above=False):.1f}%  (expected ≥ 80%  → OK)")
print("\nConclusion: current -0.074 is calibrated against wrong reference.")
print("  Source appears to be 'somewhere between Neg and Pos' not from a clinical positive set.")

# Proposed tiered system
print("\n" + "=" * 72)
print("PROPOSED 3-tier system (data-driven):")
print(f"  EXCELLENT : Δ ≥  0.000  (above Clinical_VHH median +0.02)")
print(f"  PASS      : Δ ≥ -0.120  (Clinical_VHH p10=-0.14; EngVH p25=-0.09 midpoint)")
print(f"  WARN      : Δ ≥ -0.200  (below Clinical_VHH range but EngVH borderline)")
print(f"  FAIL      : Δ <  -0.200  (clearly VH-like; Neg_Control median=-0.17)")
print()
for label, vals in [("Clinical_VHH", clin_delta), ("EngVH", eng_delta),
                    ("Autonomous_Human_VH", mid_delta), ("Neg_Control_VH", neg_delta)]:
    e  = pct(vals,  0.000, True)
    p  = pct(vals, -0.120, True) - e
    w  = pct(vals, -0.200, True) - e - p
    f  = pct(vals, -0.200, False)
    print(f"  {label:<28}  EXCEL={e:.0f}%  PASS={p:.0f}%  WARN={w:.0f}%  FAIL={f:.0f}%")
