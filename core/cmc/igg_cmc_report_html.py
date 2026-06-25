"""IgG CMC HTML report generator — API and offline batch."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]


def _fmt(v: Any, suffix: str = "", decimals: int = 2) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return str(v)


_IGG_CMC_HTML_CSS = """
<style>
:root{--ok:#059669;--warn:#d97706;--fail:#dc2626;--muted:#6b7280;--bg:#f9fafb;
     --card:#fff;--border:#d0d7e2;--accent:#1b4fad;--accent2:#2d6cdf}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:#f4f7f9;color:#2c3e50;font-size:13px;line-height:1.5;padding:20px}
.page{max-width:900px;margin:0 auto;background:#fff;padding:32px 40px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.05)}
.report-header{background:var(--accent);color:#fff;padding:20px 28px;border-radius:8px;margin-bottom:18px;display:flex;justify-content:space-between;align-items:flex-end}
.report-header h1{font-size:1.35rem;font-weight:700;margin:0 0 4px;color:#fff;letter-spacing:-.02em}
.report-header .sub{font-size:.84rem;font-weight:600;opacity:.95;line-height:1.45;color:#fff}
.report-header .ts{font-size:.78rem;font-weight:600;opacity:.92;text-align:right}
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
.cdr-box{margin-top:14px;padding:10px 14px;background:#fffbeb;border:1px solid #fcd34d;border-radius:6px}
footer{text-align:center;color:var(--muted);font-size:0.75rem;margin-top:24px;padding-top:12px;border-top:1px solid var(--border)}
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
.muted{color:var(--muted);font-style:italic}
@media print{
  body{background:#fff;font-size:10.5px;color:#000;padding:0}
  .page{max-width:100%;padding:0;box-shadow:none}
  .report-header{background:#1b4fad!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .report-header h1,.report-header .sub,.report-header .ts,.report-header .header-meta{color:#fff!important;opacity:1}
  /* Permit section pagination to reduce trailing blank space in PDF pages. */
  .section{break-inside:auto;page-break-inside:auto;margin-bottom:10px}
  .section h3{break-after:avoid;page-break-after:avoid}
  .param-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
}
</style>
"""


def _sanitize_cohort_display_label(text: Optional[str]) -> str:
    """Remove cohort enumeration counts from user-visible labels (paths/strings); JSON payloads unchanged."""
    if text is None:
        return ""
    t = str(text)
    t = re.sub(r"(?i)\bNatural Baseline\b", "Natural", t)
    t = re.sub(r"(?i)\bNat-384\b", "Natural cohort", t)
    t = re.sub(r"(?i)\bNatural384\b", "Natural", t)
    t = re.sub(r"(?i)\bEng-458\b", "Engineered clinical", t)
    t = re.sub(r"(?i)\bClinical Reference Cohort\b", "AbRef clinical", t)
    t = re.sub(r"(?i)\(\s*n\s*=\s*\d+\s*\)", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t


def _risk_class(risk: str) -> str:
    r = (risk or "").upper()
    if r == "LOW":
        return "risk-low"
    if r == "MODERATE":
        return "risk-mod"
    if r == "HIGH":
        return "risk-high"
    return ""


def _ref_pos_label(pos: str) -> str:
    MAP = {
        "central_reference_band":  "p25–p75 (core)",
        "outer_reference_band":    "p5–p95 (broad)",
        "outside_reference_band":  "Outside p5–p95",
        "favorable_to_typical":    "≤ p75 (favorable)",
        "upper_reference_band":    "p75–p95 (elevated)",
        "split_cohort_dual_band":  "Dual cohort (Nat vs Eng)",
        "not_available":           "—",
        "no_reference":            "—",
        "incomplete_reference":    "—",
    }
    return MAP.get(pos, (pos or "—").replace("_", " "))


def _html_sequence_candidates_block(sc: Any, esc) -> str:
    """Render FR K/R sites and hydrophobic runs from sequence_candidates dict."""
    if not isinstance(sc, dict) or not sc:
        return ""
    inner_parts: List[str] = []
    note = sc.get("enumeration_note")
    if note:
        inner_parts.append(f"<p style='font-size:.72rem;color:#64748b;margin:0 0 6px 0'>{esc(note)}</p>")
    policy = sc.get("mutation_policy") or {}
    if isinstance(policy, dict) and policy.get("public_summary"):
        inner_parts.append(
            f"<p style='font-size:.72rem;color:#64748b;margin:0 0 6px 0'>{esc(policy.get('public_summary'))}</p>"
        )
    sites = sc.get("fr_positive_charge_sites") or []
    if sites:
        rows = "".join(
            f"<tr><td>{esc(x.get('chain'))}</td><td>{esc(x.get('index_1'))}</td><td>{esc(x.get('imgt'))}</td>"
            f"<td>{esc(x.get('from_aa'))}→{esc(x.get('to_aa_hint'))} ({esc(x.get('region'))})</td>"
            f"<td>{esc(x.get('surface_class', 'FR surface'))}</td>"
            f"<td>{esc(x.get('selection_basis', 'non-critical FR candidate'))}</td></tr>"
            for x in sites
        )
        inner_parts.append(
            "<div style='font-size:.78rem;font-weight:600;margin:6px 0 4px 0'>FR K/R candidate sites (charge tuning)</div>"
            f"<table style='font-size:.75rem'><tr><th>Chain</th><th>Pos</th><th>IMGT</th><th>Suggested</th><th>Surface class</th><th>Selection basis</th></tr>{rows}</table>"
        )
    neg_sites = sc.get("fr_negative_charge_sites") or []
    if neg_sites:
        nrows = "".join(
            f"<tr><td>{esc(x.get('chain'))}</td><td>{esc(x.get('index_1'))}</td><td>{esc(x.get('imgt'))}</td>"
            f"<td>{esc(x.get('from_aa'))}→{esc(x.get('to_aa_hint'))} ({esc(x.get('region'))})</td>"
            f"<td>{esc(x.get('surface_class', 'FR surface'))}</td>"
            f"<td>{esc(x.get('selection_basis', 'non-critical FR candidate'))}</td></tr>"
            for x in neg_sites
        )
        inner_parts.append(
            "<div style='font-size:.78rem;font-weight:600;margin:8px 0 4px 0'>FR D/E candidate sites (reduce negative patch)</div>"
            f"<table style='font-size:.75rem'><tr><th>Chain</th><th>Pos</th><th>IMGT</th><th>Suggested</th><th>Surface class</th><th>Selection basis</th></tr>{nrows}</table>"
        )
    runs = sc.get("fr_hydrophobic_runs") or []
    if runs:
        rrows = ""
        for x in runs:
            rrows += (
                f"<tr style='background:rgba(201,162,39,.06)'>"
                f"<td>{esc(x.get('chain'))}</td><td>{esc(x.get('start_1'))}–{esc(x.get('end_1'))}</td>"
                f"<td style='font-family:monospace;font-weight:600'>{esc(x.get('segment'))}</td>"
                f"<td style='font-family:monospace;font-size:.72rem'>{esc(x.get('window'))}</td>"
                f"<td>{esc(x.get('selection_basis', 'surface-exposed FR hydrophobic patch'))}</td></tr>"
            )
            pr = x.get("per_residue") or []
            if pr:
                def _hint_span(p: Any) -> str:
                    caution_title = esc(p.get("caution", ""))
                    caution_part = (
                        f" <span style='color:#c9a227' title='{caution_title}'>&#9888;</span>"
                        if p.get("caution") else ""
                    )
                    return (
                        f"<span style='font-family:monospace'>"
                        f"{esc(p.get('index_1'))} {esc(p.get('from_aa'))}&#8594;{esc(p.get('to_aa_hint'))}"
                        f"<sub style='color:#64748b'>{esc(p.get('region',''))}</sub>"
                        f"{caution_part}</span>"
                    )
                hints = " &nbsp; ".join(_hint_span(p) for p in pr)
                rrows += (
                    f"<tr><td colspan='5' style='padding-top:0;padding-bottom:8px;font-size:.72rem;color:#64748b'>"
                    f"&nbsp;&nbsp;Per-residue hints: {hints}</td></tr>"
                )
        inner_parts.append(
            "<div style='font-size:.78rem;font-weight:600;margin:8px 0 4px 0'>FR hydrophobic runs — specific mutation sites</div>"
            f"<table style='font-size:.75rem'><tr><th>Chain</th><th>Span</th><th>Segment</th><th>Context</th><th>Selection basis</th></tr>{rrows}</table>"
        )
    if not inner_parts:
        return ""
    return (
        "<tr><td colspan='5' style='padding-top:0;padding-bottom:12px;border-bottom:1px solid #e5e7eb'>"
        "<div style='padding:10px;background:#eff6ff;border-radius:6px;border:1px solid #bfdbfe'>"
        + "".join(inner_parts)
        + "</div></td></tr>"
    )


def _generate_igg_cmc_html(data: dict, out: Path) -> "Optional[Path]":
    """Generate a self-contained HTML CMC report for IgG / VH+VL."""
    from datetime import datetime
    import html as _html

    def esc(v: Any) -> str:
        return _html.escape(str(v)) if v is not None else "—"

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    vjson: Dict[str, Any] = {}
    try:
        vjson = json.loads((ROOT / "config" / "version_control.json").read_text(encoding="utf-8"))
    except Exception:
        vjson = {}
    bid = esc(str(vjson.get("build_id") or "—"))
    analysis_ver = esc(str(vjson.get("analysis_version") or "—"))
    protocol_ver = esc(str(vjson.get("protocol_version") or "—"))
    rf_ver = esc(str(vjson.get("report_format_version") or "—"))
    from api.report_versioning import suite_service_meta_html, cohort_provenance_html

    igg_header_inner = suite_service_meta_html(
        "cmc_igg",
        protocol_ver=str(vjson.get("protocol_version") or "—"),
        analysis_ver=str(vjson.get("analysis_version") or "—"),
        extra_inner_divs=[
            "<div>Report layout shell: igG-cmc-vhvl-parity-20260501-v2</div>",
        ],
    )
    cohort_block_html = cohort_provenance_html("cmc_igg")
    proj = esc(data.get("project_name") or "—")
    status = str(data.get("overall_status") or "DONE").upper()
    status_badge = "badge-ok" if status in ("PASS", "OK") else ("badge-fail" if status == "FAIL" else "badge-warn")
    dev_index = data.get("developability_index")
    abref_raw = data.get("abref_percentile")
    if abref_raw is None:
        abref_raw = data.get("clinical_score")
    abref_f: Optional[float] = None
    try:
        if abref_raw is not None:
            abref_f = round(float(abref_raw), 1)
    except (TypeError, ValueError):
        abref_f = None

    rb = data.get("regular_ab_developability") or {}
    ref_ctx_rb = rb.get("reference_context") or {}
    ref_primary = ref_ctx_rb.get("primary") or "matched reference"
    ref_primary_disp = _sanitize_cohort_display_label(ref_primary)
    ref_short = str(ref_primary_disp).split(":")[0].strip()
    rank_label = f"Top {100 - round(abref_f)}% of {esc(ref_short)}" if abref_f is not None else "—"
    abref_index_str = f"{abref_f:.1f}" if abref_f is not None else "—"
    dev_str = f"{float(dev_index):.1f}" if dev_index is not None else "—"
    pI_str = _fmt(data.get("pI_fab"), decimals=2)
    inst_str = _fmt(data.get("instability_index"), decimals=1)
    gravy_str = _fmt(data.get("GRAVY"), decimals=3)
    inst_warn = (data.get("instability_index") or 0) > 40

    tcia_v = data.get("tcia_score")
    tcia_risk = data.get("tcia_risk_level")
    tcia_str = f"{float(tcia_v):.4f}" if tcia_v is not None else "—"
    tcia_disp = (
        f"{tcia_str} &nbsp;<span class=\"interp\" style=\"font-size:.75rem\">({esc(str(tcia_risk))})</span>"
        if tcia_v is not None and tcia_risk
        else tcia_str
    )
    tcia_err_line = data.get("tcia_error")

    # p-AbNatiV2 (V1.8)
    pab = data.get("p_abnativ2") or {}
    pab_likelihood = pab.get("pairing_likelihood")
    pab_humanness = pab.get("paired_humanness")
    pab_err = pab.get("error")
    pab_warn = pab.get("warning")
    pab_likelihood_str = f"{float(pab_likelihood):.4f}" if pab_likelihood is not None else "—"
    pab_humanness_str = f"{float(pab_humanness):.4f}" if pab_humanness is not None else "—"

    hpr_obj = data.get("hpr_index") if isinstance(data.get("hpr_index"), dict) else {}
    hpr_comb = (hpr_obj.get("combined") or {}) if hpr_obj else {}
    hpr_score = hpr_comb.get("score")
    hpr_str = f"{float(hpr_score):.4f}" if hpr_score is not None else "—"
    hpr_err_line = data.get("hpr_error") or hpr_obj.get("error")
    humanness_note = ""
    pab_warn_line = ""
    if pab_warn:
        pab_warn_line = (
            f'<p class="interp" style="margin-top:6px;font-size:.78rem;color:#475569">'
            f"p-AbNatiV2 note: {esc(str(pab_warn))}</p>"
        )
    if hpr_err_line or tcia_err_line or pab_err:
        bits = []
        if tcia_err_line:
            bits.append(f"TCIA: {esc(str(tcia_err_line))}")
        if hpr_err_line:
            bits.append(f"HPR Index: {esc(hpr_err_line)}")
        if pab_err:
            bits.append(f"p-AbNatiV2: {esc(pab_err)}")
        humanness_note = f'<p class="interp" style="margin-top:8px;font-size:.78rem;color:#64748b">Sequence immunogenicity / humanness metrics not fully computed — {"; ".join(bits)}</p>'
    stats_file_line = ref_ctx_rb.get("primary_stats_file") or ""
    stats_file_disp = _sanitize_cohort_display_label(stats_file_line)
    params = [p for p in (rb.get("parameters") or []) if p]
    skip_params = [p for p in params if p.get("risk") == "NOT_RUN"]

    def _normal_range_cell(p: dict) -> str:
        bits: List[str] = []
        if p.get("normal_range"):
            bits.append(f"Gate (intersection): {p['normal_range']}")
        if p.get("normal_range_note"):
            bits.append(str(p.get("normal_range_note")))
        if p.get("natural384_normal_range"):
            bits.append(f"Natural cohort p5–p95: {p['natural384_normal_range']}")
        if p.get("engineered458_normal_range"):
            bits.append(f"Engineered clinical cohort p5–p95: {p['engineered458_normal_range']}")
        if not bits:
            bits.append("—")
        return "<br/>".join(esc(b) for b in bits)

    def _param_dot(risk_raw: str) -> str:
        r = (risk_raw or "").upper()
        if r == "LOW":
            return "low"
        if r == "MODERATE":
            return "mod"
        if r == "HIGH":
            return "high"
        return "na"

    param_grid_cells: List[str] = []
    for p in params:
        lbl = str(p.get("label") or p.get("key") or "—")
        lbl_short = lbl.replace(" (Fv)", "").replace(" index", "")
        risk_u = (p.get("risk") or "NOT_RUN").upper()
        is_na = risk_u == "NOT_RUN"
        risk_show = "N/A" if is_na else risk_u
        val_raw = p.get("value")
        val_str = "—" if val_raw is None or val_raw == "" else str(val_raw)
        interp = str(p.get("interpretation") or "")
        interp_short = (interp[:140] + "…") if len(interp) > 140 else interp
        gate_inner = _normal_range_cell(p)
        dot = _param_dot(p.get("risk", ""))
        ref_raw = _ref_pos_label(p.get("reference_position", ""))
        ref_suffix = ""
        if ref_raw and ref_raw != "—":
            ref_suffix = f'<div class="gate-ref">Reference band: {esc(ref_raw)}</div>'
        param_grid_cells.append(
            f'<div class="param-cell" title="{esc(lbl)}">'
            f'<div class="param-title-row"><span class="param-dot {dot}"></span>'
            f'<span class="pn">{esc(lbl_short)}</span></div>'
            f'<div class="pv"><span class="pv-val">{esc(val_str)}</span>'
            f'<span class="rk {_risk_class(risk_u) if not is_na else ""}">{esc(risk_show)}</span></div>'
            f'<div class="gate">{gate_inner}{ref_suffix}</div>'
            + (f'<div class="interp2">{esc(interp_short)}</div>' if interp_short else "")
            + "</div>"
        )
    param_grid_html = (
        f'<div class="param-grid">{"".join(param_grid_cells)}</div>'
        if param_grid_cells
        else "<p class='interp'>Parameters not available in this run.</p>"
    )
    skip_note = (
        f"<p class='interp' style='margin-top:8px'>"
        f"ⓘ {len(skip_params)} structure-dependent parameter(s) not evaluated in sequence-only mode "
        f"({', '.join(esc(p.get('label') or p.get('key','?')) for p in skip_params)}).</p>"
        if skip_params else ""
    )

    method_note = (ref_ctx_rb.get("method_consistency_note") or "").strip()
    if not method_note:
        method_note = (
            "All reported values are interpreted only against reference distributions generated "
            "with the same internal calculation protocol. Cross-method thresholds are not mixed."
        )
    panel_bullets: List[str] = []
    for n in rb.get("source_specific_notes") or []:
        if isinstance(n, dict):
            t = str(n.get("text") or "").strip()
        else:
            t = str(n).strip()
        if t:
            panel_bullets.append(f"<li>{esc(t)}</li>")
    panel_bullets.append(
        "<li>Fully human regular antibodies are reviewed for naturalness and clinical drug-space compatibility.</li>"
    )
    param_panel_intro_html = (
        f'<p class="interp param-panel-intro">{esc(method_note)}</p>'
        f'<ul class="param-panel-bullets">{"".join(panel_bullets)}</ul>'
    )

    flags = data.get("overall_flags") or []

    def _cmc_flag_item(token: str) -> str:
        low = str(token).strip().lower()
        hints = {
            "cdr_scan:warn:deamidation": (
                "Sequence scan reported asparagine deamidation–associated motifs; see liability counts in "
                "the run summary and any CDR advisories in Section 6 for position context."
            ),
            "cdr_scan:warn:isomerization": (
                "Sequence scan reported isomerization–sensitive motifs; treat as advisory unless "
                "structure confirms solvent exposure and process relevance."
            ),
            "cdr_scan:warn:oxidation": (
                "Sequence scan reported methionine/cysteine oxidation–sensitive motifs; confirm in structural context."
            ),
        }
        hint = hints.get(low, "")
        if hint:
            return f"<li>{esc(token)}<div class='flag-hint'>{esc(hint)}</div></li>"
        return f"<li>{esc(token)}</li>"

    flags_html = "".join(_cmc_flag_item(f) for f in flags) if flags else "<li>No CMC flags returned.</li>"

    # Engineering Actions: FR suggestions + CDR warnings
    fr_suggs = rb.get("fr_modification_suggestions") or data.get("mutation_suggestions") or []
    cdr_warns = rb.get("cdr_warnings") or []
    if fr_suggs:
        fr_rows = ""
        for s in fr_suggs:
            prio = str(s.get("priority", "")).upper()
            badge_kind = "badge-fail" if prio == "HIGH" else "badge-warn"
            cur_val = s.get("current_value", "")
            tgt = s.get("target_range", "")
            rat = s.get("rationale", "")
            val_cell = f"{esc(cur_val)}" + (f" → target {esc(tgt)}" if tgt else "")
            if not str(val_cell).strip():
                val_cell = (
                    "<span class='interp'>No numeric current/target pair was emitted for this row — "
                    "often a qualitative liability flag without an automated FR substitution shortlist. "
                    "Cross-check HIGH / MODERATE rows in the developability tile panel (§5) above and any CDR advisories below.</span>"
                )
            note_cell = (f"<br><span style='font-size:.72rem;color:#64748b'>{esc(rat)}</span>" if rat else "")
            fr_rows += (
                f"<tr>"
                f"<td>{esc(s.get('scope','FR-only'))}</td>"
                f"<td>{esc(s.get('target','—'))}</td>"
                f"<td>{val_cell}</td>"
                f"<td><span class='badge {badge_kind}'>{esc(prio or '—')}</span></td>"
                f"<td>{esc(s.get('recommendation','—'))}{note_cell}</td>"
                f"</tr>"
            )
            sc = s.get("sequence_candidates")
            if sc:
                fr_rows += _html_sequence_candidates_block(sc, esc)
        cdr_html = ""
        if cdr_warns:
            cdr_items = "".join(
                f"<li>Position <strong>{esc(w.get('position','?'))}</strong>: "
                f"{esc(w.get('finding','?'))} — {esc(w.get('action','advisory only'))}</li>"
                for w in cdr_warns
            )
            cdr_html = f"""
<div class="cdr-box">
  <strong style="font-size:.82rem;color:var(--warn)">CDR Advisory Warnings (do not modify without structural validation)</strong>
  <ul style="margin:6px 0 0 16px;font-size:.8rem;line-height:1.8">{cdr_items}</ul>
</div>"""
        engineering_html = f"""
<div class="section">
  <h3>§6 — Engineering actions &amp; optimization suggestions</h3>
  <div class="section-body">
  <p class="interp" style="margin-bottom:10px">
    <strong>FR-only</strong> = framework regions only (CDRs are not targets for automated substitution lists).
    Prioritize non-critical, surface-exposed framework positions to improve charge balance, hydrophobic profile,
    and stability while preserving CDR binding regions.
    CDR findings below are <em>advisory</em> and require structure-based validation before any change.
  </p>
  <table class="data-table">
    <tr><th>Scope</th><th>Target metric</th><th>Current → Target range</th><th>Priority</th><th>Recommended action</th></tr>
    {fr_rows}
  </table>
  {cdr_html}
  </div>
</div>"""
    else:
        _refp = esc(ref_primary_disp)
        engineering_html = f"""
<div class="section">
  <h3>§6 — Engineering actions &amp; optimization suggestions</h3>
  <div class="section-body">
  <p class="interp">No framework-region modification recommended — evaluated metrics are within the selected reference standard ({_refp}).</p>
  </div>
</div>"""

    roadmap_points: List[str] = []
    if fr_suggs:
        roadmap_points.append(
            "Position Selection: Target non-critical, surface-exposed framework (FR) positions. Strictly avoid CDRs, Vernier zone residues, and positions within 5 Å of the CDR loops or VH/VL interface."
        )
        roadmap_points.append(
            "Mutation Rules: Apply distinct strategies based on surface properties. Use conservative substitutions at exposed hydrophobic patches to reduce aggregation risk, and utilize polar/charged surfaces for pI and net-charge tuning."
        )
    if cdr_warns:
        roadmap_points.append(
            "CDR Advisories: Treat all CDR liabilities as strictly advisory. Many highly successful clinical antibodies contain sequence liabilities within CDRs that are essential for antigen binding; modifications require explicit structural and functional validation."
        )
    if not roadmap_points:
        roadmap_points.append(
            "No immediate FR optimization action required under the current reference standard."
        )
    roadmap_html = "".join(f"<li>{esc(p)}</li>" for p in roadmap_points)

    vh_in = data.get("vh_sequence") or ""
    vl_in = data.get("vl_sequence") or ""
    seq_block = ""
    if vh_in or vl_in:
        seq_block = (
            '<div class="section"><h3>§1 — Submitted VH / VL sequences</h3><div class="section-body">'
            '<p class="interp">1-letter amino acids as submitted for this run.</p>'
            f'<div class="seq-block"><div class="seq-label">VH <span class="seq-len">({len(str(vh_in))} aa)</span></div>'
            f'<div class="seq-body">{esc(vh_in) if vh_in else "—"}</div></div>'
            f'<div class="seq-block"><div class="seq-label">VL <span class="seq-len">({len(str(vl_in))} aa)</span></div>'
            f'<div class="seq-body">{esc(vl_in) if vl_in else "—"}</div></div>'
            "</div></div>"
        )

    seg_html = ""
    _seg = data.get("imgt_segmentation") if isinstance(data.get("imgt_segmentation"), dict) else {}
    if _seg and (_seg.get("VH") or _seg.get("VL")):

        def _seg_table(chain: str) -> str:
            d = _seg.get(chain) or {}
            if not isinstance(d, dict):
                return ""
            order = ("FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4")
            rows = []
            for nm in order:
                s = str(d.get(nm, "") or "")
                rows.append(
                    "<tr>"
                    f"<td>{esc(nm)}</td>"
                    f"<td>{len(s)}</td>"
                    f"<td style=\"font-family:ui-monospace,monospace;font-size:.72rem;word-break:break-all\">{esc(s)}</td>"
                    "</tr>"
                )
            return (
                f'<div style="margin-top:12px"><strong>{esc(chain)}</strong> (IMGT)</div>'
                '<table class="data-table" style="margin-top:6px">'
                "<tr><th>Region</th><th>Len</th><th>Sequence</th></tr>"
                + "".join(rows)
                + "</table>"
            )

        seg_err = _seg.get("error")
        seg_note = f'<p class="interp" style="color:var(--warn)">{esc(seg_err)}</p>' if seg_err else ""
        seg_html = (
            '<div class="section"><h3>§1b — IMGT segmentation (FR / CDR)</h3><div class="section-body">'
            '<p class="interp">Regions from ANARCII IMGT numbering + pipeline FR/CDR boundaries '
            "(same path as humanization/VHH tooling).</p>"
            f"{seg_note}"
            f'{_seg_table("VH")}{_seg_table("VL")}'
            "</div></div>"
        )

    fv = data.get("fv_structure") or {}
    fv_block = ""
    if isinstance(fv, dict) and fv.get("pdb_url"):
        fv_block = f"""
<div class="section">
  <h3>§2 — In-silico Fv structure modeling</h3>
  <div class="section-body">
  <p class="interp">
    Confidence (pLDDT-equivalent): <strong>{esc(fv.get("plddt_eq"))}</strong>
    &nbsp;&middot;&nbsp; VH–VL angle proxy: <strong>{esc(fv.get("vh_vl_angle_deg"))}</strong>°
  </p>
  <p class="interp">{esc(fv.get("note", ""))}</p>
  <p style="font-size:.78rem;margin-top:6px">
    <a href="Fv_ABodyBuilder2.pdb" download style="color:var(--accent)">Download Fv model (PDB)</a>
    (same folder as this report)
  </p>
  </div>
</div>"""
    elif isinstance(fv, dict) and (fv.get("error") or fv.get("available") is False):
        fv_block = f"""
<div class="section">
  <h3>§2 — In-silico Fv structure modeling</h3>
  <div class="section-body">
  <p class="interp" style="color:var(--warn)">Not available: {esc(fv.get("error", "—"))}</p>
  <p class="interp">{esc(fv.get("note", ""))}</p>
  </div>
</div>"""

    origin_line = esc(rb.get("antibody_origin") or "—")
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">
<title>InSynBio AbEngineCore | IgG CMC Report — {proj}</title>
{_IGG_CMC_HTML_CSS}
</head>
<body>
<!-- IgG CMC layout: vhvl-parity-light-20260501-v2 param-panel | if missing = stale cache or old API -->
<div class="page">
<div class="report-header">
  <div>
  <h1>InSynBio AbEngineCore</h1>
  <div class="sub">IgG / VH+VL CMC Developability Report &nbsp;|&nbsp; CMC Standard v1.3</div>
  <div class="sub" style="margin-top:4px">Project: <b>{proj}</b> &nbsp;·&nbsp; Status: <span class="badge {status_badge}">{esc(status)}</span></div>
      {igg_header_inner}
      {cohort_block_html}
  </div>
  <div class="ts">{ts}<br><span style="font-size:.7rem;opacity:.6">CONFIDENTIAL</span></div>
</div>

<div class="section">
  <h3>§0 — Run summary</h3>
  <div class="section-body">
  <table class="kv">
    <tr><td class="lbl">Overall status</td><td><span class="badge {status_badge}">{esc(status)}</span></td></tr>
    <tr><td class="lbl">Developability index / 100</td><td>{dev_str}</td></tr>
    <tr><td class="lbl">Reference composite (0–100)</td><td>{abref_index_str}</td></tr>
    <tr><td class="lbl">Percentile summary</td><td>{rank_label}</td></tr>
    <tr><td class="lbl">Reference standard</td><td>{esc(ref_primary_disp)}</td></tr>
    <tr><td class="lbl">Frozen stats file</td><td>{esc(stats_file_disp or "—")}</td></tr>
    <tr><td class="lbl">Antibody origin</td><td>{origin_line}</td></tr>
    <tr><td class="lbl">HPR Index</td><td>{hpr_str} <span class="interp" style="font-size:.75rem">(variable-region human peptide repertoire compatibility)</span></td></tr>
    <tr><td class="lbl">p-AbNatiV2 Likelihood</td><td>{pab_likelihood_str} <span class="interp" style="font-size:.75rem">(VH/VL pairing likelihood proxy)</span></td></tr>
    <tr><td class="lbl">p-AbNatiV2 Humanness</td><td>{pab_humanness_str} <span class="interp" style="font-size:.75rem">(paired variable-region naturalness)</span></td></tr>
    <tr><td class="lbl">TCIA (sequence)</td><td>{tcia_disp} <span class="interp" style="font-size:.75rem">(MHC-II T-cell immunogenicity index, 0–1)</span></td></tr>
  </table>
  {humanness_note}
  {pab_warn_line}
  </div>
</div>

{seq_block}
{seg_html}
{fv_block}

<div class="section">
  <h3>§3 — Reference clinical benchmark</h3>
  <div class="section-body">
  <div class="score-row">
    <div><div class="score-val">{dev_str}</div><div class="score-lbl">Developability Index / 100</div></div>
    <div>
      <div class="score-val" style="font-size:1.75rem">{abref_index_str}</div>
      <div class="score-lbl">Reference composite index (0–100)</div>
      <div class="score-rank" style="margin-top:8px">{rank_label}</div>
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
    <tr><td>pI (Fab)</td><td>{pI_str}</td><td>4.5–9.5 preferred</td></tr>
    <tr><td>Instability Index</td><td class="{'risk-high' if inst_warn else 'risk-low'}">{inst_str}</td><td>&lt; 40 recommended (Guruprasad et al. 1990)</td></tr>
    <tr><td>GRAVY</td><td>{gravy_str}</td><td>&lt; −0.1 preferred</td></tr>
    <tr><td>Deamidation sites (NG / NS / NN motifs)</td><td>{esc(data.get('n_deamidation'))}</td><td>0 preferred in CDR; FR ≤ 2 acceptable</td></tr>
    <tr><td>Oxidation sites (Met, Trp)</td><td>{esc(data.get('n_oxidation'))}</td><td>0 preferred in CDR; FR ≤ 2 acceptable</td></tr>
    <tr><td>Glycosylation sites (N-X-S/T)</td><td>{esc(data.get('n_glycosylation'))}</td><td>0 in V-domain; Fc N297 retained</td></tr>
  </table>
  </div>
</div>

<div class="section">
  <h3>§5 — Reference developability panel (25 tiles; 27 indicators)</h3>
  <div class="section-body">
  {param_panel_intro_html}
  <p class="param-grid-hint">3-column tile grid (25 developability metrics in this section). <strong>29 indicators</strong> = these 25 + §0 <strong>HPR Index</strong> + <strong>TCIA</strong> + <strong>p-AbNatiV2 (Pairing & Humanness)</strong>. AbLang2 PLL may remain in internal JSON, but is not used as a visible CMC / humanness headline metric.</p>
  {param_grid_html}
  {skip_note}
  </div>
</div>

{engineering_html}

<div class="section">
  <h3>§7 — CMC flags</h3>
  <div class="section-body">
  <ul class="flag-list">{flags_html}</ul>
  <p class="interp" style="margin-top:12px">
    Each line is a compact pipeline token; expanded interpretation appears in Sections 0–6 (metrics, panel, and engineering table).
    Detailed action prioritization is summarized in Section 8.
  </p>
  </div>
</div>

<div class="section">
  <h3>§8 — Optimization roadmap</h3>
  <div class="section-body">
  <ul class="param-panel-bullets">{roadmap_html}</ul>
  <p class="interp">Action sequencing is FR-first and evidence-driven; maintain uniform report format across runs.</p>
  </div>
</div>

<footer>InSynBio Research &nbsp;·&nbsp; {ts} &nbsp;·&nbsp; CONFIDENTIAL &nbsp;·&nbsp; Use Ctrl+P → Save as PDF to export.</footer>
</div>
</body>
</html>"""

    report_dir = out / "reports" / "cmc_igg"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "CMC_Report.html"
    path.write_text(html, encoding="utf-8")
    return path
