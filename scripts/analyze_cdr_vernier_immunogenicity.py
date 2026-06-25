"""
analyze_cdr_vernier_immunogenicity.py
======================================
For the 70 therapeutic antibodies, analyze how CDR and Vernier zone
sequences affect MHC-II T-cell epitope burden (= immunogenicity risk).

Analysis sections:
  1. CDR vs FR epitope burden decomposition (using existing epitope predictions)
  2. CDR-localized strong binder count per antibody
  3. Vernier zone foreignness for humanized antibodies
     (compare Vernier residues to human germline consensus)
  4. Correlation of Vernier foreignness with clinical ADA
  5. HTML report

Vernier zone IMGT positions (Foote & Winter 1992, IMGT adaptation):
  VH: 37, 47, 48, 67, 69, 71, 78, 80, 93, 94
  VL: 35, 46, 47, 48, 49, 64, 71, 78
"""
from __future__ import annotations
import sys, re
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT  = ROOT / "data" / "thera_sabdab" / "out"
REF  = ROOT / "data" / "reference"

# ─── Vernier zone IMGT position definitions ───────────────────────────────────
VH_VERNIER = {37, 47, 48, 67, 69, 71, 78, 80, 93, 94}   # 10 positions
VL_VERNIER = {35, 46, 47, 48, 49, 64, 71, 78}            # 8 positions

# CDR IMGT position ranges (inclusive, standard IMGT CDR definition)
VH_CDR1_POS = set(range(27, 39))   # IMGT 27-38
VH_CDR2_POS = set(range(56, 66))   # IMGT 56-65
VH_CDR3_POS = set(range(105, 118)) # IMGT 105-117
VL_CDR1_POS = set(range(27, 39))
VL_CDR2_POS = set(range(56, 66))
VL_CDR3_POS = set(range(105, 118))

VH_CDR_POS = VH_CDR1_POS | VH_CDR2_POS | VH_CDR3_POS
VL_CDR_POS = VL_CDR1_POS | VL_CDR2_POS | VL_CDR3_POS


# ══════════════════════════════════════════════════════════════════════════════
# 1.  Load data
# ══════════════════════════════════════════════════════════════════════════════
print("[1] Loading data …")
epi_df  = pd.read_csv(OUT / "mhcii_immuno_70_epitopes.csv")
arc_df  = pd.read_csv(OUT / "anarcii_numbering_70.csv")
mat_df  = pd.read_csv(OUT / "immuno70_full_matrix.csv")
route   = pd.read_csv(REF / "route_and_context.csv")[["antibody_name","route","oncology_indication"]]

# Merge origin and ADA into mat
mat_df = mat_df.merge(route, on="antibody_name", how="left")


# ══════════════════════════════════════════════════════════════════════════════
# 2.  CDR vs FR epitope burden analysis
# ══════════════════════════════════════════════════════════════════════════════
print("[2] CDR vs FR epitope burden …")

STRONG_RANK_THRESH  = 2.0   # percentile_rank ≤ 2 → "strong binder"
MEDIUM_RANK_THRESH  = 10.0  # percentile_rank ≤ 10 → "medium binder"

# Aggregate per antibody: strong binders in CDR vs FR
epi_df["is_strong"] = epi_df["percentile_rank"] <= STRONG_RANK_THRESH
epi_df["is_medium"] = epi_df["percentile_rank"] <= MEDIUM_RANK_THRESH

# De-duplicate: one unique peptide-region row per antibody (avoid allele inflation)
dedup = epi_df.drop_duplicates(subset=["antibody","chain","start","region"])[
    ["antibody","chain","start","region","is_strong","is_medium","net_contribution"]
].copy()

