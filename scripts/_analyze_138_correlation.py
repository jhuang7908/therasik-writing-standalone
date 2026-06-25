"""
Compare 70-antibody vs 138-antibody dataset:
- Spearman correlations for key features
- LOO cross-validation with same model structures as 70-antibody report
- Quantify correlation drop due to missing confounder information

Run:
  python scripts/_analyze_138_correlation.py
"""
from __future__ import annotations
import csv, math, re, sys
from pathlib import Path
from collections import Counter

import numpy as np
from scipy import stats
from scipy.optimize import differential_evolution

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv"

# ─────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────
AA_GROUPS = {
    'aromatic': set('FYW'),
    'hydrophobic': set('VILMACFYW'),
    'polar': set('STNQ'),
    'charged_pos': set('KRH'),
    'charged_neg': set('DE'),
}

def cdrh3_composition(seq: str) -> dict:
    s = (seq or '').upper().strip()
    n = len(s) if s else 1
    out = {'len': n}
    for gname, aas in AA_GROUPS.items():
        out[gname] = sum(1 for c in s if c in aas) / max(n, 1)
    return out


def to_float(v) -> float | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in ('nan', 'none', 'nr', ''):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def encode_genetics(v: str) -> int:
    """1=fully_human, 0=humanized/chimeric/murine"""
    return 1 if str(v).strip().lower() in ('genetically_human', 'fully_human') else 0


def encode_mtx(v: str) -> float:
    """MTX comedication → 0–1 scale (only 70-panel has this)"""
    v = str(v).strip().lower()
    if 'high' in v:
        return 1.0
    if 'low' in v or 'occasional' in v:
        return 0.33
    if 'none' in v or v in ('', 'nan', 'none'):
        return 0.0
    return 0.0


def encode_immuno_ctx(v: str) -> float:
    """Immunosuppressant context → 0–1 (broader than MTX)"""
    v = str(v).strip().lower()
    if not v or v in ('none', 'nan'):
        return 0.0
    if 'mtx' in v or 'methotrexate' in v:
        return 0.8
    if 'immunosuppressant' in v or 'corticosteroid' in v:
        return 0.5
    if 'background' in v or 'chemotherapy' in v:
        return 0.4
    if 'antibiotic' in v:
        return 0.1
    return 0.3


def encode_half_life(v) -> float:
    s = str(v).strip().lower()
    # extract first number
    m = re.search(r'[\d.]+', s)
    if m:
        return float(m.group(0))
    # approximate strings
    if '~' in s:
        m2 = re.search(r'[\d.]+', s.replace('~', ''))
        if m2:
            return float(m2.group(0))
    return float('nan')


def spearman(x, y):
    """Spearman r and p, ignoring NaN pairs."""
    pairs = [(xi, yi) for xi, yi in zip(x, y)
             if xi is not None and yi is not None
             and not math.isnan(xi) and not math.isnan(yi)]
    if len(pairs) < 5:
        return float('nan'), float('nan'), len(pairs)
    xs, ys = zip(*pairs)
    r, p = stats.spearmanr(xs, ys)
    return r, p, len(pairs)


# ─────────────────────────────────────────────────────────────
# LOO with scipy differential evolution
# ─────────────────────────────────────────────────────────────
def loo_spearman(X: np.ndarray, y: np.ndarray, lam: float = 0.0):
    """LOO cross-validation: each fold re-optimizes weights from scratch."""
    n, k = X.shape
    preds = np.full(n, np.nan)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        Xt, yt = X[mask], y[mask]

        def neg_spearman(w):
            scores = Xt @ w
            r, _ = stats.spearmanr(scores, yt)
            pen = lam * np.sum(w ** 2)
            return -(r if not np.isnan(r) else 0) + pen

        res = differential_evolution(
            neg_spearman,
            [(-20, 20)] * k,
            seed=42, maxiter=300, tol=1e-6, workers=1,
            popsize=12, mutation=(0.5, 1.0), recombination=0.9,
        )
        w_opt = res.x
        preds[i] = X[i] @ w_opt

    r, p = stats.spearmanr(preds, y)
    return float(r), float(p)


# ─────────────────────────────────────────────────────────────
# Load + feature engineering
# ─────────────────────────────────────────────────────────────
rows = list(csv.DictReader(MASTER.open(encoding='utf-8')))

