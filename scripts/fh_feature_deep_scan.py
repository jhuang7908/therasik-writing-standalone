"""
FH Feature Deep Scan
═══════════════════════════════════════════════════════════════════════════
Scan ALL numeric columns in ada_master_136_curated.csv for FH antibodies,
rank by |Spearman ρ| with clinical ADA, and test multi-feature composites.
"""
import sys, warnings
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
from scipy.optimize import differential_evolution
from itertools import combinations

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CSV = ROOT / "data" / "immunogenicity_knowledge_base" / "master" / "ada_master_136_curated.csv"

df = pd.read_csv(CSV)
df["ada_first_pct"] = pd.to_numeric(df["ada_first_pct"], errors="coerce")
fh = df[df["origin"] == "natural"].copy()
fh_ada = fh["ada_first_pct"]
print(f"FH antibodies with ADA data: {fh_ada.dropna().shape[0]} / {len(fh)}")

# ═══════════════════════════════════════════════════════════════════════════
#  PART 1: Individual feature correlations (all numeric columns)
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 72)
print("  PART 1: Individual Feature Correlations (FH only)")
print("═" * 72)

skip_cols = {"ada_first_pct", "ada_v2_score", "ada_v2_risk", "ada_v2_track",
             "ada_value_display", "approval_year"}
results = []
for col in fh.columns:
    if col in skip_cols:
        continue
    vals = pd.to_numeric(fh[col], errors="coerce")
    valid = pd.DataFrame({"x": vals, "y": fh_ada}).dropna()
    if len(valid) < 15:
        continue
    rho, p = stats.spearmanr(valid["x"], valid["y"])
    results.append({"feature": col, "rho": rho, "abs_rho": abs(rho),
                    "p": p, "n": len(valid),
                    "direction": "+" if rho > 0 else "-"})

res_df = pd.DataFrame(results).sort_values("abs_rho", ascending=False)
print(f"\n{'Rank':<5} {'Feature':<40} {'ρ':>8} {'|ρ|':>6} {'p':>8} {'n':>4}")
print("─" * 75)
for i, row in enumerate(res_df.head(30).itertuples(), 1):
    sig = "***" if row.p < 0.01 else ("**" if row.p < 0.05 else ("*" if row.p < 0.10 else ""))
    print(f"{i:<5} {row.feature:<40} {row.rho:>+8.4f} {row.abs_rho:>6.4f} {row.p:>8.4f} {row.n:>4} {sig}")

# ═══════════════════════════════════════════════════════════════════════════
#  PART 2: Feature pairs — which combinations have the best joint signal?
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 72)
print("  PART 2: Best Feature Pairs (simple weighted average, FH)")
print("═" * 72)

top_features = res_df.head(15)["feature"].tolist()
pair_results = []
for f1, f2 in combinations(top_features, 2):
    v1 = pd.to_numeric(fh[f1], errors="coerce")
    v2 = pd.to_numeric(fh[f2], errors="coerce")
    valid = pd.DataFrame({"x1": v1, "x2": v2, "y": fh_ada}).dropna()
    if len(valid) < 15:
        continue
    # Normalise to [0,1] range
    x1n = (valid["x1"] - valid["x1"].min()) / (valid["x1"].max() - valid["x1"].min() + 1e-9)
    x2n = (valid["x2"] - valid["x2"].min()) / (valid["x2"].max() - valid["x2"].min() + 1e-9)
    # Check both features for sign direction (flip if negative corr)
    r1, _ = stats.spearmanr(valid["x1"], valid["y"])
    r2, _ = stats.spearmanr(valid["x2"], valid["y"])
    if r1 < 0: x1n = 1 - x1n
    if r2 < 0: x2n = 1 - x2n
    # Test equal-weight combination
    combo = 0.5 * x1n + 0.5 * x2n
    rho, p = stats.spearmanr(combo, valid["y"])
    pair_results.append({"f1": f1, "f2": f2, "rho": rho, "p": p, "n": len(valid)})

pair_df = pd.DataFrame(pair_results).sort_values("rho", ascending=False)
print(f"\n{'Rank':<5} {'Feature 1':<30} {'Feature 2':<30} {'ρ':>8} {'p':>8}")
print("─" * 90)
for i, row in enumerate(pair_df.head(15).itertuples(), 1):
    sig = "**" if row.p < 0.05 else ("*" if row.p < 0.10 else "")
    print(f"{i:<5} {row.f1:<30} {row.f2:<30} {row.rho:>+8.4f} {row.p:>8.4f} {sig}")

# ═══════════════════════════════════════════════════════════════════════════
#  PART 3: Exhaustive weight optimisation with top-N features
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 72)
print("  PART 3: Weight Optimisation (differential evolution)")
print("═" * 72)

# Select top features with |rho| > 0.15 and n >= 30
candidates = res_df[(res_df["abs_rho"] >= 0.15) & (res_df["n"] >= 30)].head(10)
print(f"\nCandidate features for optimisation (n={len(candidates)}):")
for _, r in candidates.iterrows():
    print(f"  {r['feature']:<40} ρ={r['rho']:+.4f}  p={r['p']:.4f}")

feat_names = candidates["feature"].tolist()
feat_signs = [1.0 if r > 0 else -1.0 for r in candidates["rho"].values]

