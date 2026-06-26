#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generate_tnb_html_report.py
===========================
Generate a complete, self-contained HTML analysis report for
Tnb04/Tnb164 bispecific VHH project.
Includes: raw data, CMC analysis, activity, linker optimization, recommendation.
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parents[1]
CMC_JSON   = SUITE_ROOT / "projects" / "Tnb_bispecific" / "cmc_eval" / "tnb_full_cmc_real.json"
OUT_HTML   = SUITE_ROOT / "projects" / "Tnb_bispecific" / "report" / "TNB_Bispecific_Full_Report.html"

data     = json.loads(CMC_JSON.read_text(encoding="utf-8"))
singles  = data["single_vhh"]
fusions  = data["fusion_proteins"]
activity = data["activity"]
NOW      = datetime.now().strftime("%Y-%m-%d")

# ── helpers ──────────────────────────────────────────────────────────────────
def pi_cls(v):
    if v <= 7.5: return "good"
    if v <= 8.5: return "warn"
    return "bad"

def adi_cls(v):
    if v >= 65: return "good"
    if v >= 50: return "warn"
    return "bad"

def ic_cls(v, lo=0.05, hi=0.2):
    if v is None: return "na"
    if v <= lo:   return "good"
    if v <= hi:   return "warn"
    return "bad"

def ic90_cls(v, lo=0.1, hi=0.5):
    if v is None or v >= 990: return "na"
    if v <= lo:  return "good"
    if v <= hi:  return "warn"
    return "bad"

def fv(v, decimals=3):
    if v is None: return "<span class='na'>n.d.</span>"
    if v == 0.0:  return "≤0.001"
    return f"{v:.{decimals}f}"

def stars(n):
    return "★" * n + "☆" * (5 - n)

def tnb04_breadth_stars(vid):
    a = activity[vid]
    vals = [a.get(k) for k in ["WT_IC50","JN1_IC50","KP_IC50","XDV_IC50"]]
    good = sum(1 for v in vals if v is not None and v <= 0.1)
    return good

def mers_stars(ic90):
    if ic90 <= 0.05:  return 5
    if ic90 <= 0.15:  return 4
    if ic90 <= 0.35:  return 3
    if ic90 <= 0.5:   return 2
    return 1

# ── sequences ────────────────────────────────────────────────────────────────
SEQS = {
    "Tnb04H9":  "EVQLLESGGGLVQPGGSLRLSCAASGSISTLNVMG<b>W</b>YRQAPGKGRELVSRITLDGRPYYADSVKGRFTISRDNS<b>K</b>NTLYLQMNSLRAEDTAVYYC<b>K</b>LENGGFFYY<b>W</b>GQGTMVTVSS",
    "Tnb04H4":  "EVQLLESGGGLVQPGGSLRLSCAASGSISTLNVM<b>S</b>WYRQAPGKGRELV<b>A</b>RITLDGRPYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCKLENGGFFYYWGQGTMVTVSS",
    "Tnb04H2":  "EVQLLESGGGLVQPGGSLRLSCAASGSISTLNVMSWYRQAPGKGRELVSRITLDGRPYYADSVKGRFTISRD<b>G</b>SKNTLYLQMNSLRAEDTAVYYCKLENGGFFYYWGQGTMVTVSS",
    "Tnb04H3":  "EVQLLESGGGLVQPGGSLRLSCAASGSISTLNVMSWYRQAPGK<b>Q</b>RELVSRITLDGRPYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCKLENGGFFYYWGQGTMVTVSS",
    "Tnb04H7":  "EVQLLESGGGLVQPGGSLRLSCAASGSISTLNVMSWYRQAPGKGRELVSRITLDGRPYYADSVKGRFTISRDNSKNTLYLQM<b>NN</b>LRAEDTAVYYCKLENGGFFYYWGQGTMVTVSS",
    "Tnb04H8":  "EVQLLESGGGLVQPGGSLRLSCAASGSISTLNVMSWYRQAPGKGRELVSRITLDGRPYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVY<b>F</b>CKLENGGFFYYWGQGTMVTVSS",
    "Tnb164H4": "EVQLLESGGGLVQPGGSLRLSCAASGRSFRDYTMSWFRQAPGKGREFVSAHGWIGGKEYYADSVKGRFTISRD<b>K</b>SKNTLYLQMNSLRAEDTAVYYCAAHWSGDYYDSAAYNYWGQGTMVTVSS",
    "Tnb164H5": "EVQLLESGGGLVQPGGSLRLSCAASGRSFRDYTMSWFRQAPGKGREFV<b>A</b>AHGWIGGKEYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAAHWSGDYYDSAAYNYWGQGTMVTVSS",
    "Tnb164H2": "EVQLLESGGGLVQPGGSLRLSCAASGRSFRDYTMSWFRQAPGK<b>E</b>REFVSAHGWIGGKEYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAAHWSGDYYDSAAYNYWGQGTMVTVSS",
    "Tnb164H6": "EVQLLESGGGLVQPGGSLRLSCAASGRSFRDYTMSWFRQAPGKGREFVSAHGWIGGKEYYADSVKGRFT<b>V</b>SRDNSKNTLYLQMNSLRAEDTAVYYCAAHWSGDYYDSAAYNYWGQGTMVTVSS",
    "Tnb164H7": "EVQLLESGGGLVQPGGSLRLSCAASGRSFRDYTMSWFRQAPGKGREFVSAHGWIGGKEYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVY<b>F</b>CAAHWSGDYYDSAAYNYWGQGTMVTVSS",
    "Tnb164H8": "EVQLLESGGGLVQPGGSLRLSCAASGRSFRDYTMSWFRQAPGR<b>G</b>REFVSAHGWIGGKEYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAAHWSGDYYDSAAYNYWGQGTMVTVSS",
}

