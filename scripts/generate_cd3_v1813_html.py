"""
Generate V1.8.13 HTML reports from JSON outputs.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515" / "v1813_reports"

ALGO_VERSION = "V1.8.13"


def pi_label(pI):
    if pI is None: return "<span class='u'>N/A</span>"
    v = float(pI)
    if v <= 9.0: return f"<span class='p'>{v:.2f} PASS</span>"
    if v <= 9.5: return f"<span class='w'>{v:.2f} WARN</span>"
    return f"<span class='f'>{v:.2f} FAIL</span>"


def an_label(d):
    if d is None: return "<span class='u'>N/A</span>"
    v = float(d)
    if v >= 0:     return f"<span class='p'>{v:+.4f} EXCELLENT</span>"
    if v >= -0.12: return f"<span class='p'>{v:+.4f} PASS</span>"
    if v >= -0.20: return f"<span class='w'>{v:+.4f} WARN</span>"
    return f"<span class='f'>{v:+.4f} FAIL</span>"


def tier_badge(t: str):
    colors = {
        "Cys-gate": "#c0392b",
        "Tier 1 pI-Correction": "#8e44ad",
        "Tier 1 pI-Correction (fallback scan)": "#9b59b6",
        "Tier 1 Stealth": "#2980b9",
        "Tier 2 Hallmark": "#16a085",
        "Tier 3 FAIC": "#f39c12",
    }
    color = colors.get(t, "#555")
    return f'<span style="background:{color};color:#fff;padding:2px 7px;border-radius:3px;font-size:11px">{t}</span>'


def seq_diff_html(orig: str, eng: str) -> str:
    """Side-by-side diff with mutations highlighted."""
    rows = []
    chunk = 20
    for start in range(0, max(len(orig), len(eng)), chunk):
        o_chunk = orig[start:start+chunk]
        e_chunk = eng[start:start+chunk]
        o_disp = ""
        e_disp = ""
        for i, (oa, ea) in enumerate(zip(o_chunk, e_chunk)):
            if oa != ea:
                o_disp += f'<span class="del">{oa}</span>'
                e_disp += f'<span class="ins">{ea}</span>'
            else:
                o_disp += oa
                e_disp += ea
        # ruler: 1-based from start
        ruler = ""
        for i in range(0, len(o_chunk), 5):
            n = start + i + 1
            ruler += f'<span style="margin-right:{(5 if i==0 else 0)}px">{n:5d}</span>'
        rows.append(f"""
<div class="seq-block">
  <div class="seq-ruler">{ruler}</div>
  <div class="seq-row"><span class="seq-label">Original</span><span class="seq-code">{o_disp}</span></div>
  <div class="seq-row"><span class="seq-label">Engineered</span><span class="seq-code">{e_disp}</span></div>
</div>""")
    return "".join(rows)


def build_html(d: dict) -> str:
    name = d["sample"]
    alg  = d.get("algorithm_version", ALGO_VERSION)
    init_m = d["initial_metrics"]
    final_m = d["final_metrics"]
    init_a = d["initial_abnativ"]
    final_a = d["final_abnativ"]
    pi_pred = d.get("v1813_pi_prediction", {})
    all_mut = d.get("all_mutations", [])
    tier_log = d.get("tier_log", [])
    orig_seq = d["input_seq"]
    eng_seq  = d.get("final_seq", orig_seq)
    verdict  = d.get("final_verdict", "N/A")
    stopped  = d.get("stopped_at", "—")

    verdict_color = "#27ae60" if "FAIL" not in verdict else ("#e67e22" if "WARN" not in verdict else "#f39c12")
    if "FAIL" in verdict: verdict_color = "#e74c3c"

    # Mutation table
    mut_rows = ""
    for i, m in enumerate(all_mut, 1):
        rationale = m.get("rationale", "")
        mut_rows += f"""<tr>
  <td>{i}</td>
  <td>{tier_badge(m.get('tier','?'))}</td>
  <td><b>{m.get('orig_aa','?')}→{m.get('target_aa','?')}</b></td>
  <td>{m.get('label_kabat','?')}</td>
  <td>seq pos {m.get('idx', 0)+1}</td>
  <td style="font-size:12px">{rationale}</td>
</tr>"""
    if not all_mut:
        mut_rows = "<tr><td colspan='6' style='text-align:center;color:#999'>No mutations applied</td></tr>"

    # Tier log
    tier_rows = ""
    for tl in tier_log:
        st = tl.get("stage", "?")
        if tl.get("skipped"):
            tier_rows += f"<tr><td><b>{st}</b></td><td colspan='4'><i style='color:#999'>{tl.get('reason','skipped')}</i></td></tr>"
            continue
        apps = ", ".join(tl.get("applied", []))
        pm   = tl.get("post_metrics", {})
        verd = tl.get("verdict", "")
        esc  = "→ ESCALATE" if tl.get("escalate") else ("→ STOP" if verd else "")
        pi_cell = pi_label(pm.get("pI"))
        an_cell = an_label(pm.get("abnativ_delta"))
        tier_rows += f"""<tr>
  <td><b>{st}</b></td>
  <td>{apps or '—'}</td>
  <td>{pi_cell}</td>
  <td>{an_cell}</td>
  <td>{esc}</td>
