#!/usr/bin/env python3
"""
Render IgG CMC HTML in the same layout as legacy API exports (vhvl-parity-light):
  §0 Run summary, §1 sequences, §1b IMGT, §2 Fv, §3 benchmark, §4 physicochemical,
  §5 param-grid (25 tiles), §6 engineering, §7 flags, §8 roadmap.

Input: JSON from ``run_igg_cmc_pipeline`` / ``adalimumab_cmc_pipeline_snapshot.json`` style.
"""
from __future__ import annotations

import argparse
import html as html_module
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]

CSS = """\
:root{--ok:#059669;--warn:#d97706;--fail:#dc2626;--muted:#6b7280;--bg:#f9fafb;
     --card:#fff;--border:#e5e7eb;--accent:#4f46e5}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:#111;font-size:13px;line-height:1.55}
.page{max-width:900px;margin:0 auto;padding:24px 16px}
.cover{background:linear-gradient(135deg,#1e1b4b,#312e81);color:#fff;border-radius:10px;padding:32px 28px;margin-bottom:24px}
.cover h1{font-size:1.5rem;font-weight:700;margin-bottom:6px}
.cover .sub{font-size:0.85rem;opacity:.88;margin-bottom:12px}
.cover .meta{display:flex;gap:16px;flex-wrap:wrap;font-size:0.78rem;opacity:.82;align-items:center}
.header-meta{width:100%;margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid rgba(255,255,255,.22);
             display:flex;flex-direction:column;gap:4px;font-family:ui-monospace,monospace;font-size:0.72rem;opacity:.75}
.section{background:var(--card);border:1px solid var(--border);border-radius:8px;margin-bottom:16px;overflow:hidden}
.section h3{font-size:0.85rem;font-weight:700;padding:10px 16px;background:#f3f4f6;border-bottom:1px solid var(--border);color:#374151}
.section-body{padding:14px 16px}
table.kv{width:100%;border-collapse:collapse;font-size:0.82rem}
table.kv td{padding:6px 8px;vertical-align:top;border-bottom:1px solid #f3f4f6}
table.kv tr:nth-child(even){background:#f9fafb}
.lbl{color:#6b7280;font-weight:600;width:38%;white-space:nowrap}
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:0.72rem;font-weight:700}
.badge-ok{background:#d1fae5;color:#065f46}.badge-warn{background:#fef3c7;color:#92400e}.badge-fail{background:#fee2e2;color:#991b1b}.badge-info{background:#dbeafe;color:#1e40af}
.seq-block{margin:10px 0;background:#f8f9fa;border:1px solid #e9ecef;border-radius:6px;padding:10px 12px}
.seq-label{font-size:0.78rem;font-weight:700;color:#495057;margin-bottom:6px}
.seq-len{font-weight:400;color:#6b7280}
.seq-body{font-family:'Consolas','Courier New',monospace;font-size:0.82em;letter-spacing:.03em;word-break:break-all;line-height:1.7;color:#111}
.data-table{width:100%;border-collapse:collapse;font-size:0.82rem;margin-top:8px}
.data-table th,.data-table td{padding:8px 10px;border-bottom:1px solid var(--border);text-align:left;vertical-align:top}
.data-table th{background:#f3f4f6;color:#374151;font-weight:600;font-size:0.74rem}
.score-row{display:flex;align-items:flex-end;gap:28px;margin:8px 0 4px;flex-wrap:wrap}
.score-val{font-size:2rem;font-weight:800;color:var(--accent)}
.score-lbl{font-size:0.72rem;color:var(--muted);margin-bottom:4px}
.score-rank{font-size:1.05rem;font-weight:700;color:var(--ok)}
.interp{font-size:0.8rem;color:var(--muted);line-height:1.5;margin-top:6px}
.risk-low{color:var(--ok);font-weight:600}.risk-mod{color:var(--warn);font-weight:600}.risk-high{color:var(--fail);font-weight:600}
.flag-list{list-style:none;padding:0;margin:8px 0 0 0}
.flag-list li{padding:6px 10px;border-left:3px solid var(--warn);margin-bottom:6px;font-size:0.82rem;background:#fffbeb}
.flag-hint{font-size:0.72rem;color:var(--muted);margin-top:4px;line-height:1.45;max-width:52rem}
.param-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-top:10px;font-size:0.76rem}
@media(max-width:900px){.param-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.param-grid{grid-template-columns:1fr}}
.param-cell{border:1px solid var(--border);border-radius:6px;padding:8px 10px;background:#fafafa;line-height:1.35}
.param-title-row{display:flex;align-items:center;gap:6px;min-width:0}
.param-title-row .pn{font-size:0.66rem;color:var(--muted);flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}
.param-cell .pv{margin-top:6px;display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.param-cell .pv-val{font-size:0.95rem;font-weight:800;color:#111;letter-spacing:-0.02em}
.param-cell .pv .rk{font-size:0.68rem;font-weight:700}
.param-cell .gate{font-size:0.62rem;color:var(--muted);margin-top:6px;line-height:1.45}
.param-cell .gate-ref{margin-top:4px;font-size:0.6rem;color:var(--muted);opacity:.92}
.param-cell .interp2{font-size:0.62rem;color:var(--muted);margin-top:4px;line-height:1.35}
.param-panel-intro{margin-bottom:6px}
.param-panel-bullets{margin:0 0 12px 18px;padding:0;font-size:0.78rem;color:var(--muted);line-height:1.5}
.param-panel-bullets li{margin-bottom:4px}
.param-grid-hint{font-size:0.76rem;color:var(--muted);margin-bottom:6px}
.param-dot{display:inline-block;width:7px;height:7px;border-radius:50%;flex-shrink:0;margin-top:2px}
.param-dot.low{background:var(--ok)}.param-dot.mod{background:var(--warn)}.param-dot.high{background:var(--fail)}.param-dot.na{background:#94a3b8}
.idx-banner{margin-top:14px;padding:12px 14px;background:#eef2ff;border:1px solid #c7d2fe;border-radius:8px}
.idx-banner h4{margin:0 0 6px;font-size:0.82rem;color:#3730a3;font-weight:700}
.idx-banner .idx-note{font-size:0.76rem;color:#4338ca;line-height:1.45;margin-bottom:10px}
.grid-readme{margin-top:12px;padding:10px 12px;background:#fffbeb;border-left:3px solid var(--warn);font-size:0.78rem;color:#374151;line-height:1.5}
footer{text-align:center;color:var(--muted);font-size:0.75rem;margin-top:24px;padding-top:12px;border-top:1px solid var(--border)}
@media print{
  @page{margin:11mm 12mm;size:A4}
  html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  body{background:#fff!important;color:#111;font-size:10.5px;line-height:1.42}
  .page{max-width:100%;padding:0;margin:0}
  .cover{
    background:#1e1b4b!important;
    break-inside:avoid;
    page-break-inside:avoid;
    margin-bottom:10px;
    padding:18px 20px;
    border-radius:6px;
  }
  /* Critical: do NOT keep entire .section on one page — tall §5 grids caused blank half-pages */
  .section{
    break-inside:auto!important;
    page-break-inside:auto!important;
    margin-bottom:10px;
    orphans:3;
    widows:3;
  }
  .section h3{
    break-after:avoid;
    page-break-after:avoid;
  }
  .section-body{padding:10px 12px}
  .param-grid{
    grid-template-columns:repeat(3,minmax(0,1fr));
    gap:5px;
    break-inside:auto;
    page-break-inside:auto;
  }
  /* Single metric tiles stay intact when possible; grid itself may span pages */
  .param-cell{
    break-inside:avoid;
    page-break-inside:avoid;
  }
  table.data-table,table.kv{width:100%;font-size:9.5px}
  table.data-table th,table.data-table td,table.kv td{padding:4px 6px}
  .seq-body{font-size:9px;line-height:1.5}
  .seq-block{break-inside:auto}
  .idx-banner,.grid-readme{break-inside:avoid;page-break-inside:avoid}
  .score-row{gap:16px}
  .score-val{font-size:1.5rem}
  footer{margin-top:12px;padding-top:8px;break-inside:avoid}
}
"""


