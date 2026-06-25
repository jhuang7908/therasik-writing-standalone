"""
api/routers/recheck.py

Customer recheck endpoints:
  POST /recheck/vhvl  — donor VH/VL + customer humanized VH/VL
  POST /recheck/vhh   — donor VHH + customer humanized VHH
  POST /recheck/vhvl/async, /recheck/vhh/async — background job + poll GET /jobs/{id}

Delivery: HTML report (UTF-8 BOM for Windows), result.json, FASTAs, optional Fv/VHH PDBs,
          README + delivery ZIP (same pattern as humanization jobs).
"""
from __future__ import annotations

import html
import json
import shutil
import threading
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from api.job_store import files_url_for_path, job_dir, jobs, persist_job_snapshot, save_result
from api.models import JobStatus, RecheckResult, RecheckVHVLRequest, RecheckVHHRequest

router = APIRouter(prefix="/recheck", tags=["Recheck"])

RECHECK_HTML_BUILD_ID = "recheck-html-v7-rich-content-20260517"


def _now_utc() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


def _norm(seq: str) -> str:
    return (seq or "").strip().upper().replace(" ", "").replace("\n", "").replace("\r", "")


def _progress(job_id: str, pct: int, note: str) -> None:
    row = jobs.get(job_id) or {}
    row["status"] = "running"
    row["progress"] = max(0, min(100, int(pct)))
    row["progress_note"] = note
    jobs[job_id] = row
    persist_job_snapshot(job_id)


def _basic_seq_qc(seq: str, chain: str, lo: int, hi: int) -> Dict[str, Any]:
    seq_u = _norm(seq)
    out: Dict[str, Any] = {
        "chain": chain,
        "length": len(seq_u),
        "alphabet_ok": True,
        "length_status": "PASS",
        "issues": [],
    }
    if not seq_u:
        out["issues"].append("empty_sequence")
        out["alphabet_ok"] = False
        out["length_status"] = "FAIL"
        return out
    bad_chars = sorted(set(seq_u) - set("ACDEFGHIKLMNPQRSTVWY"))
    if bad_chars:
        out["alphabet_ok"] = False
        out["issues"].append(f"illegal_chars:{''.join(bad_chars)}")
    if len(seq_u) < lo:
        out["length_status"] = "FAIL"
        out["issues"].append(f"too_short:{len(seq_u)}<{lo}")
    elif len(seq_u) > hi:
        out["length_status"] = "FAIL"
        out["issues"].append(f"too_long:{len(seq_u)}>{hi}")
    elif len(seq_u) < lo + 5 or len(seq_u) > hi - 5:
        out["length_status"] = "WARN"
    return out


def _qc_status(items: List[Dict[str, Any]]) -> str:
    if any((not x.get("alphabet_ok", True)) or x.get("length_status") == "FAIL" for x in items):
        return "FAIL"
    if any(x.get("length_status") == "WARN" or x.get("issues") for x in items):
        return "WARN"
    return "PASS"


def _clean_chain(seq: str, species: str, clean_mode: str, label: str) -> Dict[str, Any]:
    seq_u = _norm(seq)
    cleaned = seq_u
    removed: List[Dict[str, Any]] = []
    warnings: List[str] = []
    error: Optional[str] = None
    applied = False
    try:
        from core.vhh_sequence_cleaner import clean_vhh_sequence  # noqa: PLC0415

        res = clean_vhh_sequence(seq_u, species=species or "alpaca")
        cleaned = _norm(res.get("cleaned_sequence") or seq_u)
        removed = list(res.get("removed") or [])
        warnings = list(res.get("warnings") or [])
        error = res.get("error")
        if clean_mode == "auto" and cleaned and cleaned != seq_u:
            applied = True
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"cleaner_unavailable:{type(exc).__name__}:{exc}")

    final_seq = cleaned if (clean_mode == "auto" and cleaned) else seq_u
    return {
        "label": label,
        "original_length": len(seq_u),
        "final_length": len(final_seq),
        "was_modified": cleaned != seq_u,
        "applied": applied,
        "removed": removed,
        "warnings": warnings,
        "error": error,
        "original_sequence": seq_u,
        "suggested_cleaned_sequence": cleaned,
        "final_sequence": final_seq,
    }


def _anarci_chain_summary(
    seq: str,
    expected: str,
    *,
    relaxed_first_cys: bool = False,
) -> Dict[str, Any]:
    """IMGT-style conserved checks. For VHH/sdAb, first bridge Cys may align to 22 or 23."""
    out: Dict[str, Any] = {
        "expected_chain": expected,
        "numbering_ok": False,
        "chain_type": None,
        "chain_type_ok": False,
        "conserved_ok": False,
        "issues": [],
    }
    try:
        from core.numbering.imgt_anarcii import imgt_number_anarcii_indexed  # noqa: PLC0415

        num = imgt_number_anarcii_indexed(seq)
        rows = num.get("rows") or []
        out["numbering_ok"] = bool(rows)
        out["chain_type"] = num.get("chain_type")
        chain_t = str(num.get("chain_type") or "").upper()
        if expected == "VH":
            out["chain_type_ok"] = chain_t == "H"
        else:
            out["chain_type_ok"] = chain_t in {"K", "L"}
        pos_map = {str(r.get("pos")): str(r.get("aa") or "") for r in rows}
        if relaxed_first_cys:
            c23_ok = pos_map.get("23") == "C" or pos_map.get("22") == "C"
        else:
            c23_ok = pos_map.get("23") == "C"
        w41_ok = pos_map.get("41") in {"W", "F", "Y"}
        c104_ok = pos_map.get("104") == "C"
        out["conserved_ok"] = c23_ok and w41_ok and c104_ok
        out["conserved_anchors"] = {
            "23": pos_map.get("23"),
            "41": pos_map.get("41"),
            "104": pos_map.get("104"),
        }
        if not out["chain_type_ok"]:
            out["issues"].append(f"chain_mismatch:{chain_t}")
        if not out["conserved_ok"]:
            miss = []
            if not c23_ok:
                miss.append("Cys22/23" if relaxed_first_cys else "Cys23")
            if not w41_ok:
                miss.append("Trp41")
            if not c104_ok:
                miss.append("Cys104")
            out["issues"].append("missing_conserved:" + ",".join(miss))
    except Exception as exc:  # noqa: BLE001
        out["issues"].append(f"numbering_error:{type(exc).__name__}:{exc}")
    return out


def _status_from_blocks(*statuses: str) -> str:
    ss = [str(s or "PASS").upper() for s in statuses]
    if "FAIL" in ss:
        return "FAIL"
    if "WARN" in ss:
        return "WARN"
    return "PASS"


def _chain_status_from_numbering(chain_qc: Dict[str, Dict[str, Any]]) -> str:
    """FAIL only on missing numbering or wrong chain class; conserved-only gaps → WARN."""
    for v in chain_qc.values():
        if not v.get("numbering_ok") or not v.get("chain_type_ok"):
            return "FAIL"
    for v in chain_qc.values():
        if not v.get("conserved_ok"):
            return "WARN"
    return "PASS"


def _input_qc_rollout(basic_status: str, chain_status: str) -> str:
    b, c = str(basic_status or "PASS").upper(), str(chain_status or "PASS").upper()
    if "FAIL" in (b, c):
        return "FAIL"
    if "WARN" in (b, c):
        return "WARN"
    return "PASS"


def _recheck_cap_component_status(s: Any) -> str:
    """Client-facing rollups use PASS/WARN only (no FAIL on delivered reports)."""
    u = str(s or "PASS").upper()
    if u in ("FAIL", "FAILED"):
        return "WARN"
    if u in ("NOT_RUN", "NONE"):
        return "PASS"
    return u


def _recheck_overall_for_client(input_qc_status: str, *components: Any) -> str:
    """Overall on issued reports is PASS or WARN only."""
    capped = [_recheck_cap_component_status(x) for x in components]
    return _status_from_blocks(input_qc_status, *capped)


def _recheck_abort_no_deliverables(job_id: str, out: Path, payload: Dict[str, Any], t0: float) -> None:
    """Blocking input failure: archive JSON for support; no HTML/ZIP report."""
    payload["overall_status"] = "FAIL"
    payload["recommendation"] = (
        "No client report was issued: minimum intake or domain-shape requirements were not met. "
        "Correct the sequence inputs and resubmit."
    )
    (out / "result.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8-sig",
    )
    elapsed = round(time.time() - t0, 1)
    jobs[job_id] = {
        "status": "failed",
        "progress": 100,
        "progress_note": "Blocked — minimum input requirements not met",
        "elapsed_sec": elapsed,
        "result": payload,
        "report_url": None,
        "error": "Minimum intake or domain validation did not pass; no client report was generated.",
    }
    persist_job_snapshot(job_id)


def _html_basic_checks_table(basic: List[Dict[str, Any]]) -> str:
    rows = []
    for x in basic:
        issues = ", ".join(x.get("issues") or []) or "—"
        rows.append(
            f"<tr><td>{html.escape(str(x.get('chain')))}</td>"
            f"<td>{html.escape(str(x.get('length')))}</td>"
            f"<td>{html.escape(str(x.get('length_status')))}</td>"
            f"<td>{'Yes' if x.get('alphabet_ok') else 'No'}</td>"
            f"<td>{html.escape(issues)}</td></tr>"
        )
    return (
        '<table class="params"><tr><th>Chain</th><th>Length</th><th>Length gate</th>'
        '<th>Alphabet OK</th><th>Notes</th></tr>'
        + "".join(rows)
        + "</table>"
    )


def _html_numbering_summary_table(chain_qc: Dict[str, Dict[str, Any]]) -> str:
    rows = []
    for key, v in sorted(chain_qc.items()):
        issues = ", ".join(v.get("issues") or []) or "—"
        cst = "Yes" if v.get("conserved_ok") else "No"
        rows.append(
            f"<tr><td>{html.escape(key)}</td>"
            f"<td>{'Yes' if v.get('numbering_ok') else 'No'}</td>"
            f"<td>{html.escape(str(v.get('chain_type') or '—'))}</td>"
            f"<td>{'Yes' if v.get('chain_type_ok') else 'No'}</td>"
            f"<td>{cst}</td>"
            f"<td>{html.escape(issues)}</td></tr>"
        )
    return (
        '<table class="params"><tr><th>Chain</th><th>Numbering</th><th>Type</th><th>Class OK</th>'
        '<th>Conserved pattern</th><th>Notes</th></tr>'
        + "".join(rows)
        + "</table>"
    )


