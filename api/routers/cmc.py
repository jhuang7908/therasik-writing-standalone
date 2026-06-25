"""
api/routers/cmc.py
 CMC ：
  POST /cmc/igg      —— IgG / VH+VL (vs Clinical Reference Cohort clinical antibodies)
  POST /cmc/vhh      —— Single VHH   (vs VHH clinical reference)
  POST /cmc/bispecific —— Bispecific VHH-linker-VHH
"""
from __future__ import annotations

import sys, json, re, uuid, time, threading
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Structure-prediction semaphore ────────────────────────────────────────────
# ABodyBuilder2 loads ~4–5 GB of model weights; on an 8 GB server, two concurrent
# structure-prediction runs cause OOM kills.  This semaphore ensures only ONE run
# proceeds at a time; all others block the worker thread (not the event loop) and
# advertise their queue position via progress_note so the client can display it.
_STRUCTURE_SEM = threading.Semaphore(1)
_STRUCTURE_QUEUE: list[str] = []          # ordered list of job_ids waiting
_STRUCTURE_QUEUE_LOCK = threading.Lock()

from fastapi import APIRouter, HTTPException, BackgroundTasks

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from api.models import (
    CMCIgGRequest, CMCVHHRequest, CMCBispecificRequest,
    BispecificPairingScoreRequest,
    JobStatus, CMCVHHResult,
)
from api.job_store import files_url_for_path, job_dir, jobs, save_result, persist_job_snapshot

router = APIRouter(prefix="/cmc", tags=["CMC Developability"])


# ─────────────────────────────────────────────────────────────────────────────
# Helper: generate report
# ─────────────────────────────────────────────────────────────────────────────

def _report(family: str, result_json: Path, out: Path, fmt: str) -> Path:
    """Generate a CMC report in the requested format (html preferred, pdf fallback).
    Raises on failure so callers can capture the error message."""
    rf = (fmt or "html").strip().lower()
    data = json.loads(result_json.read_text(encoding="utf-8"))
    if rf in ("html", "both"):
        if family in ("vhvl_humanization",):
            html_path = _generate_igg_cmc_html(data, out)
            if html_path:
                return html_path
        if family in ("vhh_humanization",):
            html_path = _generate_vhh_cmc_html(data, out)
            if html_path:
                return html_path
        if family in ("bispecific_cmc",):
            html_path = _generate_bispecific_cmc_html(data, out)
            if html_path:
                return html_path
    # PDF fallback (only for humanization families)
    try:
        if family in ("vhvl_humanization",):
            return _generate_igg_cmc_pdf(data, out) or result_json
        if family in ("vhh_humanization",):
            return _generate_vhh_cmc_pdf(data, out) or result_json
    except Exception:
        pass
    return result_json


def _fmt(v, suffix="", decimals=2) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return str(v)


# ─────────────────────────────────────────────────────────────────────────────
# HTML report generators (shared CSS + layout)
# ─────────────────────────────────────────────────────────────────────────────

_HTML_CSS = """
<style>
:root{
  --accent:#1b4fad; --accent2:#2d6cdf; --bg:#f4f7f9; --card:#fff;
  --border:#d0d7e2; --muted:#5a6a80;
  --pass:#1a7a3c; --fail:#b91c1c; --warn:#92610a;
}
*{box-sizing:border-box;margin:0;padding:0}
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  background:var(--bg); color:#2c3e50; margin:0; padding:20px; line-height:1.5; font-size:13px;
}
.page{
  max-width:900px; margin:0 auto; background:#fff;
  padding:32px 40px; border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,.05);
}
.report-header{
  background:var(--accent); color:#fff; padding:20px 28px; border-radius:8px;
  margin-bottom:18px; display:flex; justify-content:space-between; align-items:flex-end;
}
.report-header h1{font-size:1.35rem;font-weight:700;margin:0 0 4px;color:#fff;letter-spacing:-.02em}
.report-header .sub{font-size:.84rem;font-weight:600;opacity:.95;line-height:1.45;color:#fff}
.report-header .ts{font-size:.78rem;font-weight:600;opacity:.92;text-align:right}
.report-header .header-meta{margin-top:10px;font-size:.76rem;font-weight:600;opacity:.9;line-height:1.45;width:100%}
.report-header .header-meta div{margin-top:2px}
@media print{.report-header .header-meta{color:#fff!important;opacity:1}}
.card.accent h1{font-size:1.25rem;font-weight:800;color:var(--accent);letter-spacing:.01em;margin-bottom:8px}
h2{color:var(--accent); font-size:.98rem; margin:0 0 12px; padding-bottom:6px; border-bottom:2px solid var(--border)}
.meta{font-size:.78rem;color:var(--muted);margin-top:4px;line-height:1.5}
.badge{display:inline-block;padding:2px 9px;border-radius:10px;font-size:.7rem;font-weight:700;vertical-align:middle}
.pass,.badge-ok{background:#d1fae5;color:var(--pass);border:1px solid #6ee7b7}
.warn,.badge-warn{background:#fef3c7;color:var(--warn);border:1px solid #fcd34d}
.fail,.badge-fail{background:#fee2e2;color:var(--fail);border:1px solid #fca5a5}
.card{background:var(--card); border:1px solid var(--border); border-radius:8px; padding:18px 20px; margin-bottom:16px;box-shadow:0 1px 3px rgba(15,23,42,.06)}
.card.accent{border-color:#aac4ee; background:#f8fafc}
.score-row{display:flex;align-items:flex-end;gap:32px;margin:8px 0 12px;flex-wrap:wrap}
.score-val{font-size:2.1rem;font-weight:800;color:var(--accent)}
.score-lbl{font-size:.72rem;color:var(--muted);margin-bottom:4px}
.score-rank{font-size:1.15rem;font-weight:700;color:var(--pass)}
table{width:100%;border-collapse:collapse;font-size:.83rem;margin-top:8px}
th,td{padding:7px 12px;border-bottom:1px solid #eef;text-align:left;vertical-align:top}
th{background:#e8eef8; color:var(--accent); font-weight:600; font-size:.74rem; text-transform:uppercase; letter-spacing:.04em; border-bottom:2px solid var(--border)}
.risk-low{color:var(--pass);font-weight:600}
.risk-mod{color:var(--warn);font-weight:600}
.risk-high{color:var(--fail);font-weight:600}
.interp{font-size:.78rem;color:var(--muted);line-height:1.5;margin-top:4px}
pre.seqblk{
  white-space:pre-wrap;word-break:break-all;font-size:.78rem;
  font-family:Consolas,'Courier New',monospace;
  background:#f8fafd;padding:12px 14px;border-radius:6px;border:1px solid var(--border);
  color:#1a2030;line-height:1.8;
}
footer{text-align:center;color:#8899aa;font-size:.72rem;margin-top:28px;padding-top:12px;border-top:1px solid var(--border)}
footer a{color:#1b4fad}
.param-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-top:10px;font-size:.76rem}
@media (max-width:900px){.param-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:560px){.param-grid{grid-template-columns:1fr}}
.param-cell{border:1px solid var(--border);border-radius:6px;padding:8px 10px;background:#f8fafc;line-height:1.35}
.param-cell .pn{font-size:.66rem;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.param-cell .pv{font-size:.8rem;font-weight:700;margin-top:3px;display:flex;align-items:baseline;gap:6px;flex-wrap:wrap}
.param-cell .pv .rk{font-size:.65rem;font-weight:600;color:var(--muted)}
.param-cell .gate{font-size:.62rem;color:var(--muted);margin-top:4px;line-height:1.3}
.param-cell .interp2{font-size:.62rem;color:var(--muted);margin-top:4px;line-height:1.35}
.param-dot{display:inline-block;width:7px;height:7px;border-radius:50%;flex-shrink:0;margin-top:2px}
.param-dot.low{background:var(--pass)}.param-dot.mod{background:var(--warn)}.param-dot.high{background:var(--fail)}.param-dot.na{background:#94a3b8}
@media print{
  body{background:#fff;font-size:10.5px;color:#000;padding:0}
  .page{max-width:100%;padding:0;box-shadow:none}
  .report-header{background:var(--accent) !important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .report-header h1,.report-header .sub,.report-header .ts,.report-header .header-meta{color:#fff!important;opacity:1}
  /* Permit card pagination to reduce large white gaps in exported PDFs. */
  .card{break-inside:auto;page-break-inside:auto;border:1px solid #ccc;margin-bottom:10px}
  .card h2{break-after:avoid;page-break-after:avoid}
  .param-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
}
</style>"""


from core.cmc.igg_cmc_report_html import _generate_igg_cmc_html


