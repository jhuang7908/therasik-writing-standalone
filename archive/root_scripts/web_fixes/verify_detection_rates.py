import pandas as pd
import numpy as np
import math
import json
from scipy.stats import spearmanr
from pathlib import Path

# Load data
df = pd.read_csv('data/immunogenicity_panel_136_master.csv')
panel = df[df['evidence_tier'].isin(['A','B']) & df['ada_first_pct'].notna()].copy()
panel = panel.dropna(subset=['vh_identity_842','vl_identity_842',
                              'surf_frac_exposed_vh','surf_frac_exposed_vl',
                              'interface_n_pairs','immuno_tcia_score',
                              'immuno_n_high','immuno_n_clusters',
                              'instability_index','hydro_patch_max9',
                              'surf_n_patches'])

# Load best config from the last run if available, else use defaults from script
config_path = Path('config/immunogenicity_risk_v2.json')
if config_path.exists():
    with open(config_path, 'r') as f:
        full_cfg = json.load(f)
    # Map back to flat params used in score_batch
    p = {
        'w_G': full_cfg['components']['G_germline_distance']['weight'],
        'w_F': full_cfg['components']['F_inverse_exposure']['weight'],
        'w_I': full_cfg['components']['I_interface_density']['weight'],
        'w_E': full_cfg['components']['E_high_epitopes']['weight'],
        'w_C': full_cfg['components']['C_cluster_density']['weight'],
        'w_P': full_cfg['components']['P_surface_patches']['weight'],
        'slope': full_cfg['sigmoid']['slope'],
        'mid': full_cfg['sigmoid']['midpoint'],
        'syn_GF': full_cfg['synergy_terms']['GxF'],
        'syn_GI': full_cfg['synergy_terms']['GxI'],
        'vl_nat': full_cfg['vl_modulator']['natural'],
        'vl_eng': full_cfg['vl_modulator']['engineered'],
        'i_scale': full_cfg['components']['I_interface_density']['scale'],
        'e_scale': full_cfg['components']['E_high_epitopes']['scale'],
        'p_scale': full_cfg['components']['P_surface_patches']['scale'],
        'instab_gate': full_cfg['cmc_veto_gates']['instability_index']['gate'],
        'instab_pen': full_cfg['cmc_veto_gates']['instability_index']['penalty'],
        'hydro_gate': full_cfg['cmc_veto_gates']['hydro_patch_max9']['gate'],
        'hydro_pen': full_cfg['cmc_veto_gates']['hydro_patch_max9']['penalty'],
        'threshold_high': full_cfg['thresholds']['high']
    }
else:
    # Fallback to hardcoded best from previous run if file missing
    p = {'w_G': 0.4, 'w_F': 0.3, 'w_I': 0.05, 'w_E': 0.15, 'w_C': 0.0, 'w_P': 0.1, 'slope': 3.0, 'mid': 0.25, 'syn_GF': 0.1, 'syn_GI': 0.05, 'vl_nat': -0.05, 'vl_eng': 0.15, 'i_scale': 60, 'e_scale': 40, 'p_scale': 14, 'instab_gate': 42, 'instab_pen': 0.04, 'hydro_gate': 0.7, 'hydro_pen': 0.07, 'threshold_high': 0.67}

def sigmoid(x):
    x = max(-20, min(20, x))
    return 1.0 / (1.0 + math.exp(-x))

def get_scores(df_subset, p):
    G = np.clip(1.0 - df_subset['vh_identity_842'].values, 0, 1)
    F = np.clip(1.0 - df_subset['surf_frac_exposed_vh'].values, 0, 1)
    I = np.clip(df_subset['interface_n_pairs'].values / p['i_scale'], 0, 1)
    E = np.clip(df_subset['immuno_n_high'].values / p['e_scale'], 0, 1)
    C = np.clip(df_subset['immuno_n_clusters'].values / 5.0, 0, 1)
    P = np.clip(df_subset['surf_n_patches'].values / p['p_scale'], 0, 1)
    
    z = (p['w_G']*G + p['w_F']*F + p['w_I']*I + p['w_E']*E + p['w_C']*C + p['w_P']*P)
    vl_delta = np.where(df_subset['origin'].values == 'natural', p['vl_nat'] * (df_subset['vl_identity_842'].values - 0.95), p['vl_eng'] * (df_subset['vl_identity_842'].values - 0.90))
    z += vl_delta
    z += p['syn_GF'] * G * F
    z += p['syn_GI'] * G * I
    z += np.where(df_subset['instability_index'].values > p['instab_gate'], p['instab_pen'], 0.0)
    z += np.where(df_subset['hydro_patch_max9'].values > p['hydro_gate'], p['hydro_pen'], 0.0)
    return np.array([sigmoid(p['slope'] * (zi - p['mid'])) for zi in z])

# Calculate scores for all
panel['v2_score'] = get_scores(panel, p)
ADA_HIGH_CUTOFF = 10.0
SCORE_HIGH_CUTOFF = p.get('threshold_high', 0.67)

def analyze_group(df_group, name):
    low_group = df_group[df_group['v2_score'] < SCORE_HIGH_CUTOFF]
    high_group = df_group[df_group['v2_score'] >= SCORE_HIGH_CUTOFF]
    
    def get_stats(sub):
        if len(sub) == 0: return 0, 0, 0
        high_ada_count = len(sub[sub['ada_first_pct'] > ADA_HIGH_CUTOFF])
        pct = (high_ada_count / len(sub)) * 100
        return len(sub), high_ada_count, pct

    n_low, h_low, p_low = get_stats(low_group)
    n_high, h_high, p_high = get_stats(high_group)
    
    print(f"--- {name} ---")
    print(f"LOW Score Group (n={n_low}): High ADA Count = {h_low}, Detection Rate = {p_low:.1f}%")
    print(f"HIGH Score Group (n={n_high}): High ADA Count = {h_high}, Detection Rate = {p_high:.1f}%")
    if p_low > 0:
        print(f"Risk Ratio (High/Low): {p_high/p_low:.2f}x")
    else:
        print(f"Risk Ratio (High/Low): INF")
    print()

# 1. All Antibodies
analyze_group(panel, "ALL ANTIBODIES")

# 2. Fully Human (FH) - origin == 'natural'
fh_panel = panel[panel['origin'] == 'natural']
analyze_group(fh_panel, "FULLY HUMAN (FH)")

# 3. Humanized (HU) - origin == 'engineered'
hu_panel = panel[panel['origin'] == 'engineered']
analyze_group(hu_panel, "HUMANIZED (HU)")