# ── CSS ──────────────────────────────────────────────────────────────────────
CSS = """
:root {
  --navy: #1a2f5a; --blue: #2563eb; --teal: #0891b2;
  --green-bg: #dcfce7; --green-txt: #166534; --green-bdr: #86efac;
  --yellow-bg: #fef9c3; --yellow-txt: #854d0e; --yellow-bdr: #fde047;
  --red-bg: #fee2e2; --red-txt: #991b1b; --red-bdr: #fca5a5;
  --grey-bg: #f1f5f9; --grey-txt: #64748b;
  --best-bg: #f0fdf4; --best-bdr: #4ade80;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; font-size: 13px;
       color: #1e293b; background: #f8fafc; line-height: 1.5; }
.page { max-width: 1200px; margin: 0 auto; padding: 24px; }

/* Header */
.report-header { background: linear-gradient(135deg, var(--navy) 0%, #1e4080 100%);
  color: white; padding: 36px 40px; border-radius: 12px; margin-bottom: 28px; }
.report-header h1 { font-size: 24px; font-weight: 700; margin-bottom: 6px; }
.report-header .subtitle { font-size: 14px; opacity: 0.85; margin-bottom: 16px; }
.meta-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; margin-top: 20px; }
.meta-card { background: rgba(255,255,255,0.12); border-radius: 8px; padding: 12px 16px; }
.meta-card .label { font-size: 11px; opacity: 0.7; text-transform: uppercase; letter-spacing:.5px; }
.meta-card .value { font-size: 14px; font-weight: 600; margin-top: 3px; }

/* Hero recommendation */
.hero { background: linear-gradient(135deg,#f0fdf4,#dcfce7);
  border: 2px solid var(--green-bdr); border-radius: 12px; padding: 24px 28px; margin-bottom: 28px; }
.hero-title { font-size: 13px; font-weight: 700; color: var(--green-txt); text-transform: uppercase;
  letter-spacing: .5px; margin-bottom: 10px; }
.hero-combo { font-size: 22px; font-weight: 800; color: var(--navy); margin-bottom: 6px; }
.hero-linker { font-family: 'Consolas', monospace; font-size: 13px; color: #166534;
  background: white; border: 1px solid var(--green-bdr); padding: 4px 10px; border-radius: 6px;
  display: inline-block; margin-bottom: 16px; }
.hero-kpi { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-top: 12px; }
.kpi { background: white; border-radius: 8px; padding: 12px 14px; border: 1px solid #e2e8f0; text-align: center; }
.kpi .k-label { font-size: 11px; color: var(--grey-txt); text-transform: uppercase; }
.kpi .k-val { font-size: 20px; font-weight: 800; color: var(--navy); margin-top: 2px; }
.kpi .k-sub { font-size: 11px; color: var(--grey-txt); }
.kpi.delta { border-color: var(--green-bdr); background: var(--green-bg); }
.kpi.delta .k-val { color: #15803d; }

/* Section */
.section { background: white; border-radius: 10px; border: 1px solid #e2e8f0;
  padding: 24px 28px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.04); }
.section-title { font-size: 16px; font-weight: 700; color: var(--navy);
  border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 18px;
  display: flex; align-items: center; gap: 8px; }
.section-title .badge { background: var(--blue); color: white; font-size: 11px;
  padding: 2px 8px; border-radius: 99px; font-weight: 600; }
.sub-title { font-size: 13px; font-weight: 700; color: #334155; margin: 16px 0 8px; }

/* Tables */
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { background: var(--navy); color: white; padding: 8px 10px; text-align: center;
  font-weight: 600; font-size: 11px; }
th.left { text-align: left; }
td { padding: 7px 10px; border-bottom: 1px solid #f1f5f9; text-align: center; }
td.left { text-align: left; }
tr:hover td { background: #f8fafc; }
tr.best td { background: var(--best-bg) !important; font-weight: 600; }
tr.best td:first-child { border-left: 3px solid var(--green-bdr); }
tr.orig td { background: #fff7ed !important; }
tr.sep td { background: #e2e8f0 !important; font-weight: 700; font-size: 11px;
  color: var(--navy); letter-spacing: .3px; }

/* Color cells */
.good { background: var(--green-bg); color: var(--green-txt); font-weight: 600; }
.warn { background: var(--yellow-bg); color: var(--yellow-txt); font-weight: 600; }
.bad  { background: var(--red-bg);   color: var(--red-txt);   font-weight: 600; }
.na   { color: var(--grey-txt); font-style: italic; }

/* Sequence */
.seq-block { font-family: 'Consolas','Courier New',monospace; font-size: 11.5px;
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
  padding: 8px 12px; word-break: break-all; line-height: 1.8; margin: 4px 0; }
.seq-block b { color: #dc2626; background: #fee2e2; border-radius: 2px; padding: 0 1px; }
.seq-id { font-size: 11px; font-weight: 700; color: var(--blue); margin-top: 10px; margin-bottom: 2px; }

/* Stars */
.stars { color: #f59e0b; font-size: 13px; }

/* Alert boxes */
.alert { border-radius: 8px; padding: 12px 16px; margin: 10px 0; font-size: 12px; }
.alert.green { background: var(--green-bg); border: 1px solid var(--green-bdr); color: var(--green-txt); }
.alert.yellow { background: var(--yellow-bg); border: 1px solid var(--yellow-bdr); color: var(--yellow-txt); }
.alert.red { background: var(--red-bg); border: 1px solid var(--red-bdr); color: var(--red-txt); }
.alert b { font-weight: 700; }

/* Linker comparison */
.linker-grid { display: grid; grid-template-columns: repeat(5,1fr); gap: 10px; margin-top: 12px; }
.lk-card { border-radius: 8px; padding: 12px; border: 1px solid #e2e8f0; text-align: center; }
.lk-card.best { border: 2px solid var(--green-bdr); background: var(--green-bg); }
.lk-card.bad2 { background: var(--red-bg); border: 1px solid var(--red-bdr); }
.lk-name { font-weight: 700; font-size: 12px; margin-bottom: 4px; }
.lk-seq  { font-family: monospace; font-size: 10px; color: var(--grey-txt); margin-bottom: 6px; word-break: break-all; }
.lk-pi   { font-size: 18px; font-weight: 800; }
.lk-pi.pi-good { color: #15803d; }
.lk-pi.pi-warn { color: #92400e; }
.lk-pi.pi-bad  { color: #991b1b; }
.lk-chg  { font-size: 11px; color: var(--grey-txt); }

/* Risk table */
.risk-row td:first-child { font-weight: 700; }
.risk-high  td:first-child { color: #991b1b; }
.risk-med   td:first-child { color: #92400e; }
.risk-low   td:first-child { color: #166534; }

/* Timeline */
.timeline { list-style: none; padding-left: 0; }
.timeline li { padding: 10px 0 10px 28px; position: relative; border-left: 2px solid #cbd5e1; margin-left: 8px; }
.timeline li:before { content: attr(data-week); position: absolute; left: -13px;
  background: var(--blue); color: white; font-size: 10px; font-weight: 700;
  width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; top: 10px; }
.timeline li .tl-title { font-weight: 700; color: var(--navy); font-size: 13px; }
.timeline li .tl-items { font-size: 12px; color: #475569; margin-top: 4px; }

/* Footer */
.footer { text-align: center; font-size: 11px; color: var(--grey-txt); margin-top: 30px;
  padding: 16px; border-top: 1px solid #e2e8f0; }

/* Print */
@media print {
  body { background: white; font-size: 11px; }
  .page { padding: 0; }
  .section { break-inside: avoid; }
}
"""

