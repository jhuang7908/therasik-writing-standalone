"""
Generate V1.8.17 HTML mutation-rationale reports from JSON outputs.
Each mutation is presented as a questionnaire card with full engineering rationale.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515" / "v1817_reports"
ALGO_VERSION = "V1.8.17"
SAMPLES = ["SP34", "Teplizumab", "OKT3", "Visilizumab", "Otelixizumab", "Foralumab"]

CSS = """
  body{font-family:'Segoe UI','Microsoft YaHei',Arial,sans-serif;background:#eef1f6;margin:0;padding:20px;color:#1a1a2e}
  .wrap{max-width:1080px;margin:0 auto;background:#fff;border-radius:10px;box-shadow:0 4px 24px rgba(0,0,0,.08);overflow:hidden}
  .header{background:linear-gradient(135deg,#0f1c3f,#1e3a6e);color:#fff;padding:28px 36px}
  .header h1{margin:0 0 8px;font-size:22px;font-weight:600}
  .header .sub{opacity:.8;font-size:13px;line-height:1.6}
  .section{padding:24px 36px;border-bottom:1px solid #e8ecf4}
  .section h2{color:#0f1c3f;font-size:15px;margin:0 0 16px;text-transform:uppercase;letter-spacing:.06em;border-left:4px solid #2d5aa0;padding-left:10px}
  .p{color:#1e8449;font-weight:600}.w{color:#d68910;font-weight:600}.f{color:#c0392b;font-weight:600}.u{color:#999}
  .metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
  .metric-card{background:#f4f7fb;border-radius:8px;padding:14px;border-left:4px solid #2d5aa0}
  .metric-card .label{font-size:10px;color:#888;text-transform:uppercase;letter-spacing:.05em}
  .metric-card .value{font-size:18px;font-weight:700;margin:6px 0 4px}
  .metric-card .change{font-size:11px;color:#666}
  .verdict-box{padding:12px 18px;border-radius:8px;font-weight:700;font-size:14px;display:inline-block}
  .policy-box{background:#f0f7ff;border:1px solid #c5d9f0;border-radius:8px;padding:16px 18px;font-size:13px;line-height:1.7}
  .gate-box{background:#fff8e6;border:1px solid #f0d78c;border-radius:8px;padding:14px 18px;font-size:13px}
  .monitor-box{background:#f5f5f5;border:1px solid #ddd;border-radius:8px;padding:14px 18px;font-size:12px;color:#444;margin-bottom:10px}
  .mut-card{border:1px solid #dde3ef;border-radius:10px;margin-bottom:16px;overflow:hidden}
  .mut-card-head{background:#f4f7fb;padding:14px 18px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;border-bottom:1px solid #dde3ef}
  .mut-num{background:#0f1c3f;color:#fff;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;flex-shrink:0}
  .mut-sub{font-size:20px;font-weight:700;color:#0f1c3f}
  .mut-pos{font-size:12px;color:#666}
  .mut-card-body{padding:16px 20px}
  .mut-q{font-size:11px;color:#2d5aa0;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin:0 0 8px}
  .mut-rationale{font-size:13px;line-height:1.75;color:#333;margin:0}
  .mut-meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
  .meta-tag{font-size:11px;background:#e8ecf4;color:#444;padding:3px 10px;border-radius:20px}
  .tier-badge{color:#fff;padding:3px 9px;border-radius:4px;font-size:11px;font-weight:600}
  table{width:100%;border-collapse:collapse;font-size:12px}
  th{background:#f4f7fb;color:#555;padding:8px 10px;text-align:left;border-bottom:2px solid #dde3ef}
  td{padding:8px 10px;border-bottom:1px solid #f0f0f0;vertical-align:top}
  .seq-block{margin-bottom:10px}
  .seq-row{display:flex;gap:12px;font-size:12px;align-items:flex-start}
  .seq-label{width:72px;font-size:11px;color:#888;text-align:right;flex-shrink:0;padding-top:2px}
  .seq-code{font-family:Consolas,'Courier New',monospace;letter-spacing:.5px;line-height:1.9}
  .seq-ruler{font-family:Consolas,monospace;font-size:10px;color:#bbb;padding-left:84px;margin-bottom:2px}
  .del{background:#fdecea;color:#c0392b;font-weight:700;padding:0 1px;border-radius:2px}
  .ins{background:#e8f6ef;color:#1e8449;font-weight:700;padding:0 1px;border-radius:2px}
  .no-mut{color:#888;font-style:italic;padding:20px;text-align:center}
  footer{text-align:center;padding:18px;font-size:11px;color:#aaa;border-top:1px solid #eee}
  .index-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;padding:24px 36px}
  .index-card{display:block;text-decoration:none;color:inherit;background:#f4f7fb;border:1px solid #dde3ef;border-radius:8px;padding:18px;transition:box-shadow .15s}
  .index-card:hover{box-shadow:0 4px 16px rgba(0,0,0,.1);border-color:#2d5aa0}
  .index-card h3{margin:0 0 6px;color:#0f1c3f;font-size:16px}
  .index-card p{margin:0;font-size:12px;color:#666}
"""


def pi_label(pI):
    if pI is None:
        return "<span class='u'>N/A</span>"
    v = float(pI)
    if v <= 9.0:
        return f"<span class='p'>{v:.2f} PASS</span>"
    if v <= 9.5:
        return f"<span class='w'>{v:.2f} WARN</span>"
    return f"<span class='f'>{v:.2f} FAIL</span>"


def an_label(d):
    if d is None:
        return "<span class='u'>N/A</span>"
    v = float(d)
    if v >= 0:
        return f"<span class='p'>{v:+.4f} EXCELLENT</span>"
    if v >= -0.12:
        return f"<span class='p'>{v:+.4f} PASS</span>"
    if v >= -0.20:
        return f"<span class='w'>{v:+.4f} WARN</span>"
    return f"<span class='f'>{v:+.4f} FAIL</span>"


def tier_badge(t: str) -> str:
    colors = {
        "Cys-gate": "#c0392b",
        "Tier 1 pI-Correction": "#8e44ad",
        "Tier 1 pI-Correction (fallback scan)": "#9b59b6",
        "Tier 1 Stealth": "#2980b9",
        "Tier 2 Hallmark": "#16a085",
        "Tier 3 FAIC": "#f39c12",
    }
    return f'<span class="tier-badge" style="background:{colors.get(t, "#555")}">{t}</span>'


def tier_category_cn(t: str) -> str:
    m = {
        "Cys-gate": " — CDR  Cys ",
        "Tier 1 pI-Correction": " — pI （）",
        "Tier 1 pI-Correction (fallback scan)": " — pI （）",
        "Tier 1 Stealth": " — Stealth  K （， VL ）",
        "Tier 2 Hallmark": " — VL （L45/W47）",
        "Tier 3 FAIC": " —  IGHV3 ",
    }
    return m.get(t, t)


def fix_html(s: str) -> str:
    """Repair accidental <motion> placeholder tags → div."""
    import re
    s = s.replace("</motion>", "</div>")
    s = re.sub(r"<motion\s+", "<div ", s)
    return s


def seq_diff_html(orig: str, eng: str) -> str:
    parts = []
    chunk = 20
    for start in range(0, max(len(orig), len(eng)), chunk):
        oc = orig[start : start + chunk]
        ec = eng[start : start + chunk]
        od = ed = ""
        for oa, ea in zip(oc, ec):
            if oa != ea:
                od += f'<span class="del">{oa}</span>'
                ed += f'<span class="ins">{ea}</span>'
            else:
                od += oa
                ed += ea
        ruler = "".join(f'<span>{start + i + 1:5d}</span>' for i in range(0, len(oc), 5))
        parts.append(
            f'<div class="seq-block"><div class="seq-ruler">{ruler}</motion>'
            f'<div class="seq-row"><span class="seq-label"> VH</span><span class="seq-code">{od}</span></div>'
            f'<motion class="seq-row"><span class="seq-label"> VHH</span><span class="seq-code">{ed}</span></div></div>'
        )
    return fix_html("".join(parts))


def _seq_diff_removed_dup(orig: str, eng: str) -> str:
    parts = []
    for start in range(0, max(len(orig), len(eng)), 20):
        oc = orig[start : start + 20]
        ec = eng[start : start + 20]
        od = ed = ""
        for oa, ea in zip(oc, ec):
            od += f'<span class="del">{oa}</span>' if oa != ea else oa
            ed += f'<span class="ins">{ea}</span>' if oa != ea else ea
        ruler = "".join(f'<span>{start + i + 1:5d}</span>' for i in range(0, len(oc), 5))
        parts.append(
            f'<div class="seq-block"><motion class="seq-ruler">{ruler}</motion>'
            f'<div class="seq-row"><span class="seq-label"> VH</span><span class="seq-code">{od}</span></motion>'
            f'<div class="seq-row"><span class="seq-label"> VHH</span><span class="seq-code">{ed}</span></motion></div>'
            .replace("<motion", "<div").replace("</motion>", "")
        )
    return "".join(parts)


def mutation_cards_html(all_mut: list) -> str:
    if not all_mut:
        return '<p class="no-mut">。</p>'
    cards = []
    for i, m in enumerate(all_mut, 1):
        tier = m.get("tier", "?")
        orig = m.get("orig_aa", "?")
        tgt = m.get("target_aa", "?")
        kabat = m.get("label_kabat", "?")
        idx = m.get("idx", 0) + 1
        rat = m.get("rationale", "—")
        cards.append(f"""
<div class="mut-card">
  <div class="mut-card-head">
    <div class="mut-num">{i}</div>
    <div>
      <div class="mut-sub">{orig} → {tgt}</div>
      <div class="mut-pos">Kabat {kabat} ·  {idx} · {tier_category_cn(tier)}</div>
    </div>
    {tier_badge(tier)}
  </div>
  <div class="mut-card-body">
    <p class="mut-q">？</p>
    <p class="mut-rationale">{rat}</p>
    <div class="mut-meta">
      <span class="meta-tag">Tier: {tier}</span>
      <span class="meta-tag">Kabat {kabat}</span>
      <span class="meta-tag">seq[{idx}]</span>
    </div>
  </div>
</div>""")
    return fix_html("".join(cards))


def build_html(d: dict) -> str:
    name = d["sample"]
    alg = d.get("algorithm_version", ALGO_VERSION)
    init_m = d["initial_metrics"]
    final_m = d["final_metrics"]
    init_a = d["initial_abnativ"]
    final_a = d["final_abnativ"]
    pi_pred = d.get("v1813_pi_prediction", {})
    sp = d.get("v1817_stealth_policy", {})
    mon = d.get("v1817_monitoring", {})
    all_mut = d.get("all_mutations", [])
    tier_log = d.get("tier_log", [])
    orig_seq = d["input_seq"]
    eng_seq = d.get("final_seq", orig_seq)
    verdict = d.get("final_verdict", "N/A")
    stopped = d.get("stopped_at", "—")
    vl_gate = d.get("vl_safety_gate", "—")

    if "FAIL" in verdict:
        vc, vb = "#c0392b", "#fdecea"
    elif "WARN" in verdict:
        vc, vb = "#d68910", "#fef9e7"
    else:
        vc, vb = "#1e8449", "#e8f6ef"

    pi_path = pi_pred.get("pi_correction_path", "—")
    pi_note = pi_pred.get("note", "")
    pi_path_color = "#1e8449" if "PASS" in pi_path else ("#d68910" if "WARN" in pi_path else "#c0392b")

    tier_rows = ""
    for tl in tier_log:
        st = tl.get("stage", "?")
        if tl.get("skipped"):
            tier_rows += f"<tr><td><b>{st}</b></td><td colspan='4'><i>{tl.get('reason', 'skipped')}</i></td></tr>"
            continue
        apps = ", ".join(tl.get("applied", [])) or "—"
        pm = tl.get("post_metrics", {})
        esc = "→ " if tl.get("escalate") else ("→ " if pm else "")
        extra = ""
        if tl.get("vl_safety_gate"):
            extra = f"<br><small style='color:#c0392b'>{tl['vl_safety_gate']}</small>"
        tier_rows += f"""<tr>
  <td><b>{st}</b>{extra}</td>
  <td>{apps}</td>
  <td>{pi_label(pm.get('pI'))}</td>
  <td>{an_label(pm.get('abnativ_delta'))}</td>
  <td>{tl.get('verdict', '')} {esc}</td>
</tr>"""

    monitor_html = ""
    for key, v in mon.items():
        monitor_html += f"""<div class="monitor-box">
  <b>{key}</b> ·  {v.get('position')} ·  {v.get('aa_orig')} →  {v.get('aa_final')}<br>
  <span style="color:#666">{v.get('note', '')}</span>
</motion>""".replace("<motion>", "").replace("</motion>", "")

    gate_html = ""
    if vl_gate == "TRIGGERED":
        gate_html = f"""<div class="gate-box">
  <b>VL ：</b><br>
  k45  Leu（VL ） CDR3 &lt; 18 aa（ CDR3 ）→  Tier 1  PASS， Tier 2 Hallmark（L45R + G44E + W47G）。
  ：Fv  k45 SASA ≈ 8 Å²（）→  VL  naked VH SASA ≈ 100 Å²（）。
</div>"""
    elif "NOT" in str(vl_gate):
        gate_html = f'<div class="monitor-box">VL ： — {vl_gate}</motion>'.replace("<motion>", "").replace("</motion>", "")

    stealth_scan = ", ".join(sp.get("stealth_scan") or []) or "（ Stealth ）"

    init_nb = sp.get("net_basic", init_m.get("K_count", 0) + init_m.get("R_count", 0) - init_m.get("D_count", 0) - init_m.get("E_count", 0))
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="robots" content="noindex,nofollow">
<title>InSynBio VH→VHH | {name} | {alg} </title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

<div class="header">
  <div class="sub">InSynBio AbEngineCore · VH→VHH Path C · {alg} ·  · </motion>
  <h1>{name} — </h1>
  <div class="sub">
    IGHV: <b>{d.get('ighv_family','?')}</b> ({d.get('ighv_evidence','')}) &nbsp;|&nbsp;
    CDR3: <b>{d.get('cdr3_aa','?')}</b> ({d.get('cdr3_len','?')} aa) &nbsp;|&nbsp;
    : <b>{len(all_mut)}</b> &nbsp;|&nbsp; : <b>{stopped[:50]}</b>
  </div>
</div>

<div class="section">
  <h2></h2>
  <div class="verdict-box" style="background:{vb};border:2px solid {vc};color:{vc}">{verdict}</motion>
  <p style="font-size:12px;color:#888;margin:12px 0 0">
    pI: ≤9.0 PASS · ≤9.5 WARN · &gt;9.5 FAIL &nbsp;|&nbsp;
    AbNatiV Δ: ≥0 EXCELLENT · ≥−0.12 PASS · ≥−0.20 WARN
  </p>
</motion>

<div class="section">
  <h2>（ VH →  VHH）</h2>
  <div class="metric-grid">
    <div class="metric-card"><div class="label">pI</div><div class="value">{pi_label(final_m.get('pI'))}</div>
      <div class="change">{init_m.get('pI')} → {final_m.get('pI')}</div></div>
    <motion class="metric-card"><div class="label">AbNatiV Δ</motion><div class="value">{an_label(final_a.get('delta'))}</div>
      <div class="change">{init_a.get('delta')} → {final_a.get('delta')}</div></motion>
    <div class="metric-card"><motion class="label">GRAVY</motion><motion class="value" style="font-size:16px">{final_m.get('GRAVY')}</motion>
      <div class="change">{init_m.get('GRAVY')} → {final_m.get('GRAVY')}</div></div>
    <div class="metric-card"><div class="label">net_basic</motion><motion class="value" style="font-size:16px">{final_m.get('net_basic','—')}</motion>
      <div class="change">{init_m.get('K_count',0)+init_m.get('R_count',0)-init_m.get('D_count',0)-init_m.get('E_count',0)} → {final_m.get('net_basic','—')}</div></div>
  </div>
</motion>

<div class="section">
  <h2>V1.8.17 Stealth （， CDR3 ）</h2>
  <div class="policy-box">
    <b>net_basic = {sp.get('net_basic', '?')}</b> &nbsp;|&nbsp;  pI = {sp.get('init_pI', '?')}<br>
    <b>：</b> {sp.get('stealth_depth', '—')}<br>
    <b>：</b> {stealth_scan}<br><br>
    <small>Stealth （K→R/Q/D/T）， VL （：Stealth K  Fv  SASA ≈94 Å²，）。
    Hallmark（L45R/W47G/G44E） VL  BSA→SASA 。</small>
  </div>
  {gate_html}
</div>

<div class="section">
  <h2>pI （V1.8.13 ）</h2>
  <div class="policy-box" style="border-color:{pi_path_color}">
     pI: <b>{pi_pred.get('predicted_pi_post_engineering', '—')}</b> &nbsp;|&nbsp;
    : <span style="color:{pi_path_color}"><b>{pi_path}</b></span> &nbsp;|&nbsp;
     K→D : <b>{pi_pred.get('n_corrections_planned', 0)}</b><br>
    <span style="color:#555">{pi_note}</span>
  </div>
</div>

<div class="section">
  <h2> —  {len(all_mut)} </h2>
  <p style="font-size:12px;color:#666;margin:-8px 0 16px">
    ： · Kabat  ·  · （）。
  </p>
  {mutation_cards_html(all_mut)}
</div>

<div class="section">
  <h2>（）</h2>
  {monitor_html if monitor_html else '<p class="no-mut">。</p>'}
</motion>

<div class="section">
  <h2> Tier </h2>
  <table>
    <tr><th></th><th></th><th> pI</th><th> AbNatiV Δ</th><th></th></tr>
    {tier_rows}
  </table>
</div>

<div class="section">
  <h2></h2>
  <p style="font-size:12px;color:#888"><span class="del"></span>= <span class="ins"></span>= ·  {sum(1 for a,b in zip(orig_seq,eng_seq) if a!=b)}</p>
  {seq_diff_html(orig_seq, eng_seq)}
  <p style="font-size:11px;word-break:break-all;margin-top:12px"><b>：</b><br><code>{orig_seq}</code></p>
  <p style="font-size:11px;word-break:break-all"><b>：</b><br><code>{eng_seq}</code></p>
</div>

<footer>InSynBio AbEngineCore · {alg} · {name} ·  UTC {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} ·  — </footer>
</div>
</body>
</html>"""
    return fix_html(html)


def build_index(reports: list[tuple[str, dict]]) -> str:
    cards = ""
    for name, d in reports:
        n = len(d.get("all_mutations", []))
        v = d.get("final_verdict", "")
        cards += f"""<a class="index-card" href="{name}_v1817.html">
  <h3>{name}</h3>
  <p>IGHV {d.get('ighv_family','?')} · CDR3 {d.get('cdr3_len','?')} aa · {n} </p>
  <p style="margin-top:6px;font-weight:600">{v[:40]}</p>
</a>"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="robots" content="noindex,nofollow">
<title>CD3 VH→VHH V1.8.17 </title>
<style>{CSS}
  .idx-header{{background:linear-gradient(135deg,#0f1c3f,#1e3a6e);color:#fff;padding:32px 36px}}
  .idx-header h1{{margin:0;font-size:24px}}
</style>
</head>
<body>
<div class="wrap">
<div class="idx-header">
  <p style="opacity:.8;margin:0 0 8px;font-size:13px">InSynBio · CD3  · {ALGO_VERSION}</p>
  <h1>VH→VHH  — 6 </h1>
  <p style="opacity:.75;font-size:13px;margin:12px 0 0">、Stealth 、VL 、。</p>
</div>
<div class="index-grid">{cards}</div>
<footer> · </footer>
</div>
</body>
</html>"""


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    html_dir = REPORT_DIR / "html"
    html_dir.mkdir(exist_ok=True)
    reports = []
    for name in SAMPLES:
        jp = REPORT_DIR / f"{name}_v1817.json"
        if not jp.exists():
            print(f"  [SKIP] {name}")
            continue
        d = json.loads(jp.read_text(encoding="utf-8"))
        html = build_html(d)
        out = html_dir / f"{name}_v1817.html"
        out.write_text(html, encoding="utf-8")
        print(f"  [OK] {out.name} ({len(d.get('all_mutations', []))} mutations)")
        reports.append((name, d))
    if reports:
        idx = build_index(reports)
        (html_dir / "index.html").write_text(idx, encoding="utf-8")
        print(f"\n  [OK] index.html")
    print(f"\n: {html_dir}")


if __name__ == "__main__":
    main()
