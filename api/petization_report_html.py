"""
HTML delivery reports for internal petization API (dog/cat VH/VL).

Aligned visually and structurally with project-level caninization reports while
remaining data-driven from ``run_petization`` JSON (no prose invented for
third-party facts — competitive/patent rows are explicitly marked as program FTO).
"""

from __future__ import annotations

import html
from typing import Any, Dict, List

from Bio.SeqUtils.ProtParam import ProteinAnalysis

from core.humanization.kabat_utils import (
    CDR_RANGES_VH,
    CDR_RANGES_VL,
    cdr_span,
    get_kabat_numbering,
    is_in_cdr,
    sorted_keys,
)


_AA = set("ACDEFGHIKLMNPQRSTVWY")


def _fmt(v: Any, nd: int = 3) -> str:
    try:
        return str(round(float(v), nd))
    except Exception:
        return "—"


def _kabat_region(pos: int, chain: str) -> str:
    if chain == "VH":
        if pos <= 25:
            return "FR1"
        if pos <= 35:
            return "CDR-H1"
        if pos <= 49:
            return "FR2"
        if pos <= 65:
            return "CDR-H2"
        if pos <= 94:
            return "FR3"
        if pos <= 102:
            return "CDR-H3"
        return "FR4"
    if pos <= 23:
        return "FR1"
    if pos <= 34:
        return "CDR-L1"
    if pos <= 49:
        return "FR2"
    if pos <= 56:
        return "CDR-L2"
    if pos <= 88:
        return "FR3"
    if pos <= 97:
        return "CDR-L3"
    return "FR4"


def _cdr_map(seq: str, chain: str) -> Dict[str, str]:
    kd = get_kabat_numbering(seq) or {}
    ranges = CDR_RANGES_VH if chain == "VH" else CDR_RANGES_VL
    labels = ["H1", "H2", "H3"] if chain == "VH" else ["L1", "L2", "L3"]
    return {labels[i]: cdr_span(kd, lo, hi) for i, (lo, hi) in enumerate(ranges)}


def _input_chain_status(seq: str, generic_scan: Dict[str, Any]) -> Tuple[str, int, int, str]:
    cysteines = seq.count("C")
    ng = len((generic_scan or {}).get("n_glyc_sites") or [])
    bad = [c for c in seq if c not in _AA]
    nonstd = "None" if not bad else ", ".join(sorted(set(bad)))
    st = "PASS" if not bad else "FAIL"
    return st, cysteines, ng, nonstd


def _framework_rows(donor_seq: str, pet_seq: str, chain: str) -> str:
    d = get_kabat_numbering(donor_seq) or {}
    p = get_kabat_numbering(pet_seq) or {}
    rows: List[str] = []
    for key in sorted_keys(d):
        pos = key[0]
        if is_in_cdr(pos, chain):
            continue
        da = d.get(key)
        pa = p.get(key)
        if pa is None or da == pa:
            continue
        reg = _kabat_region(pos, chain)
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(pos))}</td>"
            f"<td>{html.escape(str(da))}</td>"
            f"<td>{html.escape(str(pa))}</td>"
            f"<td>{html.escape(reg)}</td>"
            "<td>No · No</td>"
            "</tr>"
        )
    if not rows:
        return (
            "<tr><td colspan='5' style='color:#64748b;font-style:italic'>"
            "No framework differences vs input donor (unexpected — verify numbering).</td></tr>"
        )
    return "".join(rows)


def _highlighted_chain_html(donor_seq: str, pet_seq: str, chain: str) -> str:
    d = get_kabat_numbering(donor_seq) or {}
    p = get_kabat_numbering(pet_seq) or {}
    parts: List[str] = []
    for key in sorted_keys(p):
        pos = key[0]
        paa = p.get(key)
        if not paa:
            continue
        daa = d.get(key, "")
        esc = html.escape(str(paa))
        if is_in_cdr(pos, chain):
            parts.append(f'<span style="color:#1a56db;font-weight:700">{esc}</span>')
        elif daa and daa != paa:
            parts.append(
                f'<span style="background:#fef3c7;color:#92400e;font-weight:700;border-radius:2px;padding:0 1px">{esc}</span>'
            )
        else:
            parts.append(esc)
    return "".join(parts)