def _generate_vhh_cmc_html(data: dict, out: Path) -> "Optional[Path]":
    """Generate a self-contained HTML CMC report for VHH vs clinical reference."""
    from datetime import datetime
    import html as _html

    def esc(v: Any) -> str:
        return _html.escape(str(v)) if v is not None else "—"

    def fv(v, d=2):
        try:
            return f"{float(v):.{d}f}" if v is not None else "—"
        except (TypeError, ValueError):
            return str(v)

    def _seq_chunks(seq: str, size: int = 10) -> str:
        return "".join(
            f'<span style="margin-right:8px;letter-spacing:.04em">{esc(seq[i:i+size])}</span>'
            for i in range(0, len(seq), size)
        )

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    name = esc(data.get("name") or data.get("project_name") or "—")
    vhh_seq = str(data.get("sequence") or "")
    adi = data.get("adi_score") if data.get("adi_score") is not None else data.get("adi")
    adi_str = fv(adi, 1)
    status = str(data.get("adi_grade") or data.get("overall_status") or "—")
    score_display_name = str(data.get("score_display_name") or "VHH/sdAb Gate Score")
    score_method = str(data.get("score_method") or "PASS/WARN/FAIL gate-discrete 4-category weighted score")
    score_note = str(data.get("score_comparability_note") or "Not directly comparable with regular IgG ADI")

    hpr_score = data.get("hpr_score")
    hpr_str = fv(hpr_score, 4)

    # ── Reference ranges (from evaluate_single_vhh result) ────────────────────
    ref_ranges = data.get("ref_ranges") or {}
    sdab_origin = str(data.get("sdab_origin") or "camelid_vhh").lower()
    if sdab_origin in {"engineered_vh", "atlas24", "engineered"}:
        panel_type_label = "Engineered single-domain benchmark panel"
    elif sdab_origin in {"transgenic_sdab", "transgenic", "porustobart"}:
        panel_type_label = "Transgenic sdAb benchmark panel"
    elif sdab_origin in {"clinical_vhh"}:
        panel_type_label = "Clinical VHH benchmark panel"
    else:
        panel_type_label = "Source-matched VHH benchmark panel"

    # ── Metrics with reference bands ─────────────────────────────────────────
    metrics = data.get("metrics") or {}
    risk_flags = data.get("risk_flags") or {}
    percentile_ranks = data.get("percentile_ranks") or {}

    _METRIC_LABELS_DISPLAY = {
        "pI":                  "Isoelectric point (pI)",
        "GRAVY":               "GRAVY (hydrophobicity)",
        "instability_index":   "Instability index",
        "net_charge_pH7":      "Net charge (pH 7)",
        "hydro_patch_max9":    "Hydrophobic patch (9-mer max)",
        "charge_patch_max7":   "Charge patch (7-mer max)",
        "SAP_score":           "SAP score",
        "exposed_fr2_hydrophobicity": "Exposed FR2 hydrophobicity (Parker)",
        "SAP_mode":            None,   # skip
        "_positions":          None,   # skip
        "agg_motifs":          "Aggregation motifs",
        "hydro_cluster_count": "Hydrophobic clusters",
        "glycosylation_sites": "N-glycosylation sites",
        "deamidation_sites":   "Deamidation sites (NG/NS)",
        "isomerization_sites": "Isomerization sites (DG/DS)",
        "oxidation_sites":     "Oxidation-prone residues",
        "free_cys":            "Free Cys (beyond disulfide)",
    }

    def _flag_badge(flag: str) -> str:
        if flag == "PASS":
            return '<span class="badge pass">PASS</span>'
        if flag == "WARN":
            return '<span class="badge warn">WARN</span>'
        if flag == "FAIL":
            return '<span class="badge fail">FAIL</span>'
        return f'<span class="badge" style="background:#e8eef8;color:#5a6a80;border:1px solid #cdd5e4">{esc(flag)}</span>'

    metric_rows = ""
    for k, v in metrics.items():
        label = _METRIC_LABELS_DISPLAY.get(k, k)
        if label is None or k.startswith("_"):
            continue
        sap_note = ""
        if k == "SAP_score":
            sap_mode = metrics.get("SAP_mode") or "sequence_proxy_7mer"
            sap_note = f'<br><span style="font-size:.68rem;color:var(--muted)">Method: {esc(sap_mode)}</span>'
        val_str = fv(v) if isinstance(v, (int, float)) else esc(str(v))
        flag = risk_flags.get(k, "")
        badge = _flag_badge(flag) if flag else ""
        pct_band = percentile_ranks.get(k, "")
        rr = ref_ranges.get(k, {})
        if rr.get("p25") is not None and rr.get("p75") is not None:
            ref_str = f'{fv(rr["p25"])}–{fv(rr["p75"])}'
            if rr.get("p5") is not None and rr.get("p95") is not None:
                ref_str += f' <span style="font-size:.68rem;color:var(--muted)">(p5: {fv(rr["p5"])} / p95: {fv(rr["p95"])})</span>'
        else:
            ref_str = "—"
        metric_rows += (
            f"<tr>"
            f"<td>{esc(label)}{sap_note}</td>"
            f"<td><strong>{val_str}</strong></td>"
            f"<td>{ref_str}<br><span style='font-size:.68rem;color:var(--muted)'>{esc(pct_band)}</span></td>"
            f"<td>{badge}</td>"
            f"</tr>\n"
        )

    # ── Card-grid version of the same metrics (high-density display) ──────────
    def _param_card(label: str, val_str: str, ref_str: str, flag: str, pct_band: str, note: str = "") -> str:
        dot_class = {"PASS": "low", "WARN": "mod", "FAIL": "high"}.get(str(flag).upper(), "na")
        gate = f"Normal: {ref_str}" if ref_str and ref_str not in ("—", "") else ""
        rk_html = f'<span class="rk">{esc(pct_band)}</span>' if pct_band else ""
        gate_html = f'<div class="gate">{esc(gate)}</div>' if gate else ""
        note_html = f'<div class="interp2">{esc(note)}</div>' if note else ""
        return (
            f'<div class="param-cell">'
            f'<div class="pn">{esc(label)}</div>'
            f'<div class="pv"><span class="param-dot {dot_class}"></span><span>{val_str}</span>{rk_html}</div>'
            f'{gate_html}{note_html}'
            f'</div>'
        )

    param_grid_cells = ""
    for k, v in metrics.items():
        label = _METRIC_LABELS_DISPLAY.get(k, k)
        if label is None or k.startswith("_"):
            continue
        val_str = fv(v) if isinstance(v, (int, float)) else esc(str(v))
        note = ""
        if k == "SAP_score":
            sap_mode = metrics.get("SAP_mode") or "sequence_proxy_7mer"
            note = f"Method: {sap_mode}"
        flag = risk_flags.get(k, "")
        pct_band = percentile_ranks.get(k, "")
        rr = ref_ranges.get(k, {})
        ref_str = (
            f'{fv(rr["p25"])}–{fv(rr["p75"])}'
            if rr.get("p25") is not None and rr.get("p75") is not None
            else "—"
        )
        param_grid_cells += _param_card(label, val_str, ref_str, flag, pct_band, note)

    # ── AbNatiV2 full section ──────────────────────────────────────────────────
    abnativ_delta     = data.get("abnativ_delta")
    abnativ_tier      = data.get("abnativ_tier") or "UNKNOWN"
    abnativ_vh2       = data.get("abnativ_vh2_score")
    abnativ_vhh2      = data.get("abnativ_vhh2_score")

    # Internal single-domain benchmark anchors (client-safe: no cohort size disclosure)
    VHH68_VHH2_P25, VHH68_VHH2_P75 = 0.6936, 0.8009
    VHH68_VHH2_MEAN = 0.757

    def _tier_badge(tier: str) -> str:
        t = (tier or "").upper()
        if t in ("EXCELLENT", "GOOD"):
            return f'<span class="badge pass">{esc(tier)}</span>'
        if t == "PASS":
            return f'<span class="badge pass">PASS</span>'
        if t == "WARN":
            return f'<span class="badge warn">WARN</span>'
        if t in ("FAIL", "ERROR"):
            return f'<span class="badge fail">{esc(tier)}</span>'
        return f'<span class="badge" style="background:#e8eef8;color:#5a6a80;border:1px solid #cdd5e4">{esc(tier)}</span>'

    def _pct_vs_panel(score) -> str:
        """Simple percentile label vs internal VHH benchmark panel."""
        if score is None:
            return "—"
        s = float(score)
        if s < 0.6735:
            return "< p5 (below clinical floor)"
        if s < VHH68_VHH2_P25:
            return "p5–p25 (below normal)"
        if s <= VHH68_VHH2_P75:
            return "p25–p75 ✓ (within normal)"
        if s <= 0.8503:
            return "p75–p95 (above normal)"
        return "> p95 (top tier)"

    def _delta_interp(delta) -> str:
        if delta is None:
            return "—"
        d = float(delta)
        if d >= 0.10:
            return "VHH-biased — strong single-domain character"
        if d >= 0.00:
            return "Neutral-VHH — acceptable single-domain character"
        if d >= -0.05:
            return "Borderline — marginal single-domain character; monitor in expression"
        return "VH-biased — low single-domain naturalness; engineering may be needed"

    if abnativ_vhh2 is None:
        _abnativ_inner = (
            '<p class="interp" style="background:#fffbeb;border:1px solid #fde68a;border-radius:5px;'
            'padding:8px 12px;color:#92400e;margin-bottom:10px">'
            '<strong>AbNatiV2 scores not computed</strong> — deep-learning model initialization '
            'timed out during this request. Scores will appear when the model is pre-warmed '
            '(first run per server session may take ~60 s). '
            'All other CMC metrics above are unaffected.</p>'
        )
    else:
        _vhh2_status = _flag_badge("PASS" if float(abnativ_vhh2) >= VHH68_VHH2_P25 else "WARN")
        _vh2_note = "<span style='font-size:.78rem;color:var(--muted)'>lower = more VHH-like</span>"
        _abnativ_inner = (
            f'<p class="interp" style="margin-bottom:12px">'
            f"AbNatiV2 scores both models independently: <strong>VH2</strong> = naturalness as conventional paired VH domain;"
            f" <strong>VHH2</strong> = naturalness as VHH / single-domain antibody (0–1, higher = more natural)."
            f" &Delta; = VHH2 &minus; VH2 — positive values confirm single-domain character."
            f" VHH2 reference: internal source-matched benchmark panel (release R2026.05); "
            f" p25={VHH68_VHH2_P25}, p75={VHH68_VHH2_P75}, mean={VHH68_VHH2_MEAN}).</p>"
            f"<table>"
            f"<tr><th>Score</th><th>Value</th><th>Benchmark reference (release R2026.05)</th><th>Status</th></tr>"
            f"<tr><td><strong>VH2</strong> (as conventional VH)</td>"
            f"<td><strong>{fv(abnativ_vh2, 4)}</strong></td>"
            f"<td><span style='font-size:.78rem;color:var(--muted)'>Not VHH benchmark (lower = good for VHH)</span></td>"
            f"<td>{_vh2_note if abnativ_vh2 is not None else '—'}</td></tr>"
            f"<tr><td><strong>VHH2</strong> (as single-domain VHH)</td>"
            f"<td><strong>{fv(abnativ_vhh2, 4)}</strong></td>"
            f"<td>p25–p75: {VHH68_VHH2_P25}–{VHH68_VHH2_P75} &nbsp;·&nbsp; mean: {VHH68_VHH2_MEAN}</td>"
            f"<td>{_vhh2_status}</td></tr>"
            f"<tr><td><strong>&Delta; (VHH2 &minus; VH2)</strong></td>"
            f"<td><strong>{fv(abnativ_delta, 4)}</strong></td>"
            f"<td>VHH clinical anchor: Caplacizumab &Delta;=+0.227 &nbsp;·&nbsp; cut-off: &Delta; &ge; 0.00</td>"
            f"<td>{_tier_badge(abnativ_tier)}</td></tr></table>"
            f'<p class="interp" style="margin-top:8px">'
            f"<strong>Percentile vs benchmark panel:</strong> {esc(_pct_vs_panel(abnativ_vhh2))}<br>"
            f"<strong>Verdict:</strong> {esc(_delta_interp(abnativ_delta))}</p>"
        )

    abnativ_html = f"""
<div class="card">
  <h2>§N — AbNatiV2 Naturalness (VH2 / VHH2 Dual Score)</h2>
  {_abnativ_inner}
</div>"""

    # ── §V VHH-specific section ───────────────────────────────────────────────
    vs = data.get("vhh_specific") or {}
    vhh_specific_html = ""
    if vs:
        tet = esc(vs.get("fr2_hallmark_tetrad") or "—")
        tet_ok = vs.get("fr2_hallmark_ok")
        tet_flag = vs.get("fr2_hallmark_flag", "NOT_RUN")
        tet_badge = _flag_badge(tet_flag) if tet_flag not in ("NOT_RUN",) else '<span style="font-size:.75rem;color:var(--muted)">ANARCI not available</span>'
        fr2h = vs.get("exposed_fr2_hydrophobicity")
        fr2h_flag = vs.get("fr2_hydro_flag", "—")
        fr2h_ref = vs.get("vhh_specific_ref", {}).get("exposed_fr2_hydrophobicity", {})
        fr2h_ref_str = f'{fv(fr2h_ref.get("p25"),3)}–{fv(fr2h_ref.get("p75"),3)}' if fr2h_ref else "—"
        nc = vs.get("noncanonical_cys", 0)
        nc_flag = vs.get("noncanonical_cys_flag", "PASS")
        nc_note = esc(vs.get("noncanonical_cys_note", ""))
        cdr3_est = vs.get("cdr3_length_estimate")

        vhh_specific_html = f"""
<div class="card">
  <h2>§V — VHH Format-Specific Parameters</h2>
  <p class="interp" style="margin-bottom:10px">
    Parameters unique to VHH single-domain format. These are not evaluated in standard VH/VL CMC pipelines.
    Reference distributions from internal source-matched benchmark panel (release R2026.05) where available.
    Gate Score is the core VHH/sdAb developability score. Exposed FR2 hydrophobicity is included in the Gate Score (hydrophobicity category). Other VHH format-specific items (FR2 hallmark tetrad, noncanonical Cys) are reported as format-QC flags and are informational only.
  </p>
  <div class="param-grid">
    <div class="param-cell">
      <div class="pn">FR2 hallmark tetrad <span style="font-weight:400">(Kabat 37/44/45/47)</span></div>
      <div class="pv"><span class="param-dot {'low' if tet_flag == 'PASS' else 'mod' if tet_flag == 'WARN' else 'high' if tet_flag == 'FAIL' else 'na'}"></span><span style="font-family:monospace">{tet}</span><span class="rk">{'✓' if tet_ok else ('✗' if tet_ok == False else '')}</span></div>
      <div class="gate">Benchmark panel pass profile (release R2026.05)</div>
      <div class="interp2">VHH replaces VH-VL interface residues with hydrophilic residues to limit self-aggregation without VL.</div>
      <div style="margin-top:6px">{tet_badge}</div>
    </div>
    <div class="param-cell">
      <div class="pn">Exposed FR2 hydrophobicity (Parker scale)</div>
      <div class="pv"><span class="param-dot {'low' if fr2h_flag == 'PASS' else 'mod' if fr2h_flag == 'WARN' else 'high' if fr2h_flag == 'FAIL' else 'na'}"></span><span>{fv(fr2h, 3)}</span></div>
      <div class="gate">p25-p75: {fr2h_ref_str}; mean={fv(fr2h_ref.get("mean"),3)}</div>
      <div class="interp2">Mean Parker hydrophobicity of FR2 window. More negative = more hydrophilic = lower self-aggregation risk.</div>
      <div style="margin-top:6px">{_flag_badge(fr2h_flag) if fr2h_flag != "NOT_RUN" else "—"}</div>
    </div>
    <div class="param-cell">
      <div class="pn">Noncanonical Cys</div>
      <div class="pv"><span class="param-dot {'mod' if nc > 0 else 'low'}"></span><span>{nc}</span></div>
      <div class="gate">Observed in benchmark panel (release R2026.05)</div>
      <div class="interp2">Cys count beyond canonical intra-domain disulfide. Extra Cys may form stabilizing VHH structural disulfide.</div>
      <div style="margin-top:6px">{_flag_badge("INFO") if nc > 0 else _flag_badge("PASS")}</div>
    </div>
    <div class="param-cell">
      <div class="pn">CDR3 length (estimated)</div>
      <div class="pv"><span class="param-dot {'low' if cdr3_est is not None and 6 <= cdr3_est <= 24 else 'mod' if cdr3_est is not None else 'na'}"></span><span>{cdr3_est if cdr3_est is not None else "—"}</span><span class="rk">aa</span></div>
      <div class="gate">Benchmark panel: modal 12-16 aa; p5: 6 / p95: 24</div>
      <div class="interp2">Estimated from sequence; use ANARCI-confirmed count for final report.</div>
      <div style="margin-top:6px">{_flag_badge("PASS") if cdr3_est is not None and 6 <= cdr3_est <= 24 else (_flag_badge("WARN") if cdr3_est is not None else "—")}</div>
    </div>
  </div>
  <p class="interp" style="margin-top:8px">
    <strong>FR2 hallmark note:</strong> VHH uses F/L/V at pos 37 (replaces W), E/Q/L at 44 (replaces G),
    R/K at 45 (replaces L), G/F at 47 (replaces W). Any canonical VH residue at these positions increases
    hydrophobic exposure and aggregation risk without VL partner.
    <strong>NanoBERT PLL</strong> (VHH-specific language model score; benchmark mean=−0.284, p25=−0.322, p75=−0.247)
    is not currently computed online — available in offline pipeline.
  </p>
</div>"""

    # ── Structure section ──────────────────────────────────────────────────────
    sm = data.get("structure_metrics") or {}
    structure_html = ""
    if data.get("structure_requested") or sm:
        plddt = sm.get("plddt")
        plddt_str = fv(plddt, 1)
        plddt_badge = ""
        if plddt is not None:
            p = float(plddt)
            if p >= 85:
                plddt_badge = '<span class="badge pass">HIGH CONF</span>'
            elif p >= 70:
                plddt_badge = '<span class="badge warn">MODERATE</span>'
            else:
                plddt_badge = '<span class="badge fail">LOW CONF</span>'
        sap_mode = sm.get("sap_mode") or "—"
        sap_sasa = sm.get("sap_sasa")
        psh = sm.get("psh"); ppc = sm.get("ppc"); pnc = sm.get("pnc")
        cdr_sasa = sm.get("cdr_sasa") or {}

        # Load structural benchmark reference ranges (client-safe display via release ID)
        _VHH69_REF: dict = {}
        try:
            import json as _json
            _vhh69_path = Path(__file__).parent.parent.parent / "data/reference/VHH69_sasa_structural_stats_v1.json"
            _VHH69_REF = _json.loads(_vhh69_path.read_text()).get("structural_metrics", {})
        except Exception:
            pass

        def _sref(key: str) -> str:
            r = _VHH69_REF.get(key, {})
            if r.get("p25") is not None and r.get("p75") is not None:
                note = f'<span style="font-size:.68rem;color:var(--muted)">p5: {fv(r.get("p5"),2)} / p95: {fv(r.get("p95"),2)} (release R2026.05)</span>'
                return f'{fv(r["p25"],2)}–{fv(r["p75"],2)}<br>{note}'
            return "—"

        cdr_rows = "".join(
            f"<tr><td>CDR {loop} mean SASA</td><td>{fv(v, 1)} Å²</td>"
            f"<td>{_sref('cdr_' + loop + '_sasa')}</td><td></td></tr>"
            for loop, v in cdr_sasa.items() if v is not None
        )
        err = sm.get("_struct_cmc_error")
        err_html = f'<p style="color:#b91c1c;font-size:.78rem">⚠ Structure error: {esc(err)}</p>' if err else ""
        pdb_url = sm.get("pdb_url") or ""
        pdb_link = f' &nbsp;·&nbsp; <a href="{esc(pdb_url)}" style="color:#1b4fad;font-size:.75rem">Download PDB</a>' if pdb_url else ""

        structure_html = f"""
<div class="card">
  <h2>§S — Structure Quality &amp; Surface Metrics (NanoBodyBuilder2)</h2>
  {err_html}
  <div class="score-row" style="margin-bottom:8px">
    <div>
      <div class="score-val" style="font-size:1.6rem">{plddt_str}</div>
      <div class="score-lbl">pLDDT (fold confidence){pdb_link}</div>
    </div>
    <div style="display:flex;gap:4px;align-items:center">{plddt_badge}</div>
  </div>
  <table>
    <tr><th>Metric</th><th>Value</th><th>Normal range (benchmark panel, p25–p75)</th><th>Status</th></tr>
    <tr><td>SAP score (SASA-based, {esc(sap_mode)})</td><td>{fv(sap_sasa, 4)}</td>
        <td>{_sref("sap_sasa")}<br><span style="font-size:.68rem;color:var(--muted)">SASA-weighted aggregation surface</span></td>
        <td>{_flag_badge(risk_flags.get("SAP_score", "PASS"))} </td></tr>
    <tr><td>Surface hydrophobic patch (psh)</td><td>{fv(psh, 3)}</td>
        <td>{_sref("psh")}</td>
        <td>{_flag_badge(risk_flags.get("psh", "PASS"))}</td></tr>
    <tr><td>Positive charge patch (ppc)</td><td>{fv(ppc, 0)}</td>
        <td>{_sref("ppc")}<br><span style="font-size:.68rem;color:var(--muted)">&lt; 4 preferred</span></td>
        <td>{_flag_badge(risk_flags.get("ppc", "PASS"))}</td></tr>
    <tr><td>Negative charge patch (pnc)</td><td>{fv(pnc, 0)}</td>
        <td>{_sref("pnc")}<br><span style="font-size:.68rem;color:var(--muted)">&lt; 4 preferred</span></td>
        <td>{_flag_badge(risk_flags.get("pnc", "PASS"))}</td></tr>
    {cdr_rows}
  </table>
  <p class="interp" style="margin-top:8px">
    pLDDT ≥ 85: high-confidence; 70–85: moderate; &lt; 70: low — recheck CDR3 length and hydrophobic core.
    CDR loop SASA = mean per-residue solvent-accessible surface (Å²). Reference: source-matched structural benchmark panel (release R2026.05).
    psh p25–p75 range ({fv(_VHH69_REF.get("psh",{}).get("p25"),2)}–{fv(_VHH69_REF.get("psh",{}).get("p75"),2)}) corresponds to normal benchmark single-domain hydrophobic surface exposure.
  </p>
</div>"""

    from api.report_versioning import cmc_version_banner_html, cohort_provenance_html

    _ver_banner = cmc_version_banner_html(
        "cmc_vhh",
        content_variant="CMC Standard v1.2 · source-matched benchmark panel",
        extra_inner_divs=[
            f"<div>Sequence: <strong>{name}</strong></div>",
            f"<div>Generated: {ts}</div>",
        ],
        header_title="InSynBio AbEngineCore",
        header_subtitle="VHH CMC Developability Report | CMC Standard v1.2",
        right_stamp_html=f"{ts}<br><span style='font-size:.7rem;opacity:.6'>CONFIDENTIAL</span>",
    )
    _cohort_block = cohort_provenance_html("cmc_vhh")

    # ── §Rec — Recommendation block ────────────────────────────────────────────
    _fail_flags = [k for k, v in risk_flags.items() if v == "FAIL"]
    _warn_flags = [k for k, v in risk_flags.items() if v == "WARN"]
    _adi_val    = adi if isinstance(adi, (int, float)) else None
    _rec_items  = []
    if _adi_val is not None:
        if _adi_val >= 80:
            _rec_items.append(("<span style='color:var(--pass);font-weight:700'>● Grade A</span>", "Gate Score ≥ 80 — manufacturable range. Proceed to expression and functional validation."))
        elif _adi_val >= 60:
            _rec_items.append(("<span style='color:var(--warn);font-weight:700'>● Grade B</span>", "Gate Score 60–79 — acceptable with caution. Address WARN flags below before scale-up."))
        elif _adi_val >= 40:
            _rec_items.append(("<span style='color:var(--warn);font-weight:700'>● Grade C</span>", "Gate Score 40–59 — moderate risk. Engineering of flagged positions recommended before IND filing."))
        else:
            _rec_items.append(("<span style='color:var(--fail);font-weight:700'>● Grade D</span>", "Gate Score < 40 — high manufacturability risk. Framework or CDR re-engineering strongly advised."))
    for fk in _fail_flags:
        label = fk.replace("_", " ").title()
        _rec_items.append(("<span style='color:var(--fail);font-weight:700'>● FAIL — " + esc(label) + "</span>", "Out-of-range for source-matched clinical cohort. Engineering or re-design required before regulatory submission."))
    for wk in _warn_flags:
        label = wk.replace("_", " ").title()
        _rec_items.append(("<span style='color:var(--warn);font-weight:700'>● WARN — " + esc(label) + "</span>", "Borderline. Monitor closely; consider optimization if proceeding to GMP manufacturing."))
    if not _rec_items:
        _rec_items.append(("● All metrics within normal range", "No CMC-related engineering interventions required at this stage."))
    _rec_rows = "".join(
        f"<tr><td style='width:30%;font-size:.8rem;vertical-align:top;padding:6px 10px'>{bullet}</td>"
        f"<td style='font-size:.8rem;color:#374151;padding:6px 10px'>{esc(action)}</td></tr>"
        for bullet, action in _rec_items
    )
    # ── Smart-CMC FR suggestions section ─────────────────────────────────────
    _fr_suggs = data.get("fr_modification_suggestions") or []
    _smart_cmc_run = data.get("smart_cmc_run", False)
    _smart_cmc_err = data.get("smart_cmc_error")
    _is_engvh_html = sdab_origin in {"engineered_vh", "atlas24", "engineered"}

    if _fr_suggs:
        _cat_labels = {
            "hydrophobic":    "Hydrophobic Patch Reduction",
            "charge":         "Charge Patch Reduction",
            "pI":             "pI Tuning",
            "stability":      "Stability (dipeptide)",
            "sdab_adaptation":"sdAb Adaptation (FR Engineering)",
            "engvh_stealth":  "EngVH Stealth Alignment (Atlas-24)",
        }
        _prio_colors = {"HIGH": "#b91c1c", "MEDIUM": "#b45309", "LOW": "#4a7c59"}
        _sugg_rows = ""
        for s in _fr_suggs:
            cat = _cat_labels.get(s.get("category", ""), s.get("category", ""))
            lbl = esc(s.get("label", "—"))
            rat = esc(s.get("rationale", ""))
            note = esc(s.get("note", ""))
            prio = s.get("priority", "MEDIUM")
            pcolor = _prio_colors.get(prio, "#6b7280")
            note_cell = f'<br><span style="font-size:.72rem;color:#6b7280">{note}</span>' if note else ""
            _sugg_rows += (
                f"<tr>"
                f"<td style='color:{pcolor};font-weight:600'>{prio}</td>"
                f"<td>{esc(cat)}</td>"
                f"<td><code style='font-size:.82rem'>{lbl}</code></td>"
                f"<td>{rat}{note_cell}</td>"
                f"</tr>"
            )
        _origin_note = "EngVH mode: sdAb adaptation sites (L18S/F68Y) are highest priority; stealth alignment is secondary." if _is_engvh_html else \
                       "Hallmark positions (Kabat 37/44/45/47) are protected and will not appear as suggestions."
        _vhh_smart_cmc_html = f"""
<div class="card" style="border-left:3px solid #d97706">
  <h2>§FR — Smart-CMC: FR Optimization Suggestions</h2>
  <p class="interp" style="margin-bottom:8px">{_origin_note}</p>
  <table>
    <thead><tr><th>Priority</th><th>Category</th><th>Mutation</th><th>Rationale</th></tr></thead>
    <tbody>{_sugg_rows}</tbody>
  </table>
  <p class="interp" style="margin-top:8px;color:#b45309">
    These are VHH/sdAb sequence-level advisory suggestions only. Apply one mutation at a time and re-evaluate via VHH CMC.
    CDR positions are never included. Verify high-impact positions (W, F) by structure before synthesis.
  </p>
</div>"""
    elif _smart_cmc_run:
        _vhh_smart_cmc_html = f"""
<div class="card" style="border-left:3px solid #4a7c59">
  <h2>§FR — Smart-CMC: FR Optimization Suggestions</h2>
  <p class="interp" style="color:var(--pass)">
    No FR modifications recommended — VHH/sdAb CMC gates, sequence liabilities, AbNatiV2/HPR context, and origin-specific FR checks are within the selected benchmark reference.
    {_smart_cmc_err or ""}
  </p>
</div>"""
    else:
        _vhh_smart_cmc_html = ""

    _vhh_cmc_recommendation_html = f"""
<div class="card">
  <h2>§Rec — Recommendation Summary</h2>
  <p class="interp" style="margin-bottom:8px">
    Engineering and next-step recommendations derived from VHH/sdAb Gate Score grade and metric-level flags.
    Thresholds referenced to source-matched benchmark cohort (release R2026.05).
  </p>
  <table>
    <thead><tr><th>Finding</th><th>Recommended Action</th></tr></thead>
    <tbody>{_rec_rows}</tbody>
  </table>
  <p class="interp" style="margin-top:8px">
    For flag-specific residue-level mutation suggestions, request a <em>CMC Mutation Advisory</em> report.
    For premium structural TAP/colloidal stability assessment, request <em>CMC Premium Tier</em>.
  </p>
</div>"""

    _vhh_seq_len = len(vhh_seq)
    _seq_block_html = ""
    if vhh_seq:
        _seq_block_html = f"""
<div class="card">
  <h2>§Seq — Submitted VHH Sequence</h2>
  <p class="interp" style="margin-bottom:8px">Single-domain antibody sequence as submitted for this assessment ({_vhh_seq_len} aa).</p>
  <div style="background:#f8fafd;border:1px solid var(--border);border-radius:6px;padding:12px 14px">
    <div style="font-size:.72rem;font-weight:700;color:var(--accent2);margin-bottom:6px">
      {name} &nbsp;<span style="font-weight:400;color:#8a9ab0;font-size:.7rem">({_vhh_seq_len} aa)</span>
    </div>
    <div style="font-family:Consolas,'Courier New',monospace;font-size:.78rem;word-break:break-all;line-height:1.9;color:#1a2030">{_seq_chunks(vhh_seq)}</div>
  </div>
  <p class="interp" style="margin-top:6px">Sequence is archived in the delivery FASTA alongside this report.</p>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">
<title>InSynBio AbEngineCore | VHH CMC Report — {name}</title>
{_HTML_CSS}
</head>
<body>
<div class="page">
{_ver_banner}
{_cohort_block}
{_seq_block_html}

<div class="card accent">
  <h2>§0 — {esc(score_display_name)} &amp; Source-Matched Benchmark</h2>
  <div class="score-row">
    <div><div class="score-val">{adi_str}</div><div class="score-lbl">{esc(score_display_name)} / 100</div></div>
    <div><div class="score-val" style="font-size:1.4rem">{esc(status)}</div><div class="score-lbl">Grade (A≥80 / B≥60 / C≥40 / D&lt;40)</div></div>
  </div>
  <p class="interp" style="margin-top:10px"><strong>Method:</strong> {esc(score_method)}. {esc(score_note)}.</p>
  <div style="margin-top:12px;border-top:1px solid #eee;padding-top:12px;display:flex;gap:32px;flex-wrap:wrap">
    <div><div class="score-lbl">HPR Index (Humanness)</div><div style="font-size:1.05rem;font-weight:700;color:var(--accent)">{hpr_str}</div><div class="interp">Source-matched benchmark: no strict threshold (higher = more human-repertoire compatible)</div></div>
  </div>
</div>

<div class="card">
  <h2>§1 — Developability Metrics vs Benchmark Reference</h2>
  <div class="param-grid">
    {param_grid_cells or '<p class="interp">Metrics not available.</p>'}
  </div>
  <p class="interp" style="margin-top:10px">
    Normal range = p25–p75 of source-matched benchmark panel (release R2026.05).
    Status dot: <span style="color:var(--pass)">●</span> within normal &nbsp;
    <span style="color:var(--warn)">●</span> borderline &nbsp;
    <span style="color:var(--fail)">●</span> out-of-range &nbsp;
    <span style="color:#94a3b8">●</span> no reference.
    Detailed cohort composition is confidential.
  </p>
</div>

{abnativ_html}
{vhh_specific_html}
{structure_html}
{_vhh_smart_cmc_html}
{_vhh_cmc_recommendation_html}
<footer>InSynBio Research &nbsp;·&nbsp; <a href="https://www.insynbio.com">https://www.insynbio.com</a> &nbsp;·&nbsp; {ts} &nbsp;·&nbsp; CONFIDENTIAL &nbsp;·&nbsp; Use Ctrl+P → Save as PDF to export.</footer>
</div>
</body>
</html>"""

    report_dir = out / "reports" / "cmc_vhh"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "VHH_CMC_Report.html"
    try:
        from core.reporting.report_qc_gate import run_report_qc  # noqa: PLC0415
        qc = run_report_qc(html, report_family="vhh_cmc")
        html = qc.inject_qc_badge(html)
    except Exception:
        pass
    path.write_text(html, encoding="utf-8")
    return path