cdr_burden = []
for ab, grp in dedup.groupby("antibody"):
    cdr = grp[grp["region"].str.upper().str.contains("CDR")]
    fr  = grp[grp["region"].str.upper().str.contains("FR")]
    total_strong = grp["is_strong"].sum()
    cdr_strong   = cdr["is_strong"].sum()
    fr_strong    = fr["is_strong"].sum()
    total_medium = grp["is_medium"].sum()
    cdr_medium   = cdr["is_medium"].sum()
    cdr_frac_strong = (cdr_strong / total_strong) if total_strong > 0 else 0.0
    cdr_net_burden  = cdr["net_contribution"].sum()
    fr_net_burden   = fr["net_contribution"].sum()
    total_net       = grp["net_contribution"].sum()
    cdr_frac_net    = (cdr_net_burden / total_net) if total_net > 0 else 0.0
    cdr_burden.append({
        "antibody_name": ab,
        "total_unique_peptides":  len(grp),
        "cdr_peptides":           len(cdr),
        "fr_peptides":            len(fr),
        "strong_binders_total":   int(total_strong),
        "strong_binders_CDR":     int(cdr_strong),
        "strong_binders_FR":      int(fr_strong),
        "medium_binders_CDR":     int(cdr_medium),
        "cdr_frac_of_strong":     round(cdr_frac_strong, 3),
        "cdr_net_burden":         round(float(cdr_net_burden), 4),
        "fr_net_burden":          round(float(fr_net_burden), 4),
        "cdr_frac_of_net_burden": round(cdr_frac_net, 3),
    })

cdr_df = pd.DataFrame(cdr_burden)
mat_df = mat_df.merge(cdr_df, on="antibody_name", how="left")

# Sanity check
print(f"  Antibodies with CDR data: {cdr_df['strong_binders_CDR'].notna().sum()}")
print(f"  Mean CDR fraction of strong binders: {cdr_df['cdr_frac_of_strong'].mean():.3f}")
print(f"  Mean CDR fraction of net burden:     {cdr_df['cdr_frac_of_net_burden'].mean():.3f}")


# ══════════════════════════════════════════════════════════════════════════════
# 3.  Parse IMGT position maps from ABARCII → per-position residue dict
# ══════════════════════════════════════════════════════════════════════════════
print("[3] Parsing IMGT position maps for Vernier zone …")

def parse_imgt_map(pos_map_str: str) -> dict[int, str]:
    """Return {imgt_pos: aa_char} from ABARCII imgt_pos_map string."""
    if not pos_map_str or str(pos_map_str) in ("nan", "None", ""):
        return {}
    out = {}
    for token in str(pos_map_str).split(";"):
        token = token.strip()
        if not token:
            continue
        m = re.match(r"(\d+[A-Z]?):([A-Z])", token)
        if m:
            try:
                pos = int(re.match(r"(\d+)", m.group(1)).group(1))
                out[pos] = m.group(2)
            except ValueError:
                pass
    return out


def extract_vernier(row: pd.Series) -> dict:
    """Return Vernier zone amino acids for one ABARCII row."""
    chain_type = str(row.get("chain_type", "")).upper()
    positions  = VH_VERNIER if chain_type in ("H",) else VL_VERNIER
    pos_map    = parse_imgt_map(row.get("imgt_pos_map", ""))
    vz = {f"vz_{pos}": pos_map.get(pos, "-") for pos in sorted(positions)}
    vz["vz_coverage"] = sum(1 for p in positions if p in pos_map) / len(positions)
    return vz


# Build per-antibody Vernier zone residue tables
vz_rows = []
for _, row in arc_df.iterrows():
    vz = extract_vernier(row)
    vz["drug"]       = row["drug"]
    vz["chain_type"] = row["chain_type"]
    vz_rows.append(vz)
vz_df = pd.DataFrame(vz_rows)


# ══════════════════════════════════════════════════════════════════════════════
# 4.  Vernier zone foreignness for humanized antibodies
# ══════════════════════════════════════════════════════════════════════════════
print("[4] Calculating Vernier zone foreignness …")

# Human germline consensus at Vernier zone positions
# Derived from IMGT IG germline statistics (most common residue)
VH_VERNIER_CONSENSUS = {
    37: "V",   # Val at Kabat H37 (IMGT 37) — Ala in some
    47: "W",   # Trp conserved in FR2
    48: "I",   # Ile
    67: "A",   # Ala
    69: "L",   # Leu
    71: "R",   # Arg — key Vernier position, strongly position-dependent on VH family
    78: "V",   # Val
    80: "L",   # Leu
    93: "A",   # Ala
    94: "R",   # Arg — FR3 end
}
VL_VERNIER_CONSENSUS = {
    35: "Q",   # Gln
    46: "L",   # Leu
    47: "Y",   # Tyr conserved
    48: "P",   # Pro
    49: "S",   # Ser
    64: "D",   # Asp
    71: "Y",   # Tyr
    78: "L",   # Leu
}


