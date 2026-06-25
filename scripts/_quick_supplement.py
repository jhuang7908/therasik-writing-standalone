"""Quick supplementary model tests: ALL panel + log-transform."""
import sys, math, numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import spearmanr
from sklearn.linear_model import RidgeCV
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import LeaveOneOut
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')
sys.stdout.reconfigure(line_buffering=True)

# Build combined matrix by executing the setup portion of _optimize_138_model
ROOT = Path(__file__).resolve().parents[1]
code = (ROOT / "scripts/_optimize_138_model.py").read_text(encoding='utf-8')
setup = code.split("# Run exhaustive search")[0] if "# Run exhaustive search" in code else code.split("corr_hu = corr_scan")[0]
exec(setup, globals())

def loo_r(ds, feats, target='ada'):
    need = list(dict.fromkeys([target, 'ada'] + feats))
    sub = ds[need].dropna(subset=[target] + feats)
    if len(sub) < 8:
        return float('nan'), float('nan'), len(sub)
    X = sub[feats].values.astype(float)
    y = sub[target].values.astype(float).ravel()
    y_raw = sub['ada'].values.astype(float).ravel() if target != 'ada' else y
    preds = np.zeros(len(y))
    for tr, te in LeaveOneOut().split(X):
        sc = StandardScaler()
        Xtr = sc.fit_transform(X[tr]); Xte = sc.transform(X[te])
        md = RidgeCV(alphas=[0.01, 0.1, 1, 10, 50, 100, 200]).fit(Xtr, y[tr])
        preds[te] = md.predict(Xte)
    r, p = spearmanr(y_raw, preds)
    return float(r), float(p), len(sub)

def loo_gbr_r(ds, feats, target='ada'):
    need = list(dict.fromkeys([target, 'ada'] + feats))
    sub = ds[need].dropna(subset=[target] + feats)
    if len(sub) < 10:
        return float('nan'), float('nan'), len(sub)
    X = sub[feats].values.astype(float)
    y = sub[target].values.astype(float).ravel()
    y_raw = sub['ada'].values.astype(float).ravel() if target != 'ada' else y
    preds = np.zeros(len(y))
    for tr, te in LeaveOneOut().split(X):
        gb = GradientBoostingRegressor(
            n_estimators=100, max_depth=2, learning_rate=0.04,
            subsample=0.8, random_state=42, min_samples_leaf=4)
        gb.fit(X[tr], y[tr])
        preds[te] = gb.predict(X[te])
    r, p = spearmanr(y_raw, preds)
    return float(r), float(p), len(sub)

sig = lambda p: '**' if p < 0.01 else ('*' if p < 0.05 else ('^' if p < 0.10 else ' '))