def _generate_bispecific_cmc_html(data: dict, out: Path) -> "Optional[Path]":
    """HTML report for bispecific VHH-linker-VHH (fusion + per-arm benchmark context)."""
    from datetime import datetime
    import html as _html

    def esc(v: Any) -> str:
        return _html.escape(str(v)) if v is not None else "—"

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    proj = esc(data.get("project_name") or "—")
    t1 = esc(data.get("arm1_target") or "Arm1")
    t2 = esc(data.get("arm2_target") or "Arm2")
    fusion_status = esc(data.get("overall_status") or "—")
    flags = data.get("flags") or []
    flags_html = "<br>".join(esc(x) for x in flags) if flags else "—"

    arm1 = data.get("arm1") or {}
    arm2 = data.get("arm2") or {}

    # Linker hydrophobicity / SAP estimate
    linker_seq = data.get("linker_seq") or data.get("recommended_linker_seq") or ""
    linker_gravy = None
    linker_hydro_flag = ""
    if linker_seq and all(c.isalpha() for c in linker_seq):
        from core.cmc.cmc_metrics import compute_GRAVY
        try:
            linker_gravy = compute_GRAVY(linker_seq)
            if linker_gravy <= -0.5:
                linker_hydro_flag = "PASS"
            elif linker_gravy <= 0.0:
                linker_hydro_flag = "WARN"
            else:
                linker_hydro_flag = "FAIL"
        except Exception:
            pass

    def arm_block(title: str, arm: Dict[str, Any]) -> str:
        arm_seq = str(arm.get("sequence") or "")
        arm_seq_len = len(arm_seq)

        # Sequence block for this arm
        def _achunks(seq: str, size: int = 10) -> str:
            return "".join(
                f'<span style="margin-right:8px;letter-spacing:.04em">{esc(seq[i:i+size])}</span>'
                for i in range(0, len(seq), size)
            )
        seq_display = ""
        if arm_seq:
            seq_display = (
                f'<div style="background:#f8fafd;border:1px solid var(--border);border-radius:6px;'
                f'padding:10px 12px;margin-bottom:10px">'
                f'<div style="font-size:.7rem;font-weight:700;color:var(--accent2);margin-bottom:4px">'
                f'Sequence &nbsp;<span style="font-weight:400;color:#8a9ab0">({arm_seq_len} aa)</span></div>'
                f'<div style="font-family:Consolas,monospace;font-size:.76rem;word-break:break-all;line-height:1.9;color:#1a2030">'
                f'{_achunks(arm_seq)}</div></div>'
            )

        # Structure section for this arm
        sm = arm.get("structure_metrics") or {}
        struct_rows = ""
        if sm:
            plddt = sm.get("plddt")
            plddt_str = f"{float(plddt):.1f}" if plddt is not None else "—"
            sap_s = sm.get("sap_sasa"); sap_str2 = f"{float(sap_s):.4f}" if sap_s is not None else "—"
            psh2 = sm.get("psh"); psh_str2 = f"{float(psh2):.3f}" if psh2 is not None else "—"
            ppc2 = sm.get("ppc"); ppc_str2 = f"{float(ppc2):.0f}" if ppc2 is not None else "—"
            pnc2 = sm.get("pnc"); pnc_str2 = f"{float(pnc2):.0f}" if pnc2 is not None else "—"
            cdr_sasa2 = sm.get("cdr_sasa") or {}
            cdr_rows2 = "".join(
                f"<tr><td>CDR {loop} SASA</td><td>{f'{float(v):.1f}' if v is not None else '—'} Å²</td></tr>"
                for loop, v in cdr_sasa2.items()
            )
            err2 = sm.get("_struct_cmc_error")
            err_html2 = f'<tr style="color:#b91c1c"><td colspan="2">Structure error: {esc(err2)}</td></tr>' if err2 else ""
            plddt_badge_color = (
                "#15803d" if plddt is not None and float(plddt) >= 85
                else ("#b45309" if plddt is not None and float(plddt) >= 70
                else "#b91c1c" if plddt is not None else "#6b7280")
            )
            struct_rows = f"""
    <tr style="background:#f0f4ff"><th colspan="2" style="font-size:.72rem;text-transform:uppercase;letter-spacing:.04em">Structure (NanoBodyBuilder2)</th></tr>
    {err_html2}
    <tr><th>pLDDT (confidence)</th><td><strong style="color:{plddt_badge_color}">{plddt_str}</strong> <span style="font-size:.7rem;color:#6b7280">(≥85 high / ≥70 moderate / &lt;70 low)</span></td></tr>
    <tr><th>SAP (SASA-based)</th><td>{sap_str2} <span style="font-size:.7rem;color:#6b7280">aggregation-risk proxy (lower = better)</span></td></tr>
    <tr><th>psh / ppc / pnc</th><td>{psh_str2} / {ppc_str2} / {pnc_str2} <span style="font-size:.7rem;color:#6b7280">(hydrophobic / positive / negative patch)</span></td></tr>
    {cdr_rows2}"""

        # VHH-specific checks for this arm
        vs = arm.get("vhh_specific") or {}
        vhh_rows = ""
        if vs:
            tet = esc(vs.get("fr2_hallmark_tetrad") or "—")
            tet_ok = vs.get("fr2_hallmark_ok")
            tet_badge_c = "color:#15803d" if tet_ok else ("color:#b45309" if tet_ok is not None else "color:#6b7280")
            tet_ok_str = "✓ PASS" if tet_ok else ("⚠ WARN" if tet_ok is not None else "—")
            fr2h = vs.get("exposed_fr2_hydrophobicity")
            fr2h_flag = vs.get("fr2_hydro_flag", "—")
            fr2h_badge_c = "color:#15803d" if fr2h_flag == "PASS" else ("color:#b45309" if fr2h_flag == "WARN" else "color:#b91c1c")
            nc = vs.get("noncanonical_cys", 0)
            vhh_rows = f"""
    <tr style="background:#fdf6e3"><th colspan="2" style="font-size:.72rem;text-transform:uppercase;letter-spacing:.04em">VHH-Specific (FR2 / Cys)</th></tr>
    <tr><th>FR2 hallmark tetrad (K37/44/45/47)</th>
        <td><span style="font-family:monospace">{tet}</span> &nbsp;<span style="{tet_badge_c}">{tet_ok_str}</span></td></tr>
    <tr><th>Exposed FR2 hydrophobicity</th>
        <td>{f'{float(fr2h):.3f}' if fr2h is not None else '—'} &nbsp;<span style="{fr2h_badge_c}">{fr2h_flag}</span>
        <span style="font-size:.7rem;color:#6b7280"> (benchmark p25–p75: −1.150–−0.457; release R2026.05)</span></td></tr>
    <tr><th>Noncanonical Cys</th><td>{nc} {'(CDR3-FR2 disulfide — stabilizing feature)' if nc > 0 else ''}</td></tr>"""

        # Per-arm metrics in card-grid style
        arm_metrics = arm.get("metrics") or {}
        arm_ref_ranges = arm.get("ref_ranges") or {}
        arm_risk_flags = arm.get("risk_flags") or {}
        arm_pcts = arm.get("percentile_ranks") or {}
        _ARM_METRIC_LABELS = {
            "pI":                  "Isoelectric point (pI)",
            "GRAVY":               "GRAVY (hydrophobicity)",
            "instability_index":   "Instability index",
            "net_charge_pH7":      "Net charge (pH 7)",
            "hydro_patch_max9":    "Hydrophobic patch (9-mer)",
            "charge_patch_max7":   "Charge patch (7-mer)",
            "SAP_score":           "SAP score",
            "SAP_mode":            None,
            "_positions":          None,
            "agg_motifs":          "Aggregation motifs",
            "glycosylation_sites": "N-glycosylation sites",
            "deamidation_sites":   "Deamidation sites",
            "isomerization_sites": "Isomerization sites",
            "oxidation_sites":     "Oxidation-prone residues",
            "free_cys":            "Free Cys",
        }
        _adi = arm.get("adi_score") if arm.get("adi_score") is not None else arm.get("adi")
        _hpr = arm.get("hpr_score")
        if _hpr is None and isinstance(arm.get("hpr_index"), dict):
            _hpr = (arm["hpr_index"].get("combined") or {}).get("score")
        
        arm_grid = f"""
<div class="param-grid" style="margin-top:8px">
  <div class="param-cell"><div class="pn">VHH/sdAb Gate Score / 100</div>
    <div class="pv"><span class="param-dot {'low' if _adi is not None and float(_adi) >= 60 else 'mod' if _adi is not None else 'na'}"></span>
    <span>{f'{float(_adi):.1f}' if _adi is not None else '—'}</span></div>
    <div class="gate">Gate-based; not regular IgG ADI</div></div>
  <div class="param-cell"><div class="pn">HPR Index (Humanness)</div>
    <div class="pv"><span class="param-dot {'low' if _hpr is not None and float(_hpr) >= 0.6 else 'mod' if _hpr is not None else 'na'}"></span>
    <span>{f'{float(_hpr):.4f}' if _hpr is not None else '—'}</span></div>
    <div class="gate">Normal: > 0.6000</div></div>"""
        for k, v in arm_metrics.items():
            lbl = _ARM_METRIC_LABELS.get(k, k)
            if lbl is None or k.startswith("_"):
                continue
            val_str = f"{float(v):.3f}" if isinstance(v, float) else str(v) if v is not None else "—"
            flag = arm_risk_flags.get(k, "")
            dot_class = {"PASS": "low", "WARN": "mod", "FAIL": "high"}.get(str(flag).upper(), "na")
            rr = arm_ref_ranges.get(k, {})
            ref_str = (
                f'{float(rr["p25"]):.3f}–{float(rr["p75"]):.3f}'
                if rr.get("p25") is not None and rr.get("p75") is not None
                else ""
            )
            pct = arm_pcts.get(k, "")
            gate_html = f'<div class="gate">Normal: {esc(ref_str)}</div>' if ref_str else ""
            rk_html = f'<span class="rk">{esc(pct)}</span>' if pct else ""
            arm_grid += (
                f'<div class="param-cell">'
                f'<div class="pn">{esc(lbl)}</div>'
                f'<div class="pv"><span class="param-dot {dot_class}"></span><span>{val_str}</span>{rk_html}</div>'
                f'{gate_html}'
                f'</div>'
            )
        arm_grid += "\n</div>"

        return f"""
<div class="card">
  <h2>{title}</h2>
  {seq_display}
  <table style="margin-bottom:10px">
    <tr><th>Overall status</th><td>{esc(arm.get("overall_status"))}</td></tr>
    <tr><th>pI</th><td>{_fmt((arm.get("metrics") or {}).get("pI"))}</td></tr>
    <tr><th>GRAVY</th><td>{_fmt((arm.get("metrics") or {}).get("GRAVY"))}</td></tr>
    <tr><th>SAP (sequence)</th><td>{_fmt((arm.get("metrics") or {}).get("SAP_score"))}</td></tr>
    {vhh_rows}
    {struct_rows}
  </table>
  <h2 style="font-size:.84rem;color:var(--accent);margin-top:4px;border-bottom:none">Developability metrics</h2>
  {arm_grid}
</div>"""

    from api.report_versioning import cmc_version_banner_html, cohort_provenance_html

    _ver_banner = cmc_version_banner_html(
        "cmc_bispecific",
        content_variant="Bispecific VHH CMC Standard v1.0 · source-matched per-arm context",
        extra_inner_divs=[
            f"<div>Project / construct: <strong>{proj}</strong> &nbsp;·&nbsp; Targets: {t1} + {t2}</div>",
            f"<div>Generated: {ts}</div>",
        ],
        header_title="InSynBio AbEngineCore",
        header_subtitle="Bispecific VHH-linker-VHH CMC Report | CMC Standard v1.0",
        right_stamp_html=f"{ts}<br><span style='font-size:.7rem;opacity:.6'>CONFIDENTIAL</span>",
    )
    _cohort_block = cohort_provenance_html("cmc_bispecific")

    # ── §Rec — Bispecific recommendation block ─────────────────────────────────
    _b_status = str(data.get("overall_status") or "UNKNOWN").upper()
    _b_flags  = data.get("flags") or []
    _b_rec_items: list = []
    if "PASS" in _b_status:
        _b_rec_items.append(("● Overall PASS", "Fusion construct meets bispecific CMC thresholds. Proceed to expression and in-vitro validation of both epitope arms."))
    elif "WARN" in _b_status:
        _b_rec_items.append(("● Overall WARN", "One or more parameters borderline. Address flagged items below before scale-up. Consider linker or arm-pI optimization."))
    else:
        _b_rec_items.append(("● Overall FAIL / Unknown", "Critical CMC concern in fusion construct. Review per-arm flags and linker compatibility before proceeding."))
    for _bf in _b_flags[:6]:
        _b_rec_items.append((f"● {esc(str(_bf))}", "See per-arm metrics above for engineering guidance."))
    _a1_status = (arm1.get("overall_status") or "").upper()
    _a2_status = (arm2.get("overall_status") or "").upper()
    if "FAIL" in _a1_status:
        _b_rec_items.append((f"● Arm 1 ({t1}) FAIL", "Engineering of Arm 1 framework or CDRs required to meet CMC benchmarks."))
    if "FAIL" in _a2_status:
        _b_rec_items.append((f"● Arm 2 ({t2}) FAIL", "Engineering of Arm 2 framework or CDRs required to meet CMC benchmarks."))
    _pi_delta = data.get("pI_delta")
    if isinstance(_pi_delta, (int, float)) and abs(_pi_delta) > 1.5:
        _b_rec_items.append(("● ΔpI between arms > 1.5", f"ΔpI = {_pi_delta:.2f}. Large pI difference may promote arm-arm electrostatic interactions and aggregation. Consider pI-matched arm redesign."))
    if not _b_rec_items:
        _b_rec_items.append(("● No critical flags", "Construct is within expected CMC range. Proceed to cell-free or transient expression QC."))
    _b_rec_rows = "".join(
        f"<tr><td style='width:32%;font-size:.8rem;vertical-align:top;padding:6px 10px;font-weight:600'>{bullet}</td>"
        f"<td style='font-size:.8rem;color:#374151;padding:6px 10px'>{action}</td></tr>"
        for bullet, action in _b_rec_items
    )
    _bisp_cmc_recommendation_html = f"""
<div class="card">
  <h2>§Rec — Recommendation Summary</h2>
  <p class="interp" style="margin-bottom:8px">
    Engineering and next-step recommendations for the bispecific VHH-linker-VHH fusion construct.
    Per-arm thresholds reference source-matched benchmark panel (release R2026.05).
  </p>
  <table>
    <thead><tr><th>Finding</th><th>Recommended Action</th></tr></thead>
    <tbody>{_b_rec_rows}</tbody>
  </table>
  <p class="interp" style="margin-top:8px">
    For SmartLink™ linker optimization or arm-specific CMC rescue mutations, request a
    <em>Bispecific CMC Advisory</em>. For structural TAP/colloidal stability, request <em>CMC Premium Tier</em>.
  </p>
</div>"""
    _fusion_seq = str(data.get("fusion_seq") or "")
    _arm1_seq = str(arm1.get("sequence") or "")
    _arm2_seq = str(arm2.get("sequence") or "")
    _lseq = str(linker_seq or "")
    _fusion_seq_html = ""
    if _fusion_seq or _arm1_seq:
        def _bchunks(seq: str, size: int = 10) -> str:
            return "".join(
                f'<span style="margin-right:8px;letter-spacing:.04em">{esc(seq[i:i+size])}</span>'
                for i in range(0, len(seq), size)
            )
        _f_len = len(_fusion_seq)
        _a1_len = len(_arm1_seq)
        _lk_len = len(_lseq)
        _a2_len = len(_arm2_seq)
        _fusion_seq_html = f"""
<div class="card">
  <h2>§Seq — Construct Sequences</h2>
  <p class="interp" style="margin-bottom:8px">Per-arm sequences and assembled fusion construct ({_f_len} aa total).</p>
  <div style="background:#f8fafd;border:1px solid var(--border);border-radius:6px;padding:10px 12px;margin-bottom:8px">
    <div style="font-size:.7rem;font-weight:700;color:var(--accent2);margin-bottom:4px">Arm 1 — {t1} &nbsp;<span style="font-weight:400;color:#8a9ab0">({_a1_len} aa)</span></div>
    <div style="font-family:Consolas,monospace;font-size:.76rem;word-break:break-all;line-height:1.9;color:#1a2030">{_bchunks(_arm1_seq) if _arm1_seq else "—"}</div>
  </div>
  <div style="background:#fdf6e3;border:1px solid #fde68a;border-radius:6px;padding:10px 12px;margin-bottom:8px">
    <div style="font-size:.7rem;font-weight:700;color:#92400e;margin-bottom:4px">Linker: {esc(data.get("recommended_linker") or "")} &nbsp;<span style="font-weight:400;color:#8a9ab0">({_lk_len} aa)</span></div>
    <div style="font-family:Consolas,monospace;font-size:.76rem;color:#78350f;letter-spacing:.05em">{esc(_lseq) if _lseq else "—"}</div>
  </div>
  <div style="background:#f8fafd;border:1px solid var(--border);border-radius:6px;padding:10px 12px;margin-bottom:8px">
    <div style="font-size:.7rem;font-weight:700;color:var(--accent2);margin-bottom:4px">Arm 2 — {t2} &nbsp;<span style="font-weight:400;color:#8a9ab0">({_a2_len} aa)</span></div>
    <div style="font-family:Consolas,monospace;font-size:.76rem;word-break:break-all;line-height:1.9;color:#1a2030">{_bchunks(_arm2_seq) if _arm2_seq else "—"}</div>
  </div>
  {'<div style="background:#f0f4ff;border:1px solid #c7d5f0;border-radius:6px;padding:10px 12px"><div style="font-size:.7rem;font-weight:700;color:var(--accent);margin-bottom:4px">Fusion construct (Arm1–Linker–Arm2) — ' + str(_f_len) + ' aa</div><div style="font-family:Consolas,monospace;font-size:.76rem;word-break:break-all;line-height:1.9;color:#1a2030">' + _bchunks(_fusion_seq) + '</div></div>' if _fusion_seq else ""}
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">
<title>InSynBio AbEngineCore | Bispecific VHH CMC — {proj}</title>
{_HTML_CSS}
</head>
<body>
<div class="page">
{_ver_banner}
{_cohort_block}
{_fusion_seq_html}

<div class="card accent">
  <h2>§0 — Fusion construct summary</h2>
  <div class="score-row">
    <div><div class="score-val">{_fmt(data.get("fusion_pI"))}</div><div class="score-lbl">Fusion pI</div></div>
    <div><div class="score-val">{_fmt(data.get("fusion_GRAVY"))}</div><div class="score-lbl">Fusion GRAVY</div></div>
    <div><div class="score-val">{_fmt(data.get("pI_delta"))}</div><div class="score-lbl">ΔpI (arms)</div></div>
    <div><div class="score-rank">{fusion_status}</div><div class="score-lbl">Overall status</div></div>
  </div>
  <table style="margin-top:12px">
    <tr><th>Recommended linker</th><td class="mono">{esc(data.get("recommended_linker"))}</td></tr>
    <tr><th>Linker sequence</th><td class="mono" style="font-size:.8rem">{esc(linker_seq) if linker_seq else "—"}</td></tr>
    <tr><th>Linker GRAVY (hydrophobicity)</th>
        <td>{f'{float(linker_gravy):.3f}' if linker_gravy is not None else '—'}
        {f'&nbsp;<span style="color:{"#15803d" if linker_hydro_flag == "PASS" else ("#b45309" if linker_hydro_flag == "WARN" else "#b91c1c")}">{linker_hydro_flag}</span>' if linker_hydro_flag else ""}
        <span style="font-size:.7rem;color:#6b7280">(G4S-type linkers: GRAVY ≈ −0.5 to −0.7; more negative = lower aggregation risk)</span></td></tr>
    <tr><th>Linker rationale</th><td>{esc(data.get("linker_rationale"))}</td></tr>
    <tr><th>Fusion instability</th><td>{_fmt(data.get("fusion_instability"))}</td></tr>
    <tr><th>ER expression score</th><td>{_fmt(data.get("er_expression_score"))}</td></tr>
    <tr><th>Flags</th><td>{flags_html}</td></tr>
  </table>
</div>
{arm_block(f"Arm 1 — {t1}", arm1)}
{arm_block(f"Arm 2 — {t2}", arm2)}
{_bisp_cmc_recommendation_html}
<footer>InSynBio Research &nbsp;·&nbsp; <a href="https://www.insynbio.com">https://www.insynbio.com</a> &nbsp;·&nbsp; {ts} &nbsp;·&nbsp; CONFIDENTIAL &nbsp;·&nbsp; Use Ctrl+P → Save as PDF to export.</footer>
</div>
</body>
</html>"""

    report_dir = out / "reports" / "cmc_bispecific"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "bispecific_cmc_report.html"
    try:
        from core.reporting.report_qc_gate import run_report_qc  # noqa: PLC0415
        qc = run_report_qc(html, report_family="bispecific_cmc")
        html = qc.inject_qc_badge(html)
    except Exception:
        pass
    path.write_text(html, encoding="utf-8")
    return path