data = []
for r in rows:
    ada = to_float(r.get('ada_first_pct'))
    if ada is None:
        continue
    genetics = r.get('genetics_normalized', '').strip().lower()
    is_fh = 1 if genetics in ('genetically_human', 'fully_human') else 0
    is_hu = 1 - is_fh

    cdrh3 = cdrh3_composition(r.get('vh_cdr3', ''))

    # Clinical confounders
    mtx_raw = encode_mtx(r.get('mtx_comedication', ''))
    immuno_ctx = encode_immuno_ctx(r.get('immunosuppressant_context', ''))
    # combined immunosuppression score (max of the two)
    immuno_sup = max(mtx_raw, immuno_ctx)

    hl = encode_half_life(r.get('half_life_days', ''))

    immune_depl = to_float(r.get('immune_depleting')) or 0.0
    checkpoint = to_float(r.get('checkpoint_inhibitor')) or 0.0
    oncology = to_float(r.get('oncology_indication')) or 0.0

    # T-cell epitope features (from TCIA/MHC-II prediction)
    n_high = to_float(r.get('immuno_n_high'))
    n_med = to_float(r.get('immuno_n_medium'))
    n_clust = to_float(r.get('immuno_n_clusters'))
    tcia = to_float(r.get('immuno_tcia_score'))
    n_strong = n_high if n_high is not None else float('nan')
    net_burden = (n_high or 0) + 0.5 * (n_med or 0) if n_high is not None else float('nan')

    # Structural
    surf_vh = to_float(r.get('surf_frac_exposed_vh'))
    surf_vl = to_float(r.get('surf_frac_exposed_vl'))

    # Germline
    vh_id = to_float(r.get('vh_germline_identity'))

    # Assay gen
    assay_gen = to_float(r.get('assay_generation'))

    # V2 model
    v2 = to_float(r.get('ada_v2_score'))

    # Panel flag: has complete clinical confounder info (p70 set)
    has_confounders = 1 if (r.get('panel_source', '').strip() == 'confirmed_p70') else 0

    data.append({
        'name': r['antibody_name'],
        'ada': ada,
        'is_fh': is_fh,
        'is_hu': is_hu,
        'has_confounders': has_confounders,
        'panel_source': r.get('panel_source', '').strip(),
        # features
        'immuno_sup': immuno_sup,
        'mtx_raw': mtx_raw,
        'half_life': hl,
        'immune_depl': immune_depl,
        'checkpoint': checkpoint,
        'oncology': oncology,
        'cdrh3_arom': cdrh3['aromatic'],
        'cdrh3_hydro': cdrh3['hydrophobic'],
        'cdrh3_polar': cdrh3['polar'],
        'cdrh3_len': cdrh3['len'],
        'n_clusters': n_clust,
        'n_strong': n_strong,
        'net_burden': net_burden,
        'tcia': tcia,
        'surf_vh': surf_vh,
        'surf_vl': surf_vl,
        'vh_id': vh_id,
        'assay_gen': assay_gen,
        'v2_score': v2,
    })

print(f"Loaded {len(data)} rows with numeric ADA")
ps = Counter(d['panel_source'] for d in data)
print("Panel source:", dict(ps))
print()

# ─────────────────────────────────────────────────────────────
# Subset definitions
# ─────────────────────────────────────────────────────────────
def subset(data, **filters):
    out = data
    for k, v in filters.items():
        out = [d for d in out if d[k] == v]
    return out

subsets = {
    'ALL_138': data,
    'HU_138': [d for d in data if d['is_hu']],
    'FH_138': [d for d in data if d['is_fh']],
    'ALL_p70': subset(data, has_confounders=1),
    'HU_p70': [d for d in data if d['is_hu'] and d['has_confounders']],
    'FH_p70': [d for d in data if d['is_fh'] and d['has_confounders']],
    'HU_new66': [d for d in data if d['is_hu'] and not d['has_confounders']],
    'FH_new66': [d for d in data if d['is_fh'] and not d['has_confounders']],
}
for k, v in subsets.items():
    n_fh = sum(1 for d in v if d['is_fh'])
    n_hu = sum(1 for d in v if d['is_hu'])
    print(f"  {k:15s}: n={len(v):3d} (FH={n_fh}, HU={n_hu})")

print()

# ─────────────────────────────────────────────────────────────
# Spearman correlations
# ─────────────────────────────────────────────────────────────
FEATURES = [
    ('immuno_sup',   'Immunosuppressant (combined)'),
    ('mtx_raw',      'MTX comedication (coded)'),
    ('half_life',    'Half-life (days)'),
    ('immune_depl',  'Immune-depleting target'),
    ('cdrh3_arom',   'CDR-H3 aromaticity'),
    ('cdrh3_polar',  'CDR-H3 polarity'),
    ('cdrh3_len',    'CDR-H3 length'),
    ('n_clusters',   'MHC-II epitope clusters'),
    ('n_strong',     'Strong MHC-II binders'),
    ('net_burden',   'Net epitope burden'),
    ('tcia',         'TCIA score'),
    ('surf_vl',      'VL surface hydrophilic frac'),
    ('vh_id',        'VH germline identity'),
    ('assay_gen',    'Assay generation'),
    ('v2_score',     'V2 model score'),
]

def corr_table(ds, label: str) -> list[tuple]:
    y = [d['ada'] for d in ds]
    rows = []
    for fname, fdesc in FEATURES:
        x = [d[fname] if d[fname] is not None else float('nan') for d in ds]
        r, p, n = spearman(x, y)
        rows.append((fname, fdesc, r, p, n))
    return rows

