"""
build_immuno70_matrix.py
========================
Build a comprehensive multi-feature matrix for the 70 therapeutic antibodies,
merging:
  1. Sequences (confirmed70_sequences_full.csv)
  2. ABARCII CDR/FR/germline (anarcii_numbering_70.csv)
  3. ADA + origin + target + indication (confirmed70_human_humanized_germline_ada.csv + tiered_db)
  4. HLA Class II / MHC-II epitope features (mhcii_immuno_70_summary.csv)
  5. CMC sequence metrics (pI, instability, GRAVY, hydrophobic/charge patches, agg motifs)

Output:
  data/thera_sabdab/out/immuno70_full_matrix.csv
  data/thera_sabdab/out/immuno70_correlation_report.csv
  data/thera_sabdab/out/immuno70_matrix_report.html
"""
from __future__ import annotations
import sys, json, re, math
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT  = ROOT / "data" / "thera_sabdab" / "out"

# ── CMC metrics ────────────────────────────────────────────────────────────────
from core.cmc.cmc_metrics import (
    compute_pI, compute_instability_index, compute_GRAVY,
    compute_aggregation_motifs, compute_hydro_patch_max9,
    compute_charge_patch_max7, compute_net_charge,
    compute_hydro_cluster_count, compute_chemical_liabilities,
)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Load base data sources
# ══════════════════════════════════════════════════════════════════════════════
print("[1] Loading base data sources …")

seq_df = pd.read_csv(OUT / "confirmed70_sequences_full.csv")
arc_df = pd.read_csv(OUT / "anarcii_numbering_70.csv")
hla_df = pd.read_csv(OUT / "mhcii_immuno_70_summary.csv")
gda_df = pd.read_csv(OUT / "confirmed70_human_humanized_germline_ada.csv")

# tiered_db
t1 = json.loads((ROOT / "data/ADA_reliable_package/tiered_db/Tier1_Verified.json").read_text())["entries"]
t2 = json.loads((ROOT / "data/ADA_reliable_package/tiered_db/Tier2_Proprietary.json").read_text())["entries"]

# Build tiered_db lookup: antibody_name (lower) → entry dict with tier label
tiered: dict[str, dict] = {}
for e in t2:
    tiered[e["antibody_name"].lower()] = {
        "target": e.get("target", ""),
        "indication": e.get("indication", ""),
        "ada_value_raw": e.get("ada_value_ai", ""),
        "chain_origin_t2": e.get("chain_origin", ""),
        "ada_evidence_tier": "Tier2",
    }
for e in t1:  # T1 overrides T2
    tiered[e["antibody_name"].lower()] = {
        "target": e.get("target", ""),
        "indication": e.get("indication", ""),
        "ada_value_raw": e.get("ada_value_verified", ""),
        "chain_origin_t2": "",
        "ada_evidence_tier": "Tier1",
    }


# ══════════════════════════════════════════════════════════════════════════════
# 2. Pivot ABARCII: one row per antibody × arm (aggregate VH and VL separately)
# ══════════════════════════════════════════════════════════════════════════════
print("[2] Pivoting ABARCII data …")

def _pivot_arc(arc: pd.DataFrame, arm_label: str = "arm1") -> pd.DataFrame:
    """Pivot anarcii rows into one row per drug for VH and VL of a given arm."""
    rows = []
    arms = arc[arc["arm"] == arm_label]
    drugs = arms["drug"].unique()
    for drug in drugs:
        sub = arms[arms["drug"] == drug].set_index("chain_type")
        row = {"antibody_name": drug}
        for chain, prefix in [("H", "vh"), ("K", "vl"), ("L", "vl")]:
            if chain not in sub.index:
                continue
            r = sub.loc[chain]
            p = prefix
            for col in ["fr1","cdr1","fr2","cdr2","fr3","cdr3","fr4",
                        "cdr1_len","cdr2_len","cdr3_len",
                        "fr1_len","fr3_len",
                        "germline_anarcii","germline_anarcii_pct",
                        "germline_family","germline_842csv"]:
                row[f"{p}_{col}"] = r.get(col, None)
        rows.append(row)
    return pd.DataFrame(rows)