def _generate_igg_cmc_pdf(data: dict, out: Path) -> "Optional[Path]":
    """Generate IgG CMC assessment PDF report using reportlab."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        pdf_path = out / "CMC_Report.pdf"
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2.5*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        title_style  = ParagraphStyle("Title2", parent=styles["Title"], fontSize=16, spaceAfter=6)
        h2_style     = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceAfter=4)
        body_style   = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=14)
        small_style  = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#555"))

        DARK   = colors.HexColor("#1a2035")
        ACCENT = colors.HexColor("#00e5ff")
        PASS_C = colors.HexColor("#00c853")
        WARN_C = colors.HexColor("#ff9800")
        FAIL_C = colors.HexColor("#f44336")
        GRAY   = colors.HexColor("#e8ecf0")

        def _status_color(s):
            s = str(s).upper()
            if "PASS" in s: return PASS_C
            if "WARN" in s: return WARN_C
            return FAIL_C

        def _make_table(rows, widths, header_rows=1):
            t = Table(rows, colWidths=widths)
            ts = [
                ("BACKGROUND", (0,0), (-1, header_rows-1), DARK),
                ("TEXTCOLOR",  (0,0), (-1, header_rows-1), colors.white),
                ("FONTNAME",   (0,0), (-1, header_rows-1), "Helvetica-Bold"),
                ("FONTSIZE",   (0,0), (-1,-1), 9),
                ("GRID",       (0,0), (-1,-1), 0.3, GRAY),
                ("ROWBACKGROUNDS", (0, header_rows), (-1,-1), [colors.white, colors.HexColor("#f4f6fa")]),
                ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
                ("TOPPADDING", (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ]
            t.setStyle(TableStyle(ts))
            return t

        story = []
        overall = str(data.get("overall_status", "UNKNOWN")).upper()
        clinical_score = data.get("clinical_score")
        project_name = str(data.get("project_name") or "customer-vhvl")

        story.append(Paragraph("IgG CMC ", title_style))
        story.append(Paragraph("InSynBio AbEngineCore · Clinical Reference Cohort ", small_style))
        story.append(Paragraph(f"Sequence name / ID: {project_name}", small_style))
        story.append(Spacer(1, 0.3*cm))

        # Summary box
        score_txt = f"{clinical_score:.1f}/100" if isinstance(clinical_score, (int, float)) else "—"
        summary_rows = [
            ["", "", "", ""],
            [" (pI)", _fmt(data.get("pI_fab")), "GRAVY ", _fmt(data.get("GRAVY"), decimals=3)],
            ["", _fmt(data.get("instability_index")), " pH7", _fmt(data.get("net_charge_pH7"))],
            [" 9mer", _fmt(data.get("hydro_patch_max9"), decimals=3), " 7mer", _fmt(data.get("charge_patch_max7"))],
            ["", str(data.get("n_deamidation", 0)), "", str(data.get("n_isomerization", 0))],
            ["", str(data.get("n_oxidation", 0)), "", str(data.get("n_glycosylation", 0))],
        ]
        aw = A4[0] - 4*cm
        hpr_d = data.get("hpr_index") if isinstance(data.get("hpr_index"), dict) else {}
        hpr_c = (hpr_d.get("combined") or {}) if hpr_d else {}
        hpr_s = hpr_c.get("score")
        abl_pdf = data.get("ablang_score")
        summary_rows.append(
            [
                "HPR Index",
                _fmt(hpr_s, decimals=4) if hpr_s is not None else "—",
                "Humanness Index",
                _fmt(abl_pdf, decimals=3) if isinstance(abl_pdf, (int, float)) else "—",
            ]
        )

        story.append(Paragraph("§1 ", h2_style))
        story.append(_make_table(summary_rows, [aw*0.22, aw*0.28, aw*0.22, aw*0.28]))
        story.append(Spacer(1, 0.3*cm))

        # Clinical score (abref_percentile is 0–100 composite; same scale as web “Top X%” tier)
        abref_pdf = data.get("abref_percentile")
        abref_tier = "—"
        if isinstance(abref_pdf, (int, float)):
            abref_tier = f"Top {100 - int(round(float(abref_pdf)))}% of source-matched benchmark panel (release R2026.05)"
        story.append(Paragraph("§2  (Clinical Reference Cohort)", h2_style))
        score_rows = [
            [" (0–100)", "Clinical Reference Cohort ", "", ""],
            [score_txt, abref_tier, overall, "Source-matched benchmark panel (release R2026.05)"],
        ]
        story.append(_make_table(score_rows, [aw * 0.24, aw * 0.28, aw * 0.18, aw * 0.30]))
        story.append(Spacer(1, 0.3*cm))

        # Detailed Metrics & Normal Distribution
        modules = data.get("_modules", {})
        cmc_adv = modules.get("cmc_advisor", {}) if isinstance(modules, dict) else {}
        adv_metrics = cmc_adv.get("metrics", {}) if isinstance(cmc_adv, dict) else {}
        
        if adv_metrics:
            story.append(Paragraph("§3  (Clinical Reference Cohort )", h2_style))
            dist_rows = [
                ["", "", "", "", "p5", "p25", "p75", "p95"]
            ]
            for m_key, m_info in adv_metrics.items():
                m_val = _fmt(m_info.get("value"), decimals=3)
                m_band = m_info.get("percentile_band", "—")
                m_gate = m_info.get("gate", "—")
                p5 = _fmt(m_info.get("ref_p5"), decimals=3)
                p25 = _fmt(m_info.get("ref_p25"), decimals=3)
                p75 = _fmt(m_info.get("ref_p75"), decimals=3)
                p95 = _fmt(m_info.get("ref_p95"), decimals=3)
                # Translate some key names
                key_name = {
                    "pI": " (pI)", "GRAVY": "GRAVY ", "instability_index": "",
                    "net_charge_pH7": " pH7", "hydro_patch_max9": " 9mer", "charge_patch_max7": " 7mer",
                    "SAP_score": "SAP score", "Fv_charge_asymmetry": "Fv", "agg_motifs": " motif"
                }.get(m_key, m_key)
                dist_rows.append([key_name, m_val, m_band, m_gate, p5, p25, p75, p95])
            
            w_first = aw * 0.20
            w_mid = aw * 0.12
            w_small = aw * 0.10
            story.append(_make_table(dist_rows, [w_first, w_mid, w_mid, w_mid, w_small, w_small, w_small, w_small]))
            story.append(Spacer(1, 0.3*cm))

        # Client-safe engineering suggestions
        regular_block = data.get("regular_ab_developability") or {}
        safe_suggs = regular_block.get("fr_modification_suggestions", []) if isinstance(regular_block, dict) else []
        cdr_warnings = regular_block.get("cdr_warnings", []) if isinstance(regular_block, dict) else []
        story.append(Paragraph("§4 Framework Modification Advisory", h2_style))
        if safe_suggs:
            sugg_rows = [["Scope", "Target", "Priority", "Recommended action"]]
            for sugg in safe_suggs:
                sugg_rows.append([
                    sugg.get("scope", "FR-only"),
                    sugg.get("target", "—"),
                    sugg.get("priority", "—"),
                    sugg.get("recommendation", "—"),
                ])
            story.append(_make_table(sugg_rows, [aw*0.16, aw*0.22, aw*0.14, aw*0.48]))
        else:
            story.append(Paragraph("No framework-region modification is recommended from the current sequence-level review.", body_style))
        if cdr_warnings:
            story.append(Spacer(1, 0.15*cm))
            story.append(Paragraph("CDR findings are advisory only; CDR residues are not modified in this CMC workflow.", small_style))
        story.append(Spacer(1, 0.3*cm))

        # Flags
        flags = data.get("overall_flags", []) or []
        if flags:
            story.append(Paragraph("§5  / ", h2_style))
            for f in flags:
                story.append(Paragraph(f"• {f}", body_style))
            story.append(Spacer(1, 0.3*cm))

        # Disclaimer
        story.append(Paragraph(
            " CMC ，（Clinical Reference Cohort）。"
            "，。",
            small_style,
        ))

        doc.build(story)
        return pdf_path
    except Exception:
        return None


def _generate_vhh_cmc_pdf(data: dict, out: Path) -> "Optional[Path]":
    """Generate VHH CMC assessment PDF using reportlab."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        pdf_path = out / "VHH_CMC_Report.pdf"
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2.5*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=16, spaceAfter=6)
        h2_style    = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceAfter=4)
        body_style  = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=14)
        small_style = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, leading=11,
                                     textColor=colors.HexColor("#555"))

        DARK = colors.HexColor("#1a2035")
        GRAY = colors.HexColor("#e8ecf0")

        def _make_table(rows, widths):
            t = Table(rows, colWidths=widths)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1, 0), DARK),
                ("TEXTCOLOR",  (0,0), (-1, 0), colors.white),
                ("FONTNAME",   (0,0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",   (0,0), (-1,-1), 9),
                ("GRID",       (0,0), (-1,-1), 0.3, GRAY),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f4f6fa")]),
                ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
                ("TOPPADDING", (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ]))
            return t

        story = []
        metrics = data.get("metrics", {})
        aw = A4[0] - 4*cm

        story.append(Paragraph("VHH CMC ", title_style))
        story.append(Paragraph("InSynBio AbEngineCore · VHH (release R2026.05)", small_style))
        story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph("§1 VHH ", h2_style))
        m_rows = [
            ["", "", "", ""],
            [" (pI)", _fmt(metrics.get("pI")), "GRAVY", _fmt(metrics.get("GRAVY"), decimals=3)],
            ["", _fmt(metrics.get("instability_index")), " pH7", _fmt(metrics.get("net_charge_pH7"))],
            [" 9mer", _fmt(metrics.get("hydro_patch_max9"), decimals=3), "SAP score", _fmt(metrics.get("SAP_score"), decimals=3)],
            [" motif", str(metrics.get("agg_motifs", 0)), "", str(metrics.get("deamidation_sites", 0))],
            ["", str(metrics.get("oxidation_sites", 0)), "", str(metrics.get("free_cys", 0))],
        ]
        story.append(_make_table(m_rows, [aw*0.22, aw*0.28, aw*0.22, aw*0.28]))
        story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph("§2 VHH/sdAb Gate Score ", h2_style))
        adi_rows = [
            ["Gate Score", "", "", "n_warn", "n_fail"],
            [
                _fmt(data.get("adi_score"), decimals=1),
                str(data.get("adi_grade", "—")),
                str(data.get("overall_status", "—")),
                str(data.get("n_warn", 0)),
                str(data.get("n_fail", 0)),
            ],
        ]
        story.append(_make_table(adi_rows, [aw*0.2]*5))
        story.append(Spacer(1, 0.3*cm))

        # Risk flags
        risk = data.get("risk_flags") or {}
        if risk:
            story.append(Paragraph("§3 VHH (release R2026.05)", h2_style))
            flag_rows = [["", "", ""]]
            pct = data.get("percentile_ranks_vs_vhh42", {})
            for k, v in risk.items():
                flag_rows.append([k, str(v), str(pct.get(k, "—"))])
            story.append(_make_table(flag_rows, [aw*0.35, aw*0.2, aw*0.45]))
            story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph(
            " VHH CMC ， source-matched benchmark panel（release R2026.05）。。",
            small_style,
        ))

        doc.build(story)
        return pdf_path
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# CMC 1: IgG / VH+VL  vs  Clinical Reference Cohort
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/igg", response_model=JobStatus,
             summary="CMC developability for IgG / VH+VL (vs Clinical Reference Cohort)")