def e(s: Any) -> str:
    return html_module.escape("" if s is None else str(s), quote=True)


def risk_dot_class(risk: str) -> str:
    r = (risk or "").upper()
    if r == "LOW":
        return "low"
    if r == "MODERATE":
        return "mod"
    if r == "HIGH":
        return "high"
    return "na"


def risk_css_class(risk: str) -> str:
    r = (risk or "").upper()
    if r == "LOW":
        return "risk-low"
    if r == "MODERATE":
        return "risk-mod"
    if r == "HIGH":
        return "risk-high"
    return "muted"


def fmt_val(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        s = f"{v:.4g}"
        return s
    return str(v)


def imgt_tables(seg: Dict[str, Any]) -> str:
    if not seg or seg.get("error"):
        return '<p class="interp">IMGT segmentation unavailable.</p>'
    order = ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]
    out: List[str] = []
    for chain in ("VH", "VL"):
        block = seg.get(chain)
        if not isinstance(block, dict):
            continue
        rows = []
        for reg in order:
            seq = block.get(reg) or ""
            if not seq:
                continue
            rows.append(
                f"<tr><td>{e(reg)}</td><td>{len(seq)}</td>"
                f'<td style="font-family:ui-monospace,monospace;font-size:.72rem;word-break:break-all">{e(seq)}</td></tr>'
            )
        out.append(f'<div style="margin-top:12px"><strong>{chain}</strong> (IMGT)</div>')
        out.append(
            '<table class="data-table" style="margin-top:6px"><tr><th>Region</th><th>Len</th><th>Sequence</th></tr>'
            + "".join(rows)
            + "</table>"
        )
    return "\n".join(out)