arc_pivot = _pivot_arc(arc_df, arm_label="arm1")


# ══════════════════════════════════════════════════════════════════════════════
# 3. Parse ADA numeric value
# ══════════════════════════════════════════════════════════════════════════════
print("[3] Parsing ADA numeric values …")

def parse_ada_pct(s: str) -> float | None:
    """Extract the first numeric % value from a free-text ADA string."""
    if not s or str(s).strip().lower() in ("nan", "none", ""):
        return None
    # Look for patterns like "30%", "4.8%", "85%"
    m = re.search(r"(\d+\.?\d*)\s*%", str(s))
    if m:
        return float(m.group(1))
    # "no … antibodies" → 0
    if re.search(r"no\b.*\bantibod", str(s).lower()):
        return 0.0
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 4. Compute CMC sequence metrics per antibody
# ══════════════════════════════════════════════════════════════════════════════
print("[4] Computing CMC sequence metrics …")

def _cmc_for_seq(vh: str, vl: str) -> dict:
    full = (vh or "") + (vl or "")
    if not full.strip():
        return {}
    try:
        liab = compute_chemical_liabilities(full)
        return {
            "cmc_pI":              compute_pI(full),
            "cmc_instability":     compute_instability_index(full),
            "cmc_GRAVY":           compute_GRAVY(full),
            "cmc_agg_motifs":      compute_aggregation_motifs(full),
            "cmc_hydro_patch_max9":compute_hydro_patch_max9(full),
            "cmc_charge_patch_max7":compute_charge_patch_max7(full),
            "cmc_net_charge_7_4":  compute_net_charge(full, pH=7.4),
            "cmc_hydro_cluster":   compute_hydro_cluster_count(full),
            "cmc_deamidation":     liab.get("deamidation", 0),
            "cmc_isomerization":   liab.get("isomerization", 0),
            "cmc_oxidation":       liab.get("oxidation", 0),
            "cmc_glycosylation":   liab.get("glycosylation", 0),
            "cmc_free_cys":        liab.get("free_cys", 0),
        }
    except Exception as ex:
        return {"cmc_error": str(ex)}

cmc_rows = []
for _, r in seq_df.iterrows():
    vh = str(r.get("arm1_heavy_aa", "") or "").strip()
    vl = str(r.get("arm1_light_aa", "") or "").strip()
    d = _cmc_for_seq(vh, vl)
    d["antibody_name"] = r["antibody_name"]
    cmc_rows.append(d)
cmc_df = pd.DataFrame(cmc_rows)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Classify disease area / target class from indication
# ══════════════════════════════════════════════════════════════════════════════
def _disease_class(indication: str) -> str:
    ind = str(indication).lower()
    if any(k in ind for k in ["arthritis","lupus","ibd","crohn","colitis","psoriasis","ms ","sclerosis","spondylitis","myasthenia","ankylos"]):
        return "Autoimmune"
    if any(k in ind for k in ["cancer","leukemia","lymphoma","melanoma","carcinoma","myeloma","sarcoma","tumor","tumour","oncol","aml","cll","crc","nsclc","hcc"]):
        return "Oncology"
    if any(k in ind for k in ["asthma","copd","atopic","eczema","urticaria","rhinitis","allerg"]):
        return "Allergy/Respiratory"
    if any(k in ind for k in ["covid","infect","rsv","influenza","bacteria","bacterial","hiv","ebola","anthrax","clostr"]):
        return "Infectious/Antitoxin"
    if any(k in ind for k in ["osteoporosis","bone","denosumab"]):
        return "Bone/Metabolic"
    if any(k in ind for k in ["macular","ophthal","eye","retinal"]):
        return "Ophthalmology"
    if any(k in ind for k in ["alzheimer","neurol","parkinson","amyloid"]):
        return "Neurology"
    if any(k in ind for k in ["cardiac","heart","atherosclerosis","cholesterol","ldl","hyperlipid","cardiovasc"]):
        return "Cardiovascular"
    if any(k in ind for k in ["transplant","rejection","graft"]):
        return "Transplant"
    return "Other"

