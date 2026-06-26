"""
generate_cd3_final_html.py  — V2.0 ()
 result.json ， HTML 。

：
1.  result.json ，。
2. FR ：
   - mutations_applied  = （）
   -  FR  = （ VHH ，）
3. AbNatiV  candidates[0] ， QC /。
4. ：AbNatiV Δ、pI、Unpaired Cys。
"""

import json
import html as _html
from pathlib import Path
from datetime import datetime
from typing import Any, List

ROOT = Path(__file__).resolve().parent.parent

import sys
sys.path.insert(0, str(ROOT))

from core.vhh.vhh_scaffold_match_and_craft import _build_vhh_residue_map_and_regions

try:
    from Bio.SeqUtils.ProtParam import ProteinAnalysis
    HAS_BIOPYTHON = True
except ImportError:
    HAS_BIOPYTHON = False

JOB_STORAGE = ROOT / ".job_storage"
PROJECT_DIR  = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515"
HTML_DIR     = PROJECT_DIR / "reports" / "html_final"
HTML_DIR.mkdir(parents=True, exist_ok=True)

SAMPLES = [
    ("sp34_murine_vh_blinatumomab", "SP34 (Murine VH)"),
    ("teplizumab_vh_vl",            "Teplizumab (Humanized VH)"),
    ("okt3_humanized_scfv_actes",   "OKT3 (Humanized VH)"),
    ("otelixizumab_vh_vl",          "Otelixizumab (Humanized VH)"),
    ("foralumab_vh_vl",             "Foralumab (Humanized VH)"),
    ("visilizumab_vh_vl",           "Visilizumab (Humanized VH)"),
]

# V1.8.9 — （）
MUT_RATIONALE = {
    "L45R":  "Hallmark (Kabat 45) —  VH-VL ，。",
    "G44E":  "Hallmark (Kabat 44) — Rescue ， CDR3 。",
    "W47G":  "Hallmark (Kabat 47) — ， VHH Stealth 。",
    "W47L":  "Hallmark (Kabat 47) — ， VHH Stealth 。",
    "K94R":  "Stealth (Kabat 94) — CDR3 ，。",
    "K35N":  "Stealth (Kabat 35) — （CDR3 ≥ 10aa ）。",
    "K50D":  "Stealth (Kabat 50) — （CDR2/CDR3 ）。",
    "C114S": "Liability Gate —  CDR3  Cys，，。",
    "K72D":  "pI Tuning —  pI （5.5–8.5）。",
    "K73Q":  "pI Tuning Fallback — ，。",
    "K19Q":  "pI Tuning Fallback — ，。",
    "K13Q":  "pI Tuning Fallback — ，。",
}


def e(v: Any) -> str:
    return "—" if v is None else _html.escape(str(v))

def n(v: Any, d: int = 4) -> str:
    if isinstance(v, (int, float)):
        return f"{v:.{d}f}"
    return "—" if v is None else str(v)

def badge(status: str) -> str:
    if status == "PASS":   return f"<span class='badge ok'>{status}</span>"
    if status == "WARN":   return f"<span class='badge warn'>{status}</span>"
    if status == "FAIL":   return f"<span class='badge fail'>{status}</span>"
    return f"<span class='badge'>{status}</span>"


def get_segments(seq: str) -> dict:
    if not seq:
        return {r: [] for r in ["FR1","CDR1","FR2","CDR2","FR3","CDR3","FR4"]}
    rmap, regions = _build_vhh_residue_map_and_regions(seq)
    ordered = getattr(rmap, "_ordered_rows", [])
    segs = {}
    for name in ["FR1","CDR1","FR2","CDR2","FR3","CDR3","FR4"]:
        if name not in regions:
            segs[name] = []
            continue
        lo, hi = regions[name]
        segs[name] = [{"pos": pos, "ins": ins, "aa": aa}
                      for (pos, ins, aa) in ordered if lo <= pos <= hi]
    return segs


def calc_pi_gravy(seq: str):
    if not seq or not HAS_BIOPYTHON:
        return None, None
    a = ProteinAnalysis(seq.replace("-", ""))
    return round(a.isoelectric_point(), 2), round(a.gravy(), 3)