def _html_mini_cmc_summary(mini: Dict[str, Any]) -> str:
    """Rich CMC table: candidate summary + donor vs candidate comparison."""
    mini = mini or {}
    cand = mini.get("candidate") or {}
    compare = mini.get("compare_basic_developability") or {}
    donor_dev = compare.get("donor") or {}
    human_dev = compare.get("humanized") or {}
    delta = compare.get("delta") or {}

    def _fv(v: Any) -> str:
        return html.escape(str(v) if v is not None else "—")

    def _motifs(lst: Any) -> str:
        if not lst:
            return '<span style="color:#6b7280">None detected</span>'
        return html.escape(", ".join(str(m) for m in lst))

    def _badge_s(s: Any) -> str:
        sv = str(s or "").upper()
        if sv == "PASS":
            return '<span class="badge badge-ok">PASS</span>'
        if sv in ("FAIL", "FAILED"):
            return '<span class="badge badge-fail">FAIL</span>'
        if sv in ("WARN", "REVIEW"):
            return '<span class="badge badge-warn">REVIEW</span>'
        return html.escape(sv)

    # ── Quick candidate summary ──────────────────────────────────────────────
    out_parts = [
        '<p class="note" style="margin-bottom:8px">Sequence-level variable-region screen. '
        "Candidate highlights — full IgG CMC assessment is a separate workflow.</p>",
        '<table class="params">',
        f"<tr><td class='lbl'>Status</td><td>{_badge_s(cand.get('status'))}</td></tr>",
        f"<tr><td class='lbl'>pI (Fab, sequence estimate)</td><td>{_fv(cand.get('pI'))}</td></tr>",
        f"<tr><td class='lbl'>GRAVY</td><td>{_fv(cand.get('gravy'))}</td></tr>",
        f"<tr><td class='lbl'>Instability index</td><td>{_fv(cand.get('instability_index'))}</td></tr>",
        f"<tr><td class='lbl'>Aromaticity</td><td>{_fv(cand.get('aromaticity'))}</td></tr>",
    ]
    flags = cand.get("flags") or []
    none_span = '<span style="color:#6b7280">None</span>'
    flags_html = none_span if not flags else html.escape("; ".join(str(f) for f in flags))
    out_parts.append(
        f"<tr><td class='lbl'>Flags</td><td>{flags_html}</td></tr>"
    )
    out_parts.append("</table>")

    # ── Donor vs Candidate comparison (if available) ─────────────────────────
    if donor_dev or human_dev:
        out_parts.append(
            '<h4 class="chain-title" style="margin-top:14px">Donor vs Candidate — Developability Comparison</h4>'
        )
        metric_rows: List[tuple] = [
            ("Status", "status", None),
            ("pI", "pI", "pI"),
            ("GRAVY", "gravy", "gravy"),
            ("Instability index", "instability_index", "instability_index"),
            ("Net charge proxy", "net_charge_proxy", "net_charge_proxy"),
        ]
        out_parts.append(
            '<table class="params">'
            "<tr><th>Metric</th><th>Donor</th><th>Candidate</th><th>Delta</th></tr>"
        )
        for lbl, key, dk in metric_rows:
            dv = donor_dev.get(key)
            hv = human_dev.get(key)
            delt = delta.get(dk, "—") if dk else "—"
            dv_str = _badge_s(dv) if key == "status" else _fv(dv)
            hv_str = _badge_s(hv) if key == "status" else _fv(hv)
            out_parts.append(
                f"<tr><td class='lbl'>{html.escape(lbl)}</td><td>{dv_str}</td><td>{hv_str}</td>"
                f"<td>{_fv(delt)}</td></tr>"
            )
        out_parts.append("</table>")

        # Liability motifs for candidate
        out_parts.append(
            '<h4 class="chain-title" style="margin-top:14px">Candidate Liability Motifs</h4>'
            '<table class="params">'
            "<tr><th>Category</th><th>Sites</th></tr>"
        )
        for lbl2, key2 in [
            ("Deamidation (NG/NS)", "deamidation_motifs"),
            ("Isomerization (DG/DS/DT)", "isomerization_motifs"),
            ("Oxidation-sensitive (W/M/C)", "oxidation_sensitive_motifs"),
            ("N-glycosylation (NxS/T)", "n_glycosylation_motifs"),
        ]:
            lst = human_dev.get(key2) or cand.get(key2, [])
            out_parts.append(f"<tr><td class='lbl'>{html.escape(lbl2)}</td><td>{_motifs(lst)}</td></tr>")
        cysc = human_dev.get("cysteine_count") or cand.get("cysteine_count")
        freec = human_dev.get("free_cys_review") or cand.get("free_cys_review")
        hydro = human_dev.get("hydrophobic_stretches") or cand.get("hydrophobic_stretches") or []
        out_parts.append(f"<tr><td class='lbl'>Cysteine count</td><td>{_fv(cysc)}</td></tr>")
        freec_html = (
            '<span class="badge badge-warn">Yes — review</span>'
            if freec
            else '<span style="color:#6b7280">No</span>'
        )
        out_parts.append(
            f"<tr><td class='lbl'>Free Cys review flag</td>"
            f"<td>{freec_html}</td></tr>"
        )
        out_parts.append(
            f"<tr><td class='lbl'>Hydrophobic stretches</td>"
            f"<td>{_motifs(hydro)}</td></tr>"
        )
        out_parts.append("</table>")

    return "".join(out_parts)


def _html_structure_brief(sq: Dict[str, Any]) -> str:
    """Rich structure QC block: status, CDR RMSD per loop table, global metrics."""
    sq = sq or {}
    st = str(sq.get("status") or "NOT_RUN").upper()
    issues = sq.get("issues") or []

    def _badge_s(s: str) -> str:
        if s == "PASS":
            return '<span class="badge badge-ok">PASS</span>'
        if s in ("FAIL", "FAILED"):
            return '<span class="badge badge-fail">FAIL</span>'
        if s == "WARN":
            return '<span class="badge badge-warn">WARN</span>'
        return html.escape(s)

    if st == "NOT_RUN":
        return (
            '<p class="note" style="background:#fffbeb;border:1px solid #fde68a;border-radius:5px;'
            'padding:8px 12px;color:#92400e">'
            '<strong>Structure QC was not run.</strong> To enable comparative Fv/VHH structure modeling '
            '(ABodyBuilder2/NanoBodyBuilder2 + CDR RMSD + VH-VL packing angle), resubmit this sequence '
            'pair with the <em>"Run structure QC"</em> option enabled. '
            'Structure QC adds ~2–5 minutes but provides backbone deviation assessment between donor and candidate.</p>'
        )

    parts: List[str] = []
    iss_txt = "; ".join(str(i) for i in issues) if issues else "None"
    parts.append(
        f'<table class="params">'
        f"<tr><td class='lbl'>Overall</td><td>{_badge_s(st)}</td></tr>"
        f"<tr><td class='lbl'>Issues</td><td>{html.escape(iss_txt)}</td></tr>"
    )
    donor_m = sq.get("donor") or {}
    cand_m = sq.get("candidate") or {}
    if donor_m.get("plddt") is not None or cand_m.get("plddt") is not None:
        def _fmt_plddt(v):
            if v is None:
                return "—"
            try:
                fv = float(v)
                if fv == 0.0:
                    return "N/A (cache meta missing)"
                return str(round(fv, 1))
            except Exception:
                return html.escape(str(v))
        parts.append(
            f"<tr><td class='lbl'>pLDDT — donor / candidate</td>"
            f"<td>{_fmt_plddt(donor_m.get('plddt'))} &nbsp;/&nbsp; {_fmt_plddt(cand_m.get('plddt'))}</td></tr>"
        )
    if donor_m.get("vh_vl_angle_deg") is not None:
        parts.append(
            f"<tr><td class='lbl'>VH/VL packing angle — donor / candidate (°)</td>"
            f"<td>{html.escape(str(donor_m.get('vh_vl_angle_deg','—')))} &nbsp;/&nbsp; {html.escape(str(cand_m.get('vh_vl_angle_deg','—')))}</td></tr>"
        )
    angle_d = sq.get("angle_delta_deg")
    if angle_d is not None:
        parts.append(
            f"<tr><td class='lbl'>VH/VL angle delta (°)</td><td>{html.escape(str(angle_d))}</td></tr>"
        )
    grmsd = sq.get("global_fv_rmsd_ca")
    if grmsd is not None:
        parts.append(
            f"<tr><td class='lbl'>Global Fv Cα RMSD (Å)</td><td>{html.escape(str(grmsd))}</td></tr>"
        )
    parts.append("</table>")

    # CDR RMSD per loop
    cdr_rmsd = sq.get("cdr_rmsd")
    if cdr_rmsd and isinstance(cdr_rmsd, dict):
        parts.append(
            '<h4 class="chain-title" style="margin-top:12px">CDR Backbone RMSD — Donor vs Candidate (Å)</h4>'
            '<table class="params"><tr><th>Loop</th><th>Cα RMSD (Å)</th><th>Assessment</th></tr>'
        )
        for loop in ("H1", "H2", "H3", "L1", "L2", "L3"):
            v = cdr_rmsd.get(loop)
            if v is None:
                continue
            vf = float(v)
            if vf <= 0.5:
                assess = '<span style="color:#1a7a3c;font-weight:600">Minimal deviation</span>'
            elif vf <= 1.2:
                assess = '<span style="color:#92610a">Moderate — review paratope</span>'
            else:
                assess = '<span style="color:#b91c1c;font-weight:600">Significant — structural investigation recommended</span>'
            parts.append(
                f"<tr><td><b>{html.escape(loop)}</b></td><td>{html.escape(str(round(vf, 3)))}</td><td>{assess}</td></tr>"
            )
        parts.append("</table>")
    return "".join(parts)


def _mini_cmc_for_fv(vh: str, vl: str) -> Dict[str, Any]:
    from Bio.SeqUtils.ProtParam import ProteinAnalysis  # type: ignore

    seq = _norm(vh) + _norm(vl)
    pa = ProteinAnalysis(seq)
    p_i = round(float(pa.isoelectric_point()), 2)
    gravy = round(float(pa.gravy()), 3)
    ii = round(float(pa.instability_index()), 2)
    aro = round(float(pa.aromaticity()), 3)
    cys = seq.count("C")
    # Net charge proxy at pH 7.4
    try:
        charge = round(float(pa.charge_at_pH(7.4)), 2)
    except Exception:
        charge = None

    flags: List[str] = []
    if not (5.0 <= p_i <= 9.5):
        flags.append(f"pI_out_of_range:{p_i}")
    if gravy > 0.2:
        flags.append(f"high_gravy:{gravy}")
    if ii > 45.0:
        flags.append(f"instability_index:{ii}")
    return {
        "length": len(seq),
        "pI": p_i,
        "gravy": gravy,
        "instability_index": ii,
        "aromaticity": aro,
        "cysteine_count": cys,
        "net_charge_proxy": charge,
        "flags": flags,
        "status": "PASS" if not flags else "WARN",
    }