def _target_class(target: str) -> str:
    t = str(target).lower()
    if any(k in t for k in ["pd-1","pd-l1","ctla-4","lag-3","tim-3","tigit"]):
        return "Checkpoint"
    if any(k in t for k in ["il-","interleukin","il6","il4","il13","il17","il23","il33","tslp"]):
        return "Interleukin"
    if any(k in t for k in ["tnf","vegf","egfr","her2","cd20","cd19","cd38","cd52","cd3","bcma","rankl","pcsk9","ang"]):
        return "Surface/Growth"
    if any(k in t for k in ["ige","igg","igm"]):
        return "Immunoglobulin"
    return "Other"


# ══════════════════════════════════════════════════════════════════════════════
# 6. Merge everything into unified matrix
# ══════════════════════════════════════════════════════════════════════════════
print("[5] Merging into unified matrix …")

base = seq_df[["antibody_name","thera_format"]].copy()

# -- join germline / origin / ADA from confirmed70_human_humanized_germline_ada
gda_cols = ["antibody_name","thera_genetics_class","ada_value_display","ada_first_pct",
            "vh_germline","vl_germline","vh_family","vl_family",
            "vh_identity_imgt","vl_identity_imgt"]
base = base.merge(gda_df[gda_cols], on="antibody_name", how="left")
base.rename(columns={
    "thera_genetics_class": "origin",
    "ada_value_display": "ada_value_text",
    "ada_first_pct": "ada_rate_pct_primary",
    "vh_germline": "vh_germline_imgt",
    "vl_germline": "vl_germline_imgt",
    "vh_identity_imgt": "vh_identity_pct",
    "vl_identity_imgt": "vl_identity_pct",
}, inplace=True)

# -- add tiered_db fields: target, indication, parsed ADA, disease class
tdb_rows = []
for name in base["antibody_name"]:
    e = tiered.get(name.lower(), {})
    raw_ada = e.get("ada_value_raw", "")
    parsed  = parse_ada_pct(raw_ada)
    tdb_rows.append({
        "antibody_name":    name,
        "target":           e.get("target", ""),
        "indication":       e.get("indication", ""),
        "ada_rate_pct_db":  parsed,
        "ada_evidence_tier":e.get("ada_evidence_tier", ""),
    })
tdb_df = pd.DataFrame(tdb_rows)
base = base.merge(tdb_df, on="antibody_name", how="left")

# Consolidate ADA rate: prefer primary (already numeric), fallback to tiered_db parsed
base["ada_rate_pct"] = base["ada_rate_pct_primary"].combine_first(base["ada_rate_pct_db"])

# Disease + target class
base["disease_class"] = base["indication"].apply(_disease_class)
base["target_class"]  = base["target"].apply(_target_class)

# Origin numeric: fully_human=0, humanized=1
base["origin_code"] = base["origin"].map({"fully_human": 0, "humanized": 1}).fillna(0.5)

# -- join ABARCII CDR/germline pivot
arc_cols = [c for c in arc_pivot.columns if c != "antibody_name"]
base = base.merge(arc_pivot, on="antibody_name", how="left")

# CDR-H3 length from ABARCII (prefer vh_cdr3_len)
base["cdrh3_len"] = pd.to_numeric(base.get("vh_cdr3_len"), errors="coerce")
base["cdrl3_len"] = pd.to_numeric(base.get("vl_cdr3_len"), errors="coerce")

# -- join HLA/MHC-II features (rename 'antibody' → 'antibody_name')
hla_df2 = hla_df.rename(columns={"antibody": "antibody_name"})
hla_cols = ["antibody_name","clinical_ada_score","clinical_ada_risk","mhcii_risk",
            "n_strong_binders","n_clusters","net_immunogenic_burden",
            "n_hydrophilic_patches","frac_exposed_vh","frac_exposed_vl",
            "mean_sasa_vh","mean_sasa_vl","vh_len","vl_len"]
base = base.merge(hla_df2[hla_cols], on="antibody_name", how="left")

# -- join CMC metrics
base = base.merge(cmc_df, on="antibody_name", how="left")

print(f"  Matrix shape: {base.shape}")