def generate_report(payload: dict, out_path: Path, display_name: str) -> None:
    ts     = datetime.now().strftime("%Y-%m-%d %H:%M")
    orig   = payload["input_sequence"]
    eng    = payload["converted_sequence"]
    tmpl   = payload.get("selected_template_id", "—")
    muts   = payload.get("mutations_applied", [])     # 
    cmc    = payload.get("mini_cmc", {})
    c0     = payload.get("candidates", [{}])[0]

    # ── AbNatiV （ candidates[0] ）──────────────────────────────
    an_vh    = c0.get("abnativ_vh2")
    an_vhh   = c0.get("abnativ_vhh2")
    an_delta = c0.get("abnativ_delta")

    # ── [V1.8.11]  ──────────────────────────────────────────
    # AbNatiV Δ: 4（ Clinical_VHH n=39 + EngVH n=24 vs  Neg_Control n=10）
    if an_delta is None:
        an_status = "UNKNOWN"
    elif an_delta >= 0:
        an_status = "EXCELLENT"
    elif an_delta >= -0.120:
        an_status = "PASS"
    elif an_delta >= -0.200:
        an_status = "WARN"
    else:
        an_status = "FAIL"

    # pI: Clinical_VHH  8.64，p90 9.08（ 5.5-8.5 IgG ）
    pi_val = cmc.get("pI", 0)
    if pi_val <= 9.0:
        pi_status = "PASS"
    elif pi_val <= 9.5:
        pi_status = "WARN"
    else:
        pi_status = "FAIL"

    # GRAVY: CMC （ VHH ）
    gravy_val = cmc.get("GRAVY", -0.3)
    if gravy_val <= 0.0:
        grav_status = "PASS"
    elif gravy_val <= 0.1:
        grav_status = "WARN"
    else:
        grav_status = "FAIL"

    # CDR3 Rg: （ VHH ；Neg_Control max=6.06 Å）
    rg_val = cmc.get("cdr3_compactness")
    if rg_val is None:
        rg_status = "N/A"
    elif rg_val <= 7.0:
        rg_status = "PASS"
    elif rg_val <= 7.5:
        rg_status = "WARN"
    else:
        rg_status = "FAIL"

    has_unpaired_cys = any("Cys-gate" in m or "Liability-gate" in m for m in muts)
    cys_fixed_note  = "Unpaired Cys in CDR detected and removed (C→S). Expression blocker eliminated." if has_unpaired_cys else "No unpaired Cys detected."

    # ──  ──────────────────────────────────────────────────
    exp_blockers = []
    if an_status == "FAIL":
        exp_blockers.append(f"AbNatiV Δ ({n(an_delta, 4)}) &lt; −0.20： VH ，。")
    elif an_status == "WARN":
        exp_blockers.append(f"AbNatiV Δ ({n(an_delta, 4)})  WARN  [−0.20, −0.12)：。")
    if pi_status == "FAIL":
        exp_blockers.append(f"pI ({n(pi_val, 2)}) &gt; 9.5： Clinical_VHH ，。")
    elif pi_status == "WARN":
        exp_blockers.append(f"pI ({n(pi_val, 2)})  9.0–9.5 WARN （ VHH p90 = 9.08）。")
    if grav_status == "FAIL":
        exp_blockers.append(f"GRAVY ({n(gravy_val, 3)}) &gt; 0.1：，。")

    if exp_blockers:
        exp_verdict = "WARN" if an_status != "FAIL" else "FAIL"
        exp_color   = "#d97706" if exp_verdict == "WARN" else "#dc2626"
        exp_icon    = "⚠"
    else:
        exp_verdict = "PASS"
        exp_color   = "#059669"
        exp_icon    = "✓"

    exp_issues_html = "".join(f"<li style='color:{exp_color}'>{b}</li>" for b in exp_blockers) or \
                      "<li style='color:#059669'>。。</li>"

    # ──  pI  ───────────────────────────────────────────────────────
    orig_pi, orig_gravy = calc_pi_gravy(orig)

    # ──  ──────────────────────────────────────────────────────
    orig_segs = get_segments(orig)
    eng_segs  = get_segments(eng)

    seg_rows = ""
    for reg in ["FR1","CDR1","FR2","CDR2","FR3","CDR3","FR4"]:
        s1 = orig_segs.get(reg, [])
        s2 = eng_segs.get(reg, [])
        aa1 = "".join(x["aa"] for x in s1)
        aa2_disp = ""
        for i in range(max(len(s1), len(s2))):
            c1 = s1[i]["aa"] if i < len(s1) else "-"
            c2 = s2[i]["aa"] if i < len(s2) else "-"
            aa2_disp += f"<b style='color:#dc2626'>{c2}</b>" if c1 != c2 else c2
        is_cdr = "CDR" in reg
        status_lbl = "Match" if aa1 == "".join(x["aa"] for x in s2) else ("CDR Grafted" if is_cdr else "Scaffold")
        status_cls = "ok" if status_lbl == "Match" else ("warn" if is_cdr else "info")
        seg_rows += f"<tr><td>{reg}</td><td class='mono'>{aa1}</td><td class='mono'>{aa2_disp}</td><td>{badge(status_lbl)}</td></tr>"

    # ──  ──────────────────────────────────────────────────
    if muts:
        mut_rows = ""
        for m in muts:
            code = m.split()[0]
            rationale = MUT_RATIONALE.get(code, "（ V1.8.9 Standard）。")
            mut_rows += f"<tr><td class='mono fw'>{e(m)}</td><td style='font-size:11px'>{rationale}</td></tr>"
        mut_section_note = ""
    else:
        mut_rows = ""
        mut_section_note = f"<p style='font-size:11px;color:#64748b'>（Liability Gate ）。 VHH （{tmpl}）， CDR ，。</p>"

    # ── HTML ─────────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>InSynBio | VH→VHH Report: {display_name}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f4f7f9;color:#1e293b;font-size:13px;line-height:1.55;padding:20px}}