def cmc_igg(req: CMCIgGRequest):
    """Sync CMC IgG run."""
    job_id = f"cmc-igg-{uuid.uuid4().hex[:8]}"
    return _cmc_igg_impl(job_id, req)

@router.post("/igg/async", summary="Enqueue CMC IgG run (poll GET /jobs/{job_id})")
def cmc_igg_async(req: CMCIgGRequest):
    """Async CMC IgG run."""
    job_id = f"cmc-igg-{uuid.uuid4().hex[:8]}"
    jobs[job_id] = {"status": "queued", "progress": 0, "progress_note": "Queued — worker starting"}
    persist_job_snapshot(job_id)

    def _worker():
        try:
            _cmc_igg_impl(job_id, req)
        except Exception as e:
            jobs[job_id] = {"status": "failed", "progress": 0, "error": str(e)}
            persist_job_snapshot(job_id)

    threading.Thread(target=_worker, daemon=True).start()
    return {"job_id": job_id, "status": "queued", "poll_url": f"/jobs/{job_id}"}

def _cmc_igg_impl(job_id: str, req: CMCIgGRequest):
    jobs[job_id] = {"status": "running", "progress": 5}
    t0 = time.time()
    out = job_dir(job_id)

    # ── Structure semaphore gate ───────────────────────────────────────────────
    # If structure prediction is requested, acquire the global semaphore so only
    # one ABodyBuilder2 run proceeds at a time.  While waiting, update the job
    # progress_note with queue position so the frontend polling can display it.
    _acquired_structure_sem = False
    if req.predict_fv_structure:
        with _STRUCTURE_QUEUE_LOCK:
            _STRUCTURE_QUEUE.append(job_id)
        try:
            while True:
                # Non-blocking try first; if acquired, proceed immediately.
                if _STRUCTURE_SEM.acquire(blocking=False):
                    _acquired_structure_sem = True
                    break
                # Still waiting — compute queue position and advertise it.
                with _STRUCTURE_QUEUE_LOCK:
                    try:
                        pos = _STRUCTURE_QUEUE.index(job_id)
                    except ValueError:
                        pos = 0
                wait_est = max(pos, 1) * 90  # ~90s per structure run
                jobs[job_id].update({
                    "status": "queued",
                    "progress": 2,
                    "progress_note": (
                        f"Waiting for structure prediction slot — "
                        f"position {pos + 1} in queue (~{wait_est}s). "
                        f"The server processes one Fv structure at a time to avoid memory overflow."
                    ),
                })
                persist_job_snapshot(job_id)
                time.sleep(5)
        except Exception:
            with _STRUCTURE_QUEUE_LOCK:
                if job_id in _STRUCTURE_QUEUE:
                    _STRUCTURE_QUEUE.remove(job_id)
            raise

    try:
        if req.predict_fv_structure:
            # Announce that structure slot was granted
            with _STRUCTURE_QUEUE_LOCK:
                if job_id in _STRUCTURE_QUEUE:
                    _STRUCTURE_QUEUE.remove(job_id)
            jobs[job_id].update({
                "status": "running",
                "progress": 5,
                "progress_note": "Structure prediction slot acquired — starting Fv folding…",
            })

        from core.cmc.igg_cmc_pipeline import run_igg_cmc_pipeline

        project_name = (req.project_name or "").strip()[:100] or job_id

        payload = run_igg_cmc_pipeline(
            vh_sequence=req.vh_sequence,
            vl_sequence=req.vl_sequence,
            antibody_type=req.antibody_type,
            project_name=project_name,
            out_dir=out,
            job_id_for_urls=job_id,
            progress=jobs[job_id],
            run_structure=req.predict_fv_structure,
            smart_cmc=req.smart_cmc,
        )
        payload["smart_cmc_run"] = bool(req.smart_cmc)

        result_json = out / "result.json"
        result_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False,
                                          default=str), encoding="utf-8")
        jobs[job_id]["progress"] = 85

        report_url = None
        try:
            rp = _report("vhvl_humanization", result_json, out, req.report_format)
            if rp and rp.suffix.lower() in (".html", ".htm"):
                # Cache-bust query so repeat opens from insynbio.com/console always fetch fresh HTML.
                report_url = f"{files_url_for_path(job_id, rp)}?cb={int(time.time())}"
            elif rp and rp != result_json:
                report_url = f"{files_url_for_path(job_id, rp)}?cb={int(time.time())}"
        except Exception as _rpt_err:
            import traceback as _tb
            jobs[job_id]["report_error"] = f"Report generation failed: {_rpt_err}\n{_tb.format_exc()[:600]}"

        elapsed = round(time.time() - t0, 1)
        # Strip internal module dump from API response
        api_payload = {k: v for k, v in payload.items() if not k.startswith("_")}
        save_result(job_id, api_payload, report_url, elapsed)
        return JobStatus(job_id=job_id, status="done", progress=100,
                         elapsed_sec=elapsed, result=api_payload, report_url=report_url)

    except Exception as e:
        import traceback
        err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        jobs[job_id] = {"status": "failed", "progress": 0, "error": err}
        persist_job_snapshot(job_id)
        if threading.current_thread() is threading.main_thread():
            raise HTTPException(status_code=500, detail=err)
        return None

    finally:
        # Always release the structure semaphore if we acquired it, so the next
        # queued job can proceed even if this run crashed.
        if _acquired_structure_sem:
            _STRUCTURE_SEM.release()
        with _STRUCTURE_QUEUE_LOCK:
            if job_id in _STRUCTURE_QUEUE:
                _STRUCTURE_QUEUE.remove(job_id)