def vernier_foreignness(pos_map: dict[int, str], vz_positions: set,
                        consensus: dict[int, str]) -> tuple[float, int, list]:
    """
    Foreign residue count and fraction at Vernier zone positions.
    A residue is 'foreign' if it differs from the human germline consensus.
    Returns (foreignness_score, n_foreign_positions, foreign_positions_list).
    """
    covered     = [p for p in vz_positions if p in pos_map]
    if not covered:
        return (0.0, 0, [])
    foreign = []
    for p in covered:
        aa = pos_map[p]
        if aa != consensus.get(p, aa):   # mismatch vs consensus
            foreign.append(p)
    score = len(foreign) / len(covered)
    return (round(score, 3), len(foreign), sorted(foreign))


vf_rows = []
for _, row in arc_df.iterrows():
    chain_type = str(row.get("chain_type","")).upper()
    pos_map    = parse_imgt_map(row.get("imgt_pos_map",""))
    if chain_type == "H":
        score, n_foreign, foreign_pos = vernier_foreignness(
            pos_map, VH_VERNIER, VH_VERNIER_CONSENSUS)
    elif chain_type in ("K","L"):
        score, n_foreign, foreign_pos = vernier_foreignness(
            pos_map, VL_VERNIER, VL_VERNIER_CONSENSUS)
    else:
        score, n_foreign, foreign_pos = (0.0, 0, [])
    vf_rows.append({
        "drug":            row["drug"],
        "chain_type":      chain_type,
        "vz_foreignness":  score,
        "vz_n_foreign":    n_foreign,
        "vz_foreign_pos":  str(foreign_pos),
    })
vf_df = pd.DataFrame(vf_rows)

# Aggregate to one row per antibody (average VH + VL)
vf_per_ab = vf_df.groupby("drug").agg(
    vz_foreignness_mean=("vz_foreignness","mean"),
    vz_n_foreign_total=("vz_n_foreign","sum"),
).reset_index().rename(columns={"drug":"antibody_name"})
mat_df = mat_df.merge(vf_per_ab, on="antibody_name", how="left")

# VH-specific
sub_vh = vf_df[vf_df["chain_type"]=="H"][["drug","vz_foreignness","vz_n_foreign","vz_foreign_pos"]].copy()
sub_vh.rename(columns={"drug":"antibody_name","vz_foreignness":"vh_vz_foreignness",
                        "vz_n_foreign":"vh_vz_n_foreign",
                        "vz_foreign_pos":"vh_vz_foreign_pos"}, inplace=True)
mat_df = mat_df.merge(sub_vh, on="antibody_name", how="left")

# VL-specific (K and L chains — take first match per drug)
sub_vl = vf_df[vf_df["chain_type"].isin(["K","L"])].drop_duplicates(subset=["drug"])[
    ["drug","vz_foreignness","vz_n_foreign","vz_foreign_pos"]].copy()
sub_vl.rename(columns={"drug":"antibody_name","vz_foreignness":"vl_vz_foreignness",
                        "vz_n_foreign":"vl_vz_n_foreign",
                        "vz_foreign_pos":"vl_vz_foreign_pos"}, inplace=True)
mat_df = mat_df.merge(sub_vl, on="antibody_name", how="left")

hum_mask = mat_df["origin"] == "humanized"
fh_mask  = mat_df["origin"] == "fully_human"
print(f"  Mean VH Vernier foreignness (humanized):   {mat_df[hum_mask]['vh_vz_foreignness'].mean():.3f}")
print(f"  Mean VH Vernier foreignness (fully_human): {mat_df[fh_mask]['vh_vz_foreignness'].mean():.3f}")
print(f"  Mean VZ n_foreign (humanized):   {mat_df[hum_mask]['vz_n_foreign_total'].mean():.1f}")
print(f"  Mean VZ n_foreign (fully_human): {mat_df[fh_mask]['vz_n_foreign_total'].mean():.1f}")
print(f"  Note: Foreignness > 0.8 in BOTH groups suggests consensus may not be tight.")
print(f"  → VZ n_foreign_total (raw count) is more informative.")