</tr>"""

    # pI prediction panel
    pi_path = pi_pred.get("pi_correction_path", "—")
    pi_note = pi_pred.get("note", "")
    n_corr  = pi_pred.get("n_corrections_planned", 0)
    pi_path_color = "#27ae60" if "PASS" in pi_path else ("#f39c12" if "WARN" in pi_path else "#e74c3c")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="robots" content="noindex,nofollow">
<title>InSynBio VH→VHH | {name} | {alg}</title>
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#f0f2f5;margin:0;padding:20px;color:#222}}
  .wrap{{max-width:1100px;margin:0 auto;background:#fff;border-radius:8px;box-shadow:0 2px 16px rgba(0,0,0,.1);overflow:hidden}}
  .header{{background:linear-gradient(135deg,#1a2a5e,#2d4a8a);color:#fff;padding:28px 36px}}
  .header h1{{margin:0 0 6px;font-size:22px}}
  .header .sub{{opacity:.75;font-size:13px}}
  .section{{padding:24px 36px;border-bottom:1px solid #eee}}
  .section h2{{color:#1a2a5e;font-size:16px;margin:0 0 14px;text-transform:uppercase;letter-spacing:.04em}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th{{background:#f7f9fc;color:#555;padding:8px 10px;text-align:left;font-weight:600;border-bottom:2px solid #e0e4ec}}
  td{{padding:7px 10px;border-bottom:1px solid #f0f0f0;vertical-align:top}}
  tr:hover td{{background:#fafbfd}}
  .p{{color:#27ae60;font-weight:600}} .w{{color:#e67e22;font-weight:600}}
  .f{{color:#e74c3c;font-weight:600}} .u{{color:#999}}
  .metric-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}
  .metric-card{{background:#f7f9fc;border-radius:6px;padding:14px 16px;border-left:4px solid #2d4a8a}}
  .metric-card .label{{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.05em}}
  .metric-card .value{{font-size:20px;font-weight:700;margin:4px 0}}
  .metric-card .change{{font-size:12px;color:#555}}
  .verdict-box{{padding:14px 20px;border-radius:6px;font-weight:700;font-size:15px;display:inline-block;background:{verdict_color}1a;border:2px solid {verdict_color};color:{verdict_color}}}
  .pi-pred-box{{background:#f7f9fc;border-radius:6px;padding:14px 18px;border-left:4px solid {pi_path_color};margin-bottom:14px}}
  .seq-block{{margin-bottom:8px}}
  .seq-row{{display:flex;align-items:center;gap:12px;font-size:13px}}
  .seq-label{{width:90px;font-size:11px;color:#888;text-align:right;flex-shrink:0}}
  .seq-code{{font-family:'Courier New',monospace;letter-spacing:1px;line-height:1.8}}
  .seq-ruler{{font-family:'Courier New',monospace;font-size:10px;color:#bbb;padding-left:102px;margin-bottom:2px}}
  .del{{background:#ffecec;color:#c0392b;font-weight:700;border-radius:2px}}
  .ins{{background:#e8f5e9;color:#27ae60;font-weight:700;border-radius:2px}}
  .badge-ighv1{{background:#e74c3c1a;color:#c0392b;padding:2px 8px;border-radius:3px;font-size:12px;font-weight:600}}
  .badge-ighv3{{background:#27ae601a;color:#1e8449;padding:2px 8px;border-radius:3px;font-size:12px;font-weight:600}}
  .badge-ighvx{{background:#f39c121a;color:#d68910;padding:2px 8px;border-radius:3px;font-size:12px;font-weight:600}}
  footer{{text-align:center;padding:16px;font-size:11px;color:#aaa;border-top:1px solid #eee}}
</style>
</head>
<body>
<div class="wrap">

<!-- HEADER -->
<div class="header">
  <div class="sub">InSynBio AbEngineCore · VH→VHH Conversion (Path C) · {alg} · Internal Engineering Document</div>
  <h1>{name} — VH→VHH Engineering Report</h1>
  <div class="sub">
    IGHV Family: <b>{d.get("ighv_family","?")}</b> &nbsp;|&nbsp;
    CDR3: <b>{d.get("cdr3_aa","?")} ({d.get("cdr3_len","?")} aa)</b> &nbsp;|&nbsp;
    Mutations applied: <b>{len(all_mut)}</b> &nbsp;|&nbsp;
    Stopped at: <b>{stopped[:60]}</b>
  </div>
</div>

<!-- VERDICT -->
<div class="section">
  <h2>Overall Verdict</h2>
  <div class="verdict-box">{verdict}</div>
  &nbsp;&nbsp;
  <span style="color:#888;font-size:13px">pI threshold: ≤ 9.0 PASS · ≤ 9.5 WARN · > 9.5 FAIL &nbsp;|&nbsp;
  AbNatiV Δ: ≥ 0.000 EXCELLENT · ≥ -0.120 PASS · ≥ -0.200 WARN · &lt; -0.200 FAIL</span>
</div>

<!-- METRICS COMPARISON -->
<div class="section">
  <h2>Metrics: Original VH → Engineered VHH</h2>
  <div class="metric-grid">
    <div class="metric-card">
      <div class="label">Isoelectric Point (pI)</div>
      <div class="value">{pi_label(final_m.get("pI"))}</div>
      <div class="change">Before: {init_m.get("pI","—")} &nbsp;Δ = {round(final_m.get("pI",0)-init_m.get("pI",0),2):+.2f}</div>
    </div>
    <div class="metric-card">
      <div class="label">AbNatiV Δ (VHH2 − VH2)</div>
      <div class="value">{an_label(final_a.get("delta"))}</div>
      <div class="change">Before: {init_a.get("delta","—")} &nbsp;Δ = {round((final_a.get("delta") or 0)-(init_a.get("delta") or 0),4):+.4f}</div>
    </div>
    <div class="metric-card">
      <div class="label">GRAVY (hydrophobicity)</div>
      <div class="value" style="font-size:16px">{final_m.get("GRAVY","—")}</div>
      <div class="change">Before: {init_m.get("GRAVY","—")}</div>
    </div>
    <div class="metric-card">
      <div class="label">Net basic residues (K+R−D−E)</div>
      <div class="value" style="font-size:16px">{final_m.get("net_basic","—")}</div>
      <div class="change">Before: {init_m.get("net_basic","—")} · K: {final_m.get("K_count","?")} · D: {final_m.get("D_count","?")}</div>
    </div>
  </div>
</div>

<!-- V1.8.13 pI PREDICTION PANEL -->
<div class="section">
  <h2>V1.8.13 — Pre-Engineering pI Prediction</h2>
  <div class="pi-pred-box">
    <b>Predicted pI after full Stealth + Hallmark:</b> {pi_pred.get("predicted_pi_post_engineering","—")}&nbsp;
    &nbsp;<b>Path:</b> <span style="color:{pi_path_color}">{pi_path}</span>
    &nbsp;&nbsp;|&nbsp;&nbsp;pI-correction mutations planned: <b>{n_corr}</b>
    <div style="margin-top:8px;font-size:12px;color:#555">{pi_note}</div>
  </div>
  <p style="font-size:12px;color:#888;margin:0">
    V1.8.13 co-designs pI-correction K→D mutations in Tier 1 (alongside Stealth) 
    <em>before</em> Hallmark mutations are applied. This prevents pI from worsening when 
    Hallmark K45R (+0.1–0.2 pI) is introduced. Trigger: predicted pI &gt; 9.0 (1× K→D) or &gt; 9.5 (2× K→D).
  </p>
</div>

<!-- TIER LOG -->
<div class="section">
  <h2>Algorithm Tier Log</h2>
  <table>
    <tr><th>Stage</th><th>Mutations</th><th>pI post</th><th>AbNatiV Δ post</th><th>Decision</th></tr>
    {tier_rows}
  </table>
</div>

<!-- MUTATION TABLE -->
<div class="section">
  <h2>Mutation Audit — {len(all_mut)} mutations applied</h2>
  <table>
    <tr><th>#</th><th>Tier</th><th>Substitution</th><th>Position (biological)</th><th>Sequence index</th><th>Rationale</th></tr>
    {mut_rows}
  </table>
</div>

<!-- SEQUENCE COMPARISON -->
<div class="section">
  <h2>Sequence Comparison — Original VH vs Engineered VHH</h2>
  <p style="font-size:12px;color:#888;margin:0 0 12px">
    <span class="del">Red</span> = original residue (replaced) &nbsp;|&nbsp;
    <span class="ins">Green</span> = engineered residue (new) &nbsp;|&nbsp;
    Sequence length: {len(orig_seq)} aa &nbsp;|&nbsp;
    Mutations: {sum(1 for a,b in zip(orig_seq,eng_seq) if a!=b)}
  </p>
  {seq_diff_html(orig_seq, eng_seq)}
  <div style="margin-top:14px">
    <b>Original:</b><br><code style="font-size:11px;word-break:break-all">{orig_seq}</code>
  </div>
  <div style="margin-top:8px">
    <b>Engineered:</b><br><code style="font-size:11px;word-break:break-all">{eng_seq}</code>
  </div>
</div>

<!-- FOOTER -->
<footer>InSynBio AbEngineCore · VH→VHH Conversion {alg} · Confidential — Internal Engineering Use Only</footer>
</div>
</body>
</html>"""
    return html


def main():
    samples = [
        "SP34", "Teplizumab", "OKT3", "Visilizumab", "Otelixizumab", "Foralumab"
    ]
    generated = []
    for name in samples:
        json_path = REPORT_DIR / f"{name}_v1813.json"
        if not json_path.exists():
            print(f"  [SKIP] {name} — JSON not found")
            continue
        d = json.loads(json_path.read_text(encoding="utf-8"))
        html = build_html(d)
        out_path = REPORT_DIR / f"{name}_v1813.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"  [OK] {out_path.name}")
        generated.append(out_path)

    print(f"\nGenerated {len(generated)} HTML reports in:\n  {REPORT_DIR}")


if __name__ == "__main__":
    main()