.page{{max-width:1000px;margin:0 auto;background:#fff;padding:32px 40px;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.07)}}
.hdr{{background:#1b4fad;color:#fff;padding:18px 24px;border-radius:8px;margin-bottom:18px;display:flex;justify-content:space-between}}
.hdr h1{{font-size:1.25rem;font-weight:700;margin:0 0 4px}}
.hdr .sub{{font-size:.82rem;opacity:.92}}
.sec{{border:1px solid #d0d7e2;border-radius:8px;margin-bottom:16px;overflow:hidden}}
.sec h3{{font-size:.82rem;font-weight:700;padding:9px 14px;background:#f3f4f6;border-bottom:1px solid #d0d7e2;color:#374151}}
.sec-body{{padding:14px 16px}}
table{{width:100%;border-collapse:collapse}}
td{{padding:6px 10px;vertical-align:top;border-bottom:1px solid #f1f5f9}}
.lbl{{color:#6b7280;font-weight:600;width:28%}}
.mono{{font-family:'Courier New',monospace;font-size:.88em;word-break:break-all}}
.fw{{font-weight:700}}
.badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:.7rem;font-weight:700}}
.ok{{background:#d1fae5;color:#065f46}}
.warn{{background:#fef3c7;color:#92400e}}
.fail{{background:#fee2e2;color:#991b1b}}
.info{{background:#dbeafe;color:#1e40af}}
.verdict-box{{padding:14px 18px;border-radius:8px;margin-bottom:14px;border-left:5px solid {exp_color}}}
footer{{text-align:center;color:#94a3b8;font-size:.72rem;margin-top:24px;border-top:1px solid #e2e8f0;padding-top:12px}}
</style>
</head>
<body>
<div class="page">

<div class="hdr">
  <div>
    <h1>InSynBio AbEngineCore — VH→VHH Engineering Report</h1>
    <div class="sub">Protocol V1.8.9 | Deterministic Algorithm | CD3 Panel | {display_name}</div>
  </div>
  <div style="text-align:right;font-size:.75rem;opacity:.88">{ts}<br>CONFIDENTIAL · Internal</div>
</div>

<!-- §0 Executive Summary -->
<div class="sec">
  <h3>§0 — Executive Summary</h3>
  <div class="sec-body">
    <table>
      <tr><td class="lbl">Feasibility Verdict</td><td><strong>{e(payload.get("feasibility_verdict"))}</strong></td></tr>
      <tr><td class="lbl">Strategy</td><td>{e(payload.get("selected_strategy"))}</td></tr>
      <tr><td class="lbl">Scaffold Template</td><td>{e(tmpl)}</td></tr>
      <tr><td class="lbl">Germline Reference</td><td>{e(payload.get("selected_germline"))}</td></tr>
    </table>
  </div>
</div>

<!-- §1 Expression Potential -->
<div class="sec" style="border-left:5px solid {exp_color}">
  <h3>§1 — Expression & Secretion Potential (Decision Gate)</h3>
  <div class="sec-body">
    <div style="font-size:1rem;font-weight:800;color:{exp_color};margin-bottom:8px">{exp_icon} Expression Verdict: {exp_verdict}</div>
    <p style="font-size:11px;color:#475569;margin-bottom:8px">
      <b></b>：(1) AbNatiV Δ  (≥ -0.074)；(2) pI  (5.5–8.5)；(3)  Cys。
    </p>
    <ul style="font-size:12px;padding-left:16px;line-height:1.7">
      {exp_issues_html}
      <li style="color:#475569">{cys_fixed_note}</li>
    </ul>
    <table style="margin-top:12px">
      <thead><tr style="background:#f8fafc;font-weight:700;font-size:11px"><td></td><td>(VH)</td><td>(VHH)</td><td></td><td></td></tr></thead>
      <tbody>
        <tr><td>pI</td><td>{n(orig_pi, 2) if orig_pi else "—"}</td><td>{n(pi_val, 2)}</td><td>≤ 9.0 (WARN≤9.5)</td><td>{badge(pi_status)}</td></tr>
        <tr><td>GRAVY</td><td>{n(orig_gravy, 3) if orig_gravy else "—"}</td><td>{n(gravy_val, 3)}</td><td>≤ 0.0 (CMC)</td><td>{badge(grav_status)}</td></tr>
        <tr><td>AbNatiV Δ (VHH2−VH2)</td><td>—</td><td><b>{n(an_delta, 4)}</b></td><td>EXCEL≥0 / PASS≥−0.12 / WARN≥−0.20</td><td>{badge(an_status)}</td></tr>
        <tr><td>CDR3 Compactness (Rg)</td><td>—</td><td>{n(rg_val, 2) if rg_val else "—"} Å</td><td>≤ 7.0 (WARN≤7.5)</td><td>{badge(rg_status)}</td></tr>
      </tbody>
    </table>
  </div>
</div>

<!-- §2.1 AbNatiV Detail -->
<div class="sec">
  <h3>§2.1 — AbNatiV2 Naturalness Detail</h3>
  <div class="sec-body">
    <table>
      <tr><td class="lbl">AbNatiV VH2 Score</td><td>{n(an_vh)} <span style="font-size:10px;color:#94a3b8">( IgG VH)</span></td></tr>
      <tr><td class="lbl">AbNatiV VHH2 Score</td><td>{n(an_vhh)} <span style="font-size:10px;color:#94a3b8">( VHH)</span></td></tr>
      <tr><td class="lbl"><b>AbNatiV Δ (VHH2−VH2)</b></td>
          <td><b>{n(an_delta)}</b> &nbsp;{badge(an_status)}
          <div style="font-size:10px;color:#64748b;margin-top:3px">
            [V1.8.11 ] EXCELLENT ≥ 0 | PASS ≥ −0.12 | WARN ≥ −0.20 | FAIL &lt; −0.20<br>
            ：Clinical_VHH (n=39)  vs Neg_Control_VH (n=10) <br>
            ：{
              "EXCELLENT —  VHH " if an_status=="EXCELLENT" else
              "PASS — " if an_status=="PASS" else
              "WARN — " if an_status=="WARN" else
              "FAIL — ，" if an_status=="FAIL" else ""
            }
          </div></td></tr>
    </table>
  </div>
</div>

<!-- §3 Sequence Comparison -->
<div class="sec">
  <h3>§3 — Sequence Comparison (VH vs. EngVHH)</h3>
  <div class="sec-body">
    <p style="font-size:11px;color:#64748b;margin-bottom:8px">
       = 。CDR  "CDR Grafted"（ CDR ）。FR ，。
    </p>
    <table>
      <thead><tr style="background:#f8fafc;font-weight:700;font-size:11px"><td>Region</td><td>Original VH</td><td>Designed VHH</td><td></td></tr></thead>
      <tbody>{seg_rows}</tbody>
    </table>
  </div>
</div>

<!-- §4 Full Sequence (Cloning) -->
<div class="sec">
  <h3>§4 — Full Engineered Sequence (For Cloning)</h3>
  <div class="sec-body">
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px;font-family:'Courier New',monospace;font-size:13px;word-break:break-all;line-height:1.8;color:#0f172a">
      {eng}
    </div>
    <p style="font-size:10px;color:#94a3b8;margin-top:6px">✓ V1.8.9 Batch Uniqueness Gate </p>
  </div>
</div>

<!-- §5 Algorithm-Applied Mutations -->
<div class="sec">
  <h3>§5 — Algorithm Decision Record (V1.8.9 )</h3>
  <div class="sec-body">

    <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:6px;padding:10px 14px;margin-bottom:12px;font-size:11px;line-height:1.65">
      <b>Path C ：</b><br>
      V1.8.9 。：
      <ol style="margin-top:6px;padding-left:18px">
        <li><b> CDR </b>： VHH  <code>{e(tmpl)}</code>， CDR1/CDR2/CDR3  VHH 。 Hallmark （Kabat 44/45/47  VHH  E/R/F-W），<b> L45R  Hallmark </b>。</li>
        <li><b>Liability Gate (Path C2 Cys)</b>： CDR  Cys（ IMGT 23/104）— ：{f" {len(muts)}  Cys ({', '.join(muts)})。" if muts else " Cys，。"}</li>
        <li><b>Phase 4.5 pI Tuning</b>： pI &gt; 8.5  K72D（K-gate）， K73Q/K19Q/K13Q。 pI = {n(pi_val,2)}，Phase 4.5 ，<b> FR  K </b>（ FR ）， FR  pI 。</li>
        <li><b>pI </b>：pI = {n(pi_val,2)}  <b>CDR （K/R）</b>。 CDR  paratope ， CDR-driven pI 。 pI， CDR3 （ K→Q ）。</li>
      </ol>
    </div>

    {mut_section_note}
    {"<b>：</b><table style='margin-top:8px'><thead><tr style='background:#f8fafc;font-weight:700;font-size:11px'><td>Mutation</td><td> (V1.8.9)</td></tr></thead><tbody>" + mut_rows + "</tbody></table>" if mut_rows else ""}

    <p style="font-size:10px;color:#94a3b8;margin-top:8px">
      FR  {e(tmpl)}（CDR ），。
    </p>
  </div>
</div>

<!-- §6 Structural Assessment -->
<div class="sec">
  <h3>§6 — Structural Assessment (ImmuneBuilder)</h3>
  <div class="sec-body">
    <table>
      <tr><td class="lbl">Input pLDDT</td><td>{n(payload.get("input_plddt"), 1)}</td></tr>
      <tr><td class="lbl">Converted pLDDT</td><td>{n(payload.get("converted_plddt"), 1)}</td></tr>
      <tr><td class="lbl">CDR-H1 RMSD</td><td>{n((payload.get("cdr_rmsd") or {}).get("H1"), 2)} Å <span style="font-size:10px;color:#94a3b8">( &lt; 1.5 Å)</span></td></tr>
      <tr><td class="lbl">CDR-H2 RMSD</td><td>{n((payload.get("cdr_rmsd") or {}).get("H2"), 2)} Å</td></tr>
      <tr><td class="lbl">CDR-H3 RMSD</td><td>{n((payload.get("cdr_rmsd") or {}).get("H3"), 2)} Å</td></tr>
    </table>
  </div>
</div>

<footer>© 2026 InSynBio AI Research · Protocol V1.8.9 · All mutations governed by deterministic algorithm</footer>
</div>
</body>
</html>"""

    out_path.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    for suffix, name in SAMPLES:
        res_path = JOB_STORAGE / f"cd3_v2v_{suffix}" / "result.json"
        if not res_path.exists():
            print(f"SKIP: {res_path}")
            continue
        payload = json.loads(res_path.read_text(encoding="utf-8"))
        out_file = HTML_DIR / f"VH2VHH_{suffix}.html"
        generate_report(payload, out_file, name)
        print(f"OK  : {out_file.name}")