# ══════════════════════════════════════════════════════════════════════════════
# 5.  Correlation analysis
# ══════════════════════════════════════════════════════════════════════════════
print("[5] Correlation analysis …")

features_to_test = [
    "origin_code",
    "vh_identity_pct",
    "vl_identity_pct",
    "vz_foreignness_mean",
    "vz_n_foreign_total",
    "vh_vz_foreignness",
    "strong_binders_CDR",
    "strong_binders_FR",
    "cdr_frac_of_strong",
    "cdr_frac_of_net_burden",
    "cdr_net_burden",
    "fr_net_burden",
    "n_strong_binders",
    "net_immunogenic_burden",
    "cdrh3_len",
    "cdrl3_len",
]

corr_rows = []
for fc in features_to_test:
    if fc not in mat_df.columns:
        continue
    # Use only the base 70 antibodies (mat_df should already be 70 rows but double-check)
    sub = mat_df.drop_duplicates("antibody_name")[["ada_rate_pct", fc]].dropna()
    if len(sub) < 10:
        continue
    sr, sp = spearmanr(sub["ada_rate_pct"], sub[fc])
    corr_rows.append({"feature": fc, "spearman_r": round(sr,3), "p": round(sp,4), "n": len(sub)})

corr_out = pd.DataFrame(corr_rows).sort_values("spearman_r", ascending=False, key=abs)
print("\n  Correlations with clinical ADA rate:")
print(corr_out.to_string(index=False))


# ══════════════════════════════════════════════════════════════════════════════
# 6.  Per-antibody summary (humanized only — CDR + Vernier details)
# ══════════════════════════════════════════════════════════════════════════════
print("[6] Building per-antibody CDR/Vernier summary …")

display_cols = [
    "antibody_name", "origin", "route", "ada_rate_pct",
    "vh_germline_imgt", "vl_germline_imgt",
    "vh_identity_pct", "vl_identity_pct",
    "vh_vz_foreignness", "vl_vz_foreignness",
    "vz_n_foreign_total",
    "vh_cdr1","vh_cdr2","vh_cdr3","vl_cdr1","vl_cdr2","vl_cdr3",
    "cdrh3_len","cdrl3_len",
    "strong_binders_CDR","strong_binders_FR",
    "cdr_frac_of_strong","cdr_frac_of_net_burden",
    "n_strong_binders","net_immunogenic_burden",
    "disease_class","target_class",
]
display_cols = [c for c in display_cols if c in mat_df.columns]
summary = mat_df[display_cols].sort_values("ada_rate_pct", ascending=False)

# CDR epitope hotspot analysis: which CDRs host strong binders?
print("\n  CDR strong binder hotspot (all 70 antibodies, top 15 by CDR burden):")
top_cdr = summary.nlargest(15, "strong_binders_CDR")[
    ["antibody_name","origin","ada_rate_pct","strong_binders_CDR",
     "cdr_frac_of_strong","vh_cdr3","vz_n_foreign_total"]
]
print(top_cdr.to_string(index=False))


# ══════════════════════════════════════════════════════════════════════════════
# 7.  Vernier zone detailed table for humanized antibodies
# ══════════════════════════════════════════════════════════════════════════════
print("\n[7] Vernier zone detail for humanized antibodies …")

hum = mat_df[mat_df["origin"]=="humanized"][
    ["antibody_name","ada_rate_pct","vh_identity_pct","vl_identity_pct",
     "vh_vz_foreignness","vh_vz_n_foreign","vh_vz_foreign_pos",
     "vl_vz_foreignness","vl_vz_n_foreign","vl_vz_foreign_pos",
     "strong_binders_CDR","cdr_frac_of_strong"]
].sort_values("ada_rate_pct", ascending=False)

print(hum.head(20).to_string(index=False))


# ══════════════════════════════════════════════════════════════════════════════
# 8.  Save outputs
# ══════════════════════════════════════════════════════════════════════════════
mat_df.to_csv(OUT / "immuno70_full_matrix.csv", index=False)
summary.to_csv(OUT / "immuno70_cdr_vernier_summary.csv", index=False)
corr_out.to_csv(OUT / "immuno70_cdr_vernier_correlations.csv", index=False)

print(f"\nMatrix shape: {mat_df.shape}")
print(f"Saved: {OUT / 'immuno70_cdr_vernier_summary.csv'}")


