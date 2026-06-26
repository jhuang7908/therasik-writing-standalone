"""
immunogenicity_13factor_audit.py
13-Factor Immunogenicity Audit per user's framework
"""
import pandas as pd, numpy as np
from scipy.stats import spearmanr

ROOT = "d:/InSynBio-AI-Research/Antibody_Engineer_Suite"
m = pd.read_csv(f"{ROOT}/data/thera_sabdab/out/immuno70_sprint_matrix.csv")
m = m.drop_duplicates("antibody_name").copy()
target = "ada_rate_pct"

CDR_COLS = ["vh_cdr1","vh_cdr2","vh_cdr3","vl_cdr1","vl_cdr2","vl_cdr3"]

# === NEW FEATURES ===

# 1. CDR N-glycosylation motifs (N-X-S/T, X!=P)
def cdr_nglyc(row):
    count = 0
    for c in CDR_COLS:
        seq = str(row.get(c,"")) if pd.notna(row.get(c)) else ""
        for i in range(len(seq)-2):
            if seq[i]=="N" and seq[i+1]!="P" and seq[i+2] in "ST":
                count += 1
    return count
m["feat_cdr_nglyc"] = m.apply(cdr_nglyc, axis=1)

# 2. CDR oxidation-sensitive residues (Met + Trp)
def cdr_ox(row):
    count = 0
    for c in CDR_COLS:
        seq = str(row.get(c,"")) if pd.notna(row.get(c)) else ""
        count += seq.count("M") + seq.count("W")
    return count
m["feat_cdr_oxidation"] = m.apply(cdr_ox, axis=1)

# 3. Route: SC=1 (higher risk), IV=0
ROUTE_SCORE = {"SC": 1.0, "IM": 0.8, "IVT": 0.5, "IV": 0.0}
m["feat_route_sc"] = m["route"].map(ROUTE_SCORE).fillna(0.5)

# 4. Composite aggregation risk
m["feat_agg_risk"] = (m["feat_cmc_agg"].fillna(0) +
                      m["feat_cmc_gravy"].fillna(0) * 5 +
                      m["feat_cmc_hydro_patch"].fillna(0) * 0.3)

# 5. CDR hydrophobicity fraction
HYDROPHOBIC = set("VILMFYW")
def cdr_hydro(row):
    total, hydro = 0, 0
    for c in CDR_COLS:
        seq = str(row.get(c,"")) if pd.notna(row.get(c)) else ""
        total += len(seq)
        hydro += sum(1 for aa in seq if aa in HYDROPHOBIC)
    return hydro / max(total, 1)
m["feat_cdr_hydrophobicity"] = m.apply(cdr_hydro, axis=1)

# 6. Fc N297 glycan status
def fc_glycan(row):
    fc = str(row.get("fc_engineering", ""))
    if "N297" in fc or "aglyco" in fc.lower(): return 0.0
    if "afuco" in fc.lower(): return 0.8
    return 1.0
m["feat_fc_glycan"] = m.apply(fc_glycan, axis=1)

# 7. Route x Origin interaction
m["feat_sc_x_origin"] = m["feat_route_sc"] * m["feat_origin_code"]

# === AUDIT ===
hu = m[m["origin"]=="humanized"]
fu = m[m["origin"]=="fully_human"]

AUDIT = {
    "1. T-cell epitopes (MHC-II)":
        ["feat_n_strong_binders", "feat_n_clusters", "feat_net_burden"],
    "2. Germline identity":
        ["feat_vh_identity", "feat_vl_identity", "feat_vz_foreignness", "feat_vh_family_score"],
    "3. CDR length/composition":
        ["feat_cdrh3_len", "feat_cdrh3_aromaticity", "feat_total_cdr_length",
         "feat_cdrh3_charge", "feat_cdr_hydrophobicity"],
    "4. Protein aggregates":
        ["feat_cmc_agg", "feat_agg_risk", "feat_cmc_instability"],
    "5. Surface hydrophobicity":
        ["feat_surf_n_patches", "feat_surf_frac_vl", "feat_cmc_hydro_patch", "feat_cmc_gravy"],
    "6. Fc N297 glycan":
        ["feat_fc_glycan", "feat_fc_tolerogenic", "feat_fc_present"],
    "7. CDR glycosylation/PTM":
        ["feat_cdr_nglyc", "feat_cdr_deamidation", "feat_cdr_isomerization"],
    "8. Route of administration":
        ["feat_route_sc", "feat_clinical_context", "feat_sc_x_origin"],
    "9. Pre-existing ADA":
        ["(not available - need patient serology data)"],
    "10. Disease state":
        ["feat_immune_depleting", "feat_checkpoint", "feat_target_bio"],
    "11. Dosing frequency":
        ["feat_dosing_freq", "feat_half_life", "feat_hl_inv"],
    "12. Photo-oxidation":
        ["feat_cdr_oxidation", "feat_cmc_agg"],
    "13. Excipient adjuvancy":
        ["(not available - need formulation data)"],
}