@router.get("/structure_queue", summary="Current structure-prediction queue depth")
def structure_queue_status():
    """Returns how many jobs are waiting for the structure-prediction semaphore."""
    with _STRUCTURE_QUEUE_LOCK:
        queue = list(_STRUCTURE_QUEUE)
    slot_free = _STRUCTURE_SEM._value > 0  # 1 = free, 0 = occupied
    return {
        "slot_free": slot_free,
        "queue_depth": len(queue),
        "queued_jobs": queue,
        "note": "Server allows 1 concurrent Fv structure prediction (ABodyBuilder2 ~4.5 GB).",
    }


# ─────────────────────────────────────────────────────────────────────────────
# CMC 2: Single VHH  vs  VHH clinical reference
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/vhh", response_model=JobStatus,
             summary="CMC developability for single VHH (vs VHH clinical reference)")
def cmc_vhh(req: CMCVHHRequest):
    """Sync VHH CMC run."""
    job_id = f"cmc-vhh-{uuid.uuid4().hex[:8]}"
    return _cmc_vhh_impl(job_id, req)

@router.post("/vhh/async", summary="Enqueue VHH CMC run (poll GET /jobs/{job_id})")
def cmc_vhh_async(req: CMCVHHRequest):
    """Async VHH CMC run."""
    job_id = f"cmc-vhh-{uuid.uuid4().hex[:8]}"
    jobs[job_id] = {"status": "queued", "progress": 0, "progress_note": "Queued — worker starting"}
    persist_job_snapshot(job_id)

    def _worker():
        try:
            _cmc_vhh_impl(job_id, req)
        except Exception as e:
            jobs[job_id] = {"status": "failed", "progress": 0, "error": str(e)}
            persist_job_snapshot(job_id)

    threading.Thread(target=_worker, daemon=True).start()
    return {"job_id": job_id, "status": "queued", "poll_url": f"/jobs/{job_id}"}