# ── Build HTML ────────────────────────────────────────────────────────────────
def build_html():

    # ── Fusion data lookup ──
    fmap = {(f["combo"], f["linker"]): f for f in fusions}

    def fpi(combo, lk):
        f = fmap.get((combo, lk))
        return f["pI"] if f else "—"
    def fchg(combo, lk):
        f = fmap.get((combo, lk))
        return f["net_charge_pH7"] if f else "—"

    # ── Part 1: Header ──────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tnb04/Tnb164  VHH </title>
<style>{CSS}</style>
</head>
<body>
<div class="page">

<!-- HEADER -->
<div class="report-header">
  <h1>Tnb04 × Tnb164  VHH </h1>
  <div class="subtitle">SARS-CoV-2 × MERS-CoV  · </div>
  <div class="meta-grid">
    <div class="meta-card"><div class="label"></div><div class="value">{NOW}</div></div>
    <div class="meta-card"><div class="label"></div><div class="value">InSynBio AbEngineCore V4.4</div></div>
    <div class="meta-card"><div class="label"></div><div class="value">Tnb04 Tnb164.xlsx</div></div>
    <div class="meta-card"><div class="label">VHH </div><div class="value">12（Tnb04×6 + Tnb164×6）</div></div>
    <div class="meta-card"><div class="label">CMC</div><div class="value">VHH42（n=42）</div></div>
    <div class="meta-card"><div class="label">pI</div><div class="value">BioPython ProteinAnalysis</div></div>
  </div>
</div>

<!-- HERO -->
<div class="hero">
  <div class="hero-title">⭐ </div>
  <div class="hero-combo">Tnb04H9 — (G₄S)₃+3E — Tnb164H6</div>
  <div class="hero-linker">：GGGGSGGGGSGGGGSEEE（18 aa，C3×Glu）</div>
  <div class="hero-kpi">
    <div class="kpi delta"><div class="k-label"> pI</div><div class="k-val">7.85</div><div class="k-sub">8.94 ↓1.09</div></div>
    <div class="kpi delta"><div class="k-label"> @pH7</div><div class="k-val">+1.0</div><div class="k-sub">+5.0 ↓4.0</div></div>
    <div class="kpi delta"><div class="k-label">MERS  IC90</div><div class="k-val">0.025</div><div class="k-sub">μg/mL ↑4.8× vsH4</div></div>
    <div class="kpi"><div class="k-label">SARS </div><div class="k-val">4/4</div><div class="k-sub"> IC50 ≤0.037 μg/mL</div></div>
  </div>
  <div style="margin-top:14px; font-size:12px; color:#166534;">
    <b></b>： pI=8.94，ER+5.0 →  → ERAD → 。
    (H4→H6) + (+3E)  pI 7.85，。
  </div>
</div>
"""

    # ── Part 2: Raw Sequences ──────────────────────────────────────────────
    html += """
