"""
 Spearman  — CLEAN-129 (Tier A+B)
: ada_first_pct  log(1+ADA)
:  / (natural) / (engineered)
"""
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('data/immunogenicity_panel_136_master.csv')
df_c = df[df['evidence_tier'].isin(['A','B']) & df['ada_first_pct'].notna].copy
df_c['ada_log'] = np.log1p(df_c['ada_first_pct'])
n_total = len(df_c)

FEATURES = {
    'VH_identity':      'vh_identity_842',
    'VL_identity':      'vl_identity_842',
    'pI':               'pI',
    'GRAVY':            'GRAVY',
    'instability':      'instability_index',
    'net_charge_pH7':   'net_charge_pH7',
    'hydro_patch':      'hydro_patch_max9',
    'charge_patch':     'charge_patch_max7',
    'TCIA_score':       'immuno_tcia_score',
    'n_high_epitopes':  'immuno_n_high',
    'n_med_epitopes':   'immuno_n_medium',
    'n_clusters':       'immuno_n_clusters',
    'frac_exposed_vh':  'surf_frac_exposed_vh',
    'frac_exposed_vl':  'surf_frac_exposed_vl',
    'n_surf_patches':   'surf_n_patches',
    'mean_sasa_vh':     'surf_mean_sasa_vh',
    'VH_VL_angle':      'vh_vl_angle_deg',
    'interface_pairs':  'interface_n_pairs',
    'interface_dist':   'interface_mean_dist_A',
}

TARGETS = {
    'ADA%':         'ada_first_pct',
    'log(1+ADA)':   'ada_log',
}

def spearman_table(subdf, label):
    n = len(subdf)
    print("\n{'='*68}")
    print("  {}  (n={})".format(label, n))
    print("{'='*68}")
    hdr = "  {:22} " + " {:>12}" * len(TARGETS)
    print(hdr.format("Feature", *TARGETS.keys))
    print("  " + "-"*22 + (" " + "-"*12)*len(TARGETS))

    rows = []
    for fname, fcol in FEATURES.items:
        if fcol not in subdf.columns:
            continue
        row = [fname]
        for tname, tcol in TARGETS.items:
            vals = subdf[[fcol, tcol]].dropna
            if len(vals) < 10:
                row.append("  n<10  —")
                continue
            rho, pval = spearmanr(vals[fcol], vals[tcol])
            sig = '**' if pval < 0.05 else ('*' if pval < 0.1 else '  ')
            row.append("{:+.3f} p={:.3f}{}".format(rho, pval, sig))
        rows.append(row)

    # sort by abs(rho) of first target
    def sort_key(r):
        try:
            return -abs(float(r[1].split[0]))
        except:
            return 0
    rows.sort(key=sort_key)

    for row in rows:
        line = "  {:22} " + " {:>12}" * (len(row)-1)
        print(line.format(*row))

# replace braces in print strings
def run:
    print("=" * 68)
    print("  SPEARMAN CORRELATION vs ADA  —  CLEAN-129 (Tier A+B)")
    print("=" * 68)

    # Full panel
    spearman_table(df_c, "ALL  (natural + engineered)")

    # By origin
    for origin in ['natural', 'engineered']:
        sub = df_c[df_c['origin'] == origin]
        spearman_table(sub, origin.upper)

    # Summary: top signals
    print("\n" + "=" * 68)
    print("  TOP SIGNALS SUMMARY (|rho|>0.15, p<0.1, full panel n={})".format(n_total))
    print("=" * 68)
    print("  {:22} {:>10} {:>10} {:>8}".format("Feature","rho(ADA%)","rho(logADA)","note"))

    for fname, fcol in FEATURES.items:
        if fcol not in df_c.columns:
            continue
        vals_r = df_c[[fcol,'ada_first_pct']].dropna
        vals_l = df_c[[fcol,'ada_log']].dropna
        if len(vals_r) < 10:
            continue
        rho_r, p_r = spearmanr(vals_r[fcol], vals_r['ada_first_pct'])
        rho_l, p_l = spearmanr(vals_l[fcol], vals_l['ada_log'])
        if abs(rho_r) > 0.15 or p_r < 0.1 or abs(rho_l) > 0.15 or p_l < 0.1:
            sig_r = '**' if p_r < 0.05 else ('*' if p_r < 0.1 else '')
            sig_l = '**' if p_l < 0.05 else ('*' if p_l < 0.1 else '')
            print("  {:22} {:+6.3f}{:2s}   {:+6.3f}{:2s}".format(
                fname, rho_r, sig_r, rho_l, sig_l))

run