TESTS = [
    ('ALL Ridge 3f', c, ['ix_strong_nosupp', 'feat_n_strong_binders', 'feat_vh_identity'], 'ada', 'ridge'),
    ('ALL Ridge 4f', c, ['ix_strong_nosupp', 'feat_vh_identity', 'ix_route_clust', 'feat_origin_code'], 'ada', 'ridge'),
    ('ALL Ridge 5f', c, ['ix_strong_nosupp', 'feat_vh_identity', 'ix_route_clust', 'feat_origin_code', 'ix_clust_nosupp'], 'ada', 'ridge'),
    ('ALL Ridge 6f', c, ['ix_strong_nosupp', 'feat_vh_identity', 'ix_route_clust', 'feat_origin_code', 'feat_immuno_suppression', 'feat_half_life'], 'ada', 'ridge'),
    ('ALL GBR 4f', c, ['ix_strong_nosupp', 'feat_vh_identity', 'ix_route_clust', 'feat_origin_code'], 'ada', 'gbr'),
    ('ALL GBR 5f', c, ['ix_strong_nosupp', 'feat_vh_identity', 'ix_route_clust', 'feat_origin_code', 'feat_immuno_suppression'], 'ada', 'gbr'),
    ('ALL GBR 6f', c, ['ix_strong_nosupp', 'feat_vh_identity', 'ix_route_clust', 'feat_origin_code', 'feat_immuno_suppression', 'feat_half_life'], 'ada', 'gbr'),
    # Log target
    ('HU Ridge log 3f', hu_all, ['feat_immuno_suppression', 'feat_half_life', 'feat_assay_gen'], 'log_ada', 'ridge'),
    ('HU Ridge log 5f', hu_all, ['ix_sup_hl', 'feat_immuno_suppression', 'feat_half_life', 'feat_cdrh3_len', 'feat_n_clusters'], 'log_ada', 'ridge'),
    ('FH Ridge log 3f', fh_all, ['feat_net_burden', 'ix_vh_foreign_burd', 'ix_route_clust'], 'log_ada', 'ridge'),
    ('FH GBR log 4f', fh_all, ['feat_net_burden', 'ix_vh_foreign_burd', 'feat_vh_identity', 'ix_assay_clust'], 'log_ada', 'gbr'),
    ('ALL Ridge log 4f', c, ['ix_strong_nosupp', 'feat_vh_identity', 'ix_route_clust', 'feat_origin_code'], 'log_ada', 'ridge'),
    ('ALL GBR log 5f', c, ['ix_strong_nosupp', 'feat_vh_identity', 'ix_route_clust', 'feat_origin_code', 'feat_immuno_suppression'], 'log_ada', 'gbr'),
    # Baselines on 138
    ('HU-A baseline 138', hu_all, ['feat_immuno_suppression', 'feat_cdrh3_aromaticity', 'feat_immune_depleting', 'feat_half_life'], 'ada', 'ridge'),
    ('FH-A baseline 138', fh_all, ['feat_n_clusters', 'feat_net_burden', 'feat_n_strong_binders'], 'ada', 'ridge'),
    # Best new HU model
    ('HU best 5f (new)', hu_all, ['ix_sup_hl', 'feat_immuno_suppression', 'feat_half_life', 'feat_cdrh3_len', 'feat_n_clusters'], 'ada', 'ridge'),
    ('HU best 4f (new)', hu_all, ['feat_immuno_suppression', 'ix_hl_inv', 'feat_cdrh3_len', 'feat_cdrh3_polar'], 'ada', 'ridge'),
    ('HU best 3f (new)', hu_all, ['feat_immuno_suppression', 'feat_half_life', 'feat_assay_gen'], 'ada', 'ridge'),
    # Best new FH model
    ('FH best Ridge 3f', fh_all, ['ix_assay_burden', 'ix_vh_foreign_burd', 'ix_route_clust'], 'ada', 'ridge'),
    ('FH best GBR 4f', fh_all, ['feat_net_burden', 'ix_vh_foreign_burd', 'feat_vh_identity', 'ix_assay_clust'], 'ada', 'gbr'),
]

print()
print("=" * 95)
print("COMPREHENSIVE 138-PANEL MODEL RESULTS")
print("=" * 95)
hdr = "{:<25s} {:>8s} {:>8s} {:>3s} {:>4s} {}".format('Label', 'LOO r', 'p', 'k', 'n', 'Features')
print(hdr)
print("-" * 95)
for label, ds, feats, tgt, method in TESTS:
    if method == 'gbr':
        r, p, n = loo_gbr_r(ds, feats, target=tgt)
    else:
        r, p, n = loo_r(ds, feats, target=tgt)
    fs = ' + '.join(f.replace('feat_', '').replace('ix_', 'X_') for f in feats)
    s = sig(p) if not math.isnan(p) else ' '
    rs = "{:+.3f}{}".format(r, s) if not math.isnan(r) else '  N/A  '
    ps = "{:.4f}".format(p) if not math.isnan(p) else '  N/A '
    print("{:<25s} {:>8s} {:>8s} {:>3d} {:>4d} {}".format(label, rs, ps, len(feats), n, fs))

print()
print("Published 70-panel baselines:")
print("  HU-A p70: LOO r=+0.391** (p=0.010, k=4, n=43)")
print("  FH-A p70: LOO r=+0.518** (p=0.006, k=3, n=27)")
print()
print("Done.")