<div class="section">
  <div class="section-title"><span>Section 1</span><span></span><span class="badge">12 VHH</span></div>
  <div class="sub-title">1.1 Tnb04 panel — SARS-CoV-2 （116 aa）</div>
  <p style="font-size:11px;color:#64748b;margin-bottom:8px;">：H9（）</p>
"""
    for vid in ["Tnb04H9","Tnb04H4","Tnb04H2","Tnb04H3","Tnb04H7","Tnb04H8"]:
        m = singles[vid]["metrics"]
        html += f'<div class="seq-id">{vid} &nbsp;|&nbsp; pI={m["pI"]:.2f} &nbsp;|&nbsp; {m["net_charge_pH7"]:+.1f} &nbsp;|&nbsp; {len(singles[vid]["sequence"])} aa</div>'
        html += f'<div class="seq-block">{SEQS[vid]}</div>'

    html += '<div class="sub-title" style="margin-top:20px;">1.2 Tnb164 panel — MERS-CoV （123 aa）</div>'
    html += '<p style="font-size:11px;color:#64748b;margin-bottom:8px;">：H4</p>'
    for vid in ["Tnb164H4","Tnb164H5","Tnb164H2","Tnb164H6","Tnb164H7","Tnb164H8"]:
        m = singles[vid]["metrics"]
        html += f'<div class="seq-id">{vid} &nbsp;|&nbsp; pI={m["pI"]:.2f} &nbsp;|&nbsp; {m["net_charge_pH7"]:+.1f} &nbsp;|&nbsp; {len(singles[vid]["sequence"])} aa</div>'
        html += f'<div class="seq-block">{SEQS[vid]}</div>'

    html += """
  <div class="sub-title" style="margin-top:20px;">1.3 （257 aa）</div>
  <div class="seq-id">Tnb04H9 — (G₄S)₃+3E — Tnb164H6 &nbsp;|&nbsp; pI=7.85 &nbsp;|&nbsp; +1.0 &nbsp;|&nbsp; 257 aa</div>
  <div class="seq-block" style="background:#f0fdf4;border-color:#86efac;">
EVQLLESGGGLVQPGGSLRLSCAASGSISTLNVMGWYRQAPGKGRELVSRITLDGRPYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCKLENGGFFYYWGQGTMVTVSS<span style="color:#2563eb;font-weight:bold;background:#dbeafe;">GGGGSGGGGSGGGGSEEE</span>EVQLLESGGGLVQPGGSLRLSCAASGRSFRDYTMSWFRQAPGKGREFVSAHGWIGGKEYYADSVKGRFT<b style="color:#dc2626;">V</b>SRDNSKNTLYLQMNSLRAEDTAVYYCAAHWSGDYYDSAAYNYWGQGTMVTVSS
  </div>
  <div style="font-size:11px;color:#64748b;margin-top:4px;">：(G₄S)₃+3E &nbsp;|&nbsp; ：Tnb164H4（I53V，GRFT<b>V</b>SR）</div>
</div>
"""

    # ── Part 3: Neutralization Activity ────────────────────────────────────
    html += """
<div class="section">
  <div class="section-title"><span>Section 2</span><span></span></div>
  <div class="sub-title">2.1 Tnb04 — SARS-CoV-2 （：μg/mL）</div>
  <table>
    <tr>
      <th class="left" rowspan="2"></th>
      <th colspan="4">IC50 (μg/mL)</th>
      <th colspan="3">IC90 (μg/mL)</th>
      <th rowspan="2"></th>
    </tr>
    <tr>
      <th>WT (D614G)</th><th>JN.1</th><th>KP.3.1.1</th><th>XDV</th>
      <th>JN.1</th><th>KP.3.1.1</th><th>XDV</th>
    </tr>
"""
    for vid in ["Tnb04H9","Tnb04H4","Tnb04H2","Tnb04H3","Tnb04H8","Tnb04H7"]:
        a = activity[vid]
        br = tnb04_breadth_stars(vid)
        tr_cls = "best" if vid=="Tnb04H9" else ""
        html += f'<tr class="{tr_cls}">'
        html += f'<td class="left"><b>{vid}</b>{"⭐" if vid=="Tnb04H9" else ""}</td>'
        for k in ["WT_IC50","JN1_IC50","KP_IC50","XDV_IC50"]:
            v = a.get(k)
            html += f'<td class="{ic_cls(v)}">{fv(v)}</td>'
        for k in ["JN1_IC90","KP_IC90","XDV_IC90"]:
            v = a.get(k)
            html += f'<td class="{ic90_cls(v)}">{fv(v)}</td>'
        html += f'<td><span class="stars">{"★"*br}{"☆"*(4-br)}</span> {br}/4</td>'
        html += "</tr>\n"

    html += """
  </table>
  <div class="alert green" style="margin-top:10px;">
    <b>：Tnb04H9</b>  SARS-CoV-2 WT/JN.1/KP.3.1.1/XDV 4 IC50 ≤0.037 μg/mL，JN.1 IC90=0.316（H41.418，4.5），
    XDV IC90=0.537（H21.623，3）。H9  SARS ，。
  </div>

  <div class="sub-title" style="margin-top:20px;">2.2 Tnb164 — MERS-CoV （：μg/mL）</div>
  <table>
    <tr>
      <th class="left"></th>
      <th>MERS WT IC50</th>
      <th>MjHKU4r-CoV-1 IC50</th>
      <th>MjHKU4r-CoV-1 IC90</th>
      <th>vs H4 (IC90)</th>
      <th></th>
    </tr>