def flag_hint(token: str) -> str:
    t = token.lower()
    if "deamidation" in t:
        return "Sequence scan reported asparagine deamidation–associated motifs; see liability counts and CDR advisories for position context."
    if "isomerization" in t:
        return "Sequence scan reported isomerization–sensitive motifs; advisory unless structure confirms exposure and process relevance."
    if "fv charge" in t or "charge asymmetry" in t:
        return "CMC advisor: VH/VL charge asymmetry outside reference band vs selected cohort; framework-only review recommended."
    if "germline" in t:
        return "Germline database miss or partial context; Vernier precompute may be unavailable."
    return "See §0–§5 for metric context."


def render_hpr_tcia_sequence_panel(data: Dict[str, Any]) -> str:
    """Clarify HPR + TCIA are sequence-based (always attempted); show errors if present."""
    hpr_err = data.get("hpr_error")
    tcia_err = data.get("tcia_error")
    hi = data.get("hpr_index") or {}
    vh_b = hi.get("vh") or {}
    vl_b = hi.get("vl") or {}
    cb = hi.get("combined") or {}
    rows_hpr = []
    if hpr_err:
        rows_hpr.append(f'<tr><td colspan="2" style="color:var(--fail);font-weight:600">HPR failed: {e(hpr_err)}</td></tr>')
    else:
        rows_hpr.append(
            f"<tr><td class=\"lbl\">HPR combined</td><td><strong>{e(fmt_val(cb.get('score')))}</strong> "
            f"({e(cb.get('found_9mers'))}/{e(cb.get('total_9mers'))} 9-mers matched)</td></tr>"
        )
        rows_hpr.append(
            f"<tr><td class=\"lbl\">HPR VH</td><td>{e(fmt_val(vh_b.get('score')))} "
            f"({e(vh_b.get('found_9mers'))}/{e(vh_b.get('total_9mers'))})</td></tr>"
        )
        rows_hpr.append(
            f"<tr><td class=\"lbl\">HPR VL</td><td>{e(fmt_val(vl_b.get('score')))} "
            f"({e(vl_b.get('found_9mers'))}/{e(vl_b.get('total_9mers'))})</td></tr>"
        )
    tcia_v = data.get("tcia_score")
    tcia_r = data.get("tcia_risk_level") or ""
    if tcia_err:
        rows_hpr.append(
            f'<tr><td colspan="2" style="color:var(--fail);font-weight:600">TCIA failed: {e(tcia_err)}</td></tr>'
        )
    else:
        rows_hpr.append(
            f"<tr><td class=\"lbl\">TCIA (sequence)</td><td><strong>{e(fmt_val(tcia_v))}</strong> "
            f"&middot; risk <strong>{e(tcia_r)}</strong> (MHCII analyzer, offline / no IEDB)</td></tr>"
        )
    abl = data.get("ablang_score")
    abl_e = data.get("ablang_error")
    if abl_e:
        rows_hpr.append(f'<tr><td class=\"lbl\">AbLang2 PLL</td><td style=\"color:var(--fail)\">{e(abl_e)}</td></tr>')
    elif abl is not None:
        rows_hpr.append(
            f'<tr><td class=\"lbl\">AbLang2 paired PLL</td><td>{e(fmt_val(abl))} <span class=\"interp\" style=\"font-size:.72rem\">(internal)</span></td></tr>'
        )
    return f"""
<div class="idx-banner">
  <h4>Sequence-computed indices (no Fv PDB required)</h4>
  <p class="idx-note">HPR Index, TCIA, and AbLang2 are evaluated from the VH/VL amino-acid sequences on every run. They do <strong>not</strong> require §2 in-silico Fv modeling. If a value shows “failed”, check conda env <code>anarcii</code> / local dependencies for <code>core.cmc.igg_hpr_ablang</code> and <code>MHCII_Analyzer</code>.</p>
  <table class="kv">{"".join(rows_hpr)}</table>
</div>
"""