print("=" * 90)
print("13-FACTOR IMMUNOGENICITY AUDIT - Spearman r vs clinical ADA")
print(f"{'':37s} {'All(70)':>8s}  {'HU(43)':>8s}  {'FH(27)':>8s}")
print("=" * 90)

for cat, feats in AUDIT.items():
    print(f"\n  {cat}")
    for f in feats:
        if f.startswith("("):
            print(f"    {f}")
            continue
        if f not in m.columns:
            print(f"    {f.replace('feat_',''):33s}: MISSING")
            continue
        sub = m[[target, f]].dropna()
        r_all, p_all = spearmanr(sub[target], sub[f]) if len(sub)>5 else (np.nan, 1.0)
        sub_hu = hu[[target, f]].dropna()
        r_hu, _ = spearmanr(sub_hu[target], sub_hu[f]) if len(sub_hu)>5 else (np.nan, 1.0)
        sub_fu = fu[[target, f]].dropna()
        r_fu, _ = spearmanr(sub_fu[target], sub_fu[f]) if len(sub_fu)>5 else (np.nan, 1.0)
        star = "**" if p_all<0.01 else ("*" if p_all<0.05 else ("^" if p_all<0.10 else " "))
        fn = f.replace("feat_","")
        rh = f"{r_hu:+.3f}" if not np.isnan(r_hu) else "  NaN"
        rf = f"{r_fu:+.3f}" if not np.isnan(r_fu) else "  NaN"
        print(f"    {fn:33s}: {r_all:+.3f}{star}    {rh}    {rf}")

# === NEW FEATURES SUMMARY ===
print("\n" + "=" * 90)
print("NEW FEATURES added in this audit")
print("=" * 90)
NEW = ["feat_cdr_nglyc", "feat_cdr_oxidation", "feat_route_sc",
       "feat_agg_risk", "feat_cdr_hydrophobicity", "feat_fc_glycan", "feat_sc_x_origin"]
for f in NEW:
    sub = m[[target, f]].dropna()
    r, p = spearmanr(sub[target], sub[f])
    sub_hu = hu[[target, f]].dropna()
    rh, _ = spearmanr(sub_hu[target], sub_hu[f]) if len(sub_hu)>5 else (np.nan, 1.0)
    sub_fu = fu[[target, f]].dropna()
    rf, _ = spearmanr(sub_fu[target], sub_fu[f]) if len(sub_fu)>5 else (np.nan, 1.0)
    star = "**" if p<0.01 else ("*" if p<0.05 else ("^" if p<0.10 else " "))
    fn = f.replace("feat_","")
    print(f"  {fn:30s}: All={r:+.3f}{star} p={p:.3f}  HU={rh:+.3f}  FH={rf:+.3f}")

# === Coverage summary ===
covered = sum(1 for v in AUDIT.values() for f in v if not f.startswith("(") and f in m.columns)
total = sum(1 for v in AUDIT.values() for f in v if not f.startswith("("))
print(f"\nCoverage: {covered}/{total} features computed ({covered*100//total}%)")
print(f"Not available: 9. Pre-existing ADA, 13. Excipient adjuvancy")

m.to_csv(f"{ROOT}/data/thera_sabdab/out/immuno70_sprint_matrix.csv", index=False)
n_feat = len([c for c in m.columns if c.startswith("feat_")])
print(f"\nSaved: {len(m)} x {len(m.columns)} ({n_feat} features)")