# ══════════════════════════════════════════════════════════════════════════════
# 7. Correlation analysis
# ══════════════════════════════════════════════════════════════════════════════
print("[6] Computing correlations with ada_rate_pct …")

from scipy.stats import spearmanr, pearsonr

corr_df = base[base["ada_rate_pct"].notna()].copy()
print(f"  Antibodies with numeric ADA rate: {len(corr_df)}")

feature_cols = [
    # MHC-II
    "clinical_ada_score","n_strong_binders","n_clusters","net_immunogenic_burden",
    "n_hydrophilic_patches","frac_exposed_vh","frac_exposed_vl",
    "mean_sasa_vh","mean_sasa_vl",
    # Germline identity
    "vh_identity_pct","vl_identity_pct",
    # Origin
    "origin_code",
    # CDR lengths
    "cdrh3_len","cdrl3_len",
    # CMC
    "cmc_pI","cmc_instability","cmc_GRAVY",
    "cmc_agg_motifs","cmc_hydro_patch_max9","cmc_charge_patch_max7",
    "cmc_net_charge_7_4","cmc_hydro_cluster",
    "cmc_deamidation","cmc_isomerization","cmc_oxidation",
]

corr_rows = []
for fc in feature_cols:
    if fc not in corr_df.columns:
        corr_rows.append({"feature": fc, "spearman_r": None, "pearson_r": None, "n": 0})
        continue
    sub = corr_df[["ada_rate_pct", fc]].dropna()
    if len(sub) < 5:
        corr_rows.append({"feature": fc, "spearman_r": None, "pearson_r": None, "n": len(sub)})
        continue
    sr, sp = spearmanr(sub["ada_rate_pct"], sub[fc])
    pr, pp = pearsonr(sub["ada_rate_pct"], sub[fc])
    corr_rows.append({"feature": fc, "spearman_r": round(sr, 3), "pearson_r": round(pr, 3),
                      "spearman_p": round(sp, 4), "n": len(sub)})

corr_report = pd.DataFrame(corr_rows).sort_values("spearman_r", ascending=False, key=abs)
print("\n  Top correlations with ADA rate:")
print(corr_report.head(15).to_string(index=False))

# Save outputs
base.to_csv(OUT / "immuno70_full_matrix.csv", index=False)
corr_report.to_csv(OUT / "immuno70_correlation_report.csv", index=False)
print(f"\n  Saved: {OUT / 'immuno70_full_matrix.csv'}")
print(f"  Saved: {OUT / 'immuno70_correlation_report.csv'}")


# ══════════════════════════════════════════════════════════════════════════════
# 8. HTML report
# ══════════════════════════════════════════════════════════════════════════════
print("[7] Generating HTML report …")

# Summary stats per disease class
class_summary = corr_df.groupby("disease_class").agg(
    n=("antibody_name","count"),
    ada_mean=("ada_rate_pct","mean"),
    ada_median=("ada_rate_pct","median"),
    ada_std=("ada_rate_pct","std"),
    mhcii_score_mean=("clinical_ada_score","mean"),
    hum_frac=("origin_code", lambda x: (x == 0).mean())
).round(2).reset_index()

# Origin breakdown
origin_summary = corr_df.groupby("origin").agg(
    n=("antibody_name","count"),
    ada_mean=("ada_rate_pct","mean"),
    ada_std=("ada_rate_pct","std"),
).round(2).reset_index()

# Build display table: select key columns
display_cols = [
    "antibody_name","origin","thera_format","disease_class","target_class","target",
    "ada_rate_pct","ada_evidence_tier",
    "vh_germline_imgt","vl_germline_imgt","vh_family","vl_family",
    "vh_identity_pct","vl_identity_pct",
    "cdrh3_len","cdrl3_len",
    "clinical_ada_score","clinical_ada_risk",
    "n_strong_binders","n_clusters","net_immunogenic_burden",
    "n_hydrophilic_patches","frac_exposed_vh",
    "cmc_pI","cmc_instability","cmc_GRAVY",
    "cmc_agg_motifs","cmc_hydro_patch_max9","cmc_charge_patch_max7",
    "cmc_net_charge_7_4","cmc_deamidation","cmc_oxidation",
]
display_cols = [c for c in display_cols if c in base.columns]
display_df = base[display_cols].sort_values("antibody_name")