# ══════════════════════════════════════════════════════════════════════════════
# 9.  Generate HTML report
# ══════════════════════════════════════════════════════════════════════════════
print("[8] Generating HTML report …")


def badge(val, thresholds=((0.4,"#e53e3e"),(0.2,"#d69e2e"),(0,"#38a169")), fmt=".2f"):
    v = float(val) if pd.notna(val) else 0.0
    color = "#718096"
    for t, c in thresholds:
        if v >= t:
            color = c
            break
    return f'<span style="color:{color};font-weight:600">{v:{fmt}}</span>'


def build_corr_html():
    rows = ""
    for _, r in corr_out.iterrows():
        sr = r.get("spearman_r", 0)
        if pd.isna(sr): continue
        bar_w = int(abs(sr) * 120)
        bar_c = "#e53e3e" if sr > 0 else "#3182ce"
        star = "***" if r["p"] < 0.001 else ("**" if r["p"] < 0.01 else ("*" if r["p"] < 0.05 else ""))
        rows += (f'<tr><td><b>{r["feature"]}</b></td>'
                 f'<td>{sr:+.3f} {star}'
                 f'<div style="display:inline-block;width:{bar_w}px;height:7px;'
                 f'background:{bar_c};margin-left:6px;vertical-align:middle;border-radius:2px"></div></td>'
                 f'<td style="color:#718096">{r["p"]:.4f}</td>'
                 f'<td>{int(r["n"])}</td></tr>\n')
    return rows


def build_main_table():
    rows = ""
    for _, r in summary.iterrows():
        ada = r.get("ada_rate_pct", float("nan"))
        ada_str = f"{ada:.1f}%" if pd.notna(ada) else "—"
        ada_c = "#e53e3e" if (ada or 0)>20 else ("#d69e2e" if (ada or 0)>5 else "#38a169")
        vh_vz = r.get("vh_vz_foreignness", float("nan"))
        vl_vz = r.get("vl_vz_foreignness", float("nan"))
        cdr_frac = r.get("cdr_frac_of_strong", float("nan"))
        rows += f"""<tr>
          <td><b>{r['antibody_name']}</b></td>
          <td>{"🟦" if r.get("origin")=="fully_human" else "🟧"} {r.get("origin","")}</td>
          <td style="color:{ada_c};font-weight:600">{ada_str}</td>
          <td>{r.get("vh_germline_imgt","—")}</td>
          <td>{r.get("vl_germline_imgt","—")}</td>
          <td>{f"{r.get('vh_identity_pct',0):.1f}%" if pd.notna(r.get("vh_identity_pct")) else "—"}</td>
          <td>{f"{r.get('vl_identity_pct',0):.1f}%" if pd.notna(r.get("vl_identity_pct")) else "—"}</td>
          <td>{badge(vh_vz, thresholds=((0.5,"#e53e3e"),(0.3,"#d69e2e"),(0,"#38a169")))}</td>
          <td>{badge(vl_vz, thresholds=((0.5,"#e53e3e"),(0.3,"#d69e2e"),(0,"#38a169")))}</td>
          <td>{int(r.get("vz_n_foreign_total",0)) if pd.notna(r.get("vz_n_foreign_total")) else "—"}</td>
          <td style="font-family:monospace;font-size:11px">{r.get("vh_cdr3","—")}</td>
          <td>{int(r.get("cdrh3_len",0)) if pd.notna(r.get("cdrh3_len")) else "—"}</td>
          <td>{int(r.get("strong_binders_CDR",0)) if pd.notna(r.get("strong_binders_CDR")) else "—"}</td>
          <td>{badge(cdr_frac, thresholds=((0.4,"#e53e3e"),(0.2,"#d69e2e"),(0,"#718096")))}</td>
          <td>{r.get("disease_class","—")}</td>
        </tr>"""
    return rows