def _backmutation_rows(items: Any, chain: str) -> str:
    if not items:
        return (
            f"<tr><td colspan='5' style='color:#64748b;font-style:italic'>"
            f"No recorded Vernier/back-mutations for {chain}.</td></tr>"
        )
    rows: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            rows.append(
                f"<tr><td colspan='5'>{html.escape(str(item))}</td></tr>"
            )
            continue
        pos = item.get("kabat_pos", "—")
        f = item.get("from", "—")
        t = item.get("to", "—")
        reg = _kabat_region(int(pos), chain) if str(pos).isdigit() else "FR"
        rationale = item.get("detail") or item.get("rationale") or (
            "Scaffold residue replaced with donor residue at Vernier / anchor position (structure-first graft)."
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(pos))}</td>"
            f"<td>{html.escape(str(f))}</td>"
            f"<td>{html.escape(str(t))}</td>"
            f"<td>{html.escape(reg)}</td>"
            f"<td>{html.escape(str(rationale))}</td>"
            "</tr>"
        )
    return "".join(rows)


def _surface_rows(items: Any) -> str:
    if not items:
        return "<tr><td style='color:#64748b;font-style:italic'>None</td></tr>"
    if not isinstance(items, (list, tuple)):
        return f"<tr><td>{html.escape(str(items))}</td></tr>"
    row0 = items[0]
    if isinstance(row0, dict):
        return "".join(
            f"<tr><td>{html.escape(str(x))}</td></tr>" for x in items
        )
    return "".join(f"<tr><td>{html.escape(str(x))}</td></tr>" for x in items)


def _fv_biophysical(vh: str, vl: str) -> Tuple[str, str, str]:
    if not vh or not vl:
        return "—", "—", "—"
    try:
        a = ProteinAnalysis(vh + vl)
        return (
            _fmt(a.isoelectric_point(), 2),
            _fmt(a.gravy(), 3),
            _fmt(a.instability_index(), 2),
        )
    except Exception:
        return "—", "—", "—"


def _liability_summary(scan: Dict[str, Any]) -> str:
    if not scan:
        return ""
    parts: List[str] = []
    for key, label in (
        ("deamidation_sites", "Deamidation"),
        ("isomerization_sites", "Isomerization"),
        ("oxidation_sites", "Oxidation"),
    ):
        xs = scan.get(key) or []
        if xs:
            parts.append(f"{label}: {len(xs)} site(s)")
    summ = scan.get("summary") or {}
    if summ:
        parts.append(f"Scan summary: {html.escape(str(summ))}")
    return "; ".join(parts) if parts else ""


def _species_flags_html(flags: Any) -> str:
    if not flags:
        return "<p style='font-size:12px;color:#64748b;margin-top:6px'>No species-specific flags recorded.</p>"
    out: List[str] = []
    for f in flags:
        if isinstance(f, dict):
            sev = str(f.get("severity") or "WARN").upper()
            cls = "pass" if sev == "PASS" else ("fail" if sev == "FAIL" else "warn")
            out.append(
                "<div style='margin:6px 0;font-size:12.5px'>"
                f"<span class=\"badge {cls}\">{html.escape(sev)}</span> "
                f"<strong>{html.escape(str(f.get('flag') or 'flag'))}</strong> — "
                f"{html.escape(str(f.get('detail') or ''))}</div>"
            )
        else:
            out.append(f"<div style='font-size:12px'>{html.escape(str(f))}</div>")
    return "".join(out)


