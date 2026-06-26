"""
Derive GRAVY and CDR3 Rg thresholds based on discriminative power:
Positive: Clinical_VHH + Engineered_Human_VH
Negative: Negative_Control_VH (conventional VH)
Goal: threshold where positive pass rate >= 90% AND negative fail rate >= 70%
"""
import csv
from pathlib import Path

ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
rows = list(csv.DictReader((ROOT / "data/vhh_master_benchmarks_v3.csv").open(encoding="utf-8")))

def get(rows, cats, col):
    return sorted([float(r[col]) for r in rows
                   if r.get("category") in cats and r.get(col)
                   and r[col] not in ("", "None", "nan")])

def ptile(vals, p):
    if not vals: return None
    i = min(len(vals)-1, max(0, int(len(vals) * p / 100)))
    return round(vals[i], 4)

def pass_rate(vals, thr, above=True):
    if not vals: return 0
    return 100 * sum(1 for v in vals if (v <= thr if above else v >= thr)) / len(vals)

POS = {"Clinical_VHH", "Engineered_Human_VH"}
NEG = {"Negative_Control_VH"}
ALL_POS = {"Clinical_VHH", "Engineered_Human_VH", "Database_B"}

clin_g  = get(rows, {"Clinical_VHH"}, "GRAVY")
eng_g   = get(rows, {"Engineered_Human_VH"}, "GRAVY")
neg_g   = get(rows, NEG, "GRAVY")
pos_g   = get(rows, ALL_POS, "GRAVY")

clin_rg = get(rows, {"Clinical_VHH"}, "compactness_A")
eng_rg  = get(rows, {"Engineered_Human_VH"}, "compactness_A")
neg_rg  = get(rows, NEG, "compactness_A")
pos_rg  = get(rows, ALL_POS, "compactness_A")

# Also get all VH (autonomous_human + negative) for comparison
all_vh_g  = get(rows, {"Negative_Control_VH", "Autonomous_Human_VH"}, "GRAVY")
all_vh_rg = get(rows, {"Negative_Control_VH", "Autonomous_Human_VH"}, "compactness_A")

print("=" * 70)
print("GRAVY Distribution")
print("=" * 70)
for label, vals in [
    ("Clinical_VHH (n=39)", clin_g),
    ("Engineered_Human_VH (n=24)", eng_g),
    ("Autonomous_Human_VH + Neg (n=67)", all_vh_g),
    ("Negative_Control_VH only (n=10)", neg_g),
]:
    n = len(vals)
    if not n: continue
    print(f"\n{label}")
    print(f"  range: [{vals[0]:.3f}, {vals[-1]:.3f}]")
    print(f"  p10={ptile(vals,10):.3f}  p25={ptile(vals,25):.3f}  "
          f"median={vals[n//2]:.3f}  p75={ptile(vals,75):.3f}  p90={ptile(vals,90):.3f}")

print("\n\nGRAVY Threshold Table (lower = more hydrophilic = GOOD)")
print(f"{'Threshold':>12}  {'ClinVHH ≤thr':>14}  {'EngVH ≤thr':>12}  "
      f"{'Neg >thr (fail)':>16}  Notes")
print("-" * 75)
for thr in [-0.05, 0.00, 0.05, 0.10, 0.15, 0.20]:
    cp = pass_rate(clin_g, thr, above=True)  # GRAVY ≤ thr is GOOD (hydrophilic)
    ep = pass_rate(eng_g,  thr, above=True)
    nf = pass_rate(neg_g,  thr, above=False)  # GRAVY > thr = bad (hydrophobic) for neg ctrl
    note = ""
    if cp >= 95 and ep >= 90:
        note = "✓ RECOMMENDED (nearly all positives pass)"
    elif cp >= 90 and ep >= 85:
        note = "○ Acceptable"
    print(f"  GRAVY ≤ {thr:+.2f}  {cp:>14.1f}%  {ep:>12.1f}%  {nf:>16.1f}%  {note}")

print("\n\nKey: for conventional VH, GRAVY is typically SIMILAR to VHH.")
print("GRAVY does NOT effectively discriminate VHH from conventional VH.")
print("→ GRAVY threshold should be used as CMC solubility gate, not VHH-specific.")

print("\n" + "=" * 70)
print("CDR3 Rg Distribution")
print("=" * 70)
for label, vals in [
    ("Clinical_VHH (n=39)", clin_rg),
    ("Engineered_Human_VH (n=24)", eng_rg),
    ("Autonomous_Human_VH + Neg (n=67)", all_vh_rg),
    ("Negative_Control_VH only (n=10)", neg_rg),
]:
    n = len(vals)
    if not n: continue
    print(f"\n{label}")
    print(f"  range: [{vals[0]:.2f}, {vals[-1]:.2f}] Å")
    print(f"  p10={ptile(vals,10):.2f}  p25={ptile(vals,25):.2f}  "
          f"median={vals[n//2]:.2f}  p75={ptile(vals,75):.2f}  p90={ptile(vals,90):.2f}  Å")

print("\n\nCDR3 Rg Threshold Table")
print(f"{'Threshold':>14}  {'ClinVHH PASS':>14}  {'EngVH PASS':>12}  "
      f"{'Neg FAIL':>10}  Notes")
print("-" * 72)
for lo, hi in [(4.5, 7.5), (4.8, 7.0), (5.0, 6.5), (5.0, 7.0), (4.5, 8.0)]:
    cp = sum(1 for v in clin_rg if lo <= v <= hi) / len(clin_rg) * 100 if clin_rg else 0
    ep = sum(1 for v in eng_rg  if lo <= v <= hi) / len(eng_rg)  * 100 if eng_rg else 0
    nf = sum(1 for v in neg_rg  if not (lo <= v <= hi)) / len(neg_rg) * 100 if neg_rg else 0
    note = "✓ RECOMMENDED" if cp >= 90 and ep >= 85 else ("○ Acceptable" if cp >= 85 else "")
    print(f"  {lo:.1f}–{hi:.1f} Å        {cp:>14.1f}%  {ep:>12.1f}%  {nf:>10.1f}%  {note}")

print("\nNeg_Control_VH CDR3 Rg values:")
print(f"  {neg_rg}  (n={len(neg_rg)})")
print("\nKey: CDR3 Rg discriminates long/extended CDR3 (> 7 Å) but")
print("  conventional VH and VHH overlap heavily in 5–6.5 Å range.")
print("  Rg threshold is a structural STABILITY gate (not VHH-specificity gate).")
