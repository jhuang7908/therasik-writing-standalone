"""
build_immunogenicity_factors_report.py
=======================================
Generate comprehensive HTML report:
  - All factors affecting antibody immunogenicity
  - Empirical correlations from the 70-antibody dataset
  - Best achievable model and theoretical ceiling
  - Stratified analysis (oncology vs autoimmune)
  - Data quality assessment and roadmap to r=0.7
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import spearmanr
import json

ROOT = Path("d:/InSynBio-AI-Research/Antibody_Engineer_Suite")
OUT  = ROOT / "data/thera_sabdab/out"

m = pd.read_csv(OUT / "immuno70_extended_features.csv")
m = m.drop_duplicates("antibody_name").copy()

target = "ada_rate_pct"

# --- Collect all correlations -----------------------------------------------
ALL_FEAT = [c for c in m.columns if c.startswith("feat_")]
corr_rows = []
for fc in ALL_FEAT:
    sub = m[[target, fc]].dropna()
    if len(sub) < 8: continue
    r, p = spearmanr(sub[target], sub[fc])
    corr_rows.append({
        "feature_key": fc,
        "feature": fc.replace("feat_",""),
        "r": round(r, 3), "p": round(p, 4), "n": len(sub),
    })
corr_df = pd.DataFrame(corr_rows).sort_values("r", key=abs, ascending=False)

# --- Top and bottom antibodies -----------------------------------------------
top_ada = m.nlargest(8, target)[["antibody_name","ada_rate_pct","origin","route","target","disease_class","format_sab"]]
low_ada = m.nsmallest(8, target)[["antibody_name","ada_rate_pct","origin","route","target","disease_class","format_sab"]]

# --- Stratified summary -------------------------------------------------------
strat_rows = []
for grp_name, mask in [
    ("IV + Oncology", (m["route"]=="IV") & (m["oncology_indication_x"]==1)),
    ("IV + Autoimmune/Other", (m["route"]=="IV") & (m["oncology_indication_x"]!=1)),
    ("SC + Autoimmune/Other", (m["route"].isin(["SC","IM"])) & (m["oncology_indication_x"]!=1)),
    ("SC + Oncology", (m["route"].isin(["SC","IM"])) & (m["oncology_indication_x"]==1)),
]:
    sg = m[mask]
    if len(sg) == 0: continue
    strat_rows.append({
        "group": grp_name,
        "n": len(sg),
        "ada_mean": round(sg[target].mean(), 1),
        "ada_median": round(sg[target].median(), 1),
        "ada_min": round(sg[target].min(), 1),
        "ada_max": round(sg[target].max(), 1),
    })
strat_df = pd.DataFrame(strat_rows)

# ============================================================================
# HTML REPORT
# ============================================================================
def corr_bar(r, max_r=0.5, width=100):
    frac  = min(abs(r) / max_r, 1.0)
    px    = int(frac * width)
    color = "#e05a5a" if r > 0 else "#5a8ae0"
    sig_color = "#cc1111" if r > 0 else "#1144cc"
    return f'''<div style="display:flex;align-items:center;gap:6px">
      <span style="color:{sig_color};font-weight:600;min-width:52px">{r:+.3f}</span>
      <div style="background:#eee;width:{width}px;height:10px;border-radius:3px;overflow:hidden">
        <div style="background:{color};width:{px}px;height:100%;border-radius:3px"></div>
      </div>
    </div>'''

def p_badge(p):
    if p < 0.01:  return '<span style="background:#c00;color:#fff;border-radius:3px;padding:1px 5px;font-size:10px">p<0.01**</span>'
    if p < 0.05:  return '<span style="background:#e55;color:#fff;border-radius:3px;padding:1px 5px;font-size:10px">p<0.05*</span>'
    if p < 0.10:  return '<span style="background:#fa0;color:#fff;border-radius:3px;padding:1px 5px;font-size:10px">p<0.10^</span>'
    return '<span style="background:#aaa;color:#fff;border-radius:3px;padding:1px 5px;font-size:10px">ns</span>'

FACTOR_GROUPS = [
    {
        "title": "Sequence Origin & Framework Foreignness",
        "icon": "🧬",
        "color": "#3b5bdb",
        "theory": """
        <p>Humanized antibodies retain murine CDRs grafted onto human frameworks, and often 
        require "back-mutations" at Vernier zone positions. These non-human residues can form 
        novel T-cell epitopes when processed by APCs. Fully human antibodies (from transgenic mice 
        or phage display) have fully human VH/VL frameworks, reducing epitope load.</p>
        <ul>
          <li><b>Vernier zone residues</b> (FR2, ~18 positions): directly support CDR conformation; 
              foreign Vernier residues create novel MHC-II binders unavailable in tolerance induction.</li>
          <li><b>VH/VL germline identity %</b>: lower identity = more foreign residues = more potential epitopes.</li>
          <li><b>IGHV family</b>: IGHV3-family germlines are most tolerogenic (most frequent in humans).</li>
        </ul>""",
        "feats": ["origin_code","vz_foreignness","vh_identity","vl_identity","vh_family_score"],
    },
    {
        "title": "MHC-II Epitope Load (T-cell Epitopes)",
        "icon": "🎯",
        "color": "#2f9e44",
        "theory": """
        <p>T-cell help is required for high-affinity ADA production. Strong MHC-II binding 15-mers 
        (IC50 ≤ 1000 nM against ≥1 DRB1 allele) in the Fv region prime CD4⁺ T helper cells. 
        Germline tolerance deducts epitopes that overlap with human germline sequences.</p>
        <ul>
          <li><b>n_strong_binders</b>: count of peptides with ≥1 allele at ≤1% rank; 
              NOT a good stand-alone predictor because it is saturated (most drugs score >40).</li>
          <li><b>net_immunogenic_burden</b>: Σ allele_weight × (1 - germline_tolerance); 
              accounts for population frequency and tolerance induction.</li>
          <li><b>n_clusters</b>: spatial clustering of strong binders → "hot spots" drive memory B cells.</li>
          <li><em>Important caveat:</em> assay saturation (90% of drugs score >0.85) limits 
              discriminatory power of this feature alone.</li>
        </ul>""",
        "feats": ["n_strong_binders","net_burden","n_clusters"],
    },
    {
        "title": "Clinical & Immunological Context",
        "icon": "🏥",
        "color": "#e07b00",
        "theory": """
        <p>Clinical factors can drastically modulate the observed ADA rate independent of 
        molecular immunogenicity. These are the dominant confounders in our 70-drug dataset.</p>
        <ul>
          <li><b>Route of administration</b>: SC route activates skin-resident DCs (Langerhans cells, 
              dermal DCs), which are more potent APCs than systemic DCs. IV route bypasses skin 
              priming and also creates higher drug concentrations that interfere with ADA assays 
              (drug tolerance window).</li>
          <li><b>Indication (oncology vs autoimmune)</b>: Cancer patients are often immunosuppressed 
              by disease or chemotherapy → baseline ADA ~1-3% regardless of molecular features.</li>
          <li><b>Concomitant immunosuppressants</b>: MTX co-medication reduces adalimumab ADA from 
              ~40% to <5%. Tacrolimus in transplant settings similarly suppresses ADA.</li>
          <li><b>Immune-depleting targets</b> (CD52, CD20, CD38, CD19): Lymphocyte depletion 
              followed by immune reconstitution causes paradoxically HIGH ADA (reconstitution 
              immune hyperactivation). Alemtuzumab=85%, Rituximab=64%.</li>
          <li><b>ADA assay methodology</b>: ECL-based assays (modern) detect ADA 10-100× more 
              sensitively than ELISA (pre-2010). This is a major unmeasured confounder.</li>
        </ul>""",
        "feats": ["clinical_context","immune_depleting","checkpoint"],
    },
    {
        "title": "Antibody Format & Fc Engineering",
        "icon": "🔧",
        "color": "#7048e8",
        "theory": """
        <p>The structural format of the antibody determines whether Fc-mediated tolerogenic 
        mechanisms are available:</p>
        <ul>
          <li><b>Full IgG</b>: Fc enables FcγRIIb-mediated B-cell anergy, FcRn-mediated 
              long half-life (lower tissue concentration), and Fc-mediated complement depletion 
              of anti-drug immune complexes.</li>
          <li><b>Fragment antibodies (Fab, scFv, VHH)</b>: No Fc → no tolerogenic signaling. 
              Very short half-life → concentrated at injection site → more immunogenic.
              Brolucizumab (scFv, intravitreal): ADA=52%.</li>
          <li><b>IgG4</b>: Minimal Fc effector function → less DC activation → theoretically 
              lower ADA. But data show isotype has weak overall correlation (r=+0.032).</li>
          <li><b>Aglycosylated Fc</b> (Atezolizumab TQAS, Eftrenonacog): Loss of Fc glycan 
              exposes novel Fc epitopes AND eliminates FcγRIIb tolerogenic signaling → 
              can increase ADA despite IV route.</li>
          <li><b>ADC linker/payload</b>: Linker and cytotoxic payload are novel antigens → 
              modest ADA increase vs naked IgG.</li>
        </ul>""",
        "feats": ["format","isotype_immuno","fc_present"],
    },
    {
        "title": "CDR Biophysical Properties",
        "icon": "⚗️",
        "color": "#c2255c",
        "theory": """
        <p>CDR sequences can directly influence T-cell epitope quality and antigen 
        processing efficiency:</p>
        <ul>
          <li><b>CDR-H3 length</b>: Longer CDR-H3 loops provide more peptide 
              material for proteasomal processing and MHC-II loading.</li>
          <li><b>CDR aromatic content (Y/W/F)</b>: Aromatic residues create strong 
              MHC-II anchor pins. However, in our dataset r=-0.130 (unexpected negative), 
              possibly because fully human antibodies have evolved to avoid high-aromatic 
              CDRs that would create self-reactive T cells.</li>
          <li><b>CDR deamidation sites (NG motif)</b>: NG deamidation in CDRs creates 
              acidic neo-epitopes that were never present during thymic selection → 
              potentially highly immunogenic. r=+0.124 (n=70).</li>
          <li><b>CDR net charge</b>: Charged CDRs can interact electrostatically with 
              MHC-II peptide-binding groove. Effect is peptide-context dependent.</li>
        </ul>""",
        "feats": ["cdrh3_len","cdrh3_aromaticity","cdr_deamidation","cdrh3_charge","total_cdr_length"],
    },
    {
        "title": "Surface Hydrophilicity (Structural)",
        "icon": "💧",
        "color": "#0ca678",
        "theory": """
        <p>The surface exposure of the Fv region determines which parts of the antibody 
        are accessible to APCs:</p>
        <ul>
          <li><b>VL exposed fraction (SASA-based)</b>: Counter-intuitively negative (r=-0.409*) — 
              antibodies with MORE VL surface exposure have LOWER ADA. This may reflect that 
              antibodies with open Fv conformations have been engineered for stability, 
              or that the ADA assay interference from IV high-dose drugs correlates with 
              exposed Fv area. Needs n>70 to validate.</li>
          <li><b>Parker scale hydrophilicity</b>: Sequence-based estimate, r=-0.171 (n=70). 
              More hydrophilic antibodies may have lower tissue retention → less APC exposure.</li>
          <li><em>Important: SASA analysis only available for 27/70 antibodies (structural PDB). 
              Larger PDB dataset needed for validation.</em></li>
        </ul>""",
        "feats": ["surf_frac_vl","surf_n_patches"],
    },
    {
        "title": "CMC Biophysical Properties",
        "icon": "🔬",
        "color": "#868e96",
        "theory": """
        <p>CMC (Chemistry, Manufacturing, Controls) properties affect immunogenicity 
        primarily through aggregation:</p>
        <ul>
          <li><b>Aggregation</b>: Protein aggregates are potent T-cell-independent ADA inducers 
              (crosslink B-cell receptors directly). Sequence-based aggregation motif counts 
              show r=-0.115 (unexpected negative), likely because our sequence-based metric 
              does not capture formulation-specific aggregation behavior.</li>
          <li><b>pI</b>: High pI (~>8.5) antibodies have more cationic surface → interact 
              more with cell membranes → potentially more immunogenic. r=+0.064 (weak).</li>
          <li><b>GRAVY score</b>: Overall hydrophobicity; highly hydrophobic antibodies 
              aggregate more in solution. r=-0.026 (near zero).</li>
          <li><b>Net charge at pH 7.4</b>: Strongly positively charged antibodies have 
              more non-specific interactions and potentially more APC uptake. r=+0.088.</li>
          <li><em>CMC metrics are sequence-based. Real aggregation risk requires DSF, DLS, 
              SEC data from actual formulations.</em></li>
        </ul>""",
        "feats": ["cmc_agg","cmc_pI","cmc_net_charge","cmc_instability","cmc_gravy"],
    },
]

def feat_row(fkey, corr_df):
    rr = corr_df[corr_df["feature"]==fkey]
    if rr.empty: 
        rr = corr_df[corr_df["feature_key"].str.contains(fkey, na=False)]
    if rr.empty: return f'<tr><td>{fkey}</td><td colspan="3">—</td></tr>'
    row = rr.iloc[0]
    return f"""<tr>
        <td style="font-family:monospace;font-size:12px">{row["feature"]}</td>
        <td>{corr_bar(row["r"])}</td>
        <td>{p_badge(row["p"])}</td>
        <td style="color:#666;font-size:11px">n={int(row["n"])}</td>
    </tr>"""

# Build sections
sections_html = ""
for grp in FACTOR_GROUPS:
    feat_rows_html = "\n".join(feat_row(f, corr_df) for f in grp["feats"])
    sections_html += f"""
    <div class="card" style="border-top:4px solid {grp['color']}">
      <div class="card-header">
        <span style="font-size:1.5rem;margin-right:8px">{grp['icon']}</span>
        <span style="font-size:1.1rem;font-weight:700;color:{grp['color']}">{grp['title']}</span>
      </div>
      <div class="card-body">
        <div class="theory-box">{grp['theory']}</div>
        <h5 style="margin-top:16px;color:{grp['color']}">Empirical Correlations (Spearman r vs clinical ADA%)</h5>
        <table class="corr-table">
          <thead><tr><th>Feature</th><th>Spearman r</th><th>Sig.</th><th>N</th></tr></thead>
          <tbody>{feat_rows_html}</tbody>
        </table>
      </div>
    </div>"""

# Stratified table
strat_html = "".join(f"""<tr>
    <td>{r['group']}</td><td>{r['n']}</td>
    <td>{r['ada_mean']}</td><td>{r['ada_median']}</td>
    <td>{r['ada_min']}–{r['ada_max']}</td>
  </tr>""" for _, r in strat_df.iterrows())

# High/Low ADA tables
def ab_table(df):
    html = ""
    for _, row in df.iterrows():
        html += f"""<tr>
          <td><b>{row['antibody_name']}</b></td>
          <td style="color:{'#c00' if row['ada_rate_pct']>20 else '#080'};font-weight:600">
            {row['ada_rate_pct']:.1f}%</td>
          <td>{row['origin']}</td>
          <td>{row['route']}</td>
          <td style="max-width:150px;overflow:hidden;text-overflow:ellipsis">{row['target']}</td>
          <td>{row['disease_class']}</td>
        </tr>"""
    return html

# Full report HTML
html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title> – InSynBio Analysis</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, 'Segoe UI', Arial, sans-serif;
          background: #f4f6fb; color: #333; line-height: 1.6; }}
  .header {{ background: linear-gradient(135deg, #1a237e 0%, #283593 60%, #3949ab 100%);
             color: white; padding: 2rem 2.5rem; }}
  .header h1 {{ font-size: 1.9rem; font-weight: 700; }}
  .header p {{ opacity: 0.85; margin-top: 0.4rem; font-size: 0.95rem; }}
  .badge {{ display:inline-block; background:rgba(255,255,255,0.2);
            border-radius:12px; padding:2px 12px; font-size:0.8rem; margin-top:8px; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 1.5rem; }}
  .card {{ background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,.06);
           margin-bottom: 1.5rem; overflow: hidden; }}
  .card-header {{ background: #f8f9fd; padding: 1rem 1.5rem;
                  border-bottom: 1px solid #eee; display:flex; align-items:center; }}
  .card-body {{ padding: 1.25rem 1.5rem; }}
  .theory-box {{ background: #f0f4ff; border-left: 3px solid #4a6cf7;
                 padding: 12px 16px; border-radius: 0 6px 6px 0; font-size: 0.88rem; }}
  .theory-box ul {{ margin-left: 1.2rem; margin-top: 4px; }}
  .theory-box li {{ margin: 4px 0; }}
  .corr-table {{ width:100%; border-collapse:collapse; margin-top:8px; font-size:0.88rem; }}
  .corr-table th {{ background:#f0f0f0; padding:6px 10px; text-align:left;
                    font-size:0.78rem; text-transform:uppercase; color:#555; }}
  .corr-table td {{ padding:5px 10px; border-bottom:1px solid #f0f0f0; }}
  .corr-table tr:hover {{ background:#fafbff; }}
  .summary-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; margin-bottom:1.5rem; }}
  .stat-card {{ background:white; border-radius:8px; padding:1rem 1.2rem;
                box-shadow:0 2px 6px rgba(0,0,0,.06); text-align:center; }}
  .stat-card .val {{ font-size:2rem; font-weight:700; }}
  .stat-card .lbl {{ font-size:0.8rem; color:#666; margin-top:2px; }}
  .limit-box {{ background:#fff8e1; border:1px solid #ffc107; border-radius:6px;
                padding:1rem 1.25rem; margin-bottom:1rem; }}
  .roadmap {{ background:#e8f5e9; border:1px solid #66bb6a; border-radius:6px;
              padding:1rem 1.25rem; }}
  h2 {{ font-size:1.15rem; font-weight:700; color:#1a237e; margin-bottom:0.75rem; }}
  table.data-table {{ width:100%; border-collapse:collapse; font-size:0.85rem; }}
  table.data-table th {{ background:#1a237e; color:white; padding:7px 10px; text-align:left; }}
  table.data-table td {{ padding:6px 10px; border-bottom:1px solid #eee; }}
  table.data-table tr:hover {{ background:#f4f6fb; }}
  @media(max-width:700px) {{ .summary-grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="header">
  <h1> — </h1>
  <p>70ADA33Spearman | InSynBio AbEngineer Suite</p>
  <span class="badge">n=70 therapeutics</span>
  <span class="badge">33 engineered features</span>
  <span class="badge">ADA range: 0–90%</span>
</div>

<div class="container">

<!-- KEY FINDING SUMMARY -->
<div class="summary-grid" style="margin-top:1.5rem">
  <div class="stat-card">
    <div class="val" style="color:#1a237e">0.41*</div>
    <div class="lbl"><br>VL (n=27, )</div>
  </div>
  <div class="stat-card">
    <div class="val" style="color:#2f9e44">0.29*</div>
    <div class="lbl"><br> (origin_code, n=70)</div>
  </div>
  <div class="stat-card">
    <div class="val" style="color:#e07b00">~0.13</div>
    <div class="lbl">LOO<br>Spearman r (n=70)</div>
  </div>
</div>

<!-- LIMIT BOX -->
<div class="limit-box">
  <h2>⚠️ 0.30–0.40？</h2>
  <p>70、、ADA，
  ADA<b></b>：</p>
  <ul style="margin-left:1.2rem;margin-top:6px;font-size:0.88rem">
    <li><b></b>：ECL（）vs ELISA（≤2010），10–100；
        AdalimumabELISA~25%，ECL>50%。</li>
    <li><b></b>：（）ADA~1–3%；30–85%，
        。</li>
    <li><b></b>：IV（15 mg/kg），
        ADA→ADA（Bevacizumab：0.6%，>5%）。</li>
    <li><b></b>：MTXAdalimumab ADA~40%<5%；
        。</li>
    <li><b></b>：CD52（Alemtuzumab 85%）/CD20（Rituximab 64%）
        ADA，。</li>
    <li><b></b>：Donanemab（90% ADA，IV）AD；
        Atezolizumab（30% ADA，IV）Fc（TQAS）FcγRIIb。</li>
  </ul>
  <p style="margin-top:8px;font-size:0.88rem"><b>：</b>~0.3–0.4 → 
  r ≈ √0.3–0.4 ≈ 0.55–0.63。<b>0.7ADA（，）。</b></p>
</div>

<!-- PER-FACTOR SECTIONS -->
{sections_html}

<!-- STRATIFIED ANALYSIS -->
<div class="card">
  <div class="card-header">
    <span style="font-size:1.5rem;margin-right:8px">📊</span>
    <span style="font-size:1.1rem;font-weight:700;color:#555"></span>
  </div>
  <div class="card-body">
    <p style="margin-bottom:12px;font-size:0.88rem">
    ADA。：ADA，
    （ × ）ADA。
    </p>
    <table class="data-table">
      <thead><tr><th></th><th>N</th><th>(%)</th><th>(%)</th><th>(%)</th></tr></thead>
      <tbody>{strat_html}</tbody>
    </table>
    <p style="margin-top:12px;font-size:0.88rem;color:#666">
    <b>：</b>IV+6.3% vs SC+~11–15%，。
    IV+，ADA（origin_code r=+0.40），
    。
    </p>
  </div>
</div>

<!-- HIGH ADA & LOW ADA ANTIBODIES -->
<div class="card">
  <div class="card-header">
    <span style="font-size:1.5rem;margin-right:8px">📋</span>
    <span style="font-size:1.1rem;font-weight:700;color:#555">：ADA vs ADA</span>
  </div>
  <div class="card-body">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
    <div>
      <h5 style="color:#c00;margin-bottom:8px">ADA (Top 8)</h5>
      <table class="data-table" style="font-size:0.8rem">
        <thead><tr><th></th><th>ADA%</th><th></th><th></th><th></th><th></th></tr></thead>
        <tbody>{ab_table(top_ada)}</tbody>
      </table>
    </div>
    <div>
      <h5 style="color:#080;margin-bottom:8px">ADA (Bottom 8)</h5>
      <table class="data-table" style="font-size:0.8rem">
        <thead><tr><th></th><th>ADA%</th><th></th><th></th><th></th><th></th></tr></thead>
        <tbody>{ab_table(low_ada)}</tbody>
      </table>
    </div>
  </div>
  </div>
</div>

<!-- ROADMAP TO r=0.7 -->
<div class="roadmap">
  <h2>🗺️  r=0.7 </h2>
  <p style="font-size:0.88rem;margin-bottom:10px"> r≈0.13（LOO，n=70）。
  ：</p>
  <table style="width:100%;font-size:0.85rem;border-collapse:collapse">
    <thead style="background:rgba(0,100,0,0.1)">
      <tr><th style="padding:6px 10px;text-align:left"></th>
          <th style="padding:6px 10px;text-align:left">/</th>
          <th style="padding:6px 10px;text-align:left"></th>
          <th style="padding:6px 10px;text-align:left"></th></tr>
    </thead>
    <tbody>
      <tr style="border-bottom:1px solid #c8e6c9">
        <td style="padding:6px 10px"><b>P1★★★</b></td>
        <td style="padding:6px 10px"><b>ADA（ECL vs ELISA）</b><br>
          <span style="color:#666;font-size:0.8rem">ADA；ECL</span></td>
        <td style="padding:6px 10px;color:#2f9e44">Δr ≈ +0.15–0.20</td>
        <td style="padding:6px 10px">EMA/FDA</td>
      </tr>
      <tr style="border-bottom:1px solid #c8e6c9">
        <td style="padding:6px 10px"><b>P1★★★</b></td>
        <td style="padding:6px 10px"><b>（mg/kgflat dose）</b><br>
          <span style="color:#666;font-size:0.8rem">IV→</span></td>
        <td style="padding:6px 10px;color:#2f9e44">Δr ≈ +0.10–0.15</td>
        <td style="padding:6px 10px">FDA / DrugBank</td>
      </tr>
      <tr style="border-bottom:1px solid #c8e6c9">
        <td style="padding:6px 10px"><b>P2★★</b></td>
        <td style="padding:6px 10px"><b>MTX（）</b><br>
          <span style="color:#666;font-size:0.8rem">≥50% MTXADA3–5</span></td>
        <td style="padding:6px 10px;color:#2f9e44">Δr ≈ +0.08–0.12</td>
        <td style="padding:6px 10px"> / </td>
      </tr>
      <tr style="border-bottom:1px solid #c8e6c9">
        <td style="padding:6px 10px"><b>P2★★</b></td>
        <td style="padding:6px 10px"><b>Fc aglycosylation / effector function status</b><br>
          <span style="color:#666;font-size:0.8rem">TQAS/LALA/YTE → FcγRIIb</span></td>
        <td style="padding:6px 10px;color:#2f9e44">Δr ≈ +0.05–0.08</td>
        <td style="padding:6px 10px"> + WHO INN</td>
      </tr>
      <tr style="border-bottom:1px solid #c8e6c9">
        <td style="padding:6px 10px"><b>P2★★</b></td>
        <td style="padding:6px 10px"><b>n≥150（ADA）</b><br>
          <span style="color:#666;font-size:0.8rem"></span></td>
        <td style="padding:6px 10px;color:#2f9e44">Δr ≈ +0.05–0.10</td>
        <td style="padding:6px 10px">tiered_db</td>
      </tr>
      <tr style="border-bottom:1px solid #c8e6c9">
        <td style="padding:6px 10px"><b>P3★</b></td>
        <td style="padding:6px 10px"><b>HLA-DRB1*04:01（/）</b><br>
          <span style="color:#666;font-size:0.8rem">DRB1*04:01ADA</span></td>
        <td style="padding:6px 10px;color:#2f9e44">Δr ≈ +0.03–0.06</td>
        <td style="padding:6px 10px">HLA</td>
      </tr>
      <tr>
        <td style="padding:6px 10px"><b>P3★</b></td>
        <td style="padding:6px 10px"><b>CDRN-（NxS/T motif in CDR）</b><br>
          <span style="color:#666;font-size:0.8rem">CDR→→（Cetuximab α-Gal）</span></td>
        <td style="padding:6px 10px;color:#2f9e44">Δr ≈ +0.02–0.05</td>
        <td style="padding:6px 10px">，</td>
      </tr>
    </tbody>
  </table>
  <p style="margin-top:12px;font-size:0.85rem">
  <b></b>：P1 + P2 +  → r <b>0.55–0.65</b>。
  r=0.7，<b></b>ADA，。
  </p>
</div>

<div style="text-align:center;padding:1rem 0;color:#aaa;font-size:0.8rem">
  InSynBio AbEngineer Suite | Immunogenicity Analysis v2.0 | 70 Therapeutics
</div>

</div>
</body>
</html>"""

out_path = OUT / "immuno70_factors_report.html"
out_path.write_text(html, encoding="utf-8")
print(f"Report saved → {out_path}")
print(f"File size: {out_path.stat().st_size/1024:.1f} KB")