def df_to_html_table(df: pd.DataFrame, table_id: str = "tbl", max_rows: int = 200) -> str:
    """Render a DataFrame as a styled HTML table."""
    rows_html = ""
    for _, row in df.head(max_rows).iterrows():
        cells = ""
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                cells += "<td>—</td>"
            elif isinstance(val, float):
                cells += f"<td>{val:.2f}</td>"
            else:
                cells += f"<td>{val}</td>"
        rows_html += f"<tr>{cells}</tr>\n"
    headers = "".join(f"<th>{c}</th>" for c in df.columns)
    return f"""<table id="{table_id}" class="display compact" style="width:100%">
<thead><tr>{headers}</tr></thead>
<tbody>{rows_html}</tbody></table>"""


def risk_badge(risk: str) -> str:
    colors = {"HIGH": "#e53e3e", "MEDIUM": "#d69e2e", "LOW": "#38a169", "UNKNOWN": "#718096"}
    c = colors.get(str(risk).upper(), "#718096")
    return f'<span style="background:{c};color:#fff;padding:2px 6px;border-radius:4px;font-size:11px;">{risk}</span>'


html_corr_rows = ""
for _, r in corr_report.iterrows():
    sr = r.get("spearman_r")
    pr = r.get("pearson_r")
    bar_w = int(abs(sr) * 100) if pd.notna(sr) else 0
    bar_c = "#e53e3e" if (sr or 0) > 0 else "#3182ce"
    html_corr_rows += f"""<tr>
      <td>{r['feature']}</td>
      <td>{f"{sr:.3f}" if pd.notna(sr) else "—"}
        <div style="display:inline-block;width:{bar_w}px;height:8px;background:{bar_c};margin-left:6px;vertical-align:middle;border-radius:3px;"></div>
      </td>
      <td>{f"{pr:.3f}" if pd.notna(pr) else "—"}</td>
      <td>{int(r['n']) if pd.notna(r.get('n')) else 0}</td>
    </tr>"""


class_rows = "".join(
    f"<tr><td>{r['disease_class']}</td><td>{int(r['n'])}</td>"
    f"<td>{r['ada_mean']:.1f}%</td><td>{r['ada_median']:.1f}%</td>"
    f"<td>{r['ada_std']:.1f}</td><td>{r['mhcii_score_mean']:.3f}</td>"
    f"<td>{r['hum_frac']*100:.0f}%</td></tr>"
    for _, r in class_summary.iterrows()
)

origin_rows = "".join(
    f"<tr><td>{r['origin']}</td><td>{int(r['n'])}</td><td>{r['ada_mean']:.1f}%</td><td>{r['ada_std']:.1f}</td></tr>"
    for _, r in origin_summary.iterrows()
)

