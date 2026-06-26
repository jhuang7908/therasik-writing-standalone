"""
Generate detailed V1.8.12 HTML reports for the 6 CD3 samples.
Each report contains:
  - Sample metadata (IGHV family, CDR3, source)
  - Initial vs final metrics (pI, GRAVY, AbNatiV Δ, AbNatiV VH2/VHH2)
  - Tier-by-tier escalation log with rationale
  - Per-mutation table with full rationale
  - 1:1 sequence comparison (segmented by FR/CDR region)
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515" / "v1812_reports"
HTML_DIR   = REPORT_DIR / "html"
HTML_DIR.mkdir(parents=True, exist_ok=True)


def badge(label: str) -> str:
    """Color-coded verdict badge."""
    color = {
        "PASS":      "#10b981",
        "EXCELLENT": "#059669",
        "WARN":      "#f59e0b",
        "FAIL":      "#ef4444",
        "UNKNOWN":   "#94a3b8",
        "SKIPPED":   "#64748b",
    }.get(label.upper(), "#94a3b8")
    return f'<span style="display:inline-block;padding:2px 10px;border-radius:10px;background:{color};color:#fff;font-weight:600;font-size:11px">{label}</span>'


def n(v, d=2):
    if v is None:
        return "—"
    try:
        return f"{float(v):.{d}f}"
    except Exception:
        return str(v)


def split_by_region(seq: str, cdr3_start: int, cdr3_end: int) -> dict:
    """Split a VH sequence into approximate FR/CDR regions."""
    return {
        "FR1+CDR1+FR2+CDR2+FR3": seq[:cdr3_start - 3] if cdr3_start else seq,
        "CAR_motif":              seq[cdr3_start - 3:cdr3_start] if cdr3_start else "",
        "CDR3":                   seq[cdr3_start:cdr3_end] if cdr3_start and cdr3_end else "",
        "FR4":                    seq[cdr3_end:] if cdr3_end else "",
    }


def render_diff_html(orig: str, new: str) -> str:
    """Render a 1:1 colored diff between original and engineered sequences."""
    out_o, out_n = [], []
    for i, (o, e) in enumerate(zip(orig, new)):
        if o == e:
            out_o.append(o)
            out_n.append(e)
        else:
            out_o.append(f'<span style="background:#fee2e2;color:#dc2626;font-weight:700">{o}</span>')
            out_n.append(f'<span style="background:#dcfce7;color:#16a34a;font-weight:700">{e}</span>')
    return "".join(out_o), "".join(out_n)


def render_segmented_comparison(orig: str, new: str, cdr3_start: int, cdr3_end: int) -> str:
    """Render a segmented (region-by-region) comparison."""
    if not cdr3_start or not cdr3_end:
        return "<div>CDR3 boundary not detected; full-sequence diff only.</div>"
    
    segments = [
        ("FR1+CDR1+FR2+CDR2+FR3", 0, cdr3_start - 3),
        ("C-AR motif (FR3 end)",  cdr3_start - 3, cdr3_start),
        ("CDR3",                  cdr3_start, cdr3_end),
        ("FR4",                   cdr3_end, len(orig)),
    ]
    rows = []
    for label, s, e in segments:
        o_seg, n_seg = orig[s:e], new[s:e]
        o_html, n_html = render_diff_html(o_seg, n_seg)
        identical = (o_seg == n_seg)
        diff_n = sum(1 for a, b in zip(o_seg, n_seg) if a != b)
        identity = f"{(len(o_seg) - diff_n) / len(o_seg) * 100:.1f}%" if o_seg else "n/a"
        status = "✓ identical" if identical else f"{diff_n} mutations · {identity} identity"
        bg = "#f0fdf4" if identical else "#fef3c7"
        rows.append(f"""
        <div style="border-left:4px solid #6366f1;padding:10px 16px;margin:12px 0;background:{bg};border-radius:0 6px 6px 0">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <h4 style="margin:0;color:#3730a3">{label} <span style="font-size:11px;color:#64748b;font-weight:400">(positions {s+1}–{e})</span></h4>
            <span style="font-size:12px;color:#475569">{status}</span>
          </div>
          <div style="font-family:Consolas,monospace;font-size:12px;line-height:1.6">
            <div><span style="color:#94a3b8">Original  : </span>{o_html}</div>
            <div><span style="color:#94a3b8">Engineered: </span>{n_html}</div>
          </div>
        </div>""")
    return "\n".join(rows)


def render_tier_log(tier_log: list) -> str:
    rows = []
    for tl in tier_log:
        stage = tl.get("stage", "?")
        if tl.get("skipped"):
            rows.append(f"""
            <div style="border-left:3px solid #94a3b8;padding:8px 14px;margin:8px 0;background:#f8fafc">
              <h4 style="margin:0 0 4px;color:#64748b">{stage} — SKIPPED</h4>
              <div style="font-size:12px;color:#475569">{tl.get('reason', '')}</div>
            </div>""")
            continue
        applied = tl.get("applied", [])
        pm = tl.get("post_metrics", {})
        verdict = tl.get("verdict", "—")
        verdict_color = "#10b981" if "FAIL" not in verdict and "WARN" not in verdict else ("#f59e0b" if "WARN" in verdict else "#ef4444")
        depth_note = f"<div style='font-size:11px;color:#7c3aed;margin-bottom:6px'>{tl['depth']}</div>" if tl.get("depth") else ""
        scan_note = ""
        if tl.get("scan_positions"):
            scan_note = f"<div style='font-size:11px;color:#475569'>Scanned: {', '.join(tl['scan_positions'])}</div>"
        applied_html = ""
        if applied:
            applied_html = "<div style='font-size:12px;margin:6px 0'><b>Applied:</b> " + "; ".join(f"<code style='background:#e0e7ff;color:#3730a3;padding:1px 6px;border-radius:3px'>{a}</code>" for a in applied) + "</div>"
        else:
            applied_html = "<div style='font-size:12px;color:#94a3b8;margin:6px 0'><i>No eligible mutations</i></div>"
        metric_line = ""
        if pm:
            metric_line = f"<div style='font-size:12px;color:#1e40af'>Post-tier: pI={n(pm.get('pI'),2)}, GRAVY={n(pm.get('GRAVY'),3)}, AbNatiV Δ={n(pm.get('abnativ_delta'),4)}</div>"
        rows.append(f"""
        <div style="border-left:3px solid {verdict_color};padding:10px 14px;margin:10px 0;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,0.05);border-radius:0 6px 6px 0">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <h4 style="margin:0;color:#1e293b">{stage}</h4>
            <span style="font-weight:600;color:{verdict_color}">{verdict}</span>
          </div>
          {depth_note}
          {scan_note}
          {applied_html}
          {metric_line}
        </div>""")
    return "\n".join(rows)


def render_mutation_table(muts: list) -> str:
    if not muts:
        return "<div style='color:#94a3b8;font-style:italic'>No mutations applied.</div>"
    rows = []
    for i, m in enumerate(muts, 1):
        tier = m.get("tier", "?")
        tier_color = {
            "Cys-gate":         "#dc2626",
            "Tier 1 Stealth":   "#2563eb",
            "Tier 2 Hallmark":  "#7c3aed",
            "Tier 3 FAIC":      "#ea580c",
        }.get(tier, "#475569")
        rows.append(f"""
        <tr>
          <td style="text-align:center;font-weight:600">{i}</td>
          <td><span style="color:{tier_color};font-weight:600;font-size:11px">{tier}</span></td>
          <td style="font-family:Consolas,monospace;font-weight:700">{m['orig_aa']}{m['idx']+1}{m['target_aa']}</td>
          <td style="font-family:Consolas,monospace">{m['label_kabat']}</td>
          <td style="font-size:12px;line-height:1.5">{m['rationale']}</td>
        </tr>""")
    return f"""
    <table style="width:100%;border-collapse:collapse;font-size:13px;background:#fff;border:1px solid #e2e8f0">
      <thead>
        <tr style="background:#f1f5f9">
          <th style="padding:8px;text-align:center;border-bottom:2px solid #cbd5e1;width:30px">#</th>
          <th style="padding:8px;text-align:left;border-bottom:2px solid #cbd5e1;width:130px">Tier</th>
          <th style="padding:8px;text-align:left;border-bottom:2px solid #cbd5e1;width:90px">Mutation</th>
          <th style="padding:8px;text-align:left;border-bottom:2px solid #cbd5e1;width:90px">Kabat label</th>
          <th style="padding:8px;text-align:left;border-bottom:2px solid #cbd5e1">Rationale & Evidence</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>"""


def generate_report(payload: dict, out_path: Path):
    name = payload["sample"]
    family = payload["ighv_family"]
    cdr3_len = payload["cdr3_len"]
    cdr3_aa = payload["cdr3_aa"]
    orig_seq = payload["input_seq"]
    final_seq = payload["final_seq"]
    cdr3_start = payload.get("cdr3_start_idx")
    cdr3_end = payload.get("cdr3_end_idx")
    
    im = payload["initial_metrics"]
    fm = payload["final_metrics"]
    ia = payload["initial_abnativ"]
    fa = payload["final_abnativ"]
    
    # Verdict labels
    pi_init = "PASS" if im["pI"] <= 9.0 else ("WARN" if im["pI"] <= 9.5 else "FAIL")
    pi_fin  = "PASS" if fm["pI"] <= 9.0 else ("WARN" if fm["pI"] <= 9.5 else "FAIL")
    def an_label(d):
        if d is None: return "UNKNOWN"
        if d >= 0:    return "EXCELLENT"
        if d >= -0.12: return "PASS"
        if d >= -0.20: return "WARN"
        return "FAIL"
    an_init = an_label(ia.get("delta"))
    an_fin  = an_label(fa.get("delta"))
    
    # Calculate identity
    n_muts = len(payload["all_mutations"])
    n_identical = sum(1 for a, b in zip(orig_seq, final_seq) if a == b)
    seq_identity = n_identical / len(orig_seq) * 100
    
    overall = payload["final_verdict"]
    overall_color = "#10b981" if ("PASS" in overall and "FAIL" not in overall) else ("#f59e0b" if "WARN" in overall else "#ef4444")
    
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    diff_html = render_segmented_comparison(orig_seq, final_seq, cdr3_start, cdr3_end)
    tier_html = render_tier_log(payload["tier_log"])
    mut_html  = render_mutation_table(payload["all_mutations"])
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="robots" content="noindex,nofollow">
<title>{name} — VH→VHH V1.8.12 Report</title>
<style>
  body{{font-family:-apple-system,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:20px;line-height:1.55}}
  .wrap{{max-width:1280px;margin:0 auto;background:#fff;border-radius:8px;padding:30px;box-shadow:0 2px 8px rgba(0,0,0,0.06)}}
  h1{{margin:0 0 8px;font-size:24px;color:#1e293b}}
  h2{{font-size:17px;color:#3730a3;border-bottom:2px solid #e0e7ff;padding-bottom:6px;margin-top:30px}}
  h3{{font-size:14px;color:#475569}}
  .meta{{display:flex;gap:30px;font-size:12px;color:#64748b;margin-bottom:8px}}
  .summary-box{{background:linear-gradient(to right,#eef2ff,#f8fafc);border-radius:8px;padding:18px 22px;border:1px solid #e2e8f0;margin:18px 0}}
  table.metrics{{width:100%;border-collapse:collapse;background:#fff;font-size:13px}}
  table.metrics th,table.metrics td{{padding:8px 12px;border-bottom:1px solid #e2e8f0;text-align:left}}
  table.metrics th{{background:#f8fafc;font-weight:600;color:#475569}}
  table.metrics td.change-up{{color:#dc2626;font-weight:600}}
  table.metrics td.change-down{{color:#16a34a;font-weight:600}}
  .pill{{display:inline-block;padding:2px 10px;border-radius:10px;font-size:11px;font-weight:600;color:#fff}}
</style>
</head>
<body>
<div class="wrap">
  <h1>{name} — VH→VHH Conversion (V1.8.12)</h1>
  <div class="meta">
    <span>Sample: <b>{name}</b></span>
    <span>IGHV family: <b>{family}</b></span>
    <span>Generated: {ts}</span>
    <span>Algorithm: V1.8.12 (3-Tier, CDR3-aware, IGHV-aware)</span>
  </div>
  
  <div class="summary-box">
    <h2 style="margin-top:0;border:none">Executive Summary {badge(overall.split(',')[0].strip().split('=')[1] if '=' in overall else overall)}</h2>
    <table style="width:100%;font-size:13px">
      <tr><td><b>Family evidence:</b></td><td>{payload['ighv_evidence']}</td></tr>
      <tr><td><b>CDR3:</b></td><td><code>{cdr3_aa}</code> ({cdr3_len} aa)</td></tr>
      <tr><td><b>Mutations applied:</b></td><td>{n_muts} (sequence identity to input: <b>{seq_identity:.1f}%</b>)</td></tr>
      <tr><td><b>Stop point:</b></td><td>{payload['stopped_at']}</td></tr>
      <tr><td><b>Final verdict:</b></td><td>{overall}</td></tr>
    </table>
  </div>

  <h2>1. Initial vs Final Metrics</h2>
  <table class="metrics">
    <thead>
      <tr><th>Metric</th><th>Initial</th><th>Final</th><th>Change</th><th>Status (init → final)</th></tr>
    </thead>
    <tbody>
      <tr>
        <td><b>pI</b></td>
        <td>{n(im['pI'],2)}</td><td>{n(fm['pI'],2)}</td>
        <td class="{'change-up' if fm['pI']>im['pI'] else 'change-down'}">{(fm['pI']-im['pI']):+.2f}</td>
        <td>{badge(pi_init)} → {badge(pi_fin)}</td>
      </tr>
      <tr>
        <td><b>GRAVY</b></td>
        <td>{n(im['GRAVY'],3)}</td><td>{n(fm['GRAVY'],3)}</td>
        <td>{(fm['GRAVY']-im['GRAVY']):+.3f}</td>
        <td><span style="font-size:11px;color:#64748b">(CMC: PASS≤0)</span></td>
      </tr>
      <tr>
        <td><b>AbNatiV VH2</b></td>
        <td>{n(ia.get('vh2'),4)}</td><td>{n(fa.get('vh2'),4)}</td>
        <td>{(fa.get('vh2',0)-ia.get('vh2',0)):+.4f}</td>
        <td><span style="font-size:11px;color:#64748b">VH naturalness (higher = more VH-like)</span></td>
      </tr>
      <tr>
        <td><b>AbNatiV VHH2</b></td>
        <td>{n(ia.get('vhh2'),4)}</td><td>{n(fa.get('vhh2'),4)}</td>
        <td>{(fa.get('vhh2',0)-ia.get('vhh2',0)):+.4f}</td>
        <td><span style="font-size:11px;color:#64748b">VHH naturalness (higher = more VHH-like)</span></td>
      </tr>
      <tr>
        <td><b>AbNatiV Δ (VHH2−VH2)</b></td>
        <td>{n(ia.get('delta'),4)}</td><td>{n(fa.get('delta'),4)}</td>
        <td class="{'change-down' if fa.get('delta',0)>ia.get('delta',0) else 'change-up'}">{(fa.get('delta',0)-ia.get('delta',0)):+.4f}</td>
        <td>{badge(an_init)} → {badge(an_fin)}</td>
      </tr>
      <tr>
        <td><b>K count (surface basic)</b></td>
        <td>{im['K_count']}</td><td>{fm['K_count']}</td>
        <td>{fm['K_count']-im['K_count']:+d}</td>
        <td><span style="font-size:11px;color:#64748b">Stealth target</span></td>
      </tr>
      <tr>
        <td><b>Net basic charge (K+R−D−E)</b></td>
        <td>{im['net_basic']}</td><td>{fm['net_basic']}</td>
        <td>{fm['net_basic']-im['net_basic']:+d}</td>
        <td><span style="font-size:11px;color:#64748b">pI correlate</span></td>
      </tr>
    </tbody>
  </table>
  
  <h2>2. Tier Escalation Log</h2>
  <p style="font-size:12px;color:#64748b;margin-bottom:6px">
    V1.8.12 applies a 3-tier adaptive strategy. Each tier applies ALL eligible mutations in parallel.
    Escalation across tiers is CONDITIONAL on metric gate failure.
  </p>
  {tier_html}
  
  <h2>3. Per-Mutation Rationale</h2>
  {mut_html}
  
  <h2>4. Sequence Comparison (Region by Region)</h2>
  <p style="font-size:12px;color:#64748b;margin-bottom:8px">
    Red = original residue (replaced); Green = new residue (engineered). 
    CDR3 is the antigen-binding loop and is preserved unchanged except for mandatory Cys-gate (if applicable).
  </p>
  {diff_html}
  
  <h2>5. Full Sequence (Engineered VHH)</h2>
  <div style="font-family:Consolas,monospace;font-size:12px;padding:14px;background:#f1f5f9;border-radius:6px;word-break:break-all;border-left:4px solid #6366f1">
    {final_seq}
  </div>
  <div style="font-size:11px;color:#64748b;margin-top:6px">
    Length: {len(final_seq)} aa · Identity to input: {seq_identity:.1f}% · Mutations: {n_muts}
  </div>
  
  <h2>6. Algorithm Decision Notes</h2>
  <div style="background:#fef3c7;border-left:4px solid #f59e0b;padding:12px 16px;font-size:12px;color:#78350f;border-radius:0 6px 6px 0">
    <b>V1.8.12 Decision Logic:</b><br>
    1. <b>Family:</b> {family} — {'IGHV3 native (Tier 3 FAIC skipped)' if family == 'IGHV3' else 'non-IGHV3 (Tier 3 FAIC enabled if needed)'}<br>
    2. <b>CDR3:</b> {cdr3_len} aa — {'short, no VL-drape (Hallmark prioritized)' if cdr3_len < 10 else 'medium-length CDR3 (standard Stealth scan)' if cdr3_len < 18 else 'long CDR3 drapes over VL interface (Hallmark skipped)'}<br>
    3. <b>Stealth depth:</b> {'LIGHT' if cdr3_len < 10 else 'STANDARD' if cdr3_len < 15 else 'DEEP' if cdr3_len < 18 else 'STRICT-DEEP'}<br>
    4. <b>Cys-gate:</b> {'TRIGGERED — unpaired CDR3 Cys removed' if payload.get('unpaired_cys_cdr3') else 'not required (no unpaired Cys in CDR3)'}<br>
    5. <b>Termination:</b> {payload['stopped_at']}<br>
    <br>
    <b>Reference cohorts:</b> AutonomousHumanVH_Cohort_v1 (n=36, 100% IGHV3, PDB-validated single-domain VH);
    vhh_master_benchmarks_v3 (n=160; Clinical_VHH n=39, Engineered_Human_VH n=24, Negative_Control_VH n=10).
  </div>
  
  <div style="margin-top:30px;font-size:11px;color:#94a3b8;text-align:center">
    InSynBio AbEngineCore · VH→VHH Conversion Standard V1.8.12 · Internal Engineering Report · Confidential
  </div>
</div>
</body>
</html>"""
    out_path.write_text(html, encoding="utf-8")


