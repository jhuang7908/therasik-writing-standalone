import pandas as pd
import numpy as np
import sys
from scipy.stats import spearmanr, pearsonr

sys.path.insert(0, ".")
from core.immunogenicity.ada_risk_scorer import ADAScorer

df = pd.read_csv("data/immunogenicity_panel_136_master.csv")
df = df[df["evidence_tier"].isin(["A", "B"])].dropna(subset=["ada_first_pct"])

scorer = ADAScorer()

scores_base = []
scores_auto = []

for _, row in df.iterrows():
    if pd.isna(row.get("vh_identity_842")) or pd.isna(row.get("immuno_n_high")):
        continue

    common = dict(
        mhc_result={
            "summary": {"n_high": int(row.get("immuno_n_high", 0))},
            "n_clusters": int(row.get("immuno_n_clusters", 0)),
        },
        surf_result={
            "frac_exposed_vh": row.get("surf_frac_exposed_vh"),
            "n_hydrophilic_patches": int(row.get("surf_n_patches", 0)),
        },
        germline_identity_vh=row.get("vh_identity_842"),
        germline_identity_vl=row.get("vl_identity_842"),
        interface_n_pairs=row.get("interface_n_pairs"),
        instability_index=row.get("instability_index"),
        hydro_patch_max9=row.get("hydro_patch_max9"),
        origin=str(row.get("origin", "engineered")),
    )
    scores_base.append(scorer.score(**common)["clinical_ada_score"])
    scores_auto.append(
        scorer.score(
            **common,
            targets=row.get("targets"),
            fc_isotype=row.get("fc_isotype"),
            format_type=row.get("format_type"),
            modality=row.get("modality"),
        )["clinical_ada_score"]
    )

valid = df.dropna(subset=["vh_identity_842", "immuno_n_high"]).copy()
y = valid["ada_first_pct"].values.astype(float)
y_log = np.log1p(y)

rho_base, p_base = spearmanr(scores_base, y)
r_base, rp_base = pearsonr(scores_base, y_log)
rho_auto, p_auto = spearmanr(scores_auto, y)
r_auto, rp_auto = pearsonr(scores_auto, y_log)

print("=== AUTO-PROFILE VS FIXED-PARAM COMPARISON ===")
print(f"n = {len(y)}")
print()
print(f"Fixed V2  Spearman rho = {rho_base:+.3f}  p={p_base:.4f}")
print(f"Fixed V2  Pearson  r   = {r_base:+.3f}  p={rp_base:.4f}  (log ADA)")
print()
print(f"Auto V2   Spearman rho = {rho_auto:+.3f}  p={p_auto:.4f}")
print(f"Auto V2   Pearson  r   = {r_auto:+.3f}  p={rp_auto:.4f}  (log ADA)")
print()
print(f"Delta Spearman = {rho_auto - rho_base:+.3f}")
print(f"Delta Pearson  = {r_auto - r_base:+.3f}")

valid["score_auto"] = scores_auto
valid["disease"] = [
    scorer.score(
        **dict(
            mhc_result={
                "summary": {"n_high": int(row.get("immuno_n_high", 0))},
                "n_clusters": int(row.get("immuno_n_clusters", 0)),
            },
            surf_result={
                "frac_exposed_vh": row.get("surf_frac_exposed_vh"),
                "n_hydrophilic_patches": int(row.get("surf_n_patches", 0)),
            },
            germline_identity_vh=row.get("vh_identity_842"),
            germline_identity_vl=row.get("vl_identity_842"),
            interface_n_pairs=row.get("interface_n_pairs"),
            instability_index=row.get("instability_index"),
            hydro_patch_max9=row.get("hydro_patch_max9"),
            origin=str(row.get("origin", "engineered")),
            targets=row.get("targets"),
            fc_isotype=row.get("fc_isotype"),
            format_type=row.get("format_type"),
            modality=row.get("modality"),
        )
    )["profile"]["disease_class"]
    for _, row in valid.iterrows()
]

print()
print("By inferred disease class:")
for cls in sorted(valid["disease"].dropna().unique()):
    sub = valid[valid["disease"] == cls]
    if len(sub) < 8:
        continue
    rho, p = spearmanr(sub["score_auto"], sub["ada_first_pct"])
    r, pp = pearsonr(sub["score_auto"], np.log1p(sub["ada_first_pct"]))
    print(f"  {cls:12} n={len(sub):3}  rho={rho:+.3f} p={p:.4f}  r={r:+.3f} p={pp:.4f}")