def render_clinical_ada_section(rab: Dict[str, Any]) -> str:
    """Mirror console 'Clinical ADA Context' — label-linked historical rates, not predictions."""
    ada_ctx = rab.get("ada_context") or {}
    if not isinstance(ada_ctx, dict):
        return ""
    entries = ada_ctx.get("matched_clinical_entries") or []
    vh_g = ada_ctx.get("vh_germline") or "—"
    vl_g = ada_ctx.get("vl_germline") or "—"
    interp = ada_ctx.get("interpretation") or ""
    if not entries and vh_g == "—" and vl_g == "—":
        return ""

    rows = []
    for ent in entries:
        rows.append(
            "<tr>"
            f"<td>{e(ent.get('name'))}</td>"
            f"<td>{e(ent.get('match_type'))}</td>"
            f"<td><strong>{e(ent.get('ada_display'))}</strong></td>"
            f"<td>{e(ent.get('target'))}</td>"
            "</tr>"
        )
    table_body = "".join(rows) if rows else '<tr><td colspan="4" class="interp">No matched clinical entries.</td></tr>'
    return f"""
<div class="section">
  <h3>§5b — Clinical ADA context (label-level literature)</h3>
  <div class="section-body">
  <p class="interp" style="margin-bottom:10px;padding:10px 12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;color:#1e3a5f">
    <strong>Why this section exists:</strong> Approved-product ADA rates come from <strong>labels and trials</strong>, not from TCIA/HPR or developability gates.
    When the submitted Fv matches a sequence-backed drug record, the engine surfaces that drug’s <strong>reported ADA</strong> as a <strong>reference line</strong> — it does <strong>not</strong> re-predict patient ADA from physics metrics.
  </p>
  <p class="interp">Germline context used for literature linkage: VH <span class="mono">{e(vh_g)}</span> · VL <span class="mono">{e(vl_g)}</span></p>
  <table class="data-table" style="margin-top:10px">
    <tr><th>Clinical entry</th><th>Match</th><th>Reported ADA</th><th>Target</th></tr>
    {table_body}
  </table>
  <p class="interp" style="margin-top:12px">{e(interp)}</p>
  </div>
</div>
"""