# Build feature matrix
fh_opt = fh[feat_names + ["ada_first_pct"]].dropna()
X_raw = fh_opt[feat_names].values.astype(float)
y = fh_opt["ada_first_pct"].values.astype(float)

# Normalise each column to [0,1]
X_min = X_raw.min(axis=0)
X_max = X_raw.max(axis=0)
X = (X_raw - X_min) / (X_max - X_min + 1e-9)
# Flip sign for negative-correlation features
for i, s in enumerate(feat_signs):
    if s < 0:
        X[:, i] = 1 - X[:, i]

n_feat = len(feat_names)
print(f"\nOptimising {n_feat} features over {len(y)} FH antibodies...")

def neg_spearman(weights):
    w = np.array(weights)
    w = w / (w.sum() + 1e-9)
    composite = X @ w
    rho, _ = stats.spearmanr(composite, y)
    return -rho  # minimise negative ρ

bounds = [(0.0, 1.0)] * n_feat
result = differential_evolution(neg_spearman, bounds, seed=42,
                                maxiter=2000, tol=1e-8, popsize=30)
best_w = np.array(result.x)
best_w = best_w / (best_w.sum() + 1e-9)
best_composite = X @ best_w
best_rho, best_p = stats.spearmanr(best_composite, y)

print(f"\nOptimal Spearman ρ = {best_rho:+.4f}  (p = {best_p:.6f})")
print(f"\nOptimal weights:")
for name, w, s in sorted(zip(feat_names, best_w, feat_signs),
                         key=lambda x: -x[1]):
    direction = "(+)" if s > 0 else "(-inverted)"
    if w > 0.01:
        print(f"  {name:<40} w={w:.4f}  {direction}")

# ═══════════════════════════════════════════════════════════════════════════
#  PART 4: Leave-one-out cross-validation of optimised composite
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 72)
print("  PART 4: Leave-One-Out Cross-Validation")
print("═" * 72)

from scipy.optimize import minimize

loo_predictions = np.zeros(len(y))
for i in range(len(y)):
    X_train = np.delete(X, i, axis=0)
    y_train = np.delete(y, i)
    def neg_sp_loo(weights):
        w = np.array(weights)
        w = w / (w.sum() + 1e-9)
        c = X_train @ w
        rho, _ = stats.spearmanr(c, y_train)
        return -rho
    res_loo = minimize(neg_sp_loo, best_w, method="Nelder-Mead",
                       options={"maxiter": 500})
    w_loo = np.array(res_loo.x)
    w_loo = np.clip(w_loo, 0, None)
    w_loo = w_loo / (w_loo.sum() + 1e-9)
    loo_predictions[i] = X[i] @ w_loo

loo_rho, loo_p = stats.spearmanr(loo_predictions, y)
print(f"LOO-CV Spearman ρ = {loo_rho:+.4f}  (p = {loo_p:.6f})")
print(f"  (vs in-sample ρ = {best_rho:+.4f})")
print(f"  Shrinkage: {best_rho - loo_rho:.4f}")

# ═══════════════════════════════════════════════════════════════════════════
#  PART 5: Compare with current ADA V2 FH score
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 72)
print("  PART 5: Current ADA V2 vs Optimised")
print("═" * 72)

curr_v2 = fh_opt.merge(fh[["antibody_name","ada_v2_score"]],
                        left_index=True, right_index=True, how="left")
v2_valid = curr_v2[["ada_v2_score","ada_first_pct"]].dropna()
curr_rho, curr_p = stats.spearmanr(v2_valid["ada_v2_score"], v2_valid["ada_first_pct"])
print(f"  Current ADA V2 FH:  ρ = {curr_rho:+.4f}  p = {curr_p:.4f}")
print(f"  Optimised (in-sample): ρ = {best_rho:+.4f}  p = {best_p:.6f}")
print(f"  Optimised (LOO-CV):    ρ = {loo_rho:+.4f}  p = {loo_p:.6f}")
print(f"  Improvement (LOO):     Δρ = {loo_rho - curr_rho:+.4f}")

# ═══════════════════════════════════════════════════════════════════════════
#  PART 6: Check impact on HU and ALL when replacing FH scores
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 72)
print("  PART 6: Impact on ALL panel if FH scores replaced")
print("═" * 72)

# Simulate: replace FH ada_v2_score with optimised, keep HU unchanged
df_sim = df.copy()
fh_idx = fh_opt.index
df_sim.loc[fh_idx, "ada_v2_score_new"] = best_composite
# For non-FH, keep original
df_sim.loc[~df_sim.index.isin(fh_idx), "ada_v2_score_new"] = df_sim.loc[
    ~df_sim.index.isin(fh_idx), "ada_v2_score"]

for label, sub in [("ALL", df_sim), ("FH", df_sim[df_sim["origin"]=="natural"]),
                   ("HU", df_sim[df_sim["origin"]=="engineered"])]:
    v = sub[["ada_v2_score_new","ada_first_pct"]].dropna()
    if len(v) < 5:
        continue
    rho, p = stats.spearmanr(v["ada_v2_score_new"], v["ada_first_pct"])
    print(f"  {label:4s}: n={len(v):3d}  ρ={rho:+.4f}  p={p:.4f}")

print("\n" + "═" * 72)
print("  DONE")
print("═" * 72)