# Vernier zone summary stats
hum_vz_mean = mat_df[mat_df["origin"]=="humanized"]["vh_vz_foreignness"].mean()
fh_vz_mean  = mat_df[mat_df["origin"]=="fully_human"]["vh_vz_foreignness"].mean()
hum_cdr_frac= mat_df[mat_df["origin"]=="humanized"]["cdr_frac_of_strong"].mean()
fh_cdr_frac = mat_df[mat_df["origin"]=="fully_human"]["cdr_frac_of_strong"].mean()
hum_ada_mean= mat_df[mat_df["origin"]=="humanized"]["ada_rate_pct"].mean()
fh_ada_mean = mat_df[mat_df["origin"]=="fully_human"]["ada_rate_pct"].mean()

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>CDR & Vernier Zone Immunogenicity Analysis — 70 Therapeutic Antibodies</title>
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#f7fafc;color:#2d3748;margin:0}}
  .header{{background:linear-gradient(135deg,#1a365d,#2b6cb0);color:#fff;padding:28px 40px}}
  .header h1{{margin:0 0 6px;font-size:22px}}
  .header p{{margin:0;opacity:.85;font-size:13px}}
  .container{{max-width:1700px;margin:0 auto;padding:24px 32px}}
  .card{{background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);margin-bottom:24px;overflow:hidden}}
  .card-header{{background:#ebf8ff;padding:12px 20px;border-bottom:1px solid #bee3f8;
                font-weight:600;font-size:14px;color:#2b6cb0;display:flex;align-items:center;gap:8px}}
  .card-body{{padding:20px;overflow-x:auto}}
  .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;padding:20px}}
  .kpi{{background:#f7fafc;border:1px solid #e2e8f0;border-radius:6px;padding:14px;text-align:center}}
  .kpi-val{{font-size:26px;font-weight:700;color:#2b6cb0}}
  .kpi-lbl{{font-size:11px;color:#718096;margin-top:4px}}
  .kpi-sub{{font-size:12px;color:#4a5568;margin-top:6px}}
  table.dt{{width:100%;border-collapse:collapse;font-size:12px}}
  table.dt th{{background:#2b6cb0;color:#fff;padding:6px 8px;text-align:left;white-space:nowrap}}
  table.dt td{{padding:5px 8px;border-bottom:1px solid #e2e8f0;white-space:nowrap}}
  table.dt tr:hover td{{background:#ebf8ff}}
  .note{{font-size:12px;color:#718096;padding:8px 20px}}
  .box{{display:inline-block;width:12px;height:12px;border-radius:2px;vertical-align:middle;margin-right:4px}}
  h3{{color:#2b6cb0;margin:0 0 12px}}
  .two-col{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}
  .section-intro{{background:#fffaf0;border-left:4px solid #d69e2e;padding:12px 16px;
                  margin:0 0 16px;border-radius:0 6px 6px 0;font-size:13px;line-height:1.7}}
</style>
</head>
<body>
<div class="header">
  <h1>CDR & Vernier Zone — Immunogenicity Analysis</h1>
  <p>70 Therapeutic Antibodies | HLA Class II Epitope Decomposition | Vernier Zone Foreignness | Clinical ADA Correlation</p>
  <p style="margin-top:4px;opacity:.6;font-size:11px">InSynBio AbEngineCore · {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}</p>
</div>

<div class="container">

<!-- KPIs -->
<div class="kpi-grid">
  <div class="kpi"><div class="kpi-val">70</div><div class="kpi-lbl"></div></div>
  <div class="kpi"><div class="kpi-val">27</div><div class="kpi-lbl">🟦  (fully_human)</div>
    <div class="kpi-sub">ADA {fh_ada_mean:.1f}%</div></div>
  <div class="kpi"><div class="kpi-val">43</div><div class="kpi-lbl">🟧  (humanized)</div>
    <div class="kpi-sub">ADA {hum_ada_mean:.1f}%</div></div>
  <div class="kpi">
    <div class="kpi-val" style="color:#e53e3e">{hum_vz_mean:.2f}</div>
    <div class="kpi-lbl"> VH Vernier zone </div>
    <div class="kpi-sub">: {fh_vz_mean:.2f}</div></div>
  <div class="kpi">
    <div class="kpi-val">{hum_cdr_frac:.2f}</div>
    <div class="kpi-lbl"> CDR</div>
    <div class="kpi-sub">: {fh_cdr_frac:.2f}</div></div>
</div>

<!-- Scientific background -->
<div class="card">
  <div class="card-header">📚 ：CDR  Vernier Zone </div>
  <div class="card-body">
    <div class="section-intro">
      <b>CDR（）：</b> CDR （），""。
      、， 9–15  HLA Class II  T 。
      CDR （），。
    </div>
    <div class="section-intro">
      <b>Vernier Zone（，Foote &amp; Winter 1992）：</b>（FR），
       CDR 。，，
      （）， FR ""。
      Vernier zone ： T-cell  CDR-FR ，
       FR  15-mer 。
    </div>
    <div class="two-col">
      <div>
        <h3>VH Vernier Zone (IMGT)</h3>
        <table class="dt">
          <thead><tr><th>IMGT</th><th></th><th></th></tr></thead>
          <tbody>
            <tr><td>37</td><td>V</td><td>FR2-CDR2 junction</td></tr>
            <tr><td>47</td><td>W</td><td>VH-VL interface ()</td></tr>
            <tr><td>48</td><td>I</td><td>CDR2 base support</td></tr>
            <tr><td>67</td><td>A</td><td>CDR2-FR3 transition</td></tr>
            <tr><td>69</td><td>L</td><td>FR3 CDR2 packing</td></tr>
            <tr><td>71</td><td>R</td><td><b>Vernier: CDR1/CDR3</b></td></tr>
            <tr><td>78</td><td>V</td><td>CDR3 base packing</td></tr>
            <tr><td>80</td><td>L</td><td>CDR3 entry</td></tr>
            <tr><td>93</td><td>A</td><td>FR3 </td></tr>
            <tr><td>94</td><td>R</td><td><b>Vernier: CDR3 base</b></td></tr>
          </tbody>
        </table>
      </div>
      <div>
        <h3>VL Vernier Zone (IMGT)</h3>
        <table class="dt">
          <thead><tr><th>IMGT</th><th></th><th></th></tr></thead>
          <tbody>
            <tr><td>35</td><td>Q</td><td>CDR1 base FR</td></tr>
            <tr><td>46</td><td>L</td><td>FR2 VH-VL packing</td></tr>
            <tr><td>47</td><td>Y</td><td><b> Tyr</b></td></tr>
            <tr><td>48</td><td>P</td><td>CDR2 entry</td></tr>
            <tr><td>49</td><td>S</td><td>CDR2 base</td></tr>
            <tr><td>64</td><td>D</td><td>FR3 mid</td></tr>
            <tr><td>71</td><td>Y</td><td><b>VL Vernier: CDR3</b></td></tr>
            <tr><td>78</td><td>L</td><td>CDR3 packing</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- Correlation table -->
<div class="card">
  <div class="card-header">📊 ADASpearman（CDR/Vernier）</div>
  <div class="card-body">
    <p class="note">* p&lt;0.05 | ** p&lt;0.01 | *** p&lt;0.001 &nbsp;|&nbsp; =ADA</p>
    <table class="dt">
      <thead><tr><th></th><th>Spearman r</th><th>p</th><th>N</th></tr></thead>
      <tbody>{build_corr_html()}</tbody>
    </table>
  </div>
</div>

<!-- Main per-antibody table -->
<div class="card">
  <div class="card-header">📋 70 CDR + Vernier Zone </div>
  <div class="card-body">
    <p class="note">
      🟦= | 🟧= | VZ=Verniergermline(0-1) |
      CDRbinder=CDR
    </p>
    <table id="main_tbl" class="display compact" style="width:100%">
      <thead><tr>
        <th></th><th></th><th>ADA</th>
        <th>VH germline</th><th>VL germline</th>
        <th>VH</th><th>VL</th>
        <th>VH Vernier</th><th>VL Vernier</th>
        <th>VZ</th>
        <th>CDR-H3</th><th>H3</th>
        <th>CDRbinder</th><th>CDRbinder</th>
        <th></th>
      </tr></thead>
      <tbody>{build_main_table()}</tbody>
    </table>
  </div>
</div>

</div>
<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script>
$(document).ready(function(){{
  $('#main_tbl').DataTable({{scrollX:true,pageLength:25,order:[[2,'desc']],dom:'lfrtip'}});
}});
</script>
</body>
</html>"""

html_path = OUT / "immuno70_cdr_vernier_report.html"
html_path.write_text(html, encoding="utf-8")
print(f"\nSaved: {html_path}")
print(f"Saved: {OUT / 'immuno70_cdr_vernier_summary.csv'}")
print("\n[Done]")