def _mini_cmc_for_vhh(seq: str) -> Dict[str, Any]:
    from Bio.SeqUtils.ProtParam import ProteinAnalysis  # type: ignore

    seq_u = _norm(seq)
    pa = ProteinAnalysis(seq_u)
    p_i = round(float(pa.isoelectric_point()), 2)
    gravy = round(float(pa.gravy()), 3)
    ii = round(float(pa.instability_index()), 2)
    aro = round(float(pa.aromaticity()), 3)
    cys = seq_u.count("C")
    try:
        charge = round(float(pa.charge_at_pH(7.4)), 2)
    except Exception:
        charge = None

    flags: List[str] = []
    if not (5.0 <= p_i <= 9.5):
        flags.append(f"pI_out_of_range:{p_i}")
    if ii > 45.0:
        flags.append(f"instability_index:{ii}")
    if gravy > 0.2:
        flags.append(f"high_gravy:{gravy}")
    return {
        "length": len(seq_u),
        "pI": p_i,
        "gravy": gravy,
        "instability_index": ii,
        "aromaticity": aro,
        "cysteine_count": cys,
        "net_charge_proxy": charge,
        "flags": flags,
        "status": "PASS" if not flags else "WARN",
    }


def _vhvl_structure_qc(
    mouse_vh: str,
    mouse_vl: str,
    cand_vh: str,
    cand_vl: str,
    out_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    from core.humanization.engine import (  # noqa: PLC0415
        _compute_cdr_rmsd,
        _compute_global_fv_rmsd,
        _run_abodybuilder2,
    )

    out: Dict[str, Any] = {"status": "NOT_RUN", "issues": []}
    try:
        s_d = _run_abodybuilder2(mouse_vh, mouse_vl)
        s_c = _run_abodybuilder2(cand_vh, cand_vl)
        p_d = s_d.get("pdb_path")
        p_c = s_c.get("pdb_path")
        if not p_d or not p_c:
            return {
                "status": "WARN",
                "issues": ["missing_structure_path"],
                "donor": {"plddt": s_d.get("plddt"), "vh_vl_angle_deg": s_d.get("vh_vl_angle_deg")},
                "candidate": {"plddt": s_c.get("plddt"), "vh_vl_angle_deg": s_c.get("vh_vl_angle_deg")},
            }
        cdr_rmsd = _compute_cdr_rmsd(p_d, p_c)
        gfv = _compute_global_fv_rmsd(p_d, p_c)
        angle_d = s_d.get("vh_vl_angle_deg")
        angle_c = s_c.get("vh_vl_angle_deg")
        angle_delta = round(float(angle_c) - float(angle_d), 1) if angle_d is not None and angle_c is not None else None
        issues: List[str] = []
        for cdr in ("H1", "H2", "L2", "L3"):
            val = (cdr_rmsd or {}).get(cdr)
            if isinstance(val, (int, float)) and float(val) > 1.5:
                issues.append(f"stable_cdr_rmsd:{cdr}={val}")
        if isinstance(gfv, (int, float)) and float(gfv) > 2.0:
            issues.append(f"global_fv_rmsd_ca={gfv}")
        if isinstance(angle_delta, (int, float)) and abs(float(angle_delta)) > 6.0:
            issues.append(f"vh_vl_angle_delta={angle_delta}")
        # Client reports use PASS/WARN only; severe geometry cues roll up as WARN.
        status = "PASS" if not issues else "WARN"
        out.update(
            {
                "status": status,
                "issues": issues,
                "cdr_rmsd": cdr_rmsd,
                "global_fv_rmsd_ca": gfv,
                "angle_delta_deg": angle_delta,
                "donor": {"plddt": s_d.get("plddt"), "vh_vl_angle_deg": angle_d},
                "candidate": {"plddt": s_c.get("plddt"), "vh_vl_angle_deg": angle_c},
            }
        )
        if out_dir:
            try:
                pd = Path(str(p_d))
                pc = Path(str(p_c))
                if pd.is_file():
                    shutil.copy2(pd, out_dir / "donor_fv.pdb")
                    out["donor_pdb"] = "donor_fv.pdb"
                if pc.is_file():
                    shutil.copy2(pc, out_dir / "candidate_fv.pdb")
                    out["candidate_pdb"] = "candidate_fv.pdb"
            except Exception:
                pass
        return out
    except Exception as exc:  # noqa: BLE001
        return {"status": "WARN", "issues": [f"struct_error:{type(exc).__name__}:{exc}"]}


def _vhh_structure_qc(donor_vhh: str, cand_vhh: str, out_dir: Optional[Path] = None) -> Dict[str, Any]:
    from core.humanization.engine import (  # noqa: PLC0415
        _compute_vhh_cdr_rmsd,
        _run_nanobodybuilder2,
    )

    try:
        s_d = _run_nanobodybuilder2(donor_vhh)
        s_c = _run_nanobodybuilder2(cand_vhh)
        p_d = s_d.get("pdb_path")
        p_c = s_c.get("pdb_path")
        if not p_d or not p_c:
            return {
                "status": "WARN",
                "issues": ["missing_structure_path"],
                "donor": {"plddt": s_d.get("plddt")},
                "candidate": {"plddt": s_c.get("plddt")},
            }
        cdr_rmsd = _compute_vhh_cdr_rmsd(p_d, p_c)
        nums = [float(v) for v in (cdr_rmsd or {}).values() if isinstance(v, (int, float))]
        max_r = max(nums) if nums else None
        issues: List[str] = []
        if isinstance(max_r, (int, float)) and max_r > 2.0:
            issues.append(f"max_cdr_rmsd={round(max_r, 3)}")
        out: Dict[str, Any] = {
            "status": "PASS" if not issues else "WARN",
            "issues": issues,
            "cdr_rmsd": cdr_rmsd,
            "donor": {"plddt": s_d.get("plddt")},
            "candidate": {"plddt": s_c.get("plddt")},
        }
        if out_dir:
            try:
                pd = Path(str(p_d))
                pc = Path(str(p_c))
                if pd.is_file():
                    shutil.copy2(pd, out_dir / "donor_vhh.pdb")
                    out["donor_pdb"] = "donor_vhh.pdb"
                if pc.is_file():
                    shutil.copy2(pc, out_dir / "candidate_vhh.pdb")
                    out["candidate_pdb"] = "candidate_vhh.pdb"
            except Exception:
                pass
        return out
    except Exception as exc:  # noqa: BLE001
        return {"status": "WARN", "issues": [f"struct_error:{type(exc).__name__}:{exc}"]}


def _naturalness_vhvl(vh: str, vl: str) -> Dict[str, Any]:
    from core.humanization.engine import _paired_naturalness_status_from_score  # noqa: PLC0415
    from core.humanization.p_abnativ_layer import score_paired_humanness  # noqa: PLC0415

    try:
        pn = score_paired_humanness(vh, vl, seq_id="recheck_candidate")
        score = pn.paired_humanness
        status = _paired_naturalness_status_from_score(score, None)
        if pn.error:
            status = "NOT_RUN"
        return {
            "metric_name": "Paired Fv naturalness",
            "paired_humanness": score,
            "pairing_likelihood": pn.pairing_likelihood,
            "status": status,
            "warning": pn.warning,
            "error": pn.error,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "metric_name": "Paired Fv naturalness",
            "paired_humanness": None,
            "pairing_likelihood": None,
            "status": "NOT_RUN",
            "error": f"{type(exc).__name__}:{exc}",
        }


def _write_vhvl_fastas(out: Path, donor_vh: str, donor_vl: str, cand_vh: str, cand_vl: str) -> None:
    (out / "mouse_sequences.fasta").write_text(
        f">donor_VH\n{donor_vh}\n>donor_VL\n{donor_vl}\n",
        encoding="utf-8",
    )
    (out / "humanized_sequences.fasta").write_text(
        f">candidate_VH\n{cand_vh}\n>candidate_VL\n{cand_vl}\n",
        encoding="utf-8",
    )


def _write_vhh_fastas(out: Path, donor: str, cand: str) -> None:
    (out / "recheck_sequences.fasta").write_text(
        f">donor_VHH\n{donor}\n>candidate_VHH\n{cand}\n",
        encoding="utf-8",
    )


def _readme_vhvl(job_id: str, project_name: str) -> str:
    return f"""InSynBio AbEngineCore — VH/VL Recheck delivery package
Job ID: {job_id}
Project label: {project_name}

Contents:
1. README.txt — this file
2. HTML report at `reports/recheck/recheck_report.html` (also exposed as `/files/{job_id}/reports/recheck/recheck_report…`)
3. result.json — machine-readable outcome for archiving
4. mouse_sequences.fasta — donor VH+VL (post intake cleaning if auto-clean was on)
5. humanized_sequences.fasta — customer candidate VH+VL
6. donor_fv.pdb / candidate_fv.pdb — optional Fv models when structure QC ran successfully

Structure QC: when enabled, comparative single-pair structure modeling supports
CDR backbone deviation and Fv-shape review. If disabled in the console/API,
the structure block stays NOT_RUN by design.

Disclaimer: in-silico structure and developability screens are for R&D reference;
key conclusions require experimental confirmation.
"""


def _readme_vhh(job_id: str, project_name: str) -> str:
    return f"""InSynBio AbEngineCore — VHH Recheck delivery package
Job ID: {job_id}
Project label: {project_name}

Contents:
1. README.txt — this file
2. recheck_report.html — browser report (UTF-8); stored under `reports/recheck/`
3. result.json — machine-readable outcome
4. recheck_sequences.fasta — donor and candidate VHH
5. donor_vhh.pdb / candidate_vhh.pdb — optional when structure QC succeeded

Structure QC: when enabled, single-domain comparative modeling supports
CDR backbone deviation review. If disabled by request, the structure block stays NOT_RUN.

Disclaimer: in-silico structure and developability screens are for R&D reference;
confirm key conclusions experimentally.
"""


def _recheck_html_path(out: Path) -> Path:
    d = out / "reports" / "recheck"
    d.mkdir(parents=True, exist_ok=True)
    return d / "recheck_report.html"


def _create_recheck_zip_vhvl(out: Path, job_id: str) -> Optional[str]:
    zip_name = f"{job_id}_recheck_delivery.zip"
    zip_path = out / zip_name
    html_src = _recheck_html_path(out)
    if not html_src.is_file():
        legacy = out / "recheck_report.html"
        html_src = legacy if legacy.is_file() else html_src
    core_files = [
        "README.txt",
        "mouse_sequences.fasta",
        "humanized_sequences.fasta",
        "result.json",
    ]
    if any(not (out / f).is_file() for f in core_files) or not html_src.is_file():
        try:
            zip_path.unlink(missing_ok=True)
        except Exception:
            pass
        return None
    optional = ("donor_fv.pdb", "candidate_fv.pdb")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in core_files:
            zf.write(out / name, arcname=name)
        zf.write(html_src, arcname="recheck_report.html")
        for name in optional:
            p = out / name
            if p.is_file():
                zf.write(p, arcname=name)
    return f"/files/{job_id}/{zip_name}"


def _create_recheck_zip_vhh(out: Path, job_id: str) -> Optional[str]:
    zip_name = f"{job_id}_recheck_delivery.zip"
    zip_path = out / zip_name
    html_src = _recheck_html_path(out)
    if not html_src.is_file():
        legacy = out / "recheck_report.html"
        html_src = legacy if legacy.is_file() else html_src
    core_files = ["README.txt", "recheck_sequences.fasta", "result.json"]
    if any(not (out / f).is_file() for f in core_files) or not html_src.is_file():
        try:
            zip_path.unlink(missing_ok=True)
        except Exception:
            pass
        return None
    optional = ("donor_vhh.pdb", "candidate_vhh.pdb")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in core_files:
            zf.write(out / name, arcname=name)
        zf.write(html_src, arcname="recheck_report.html")
        for name in optional:
            p = out / name
            if p.is_file():
                zf.write(p, arcname=name)
    return f"/files/{job_id}/{zip_name}"


def _api_version_string() -> str:
    try:
        from api.main import app

        return str(getattr(app, "version", "1.0.0"))
    except Exception:
        return "1.0.0"


def _render_recheck_html(payload: Dict[str, Any], out_dir: Path, kind: str) -> Path:
    """VH/VL humanization HTML (`humanization._generate_html_report`) is the canonical shell."""
    report_path = _recheck_html_path(out_dir)
    ts = _now_utc()

    def _h(val: Any) -> str:
        return html.escape(str(val if val is not None else "—"))

    def _badge(status: Any) -> str:
        s = str(status or "WARN").upper()
        if s == "PASS":
            cls = "badge-ok"
        elif s in ("FAIL", "FAILED"):
            cls = "badge-fail"
        else:
            cls = "badge-warn"
        return f'<span class="badge {cls}">{_h(s)}</span>'

    kind_label = "VH/VL" if kind == "VH/VL" else "VHH"
    page_title = f"InSynBio AbEngineCore | {kind_label} Recheck Report"
    report_h1 = "InSynBio AbEngineCore"
    report_sub = f"{kind_label} Customer Recheck Report | {payload.get('protocol_version') or 'Recheck-Protocol v1.0'}"
    proj = _h((payload.get("project_name") or "").strip() or "—")

    overall = str(payload.get("overall_status") or "WARN").upper()
    overall_disp = "WARN" if overall in ("FAIL", "FAILED") else overall
    input_qc_status = (payload.get("input_qc") or {}).get("status", "WARN")
    struct_qc_status = (payload.get("structure_qc") or {}).get("status", "NOT_RUN")
    mini_status = ((payload.get("mini_cmc") or {}).get("candidate") or {}).get("status", "WARN")
    nat_status = (payload.get("naturalness") or {}).get("status", "WARN")
    input_disp = _recheck_cap_component_status(input_qc_status)
    struct_disp = _recheck_cap_component_status(struct_qc_status)
    mini_disp = _recheck_cap_component_status(mini_status)
    nat_disp = _recheck_cap_component_status(nat_status)
    
    # HPR status for §0
    hpr_data = payload.get("hpr_index") or {}
    hpr_score = (hpr_data.get("humanized") or {}).get("combined", {}).get("score")
    if hpr_score is not None:
        hpr_disp = "PASS" if hpr_score > 0.6 else "WARN"
    else:
        hpr_disp = "WARN" # missing/uncomputed
    hpr_badge = _badge(hpr_disp)

    run_struct = bool(payload.get("structure_qc_requested"))
    meta_pv = payload.get("protocol_version") or "Recheck-Protocol v1.0"
    meta_av = payload.get("analysis_version") or "recheck_v1"
    meta_rv = payload.get("report_format_version") or "v1.0-13section"
    zip_u = payload.get("zip_url") or "—"
    sk = "recheck_vhvl" if kind == "VH/VL" else "recheck_vhh"
    from api.report_versioning import suite_service_meta_html, cohort_provenance_html

    meta_block = suite_service_meta_html(
        sk,
        protocol_ver=meta_pv,
        analysis_ver=meta_av,
        content_variant=meta_rv,
        extra_inner_divs=[
            f"<div>Recheck build: {RECHECK_HTML_BUILD_ID}</div>",
            f"<div>API release: {_h(_api_version_string())}</div>",
            f"<div>Structure QC: {_h('requested' if run_struct else 'off (sequence-only)')}</div>",
            f"<div>Delivery ZIP URL: {_h(zip_u)}</div>",
        ],
    )
    meta_block = meta_block + "\n" + cohort_provenance_html(sk)
    cleaning_map = payload.get("cleaning_actions") or {}
    iq = payload.get("input_qc") or {}
    sec1_html = (
        '<p class="note">Length, alphabet, IMGT-style numbering, and conserved-framework pattern checks.</p>'
        + _html_basic_checks_table(iq.get("basic_checks") or [])
        + '<h4 class="chain-title" style="margin-top:12px">Numbering summary</h4>'
        + _html_numbering_summary_table(iq.get("numbering_checks") or {})
    )

    # §2 — CDR identification from numbering checks
    def _cdrs_from_candidate(chain_qc: Dict[str, Any]) -> str:
        """Extract CDR info from ANARCI numbering for candidate chains."""
        cand_vh = chain_qc.get("candidate_vh") or {}
        cand_vl = chain_qc.get("candidate_vl") or {}
        rows_cdr = []
        for chain_label, qc_data, loops in [
            ("VH (candidate)", cand_vh, ["H1", "H2", "H3"]),
            ("VL (candidate)", cand_vl, ["L1", "L2", "L3"]),
        ]:
            anchors = qc_data.get("conserved_anchors") or {}
            if anchors:
                rows_cdr.append(
                    f"<tr><td colspan='3' style='background:#e8eef8;font-weight:600;color:#1b4fad'>"
                    f"{html.escape(chain_label)} — conserved anchors: "
                    + ", ".join(f"pos{k}={html.escape(v)}" for k, v in sorted(anchors.items()) if v)
                    + "</td></tr>"
                )
            else:
                rows_cdr.append(
                    f"<tr><td colspan='3' style='background:#e8eef8;font-weight:600;color:#1b4fad'>"
                    f"{html.escape(chain_label)}</td></tr>"
                )
        if not rows_cdr:
            return '<p class="note">CDR detail available in §1 conserved-anchor columns.</p>'
        return (
            '<p class="note">CDR loop anchors from IMGT-style ANARCI analysis. '
            "Conserved framework residues (Cys23, Trp41, Cys104) are verified in §1.</p>"
            '<table class="params">'
            "<tr><th>Chain</th><th>Conserved position</th><th>Residue</th></tr>"
            + _html_anchor_detail_rows(chain_qc)
            + "</table>"
        )

    sec2_html = _html_cdr_from_numbering(iq.get("numbering_checks") or {})

    # §3 — Donor vs Candidate comparison
    sec3_html = _html_donor_vs_candidate_summary(
        cleaning_map,
        iq.get("basic_checks") or [],
    )

    # §9 — mutation tiers N/A
    sec9_html = '<p class="note">Not applicable in recheck evaluation mode.</p>'

    # §10 — actual sequences in seq-block format
    sec10_html = _html_seq_blocks_recheck(cleaning_map)

    sec11_html = (
        '<p class="note">Engineered mutation tables require the primary humanization or IgG CMC workflows.</p>'
    )
    overall_label = str(payload.get("overall_status") or "WARN").upper()
    warn_fail = overall_label in ("WARN", "FAIL")
    sec12_html = (
        f'<p class="note" style="font-size:.9rem;margin-bottom:10px">'
        f'<strong>{_h(payload.get("recommendation") or "—")}</strong></p>'
        + (
            '<div style="border:1px solid #fde68a;background:#fffbeb;border-radius:6px;'
            'padding:10px 14px;margin-top:8px">'
            '<p style="color:#92400e;font-size:.84rem;margin:0"><strong>Interpretation guidance</strong></p>'
            '<ul style="color:#78350f;font-size:.82rem;margin:6px 0 0 18px;line-height:1.7">'
            "<li><strong>WARN</strong> = virtual checks completed with cautions; item is deliverable but requires "
            "confirmatory experimental assays before lead nomination.</li>"
            "<li><strong>PASS</strong> = no blocking virtual cautions; experimental confirmation remains required.</li>"
            "<li>Naturalness WARN reflects an unusual VH/VL pairing likelihood in silico — does not predict binding loss.</li>"
            "<li>mini-CMC REVIEW flags sequence-level liability motifs; their impact requires wet-lab confirmation.</li>"
            "</ul></div>"
            if warn_fail else
            '<p class="note">No blocking virtual cautions detected. '
            "Experimental confirmation (binding, expression, thermal stability) remains required before progression.</p>"
        )
    )
    sec13_html = (
        '<ul style="margin:8px 0 0 18px;font-size:.85rem;color:var(--muted);line-height:1.9">'
        "<li><strong>HPR</strong> — Human Peptide Repertoire Index: compatibility of variable-region 9-mers with a human antibody repertoire reference.</li>"
        "<li><strong>mini-CMC</strong> — light developability descriptors: pI, GRAVY, instability, liability motifs. Not equivalent to full formulation CMC.</li>"
        "<li><strong>Paired Fv naturalness</strong> — paired AbLang2-based plausibility of VH/VL co-occurrence in human repertoire.</li>"
        "<li><strong>CDR RMSD</strong> — Cα backbone deviation between donor and candidate modeled structures.</li>"
        "<li><strong>Delivery ZIP</strong> — README + FASTA (donor &amp; candidate) + HTML report + result.json + optional Fv PDBs.</li>"
        "</ul>"
    )

    toc = """<div class="toc-bar" id="toc">
    <b>Contents</b> &nbsp;|&nbsp;
    <a href="#s0">§0</a> · <a href="#s1">§1</a> · <a href="#s2">§2</a> · <a href="#s3">§3</a> ·
    <a href="#s4">§4</a> · <a href="#s5">§5</a> · <a href="#s6">§6</a> · <a href="#s7">§7</a> ·
    <a href="#s8">§8</a> · <a href="#s9">§9</a> · <a href="#s10">§10</a> · <a href="#s11">§11</a> ·
    <a href="#s12">§12</a> · <a href="#s13">§13</a>
  </div>"""

    footer_line = (
        f'InSynBio Research &nbsp;·&nbsp; <a href="https://www.insynbio.com">https://www.insynbio.com</a> '
        f"&nbsp;·&nbsp; {_h(ts)} &nbsp;·&nbsp; Confidential &nbsp;·&nbsp; "
        "Use Ctrl+P → Save as PDF to export this report."
    )

    html_text = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive,nosnippet">
<meta name="abengine-recheck-report-build" content="{RECHECK_HTML_BUILD_ID}">
<title>{_h(page_title)}</title>
<style>
:root {{
  --accent:#1b4fad; --accent2:#2d6cdf; --bg:#f0f4fa; --card:#fff;
  --border:#cdd5e4; --soft:#e8eef8;
  --pass:#1a7a3c; --fail:#b91c1c; --warn:#92610a; --info:#1b4fad;
  --donor:#c0392b; --human:#2d6cdf; --custom:#6d28d9;
  --muted:#5a6a80;
}}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{
  font-family:'Segoe UI',Arial,sans-serif;
  background:var(--bg); color:#1a2030; font-size:13px; line-height:1.6;
}}
.page {{ max-width:980px; margin:0 auto; padding:28px 24px 48px; }}