def render_index(samples_summary: list) -> str:
    rows = []
    for s in samples_summary:
        verdict = s["verdict"]
        v_color = "#10b981" if ("PASS" in verdict and "FAIL" not in verdict) else ("#f59e0b" if "WARN" in verdict else "#ef4444")
        rows.append(f"""
        <tr>
          <td><a href="{s['name']}_v1812.html" style="color:#3730a3;text-decoration:none;font-weight:600">{s['name']}</a></td>
          <td>{s['family']}</td>
          <td><code>{s['cdr3']}</code></td>
          <td>{s['cdr3_len']}</td>
          <td>{s['n_mut']}</td>
          <td>{s['init_pI']} → {s['final_pI']}</td>
          <td>{s['init_delta']} → {s['final_delta']}</td>
          <td><span style="color:{v_color};font-weight:600">{verdict}</span></td>
        </tr>""")
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>CD3 V1.8.12 Batch Index</title>
<style>
  body{{font-family:-apple-system,'Segoe UI',sans-serif;background:#f8fafc;margin:0;padding:20px}}
  .wrap{{max-width:1180px;margin:0 auto;background:#fff;border-radius:8px;padding:30px}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th,td{{padding:10px;text-align:left;border-bottom:1px solid #e2e8f0}}
  th{{background:#f1f5f9;color:#475569}}
</style></head><body>
<div class="wrap">
  <h1>CD3 VH→VHH Batch Report — V1.8.12</h1>
  <p style="color:#64748b">Six anti-CD3 antibodies converted using the V1.8.12 IGHV-family-aware + CDR3-length-aware + 3-Tier algorithm. Click sample name for full per-mutation rationale.</p>
  <table>
    <thead><tr>
      <th>Sample</th><th>IGHV Family</th><th>CDR3</th><th>Len</th>
      <th>N mutations</th><th>pI (init → final)</th><th>AbNatiV Δ (init → final)</th><th>Verdict</th>
    </tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <div style="margin-top:30px;font-size:11px;color:#94a3b8">InSynBio AbEngineCore · V1.8.12 Batch · {datetime.now().strftime('%Y-%m-%d')}</div>
</div></body></html>"""


def main():
    summary = json.loads((REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
    for s in summary:
        name = s["name"]
        json_path = REPORT_DIR / f"{name}_v1812.json"
        if not json_path.exists():
            print(f"  ! Skip {name}: no JSON file")
            continue
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        out = HTML_DIR / f"{name}_v1812.html"
        generate_report(payload, out)
        print(f"  ✓ {out.name}")
    
    index_path = HTML_DIR / "index.html"
    index_path.write_text(render_index(summary), encoding="utf-8")
    print(f"\nIndex: {index_path}")


if __name__ == "__main__":
    main()