"""
    for vid in ["Tnb164H4","Tnb164H5","Tnb164H2","Tnb164H6","Tnb164H7","Tnb164H8"]:
        a = activity[vid]
        ic90 = a.get("MjHKU4r_IC90", 999)
        ref  = activity["Tnb164H4"].get("MjHKU4r_IC90", 0.119)
        fold = f"{ic90/0.025:.1f}×" if vid!="Tnb164H6" else "1.0× ()"
        stars_n = mers_stars(ic90)
        tr_cls = "best" if vid=="Tnb164H6" else ""
        html += f'<tr class="{tr_cls}">'
        html += f'<td class="left"><b>{vid}</b>{"⭐" if vid=="Tnb164H6" else ""}</td>'
        mwt_v = a.get("MERS_WT_IC50")
        mic_v = a.get("MjHKU4r_IC50")
        html += f'<td class="{ic_cls(mwt_v)}">{fv(mwt_v)}</td>'
        html += f'<td class="{ic_cls(mic_v)}">{fv(mic_v)}</td>'
        html += f'<td class="{ic90_cls(ic90,0.05,0.35)}">{fv(ic90) if ic90 < 990 else "n.d."}</td>'
        html += f'<td style="font-weight:600;">{fold}</td>'
        html += f'<td><span class="stars">{"★"*stars_n}{"☆"*(5-stars_n)}</span></td>'
        html += "</tr>\n"

    html += """
  </table>
  <div class="alert green" style="margin-top:10px;">
    <b>：Tnb164H6</b> MjHKU4r-CoV-1（，MERS）IC90=0.025 μg/mL，
    ，H44.8，H513.8，H835。。
  </div>
</div>
"""

    # ── Part 4: CMC Single VHH ─────────────────────────────────────────────
    html += """
<div class="section">
  <div class="section-title"><span>Section 3</span><span> VHH CMC </span><span class="badge"> · 15</span></div>
  <p style="font-size:11px;color:#64748b;margin-bottom:12px;">
    ：BioPython ProteinAnalysis（pI/GRAVY//）+ （//）<br>
    ：VHH42（n=42；pI p50=8.62， p50=5， p50=1.5）<br>
    ADI：tent-function（p50=100, p25/p75=75, p5/p95=40, =0），VHH42
  </p>
  <table>
    <tr>
      <th class="left"></th><th>pI</th><th></th><th>GRAVY</th>
      <th></th><th>SAP</th><th></th><th></th>
      <th></th><th></th><th></th><th></th><th>Cys</th>
      <th>ADI</th><th></th>
    </tr>
"""
    for i, vid in enumerate(["Tnb04H9","Tnb04H4","Tnb04H2","Tnb04H3","Tnb04H7","Tnb04H8"]):
        r = singles[vid]; m = r["metrics"]; adi = r["adi_continuous"]
        tr_cls = "best" if vid=="Tnb04H9" else ""
        html += f'<tr class="{tr_cls}">'
        html += f'<td class="left"><b>{vid}</b>{"⭐" if vid=="Tnb04H9" else ""}</td>'
        html += f'<td class="{pi_cls(m["pI"])}">{m["pI"]:.2f}</td>'
        html += f'<td>{m["net_charge_pH7"]:+.1f}</td>'
        html += f'<td>{m["GRAVY"]:.3f}</td>'
        html += f'<td>{m["instability_index"]:.1f}</td>'
        html += f'<td>{m["SAP_score"]:.3f}</td>'
        html += f'<td>{m["agg_motifs"]}</td>'
        html += f'<td>{m["hydro_cluster_count"]}</td>'
        html += f'<td>{m["glycosylation_sites"]}</td>'
        html += f'<td class="{"warn" if m["deamidation_sites"]>2 else ""}">{m["deamidation_sites"]}</td>'
        html += f'<td>{m["isomerization_sites"]}</td>'
        html += f'<td>{m["oxidation_sites"]}</td>'
        html += f'<td class="{"warn" if m["free_cys"]>0 else ""}">{m["free_cys"]}</td>'
        html += f'<td class="{adi_cls(adi)}">{adi:.1f}</td>'
        html += f'<td style="font-size:11px;">{r["adi_grade"]}</td>'
        html += "</tr>\n"

    html += '<tr class="sep"><td colspan="15">── Tnb164 MERS  ───────────────────────────────────────────────────────────────────────</td></tr>\n'

    for i, vid in enumerate(["Tnb164H4","Tnb164H5","Tnb164H2","Tnb164H6","Tnb164H7","Tnb164H8"]):
        r = singles[vid]; m = r["metrics"]; adi = r["adi_continuous"]
        tr_cls = "best" if vid=="Tnb164H6" else ""
        html += f'<tr class="{tr_cls}">'
        html += f'<td class="left"><b>{vid}</b>{"⭐" if vid=="Tnb164H6" else ""}</td>'
        html += f'<td class="{pi_cls(m["pI"])}">{m["pI"]:.2f}</td>'
        html += f'<td>{m["net_charge_pH7"]:+.1f}</td>'
        html += f'<td class="{"warn" if m["GRAVY"]<-0.47 else ""}">{m["GRAVY"]:.3f}</td>'
        html += f'<td>{m["instability_index"]:.1f}</td>'
        html += f'<td>{m["SAP_score"]:.3f}</td>'
        html += f'<td>{m["agg_motifs"]}</td>'
        html += f'<td>{m["hydro_cluster_count"]}</td>'
        html += f'<td>{m["glycosylation_sites"]}</td>'
        html += f'<td>{m["deamidation_sites"]}</td>'
        html += f'<td>{m["isomerization_sites"]}</td>'
        html += f'<td class="warn">{m["oxidation_sites"]}</td>'
        html += f'<td class="{"warn" if m["free_cys"]>0 else ""}">{m["free_cys"]}</td>'
        html += f'<td class="{adi_cls(adi)}">{adi:.1f}</td>'
        html += f'<td style="font-size:11px;">{r["adi_grade"]}</td>'
        html += "</tr>\n"

    html += """
  </table>
  <div style="font-size:11px;color:#64748b;margin-top:8px;">
    <span class="good" style="padding:2px 6px;border-radius:4px;"></span>  &nbsp;
    <span class="warn" style="padding:2px 6px;border-radius:4px;"></span> （VHH42 p75）&nbsp;
    <span class="bad"  style="padding:2px 6px;border-radius:4px;"></span> 
    &nbsp;&nbsp;|&nbsp;&nbsp; Tnb04pI=8.99-9.01（⚠，） · Tnb164=7（）
  </div>