def build_petization_delivery_html(
    *,
    result: Dict[str, Any],
    project_name: str,
    job_id: str,
    generated_at: str,
    strategy_requested: str,
) -> str:
    seqs = result.get("sequences") or {}
    in_vh = str(seqs.get("input_vh") or "")
    in_vl = str(seqs.get("input_vl") or "")
    vh_seq = str(seqs.get("petized_vh") or "")
    vl_seq = str(seqs.get("petized_vl") or "")
    selection = result.get("selection") or {}
    vh_sel = selection.get("vh") or {}
    vl_sel = selection.get("vl") or {}
    mutations = result.get("mutations") or {}
    cmc = result.get("cmc") or {}
    vh_c = cmc.get("vh") or {}
    vl_c = cmc.get("vl") or {}
    vh_m = vh_c.get("metrics") or {}
    vl_m = vl_c.get("metrics") or {}
    qa = result.get("_qa_audit") or {}
    sq = qa.get("structure_qc") or {}
    sq_status = str(sq.get("status") or "NOT_RUN").upper()
    sq_m = sq.get("metrics") or {}
    cdr_rmsd = sq.get("cdr_rmsd") or {}
    cdr_checks = qa.get("cdr_preservation") or {}
    vh_ce = cdr_checks.get("vh") or []
    vl_ce = cdr_checks.get("vl") or []
    cdr_ok = not vh_ce and not vl_ce

    overall = str(result.get("overall_status") or "WARN").upper()
    overall_cls = "pass" if overall == "PASS" else ("fail" if overall == "FAIL" else "warn")
    species = html.escape(str(result.get("species") or "dog"))
    strat = html.escape(str(result.get("strategy_selected") or "—"))
    strat_by = result.get("strategies_by_chain") or {}
    fr4s = html.escape(str(result.get("fr4_strategy") or "—"))

    fv_pi, fv_gravy, fv_instab = _fv_biophysical(vh_seq, vl_seq)

    vh_scan = vh_c.get("generic_scan") or {}
    vl_scan = vl_c.get("generic_scan") or {}
    st_vh, c_vh, n_vh, ns_vh = _input_chain_status(vh_seq, vh_scan)
    st_vl, c_vl, n_vl, ns_vl = _input_chain_status(vl_seq, vl_scan)

    c_vh_d = _cdr_map(in_vh, "VH")
    c_vl_d = _cdr_map(in_vl, "VL")
    c_vh_p = _cdr_map(vh_seq, "VH")
    c_vl_p = _cdr_map(vl_seq, "VL")

    cdr_table_rows: List[str] = []
    for label, ch, cd, cp in (
        ("CDR-H1", "VH", c_vh_d.get("H1"), c_vh_p.get("H1")),
        ("CDR-H2", "VH", c_vh_d.get("H2"), c_vh_p.get("H2")),
        ("CDR-H3", "VH", c_vh_d.get("H3"), c_vh_p.get("H3")),
        ("CDR-L1", "VL", c_vl_d.get("L1"), c_vl_p.get("L1")),
        ("CDR-L2", "VL", c_vl_d.get("L2"), c_vl_p.get("L2")),
        ("CDR-L3", "VL", c_vl_d.get("L3"), c_vl_p.get("L3")),
    ):
        Ld, Lp = len(cd or ""), len(cp or "")
        ident = "100%" if cd == cp else "diff"
        bdg = "pass" if ident == "100%" else "fail"
        cdr_table_rows.append(
            "<tr>"
            f"<td>{label}</td>"
            f"<td style=\"font-family:monospace;color:#1a56db;font-weight:700\">{html.escape(cd or '—')}</td>"
            f"<td>{Ld}</td>"
            f"<td style=\"font-family:monospace\">{html.escape(cp or '—')}</td>"
            f"<td>{Lp}</td>"
            f"<td>{ident}</td>"
            f"<td><span class=\"badge {bdg}\">{('PASS' if ident == '100%' else 'FAIL')}</span></td>"
            "</tr>"
        )

    cdrs_rmsd_rows: List[str] = []
    for loop in ("H1", "H2", "H3", "L1", "L2", "L3"):
        val = cdr_rmsd.get(loop)
        if isinstance(val, (int, float)):
            lim = 2.0 if loop in ("H3", "L3") else 1.5
            ok = val <= lim
            cls = "pass" if ok else "warn"
            cdrs_rmsd_rows.append(
                f"<tr><td>{loop}</td><td>{_fmt(val, 3)} Å</td>"
                f"<td><span class=\"badge {cls}\">{'PASS' if ok else 'WARN'}</span></td>"
                f"<td>Loop RMSD vs input-Fv model reference.</td></tr>"
            )
    if not cdrs_rmsd_rows:
        cdrs_rmsd_rows.append(
            "<tr><td colspan='4' style='color:#64748b;font-style:italic'>"
            "No per-CDR RMSD breakdown returned (see global RMSD row).</td></tr>"
        )

    issues = sq.get("issues") or []
    issues_html = "<br>".join(html.escape(str(x)) for x in issues) if issues else "None"

    n_bm_vh = len(mutations.get("vh_backmutations") or [])
    n_bm_vl = len(mutations.get("vl_backmutations") or [])

    def _fw_count(donor: str, pet: str, chain: str) -> int:
        d, p = get_kabat_numbering(donor) or {}, get_kabat_numbering(pet) or {}
        return sum(
            1
            for k in sorted_keys(d)
            if not is_in_cdr(k[0], chain) and d.get(k) != p.get(k) and p.get(k) is not None
        )

    n_fw_vh = _fw_count(in_vh, vh_seq, "VH")
    n_fw_vl = _fw_count(in_vl, vl_seq, "VL")

    sq_row_cls = (
        "pass"
        if sq_status == "PASS"
        else ("fail" if sq_status == "FAIL" else "warn")
    )
    sq_row_lbl = (
        "PASS"
        if sq_status == "PASS"
        else ("FAIL" if sq_status == "FAIL" else "REVIEW")
    )

    status_banner = (
        '<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:14px">'
        '<span class="overall-status">&#10003; PASS — Internal delivery checkpoint cleared</span>'
        f'<span style="font-size:12.5px;color:#475569">CDR graft verified · Structure QC: {html.escape(sq_status)} · '
        f'Overall {html.escape(overall)}</span></div>'
        if overall == "PASS" and cdr_ok
        else f'<div style="margin-bottom:12px"><span class="badge {overall_cls}" style="font-size:14px;padding:8px 14px">'
        f"Overall {html.escape(overall)}</span>"
        f' <span class="badge {"pass" if cdr_ok else "fail"}">CDR check: {"PASS" if cdr_ok else "FAIL"}</span>'
        f' <span class="badge {"pass" if sq_status == "PASS" else "warn"}">Structure: {html.escape(sq_status)}</span></div>'
    )

    advisory_blocks: List[str] = []
    if cdr_ok:
        advisory_blocks.append(
            '<div class="alert-pass"><strong>[PASS] CDR fidelity:</strong> All six CDR spans match donor input.</div>'
        )
    else:
        advisory_blocks.append(
            '<div class="alert-warn"><strong>[FAIL] CDR audit:</strong> '
            f"VH: {html.escape(str(vh_ce))} VL: {html.escape(str(vl_ce))}</div>"
        )
    if sq_status == "PASS":
        advisory_blocks.append(
            '<div class="alert-pass"><strong>[PASS] Structure QC:</strong> Phase 4.5 completed without FAIL.</div>'
        )
    elif sq_status == "NOT_RUN":
        advisory_blocks.append(
            '<div class="alert-info"><strong>[INFO] Structure QC:</strong> Not executed — rerun API with '
            "<code>run_struct_qc=true</code> for structural evidence.</div>"
        )
    else:
        advisory_blocks.append(
            f'<div class="alert-warn"><strong>[WARN] Structure QC:</strong> Status {html.escape(sq_status)}. Review metrics and issues.</div>'
        )

    for arm, c_dict in ("VH", vh_c), ("VL", vl_c):
        o = c_dict.get("overall") or "—"
        if o == "FAIL":
            advisory_blocks.append(
                f'<div class="alert-warn"><strong>[FAIL] CMC {arm}:</strong> address species or liability flags before release.</div>'
            )
        elif o == "WARN":
            advisory_blocks.append(
                f'<div class="alert-warn"><strong>[WARN] CMC {arm}:</strong> review flags below; may be acceptable with formulation monitoring.</div>'
            )

    advisory_blocks.append(
        '<div class="alert-info"><strong>[INFO] Patent / FTO:</strong> '
        "Germline pairing and framework edits must be reviewed against program claims and competitor sequences. "
        "This report does not provide legal conclusions.</div>"
    )

    css = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#f8fafc;color:#1e293b;font-size:14px;line-height:1.6}
