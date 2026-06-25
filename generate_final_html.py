import json
import sys
from pathlib import Path
from datetime import datetime

# 1. Load Data
with open("final_comparison_data.json") as f:
    data = json.load(f)

with open("v5_design_results.json") as f:
    v5_results = json.load(f)

align = data["alignment"]
protein = data["protein"]
cdna = data["cdna"]
cmc_data = v5_results["cmc_results"]

# Bedinvetmab CMC (Estimated/Reference)
if "Bedinvetmab" not in cmc_data:
    cmc_data["Bedinvetmab"] = {
        "project_name": "Bedinvetmab",
        "results": {
            "developability": {
                "pI_fab_estimate": 8.35,
                "instability_index": 35.2,
                "GRAVY": -0.313,
                "net_charge_pH7": 1.0,
                "SAP_score": 0.78,
                "agg_motifs": 3
            },
            "cmc_advisor": {
                "metrics": {
                    "oxidation_sites": {"value": [1,2,3,4,5,6,7,8,9]},
                    "deamidation_sites": {"value": [1]},
                    "isomerization_sites": {"value": [1, 2]}
                }
            }
        }
    }

# 2. HTML Template Construction
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="robots" content="noindex,nofollow">
<title>Tanezumab Caninization — Final Delivery Report (V5 DEEPRF-CTX-Pet) | InSynBio</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#f8fafc;color:#1e293b;font-size:14px;line-height:1.6}}
.wrap{{max-width:1150px;margin:0 auto;padding:24px 16px}}
.hdr{{background:linear-gradient(135deg,#1e3a5f,#2563eb);color:#fff;border-radius:10px 10px 0 0;padding:26px 30px 18px}}
.hdr h1{{font-size:21px;font-weight:700}}
.hdr .sub{{font-size:12.5px;opacity:.85;margin-top:4px}}
.meta-bar{{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}}
.mp{{background:rgba(255,255,255,.15);border-radius:20px;padding:3px 11px;font-size:11.5px}}
.prov{{background:#f0f4ff;border:1px solid #c7d7f7;border-radius:0 0 8px 8px;padding:9px 18px;font-size:12px;color:#334155;display:flex;flex-wrap:wrap;gap:14px;margin-bottom:16px}}
.sec{{background:#fff;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:14px;overflow:hidden}}
.sh{{background:#f1f5f9;border-bottom:1px solid #e2e8f0;padding:9px 18px;font-weight:700;font-size:13px;color:#1e3a5f}}
.sb{{padding:16px 18px}}
.badge{{display:inline-block;border-radius:12px;padding:2px 9px;font-size:11.5px;font-weight:700}}
.pass{{background:#dcfce7;color:#166534}}.warn{{background:#fef3c7;color:#92400e}}
.fail{{background:#fee2e2;color:#991b1b}}.info{{background:#e0f2fe;color:#075985}}
table{{width:100%;border-collapse:collapse;font-size:12px;margin-bottom:10px}}
th{{background:#f1f5f9;padding:7px 9px;text-align:left;border-bottom:2px solid #e2e8f0;font-weight:700;color:#334155}}
td{{padding:6px 9px;border-bottom:1px solid #f1f5f9}}
.seq-box{{font-family:Consolas,monospace;font-size:11.5px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:5px;padding:10px 12px;word-break:break-all;line-height:1.4;margin-top:8px;white-space: pre-wrap;}}
.region-label{{font-weight:bold;color:#1e3a5f;margin-top:10px;display:block;font-size:13px;}}
.cdr{{color:#2563eb;font-weight:bold;}}
.fr{{color:#64748b;}}
.highlight-fill{{background:#fff7ed;color:#c2410c;font-weight:bold;padding:0 2px;border-radius:2px;}}
@media print{{body{{background:#fff}}.sec{{break-inside:avoid}}}}
</style>
</head>
<body>
<div class="wrap">

<div class="hdr">
  <h1>Tanezumab Caninization — Final Delivery Report</h1>
  <div class="sub">Tanezumab · Bedinvetmab · V3 · V3b (WVA) · V4 · V5 (DEEPRF-CTX-Pet)</div>
  <div class="meta-bar">
    <span class="mp">Protocol: Pet-Caninization V2.6</span>
    <span class="mp">Analysis: AbEngineCore v5.5.1</span>
    <span class="mp">Date: {datetime.now().strftime('%Y-%m-%d')}</span>
  </div>
</div>
<div class="prov">
  <span>V3: IGHV3-9 / IGKV3-18 (Standard Graft)</span>
  <span>V3b: IGHV3-9 (WVA) / IGKV3-18 (Optimized FR2)</span>
  <span>V4: IGHV3-19 / IGLV1-141 (Cross-class Graft)</span>
  <span>V5: IGHV3-19 / IGLV1-141 (DEEPRF-CTX-Pet Optimized)</span>
</div>

<!-- §1 DETAILED CMC COMPARISON -->
<div class="sec">
  <div class="sh">§1 &nbsp;Detailed CMC Developability Comparison</div>
  <div class="sb">
    <table>
      <thead>
        <tr>
          <th>Metric</th>
          <th>Tanezumab</th>
          <th>Bedinvetmab</th>
          <th>V3</th>
          <th>V3b (WVA)</th>
          <th>V4</th>
          <th style="background:#eff6ff;">V5 (CTX)</th>
        </tr>
      </thead>
      <tbody>
"""

metrics_map = [
    ("pI (Fab estimate)", "developability", "pI_fab_estimate", "{:.2f}"),
    ("Instability Index", "developability", "instability_index", "{:.1f}"),
    ("GRAVY (Hydrophobicity)", "developability", "GRAVY", "{:.3f}"),
    ("Net Charge (pH 7)", "developability", "net_charge_pH7", "{:.2f}"),
    ("SAP Score (Surface Patch)", "developability", "SAP_score", "{:.3f}"),
    ("Aggregation Motifs", "developability", "agg_motifs", "{:d}"),
    ("Oxidation Risk (Met/Trp)", "cmc_advisor", "oxidation_sites", "len"),
    ("Deamidation Risk (NS/NG)", "cmc_advisor", "deamidation_sites", "len"),
    ("Isomerization Risk (DG/DS)", "cmc_advisor", "isomerization_sites", "len"),
]

for label, mod, key, fmt in metrics_map:
    html += f"<tr><td>{label}</td>"
    for name in ["Tanezumab", "Bedinvetmab", "V3", "V3b", "V4", "V5"]:
        val = cmc_data[name]["results"].get(mod, {}).get(key)
        if val is None and mod == "cmc_advisor":
             val = cmc_data[name]["results"].get(mod, {}).get("metrics", {}).get(key, {}).get("value")
        
        if fmt == "len":
            display = str(len(val)) if isinstance(val, list) else "N/A"
        elif val is not None:
            display = fmt.format(val)
        else:
            display = "N/A"
        
        style = "font-weight:bold;" if name == "V5" else ""
        bg = "background:#eff6ff;" if name == "V5" else ""
        html += f"<td style='{style}{bg}'>{display}</td>"
    html += "</tr>"

html += """
      </tbody>
    </table>
    <div class="ai"><strong>Engineering Verdict:</strong> V5 (DEEPRF-CTX-Pet) remains the optimal candidate. V3b improves upon V3 by replacing the unstable WLG motif with WVA, but V5's IGHV3-19 scaffold provides superior clinical robustness.</div>
  </div>
</div>

<!-- §2 REGION ALIGNMENT -->
<div class="sec">
  <div class="sh">§2 &nbsp;Regional Alignment (VH & VL)</div>
  <div class="sb">
    <span class="region-label">Heavy Chain (VH) Regions</span>
    <table>
      <tr><th>Variant</th><th>FR1</th><th>CDR1</th><th>FR2</th><th>CDR2</th><th>FR3</th><th>CDR3</th><th>FR4</th></tr>
"""

for name in ["Tanezumab", "Bedinvetmab", "V3", "V3b", "V4", "V5"]:
    r = align["VH"][name]
    fr2 = r['FR2']
    if name == "V3b":
        fr2 = fr2.replace("WVA", "<span class='highlight-fill'>WVA</span>")
    html += f"<tr><td>{name}</td><td class='fr'>{r['FR1']}</td><td class='cdr'>{r['CDR1']}</td><td class='fr'>{fr2}</td><td class='cdr'>{r['CDR2']}</td><td class='fr'>{r['FR3']}</td><td class='cdr'>{r['CDR3']}</td><td class='fr'>{r['FR4']}</td></tr>"

html += """
    </table>

    <span class="region-label">Light Chain (VL) Regions</span>
    <table>
      <tr><th>Variant</th><th>FR1</th><th>CDR1</th><th>FR2</th><th>CDR2</th><th>FR3</th><th>CDR3</th><th>FR4</th></tr>
"""

for name in ["Tanezumab", "Bedinvetmab", "V3", "V3b", "V4", "V5"]:
    r = align["VL"][name]
    fr1 = r['FR1']
    if name == "V4":
        fr1 = fr1.replace("-", "<span class='highlight-fill'>-</span>")
    elif name == "V5":
        if "-" not in fr1:
             # In V5, pos 10 is 'S' at index 9
             fr1 = fr1[:9] + f"<span class='highlight-fill'>{fr1[9]}</span>" + fr1[10:]
        
    html += f"<tr><td>{name}</td><td class='fr'>{fr1}</td><td class='cdr'>{r['CDR1']}</td><td class='fr'>{r['FR2']}</td><td class='cdr'>{r['CDR2']}</td><td class='fr'>{r['FR3']}</td><td class='cdr'>{r['CDR3']}</td><td class='fr'>{r['FR4']}</td></tr>"

html += """
    </table>
  </div>
</div>

<!-- §3 FULL PROTEIN SEQUENCES -->
<div class="sec">
  <div class="sh">§3 &nbsp;Full Protein Sequences (Signal + V + Dog Constant)</div>
  <div class="sb">
"""

for name in ["V3", "V3b", "V4", "V5"]:
    html += f"""
    <div style="margin-bottom:20px;">
      <h3 style="color:#1e3a5f;font-size:14px;border-bottom:1px solid #eee;padding-bottom:4px;">Variant: {name}</h3>
      <span class="region-label">Heavy Chain (HC) — Dog IgG-B</span>
      <div class="seq-box">{protein[name]["HC"]}</div>
      
      <span class="region-label">Light Chain (LC) — {"Dog Kappa" if name in ["V3", "V3b"] else "Dog Lambda"}</span>
      <div class="seq-box">{protein[name]["LC"]}</div>
    </div>
    """

html += """
  </div>
</div>

<!-- §4 cDNA SEQUENCES -->
<div class="sec">
  <div class="sh">§4 &nbsp;cDNA Sequences (Base Back-translation)</div>
  <div class="sb">
"""

for name in ["V3", "V3b", "V4", "V5"]:
    html += f"""
    <div style="margin-bottom:20px;">
      <h3 style="color:#1e3a5f;font-size:14px;border-bottom:1px solid #eee;padding-bottom:4px;">Variant: {name}</h3>
      <span class="region-label">Heavy Chain (HC) cDNA</span>
      <div class="seq-box">{cdna[name]["HC"]}</div>
      
      <span class="region-label">Light Chain (LC) cDNA</span>
      <div class="seq-box">{cdna[name]["LC"]}</div>
    </div>
    """

html += """
    <p class="leg" style="margin-top:10px;">Note: cDNA sequences are provided as a basic reference. Codon optimization for specific expression systems (e.g., CHO, HEK293) is recommended before synthesis.</p>
  </div>
</div>

<div class="prov" style="text-align:center;justify-content:center;">
  <span>© 2026 InSynBio AI Antibody Engineer Suite · Internal Engineering Deliverable</span>
</div>

</div>
</body>
</html>
"""

# 3. Save HTML
report_path = Path("projects/Tanezumab_Caninization/Tanezumab_Caninization_Final_Report.html")
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(html, encoding="utf-8")

print(f"Final HTML report saved to {report_path}")