def _cmc_vhh_impl(job_id: str, req: CMCVHHRequest):
    jobs[job_id] = {"status": "running", "progress": 5}
    t0 = time.time()
    out = job_dir(job_id)

    try:
        from core.cmc.vhh_cmc_engine import (
            evaluate_single_vhh, load_vhh_ref, get_sdab_origin_ref
        )
        jobs[job_id]["progress"] = 20

        ref_path = get_sdab_origin_ref(getattr(req, "sdab_origin", "camelid_vhh"))
        ref_stats = load_vhh_ref(ref_path) if ref_path.exists() else {}
        seq_label = (req.project_name or "").strip()
        if seq_label.lower() in ("", "demo"):
            seq_label = job_id
        result = evaluate_single_vhh(
            name=seq_label,
            seq=req.vhh_sequence.strip().upper(),
            ref_stats=ref_stats,
            skip_percentile=not bool(ref_stats),
            origin=getattr(req, "sdab_origin", "camelid_vhh"),
        )
        result["reference_source"] = ref_path.name
        result["sdab_origin"] = getattr(req, "sdab_origin", "camelid_vhh")
        result["score_display_name"] = "VHH/sdAb Gate Score"
        result["score_method"] = "PASS/WARN/FAIL gate-discrete 4-category weighted score"
        result["score_comparability_note"] = "Not directly comparable with regular IgG ADI"
        result["structure_metric_scope"] = "sequence_proxy"
        jobs[job_id]["progress"] = 72
        try:
            from core.cmc.igg_hpr_ablang import compute_vhh_cmc_hpr_ablang

            _ha = compute_vhh_cmc_hpr_ablang(req.vhh_sequence.strip().upper())
            result["hpr_index"] = _ha.get("hpr_index")
            if isinstance(result["hpr_index"], dict):
                result["hpr_score"] = (result["hpr_index"].get("combined") or {}).get("score")
            result["hpr_error"] = _ha.get("hpr_error")
            result["ablang_score"] = _ha.get("ablang_score")
            result["ablang_error"] = _ha.get("ablang_error")
        except Exception as e:  # noqa: BLE001
            result["hpr_error"] = f"{type(e).__name__}: {e}"
            result.setdefault("ablang_score", None)
            result.setdefault("ablang_error", f"{type(e).__name__}: {e}")

        jobs[job_id]["progress"] = 75

        # ── Structure prediction (NanoBodyBuilder2) ───────────────────────────
        result["structure_requested"] = bool(req.run_structure)
        if req.run_structure:
            try:
                jobs[job_id]["progress_note"] = "Structure prediction (NanoBodyBuilder2)…"
                from core.humanization.engine import _run_nanobodybuilder2  # noqa: PLC0415
                from core.cmc.vhh_cmc_engine import compute_vhh_structural_metrics  # noqa: PLC0415

                seq_clean = req.vhh_sequence.strip().upper()
                nbb2 = _run_nanobodybuilder2(seq_clean)
                plddt = nbb2.get("plddt")
                pdb_path = nbb2.get("pdb_path")

                struct_metrics: Dict[str, Any] = {"plddt": plddt, "structure_computed": True}
                if pdb_path:
                    import shutil
                    dest_pdb = out / "VHH_NanoBodyBuilder2.pdb"
                    if str(pdb_path) != str(dest_pdb):
                        shutil.copy2(pdb_path, dest_pdb)
                    struct_metrics["pdb_url"] = f"{files_url_for_path(job_id, dest_pdb)}"
                    struct_metrics["pdb_filename"] = "VHH_NanoBodyBuilder2.pdb"

                    sasa_m = compute_vhh_structural_metrics(str(dest_pdb))
                    if not sasa_m.get("_struct_cmc_error"):
                        struct_metrics.update({k: v for k, v in sasa_m.items()
                                               if k != "_struct_cmc_error"})
                        # SAP SASA has a very different distribution from sequence-proxy SAP
                        # (VHH69 clinical: p25=0.94, p75=1.00 — nearly all clinical VHHs are near 1.0).
                        # Do NOT overwrite SAP_score with sap_sasa as it would use wrong thresholds.
                        # SAP SASA is displayed separately in the Structure section.
                        m = result.setdefault("metrics", {})
                        m["SAP_mode"] = "sasa_7mer"  # mark that structure was computed
                        # Inject psh, ppc, pnc into metrics so they affect flags/Gate Score
                        if "psh" in sasa_m: m["psh"] = sasa_m["psh"]
                        if "ppc" in sasa_m: m["ppc"] = sasa_m["ppc"]
                        if "pnc" in sasa_m: m["pnc"] = sasa_m["pnc"]
                        
                        # Recompute flags and ADI now that structure metrics are injected
                        from core.cmc.vhh_cmc_engine import compute_flags, compute_adi_vhh, adi_grade
                        result["risk_flags"] = compute_flags(m)
                        result["adi_score"] = compute_adi_vhh(result["risk_flags"])
                        result["adi_grade"] = adi_grade(result["adi_score"])
                        # Sync n_warn / n_fail / overall_status with updated flags
                        result["n_warn"] = sum(1 for v in result["risk_flags"].values() if v == "WARN")
                        result["n_fail"] = sum(1 for v in result["risk_flags"].values() if v == "FAIL")
                        result["overall_status"] = (
                            "FAIL" if result["n_fail"] > 0
                            else ("WARN" if result["n_warn"] > 0 else "PASS")
                        )
                        result["structure_metric_scope"] = "structure_enriched"
                    else:
                        struct_metrics["_struct_cmc_error"] = sasa_m["_struct_cmc_error"]
                else:
                    struct_metrics["structure_computed"] = False

                result["structure_metrics"] = struct_metrics
                jobs[job_id]["progress"] = 82
            except Exception as e:  # noqa: BLE001
                result["structure_metrics"] = {
                    "structure_computed": False,
                    "_struct_cmc_error": f"{type(e).__name__}: {e}",
                }

        # ── Smart-CMC FR suggestions (VHH / EngVH) ───────────────────────────
        result["smart_cmc_run"] = False
        result["fr_modification_suggestions"] = []

        if getattr(req, "smart_cmc", False):
            jobs[job_id]["progress_note"] = "Smart-CMC: generating FR optimization suggestions…"
            try:
                from core.cmc.vhh_fr_mutation_sites import get_vhh_fr_suggestions
                from core.cmc.candidate_cross_validator import validate_and_rank_vhh_candidates
                _vhh_seq_clean = req.vhh_sequence.strip().upper()
                vhh_suggs = get_vhh_fr_suggestions(
                    seq        = _vhh_seq_clean,
                    flags      = result.get("risk_flags", {}),
                    metrics    = result.get("metrics", {}),
                    origin     = getattr(req, "sdab_origin", "camelid_vhh"),
                    engvh_adaptation = result.get("engvh_adaptation"),
                )
                # Cross-metric validation: reject/demote candidates that worsen other miniCMC metrics
                vhh_suggs = validate_and_rank_vhh_candidates(
                    seq          = _vhh_seq_clean,
                    candidates   = vhh_suggs,
                    base_metrics = result.get("metrics", {}),
                    base_flags   = result.get("risk_flags", {}),
                )
                result["fr_modification_suggestions"] = vhh_suggs
                result["smart_cmc_run"] = True
            except Exception as _smce:
                result["smart_cmc_run"] = True   # was requested; error shown in UI
                result["smart_cmc_error"] = f"{type(_smce).__name__}: {_smce}"

        result_json = out / "result.json"
        result_json.write_text(json.dumps(result, indent=2, ensure_ascii=False,
                                          default=str), encoding="utf-8")
        jobs[job_id]["progress"] = 85

        try:
            rp = _report("vhh_humanization", result_json, out, req.report_format)
            report_url = f"{files_url_for_path(job_id, rp)}?cb={int(time.time())}"
        except Exception:
            report_url = None

        elapsed = round(time.time() - t0, 1)
        save_result(job_id, result, report_url, elapsed)
        return JobStatus(job_id=job_id, status="done", progress=100,
                         elapsed_sec=elapsed, result=result, report_url=report_url)

    except Exception as e:
        import traceback
        err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        jobs[job_id] = {"status": "failed", "progress": 0, "error": err}
        persist_job_snapshot(job_id)
        if threading.current_thread() is threading.main_thread():
            raise HTTPException(status_code=500, detail=err)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# CMC 3: Bispecific VHH-linker-VHH
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/bispecific", response_model=JobStatus,
             summary="CMC for bispecific VHH-linker-VHH construct")
def cmc_bispecific(req: CMCBispecificRequest):
    """Sync Bispecific CMC run."""
    job_id = f"cmc-bs-{uuid.uuid4().hex[:8]}"
    return _cmc_bs_impl(job_id, req)

@router.post("/bispecific/async", summary="Enqueue Bispecific CMC run (poll GET /jobs/{job_id})")
def cmc_bispecific_async(req: CMCBispecificRequest):
    """Async Bispecific CMC run."""
    job_id = f"cmc-bs-{uuid.uuid4().hex[:8]}"
    jobs[job_id] = {"status": "queued", "progress": 0, "progress_note": "Queued — worker starting"}
    persist_job_snapshot(job_id)

    def _worker():
        try:
            _cmc_bs_impl(job_id, req)
        except Exception as e:
            jobs[job_id] = {"status": "failed", "progress": 0, "error": str(e)}
            persist_job_snapshot(job_id)

    threading.Thread(target=_worker, daemon=True).start()
    return {"job_id": job_id, "status": "queued", "poll_url": f"/jobs/{job_id}"}

