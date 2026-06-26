"""
FH Feature Scan — Lightweight version (no LOO, fast)
"""
import sys, warnings, math
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CSV = ROOT / "data" / "immunogenicity_knowledge_base" / "master" / "ada_master_136_curated.csv"

df = pd.read_csv(CSV)
df["ada_first_pct"] = pd.to_numeric(df["ada_first_pct"], errors="coerce")
fh = df[df["origin"] == "natural"].copy()
fh_ada = fh["ada_first_pct"]
print(f"FH n={fh_ada.dropna().shape[0]}")

# ── PART 1: All feature correlations ──────────────────────────────────────
print("\n=== PART 1: Individual Feature Correlations (FH) ===")
skip = {"ada_first_pct","ada_v2_score","ada_v2_risk","ada_v2_track","ada_value_display","approval_year"}
results = []
for col in fh.columns:
    if col in skip: continue
    vals = pd.to_numeric(fh[col], errors="coerce")
    valid = pd.DataFrame({"x": vals, "y": fh_ada}).dropna()
    if len(valid) < 15: continue
    rho, p = stats.spearmanr(valid["x"], valid["y"])
    results.append({"feature": col, "rho": rho, "abs_rho": abs(rho), "p": p, "n": len(valid)})

res_df = pd.DataFrame(results).sort_values("abs_rho", ascending=False)
print(f"\n{'Rk':<4} {'Feature':<45} {'rho':>7} {'|rho|':>6} {'p':>8} {'n':>4}")
print("-" * 80)
for i, r in enumerate(res_df.head(35).itertuples(), 1):
    sig = "***" if r.p < 0.01 else ("**" if r.p < 0.05 else ("*" if r.p < 0.10 else ""))
    print(f"{i:<4} {r.feature:<45} {r.rho:>+7.4f} {r.abs_rho:>6.4f} {r.p:>8.4f} {r.n:>4} {sig}")

# ── PART 2: Grid search over top features ────────────────────────────────
print("\n=== PART 2: Grid Search Weight Optimisation ===")
top = res_df[(res_df["abs_rho"] >= 0.12) & (res_df["n"] >= 30)].head(8)
feat_names = top["feature"].tolist()
feat_rhos  = top["rho"].values

print(f"Using {len(feat_names)} features:")
for n, r in zip(feat_names, feat_rhos):
    print(f"  {n:<45} rho={r:+.4f}")

fh_opt = fh[feat_names + ["ada_first_pct"]].dropna()
X_raw = fh_opt[feat_names].values.astype(float)
y = fh_opt["ada_first_pct"].values.astype(float)
print(f"Samples with complete data: {len(y)}")

# Normalise [0,1], flip negative-corr features
X_min, X_max = X_raw.min(0), X_raw.max(0)
X = (X_raw - X_min) / (X_max - X_min + 1e-9)
for i, r in enumerate(feat_rhos):
    if r < 0:
        X[:, i] = 1 - X[:, i]

# Grid search: sample 200k random weight vectors
rng = np.random.default_rng(42)
n_trials = 200000
best_rho_val = -1
best_w = None
for _ in range(n_trials):
    w = rng.dirichlet(np.ones(len(feat_names)))
    composite = X @ w
    rho, _ = stats.spearmanr(composite, y)
    if rho > best_rho_val:
        best_rho_val = rho
        best_w = w.copy()

best_rho, best_p = stats.spearmanr(X @ best_w, y)
print(f"\nBest grid-search: rho={best_rho:+.4f}  p={best_p:.6f}")
print("Weights:")
for n, w in sorted(zip(feat_names, best_w), key=lambda x: -x[1]):
    if w > 0.01:
        print(f"  {n:<45} w={w:.4f}")

# ── PART 3: Bootstrap validation ─────────────────────────────────────────
print("\n=== PART 3: Bootstrap Stability (1000 resamples) ===")
n_boot = 1000
boot_rhos = []
for _ in range(n_boot):
    idx = rng.integers(0, len(y), size=len(y))
    comp = X[idx] @ best_w
    rho, _ = stats.spearmanr(comp, y[idx])
    boot_rhos.append(rho)

boot_rhos = np.array(boot_rhos)
ci_lo, ci_hi = np.percentile(boot_rhos, [2.5, 97.5])
print(f"  Bootstrap rho: {boot_rhos.mean():+.4f} ± {boot_rhos.std():.4f}")
print(f"  95% CI: [{ci_lo:+.4f}, {ci_hi:+.4f}]")

# ── PART 4: Compare current V2 ──────────────────────────────────────────
print("\n=== PART 4: Current V2 vs Optimised ===")
fh_v2 = fh[["ada_v2_score","ada_first_pct"]].dropna()
curr_rho, curr_p = stats.spearmanr(fh_v2["ada_v2_score"], fh_v2["ada_first_pct"])
print(f"  Current V2:       rho={curr_rho:+.4f}  p={curr_p:.4f}  n={len(fh_v2)}")
print(f"  Optimised:        rho={best_rho:+.4f}  p={best_p:.6f}  n={len(y)}")
delta = best_rho - curr_rho
print(f"  Improvement:      +{delta:.4f}")

# ── PART 5: Which new features matter most? ──────────────────────────────
print("\n=== PART 5: Ablation Study (drop one feature at a time) ===")
base_rho = best_rho
for i, name in enumerate(feat_names):
    w_drop = best_w.copy()
    w_drop[i] = 0
    w_drop = w_drop / (w_drop.sum() + 1e-9)
    comp = X @ w_drop
    rho, _ = stats.spearmanr(comp, y)
    drop = base_rho - rho
    print(f"  Drop {name:<40} rho={rho:+.4f}  drop={drop:+.4f}")

print("\nDONE")
