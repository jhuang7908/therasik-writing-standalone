"""
Re-apply updated ADA V2 scorer (dual-track FH/HU) to ada_master_136_curated.csv.
Updates ada_v2_score and ada_v2_risk in place.
"""
import sys, numpy as np, pandas as pd
from pathlib import Path
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.immunogenicity.ada_risk_scorer import ADAScorer

ROOT     = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "immunogenicity_knowledge_base" / "master" / "ada_master_136_curated.csv"

df = pd.read_csv(CSV_PATH)
df["ada_first_pct"] = pd.to_numeric(df["ada_first_pct"], errors="coerce")

scorer = ADAScorer()
scores, risks, tracks = [], [], []

for _, row in df.iterrows():
    try:
        res = scorer.score(
            mhc_result  = {"summary": {"n_high": int(row.get("immuno_n_high") or 0)},
                           "n_clusters": int(row.get("immuno_n_clusters") or 0)},
            surf_result = {"frac_exposed_vh": row.get("surf_frac_exposed_vh"),
                           "n_hydrophilic_patches": int(row.get("surf_n_patches") or 0)},
            germline_identity_vh = row.get("vh_germline_identity"),
            germline_identity_vl = row.get("vl_germline_identity"),
            interface_n_pairs    = row.get("interface_n_pairs"),
            instability_index    = row.get("instability_index"),
            hydro_patch_max9     = row.get("hydro_patch_max9"),
            origin               = str(row.get("origin", "engineered")),
            targets              = row.get("targets"),
            fc_isotype           = row.get("fc_isotype"),
        )
        scores.append(res["clinical_ada_score"])
        risks.append(res["clinical_ada_risk"])
        tracks.append(res.get("track", "?"))
    except Exception as e:
        scores.append(np.nan)
        risks.append("UNKNOWN")
        tracks.append("?")

df["ada_v2_score"] = scores
df["ada_v2_risk"]  = risks
df["ada_v2_track"] = tracks
df.to_csv(CSV_PATH, index=False, encoding="utf-8")
print(f"Saved {CSV_PATH.name}  (n={len(df)})")

# ── Validation ─────────────────────────────────────────────────────────────
df["origin_class"] = "Other"
df.loc[df["origin"] == "natural",    "origin_class"] = "FH"
df.loc[df["origin"] == "engineered", "origin_class"] = "HU"

print("\nSpearman correlations (ada_v2_score vs clinical ADA):")
for label, sub in [("ALL", df), ("FH", df[df["origin_class"]=="FH"]), ("HU", df[df["origin_class"]=="HU"])]:
    v = sub[["ada_v2_score","ada_first_pct"]].dropna()
    rho, p = stats.spearmanr(v["ada_v2_score"], v["ada_first_pct"])
    print(f"  {label:4s}: n={len(v):3d}  rho={rho:+.4f}  p={p:.4f}")

print("\nFH individual factors (for comparison):")
fh = df[df["origin_class"]=="FH"]
for col, label in [("interface_n_pairs","Interface (I)"),("vl_germline_identity","VL identity (raw)"),
                   ("surf_n_patches","Surface patches"),("immuno_n_high","MHC-II epitopes")]:
    v = fh[[col,"ada_first_pct"]].dropna()
    rho, p = stats.spearmanr(v[col], v["ada_first_pct"])
    print(f"  {label:25s}: rho={rho:+.4f}  p={p:.4f}  n={len(v)}")