def ada_summary_row_for_kv(rab: Dict[str, Any]) -> str:
    """One-line §0 summary when label-linked ADA rows exist."""
    ada_ctx = rab.get("ada_context") or {}
    entries = ada_ctx.get("matched_clinical_entries") or []
    if not entries:
        return ""
    bits = []
    for ent in entries[:4]:
        nm = ent.get("name") or "—"
        ad = ent.get("ada_display") or "—"
        bits.append(f"<strong>{e(nm)}</strong>: {e(ad)}")
    return (
        '<tr><td class="lbl">Label-linked ADA (trials / labels)</td><td>'
        + " · ".join(bits)
        + ' <span class="interp" style="font-size:.75rem">(see §5b — not predicted from TCIA)</span></td></tr>'
    )


def param_value_by_key(rab: Dict[str, Any], key: str) -> Any:
    for p in rab.get("parameters") or []:
        if p.get("key") == key:
            return p.get("value")
    return None


def render_param_cell(p: Dict[str, Any]) -> str:
    lab = p.get("label") or p.get("key") or "—"
    risk = p.get("risk") or "NOT_RUN"
    dc = risk_dot_class(risk)
    rc = risk_css_class(risk)
    nr = p.get("normal_range") or ""
    pr = p.get("preferred_range") or ""
    interp = (p.get("interpretation") or "")[:220]
    gate_ref = f"Preferred band: {pr}" if pr else ""
    val = fmt_val(p.get("value"))
    rk = risk if risk != "NOT_RUN" else "N/A"
    return f"""<div class="param-cell" title="{e(lab)}"><div class="param-title-row"><span class="param-dot {dc}"></span><span class="pn">{e(lab)}</span></div><div class="pv"><span class="pv-val">{e(val)}</span><span class="rk {rc}">{e(rk)}</span></div><div class="gate">Gate (intersection): {e(nr)}<div class="gate-ref">{e(gate_ref)}</div></div><div class="interp2">{e(interp)}</div></div>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--versions", type=Path, default=ROOT / "config" / "version_control.json")
    args = ap.parse_args()

    data = json.loads(args.snapshot.read_text(encoding="utf-8"))
    ver: Dict[str, Any] = {}
    if args.versions.exists():
        ver = json.loads(args.versions.read_text(encoding="utf-8"))

    rab = data.get("regular_ab_developability") or {}
    rc = rab.get("reference_context") or {}
    primary = rc.get("primary") or "—"
    stats_file = rc.get("primary_stats_file") or "—"
    params: List[Dict[str, Any]] = list(rab.get("parameters") or [])

    overall = data.get("overall_status") or rab.get("overall_gate_status") or "—"
    badge_class = "badge-warn"
    if str(overall).upper() == "FAIL":
        badge_class = "badge-fail"
    elif str(overall).upper() == "PASS":
        badge_class = "badge-ok"

    clinical = data.get("clinical_score")
    pct_txt = "—"
    if clinical is not None:
        try:
            pct_txt = f"Top {100 - round(float(clinical))}% of {primary.split(':')[0].strip()}"
        except (TypeError, ValueError):
            pct_txt = str(primary)

    dev_idx = rab.get("developability_index")
    if dev_idx is None:
        dev_idx = data.get("developability_index")

    hpr_c = ((data.get("hpr_index") or {}).get("combined") or {}).get("score")
    hpr_s = f"{float(hpr_c):.4f}" if hpr_c is not None else "—"

    tcia_v = data.get("tcia_score")
    tcia_r = data.get("tcia_risk_level") or ""
    tcia_line = f"{float(tcia_v):.4f} ({tcia_r})" if tcia_v is not None else "—"

    vh = data.get("vh_sequence") or ""
    vl = data.get("vl_sequence") or ""
    proj = data.get("project_name") or "project"

    fv = data.get("fv_structure") or {}

    inst_ix = data.get("instability_index")
    inst_class = "risk-low" if inst_ix is not None and float(inst_ix) <= 40 else "risk-mod"

    grid_html = "".join(render_param_cell(p) for p in params)

    sugg = rab.get("fr_modification_suggestions") or data.get("mutation_suggestions") or []
    eng_lines: List[str] = []
    if sugg:
        eng_lines.append('<table class="data-table"><tr><th>Target</th><th>Priority</th><th>Direction</th><th>Recommendation</th></tr>')
        for s in sugg:
            eng_lines.append(
                f"<tr><td>{e(s.get('target'))}</td><td>{e(s.get('priority'))}</td>"
                f"<td>{e(s.get('direction'))}</td><td>{e(s.get('recommendation'))}</td></tr>"
            )
        eng_lines.append("</table>")
    else:
        if str(overall).upper() == "PASS":
            eng_lines.append(
                f"<p class=\"interp\">No framework-region modification recommended — evaluated metrics are within "
                f"<strong>{e(primary)}</strong>.</p>"
            )
        else:
            eng_lines.append(
                "<p class=\"interp\">No automated FR substitution rows in this snapshot — see §5 FAIL/WARN tiles and §7 flags; "
                "re-run with Fv modeling for candidate site tables when available.</p>"
            )

    flags = data.get("overall_flags") or []
    flag_items = "".join(
        f"<li>{e(f)}<div class=\"flag-hint\">{e(flag_hint(str(f)))}</div></li>" for f in flags
    )

    cdr_w = rab.get("cdr_warnings") or []
    if cdr_w:
        eng_lines.append("<p class=\"interp\" style=\"margin-top:12px\"><strong>CDR advisories</strong> (do not modify without validation)</p><ul class=\"param-panel-bullets\">")
        for w in cdr_w:
            eng_lines.append(
                f"<li>Position <strong>{e(w.get('position'))}</strong>: {e(w.get('finding'))} — {e(w.get('action'))}</li>"
            )
        eng_lines.append("</ul>")

    seq_panel = render_hpr_tcia_sequence_panel(data)

    n_struct_nr = sum(1 for p in params if (p.get("risk") or "").upper() == "NOT_RUN")
    fv_modeled = bool((fv.get("pdb_url") or "").strip()) or fv.get("available") is True
    if n_struct_nr == 0 and fv_modeled:
        struct_msg = (
            "All structure-dependent metrics in this snapshot have values (Fv PDB was modeled and merged into the panel)."
        )
    elif n_struct_nr == 0 and not fv_modeled:
        struct_msg = (
            "No NOT_RUN tiles in this export (unusual if structure was skipped — verify JSON source)."
        )
    elif fv_modeled:
        struct_msg = (
            f"<strong>{n_struct_nr}</strong> tile(s) remain NOT_RUN even though an Fv model path is present — check "
            f"<code>compute_igg_structural_metrics</code> / merge step in the pipeline log."
        )
    else:
        struct_msg = (
            f"<strong>{n_struct_nr}</strong> structure-dependent tile(s) are NOT_RUN — re-run with "
            f"<code>run_structure=True</code> or console <code>predict_fv_structure: true</code> to fill PSH/PPC/PNC/SFVCSP, "
            f"VH/VL geometry, interface metrics, and Vernier SASA."
        )
    grid_readme = (
        f'<div class="grid-readme"><strong>How to read the 25 tiles:</strong> '
        f'<strong>HPR</strong> and <strong>TCIA</strong> are <em>not</em> repeated here — they appear in the blue box above (sequence-only). '
        f"{struct_msg}</div>"
    )

    gen_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    layout_tag = "igg-cmc-vhvl-parity-light-from-snapshot"

    ada_section = render_clinical_ada_section(rab)
    ada_kv = ada_summary_row_for_kv(rab)

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">
<title>InSynBio AbEngineCore | IgG CMC Report — {e(proj)}</title>
<style>
{CSS}
</style>
</head>
<body>
<!-- IgG CMC layout: vhvl-parity-light | generated by scripts/render_igg_cmc_snapshot_html.py -->
<div class="page">
<div class="cover">
  <h1>InSynBio AbEngineCore</h1>
  <div class="sub">IgG / VH+VL CMC Developability Report &nbsp;|&nbsp; CMC Standard v1.3</div>
  <div class="meta">
    <div class="header-meta">
      <div>Report layout: {e(layout_tag)}</div>
      <div>Build: {e(ver.get("build_id", "—"))}</div>
      <div>Analysis: {e(ver.get("analysis_version", "—"))}</div>
      <div>Protocol: {e(ver.get("protocol_version", "—"))}</div>
      <div>Report format: {e(ver.get("report_format_version", "—"))}</div>
      <div>AbEngineCore: {e(data.get("abenginecore_version", "—"))}</div>
      <div>CMC policy: {e(data.get("cmc_policy_version", "—"))}</div>
    </div>
    <span>Project: <strong>{e(proj)}</strong></span>
    <span>Status: <span class="badge {badge_class}">{e(overall)}</span></span>
    <span>Generated: {e(gen_ts)}</span>
    <span>CONFIDENTIAL</span>
  </div>
</div>

<div class="section">
  <h3>§0 — Run summary</h3>
  <div class="section-body">
  <table class="kv">
    <tr><td class="lbl">Overall status</td><td><span class="badge {badge_class}">{e(overall)}</span></td></tr>
    <tr><td class="lbl">Developability index / 100</td><td>{e(dev_idx)}</td></tr>
    <tr><td class="lbl">Reference composite (0–100)</td><td>{e(clinical)}</td></tr>
    <tr><td class="lbl">Percentile summary</td><td>{e(pct_txt)}</td></tr>
    <tr><td class="lbl">Reference standard</td><td>{e(primary)}</td></tr>
    <tr><td class="lbl">Frozen stats file</td><td>{e(stats_file)}</td></tr>
    <tr><td class="lbl">Antibody origin</td><td>{e(rab.get("antibody_origin"))}</td></tr>
    {ada_kv}
    <tr><td class="lbl">HPR Index (summary)</td><td>{e(hpr_s)} <span class="interp" style="font-size:.75rem">(see detailed breakdown below)</span></td></tr>
    <tr><td class="lbl">TCIA (summary)</td><td>{e(tcia_line)} <span class="interp" style="font-size:.75rem">(see below)</span></td></tr>
  </table>
  {seq_panel}
  </div>
</div>

<div class="section"><h3>§1 — Submitted VH / VL sequences</h3><div class="section-body"><p class="interp">1-letter amino acids as submitted for this run.</p><div class="seq-block"><div class="seq-label">VH <span class="seq-len">({len(vh)} aa)</span></div><div class="seq-body">{e(vh)}</div></div><div class="seq-block"><div class="seq-label">VL <span class="seq-len">({len(vl)} aa)</span></div><div class="seq-body">{e(vl)}</div></div></div></div>

<div class="section">
  <h3>§1b — IMGT segmentation (FR / CDR)</h3>
  <div class="section-body">
  <p class="interp">Regions from pipeline IMGT segmentation (same path as console / humanization tooling).</p>
  {imgt_tables(data.get("imgt_segmentation") or {})}
  </div>
</div>

<div class="section">
  <h3>§2 — In-silico Fv structure modeling</h3>
  <div class="section-body">
  {(
        "<p class=\"interp\">Confidence (pLDDT-equivalent): <strong>"
        + e(fv.get("plddt_eq"))
        + "</strong> &middot; VH–VL angle proxy: <strong>"
        + e(fv.get("vh_vl_angle_deg"))
        + "°</strong></p><p class=\"interp\"><strong>Model generated.</strong> PDB: <code>"
        + e(fv.get("pdb_filename") or fv.get("pdb_url") or "Fv_ABodyBuilder2.pdb")
        + "</code> (same folder as this HTML export when saved alongside the job).</p><p class=\"interp\">"
        + e(fv.get("note") or "")
        + "</p>"
    )
    if fv_modeled
    else "<p class=\"interp\"><strong>Not run.</strong> "
    + e(fv.get("note") or fv.get("error") or "Structure modeling skipped.")
    + "</p><p class=\"interp\">Structure-dependent tiles in §5 stay NOT_RUN until Fv modeling completes and merges.</p>"}
  </div>
</div>

<div class="section">
  <h3>§3 — Reference clinical benchmark</h3>
  <div class="section-body">
  <div class="score-row">
    <div><div class="score-val">{e(dev_idx)}</div><div class="score-lbl">Developability Index / 100</div></div>
    <div>
      <div class="score-val" style="font-size:1.75rem">{e(clinical)}</div>
      <div class="score-lbl">Reference composite index (0–100)</div>
      <div class="score-rank" style="margin-top:8px">{e(pct_txt)}</div>
      <div class="score-lbl" style="margin-top:2px">Percentile rank vs selected reference panel</div>
    </div>
  </div>
  </div>
</div>

<div class="section">
  <h3>§4 — Key physicochemical metrics</h3>
  <div class="section-body">
  <table class="data-table">
    <tr><th>Metric</th><th>Value</th><th>Threshold / Note</th></tr>
    <tr><td>pI (Fab)</td><td>{e(data.get("pI_fab"))}</td><td>4.5–9.5 preferred</td></tr>
    <tr><td>Instability Index</td><td class="{inst_class}">{e(inst_ix)}</td><td>&lt; 40 recommended (Guruprasad et al. 1990)</td></tr>
    <tr><td>GRAVY</td><td>{e(data.get("GRAVY"))}</td><td>&lt; −0.1 preferred</td></tr>
    <tr><td>Deamidation sites (cohort count)</td><td>{e(fmt_val(param_value_by_key(rab, "deamidation_sites")))}</td><td>from §5 gate context</td></tr>
    <tr><td>Oxidation sites (cohort count)</td><td>{e(fmt_val(param_value_by_key(rab, "oxidation_sites")))}</td><td></td></tr>
    <tr><td>Glycosylation sites (cohort count)</td><td>{e(fmt_val(param_value_by_key(rab, "glycosylation_sites")))}</td><td></td></tr>
  </table>
  </div>
</div>

<div class="section">
  <h3>§5 — Reference developability panel (25 tiles; 27 indicators)</h3>
  <div class="section-body">
  <p class="interp param-panel-intro">{e(rc.get("method_consistency_note") or "Values interpreted against frozen cohort distributions.")}</p>
  <ul class="param-panel-bullets"><li>{e(primary)} — primary gate file: <code>{e(stats_file)}</code></li></ul>
  <p class="param-grid-hint">3-column tile grid (25 developability metrics). <strong>27 indicators</strong> = these 25 + §0 <strong>HPR Index</strong> + <strong>TCIA</strong>.</p>
  {grid_readme}
  <div class="param-grid">{grid_html}</div>
  </div>
</div>

{ada_section}

<div class="section">
  <h3>§6 — Engineering actions &amp; optimization suggestions</h3>
  <div class="section-body">
  <p class="interp">Framework-only policy; CDR liabilities remain advisory unless a redesign project is approved.</p>
  {"".join(eng_lines)}
  </div>
</div>

<div class="section">
  <h3>§7 — CMC flags</h3>
  <div class="section-body">
  <ul class="flag-list">{flag_items}</ul>
  <p class="interp" style="margin-top:12px">
    Each line is a compact pipeline token; expanded interpretation appears in Sections 0–6 (including §5b label ADA context when present).
  </p>
  </div>
</div>

<div class="section">
  <h3>§8 — Optimization roadmap</h3>
  <div class="section-body">
  <ul class="param-panel-bullets">
    <li><strong>Fv modeling:</strong> Re-run <code>POST /cmc/igg</code> with <code>predict_fv_structure: true</code> to populate structure-dependent tiles and SASA-filtered FR hints.</li>
    <li><strong>Charge asymmetry:</strong> Address VH/VL charge asymmetry with conservative FR substitutions only; pair with binding/PK studies for engineering variants.</li>
    <li><strong>CDR advisories:</strong> Treat CDR scan findings as advisory; clinical antibodies often retain CDR liabilities essential for antigen recognition.</li>
  </ul>
  <p class="interp">Action sequencing is FR-first and evidence-driven; maintain uniform report format across runs.</p>
  </div>
</div>

<footer>InSynBio Research &nbsp;·&nbsp; {e(gen_ts)} &nbsp;·&nbsp; CONFIDENTIAL &nbsp;·&nbsp; Use Ctrl+P → Save as PDF to export.</footer>
</div>
</body>
</html>
"""

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html_out, encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