.report-wrap{max-width:980px;margin:0 auto;padding:24px 16px}
.report-header{background:linear-gradient(135deg,#1e3a5f 0%,#2563eb 100%);color:#fff;border-radius:10px 10px 0 0;padding:28px 32px 20px}
.report-header h1{font-size:22px;font-weight:700;letter-spacing:.3px}
.report-header .subtitle{font-size:13px;opacity:.85;margin-top:4px}
.meta-bar{display:flex;flex-wrap:wrap;gap:12px;margin-top:14px}
.meta-pill{background:rgba(255,255,255,.15);border-radius:20px;padding:3px 12px;font-size:11.5px}
.provenance-block{background:#f0f4ff;border:1px solid #c7d7f7;border-radius:0 0 8px 8px;padding:10px 20px;font-size:12px;color:#334155;display:flex;flex-wrap:wrap;gap:16px;margin-bottom:18px}
.provenance-block span{white-space:nowrap}
.section{background:#fff;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:14px;overflow:hidden}
.section-header{background:#f1f5f9;border-bottom:1px solid #e2e8f0;padding:10px 18px;font-weight:700;font-size:13px;color:#1e3a5f;display:flex;align-items:center;gap:8px}
.section-body{padding:16px 18px}
.badge{display:inline-block;border-radius:12px;padding:2px 10px;font-size:11.5px;font-weight:700}
.pass{background:#dcfce7;color:#166534}.warn{background:#fef3c7;color:#92400e}.fail{background:#fee2e2;color:#991b1b}.info{background:#e0f2fe;color:#075985}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:8px}
.metric-card{border:1px solid #e2e8f0;border-radius:6px;padding:10px 14px;background:#fafafa}
.metric-label{font-size:11px;color:#64748b;margin-bottom:3px}
.metric-value{font-size:16px;font-weight:700;color:#1e293b}
.metric-sub{font-size:11px;color:#94a3b8;margin-top:2px}
table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px}
th{background:#f1f5f9;font-weight:700;padding:7px 10px;text-align:left;border-bottom:2px solid #e2e8f0;color:#334155}
td{padding:6px 10px;border-bottom:1px solid #f1f5f9;vertical-align:top}
tr:last-child td{border-bottom:none}tr:hover td{background:#f8fafc}
.seq-box{font-family:'Consolas','Courier New',monospace;font-size:12.5px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px 14px;line-height:1.8;word-break:break-all;margin-top:6px}
.alert-warn{background:#fef3c7;border-left:4px solid #f59e0b;color:#78350f;padding:10px 14px;margin:6px 0}
.alert-info{background:#e0f2fe;border-left:4px solid #0ea5e9;color:#0c4a6e;padding:10px 14px;margin:6px 0}
.alert-pass{background:#dcfce7;border-left:4px solid #22c55e;color:#14532d;padding:10px 14px;margin:6px 0}
.alert-box{border-radius:6px;padding:10px 14px;margin:6px 0;font-size:12.5px}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.highlight-box{background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;padding:12px 14px;margin-top:8px}
.divider{border:none;border-top:1px solid #e2e8f0;margin:10px 0}
.seq-legend{font-size:11px;color:#64748b;margin-top:6px}
.overall-status{display:inline-flex;align-items:center;gap:8px;padding:8px 18px;border-radius:8px;font-weight:700;font-size:15px;background:#dcfce7;color:#166534;border:2px solid #22c55e}
@media print{body{background:#fff}.report-wrap{max-width:100%;padding:8px}.section{break-inside:avoid}}
"""

    title = html.escape(f"Internal Caninization / Petization — {project_name}")
    analysis_v = html.escape(str(result.get("abenginecore_version", "petization_cli_v1.4.0")))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div class="report-wrap">
<div class="report-header">
  <h1>Internal Caninization Report ({species.upper()} VH/VL)</h1>
  <div class="subtitle">Internal API delivery · PETIZATION_STANDARD V1.2.0 · Structure QC · CMC · CDR preservation</div>
  <div class="meta-bar">
    <span class="meta-pill">Protocol: PETIZATION_STANDARD V1.2.0</span>
    <span class="meta-pill">Analysis: {analysis_v}</span>
    <span class="meta-pill">Report Format: V4.1</span>
    <span class="meta-pill">Project: {html.escape(project_name)}</span>
    <span class="meta-pill">Generated: {html.escape(generated_at)}</span>
    <span class="meta-pill">Job: {html.escape(job_id)}</span>
    <span class="meta-pill">API: POST /internal/petization/run</span>
  </div>
</div>
<div class="provenance-block">
  <span>Input strategy request: {html.escape(strategy_requested)}</span>
  <span>Strategy (resolved): {strat}</span>
  <span>VH routing: {html.escape(str(strat_by.get("vh") or "—"))}</span>
  <span>VL routing: {html.escape(str(strat_by.get("vl") or "—"))}</span>
  <span>FR4 policy: {fr4s}</span>
  <span>Scaffold: {html.escape(str(vh_sel.get("germline") or "—"))} / {html.escape(str(vl_sel.get("germline") or "—"))}</span>
</div>

<div class="section">
  <div class="section-header">§0  Overview & Overall Status</div>
  <div class="section-body">
    {status_banner}
    <div class="grid-3">
      <div class="metric-card">
        <div class="metric-label">VH germline (selected)</div>
        <div class="metric-value">{html.escape(str(vh_sel.get("germline") or "—"))}</div>
        <div class="metric-sub">Tier {html.escape(str(vh_sel.get("tier") or "—"))} · FR id {html.escape(str(vh_sel.get("fr_identity") or "—"))}%</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">VL germline (selected)</div>
        <div class="metric-value">{html.escape(str(vl_sel.get("germline") or "—"))}</div>
        <div class="metric-sub">Tier {html.escape(str(vl_sel.get("tier") or "—"))} · FR id {html.escape(str(vl_sel.get("fr_identity") or "—"))}%</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Framework differences (donor &rarr; petized)</div>
        <div class="metric-value">{n_fw_vh + n_fw_vl}</div>
        <div class="metric-sub">VH {n_fw_vh} · VL {n_fw_vl} · Back-muts VH {n_bm_vh} / VL {n_bm_vl}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Fv pI (concat)</div>
        <div class="metric-value">{fv_pi}</div>
        <div class="metric-sub">ProteinAnalysis on VH+VL concatenate</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Fv GRAVY / Instability</div>
        <div class="metric-value">{fv_gravy}</div>
        <div class="metric-sub">Instability {fv_instab}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Structure QC</div>
        <div class="metric-value">{html.escape(sq_status)}</div>
        <div class="metric-sub">pLDDT {_fmt(sq_m.get("plddt"), 2)} · RMSD {_fmt(sq_m.get("global_rmsd"), 3)} Å · angle {_fmt(sq_m.get("vh_vl_angle_deg"), 2)}°</div>
      </div>
    </div>
    <div class="highlight-box">
      <strong>Design note:</strong> This report is generated only from the internal petization engine JSON.
      Competitive naming, clinical precedence tables, and antigen-contact claims are intentionally omitted unless present in upstream project data — add them via project memoranda linked to this <code>job_id</code>.
    </div>
  </div>
</div>

<div class="section">
  <div class="section-header">§1  Input QC — Sequence validation (petized output)</div>
  <div class="section-body">
    <table>
      <tr><th>Chain</th><th>Length</th><th>Cys count</th><th>N-glyc (NxS/T)</th><th>Non-standard AA</th><th>Status</th></tr>
      <tr>
        <td>VH</td><td>{len(vh_seq)} aa</td><td>{c_vh}</td><td>{n_vh}</td><td>{html.escape(ns_vh)}</td>
        <td><span class="badge {st_vh.lower() if st_vh in ('PASS','FAIL') else 'warn'}">{st_vh}</span></td>
      </tr>
      <tr>
        <td>VL</td><td>{len(vl_seq)} aa</td><td>{c_vl}</td><td>{n_vl}</td><td>{html.escape(ns_vl)}</td>
        <td><span class="badge {st_vl.lower() if st_vl in ('PASS','FAIL') else 'warn'}">{st_vl}</span></td>
      </tr>
    </table>
    <hr class="divider">
    <strong>Scaffold registry selection</strong>
    <table>
      <tr><th>Chain</th><th>Germline</th><th>Tier</th><th>FR identity (%)</th><th>CDR length match</th><th>Registry source</th></tr>
      <tr>
        <td>VH</td>
        <td>{html.escape(str(vh_sel.get("germline") or "—"))}</td>
        <td>{html.escape(str(vh_sel.get("tier") or "—"))}</td>
        <td>{html.escape(str(vh_sel.get("fr_identity") or "—"))}</td>
        <td>{html.escape(str(vh_sel.get("length_match")))}</td>
        <td>{html.escape(str(vh_sel.get("source") or "dog/cat scaffold JSON"))}</td>
      </tr>
      <tr>
        <td>VL</td>
        <td>{html.escape(str(vl_sel.get("germline") or "—"))}</td>
        <td>{html.escape(str(vl_sel.get("tier") or "—"))}</td>
        <td>{html.escape(str(vl_sel.get("fr_identity") or "—"))}</td>
        <td>{html.escape(str(vl_sel.get("length_match")))}</td>
        <td>{html.escape(str(vl_sel.get("source") or "dog/cat scaffold JSON"))}</td>
      </tr>
    </table>
  </div>
</div>

<div class="section">
  <div class="section-header">§2  CDR Segments — Donor preservation</div>
  <div class="section-body">
    <table>
      <tr><th>CDR</th><th>Donor (input)</th><th>Len</th><th>Petized</th><th>Len</th><th>Identity</th><th>Status</th></tr>
      {''.join(cdr_table_rows)}
    </table>
  </div>
</div>

<div class="section">
  <div class="section-header">§3  Scaffold selection &amp; Vernier / back-mutations</div>
  <div class="section-body">
    <div class="two-col">
      <div>
        <strong>VH Vernier / back-mutations (scaffold &rarr; donor)</strong>
        <table>
          <tr><th>Kabat</th><th>Scaffold</th><th>Donor</th><th>Region</th><th>Rationale</th></tr>
          {_backmutation_rows(mutations.get("vh_backmutations"), "VH")}
        </table>
      </div>
      <div>
        <strong>VL Vernier / back-mutations</strong>
        <table>
          <tr><th>Kabat</th><th>Scaffold</th><th>Donor</th><th>Region</th><th>Rationale</th></tr>
          {_backmutation_rows(mutations.get("vl_backmutations"), "VL")}
        </table>
      </div>
    </div>
    <hr class="divider">
    <strong>Surface reshaping mutations</strong> (if any)
    <div class="two-col" style="margin-top:8px">
      <div><table><tr><th>VH</th></tr>{_surface_rows(mutations.get("vh_surface_reshaping"))}</table></div>
      <div><table><tr><th>VL</th></tr>{_surface_rows(mutations.get("vl_surface_reshaping"))}</table></div>
    </div>
  </div>
</div>

<div class="section">
  <div class="section-header">§3.5  Structure QC — pLDDT, RMSD, packing</div>
  <div class="section-body">
    <table>
      <tr><th>Metric</th><th>Value</th><th>Status</th><th>Interpretation</th></tr>
      <tr><td>Structure QC</td><td>{html.escape(sq_status)}</td><td><span class="badge {sq_row_cls}">{html.escape(sq_row_lbl)}</span></td><td>Phase 4.5 backend output.</td></tr>
      <tr><td>pLDDT</td><td>{_fmt(sq_m.get("plddt"), 2)}</td><td>—</td><td>Model confidence (tool-native scale).</td></tr>
      <tr><td>Global RMSD</td><td>{_fmt(sq_m.get("global_rmsd"), 3)} Å</td><td>—</td><td>Fv backbone deviation check.</td></tr>
      <tr><td>VH–VL packing angle</td><td>{_fmt(sq_m.get("vh_vl_angle_deg"), 2)}°</td><td>—</td><td>Orientation vs reference build.</td></tr>
    </table>
    <table style="margin-top:10px">
      <tr><th>Loop</th><th>Cα RMSD</th><th>Status</th><th>Note</th></tr>
      {''.join(cdrs_rmsd_rows)}
    </table>
    <p style="margin-top:8px;font-size:12.5px"><strong>Issues:</strong> {issues_html}</p>
  </div>
</div>

<div class="section">
  <div class="section-header">§4  CMC developability — chain scan</div>
  <div class="section-body">
    <div class="grid-3">
      <div class="metric-card">
        <div class="metric-label">VH pI / GRAVY / Instab</div>
        <div class="metric-value">{_fmt(vh_m.get("pI"), 2)} / {_fmt(vh_m.get("gravy"), 3)}</div>
        <div class="metric-sub">Instability {_fmt(vh_m.get("instability_index"), 2)} · {html.escape(str(vh_c.get("overall") or "—"))}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">VL pI / GRAVY / Instab</div>
        <div class="metric-value">{_fmt(vl_m.get("pI"), 2)} / {_fmt(vl_m.get("gravy"), 3)}</div>
        <div class="metric-sub">Instability {_fmt(vl_m.get("instability_index"), 2)} · {html.escape(str(vl_c.get("overall") or "—"))}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Fv combine (quick)</div>
        <div class="metric-value">pI {fv_pi}</div>
        <div class="metric-sub">GRAVY {fv_gravy} · Instability {fv_instab}</div>
      </div>
    </div>
    <div class="two-col" style="margin-top:12px">
      <div>
        <strong>VH liability scan</strong>
        <p style="font-size:12px;color:#475569;margin-top:6px">{html.escape(_liability_summary(vh_scan) or "—")}</p>
      </div>
      <div>
        <strong>VL liability scan</strong>
        <p style="font-size:12px;color:#475569;margin-top:6px">{html.escape(_liability_summary(vl_scan) or "—")}</p>
      </div>
    </div>
    <div class="two-col" style="margin-top:12px">
      <div>
        <strong>VH species / developability flags</strong>
        {_species_flags_html(vh_c.get("species_flags"))}
      </div>
      <div>
        <strong>VL species / developability flags</strong>
        {_species_flags_html(vl_c.get("species_flags"))}
      </div>
    </div>
  </div>
</div>

<div class="section">
  <div class="section-header">§5  Framework substitutions — petized vs donor input</div>
  <div class="section-body">
    <div class="two-col">
      <div>
        <strong>VH ({n_fw_vh} positions)</strong>
        <table>
          <tr><th>Pos</th><th>Donor</th><th>Petized</th><th>Region</th><th>NGF contact?</th></tr>
          {_framework_rows(in_vh, vh_seq, "VH")}
        </table>
      </div>
      <div>
        <strong>VL ({n_fw_vl} positions)</strong>
        <table>
          <tr><th>Pos</th><th>Donor</th><th>Petized</th><th>Region</th><th>NGF contact?</th></tr>
          {_framework_rows(in_vl, vl_seq, "VL")}
        </table>
      </div>
    </div>
    <p style="font-size:12px;color:#64748b;margin-top:8px">Antigen contact column is placeholder "No" unless a project complex/PDB is wired into the petization run for contact marking.</p>
  </div>
</div>

<div class="section">
  <div class="section-header">§6  Patent &amp; competitive differentiation (FTO checkpoint)</div>
  <div class="section-body">
    <table>
      <tr><th>Checkpoint</th><th>Owner action</th><th>Status</th></tr>
      <tr><td>Compare VH/VL germline genes vs competitor filings</td><td>Patent counsel + sequence alignment package</td><td><span class="badge info">REVIEW</span></td></tr>
      <tr><td>Back-mutation footprint vs prior art</td><td>Claim chart / file history</td><td><span class="badge info">REVIEW</span></td></tr>
      <tr><td>Fc / isotype selection</td><td>Cross-check with freedom-to-operate memo</td><td><span class="badge info">REVIEW</span></td></tr>
    </table>
    <div class="highlight-box">
      Figures naming approved veterinary antibodies are <em>not</em> auto-inserted here (external claims require verified sources). Attach program FTO tables to this job folder when available.
    </div>
  </div>
</div>

<div class="section">
  <div class="section-header">§7  Final sequences (highlighted)</div>
  <div class="section-body">
    <strong>VH — {len(vh_seq)} aa (CDR blue · FR change vs donor amber)</strong>
    <div class="seq-box">{_highlighted_chain_html(in_vh, vh_seq, "VH")}</div>
    <div class="seq-legend"><span style="color:#1a56db;font-weight:700">■ CDR</span> <span style="background:#fef3c7;color:#92400e;border-radius:2px;padding:0 3px">■</span> Framework change vs donor</div>
    <strong style="display:block;margin-top:12px">VH — plain</strong>
    <div class="seq-box" style="color:#1e3a5f">{html.escape(vh_seq)}</div>

    <strong style="display:block;margin-top:16px">VL — {len(vl_seq)} aa</strong>
    <div class="seq-box">{_highlighted_chain_html(in_vl, vl_seq, "VL")}</div>
    <strong style="display:block;margin-top:12px">VL — plain</strong>
    <div class="seq-box" style="color:#1e3a5f">{html.escape(vl_seq)}</div>

    <hr class="divider">
    <div class="two-col">
      <div>
        <strong>VH donor vs petized (pairwise)</strong>
        <div class="seq-box" style="font-size:11.5px">{_highlighted_chain_html(in_vh, vh_seq, "VH")}</div>
      </div>
      <div>
        <strong>VL donor vs petized</strong>
        <div class="seq-box" style="font-size:11.5px">{_highlighted_chain_html(in_vl, vl_seq, "VL")}</div>
      </div>
    </div>
  </div>
</div>

<div class="section">
  <div class="section-header">§8  Optional: multi-candidate comparison</div>
  <div class="section-body">
    <p style="font-size:13px">Run a second <code>/internal/petization/run</code> with baseline sequences and diff JSON; or use the project comparison HTML template. This section is intentionally single-candidate.</p>
  </div>
</div>

<div class="section">
  <div class="section-header">§9  Advisory &amp; recommendations</div>
  <div class="section-body">
    {''.join(advisory_blocks)}
  </div>
</div>

<div class="section">
  <div class="section-header">§10  Delivery checklist</div>
  <div class="section-body">
    <ul style="margin-left:18px;font-size:13px;line-height:1.7">
      <li>[ ] CDR preservation signed off (engine + Kabat spot-check)</li>
      <li>[ ] Structure QC artifact archived under job <code>{html.escape(job_id)}</code></li>
      <li>[ ] CMC flags triaged (VH/VL overall {html.escape(str(vh_c.get("overall")))} / {html.escape(str(vl_c.get("overall")))})</li>
      <li>[ ] Expression construct + signal peptide defined</li>
      <li>[ ] FTO / competitive sequence review attached</li>
    </ul>
  </div>
</div>

<div class="section">
  <div class="section-header">§11  API provenance</div>
  <div class="section-body">
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Endpoint</td><td>POST /internal/petization/run</td></tr>
      <tr><td>job_id</td><td>{html.escape(job_id)}</td></tr>
      <tr><td>Generated</td><td>{html.escape(generated_at)}</td></tr>
      <tr><td>Standard</td><td>{html.escape(str(result.get("petization_standard") or "docs/PETIZATION_STANDARD_V1.0.md"))}</td></tr>
    </table>
    <p style="margin-top:12px;font-size:11px;color:#ef4444;font-weight:700">INTERNAL ONLY — NOT FOR PUBLIC DISTRIBUTION</p>
  </div>
</div>

</div>
</body>
</html>"""