def _cmc_bs_impl(job_id: str, req: CMCBispecificRequest):
    jobs[job_id] = {"status": "running", "progress": 5}
    t0 = time.time()
    out = job_dir(job_id)

    try:
        from core.cmc.vhh_cmc_engine import (
            evaluate_single_vhh, load_vhh_ref, get_sdab_origin_ref
        )

        jobs[job_id]["progress"] = 15

        _origin = getattr(req, "sdab_origin", "camelid_vhh")
        ref_path = get_sdab_origin_ref(_origin)
        ref_stats = load_vhh_ref(ref_path) if ref_path.exists() else {}

        arm1 = evaluate_single_vhh(
            f"{job_id}_arm1", req.arm1_sequence.strip().upper(), ref_stats,
            origin=_origin,
        )
        arm1["reference_source"] = ref_path.name
        jobs[job_id]["progress"] = 40

        arm2 = evaluate_single_vhh(
            f"{job_id}_arm2", req.arm2_sequence.strip().upper(), ref_stats,
            origin=_origin,
        )
        arm2["reference_source"] = ref_path.name
        jobs[job_id]["progress"] = 62
        try:
            from core.cmc.igg_hpr_ablang import compute_vhh_cmc_hpr_ablang

            _h1 = compute_vhh_cmc_hpr_ablang(req.arm1_sequence.strip().upper())
            _h2 = compute_vhh_cmc_hpr_ablang(req.arm2_sequence.strip().upper())
            for k in ("hpr_index", "hpr_error", "ablang_score", "ablang_error"):
                arm1[k] = _h1.get(k)
                arm2[k] = _h2.get(k)
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
            for arm in (arm1, arm2):
                arm["hpr_error"] = err
                arm.setdefault("ablang_score", None)
                arm.setdefault("ablang_error", err)

        jobs[job_id]["progress"] = 65

        # ── Per-arm structure prediction ─────────────────────────────────────
        if req.run_structure:
            try:
                from core.humanization.engine import _run_nanobodybuilder2  # noqa: PLC0415
                from core.cmc.vhh_cmc_engine import compute_vhh_structural_metrics  # noqa: PLC0415

                def _arm_struct(arm_seq: str, arm_label: str) -> Dict[str, Any]:
                    jobs[job_id]["progress_note"] = f"NanoBodyBuilder2 — {arm_label}…"
                    nbb2 = _run_nanobodybuilder2(arm_seq.strip().upper())
                    plddt = nbb2.get("plddt")
                    pdb_src = nbb2.get("pdb_path")
                    sm: Dict[str, Any] = {"plddt": plddt, "structure_computed": True}
                    if pdb_src:
                        import shutil
                        dest = out / f"{arm_label}_NanoBodyBuilder2.pdb"
                        if str(pdb_src) != str(dest):
                            shutil.copy2(pdb_src, dest)
                        sm["pdb_url"] = files_url_for_path(job_id, dest)
                        sm["pdb_filename"] = dest.name
                        sasa_m = compute_vhh_structural_metrics(str(dest))
                        if not sasa_m.get("_struct_cmc_error"):
                            sm.update({k: v for k, v in sasa_m.items() if k != "_struct_cmc_error"})
                            # Inject into arm metrics
                            arm_m = arm_dict.setdefault("metrics", {})
                            if "psh" in sasa_m: arm_m["psh"] = sasa_m["psh"]
                            if "ppc" in sasa_m: arm_m["ppc"] = sasa_m["ppc"]
                            if "pnc" in sasa_m: arm_m["pnc"] = sasa_m["pnc"]
                            
                            # Recompute flags and ADI
                            from core.cmc.vhh_cmc_engine import compute_flags, compute_adi_vhh, adi_grade
                            arm_dict["risk_flags"] = compute_flags(arm_m)
                            arm_dict["adi_score"] = compute_adi_vhh(arm_dict["risk_flags"])
                            arm_dict["adi_grade"] = adi_grade(arm_dict["adi_score"])
                            arm_dict["n_warn"] = sum(1 for v in arm_dict["risk_flags"].values() if v == "WARN")
                            arm_dict["n_fail"] = sum(1 for v in arm_dict["risk_flags"].values() if v == "FAIL")
                            arm_dict["overall_status"] = "FAIL" if arm_dict["n_fail"] > 0 else ("WARN" if arm_dict["n_warn"] > 0 else "PASS")
                        else:
                            sm["_struct_cmc_error"] = sasa_m["_struct_cmc_error"]
                    else:
                        sm["structure_computed"] = False
                    return sm

                arm1["structure_metrics"] = _arm_struct(req.arm1_sequence, "arm1")
                jobs[job_id]["progress"] = 72
                arm2["structure_metrics"] = _arm_struct(req.arm2_sequence, "arm2")
                jobs[job_id]["progress"] = 78
            except Exception as e:  # noqa: BLE001
                arm1["structure_metrics"] = {"structure_computed": False, "_struct_cmc_error": str(e)}
                arm2["structure_metrics"] = {"structure_computed": False, "_struct_cmc_error": str(e)}

        from core.cmc.bispecific_cmc_engine import (
            compute_fusion_matrix,
            select_recommendations,
            DEFAULT_LINKERS,
        )
        from core.cmc.cmc_metrics import compute_GRAVY, compute_instability_index

        linker_req = (req.linker or "(G4S)3").strip()
        if linker_req in DEFAULT_LINKERS:
            linkers = {linker_req: DEFAULT_LINKERS[linker_req]}
        else:
            raw = "".join(c for c in linker_req.upper() if c.isalpha())
            if 4 <= len(raw) <= 80 and set(raw).issubset(set("ACDEFGHIKLMNPQRSTVWY")):
                linkers = {"custom": raw}
            else:
                linkers = dict(DEFAULT_LINKERS)

        if not req.smart_cmc:
            # Force single linker if smart_cmc is OFF
            linker_req = (req.linker or "(G4S)3").strip()
            if linker_req in DEFAULT_LINKERS:
                linkers = {linker_req: DEFAULT_LINKERS[linker_req]}
            else:
                raw = "".join(c for c in linker_req.upper() if c.isalpha())
                if 4 <= len(raw) <= 80 and set(raw).issubset(set("ACDEFGHIKLMNPQRSTVWY")):
                    linkers = {"custom": raw}
                else:
                    linkers = {"(G4S)3": DEFAULT_LINKERS["(G4S)3"]}
            fusion_rows = compute_fusion_matrix([arm1], [arm2], linkers=linkers)
            primary = fusion_rows[0]
            recs = {
                "primary": primary, "runner_up": None,
                "n_passing": 1 if primary["pi_flag"] == "pass" else 0,
                "n_warning": 1 if primary["pi_flag"] == "warn" else 0,
                "n_critical": 1 if primary["pi_flag"] == "critical" else 0,
            }
        else:
            fusion_rows = compute_fusion_matrix([arm1], [arm2], linkers=linkers)
            arm_a_dict = {arm1["name"]: arm1}
            arm_b_dict = {arm2["name"]: arm2}
            recs = select_recommendations(fusion_rows, arm_a_dict, arm_b_dict)
            primary = recs["primary"]
        fusion_seq = arm1["sequence"] + primary["linker_seq"] + arm2["sequence"]
        fusion_pi = float(primary["fusion_pi"])
        m1 = arm1.get("metrics") or {}
        m2 = arm2.get("metrics") or {}
        p1 = m1.get("pI")
        p2 = m2.get("pI")
        if p1 is not None and p2 is not None:
            pI_delta = abs(float(p1) - float(p2))
        else:
            pI_delta = None
        fusion_gravy = compute_GRAVY(fusion_seq)
        fusion_instability = compute_instability_index(fusion_seq)
        pi_flag = primary.get("pi_flag") or "pass"
        if pi_flag == "critical":
            overall_stat = "FAIL"
        elif pi_flag == "warn":
            overall_stat = "WARN"
        else:
            overall_stat = "PASS"
        flags: List[str] = []
        if recs.get("n_critical"):
            flags.append(f"{recs['n_critical']} fusion row(s) with critical ER pI (≥{8.5})")
        if recs.get("n_warning"):
            flags.append(f"{recs['n_warning']} fusion row(s) with warn-tier pI")
        linker_rationale = (
            f"SmartLink primary: {primary.get('linker')} "
            f"(fusion pI={fusion_pi:.2f}, pi_flag={pi_flag}). "
            f"Passing fusion rows: {recs.get('n_passing', 0)}."
        )
        # Heuristic ER-expression score: lower fusion pI at pH 7 → slightly better (0–1)
        try:
            er_expression_score = max(0.0, min(1.0, 1.0 - max(0.0, fusion_pi - 7.0) / 3.0))
        except Exception:  # noqa: BLE001
            er_expression_score = None

        project_label = (req.project_name or "").strip()[:100] or job_id
        payload = {
            "project_name":         project_label,
            "arm1":                 arm1,
            "arm1_target":          req.arm1_target,
            "arm2":                 arm2,
            "arm2_target":          req.arm2_target,
            "fusion_pI":            fusion_pi,
            "fusion_GRAVY":         fusion_gravy,
            "fusion_instability":   fusion_instability,
            "pI_delta":             pI_delta,
            "recommended_linker":   str(primary.get("linker", req.linker)),
            "linker_seq":           str(primary.get("linker_seq", "")),
            "linker_rationale":     linker_rationale,
            "er_expression_score":  er_expression_score,
            "overall_status":       overall_stat,
            "flags":                flags,
            "fusion_matrix_top":    fusion_rows[:12],
            "structure_requested":  bool(req.run_structure),
            "fusion_seq":           fusion_seq,
        }

        # ── Smart-CMC per-arm FR suggestions ─────────────────────────────────
        if getattr(req, "smart_cmc", False):
            payload["smart_cmc_run"] = True
            jobs[job_id]["progress_note"] = "Smart-CMC: per-arm FR suggestions…"
            try:
                from core.cmc.vhh_fr_mutation_sites import get_vhh_fr_suggestions
                from core.cmc.candidate_cross_validator import validate_and_rank_vhh_candidates
                for _arm_obj, _arm_seq in ((arm1, req.arm1_sequence), (arm2, req.arm2_sequence)):
                    _arm_seq_clean = _arm_seq.strip().upper()
                    _suggs = get_vhh_fr_suggestions(
                        seq=_arm_seq_clean,
                        flags=_arm_obj.get("risk_flags", {}),
                        metrics=_arm_obj.get("metrics", {}),
                        origin=_origin,
                        engvh_adaptation=_arm_obj.get("engvh_adaptation"),
                    )
                    _suggs = validate_and_rank_vhh_candidates(
                        seq=_arm_seq_clean,
                        candidates=_suggs,
                        base_metrics=_arm_obj.get("metrics", {}),
                        base_flags=_arm_obj.get("risk_flags", {}),
                    )
                    _arm_obj["fr_modification_suggestions"] = _suggs
                    _arm_obj["smart_cmc_run"] = True
            except Exception as _bse:
                for _arm_obj in (arm1, arm2):
                    _arm_obj.setdefault("fr_modification_suggestions", [])
                    _arm_obj["smart_cmc_run"] = True
                    _arm_obj["smart_cmc_error"] = f"{type(_bse).__name__}: {_bse}"
                payload["smart_cmc_error"] = f"{type(_bse).__name__}: {_bse}"
        else:
            payload["smart_cmc_run"] = False
            for _arm_obj in (arm1, arm2):
                _arm_obj["fr_modification_suggestions"] = []
                _arm_obj["smart_cmc_run"] = False

        result_json = out / "result.json"
        result_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False,
                                          default=str), encoding="utf-8")
        jobs[job_id]["progress"] = 88

        try:
            rp = _report("bispecific_cmc", result_json, out, req.report_format)
            report_url = f"{files_url_for_path(job_id, rp)}?cb={int(time.time())}"
        except Exception:
            report_url = None

        elapsed = round(time.time() - t0, 1)
        save_result(job_id, payload, report_url, elapsed)
        return JobStatus(job_id=job_id, status="done", progress=100,
                         elapsed_sec=elapsed, result=payload, report_url=report_url)

    except Exception as e:
        import traceback
        err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        jobs[job_id] = {"status": "failed", "progress": 0, "error": err}
        persist_job_snapshot(job_id)
        if threading.current_thread() is threading.main_thread():
            raise HTTPException(status_code=500, detail=err)
        return None


@router.post("/bispecific_pairing_score",
             summary="4-way p-AbNatiV2 pairing score for bispecific VH/VL")
def bispecific_pairing_score(req: BispecificPairingScoreRequest):
    """
    Computes p-AbNatiV2 pairing_likelihood and paired_humanness for all 4 combinations:
    cognate A (VH-A+VL-A), cognate B (VH-B+VL-B),
    mispaired AB (VH-A+VL-B), mispaired BA (VH-B+VL-A).
    Returns per-pair scores + selectivity deltas + overall pairing risk classification.
    """
    from api.models import BispecificPairingScoreRequest as _Req  # noqa
    from core.humanization.p_abnativ_layer import score_paired_humanness

    vh_a = (req.vh_a or "").strip().upper()
    vl_a = (req.vl_a or "").strip().upper()
    vh_b = (req.vh_b or "").strip().upper()
    vl_b = (req.vl_b or "").strip().upper()

    if not vh_a or not vh_b:
        raise HTTPException(status_code=422, detail="vh_a and vh_b are required.")

    pairs_def = {
        "cognate_a":    (vh_a, vl_a),
        "cognate_b":    (vh_b, vl_b),
        "mispaired_ab": (vh_a, vl_b),
        "mispaired_ba": (vh_b, vl_a),
    }

    results = {}
    for pair_id, (vh, vl) in pairs_def.items():
        if not vl:
            results[pair_id] = {"pairing_likelihood": None, "paired_humanness": None,
                                 "vh_humanness": None, "vl_humanness": None,
                                 "error": "VL not provided - skipped"}
            continue
        try:
            r = score_paired_humanness(vh, vl, seq_id=pair_id)
            results[pair_id] = {
                "pairing_likelihood": round(float(r.pairing_likelihood), 6) if r.pairing_likelihood is not None else None,
                "paired_humanness":   round(float(r.paired_humanness),   4) if r.paired_humanness   is not None else None,
                "vh_humanness":       round(float(r.vh_humanness),        4) if r.vh_humanness       is not None else None,
                "vl_humanness":       round(float(r.vl_humanness),        4) if r.vl_humanness       is not None else None,
                "error":              r.error,
            }
        except Exception as e:
            results[pair_id] = {"pairing_likelihood": None, "paired_humanness": None,
                                 "vh_humanness": None, "vl_humanness": None,
                                 "error": f"{type(e).__name__}: {e}"}

    cog_a  = results["cognate_a"].get("pairing_likelihood") or 0.0
    mis_ab = results["mispaired_ab"].get("pairing_likelihood") or 0.0
    cog_b  = results["cognate_b"].get("pairing_likelihood") or 0.0
    mis_ba = results["mispaired_ba"].get("pairing_likelihood") or 0.0

    delta_a = round(cog_a - mis_ab, 6)
    delta_b = round(cog_b - mis_ba, 6)

    if delta_a > 0.0015 and delta_b > 0.0015:
        overall_risk = "LOW"
    elif delta_a > 0.0005 or delta_b > 0.0005:
        overall_risk = "MODERATE"
    else:
        overall_risk = "HIGH"

    return {
        "pairs": results,
        "pairing_selectivity_delta_a": delta_a,
        "pairing_selectivity_delta_b": delta_b,
        "overall_pairing_risk": overall_risk,
    }

