"""
build_immunogenicity_decomposition_report.py
=============================================
Generate a comprehensive HTML report visualizing three immunogenicity
computation modules for all 70 therapeutic antibodies:

  1. Germline Tolerance Filter
       tolerance = sigmoid(f_max_germline)
       net_contribution = allele_weight × (1 – tolerance)
       net_immunogenic_burden = Σ net_contribution

  2. Surface Hydrophilicity (n_hydrophilic_patches / SASA)
       PDB mode: freesasa per residue; patch = SASA > 20 Å²
       Fallback: Parker hydrophilicity scale on sequence

  3. Strong Epitope Clustering (spatial hotspot)
       Cluster = ≥3 non-tolerant strong binders within 15-residue window
       Reports n_clusters, region (FR/CDR/MIXED), net_cluster_burden
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT  = ROOT / "data" / "thera_sabdab" / "out"
REF  = ROOT / "data" / "reference"

# ── Load data ─────────────────────────────────────────────────────────────────
epi = pd.read_csv(OUT / "mhcii_immuno_70_epitopes.csv")
hla = pd.read_csv(OUT / "mhcii_immuno_70_summary.csv")
mat = pd.read_csv(OUT / "immuno70_full_matrix.csv")
route = pd.read_csv(REF / "route_and_context.csv")[
    ["antibody_name", "route", "oncology_indication"]]

mat = mat.merge(route, on="antibody_name", how="left")
hla_ada = hla.merge(
    mat[["antibody_name", "ada_rate_pct", "origin", "disease_class"]].rename(
        columns={"antibody_name": "antibody"}),
    on="antibody", how="left")

# ══════════════════════════════════════════════════════════════════════════════
# Module 1: Tolerogenic decomposition per antibody
# ══════════════════════════════════════════════════════════════════════════════
STRONG_THRESH = 2.0

strong = epi[epi["percentile_rank"] <= STRONG_THRESH].copy()
strong["is_tolerogenic"]  = strong["tolerance"] >= 0.8
strong["is_immunogenic"]  = strong["tolerance"] <  0.2
strong["is_intermediate"] = ~strong["is_tolerogenic"] & ~strong["is_immunogenic"]

tol_rows = []
for ab, grp in strong.groupby("antibody"):
    n_total  = len(grp)
    n_tol    = grp["is_tolerogenic"].sum()
    n_immuno = grp["is_immunogenic"].sum()
    n_inter  = grp["is_intermediate"].sum()
    net_b    = grp["net_contribution"].sum()
    raw_b    = grp["allele_weight"].sum()
    tol_rows.append({
        "antibody": ab,
        "n_strong_total":    int(n_total),
        "n_tolerogenic":     int(n_tol),
        "n_immunogenic":     int(n_immuno),
        "n_intermediate":    int(n_inter),
        "pct_tolerogenic":   round(n_tol / n_total * 100, 1) if n_total else 0,
        "pct_immunogenic":   round(n_immuno / n_total * 100, 1) if n_total else 0,
        "net_burden":        round(float(net_b), 4),
        "raw_burden":        round(float(raw_b), 4),
        "tolerance_reduction_pct": round((1 - net_b / raw_b) * 100, 1) if raw_b > 0 else 0,
    })
tol_df = pd.DataFrame(tol_rows)
tol_df = tol_df.merge(
    mat[["antibody_name", "ada_rate_pct", "origin", "disease_class", "route"]].rename(
        columns={"antibody_name": "antibody"}),
    on="antibody", how="left")
tol_df = tol_df.sort_values("net_burden", ascending=False)

# ══════════════════════════════════════════════════════════════════════════════
# Correlations (all three modules)
# ══════════════════════════════════════════════════════════════════════════════
def spear(a, b):
    sub = pd.DataFrame({"x": a, "y": b}).dropna()
    if len(sub) < 10: return (None, None, len(sub))
    r, p = spearmanr(sub["x"], sub["y"])
    return (round(r, 3), round(p, 4), len(sub))

corr_metrics = {
    "net_immunogenic_burden":    hla_ada["net_immunogenic_burden"],
    "n_strong_binders":          hla_ada["n_strong_binders"],
    "n_clusters":                hla_ada["n_clusters"],
    "frac_exposed_vh":           hla_ada["frac_exposed_vh"],
    "frac_exposed_vl":           hla_ada["frac_exposed_vl"],
    "n_hydrophilic_patches":     hla_ada["n_hydrophilic_patches"],
    "mean_sasa_vh":              hla_ada["mean_sasa_vh"],
    "score_S_surface":           hla_ada["score_S_surface"],
}
ada_vals = hla_ada["ada_rate_pct"]
corr_table = []
for name, vals in corr_metrics.items():
    r, p, n = spear(ada_vals, vals)
    corr_table.append({"metric": name, "spearman_r": r, "p": p, "n": n})
corr_df = pd.DataFrame(corr_table)


# ══════════════════════════════════════════════════════════════════════════════
# HTML generation helpers
# ══════════════════════════════════════════════════════════════════════════════
def origin_badge(orig):
    if str(orig) == "fully_human":
        return '<span style="background:#3182ce;color:#fff;padding:1px 5px;border-radius:3px;font-size:10px">FH</span>'
    return '<span style="background:#d69e2e;color:#fff;padding:1px 5px;border-radius:3px;font-size:10px">HZ</span>'


def ada_badge(ada):
    if pd.isna(ada): return "—"
    v = float(ada)
    c = "#e53e3e" if v > 20 else ("#d69e2e" if v > 5 else "#38a169")
    return f'<span style="color:{c};font-weight:600">{v:.1f}%</span>'


def stacked_bar(tol, immuno, inter, total, width=120):
    """Return HTML stacked bar for tolerogenic/intermediate/immunogenic ratio."""
    if total == 0: return ""
    w_t = round(tol / total * width)
    w_i = round(immuno / total * width)
    w_m = max(0, width - w_t - w_i)
    return (
        f'<div style="display:flex;width:{width}px;height:12px;border-radius:3px;overflow:hidden">'
        f'<div style="width:{w_t}px;background:#38a169" title="Tolerogenic:{tol}"></div>'
        f'<div style="width:{w_m}px;background:#e2e8f0" title="Intermediate:{inter}"></div>'
        f'<div style="width:{w_i}px;background:#e53e3e" title="Immunogenic:{immuno}"></div>'
        f'</div>'
    )


def cluster_dots(n):
    if pd.isna(n): return "—"
    n = int(n)
    dots = ""
    for i in range(min(n, 7)):
        c = "#e53e3e" if n >= 5 else ("#d69e2e" if n >= 3 else "#3182ce")
        dots += f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{c};margin-right:2px"></span>'
    return dots + f' <small style="color:#718096">{n}</small>'


def surface_bar(val, max_val=10, label=""):
    if pd.isna(val): return "—"
    v = float(val)
    w = int(v / max_val * 80)
    c = "#e53e3e" if v > 6 else ("#d69e2e" if v > 3 else "#38a169")
    return (f'<div style="display:flex;align-items:center;gap:4px">'
            f'<div style="width:{w}px;height:10px;background:{c};border-radius:2px"></div>'
            f'<small>{v:.1f}{label}</small></div>')


# ══════════════════════════════════════════════════════════════════════════════
# Module 1 HTML table
# ══════════════════════════════════════════════════════════════════════════════
tol_rows_html = ""
for _, r in tol_df.iterrows():
    tol_rows_html += f"""<tr>
      <td><b>{r['antibody']}</b></td>
      <td>{origin_badge(r.get('origin',''))}</td>
      <td>{ada_badge(r.get('ada_rate_pct'))}</td>
      <td>{int(r['n_strong_total'])}</td>
      <td>{stacked_bar(r['n_tolerogenic'],r['n_immunogenic'],r['n_intermediate'],r['n_strong_total'])}
          <small style="color:#718096">&nbsp;{r['pct_tolerogenic']:.0f}% tol / {r['pct_immunogenic']:.0f}% immuno</small>
      </td>
      <td style="font-weight:600;color:#e53e3e">{r['net_burden']:.4f}</td>
      <td style="color:#718096">{r['raw_burden']:.4f}</td>
      <td style="color:#38a169">−{r['tolerance_reduction_pct']:.0f}%</td>
      <td style="color:#718096;font-size:11px">{r.get('disease_class','')}</td>
    </tr>"""

# ══════════════════════════════════════════════════════════════════════════════
# Module 2+3 HTML table (surface + cluster)
# ══════════════════════════════════════════════════════════════════════════════
hla_sorted = hla_ada.sort_values("net_immunogenic_burden", ascending=False)
surf_rows_html = ""
for _, r in hla_sorted.iterrows():
    mode = r.get("surface_mode", "")
    mode_badge = (
        '<span style="background:#276749;color:#fff;padding:1px 4px;border-radius:2px;font-size:10px">PDB</span>'
        if "PDB" in str(mode) else
        '<span style="background:#553c9a;color:#fff;padding:1px 4px;border-radius:2px;font-size:10px">freeSASA</span>'
        if "freesasa" in str(mode) else
        '<span style="background:#718096;color:#fff;padding:1px 4px;border-radius:2px;font-size:10px">Parker</span>'
    )
    surf_rows_html += f"""<tr>
      <td><b>{r['antibody']}</b></td>
      <td>{origin_badge(r.get('origin',''))}</td>
      <td>{ada_badge(r.get('ada_rate_pct'))}</td>
      <td>{mode_badge}</td>
      <td>{surface_bar(r.get('n_hydrophilic_patches'), max_val=12)}</td>
      <td>{f"{r['frac_exposed_vh']:.3f}" if pd.notna(r.get("frac_exposed_vh")) else "—"}</td>
      <td>{f"{r['mean_sasa_vh']:.1f} Å²" if pd.notna(r.get("mean_sasa_vh")) else "—"}</td>
      <td>{cluster_dots(r.get('n_clusters'))}</td>
      <td style="font-weight:600;color:#e53e3e">{r['net_immunogenic_burden']:.4f}</td>
      <td>{f"{r['n_strong_binders']:.0f}" if pd.notna(r.get("n_strong_binders")) else "—"}</td>
      <td style="color:#718096;font-size:11px">{r.get('clinical_ada_risk','')}</td>
    </tr>"""

# ══════════════════════════════════════════════════════════════════════════════
# Correlation table HTML
# ══════════════════════════════════════════════════════════════════════════════
corr_html = ""
for _, r in corr_df.iterrows():
    sr = r.get("spearman_r")
    p  = r.get("p")
    if sr is None:
        corr_html += f'<tr><td>{r["metric"]}</td><td colspan="3" style="color:#718096">n&lt;10</td></tr>'
        continue
    if sr is None or (isinstance(sr, float) and np.isnan(sr)):
        corr_html += f'<tr><td>{r["metric"]}</td><td colspan="3" style="color:#718096">—</td></tr>'
        continue
    bar_w = int(abs(sr) * 100)
    bar_c = "#e53e3e" if sr > 0 else "#3182ce"
    star = "***" if (p or 1) < 0.001 else ("**" if (p or 1) < 0.01 else ("*" if (p or 1) < 0.05 else ""))
    corr_html += (
        f'<tr><td><b>{r["metric"]}</b></td>'
        f'<td>{sr:+.3f} {star}'
        f'<div style="display:inline-block;width:{bar_w}px;height:7px;background:{bar_c};'
        f'margin-left:6px;vertical-align:middle;border-radius:2px"></div></td>'
        f'<td style="color:#718096">{p:.4f}</td>'
        f'<td>{int(r["n"])}</td></tr>\n'
    )

# ── Summary stats ─────────────────────────────────────────────────────────────
mean_tol_pct    = tol_df["pct_tolerogenic"].mean()
mean_immuno_pct = tol_df["pct_immunogenic"].mean()
mean_tol_reduce = tol_df["tolerance_reduction_pct"].mean()
mean_clusters   = hla["n_clusters"].mean()
max_clusters    = hla["n_clusters"].max()
parker_n        = (hla["surface_mode"] == "parker_scale").sum()
pdb_n           = hla["pdb_used"].sum()

# ══════════════════════════════════════════════════════════════════════════════
# Final HTML
# ══════════════════════════════════════════════════════════════════════════════
html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title> — 70 Antibodies</title>
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#f7fafc;color:#2d3748;margin:0}}
  .header{{background:linear-gradient(135deg,#1a365d,#2b6cb0);color:#fff;padding:28px 40px}}
  .header h1{{margin:0 0 6px;font-size:22px}}
  .header p{{margin:0;opacity:.85;font-size:13px}}
  .container{{max-width:1700px;margin:0 auto;padding:24px 32px}}
  .card{{background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);margin-bottom:28px;overflow:hidden}}
  .card-header{{padding:14px 20px;border-bottom:1px solid #e2e8f0;font-weight:700;font-size:15px;
                display:flex;align-items:center;gap:10px}}
  .card-body{{padding:20px;overflow-x:auto}}
  .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:16px;padding:20px}}
  .kpi{{background:#f7fafc;border:1px solid #e2e8f0;border-radius:6px;padding:14px;text-align:center}}
  .kpi-val{{font-size:26px;font-weight:700;color:#2b6cb0}}
  .kpi-lbl{{font-size:11px;color:#718096;margin-top:4px;line-height:1.4}}
  table.dt{{width:100%;border-collapse:collapse;font-size:12px}}
  table.dt th{{background:#2b6cb0;color:#fff;padding:7px 9px;text-align:left;white-space:nowrap}}
  table.dt td{{padding:5px 9px;border-bottom:1px solid #e2e8f0;vertical-align:middle}}
  table.dt tr:hover td{{background:#ebf8ff}}
  .formula-box{{background:#1a202c;color:#f6e05e;padding:14px 18px;border-radius:6px;
                font-family:monospace;font-size:13px;line-height:1.8;margin-bottom:16px}}
  .algo-block{{background:#f0fff4;border:1px solid #9ae6b4;border-radius:6px;
               padding:12px 16px;margin-bottom:12px;font-size:13px;line-height:1.7}}
  .legend{{display:flex;gap:16px;margin-bottom:10px;font-size:12px;align-items:center}}
  .legend-item{{display:flex;align-items:center;gap:5px}}
  .dot{{width:12px;height:12px;border-radius:2px;display:inline-block}}
  .note{{font-size:12px;color:#718096;padding:0 20px 10px}}
  .warn{{background:#fffbeb;border-left:4px solid #d69e2e;padding:8px 14px;font-size:12px;
         color:#744210;border-radius:0 4px 4px 0;margin-bottom:12px}}
</style>
</head>
<body>

<div class="header">
  <h1> · 70 Therapeutic Antibodies</h1>
  <p>① （Germline Tolerance）&nbsp;|&nbsp;
     ② （Surface Hydrophilicity / SASA）&nbsp;|&nbsp;
     ③ （Epitope Clustering Hotspots）</p>
  <p style="opacity:.6;font-size:11px;margin-top:4px">
    InSynBio AbEngineCore · {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")} · 35-allele DRB1 panel
  </p>
</div>

<div class="container">

<!-- KPIs -->
<div class="kpi-grid">
  <div class="kpi">
    <div class="kpi-val" style="color:#38a169">{mean_tol_pct:.0f}%</div>
    <div class="kpi-lbl"> tolerogenic </div>
  </div>
  <div class="kpi">
    <div class="kpi-val" style="color:#e53e3e">{mean_immuno_pct:.0f}%</div>
    <div class="kpi-lbl"> immunogenic </div>
  </div>
  <div class="kpi">
    <div class="kpi-val" style="color:#3182ce">−{mean_tol_reduce:.0f}%</div>
    <div class="kpi-lbl">（）</div>
  </div>
  <div class="kpi">
    <div class="kpi-val">{mean_clusters:.1f}</div>
    <div class="kpi-lbl">（max={int(max_clusters)}）</div>
  </div>
  <div class="kpi">
    <div class="kpi-val">{int(pdb_n)}</div>
    <div class="kpi-lbl">PDB（/{hla.shape[0]}）</div>
  </div>
  <div class="kpi">
    <div class="kpi-val" style="color:#718096">{int(parker_n)}</div>
    <div class="kpi-lbl">Parker scale（PDB）</div>
  </div>
</div>

<!-- Module 1: Tolerance -->
<div class="card">
  <div class="card-header" style="background:#f0fff4">
    🧬 ①：（Germline Tolerance Filter）
  </div>
  <div class="card-body">

    <div class="formula-box">
tolerance(core9) = sigmoid(f_max)
    where: f_max = max usage frequency of 9-mer core in IMGT human V-gene germlines
           sigmoid(x) = 1 / (1 + exp(−100 × (x − 0.005)))
           → f_max > 1% → tolerance ≈ 1.0 ( / self-similar → )
           → f_max = 0  → tolerance = 0.0 ( → )

net_contribution = allele_weight × (1 − tolerance)
net_immunogenic_burden = Σ net_contribution   ← 
    </div>

    <div class="algo-block">
      <b>：</b>9-mer anchor core  IGHV/IGKV/IGLV  → "" → 
      （thymic deletion） → tolerance → 1.0 → 。<br>
      （ CDR 、）→ tolerance = 0 → 。
    </div>

    <div class="legend">
      <div class="legend-item"><div class="dot" style="background:#38a169"></div> （tolerance≥0.8）</div>
      <div class="legend-item"><div class="dot" style="background:#e2e8f0"></div> （0.2–0.8）</div>
      <div class="legend-item"><div class="dot" style="background:#e53e3e"></div> （tolerance&lt;0.2）</div>
    </div>

    <table id="tol_tbl" class="display compact" style="width:100%">
      <thead><tr>
        <th></th><th></th><th>ADA</th>
        <th></th><th>/（= =）</th>
        <th></th><th></th><th></th><th></th>
      </tr></thead>
      <tbody>{tol_rows_html}</tbody>
    </table>
  </div>
</div>

<!-- Module 2+3: Surface + Cluster -->
<div class="card">
  <div class="card-header" style="background:#ebf8ff">
    🌊 ②③： + 
  </div>
  <div class="card-body">

    <div class="formula-box">
【②：】
  PDB (27/70)：
    SASA = freesasa  (threshold > 20 Å²)
    frac_exposed_vh  = SASA > 20Å²  / VH 
    n_hydrophilic_patches = Parker > 0 
  Parker scale (43/70)：
     Parker (1986) 
    "" = Parker > 1.6 ， ≥ 4 aa

【③：（Hotspot）】
   non-tolerant （rank≤2%, tolerance&lt;0.5）
  cluster = ≥3  15-（|start_i − start_j| ≤ 15）
  n_clusters = 
    </div>

    <div class="warn">
      ⚠️ PDB  n_hydrophilic_patches  NaN（SASA）。
      PDB  frac_exposed_vh / mean_sasa_vh （Parker scale ）。
      ： Parker scale ； PDB  frac_exposed_vh 。
    </div>

    <table id="surf_tbl" class="display compact" style="width:100%">
      <thead><tr>
        <th></th><th></th><th>ADA</th>
        <th></th>
        <th></th>
        <th>VH</th>
        <th>VHSASA</th>
        <th>●</th>
        <th></th>
        <th></th>
        <th>ADA</th>
      </tr></thead>
      <tbody>{surf_rows_html}</tbody>
    </table>
  </div>
</div>

<!-- Correlation with ADA -->
<div class="card">
  <div class="card-header" style="background:#fff5f5">
    📊 ADASpearman
  </div>
  <div class="card-body">
    <p class="note">=ADA | =ADA | * p&lt;0.05</p>
    <table class="dt" style="width:600px">
      <thead><tr><th></th><th>Spearman r</th><th>p</th><th>N</th></tr></thead>
      <tbody>{corr_html}</tbody>
    </table>

    <div class="algo-block" style="margin-top:16px">
      <b>：</b><br>
      1. <b>net_immunogenic_burden</b>（r≈0.14）：
         MHC-II>0.85（），。<br>
      2. <b>n_clusters</b>（r≈0.14）：
          n_strong_binders （r=0.71）， n_strong_binders ADA。<br>
      3. <b>n_hydrophilic_patches</b>（r≈-0.06，）：
         43/70  Parker ，；PDB（NaN）。<br>
      4. <b></b>：（SC vs IV）、（）、
         （MTX）。 r≈0.45–0.55。
    </div>
  </div>
</div>

</div>
<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script>
$(document).ready(function(){{
  $('#tol_tbl').DataTable({{scrollX:true,pageLength:25,order:[[5,'desc']],dom:'lfrtip'}});
  $('#surf_tbl').DataTable({{scrollX:true,pageLength:25,order:[[8,'desc']],dom:'lfrtip'}});
}});
</script>
</body>
</html>"""

out_path = OUT / "immuno70_decomposition_report.html"
out_path.write_text(html, encoding="utf-8")
print(f"[Done] Saved: {out_path}")
print(f"  Module 1 rows: {len(tol_df)}")
print(f"  Module 2+3 rows: {len(hla_sorted)}")