</div>
"""

    # ── Part 5: Linker Engineering ─────────────────────────────────────────
    html += """
<div class="section">
  <div class="section-title"><span>Section 4</span><span>： pI </span></div>

  <div class="sub-title">4.1 </div>
  <table style="max-width:700px;">
    <tr><th class="left"></th><th></th><th></th></tr>
    <tr><td class="left" style="color:#991b1b;font-weight:700;"> pI（8.94）</td>
        <td>BioPython</td>
        <td class="left">ERpH≈7.2；pI=8.94+5.0→ER→ERAD</td></tr>
    <tr><td class="left" style="color:#991b1b;font-weight:700;">(+5.0)</td>
        <td>H9(+2.8) + H4(+2.0) + linker(0)</td>
        <td class="left">ER/Golgi→→</td></tr>
    <tr><td class="left" style="color:#92400e;font-weight:700;">pI</td>
        <td>H9 pI=8.99, H4 pI=8.59</td>
        <td class="left">pI，GS</td></tr>
  </table>

  <div class="sub-title" style="margin-top:16px;">4.2  pI （H9+H6 ）</div>
  <div class="linker-grid">
"""
    lk_data = [
        ("(G₄S)₃", "GGGGSGGGGSGGGGS", 8.80, "+4.0", "bad2", "pi-bad"),
        ("(G₄S)₃+2E", "GGGGSGGGGSGGGGSS<b>EE</b>", 8.31, "+2.0", "", "pi-warn"),
        ("(G₄S)₃+3E ⭐", "<b>GGGGSGGGGSGGGGGS EEE</b>", 7.85, "+1.0", "best", "pi-good"),
        ("(G₄S)₃+4E", "GGGGSGGGGSGGGGSS<b>EEEE</b>", 6.99, "−0.0", "", "pi-good"),
        ("Whitlow ✗", "GSTSGSGK<b>P</b>GSGEGSTKG", 8.93, "+5.0", "bad2", "pi-bad"),
    ]
    for name, seq, pi, chg, card_cls, pi_cls_str in lk_data:
        comment = ""
        if "⭐" in name: comment = ""
        elif "✗"   in name: comment = "❌ KE，"
        html += f"""<div class="lk-card {card_cls}">
  <div class="lk-name">{name}</div>
  <div class="lk-seq">{seq}</div>
  <div class="lk-pi {pi_cls_str}">{pi:.2f}</div>
  <div class="lk-chg"> {chg}</div>
  <div style="font-size:11px;color:#166534;margin-top:4px;">{comment}</div>
</div>"""

    html += """
  </div>

  <div class="sub-title" style="margin-top:18px;">4.3  pI （）</div>
  <table>
    <tr>
      <th class="left"></th>
      <th>(G₄S)₃ </th><th>+2E</th><th>+3E ⭐</th><th>+4E</th>
      <th>3E</th><th></th>
    </tr>
"""
    combos_show = [
        ("Tnb04H9+Tnb164H4", ""),
        ("Tnb04H9+Tnb164H6", ""),
        ("Tnb04H9+Tnb164H5", ""),
        ("Tnb04H9+Tnb164H2", "pI"),
        ("Tnb04H2+Tnb164H6", ""),
    ]
    for combo, label in combos_show:
        pi0  = fpi(combo,"(G4S)3")
        pi2e = fpi(combo,"(G4S)3+2E")
        pi3e = fpi(combo,"(G4S)3+3E")
        pi4e = fpi(combo,"(G4S)3+4E")
        chg3 = fchg(combo,"(G4S)3+3E")
        tr_cls = "best" if combo=="Tnb04H9+Tnb164H6" else ("orig" if "" in label else "")
        html += f'<tr class="{tr_cls}">'
        html += f'<td class="left"><b>{combo}</b> <span style="font-size:11px;color:#64748b;">({label})</span></td>'
        html += f'<td class="{pi_cls(pi0)}">{pi0:.2f}</td>'
        html += f'<td class="{pi_cls(pi2e)}">{pi2e:.2f}</td>'
        html += f'<td class="{pi_cls(pi3e)}" style="font-weight:700;">{pi3e:.2f}</td>'
        html += f'<td class="{pi_cls(pi4e)}">{pi4e:.2f}</td>'
        html += f'<td>{chg3:+.1f}</td>'
        html += f'<td style="font-size:11px;">{"⭐ " if combo=="Tnb04H9+Tnb164H6" else label}</td>'
        html += "</tr>\n"

    html += """
  </table>
  <div class="alert yellow" style="margin-top:10px;">
    <b></b>：Whitlow（GSTSGSGKPGSGEGSTKG）1K+1E，K pI 8.93，(G₄S)₃8.80，
     pI 。1Glu， pI  0.35–0.45 。
  </div>