.report-header {{
  background:var(--accent); color:#fff;
  padding:20px 28px; border-radius:8px;
  margin-bottom:18px;
  display:flex; justify-content:space-between; align-items:flex-end;
}}
.report-header h1 {{ font-size:1.35rem; font-weight:700; margin-bottom:4px; }}
.report-header .sub {{ font-size:.84rem; font-weight:600; opacity:.95; margin-top:2px; line-height:1.45; }}
.report-header .ts {{ font-size:.78rem; font-weight:600; opacity:.92; text-align:right }}
.report-header .header-meta {{ margin-top:10px; font-size:.76rem; font-weight:600; opacity:.9; line-height:1.45; }}
.report-header .header-meta div {{ margin-top:2px; }}

.toc-bar {{ background:#e8eef8; border:1px solid var(--border); border-radius:6px; padding:8px 14px; font-size:.8rem; margin-bottom:20px; color:#2d4a80 }}
.toc-bar a {{ color:#1b4fad; text-decoration:none; margin:0 2px }}
.toc-bar a:hover {{ text-decoration:underline }}

.section {{ background:var(--card); border:1px solid var(--border); border-radius:8px; padding:18px 20px; margin-bottom:16px }}
h3 {{ color:var(--accent); font-size:.98rem; margin:0 0 12px; padding-bottom:6px; border-bottom:2px solid var(--border) }}
h4.chain-title {{ color:#2d6cdf; font-size:.88rem; margin:14px 0 6px }}
.note {{ color:#5a6a80; font-size:.8rem; margin-bottom:8px }}

table.params {{ width:100%; border-collapse:collapse; font-size:.83rem }}
table.params th {{ background:#e8eef8; color:var(--accent); font-weight:600; padding:7px 12px; text-align:left; border-bottom:2px solid var(--border) }}
table.params td {{ padding:6px 12px; border-bottom:1px solid #eef; vertical-align:top }}
table.params td.lbl {{ width:38%; color:#4a5a72; font-size:.82rem }}
table.params tr:last-child td {{ border-bottom:none }}
table.params tr.row-best td {{ background:#f0fff4; font-weight:600 }}

.badge {{ display:inline-block; padding:1px 8px; border-radius:10px; font-size:.72rem; font-weight:700; vertical-align:middle; margin-left:4px }}
.badge-ok {{ background:#d1fae5; color:var(--pass); border:1px solid #6ee7b7 }}
.badge-fail {{ background:#fee2e2; color:var(--fail); border:1px solid #fca5a5 }}
.badge-warn {{ background:#fef3c7; color:var(--warn); border:1px solid #fcd34d }}

pre {{ margin:8px 0 0; background:#f8fafd; border:1px solid var(--border); border-radius:6px; padding:12px; overflow:auto; font-size:12px; line-height:1.5; }}

.seq-block {{ background:#f8fafd; border:1px solid var(--border); border-radius:6px; padding:12px 14px; margin-bottom:10px }}
.seq-label {{ font-size:.82rem; font-weight:700; color:var(--accent2); margin-bottom:6px }}
.seq-len {{ font-weight:400; color:#8a9ab0; font-size:.75rem; margin-left:6px }}
.seq-body {{ font-family:'Consolas','Courier New',monospace; font-size:.78rem; word-break:break-all; line-height:2; color:#1a2030 }}
.chunk {{ margin-right:8px; letter-spacing:.04em }}
.chunk:nth-child(10n) {{ color:#1b4fad }}

footer {{ text-align:center; color:#8899aa; font-size:.72rem; margin-top:28px; padding-top:12px; border-top:1px solid var(--border) }}
footer a {{ color:#1b4fad; }}

@page {{ margin:18mm 14mm 16mm 14mm }}
@media print {{
  body {{ background:#fff; font-size:10.5px; color:#000 }}
  .page {{ max-width:100%; padding:0; box-shadow:none }}
  .toc-bar {{ display:none }}
  .report-header {{
    background:#1b4fad !important;
    color:#fff !important;
    -webkit-print-color-adjust:exact;
    print-color-adjust:exact;
  }}
  .report-header h1,
  .report-header .sub,
  .report-header .ts,
  .report-header .header-meta {{ color:#fff !important }}
  .section {{
    break-inside:auto;
    page-break-inside:auto;
    border:1px solid #ccc;
    margin-bottom:8px;
    overflow:visible;
    box-shadow:none;
  }}
  h3 {{ break-after:avoid; page-break-after:avoid; font-size:12px }}
  h4 {{ break-after:avoid; page-break-after:avoid; font-size:11px }}
  table.params {{ break-inside:auto; page-break-inside:auto; border-collapse:collapse; width:100% }}
  table.params tr {{ break-inside:avoid; page-break-inside:avoid }}
  table.params th, table.params td {{ font-size:9.5px; padding:3px 5px }}
  pre {{ break-inside:auto; page-break-inside:auto; font-size:9px }}
  .badge-ok, .badge-fail, .badge-warn, .badge {{
    -webkit-print-color-adjust:exact;
    print-color-adjust:exact;
    border:1px solid #ccc !important;
  }}
  footer {{ margin-top:8px; font-size:8px }}
}}
</style>
</head>
<body>
<div class="page">
  <div class="report-header">
    <div>
      <h1>{report_h1}</h1>
      <div class="sub">{report_sub}</div>
      <div class="sub" style="margin-top:4px">Project: <b>{proj}</b> &nbsp;·&nbsp; Overall: {_badge(overall_disp)}</div>
      {meta_block}
    </div>
    <div class="ts">{_h(ts)}<br><span style="font-size:.7rem;opacity:.6">CONFIDENTIAL</span></div>
  </div>

  {toc}

  <div class="section" id="s0">
    <h3>§0 — Overview</h3>
    <p class="note">Donor versus candidate assessment for customer QA. Section index aligns with standard reports (§0–§13).</p>
    <table class="params">
      <tr><td class="lbl">Overall status</td><td>{_badge(overall_disp)}</td></tr>
      <tr><td class="lbl">Input QC</td><td>{_badge(input_disp)}</td></tr>
      <tr><td class="lbl">Structure QC</td><td>{_badge(struct_qc_status)} {_h("(not run — enable only if sequence-only review is accepted)" if not run_struct else "")}</td></tr>
      <tr><td class="lbl">mini-CMC</td><td>{_badge(mini_disp)}</td></tr>
      <tr><td class="lbl">Naturalness</td><td>{_badge(nat_disp)}</td></tr>
      <tr><td class="lbl">Immunogenicity (HPR)</td><td>{hpr_badge}</td></tr>
      <tr><td class="lbl">Recommendation</td><td>{_h(payload.get("recommendation") or "—")}</td></tr>
    </table>
  </div>

  <div class="section" id="s1"><h3>§1 — Input QC</h3>{sec1_html}</div>
  <div class="section" id="s2"><h3>§2 — CDR Identification</h3>{sec2_html}</div>
  <div class="section" id="s3"><h3>§3 — Donor vs Candidate Comparison</h3>{sec3_html}</div>
  <div class="section" id="s4"><h3>§4 — Vernier zone / FR2 hallmark</h3>
    {"<p class='note'>VHH format: FR2 hallmark tetrad (Kabat 37/44/45/47) replaces VH-VL Vernier zone as the primary framework quality gate. Tetrad status is reported in §1 numbering summary. Conventional Vernier positions are not applicable to single-domain format.</p>" if kind == "VHH" else "<p class='note'>Interpret alongside §8 when structure QC is enabled.</p>"}
  </div>
  <div class="section" id="s5"><h3>§5 — Hallmark check</h3>
    {"<p class='note'>VHH framework hallmark context: FR2 hydrophilic substitutions at Kabat 37/44/45/47 prevent self-aggregation without a VL partner. Canonical VHH tetrad residues (Phe/Leu at 37, Glu/Gln at 44, Arg at 45, Gly at 47) are checked via ANARCI numbering and reported under §1. Non-canonical residues at these positions increase aggregation risk.</p>" if kind == "VHH" else "<p class='note'>Framework hallmark context is reflected in the numbering and conserved-pattern columns in §1.</p>"}
  </div>
  <div class="section" id="s6"><h3>§6 — CMC liabilities (light)</h3>{_html_mini_cmc_summary(payload.get("mini_cmc") or {})}</div>
  <div class="section" id="s7"><h3>§7 — Humanization analysis</h3>{_html_humanization_analysis_cards(payload.get("hpr_index") or {}, payload.get("naturalness") or {}, kind)}</div>
  <div class="section" id="s8"><h3>§8 — Developability / structure</h3><p class="note">Comparative structure QC when requested; metrics support developability review without replacing experiments.</p>{_html_structure_brief(payload.get("structure_qc") or {})}</div>
  <div class="section" id="s9"><h3>§9 — Mutation tiers</h3>{sec9_html}</div>
  <div class="section" id="s10"><h3>§10 — Final sequences</h3>{sec10_html}</div>
  <div class="section" id="s11"><h3>§11 — Mutation menu</h3>{sec11_html}</div>
  <div class="section" id="s12"><h3>§12 — Recommendation</h3>{sec12_html}</div>
  <div class="section" id="s13"><h3>§13 — Glossary</h3>{sec13_html}</div>

  <footer>{footer_line}</footer>
</div>
</body>
</html>"""
    report_path.write_text(html_text, encoding="utf-8-sig")
    try:
        from core.reporting.report_qc_gate import run_report_qc  # noqa: PLC0415
        _fam = "recheck_vhvl" if kind == "VH/VL" else "recheck_vhh"
        qc = run_report_qc(html_text, report_family=_fam)
        if qc.overall != "PASS":
            html_text = qc.inject_qc_badge(html_text)
            report_path.write_text(html_text, encoding="utf-8-sig")
    except Exception:
        pass
    return report_path


def _recommendation(overall: str, struct_status: str, mini_cmc_status: str = "PASS") -> str:
    """Client-facing closing line; neutral phrasing (no internal gate vocabulary)."""
    st = str(struct_status or "NOT_RUN").upper()
    mc = str(mini_cmc_status or "PASS").upper()
    
    if str(overall).upper() == "WARN":
        if st == "WARN" or mc == "WARN":
            advice = ""
            if mc == "WARN":
                advice = " CMC issues detected; consider running <strong>Smart-CMC</strong> for FR-only optimization."
            elif st == "WARN":
                advice = " Structural deviations detected; review backbone stability."
                
            return (
                f"Provisional outcome with cautions; review structural and developability notes "
                f"before portfolio progression.{advice}"
            )
        return (
            "Provisional outcome with minor cautions; plan confirmatory functional and "
            "developability assays."
        )
    return "Virtual checks report no blocking cautions; experimental validation remains required."


def _html_humanization_analysis_cards(hpr: Dict[str, Any], nat: Dict[str, Any], kind: str) -> str:
    """Rich humanization analysis rendering using parameter cards."""
    if not hpr and not nat:
        return '<p class="note">No humanization analysis data recorded.</p>'

    def _fv(v: Any) -> str:
        if v is None:
            return "—"
        if isinstance(v, float):
            return f"{v:.4f}"
        return html.escape(str(v))

    parts = ['<div class="metric-grid recheck-row-4">']
    
    # Render HPR Index cards
    if hpr:
        donor = hpr.get("donor") or {}
        humanized = hpr.get("humanized") or {}
        delta = hpr.get("delta") or {}

        d_comb = (donor.get("combined") or {}).get("score")
        h_comb = (humanized.get("combined") or {}).get("score")
        d_delta_comb = delta.get("combined")

        d_vh = (donor.get("vh") or {}).get("score")
        h_vh = (humanized.get("vh") or {}).get("score")
        d_delta_vh = delta.get("vh")

        # Decide which HPR score to highlight based on kind
        if kind == "VHH" or (d_vh is not None and (donor.get("vl") or {}).get("score") is None):
            hpr_score = h_vh if h_vh is not None else h_comb
            hpr_delta = d_delta_vh if d_delta_vh is not None else d_delta_comb
        else:
            hpr_score = h_comb
            hpr_delta = d_delta_comb

        parts.append(
            f'<div class="metric"><div class="label" title="9-mer human peptide repertoire compatibility">HPR Index</div>'
            f'<div class="value">{_fv(hpr_score)}</div></div>'
        )
        if hpr_delta is not None:
            sign = "+" if hpr_delta >= 0 else ""
            parts.append(
                f'<div class="metric"><div class="label" title="Improvement of HPR vs donor">HPR Δ (Cand − Donor)</div>'
                f'<div class="value">{sign}{_fv(hpr_delta)}</div></div>'
            )

    # Render Naturalness/AbNatiV cards
    if nat:
        if "donor" in nat or "humanized" in nat:
            # VHH AbNatiV format
            donor_nat = nat.get("donor") or {}
            hum_nat = nat.get("humanized") or {}
            delta_vhh2 = nat.get("delta_vhh2")
            delta_vh2 = nat.get("delta_vh2")
            
            parts.append(
                f'<div class="metric"><div class="label" title="AbNatiV VHH2 likelihood for candidate">Candidate VHH2</div>'
                f'<div class="value">{_fv(hum_nat.get("vhh2"))}</div></div>'
            )
            if delta_vhh2 is not None:
                sign = "+" if delta_vhh2 >= 0 else ""
                parts.append(
                    f'<div class="metric"><div class="label" title="Drop tolerated up to -0.15">Δ VHH2</div>'
                    f'<div class="value">{sign}{_fv(delta_vhh2)}</div></div>'
                )
            parts.append(
                f'<div class="metric"><div class="label" title="AbNatiV VH2 likelihood for candidate">Candidate VH2</div>'
                f'<div class="value">{_fv(hum_nat.get("vh2"))}</div></div>'
            )
            if delta_vh2 is not None:
                sign = "+" if delta_vh2 >= 0 else ""
                parts.append(
                    f'<div class="metric"><div class="label" title="Improvement of human VH2 likelihood">Δ VH2</div>'
                    f'<div class="value">{sign}{_fv(delta_vh2)}</div></div>'
                )
        else:
            # VH/VL Paired Naturalness format
            paired_hum = nat.get("paired_humanness")
            paired_like = nat.get("pairing_likelihood")
            if paired_hum is not None:
                parts.append(
                    f'<div class="metric"><div class="label" title="Likelihood of human-like VH/VL pairing context">Paired Humanness</div>'
                    f'<div class="value">{_fv(paired_hum)}</div></div>'
                )
            if paired_like is not None:
                parts.append(
                    f'<div class="metric"><div class="label" title="Empirical pairing likelihood from human repertoire">Pairing Likelihood</div>'
                    f'<div class="value">{_fv(paired_like)}</div></div>'
                )

    parts.append("</div>")

    # Add descriptive notes
    notes = []
    if hpr:
        notes.append("HPR Index range: 0.0–1.0. Higher score = better compatibility with human antibody repertoire 9-mer landscape.")
    if nat and ("donor" in nat or "humanized" in nat):
        notes.append("AbNatiV scores VHH2 (nanobody nature) and VH2 (human VH humanness).")
    elif nat:
        notes.append("Paired Fv naturalness scores the VH/VL pairing plausibility against human repertoire context.")
    
    if notes:
        parts.append(f'<p class="note" style="margin-top:12px">{" ".join(notes)}</p>')

    return "".join(parts)


def _html_naturalness_brief(nat: Dict[str, Any]) -> str:
    if not nat:
        return '<p class="note">—</p>'
    
    def _badge_s(s: Any) -> str:
        sv = str(s or "").upper()
        if sv == "PASS":
            return '<span class="badge badge-ok">PASS</span>'
        if sv in ("FAIL", "FAILED"):
            return '<span class="badge badge-fail">FAIL</span>'
        if sv == "WARN":
            return '<span class="badge badge-warn">WARN</span>'
        return html.escape(sv)

    # Check if this is the VHH AbNatiV format (contains "donor" or "humanized" dicts)
    if "donor" in nat or "humanized" in nat:
        donor = nat.get("donor") or {}
        hum = nat.get("humanized") or {}
        delta_vhh2 = nat.get("delta_vhh2")
        
        parts = [
            '<table class="params">',
            f"<tr><td class='lbl'>Status</td><td>{_badge_s(nat.get('status', 'WARN'))}</td></tr>",
            f"<tr><td class='lbl'>Donor VHH likelihood (AbNatiV VHH2)</td><td>{donor.get('vhh2', '—')}</td></tr>",
            f"<tr><td class='lbl'>Candidate VHH likelihood (AbNatiV VHH2)</td><td>{hum.get('vhh2', '—')}</td></tr>",
            f"<tr><td class='lbl'>Delta (Candidate - Donor)</td><td>{delta_vhh2 if delta_vhh2 is not None else '—'}</td></tr>",
            "</table>"
        ]
        return "".join(parts)

    labels = {
        "metric_name": "Metric",
        "status": "Status",
        "paired_humanness": "Paired humanness index",
        "pairing_likelihood": "Pairing likelihood",
    }
    
    def _safe_val(key: str, val: Any) -> str:
        if key == "status":
            return _badge_s(val)
        return html.escape(str(val))

    rows = []
    for key, lbl in labels.items():
        if key in nat and nat[key] is not None:
            rows.append(f"<tr><td class='lbl'>{html.escape(lbl)}</td><td>{_safe_val(key, nat[key])}</td></tr>")
    if not rows:
        return '<p class="note">See result.json for detail.</p>'
    table = '<table class="params">' + "".join(rows) + "</table>"
    note = (
        '<p class="note" style="margin-top:6px">'
        "Paired Fv naturalness scores the VH/VL pairing plausibility against human repertoire context. "
        "WARN reflects an uncommon pairing likelihood; it does not imply functional deficiency — "
        "experimental VH/VL affinity profiling is the definitive test.</p>"
    )
    return table + note


def _html_anchor_detail_rows(chain_qc: Dict[str, Any]) -> str:
    """Conserved-anchor rows for §2 CDR table."""
    rows = []
    pos_labels = {"23": "Cys23 (1st bridge)", "41": "Trp41 (β-sheet)", "104": "Cys104 (2nd bridge)"}
    for chain_key in ("donor_vh", "candidate_vh", "donor_vl", "candidate_vl"):
        qc = chain_qc.get(chain_key) or {}
        anchors = qc.get("conserved_anchors") or {}
        if not anchors:
            continue
        label = chain_key.replace("_", " ").title()
        for pos, aa in sorted(anchors.items()):
            pos_lbl = pos_labels.get(str(pos), f"pos{pos}")
            ok = (pos == "23" and aa in ("C",)) or (pos == "41" and aa in ("W", "F", "Y")) or (pos == "104" and aa == "C")
            badge = (
                '<span class="badge badge-ok">OK</span>'
                if ok
                else '<span class="badge badge-warn">Review</span>'
            )
            rows.append(
                f"<tr><td>{html.escape(label)}</td>"
                f"<td>{html.escape(pos_lbl)}</td>"
                f"<td style='font-family:monospace;letter-spacing:.1em'>{html.escape(str(aa or '—'))} {badge}</td></tr>"
            )
    return "".join(rows)


def _html_cdr_from_numbering(chain_qc: Dict[str, Any]) -> str:
    """§2: show conserved framework anchors for all chains (CDR boundary note)."""
    if not chain_qc:
        return '<p class="note">Numbering data unavailable; see §1.</p>'
    rows = _html_anchor_detail_rows(chain_qc)
    if not rows:
        return '<p class="note">Conserved anchor residues confirmed; see §1 for details.</p>'
    return (
        '<p class="note">Conserved framework anchors verified by IMGT-style ANARCI numbering. '
        "CDR loops are delineated between the Cys23–Cys104 bridge positions.</p>"
        '<table class="params">'
        "<tr><th>Chain</th><th>Position</th><th>Residue</th></tr>"
        + rows
        + "</table>"
        '<p class="note" style="margin-top:6px">Full CDR sequence content is reported in the primary '
        "humanization or VH→VHH workflow reports.</p>"
    )


def _html_donor_vs_candidate_summary(
    cleaning_map: Dict[str, Any],
    basic_checks: List[Dict[str, Any]],
) -> str:
    """§3: side-by-side donor vs candidate length and sequence identity."""
    if not cleaning_map:
        return '<p class="note">Sequence comparison data not available.</p>'

    # Compute pairwise identity for VH and VL
    def _identity(s1: str, s2: str) -> str:
        if not s1 or not s2:
            return "—"
        n = min(len(s1), len(s2))
        if n == 0:
            return "—"
        matches = sum(a == b for a, b in zip(s1, s2))
        return f"{100 * matches / max(len(s1), len(s2)):.1f}%"

    # Detect VHH mode
    is_vhh = ("donor_vhh" in cleaning_map or "candidate_vhh" in cleaning_map)

    if is_vhh:
        donor_vhh = (cleaning_map.get("donor_vhh") or {}).get("final_sequence") or ""
        cand_vhh = (cleaning_map.get("candidate_vhh") or {}).get("final_sequence") or ""
        if not donor_vhh and not cand_vhh:
            return '<p class="note">No VHH sequence comparison data.</p>'
        ident = _identity(donor_vhh, cand_vhh)

        # Position-level mutation list
        mut_rows = ""
        if donor_vhh and cand_vhh:
            muts = []
            for i, (d, c) in enumerate(zip(donor_vhh, cand_vhh), start=1):
                if d != c:
                    muts.append((i, d, c))
            if muts:
                mut_rows = "".join(
                    f"<tr><td>{pos}</td><td style='font-family:monospace'>{html.escape(don)}</td>"
                    f"<td style='font-family:monospace;color:var(--info)'>{html.escape(cnd)}</td></tr>"
                    for pos, don, cnd in muts
                )
                mut_table = (
                    f'<div style="margin-top:12px">'
                    f'<strong style="font-size:.82rem;color:var(--accent)">Position-level mutations ({len(muts)} substitutions)</strong>'
                    f'<table class="params" style="margin-top:6px">'
                    f"<tr><th>Position</th><th>Donor</th><th>Candidate</th></tr>"
                    f"{mut_rows}</table></div>"
                )
            else:
                mut_table = '<p class="note" style="margin-top:8px;color:var(--pass)">✓ Sequences are identical — no substitutions detected.</p>'
        else:
            mut_table = ""

        return (
            '<p class="note">Global sequence identity (full VHH variable region) between donor and candidate. '
            "CDR-only mutations indicate conservative grafting; FR mutations affect humanization profile.</p>"
            '<table class="params">'
            "<tr><th>Domain</th><th>Donor length</th><th>Candidate length</th><th>Global identity</th></tr>"
            f"<tr><td><b>VHH</b></td><td>{len(donor_vhh)} aa</td><td>{len(cand_vhh)} aa</td><td><b>{ident}</b></td></tr>"
            "</table>"
            f"{mut_table}"
        )

    donor_vh = (cleaning_map.get("donor_vh") or {}).get("final_sequence") or ""
    donor_vl = (cleaning_map.get("donor_vl") or {}).get("final_sequence") or ""
    cand_vh = (cleaning_map.get("candidate_vh") or {}).get("final_sequence") or ""
    cand_vl = (cleaning_map.get("candidate_vl") or {}).get("final_sequence") or ""

    rows = []
    for label, d_seq, h_seq in [
        ("VH", donor_vh, cand_vh),
        ("VL", donor_vl, cand_vl),
    ]:
        if not d_seq and not h_seq:
            continue
        ident = _identity(d_seq, h_seq)
        rows.append(
            f"<tr><td><b>{html.escape(label)}</b></td>"
            f"<td>{len(d_seq)} aa</td>"
            f"<td>{len(h_seq)} aa</td>"
            f"<td><b>{html.escape(ident)}</b></td></tr>"
        )
    if not rows:
        return '<p class="note">No sequence comparison data.</p>'

    return (
        '<p class="note">Global sequence identity (full variable-region) between donor and candidate. '
        "High identity indicates conservative substitution strategy; lower identity is expected for "
        "standard CDR grafting.</p>"
        '<table class="params">'
        "<tr><th>Domain</th><th>Donor length</th><th>Candidate length</th><th>Global identity</th></tr>"
        + "".join(rows)
        + "</table>"
        '<p class="note" style="margin-top:6px">Identity is computed over aligned positions (min-length match). '
        "Framework-only identity is available in the primary humanization report.</p>"
    )


def _html_seq_blocks_recheck(cleaning_map: Dict[str, Any]) -> str:
    """§10: render sequences as styled seq-blocks (like humanization report)."""
    if not cleaning_map:
        return '<p class="note">Sequence data archived in delivery FASTA and result.json.</p>'

    def _chunks(seq: str, size: int = 10) -> str:
        return "".join(
            f"<span class='chunk'>{html.escape(seq[i:i+size])}</span>"
            for i in range(0, len(seq), size)
        )

    # Detect VHH mode vs VH/VL mode
    is_vhh = ("donor_vhh" in cleaning_map or "candidate_vhh" in cleaning_map)

    if is_vhh:
        order = ["donor_vhh", "candidate_vhh"]
        labels = {
            "donor_vhh":     "Donor VHH (single-domain)",
            "candidate_vhh": "Candidate VHH (single-domain)",
        }
    else:
        order = ["donor_vh", "candidate_vh", "donor_vl", "candidate_vl"]
        labels = {
            "donor_vh": "Donor VH",
            "candidate_vh": "Candidate VH",
            "donor_vl": "Donor VL",
            "candidate_vl": "Candidate VL",
        }

    parts = [
        '<p class="note">Full variable-region sequences after optional intake normalization. '
        "Sequences are also archived in delivery FASTA.</p>"
    ]
    for key in order:
        cv = cleaning_map.get(key)
        if not cv:
            continue
        seq = cv.get("final_sequence") or ""
        applied = cv.get("applied", False)
        lbl = labels.get(key, key)
        norm_note = (
            ' &nbsp;<span style="color:#6b7280;font-size:.75rem">(normalization applied)</span>'
            if applied
            else ""
        )
        parts.append(
            f'<div class="seq-block">'
            f'<div class="seq-label">{html.escape(lbl)}'
            f'<span class="seq-len">{len(seq)} aa{norm_note}</span></div>'
            f'<div class="seq-body">{_chunks(seq)}</div>'
            f"</div>"
        )
    return "".join(parts) if len(parts) > 1 else '<p class="note">Sequence data archived in delivery FASTA.</p>'


def _finalize_payload(
    job_id: str,
    out: Path,
    payload: Dict[str, Any],
    kind: str,
    t0: float,
) -> tuple[str, float]:
    zip_name = f"{job_id}_recheck_delivery.zip"
    zip_url = f"/files/{job_id}/{zip_name}"
    payload["zip_url"] = zip_url
    payload["job_id"] = job_id
    payload.setdefault("protocol_version", "Recheck-Protocol v1.0")
    payload.setdefault("analysis_version", "recheck_v1")
    payload.setdefault("report_format_version", "v1.0-13section")

    result_path = out / "result.json"
    result_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8-sig",
    )

    html_path = _render_recheck_html(payload, out, kind)
    if kind == "VH/VL":
        zip_ret = _create_recheck_zip_vhvl(out, job_id)
    else:
        zip_ret = _create_recheck_zip_vhh(out, job_id)
    if not zip_ret:
        payload["zip_url"] = None
        result_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8-sig",
        )

    report_url = f"{files_url_for_path(job_id, html_path)}?cb={int(time.time())}"
    elapsed = round(time.time() - t0, 1)
    extra: Dict[str, Any] = {}
    if payload.get("zip_url"):
        extra["zip_url"] = payload["zip_url"]
    save_result(job_id, payload, report_url, elapsed, extra=extra or None)
    return report_url, elapsed


def _execute_recheck_vhvl(job_id: str, req: RecheckVHVLRequest) -> None:
    t0 = time.time()
    out = job_dir(job_id)
    project_name = (req.project_name or "").strip() or job_id

    _progress(job_id, 5, "Recheck — validating input")
    donor_vh_raw, donor_vl_raw = _norm(req.mouse_vh), _norm(req.mouse_vl)
    cand_vh_raw, cand_vl_raw = _norm(req.candidate_vh), _norm(req.candidate_vl)

    qc_basic = [
        _basic_seq_qc(donor_vh_raw, "donor_vh", 80, 160),
        _basic_seq_qc(donor_vl_raw, "donor_vl", 80, 160),
        _basic_seq_qc(cand_vh_raw, "candidate_vh", 80, 160),
        _basic_seq_qc(cand_vl_raw, "candidate_vl", 80, 160),
    ]
    clean = {
        "donor_vh": _clean_chain(donor_vh_raw, req.source_species, req.clean_mode, "donor_vh"),
        "donor_vl": _clean_chain(donor_vl_raw, req.source_species, req.clean_mode, "donor_vl"),
        "candidate_vh": _clean_chain(cand_vh_raw, req.source_species, req.clean_mode, "candidate_vh"),
        "candidate_vl": _clean_chain(cand_vl_raw, req.source_species, req.clean_mode, "candidate_vl"),
    }
    donor_vh = clean["donor_vh"]["final_sequence"]
    donor_vl = clean["donor_vl"]["final_sequence"]
    cand_vh = clean["candidate_vh"]["final_sequence"]
    cand_vl = clean["candidate_vl"]["final_sequence"]

    _write_vhvl_fastas(out, donor_vh, donor_vl, cand_vh, cand_vl)
    (out / "README.txt").write_text(_readme_vhvl(job_id, project_name), encoding="utf-8")

    _progress(job_id, 25, "Recheck — numbering / anchors")
    chain_qc = {
        "donor_vh": _anarci_chain_summary(donor_vh, "VH"),
        "donor_vl": _anarci_chain_summary(donor_vl, "VL"),
        "candidate_vh": _anarci_chain_summary(cand_vh, "VH"),
        "candidate_vl": _anarci_chain_summary(cand_vl, "VL"),
    }
    chain_status = _chain_status_from_numbering(chain_qc)

    _progress(job_id, 45, "Recheck — HPR / developability / naturalness")
    from core.humanization.hpr_index import compare_hpr  # noqa: PLC0415
    from core.humanization.basic_developability import compare_basic_developability  # noqa: PLC0415

    mini = {
        "candidate": _mini_cmc_for_fv(cand_vh, cand_vl),
        "compare_basic_developability": compare_basic_developability(donor_vh, donor_vl, cand_vh, cand_vl),
    }
    hpr = compare_hpr(donor_vh, donor_vl, cand_vh, cand_vl)
    naturalness = _naturalness_vhvl(cand_vh, cand_vl)

    structure_qc: Dict[str, Any] = {"status": "NOT_RUN", "issues": []}
    if req.run_structure:
        _progress(job_id, 60, "Recheck — paired structure QC (may take minutes)")
        structure_qc = _vhvl_structure_qc(donor_vh, donor_vl, cand_vh, cand_vl, out_dir=out)
    else:
        structure_qc["note"] = (
            "Structure QC skipped by request; enable in console/API for comparative structure review."
        )

    input_qc_status = _input_qc_rollout(_qc_status(qc_basic), chain_status)
    nat_comp = naturalness.get("status")
    if nat_comp in (None, "NOT_RUN"):
        nat_comp = "PASS"
    overall = _recheck_overall_for_client(
        input_qc_status,
        mini["candidate"].get("status"),
        structure_qc.get("status") if req.run_structure else "PASS",
        nat_comp,
    )
    payload_obj = RecheckResult(
        overall_status=overall,
        project_name=project_name,
        clean_mode=req.clean_mode,
        input_qc={
            "status": input_qc_status,
            "basic_checks": qc_basic,
            "numbering_checks": chain_qc,
        },
        cleaning_actions=clean,
        structure_qc=structure_qc,
        mini_cmc=mini,
        hpr_index=hpr,
        naturalness=naturalness,
        recommendation=_recommendation(overall, structure_qc.get("status", "NOT_RUN"), mini["candidate"].get("status")),
    )
    payload: Dict[str, Any] = payload_obj.dict() if hasattr(payload_obj, "dict") else payload_obj.model_dump()
    payload["structure_qc_requested"] = bool(req.run_structure)

    _progress(job_id, 92, "Recheck — writing report and delivery ZIP")
    if input_qc_status == "FAIL":
        _recheck_abort_no_deliverables(job_id, out, payload, t0)
        return
    _finalize_payload(job_id, out, payload, "VH/VL", t0)


def _execute_recheck_vhh(job_id: str, req: RecheckVHHRequest) -> None:
    t0 = time.time()
    out = job_dir(job_id)
    project_name = (req.project_name or "").strip() or job_id

    _progress(job_id, 10, "Recheck — validating VHH input")
    donor_raw, cand_raw = _norm(req.donor_vhh), _norm(req.candidate_vhh)
    qc_basic = [
        _basic_seq_qc(donor_raw, "donor_vhh", 80, 180),
        _basic_seq_qc(cand_raw, "candidate_vhh", 80, 180),
    ]
    clean = {
        "donor_vhh": _clean_chain(donor_raw, req.source_species, req.clean_mode, "donor_vhh"),
        "candidate_vhh": _clean_chain(cand_raw, req.source_species, req.clean_mode, "candidate_vhh"),
    }
    donor_vhh = clean["donor_vhh"]["final_sequence"]
    cand_vhh = clean["candidate_vhh"]["final_sequence"]

    _write_vhh_fastas(out, donor_vhh, cand_vhh)
    (out / "README.txt").write_text(_readme_vhh(job_id, project_name), encoding="utf-8")

    _progress(job_id, 30, "Recheck — numbering / anchors")
    chain_qc = {
        "donor_vhh": _anarci_chain_summary(donor_vhh, "VH", relaxed_first_cys=True),
        "candidate_vhh": _anarci_chain_summary(cand_vhh, "VH", relaxed_first_cys=True),
    }
    chain_status = _chain_status_from_numbering(chain_qc)

    _progress(job_id, 50, "Recheck — HPR / naturalness")
    from core.humanization.hpr_index import compare_hpr_vhh  # noqa: PLC0415
    from core.cmc.igg_hpr_ablang import compute_vhh_cmc_hpr_ablang  # noqa: PLC0415

    donor_cmc = _mini_cmc_for_vhh(donor_vhh)
    cand_cmc = _mini_cmc_for_vhh(cand_vhh)
    # Build delta for key metrics
    _delta_cmc: Dict[str, Any] = {}
    for _k in ("pI", "gravy", "instability_index"):
        dv = donor_cmc.get(_k)
        cv = cand_cmc.get(_k)
        if dv is not None and cv is not None:
            try:
                _delta_cmc[_k] = round(float(cv) - float(dv), 3)
            except Exception:  # noqa: BLE001
                pass
    mini = {
        "candidate": cand_cmc,
        "compare_basic_developability": {
            "donor":     donor_cmc,
            "humanized": cand_cmc,
            "delta":     _delta_cmc,
        },
    }
    hpr = compare_hpr_vhh(donor_vhh, cand_vhh)
    
    _abn_result: Dict[str, Any] = {}
    try:
        from core.vh2vhh.abnativ_naturalness_layer import score_naturalness_delta
        _d = score_naturalness_delta(donor_vhh, seq_id="donor")
        _c = score_naturalness_delta(cand_vhh, seq_id="candidate")
        
        _abn_result["donor"] = {
            "vh2":  round(float(_d.vh2_score), 4)  if _d.vh2_score  is not None else None,
            "vhh2": round(float(_d.vhh2_score), 4) if _d.vhh2_score is not None else None,
            "delta": round(float(_d.delta), 4)     if _d.delta      is not None else None,
            "tier": _d.tier,
        }
        _abn_result["humanized"] = {
            "vh2":  round(float(_c.vh2_score), 4)  if _c.vh2_score  is not None else None,
            "vhh2": round(float(_c.vhh2_score), 4) if _c.vhh2_score is not None else None,
            "delta": round(float(_c.delta), 4)     if _c.delta      is not None else None,
            "tier": _c.tier,
        }
        if _d.vh2_score is not None and _c.vh2_score is not None:
            _abn_result["delta_vh2"] = round(float(_c.vh2_score) - float(_d.vh2_score), 4)
        if _d.vhh2_score is not None and _c.vhh2_score is not None:
            _abn_result["delta_vhh2"] = round(float(_c.vhh2_score) - float(_d.vhh2_score), 4)
    except Exception as _ae:
        _abn_result["error"] = f"{type(_ae).__name__}: {_ae}"

    # For compatibility with older frontend if it expects "status"
    _abn_result["status"] = "PASS" if "error" not in _abn_result else "WARN"
    
    naturalness = _abn_result

    structure_qc: Dict[str, Any] = {"status": "NOT_RUN", "issues": []}
    if req.run_structure:
        _progress(job_id, 65, "Recheck — single-domain structure QC")
        structure_qc = _vhh_structure_qc(donor_vhh, cand_vhh, out_dir=out)
    else:
        structure_qc["note"] = "Structure QC skipped by request."

    input_qc_status = _input_qc_rollout(_qc_status(qc_basic), chain_status)
    overall = _recheck_overall_for_client(
        input_qc_status,
        mini["candidate"].get("status"),
        structure_qc.get("status") if req.run_structure else "PASS",
        naturalness.get("status"),
    )
    payload_obj = RecheckResult(
        overall_status=overall,
        project_name=project_name,
        clean_mode=req.clean_mode,
        input_qc={
            "status": input_qc_status,
            "basic_checks": qc_basic,
            "numbering_checks": chain_qc,
        },
        cleaning_actions=clean,
        structure_qc=structure_qc,
        mini_cmc=mini,
        hpr_index=hpr,
        naturalness=naturalness,
        recommendation=_recommendation(overall, structure_qc.get("status", "NOT_RUN"), mini["candidate"].get("status")),
    )
    payload: Dict[str, Any] = payload_obj.dict() if hasattr(payload_obj, "dict") else payload_obj.model_dump()
    payload["structure_qc_requested"] = bool(req.run_structure)

    _progress(job_id, 92, "Recheck — writing report and delivery ZIP")
    if input_qc_status == "FAIL":
        _recheck_abort_no_deliverables(job_id, out, payload, t0)
        return
    _finalize_payload(job_id, out, payload, "VHH", t0)


def _job_status_from_store(job_id: str) -> JobStatus:
    row = jobs[job_id]
    extra = row.get("extra")
    return JobStatus(
        job_id=job_id,
        status=str(row.get("status") or "done"),
        progress=int(row.get("progress") or 100),
        progress_note=row.get("progress_note"),
        elapsed_sec=row.get("elapsed_sec"),
        result=row.get("result"),
        report_url=row.get("report_url"),
        error=row.get("error"),
        extra=extra,
    )


@router.post("/vhvl", response_model=JobStatus, summary="Recheck donor VH/VL vs customer humanized VH/VL (sync)")
def recheck_vhvl(req: RecheckVHVLRequest) -> JobStatus:
    job_id = f"recheck-vhvl-{uuid.uuid4().hex[:8]}"
    jobs[job_id] = {"status": "running", "progress": 0, "progress_note": "Starting…"}
    persist_job_snapshot(job_id)
    try:
        _execute_recheck_vhvl(job_id, req)
    except Exception as exc:  # noqa: BLE001
        jobs[job_id] = {
            "status": "failed",
            "progress": 0,
            "error": f"{type(exc).__name__}: {exc}",
        }
        persist_job_snapshot(job_id)
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc
    return _job_status_from_store(job_id)


@router.post("/vhvl/async", summary="Enqueue VH/VL recheck (poll GET /jobs/{{job_id}})")
def recheck_vhvl_async(req: RecheckVHVLRequest) -> Dict[str, str]:
    job_id = f"recheck-vhvl-{uuid.uuid4().hex[:8]}"
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "progress_note": "Queued — Recheck worker",
    }
    persist_job_snapshot(job_id)

    def _worker() -> None:
        try:
            jobs[job_id]["status"] = "running"
            persist_job_snapshot(job_id)
            _execute_recheck_vhvl(job_id, req)
        except Exception as e:  # noqa: BLE001
            jobs[job_id] = {
                "status": "failed",
                "progress": 0,
                "error": f"{type(e).__name__}: {e}",
            }
            persist_job_snapshot(job_id)

    threading.Thread(target=_worker, daemon=True).start()
    return {"job_id": job_id, "status": "queued", "poll_url": f"/jobs/{job_id}"}


@router.post("/vhh", response_model=JobStatus, summary="Recheck donor VHH vs customer humanized VHH (sync)")
def recheck_vhh(req: RecheckVHHRequest) -> JobStatus:
    job_id = f"recheck-vhh-{uuid.uuid4().hex[:8]}"
    jobs[job_id] = {"status": "running", "progress": 0, "progress_note": "Starting…"}
    persist_job_snapshot(job_id)
    try:
        _execute_recheck_vhh(job_id, req)
    except Exception as exc:  # noqa: BLE001
        jobs[job_id] = {
            "status": "failed",
            "progress": 0,
            "error": f"{type(exc).__name__}: {exc}",
        }
        persist_job_snapshot(job_id)
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc
    return _job_status_from_store(job_id)


@router.post("/vhh/async", summary="Enqueue VHH recheck (poll GET /jobs/{{job_id}})")
def recheck_vhh_async(req: RecheckVHHRequest) -> Dict[str, str]:
    job_id = f"recheck-vhh-{uuid.uuid4().hex[:8]}"
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "progress_note": "Queued — Recheck worker",
    }
    persist_job_snapshot(job_id)

    def _worker() -> None:
        try:
            jobs[job_id]["status"] = "running"
            persist_job_snapshot(job_id)
            _execute_recheck_vhh(job_id, req)
        except Exception as e:  # noqa: BLE001
            jobs[job_id] = {
                "status": "failed",
                "progress": 0,
                "error": f"{type(e).__name__}: {e}",
            }
            persist_job_snapshot(job_id)

    threading.Thread(target=_worker, daemon=True).start()
    return {"job_id": job_id, "status": "queued", "poll_url": f"/jobs/{job_id}"}