# Top correlated features highlight text
top3 = corr_report.dropna(subset=["spearman_r"]).head(3)["feature"].tolist()

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>70-Antibody Immunogenicity Multi-Feature Matrix</title>
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#f7fafc;color:#2d3748;margin:0;padding:0}}
  .header{{background:linear-gradient(135deg,#1a365d 0%,#2b6cb0 100%);color:white;padding:32px 40px}}
  .header h1{{margin:0 0 8px;font-size:24px}}
  .header p{{margin:0;opacity:.85;font-size:14px}}
  .container{{max-width:1600px;margin:0 auto;padding:24px 32px}}
  .card{{background:white;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);margin-bottom:24px;overflow:hidden}}
  .card-header{{background:#ebf8ff;padding:14px 20px;border-bottom:1px solid #bee3f8;font-weight:600;font-size:15px;color:#2b6cb0}}
  .card-body{{padding:20px;overflow-x:auto}}
  .metric-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px;padding:20px}}
  .metric-box{{background:#f7fafc;border:1px solid #e2e8f0;border-radius:6px;padding:14px;text-align:center}}
  .metric-val{{font-size:28px;font-weight:700;color:#2b6cb0}}
  .metric-lbl{{font-size:12px;color:#718096;margin-top:4px}}
  table.dt{{width:100%;border-collapse:collapse;font-size:12px}}
  table.dt th{{background:#2b6cb0;color:white;padding:6px 10px;text-align:left;white-space:nowrap}}
  table.dt td{{padding:5px 10px;border-bottom:1px solid #e2e8f0;white-space:nowrap}}
  table.dt tr:hover td{{background:#ebf8ff}}
  .corr-pos{{color:#e53e3e;font-weight:600}}
  .corr-neg{{color:#3182ce;font-weight:600}}
  .section-note{{font-size:12px;color:#718096;margin:8px 20px 0}}
</style>
</head>
<body>
<div class="header">
  <h1>70 Therapeutic Antibody — Immunogenicity Multi-Feature Matrix</h1>
  <p>ADA · Sequence · Germline · CDR · Structure · HLA Class II Epitopes · CMC Metrics · Disease/Target Class · Origin</p>
  <p style="margin-top:6px;opacity:.7;font-size:12px">Generated {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")} | InSynBio AbEngineCore</p>
</div>

<div class="container">

<!-- Overview KPIs -->
<div class="metric-grid">
  <div class="metric-box"><div class="metric-val">{len(base)}</div><div class="metric-lbl"></div></div>
  <div class="metric-box"><div class="metric-val">{len(corr_df)}</div><div class="metric-lbl">ADA</div></div>
  <div class="metric-box"><div class="metric-val">{(base["origin"]=="fully_human").sum()}</div><div class="metric-lbl"></div></div>
  <div class="metric-box"><div class="metric-val">{(base["origin"]=="humanized").sum()}</div><div class="metric-lbl"></div></div>
  <div class="metric-box"><div class="metric-val">{corr_df["ada_rate_pct"].mean():.1f}%</div><div class="metric-lbl">ADA</div></div>
  <div class="metric-box"><div class="metric-val">{corr_df["ada_rate_pct"].median():.1f}%</div><div class="metric-lbl">ADA</div></div>
  <div class="metric-box"><div class="metric-val">{base["disease_class"].nunique()}</div><div class="metric-lbl"></div></div>
  <div class="metric-box"><div class="metric-val">{base["clinical_ada_score"].mean():.3f}</div><div class="metric-lbl">MHC-II</div></div>
</div>

<!-- Feature Correlation Table -->
<div class="card">
  <div class="card-header">📊 ADA（Spearman + Pearson r）</div>
  <div class="card-body">
    <p class="section-note"> =  ADA  |  =  ADA  | Top 3 : {", ".join(top3)}</p>
    <table class="dt">
      <thead><tr><th></th><th>Spearman r</th><th>Pearson r</th><th>N</th></tr></thead>
      <tbody>{html_corr_rows}</tbody>
    </table>
  </div>
</div>

<!-- Disease Class Summary -->
<div class="card">
  <div class="card-header">🏥  — ADA</div>
  <div class="card-body">
    <table class="dt">
      <thead><tr><th></th><th>N</th><th>ADA</th><th>ADA</th><th>ADA</th><th>MHC-II</th><th></th></tr></thead>
      <tbody>{class_rows}</tbody>
    </table>
  </div>
</div>

<!-- Origin Summary -->
<div class="card">
  <div class="card-header">🧬  — ADA</div>
  <div class="card-body">
    <table class="dt">
      <thead><tr><th></th><th>N</th><th>ADA</th><th>ADA</th></tr></thead>
      <tbody>{origin_rows}</tbody>
    </table>
    <p class="section-note">fully_human = （/）；humanized = </p>
  </div>
</div>

<!-- Full Matrix Table -->
<div class="card">
  <div class="card-header">📋 （70  × ）</div>
  <div class="card-body">
    {df_to_html_table(display_df, table_id="main_tbl")}
  </div>
</div>

</div>

<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script>
$(document).ready(function(){{
  $('#main_tbl').DataTable({{
    scrollX: true, pageLength: 25, order: [[6, 'desc']],
    dom: 'lfrtip'
  }});
}});
</script>
</body>
</html>"""

html_path = OUT / "immuno70_matrix_report.html"
html_path.write_text(html, encoding="utf-8")
print(f"  Saved: {html_path}")
print("\n[Done] All outputs written to", OUT)