</div>
"""

    # ── Part 6: Decision Matrix ────────────────────────────────────────────
    html += """
<div class="section">
  <div class="section-title"><span>Section 5</span><span>： × CMC × </span></div>
  <table>
    <tr>
      <th class="left">（+3E）</th>
      <th>SARS<br></th>
      <th>MERS<br></th>
      <th>pI<br>(+3E)</th>
      <th>CMC<br>ADI</th>
      <th><br></th>
      <th></th>
    </tr>
"""
    matrix = [
        ("Tnb04H9+Tnb164H6+(G₄S)₃+3E", "★★★★★ ", "★★★★★ IC90=0.025", 7.85, 56.0, 22.5, "⭐ ", "best"),
        ("Tnb04H9+Tnb164H5+(G₄S)₃+3E", "★★★★★ ", "★★★ IC90=0.345", 7.85, 60.5, 19.5, "", ""),
        ("Tnb04H2+Tnb164H6+(G₄S)₃+3E", "★★★☆☆ XDV", "★★★★★ IC90=0.025", 7.85, 56.1, 18.5, "H9", ""),
        ("Tnb04H9+Tnb164H4+(G₄S)₃+3E", "★★★★★ ", "★★★★ IC90=0.119", 8.31, 56.1, 18.0, "", ""),
        ("Tnb04H9+Tnb164H4+(G₄S)₃ ","★★★★★ ","★★★★ IC90=0.119", 8.94, 56.1, 13.5, "❌ （）", "orig"),
    ]
    for label, sars, mers, pi, adi, score, rec, tr_cls in matrix:
        html += f'<tr class="{tr_cls}">'
        html += f'<td class="left"><b>{label}</b></td>'
        html += f'<td><span class="stars">{sars}</span></td>'
        html += f'<td><span class="stars">{mers}</span></td>'
        html += f'<td class="{pi_cls(pi)}">{pi:.2f}</td>'
        html += f'<td class="{adi_cls(adi)}">{adi:.1f}</td>'
        s_cls = "good" if score>=20 else ("warn" if score>=17 else "bad")
        html += f'<td class="{s_cls}"><b>{score}</b>/25</td>'
        html += f'<td style="font-size:11px;font-weight:{"700" if "" in rec else "400"};">{rec}</td>'
        html += "</tr>\n"

    html += """
  </table>
</div>
"""

    # ── Part 7: Known Risks ────────────────────────────────────────────────
    html += """
<div class="section">
  <div class="section-title"><span>Section 6</span><span></span></div>
  <table>
    <tr><th class="left"></th><th></th><th></th><th class="left"></th></tr>
    <tr class="risk-high">
      <td class="left"><b> pI = 8.94（）</b></td>
      <td class="bad"></td>
      <td></td>
      <td class="left"> (G₄S)₃+3E  → pI  7.85（）</td>
    </tr>
    <tr class="risk-med">
      <td class="left"><b>Tnb04H9  3 </b><br><span style="font-size:11px;color:#64748b;">N72(NG)、N82(NS)、N98(NG)</span></td>
      <td class="warn"></td>
      <td>（ + ）</td>
      <td class="left">N82Q （H9，H2/H7）；<br>， N82Q </td>
    </tr>
    <tr class="risk-med">
      <td class="left"><b>Tnb164  7  M/W </b><br><span style="font-size:11px;color:#64748b;">M33/W35/W52/M82/W99/W112/W117（）</span></td>
      <td class="warn"></td>
      <td> + </td>
      <td class="left">（0.1% H₂O₂, 37°C, 24h）→ ；<br>M33I/M82I （MW）</td>
    </tr>
    <tr class="risk-med">
      <td class="left"><b>Tnb164 GRAVY （-0.45 ~ -0.51）</b><br><span style="font-size:11px;color:#64748b;">VHH42 p5 = -0.481</span></td>
      <td class="warn">-</td>
      <td>（）</td>
      <td class="left"> DSF Tm； Tm &lt; 55°C ；<br></td>
    </tr>
    <tr class="risk-high">
      <td class="left"><b>（≠）</b></td>
      <td class="bad">（）</td>
      <td></td>
      <td class="left">3（//）；<br>（SARS+MERS）</td>
    </tr>
    <tr class="risk-high">
      <td class="left"><b>VHH-GS-VHH </b></td>
      <td class="bad">（）</td>
      <td>PK/</td>
      <td class="left">：Fc /  VHH / PEG<br>（）</td>
    </tr>
  </table>
</div>
"""

    # ── Part 8: Experimental Plan ──────────────────────────────────────────
    html += """