print("=" * 90)
print("SPEARMAN CORRELATIONS vs ADA RATE")
print("=" * 90)
print(f"{'Feature':<24} {'HU_p70':>8} {'HU_138':>8} {'Δr':>6}  | {'FH_p70':>8} {'FH_138':>8} {'Δr':>6}")
print("-" * 90)

hu_p70 = subsets['HU_p70']
hu_138 = subsets['HU_138']
fh_p70 = subsets['FH_p70']
fh_138 = subsets['FH_138']

for fname, fdesc in FEATURES:
    y_hu_p70 = [d['ada'] for d in hu_p70]
    y_hu_138 = [d['ada'] for d in hu_138]
    y_fh_p70 = [d['ada'] for d in fh_p70]
    y_fh_138 = [d['ada'] for d in fh_138]

    def r_str(ds, fn):
        x = [d[fn] if d[fn] is not None else float('nan') for d in ds]
        y = [d['ada'] for d in ds]
        r, p, n = spearman(x, y)
        if math.isnan(r):
            return '  N/A  ', float('nan')
        sig = '**' if p < 0.01 else ('*' if p < 0.05 else ('^' if p < 0.10 else ' '))
        return f"{r:+.3f}{sig}", r

    s_hu_p70, r_hu_p70 = r_str(hu_p70, fname)
    s_hu_138, r_hu_138 = r_str(hu_138, fname)
    s_fh_p70, r_fh_p70 = r_str(fh_p70, fname)
    s_fh_138, r_fh_138 = r_str(fh_138, fname)

    d_hu = (r_hu_138 - r_hu_p70) if not (math.isnan(r_hu_138) or math.isnan(r_hu_p70)) else float('nan')
    d_fh = (r_fh_138 - r_fh_p70) if not (math.isnan(r_fh_138) or math.isnan(r_fh_p70)) else float('nan')
    d_hu_s = f"{d_hu:+.3f}" if not math.isnan(d_hu) else '  N/A'
    d_fh_s = f"{d_fh:+.3f}" if not math.isnan(d_fh) else '  N/A'

    print(f"  {fdesc:<22} {s_hu_p70:>8} {s_hu_138:>8} {d_hu_s:>6}  | {s_fh_p70:>8} {s_fh_138:>8} {d_fh_s:>6}")

print()
print(f"  HU n: p70={len(hu_p70)}, 138={len(hu_138)} (+{len(hu_138)-len(hu_p70)})")
print(f"  FH n: p70={len(fh_p70)}, 138={len(fh_138)} (+{len(fh_138)-len(fh_p70)})")
print()

# ─────────────────────────────────────────────────────────────
# LOO cross-validation (same model structures as 70-antibody report)
# ─────────────────────────────────────────────────────────────
print("=" * 70)
print("LOO CROSS-VALIDATION COMPARISON (key models)")
print("=" * 70)

def loo_model(ds, feature_names: list[str], lam: float = 0.0, label: str = ''):
    valid = [d for d in ds if all(
        d[f] is not None and not math.isnan(d[f]) for f in feature_names
    ) and d['ada'] is not None]
    if len(valid) < 8:
        print(f"  {label}: n={len(valid)} (too few for LOO)")
        return float('nan'), float('nan'), len(valid)
    X = np.array([[d[f] for f in feature_names] for d in valid])
    y = np.array([d['ada'] for d in valid])
    r_loo, p_loo = loo_spearman(X, y, lam=lam)
    # also compute fit r
    scores_full = X @ np.ones(X.shape[1])  # placeholder; real fit needs optimizer
    r_fit, _ = stats.spearmanr(X.mean(axis=1), y)  # rough
    print(f"  {label:<35}  n={len(valid):3d}  LOO r={r_loo:+.3f}  p={p_loo:.3f}")
    return r_loo, p_loo, len(valid)

print()
print("--- HU-A model: immuno_sup + cdrh3_arom + immune_depl + half_life ---")
print("  (from 70-antibody report: LOO r=0.391, p=0.010, n=43)")
loo_model(hu_p70,  ['immuno_sup','cdrh3_arom','immune_depl','half_life'], label='HU-A  p70  (should ≈ 0.391)')
loo_model(hu_138,  ['immuno_sup','cdrh3_arom','immune_depl','half_life'], label='HU-A  138  (degraded?)')

print()
print("--- FH-A model: n_clusters + net_burden + n_strong ---")
print("  (from 70-antibody report: LOO r=0.518, p=0.006, n=27)")
loo_model(fh_p70,  ['n_clusters','net_burden','n_strong'],               label='FH-A  p70  (should ≈ 0.518)')
loo_model(fh_138,  ['n_clusters','net_burden','n_strong'],               label='FH-A  138  (degraded?)')

print()
print("--- Sequence-only model (no clinical confounders) ---")
loo_model(hu_138,  ['cdrh3_arom','cdrh3_polar','half_life'],             label='HU-seqonly  138')
loo_model(fh_138,  ['n_clusters','tcia','vh_id'],                        label='FH-seqonly  138')

print()
print("Done.")