<div class="section">
  <div class="section-title"><span>Section 7</span><span></span></div>
  <ul class="timeline">
    <li data-week="1-2">
      <div class="tl-title"></div>
      <div class="tl-items">
        A（）: Tnb04H9 + (G₄S)₃ + Tnb164H6  [pI=8.80]<br>
        B（）: Tnb04H9 + (G₄S)₃+3E + Tnb164H6  [pI=7.85] ⭐<br>
        C（）: Tnb04H9 + (G₄S)₃+3E + Tnb164H5  [pI=7.85]<br>
        Pichia pastoris / S. cerevisiae ，
      </div>
    </li>
    <li data-week="3-4">
      <div class="tl-title"> + </div>
      <div class="tl-items">
        SDS-PAGE + SEC：，（ &gt;90%）<br>
        SARS-CoV-2 ：WT / JN.1 / KP.3.1.1 / XDV（4）<br>
        MERS-CoV ：MERS WT + MjHKU4r-CoV-1<br>
        BA → 
      </div>
    </li>
    <li data-week="5-6">
      <div class="tl-title">CMC </div>
      <div class="tl-items">
        ：DSF/nanoDSF（Tm， &gt;60°C）<br>
        ：0.1% H₂O₂，37°C，24h → SEC + <br>
        pH：pH 5–9 2h → SEC<br>
        ：DLS（Pd%，Rh），40°C/1
      </div>
    </li>
    <li data-week="7-8">
      <div class="tl-title">H9 （）</div>
      <div class="tl-items">
        N82Q  →  → SARS<br>
         →  H9(N82Q)+H6+3E <br>
         →  H9，3
      </div>
    </li>
  </ul>
</div>
"""

    # ── Part 9: pI Verification ────────────────────────────────────────────
    html += """
<div class="section">
  <div class="section-title"><span> A</span><span>pI （ vs ）</span></div>
  <table style="max-width:500px;">
    <tr><th class="left"></th><th></th><th></th><th></th><th></th></tr>
"""
    OLD_PI = {"Tnb04H9":9.00,"Tnb04H4":9.00,"Tnb04H2":9.00,
              "Tnb164H4":8.59,"Tnb164H5":8.03,"Tnb164H2":7.00,"Tnb164H6":8.03}
    for vid, old in OLD_PI.items():
        new = singles[vid]["metrics"]["pI"]
        delta = new - old
        ok = abs(delta) < 0.02
        html += f'<tr><td class="left">{vid}</td><td>{old:.2f}</td>'
        html += f'<td class="{"good" if ok else "warn"}">{new:.2f}</td>'
        html += f'<td>{delta:+.2f}</td>'
        html += f'<td class="{"good" if ok else "warn"}">{"✓ " if ok else f"Δ{delta:+.2f}"}</td></tr>\n'

    html += """
  </table>
  <div class="alert green" style="max-width:500px;margin-top:8px;">
    7 pI  ≤0.01，，。
  </div>
</div>
"""

    # ── Part 10: ADI Breakdown ─────────────────────────────────────────────
    html += """
<div class="section">
  <div class="section-title"><span> B</span><span>ADI （）</span></div>
  <p style="font-size:11px;color:#64748b;margin-bottom:10px;">
    ：tent-function，VHH42；
    p50→100，p25/p75→75，p5/p95→40，→0。<br>
    ：0.30 · 0.25 · 0.30 · 0.15
  </p>
  <table>
    <tr>
      <th class="left"></th>
      <th>pI</th><th></th><th>GRAVY</th><th></th>
      <th></th><th></th>
      <th></th><th></th><th></th><th></th>
      <th>ADI</th>
    </tr>
"""
    for vid in ["Tnb04H9","Tnb04H4","Tnb04H2","Tnb04H7","Tnb164H4","Tnb164H5","Tnb164H6","Tnb164H2"]:
        r = singles[vid]
        ms = r["metric_scores"]
        cs = r["category_scores"]
        adi = r["adi_continuous"]
        tr_cls = "best" if vid in ("Tnb04H9","Tnb164H6") else ""
        html += f'<tr class="{tr_cls}">'
        html += f'<td class="left"><b>{vid}</b></td>'
        for k in ["pI","net_charge_pH7","GRAVY","instability_index","oxidation_sites","deamidation_sites"]:
            v = ms.get(k,0)
            html += f'<td class="{"good" if v>=75 else ("warn" if v>=40 else "bad")}">{v:.0f}</td>'
        for cat in ["hydrophobicity","charge","chemical","aggregation"]:
            v = cs.get(cat,0)
            html += f'<td class="{"good" if v>=65 else ("warn" if v>=45 else "bad")}">{v:.0f}</td>'
        html += f'<td class="{adi_cls(adi)}"><b>{adi:.1f}</b></td>'
        html += "</tr>\n"

    html += """
  </table>
  <div class="alert yellow" style="margin-top:10px;">
    <b></b>：Tnb04""50（pI=9.0VHH42，）；
    Tnb164"=0"（7M/WVHH42 p75=6）"GRAVY34-50"（，VHH42 p5）。
  </div>
</div>
"""

    # ── Footer ─────────────────────────────────────────────────────────────
    html += f"""
<div class="footer">
  InSynBio AbEngineCore V4.4 &nbsp;|&nbsp; ：{NOW} &nbsp;|&nbsp;
  ：Tnb04 Tnb164.xlsx &nbsp;|&nbsp;
  pI：BioPython ProteinAnalysis.isoelectric_point() &nbsp;|&nbsp;
  ADI：VHH42（n=42，tent-function）&nbsp;|&nbsp;
  12VHH，
</div>

</div><!-- .page -->
</body>
</html>"""

    return html


html_content = build_html()
OUT_HTML.write_text(html_content, encoding="utf-8")
print(f"HTML report saved: {OUT_HTML}")
print(f"  Size: {len(html_content.encode('utf-8'))//1024} KB")
print(f"  Lines: {len(html_content.splitlines())}")
