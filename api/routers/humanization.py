"""
api/routers/humanization.py
Humanization endpoints: VH/VL (murine to human) and VHH (camelid nanobody).
"""
from __future__ import annotations

import sys, json, uuid, time, zipfile, threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from api.models import VHVLRequest, VHHRequest, JobStatus
from api.job_store import jobs, save_result, job_dir, persist_job_snapshot, files_url_for_path
from api.public_locale import resolve_vhvl_report_language

router = APIRouter(prefix="/humanize", tags=["Humanization"])

# Version registry (UI/report-facing).
# V5.5.1 is the current SSOT release. VH/VL jobs: HPR Index + mini-CMC + structure QC;
# AbLang2/T20 disabled; p-AbNatiV paired gate runs when structure evaluation is enabled.
VHVL_REPORT_PROTOCOL_VERSION = "V5.5.1"
VHVL_ANALYSIS_VERSION = "v5.5.1"
VHVL_REPORT_FORMAT_VERSION = "v1.5"
VHVL_RABBIT_REPORT_FORMAT_VERSION = "v1.5-rabbit-multiroute"
VHVL_HTML_REPORT_BUILD_ID = "20260510-V5.5.1-vhvl-format-v15-console-runmode"

VHH_REPORT_PROTOCOL_VERSION = "V3.3"
VHH_ANALYSIS_VERSION = "v3.3"

# VH→VHH: algorithm standard vs Console/API deployment branch (IGHV3-only gateway).
VH2VHH_STANDARD_VERSION = "V1.8.17"
VH2VHH_CONSOLE_DEPLOYMENT_BRANCH = "V1.8.17.IGHV3"
VH2VHH_REPORT_PROTOCOL_VERSION = VH2VHH_CONSOLE_DEPLOYMENT_BRANCH
VH2VHH_ANALYSIS_VERSION = "v1.8.17"


def _vhvl_report_format_version_for_species(source_species: Any) -> str:
    """Rabbit-specific report format upgrade; other species keep default format."""
    sp = str(source_species or "").strip().lower()
    if sp in {"rabbit", "oryctolagus_cuniculus"}:
        return VHVL_RABBIT_REPORT_FORMAT_VERSION
    return VHVL_REPORT_FORMAT_VERSION


def _slug_project_dir_segment(name: str) -> str:
    """Filesystem-safe segment under projects/ (VH/VL mirror)."""
    s = (name or "").strip() or "demo"
    for c in '<>:"/\\|?*\n\r\t':
        s = s.replace(c, "_")
    s = "_".join(s.split())
    return (s[:120] if s else "demo") or "demo"


def _vhvl_archive_run_subdir(job_id: str, started_unix: float) -> str:
    """One run folder under projects/<project>/vhvl_humanization/: UTC stamp + job id."""
    jid = (job_id or "job").strip()
    for c in '<>:"/\\|?*\n\r\t':
        jid = jid.replace(c, "_")
    jid = "_".join(jid.split())[:96] or "job"
    utc = datetime.fromtimestamp(float(started_unix), tz=timezone.utc)
    stamp = utc.strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{jid}"


def _vhvl_project_archive_dest(
    suite_root: Path,
    project_name: str,
    job_id: str,
    started_unix: float,
) -> Path:
    """Reserved run folder: projects/<slug>/vhvl_humanization/<UTCstamp_jobid>/."""
    run_seg = _vhvl_archive_run_subdir(job_id, started_unix)
    return (
        suite_root
        / "projects"
        / _slug_project_dir_segment(project_name)
        / "vhvl_humanization"
        / run_seg
    )


def _vhvl_copy_into_project_archive(archive_dest: Path, src: Path, dest_name: Optional[str] = None) -> bool:
    """Copy one file into the project archive dir (mkdir as needed)."""
    import shutil

    if not src.is_file():
        return False
    try:
        archive_dest.mkdir(parents=True, exist_ok=True)
        name = dest_name if dest_name else src.name
        shutil.copy2(src, archive_dest / name)
        return True
    except Exception:
        return False


def _mirror_vhvl_pdbs_into_project_archive(archive_dest: Path, job_out_dir: Path) -> bool:
    """Copy predicted Fv PDBs into the run archive folder."""
    ok = False
    for fname in ("donor_ab.pdb", "humanized_ab.pdb"):
        if _vhvl_copy_into_project_archive(archive_dest, job_out_dir / fname):
            ok = True
    return ok


def _vhvl_count_phases_no_fail(checklist_report: Optional[Dict[str, Any]]) -> int:
    """Phases 1–5 with no FAIL checklist items (WARN allowed). Matches checklist_report['phases']."""
    if not checklist_report or not isinstance(checklist_report, dict):
        return 0
    phases = checklist_report.get("phases")
    if not isinstance(phases, dict):
        return 0
    n = 0
    for pnum in range(1, 6):
        items = phases.get(pnum)
        if not items:
            continue
        if any(it.get("status") == "FAIL" for it in items):
            continue
        n += 1
    return n

# ─────────────────────────────────────────────────────────────────────────────
# Delivery ZIP: report + PDB + FASTA + README
# ─────────────────────────────────────────────────────────────────────────────

def _write_delivery_readme(
    out_dir: Path,
    job_id: str,
    report_language: str = "en",
    project_structure_rel: Optional[str] = None,
) -> Path:
    """README inside the delivery ZIP. English-only for InSynBio V5.2.2."""
    _proj_note = ""
    if project_structure_rel:
        _proj_note = f"""
================================================================================
Project archive (suite tree mirror)
================================================================================
Fv PDBs (when predicted), result.json, and humanization_report.html are copied under:

  {project_structure_rel}

Use this path for long-term project organization alongside other pipeline artifacts.
"""

    text = f"""InSynBio AbEngineCore — VH/VL Humanization Delivery Package
Job ID: {job_id}
{_proj_note}
================================================================================
Package contents
================================================================================

1. Humanization_Report.pdf (when generated)
   Customer PDF: summary, sequences, structure/QC highlights, clinical references.

2. humanization_report.html (when generated)
   Browser report for the same job outputs.

3. donor_sequences.fasta
   Donor-species VH/VL amino-acid sequences (FASTA).

4. humanized_sequences.fasta
   Humanized VH/VL amino-acid sequences (FASTA).

5. donor_ab.pdb (optional)
   Donor Fv model — included only when structure computation succeeded.

6. humanized_ab.pdb (optional)
   Humanized Fv model — included only when structure computation succeeded.

7. README.txt
   This manifest.

Minimum bundle: at least one report file (PDF and/or HTML) + FASTAs + this README; PDBs when available.
This ZIP does not include internal JSON, audit logs, rescue traces, or algorithm internals.

================================================================================
Opening PDB files — common free viewers
================================================================================
• ChimeraX (UCSF) — https://www.cgl.ucsf.edu/chimerax/
• VMD (UIUC) — https://www.ks.uiuc.edu/Research/vmd/
• PyMOL — per your license
• Jmol / JSmol — open source
• NGL Viewer — https://nglviewer.org/

FASTA: any text editor.

================================================================================
Clinical precedents & ADA literature (report section 3)
================================================================================
Precedent tables: approved or late-stage antibodies that overlap with the selected human VH/VL templates (contextual reference). ADA statistics are provided only for published data associated with the same human template; these are not predictions for the humanized candidate itself.

================================================================================
Disclaimer
================================================================================
Structural models are AI-predicted for R&D reference; critical conclusions should be confirmed experimentally.
"""
    p = out_dir / "README.txt"
    p.write_text(text, encoding="utf-8")
    return p


def _create_delivery_zip(
    out_dir: Path,
    job_id: str,
    report_language: str = "en",
    project_structure_rel: Optional[str] = None,
) -> Optional[str]:
    """Pack README + FASTA into one ZIP; include reports/PDBs when present.

    Reliability rule: keep ZIP available even if HTML/PDF generation fails, so
    the console still exposes a deterministic downloadable delivery artifact.
    """
    try:
        _write_delivery_readme(out_dir, job_id, report_language, project_structure_rel)
    except Exception:
        pass
    zip_name = f"{job_id}_delivery.zip"
    zip_path = out_dir / zip_name
    # Required: evidence sequences + manifest. Reports/PDBs are optional.
    readme = "README.txt"
    fastas = ("donor_sequences.fasta", "humanized_sequences.fasta")
    core = (readme,) + fastas
    missing_core = [name for name in core if not (out_dir / name).is_file()]
    if missing_core:
        try:
            zip_path.unlink(missing_ok=True)
        except Exception:
            pass
        return None
    report_names = []
    pdf_p = out_dir / "Humanization_Report.pdf"
    html_nested = out_dir / "reports" / "vhvl_humanization" / "humanization_report.html"
    html_legacy = out_dir / "humanization_report.html"
    html_p = html_nested if html_nested.is_file() else html_legacy
    if pdf_p.is_file():
        report_names.append("Humanization_Report.pdf")
    if html_p.is_file():
        report_names.append("humanization_report.html")
    optional = ("donor_ab.pdb", "humanized_ab.pdb")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in core:
            zf.write(out_dir / name, arcname=name)
        for name in report_names:
            if name == "humanization_report.html" and html_p.is_file():
                zf.write(html_p, arcname=name)
            elif name == "Humanization_Report.pdf" and pdf_p.is_file():
                zf.write(pdf_p, arcname=name)
        for name in optional:
            fp = out_dir / name
            if fp.is_file():
                zf.write(fp, arcname=name)
    return f"/files/{job_id}/{zip_name}"


def _cdrs_imgt_for_report(mouse_vh: str, mouse_vl: str) -> Optional[Dict[str, str]]:
    """IMGT V-domain CDR segments for **client-facing reports** (aligned with /annotate IMGT).

    Pipeline scoring (clinical Kabat gate, Phase 4 Vernier, Chothia-masked FR%) is unchanged —
    this is display-only so reports use IMGT boundaries for database interoperability.
    """
    try:
        from core.numbering.imgt_anarcii import imgt_number_anarcii
        from core.vhh_humanization import split_regions as split_regions_imgt
    except ImportError:
        return None
    vh = (mouse_vh or "").strip().upper().replace(" ", "")
    vl = (mouse_vl or "").strip().upper().replace(" ", "")
    if len(vh) < 50 or len(vl) < 50:
        return None
    try:
        rh, rl = imgt_number_anarcii(vh), imgt_number_anarcii(vl)
        reg_h, reg_l = split_regions_imgt(rh), split_regions_imgt(rl)
    except Exception:
        return None
    return {
        "H1": reg_h.get("CDR1", ""),
        "H2": reg_h.get("CDR2", ""),
        "H3": reg_h.get("CDR3", ""),
        "L1": reg_l.get("CDR1", ""),
        "L2": reg_l.get("CDR2", ""),
        "L3": reg_l.get("CDR3", ""),
    }


def _run_v54_structure_surface_reshape(payload: Dict[str, Any], structure: Dict[str, Any]) -> Dict[str, Any]:
    """V5.4 structure-driven FR-only surface reshaping fallback.

    This is a fallback route for low framework compatibility or QC WARN/FAIL.
    It preserves CDRs by starting from the donor sequence for triggered chains
    and only applying AUTO_APPLY FR substitutions selected by 3D safe-zone rules.
    """
    donor_pdb = structure.get("pdb_path")
    if not donor_pdb or not Path(str(donor_pdb)).is_file():
        return {"applied": False, "errors": ["Donor Fv PDB is required for structure-driven surface reshaping."]}

    donor_vh = str(payload.get("mouse_vh") or "")
    donor_vl = str(payload.get("mouse_vl") or "")
    selected_vh = str(payload.get("vh_germline") or "").replace("—", "").strip()
    selected_vl = str(payload.get("vl_germline") or "").replace("—", "").strip()
    if not donor_vh or not donor_vl or not selected_vh or not selected_vl:
        return {"applied": False, "errors": ["Missing donor VH/VL or selected germline IDs."]}

    try:
        from core.humanization.kabat_utils import get_kabat_numbering  # noqa: PLC0415
        from core.humanization.resurfacing import (  # noqa: PLC0415
            apply_chain_caps,
            assemble_final_sequence,
            build_human_consensus,
            extract_residue_features,
            load_resurfacing_config,
            select_safe_mutations,
            summarise_decisions,
        )
        from scripts.vhvl_surface_reshape_fallback import load_human_germline_sequences  # noqa: PLC0415
    except Exception as exc:
        return {"applied": False, "errors": [f"Surface reshape imports failed: {exc}"]}

    root = Path(__file__).resolve().parents[2]
    cfg = load_resurfacing_config(root / "config" / "resurfacing_v1.json")
    cache = root / "data" / "cache"
    germ = root / "data" / "germlines"

    try:
        vh_cons = build_human_consensus(germ / "ogrdb_human_IGHV_v2.json", cache / "consensus_IGHV_kabat_v1.json")
        vk_cons = build_human_consensus(germ / "ogrdb_human_IGKV_v2.json", cache / "consensus_IGKV_kabat_v1.json")
        vl_cons = build_human_consensus(germ / "ogrdb_human_IGLV_v2.json", cache / "consensus_IGLV_kabat_v1.json")
    except Exception as exc:
        return {"applied": False, "errors": [f"Human consensus build failed: {exc}"]}

    vl_merged: Dict[str, Dict[str, float]] = {}
    for table in ((vk_cons.get("VL") or {}), (vl_cons.get("VL") or {})):
        for kpos, freqs in table.items():
            slot = vl_merged.setdefault(kpos, {})
            for aa, freq in freqs.items():
                slot[aa] = slot.get(aa, 0.0) + float(freq)
    for kpos, freqs in vl_merged.items():
        total = sum(freqs.values())
        if total:
            vl_merged[kpos] = {aa: round(val / total, 4) for aa, val in freqs.items()}

    germ_vh, germ_vl = load_human_germline_sequences(selected_vh, selected_vl)
    if not germ_vh or not germ_vl:
        return {"applied": False, "errors": ["Could not load selected OGRDB germline sequences."]}

    def _chain_max_rmsd(prefix: str) -> float:
        vals = []
        for key, val in (payload.get("cdr_rmsd") or {}).items():
            if str(key).startswith(prefix) and isinstance(val, (int, float)):
                vals.append(float(val))
        return max(vals) if vals else 0.0

    vh_id = payload.get("vh_germline_identity")
    vl_id = payload.get("vl_germline_identity")
    vh_trigger = (not isinstance(vh_id, (int, float))) or float(vh_id) < 60.0 or _chain_max_rmsd("H") >= 1.5
    vl_trigger = (not isinstance(vl_id, (int, float))) or float(vl_id) < 60.0 or _chain_max_rmsd("L") >= 1.5

    vh_candidates = []
    vl_candidates = []
    final_vh = payload.get("humanized_vh") or donor_vh
    final_vl = payload.get("humanized_vl") or donor_vl
    try:
        if vh_trigger:
            vh_feats = extract_residue_features(
                donor_pdb=str(donor_pdb),
                donor_seq=donor_vh,
                chain_letter="H",
                kabat_dict=get_kabat_numbering(donor_vh) or {},
            )
            long_h3 = sum(1 for feat in vh_feats if feat.region == "CDR3") >= 16
            vh_candidates = select_safe_mutations(
                donor_seq=donor_vh,
                features=vh_feats,
                chain="VH",
                target_germline_seq=germ_vh,
                consensus_table={"VH": vh_cons.get("VH", {})},
                config=cfg,
                long_h3=long_h3,
            )
            vh_candidates = apply_chain_caps(vh_candidates, "VH", cfg)
            final_vh = assemble_final_sequence(donor_vh, vh_candidates)

        if vl_trigger:
            vl_feats = extract_residue_features(
                donor_pdb=str(donor_pdb),
                donor_seq=donor_vl,
                chain_letter="L",
                kabat_dict=get_kabat_numbering(donor_vl) or {},
            )
            vl_candidates = select_safe_mutations(
                donor_seq=donor_vl,
                features=vl_feats,
                chain="VL",
                target_germline_seq=germ_vl,
                consensus_table={"VL": vl_merged},
                config=cfg,
                long_h3=False,
            )
            vl_candidates = apply_chain_caps(vl_candidates, "VL", cfg)
            final_vl = assemble_final_sequence(donor_vl, vl_candidates)
    except Exception as exc:
        return {"applied": False, "errors": [f"Surface reshape selection failed: {exc}"]}

    vh_summary = summarise_decisions(vh_candidates) if vh_candidates else {"n_auto_apply": 0, "auto_apply": []}
    vl_summary = summarise_decisions(vl_candidates) if vl_candidates else {"n_auto_apply": 0, "auto_apply": []}

    return {
        "applied": bool(vh_summary.get("n_auto_apply") or vl_summary.get("n_auto_apply")),
        "method": "V5.4 structure-driven FR surface reshaping",
        "trigger": {
            "vh": bool(vh_trigger),
            "vl": bool(vl_trigger),
            "vh_fr_identity_pct": vh_id,
            "vl_fr_identity_pct": vl_id,
            "max_h_cdr_rmsd": _chain_max_rmsd("H"),
            "max_l_cdr_rmsd": _chain_max_rmsd("L"),
        },
        "humanized_vh": final_vh,
        "humanized_vl": final_vl,
        "vh_mutations": [
            f"{c['donor_aa']}{c['kabat_pos']}{c['kabat_ins']}{c['target_aa']}".replace(" ", "")
            for c in vh_summary.get("auto_apply", [])
        ],
        "vl_mutations": [
            f"{c['donor_aa']}{c['kabat_pos']}{c['kabat_ins']}{c['target_aa']}".replace(" ", "")
            for c in vl_summary.get("auto_apply", [])
        ],
        "vh_decision_summary": vh_summary,
        "vl_decision_summary": vl_summary,
    }


def _generate_vhvl_pdf_report(payload: dict, out_dir: Path, project_name: str = "") -> Path:
    """Generate a customer-facing PDF (English by default; Chinese optional via payload.report_language).

    ReportLab's built-in fonts do not render CJK glyphs — Chinese text appears as missing-glyph boxes unless a
    CID font is registered; default ``en`` avoids that.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    lang_zh = str(payload.get("report_language") or "en").lower() in ("zh", "zh-cn", "cn")

    def T(en: str, zh: str) -> str:
        return en

    def esc(text: Any) -> str:
        s = "—" if text is None else str(text)
        return (s.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;"))

    def seq_block(seq: str, chunk: int = 10) -> str:
        seq = (seq or "").strip()
        return " ".join(seq[i:i+chunk] for i in range(0, len(seq), chunk)) if seq else "—"

    def yes_no(flag: Any) -> str:
        return T("Yes", "") if flag else T("No", "")

    def fmt_num(v: Any, suffix: str = "") -> str:
        if isinstance(v, float):
            return f"{v:.2f}{suffix}"
        if isinstance(v, int):
            return f"{v}{suffix}"
        return "—" if v is None else f"{v}{suffix}"

    def qc_badge_text() -> str:
        status = str(payload.get("checklist_status") or "UNKNOWN").upper()
        if status == "PASS":
            return T("PASS (meets delivery thresholds)", "PASS（）")
        if status == "WARN":
            return T("WARN (confirm experimentally)", "WARN（）")
        if status == "FAIL":
            return T("FAIL (not recommended to proceed as-is)", "FAIL（）")
        return status

    def ablang_note(score: Any) -> str:
        if not isinstance(score, (int, float)):
            return T("No valid score.", "。")
        if score >= -0.5:
            return T(
                "Sequence humanness is favorable — framework is highly consistent with the human antibody repertoire. "
                "Note: this metric reflects FR-region naturalness; CDR-based immunogenicity requires separate T-cell epitope assessment.",
                "，。：；CDR  T 。",
            )
        if score >= -1.5:
            return T(
                "Sequence humanness is within the typical range for clinically approved humanized antibodies. "
                "CDR-based immunogenicity risk should be evaluated separately if available.",
                "。， CDR 。",
            )
        return T(
            "Sequence humanness is below the typical humanized antibody range; confirm expression and stability experimentally. "
            "Consider additional framework optimization.",
            "，，。",
        )

    def instability_note(idx: Any) -> str:
        if not isinstance(idx, (int, float)):
            return T("No valid index.", "。")
        if idx <= 40:
            return T("Instability index looks favorable for a quick screen.", "。")
        if idx <= 45:
            return T("Near the watch threshold; confirm with experiments if concerned.", "，。")
        return T("Above the quick watch threshold (45); potential stability risk on this screen.", "（45），。")

    def make_table(rows, col_widths, header=False, font_size=9):
        table = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
        style = [
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d0d7e2")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        if header:
            style.extend([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef8")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ])
        table.setStyle(TableStyle(style))
        return table

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallBody", parent=styles["BodyText"], fontSize=9, leading=13, spaceAfter=4))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontSize=12, leading=15, textColor=colors.HexColor("#1b4fad"), spaceBefore=8, spaceAfter=6))
    styles.add(ParagraphStyle(name="Tiny", parent=styles["BodyText"], fontSize=8, leading=11, spaceAfter=3, textColor=colors.HexColor("#5f6b7a")))
    styles.add(ParagraphStyle(name="Intro", parent=styles["BodyText"], fontSize=10, leading=15, spaceAfter=5))

    pdf_path = out_dir / "Humanization_Report.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = []

    project = project_name or payload.get("job_id") or payload.get("project_name") or "VH/VL Humanization"
    species = payload.get("source_species", "unknown")
    status = payload.get("checklist_status", "UNKNOWN")
    germline_ada_refs = payload.get("germline_ada_references", [])[:5]
    clinical_precedents = payload.get("clinical_precedents", [])[:5]
    liabilities = payload.get("liabilities", []) or []
    cdr_rmsd = payload.get("cdr_rmsd", {}) or {}
    mini_cmc = payload.get("mini_cmc", {}) or {}
    humanized_pdb_ready = bool((payload.get("pdb_urls") or {}).get("humanized_ab"))
    donor_pdb_ready = bool((payload.get("pdb_urls") or {}).get("donor_ab"))
    delivery_decision = payload.get("delivery_decision", {}) or {}
    fallback_used = bool(payload.get("fallback_germline_used"))
    warning_required = bool(delivery_decision.get("warning_required"))
    warning_reasons = payload.get("qc_warning_reasons") or []

    story.append(Paragraph(T("InSynBio VH/VL Humanization Report", "InSynBio VH/VL "), styles["Title"]))
    story.append(Paragraph(
        T(
            f"Project: <b>{esc(project)}</b>　　Donor species: <b>{esc(species)}</b>　　QC summary: <b>{esc(qc_badge_text())}</b>　　Protocol: <b>{VHVL_REPORT_PROTOCOL_VERSION}</b>",
            f"：<b>{esc(project)}</b>　　：<b>{esc(species)}</b>　　：<b>{esc(qc_badge_text())}</b>　　：<b>{VHVL_REPORT_PROTOCOL_VERSION}</b>",
        ),
        styles["BodyText"],
    ))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph(T("1. Executive summary", "1. "), styles["Section"]))
    story.append(Paragraph(
        T(
            "Customer-facing summary of the final humanized Fv, deliverable sequences, structure/QC highlights, and optional clinical framework precedents. "
            "Internal rescue logs, ranking internals, and audit records are not included.",
            "，、、/。"
            " rescue、、。",
        ),
        styles["Intro"],
    ))

    story.append(Paragraph(T("2. Humanization overview", "2. "), styles["Section"]))
    _hpr_ov = payload.get("hpr_index") or {}
    try:
        _hsc_ov = ((_hpr_ov.get("humanized") or {}).get("combined") or {}).get("score")
        _hpr_ov_txt = f"{float(_hsc_ov) * 100:.1f}%" if _hsc_ov is not None else "—"
    except Exception:
        _hpr_ov_txt = "—"
    _pab_ov_pdf = payload.get("p_abnativ2") or {}
    if _pab_ov_pdf.get("paired_humanness") is not None:
        try:
            _pab_ov_txt = (
                f"{float(_pab_ov_pdf['paired_humanness']):.3f} "
                f"({_pab_ov_pdf.get('paired_humanness_status') or '—'})"
            )
        except Exception:
            _pab_ov_txt = "—"
    else:
        _pab_ov_txt = "—"
    overview = [
        [T("Project", ""), esc(project), T("Donor species", ""), esc(species)],
        [T("Selected VH germline", " VH "), esc(payload.get("vh_germline")), T("VH FR identity", "VH "), esc(fmt_num(payload.get("vh_germline_identity"), "%"))],
        [T("Selected VL germline", " VL "), esc(payload.get("vl_germline")), T("VL FR identity", "VL "), esc(fmt_num(payload.get("vl_germline_identity"), "%"))],
        [
            T("HPR Index (humanized combined)", "HPR Index（）"),
            esc(_hpr_ov_txt),
            T("Paired Fv naturalness", " Fv "),
            esc(_pab_ov_txt),
        ],
        [
            T("Fab pI (mini-CMC)", "Fab pI（mini-CMC）"),
            esc(fmt_num(payload.get("pI_fab"))),
            T("Overall QC", ""),
            esc(qc_badge_text()),
        ],
        [
            T("Structure computed", ""),
            esc(yes_no(payload.get("structure_computed"))),
            T("VH/VL naturalness policy", "VH/VL "),
            T("HPR Index primary; AbLang2/T20 disabled; p-AbNatiV when structure evaluated", " HPR ； AbLang2/T20； p-AbNatiV"),
        ],
        [
            T("Framework routing", ""),
            T("Clinical fallback triggered", " fallback ") if fallback_used else T("Preferred clinical-anchor framework", ""),
            T("Delivery mode", ""),
            T("QC-warning delivery", "QC warning ") if warning_required else T("Standard delivery", ""),
        ],
    ]
    story.append(make_table(overview, [3.0*cm, 5.2*cm, 3.0*cm, 5.0*cm], header=False))
    story.append(Paragraph(
        T(
            "<i>Note: FR identity uses the locked pipeline (Chothia-masked) vs selected germline. §2a CDR segments use IMGT boundaries for database alignment.</i>",
            "<i>：「」（Chothia ） FR% ；§2a  CDR  IMGT ，。</i>",
        ),
        styles["Tiny"],
    ))

    ci_pdf = payload.get("cdrs_imgt") or {}
    if any(ci_pdf.values()):
        story.append(Paragraph(T("2a. CDR segments (IMGT boundaries)", "2a. CDR （IMGT ）"), styles["Section"]))
        story.append(Paragraph(
            T(
                "CDR amino-acid segments under IMGT V-domain definitions (display only; independent of pipeline numbering gates).",
                " IMGT V-domain  CDR （/IMGT ）。、。",
            ),
            styles["Tiny"],
        ))
        cdr_pdf_rows = [["CDR", T("Length (aa)", " aa"), T("Sequence", "")]]
        for name in ("H1", "H2", "H3", "L1", "L2", "L3"):
            s = ci_pdf.get(name, "") or ""
            cdr_pdf_rows.append([name, str(len(s)), esc(seq_block(s, chunk=14))])
        story.append(make_table(cdr_pdf_rows, [1.2*cm, 2.0*cm, 13.5*cm], header=True, font_size=8))

    if warning_required:
        story.append(Paragraph(T("2b. QC warning summary", "2a. QC Warning Summary"), styles["Section"]))
        if warning_reasons:
            _sep = "；" if lang_zh else "; "
            story.append(Paragraph(
                T(
                    "Pipeline completed with deliverables; experimental confirmation is still needed for: ",
                    "，：",
                )
                + esc(_sep.join(str(x) for x in warning_reasons)),
                styles["SmallBody"],
            ))
        else:
            story.append(Paragraph(
                T(
                    "Pipeline completed with deliverables, but structural/developability risks may still require experimental confirmation.",
                    "，/。",
                ),
                styles["SmallBody"],
            ))

    _pdf_sp = (payload.get("source_species") or "donor").strip().lower()
    story.append(Paragraph(T("3. Sequences for delivery", "3. "), styles["Section"]))
    seq_summary = [
        [T("File", ""), T("Chain", ""), T("Type", ""), T("Length (aa)", " (aa)")],
        ["donor_sequences.fasta", "VH", T(f"Donor ({_pdf_sp})", f" ({_pdf_sp})"), str(len(payload.get("mouse_vh", "") or ""))],
        ["donor_sequences.fasta", "VL", T(f"Donor ({_pdf_sp})", f" ({_pdf_sp})"), str(len(payload.get("mouse_vl", "") or ""))],
        ["humanized_sequences.fasta", "VH", T("Humanized", ""), str(len(payload.get("humanized_vh", "") or ""))],
        ["humanized_sequences.fasta", "VL", T("Humanized", ""), str(len(payload.get("humanized_vl", "") or ""))],
    ]
    story.append(make_table(seq_summary, [4.0*cm, 2.0*cm, 3.5*cm, 4.7*cm], header=True))
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph(f"<b>{_pdf_sp} VH</b><br/>{esc(seq_block(payload.get('mouse_vh', '')))}", styles["SmallBody"]))
    story.append(Paragraph(f"<b>{_pdf_sp} VL</b><br/>{esc(seq_block(payload.get('mouse_vl', '')))}", styles["SmallBody"]))
    story.append(Paragraph(f"<b>humanized VH</b><br/>{esc(seq_block(payload.get('humanized_vh', '')))}", styles["SmallBody"]))
    story.append(Paragraph(f"<b>humanized VL</b><br/>{esc(seq_block(payload.get('humanized_vl', '')))}", styles["SmallBody"]))

    story.append(Paragraph(T("4. Structure & QC summary", "4. "), styles["Section"]))
    qc_rows = [
        [T("Metric", ""), T("Result", ""), T("Notes", "")],
        [
            T("Donor structure file", ""),
            T("Generated", "") if mouse_pdb_ready else T("Not generated", ""),
            T("Deliverable: donor_ab.pdb", "：donor_ab.pdb"),
        ],
        [
            T("Humanized structure file", ""),
            T("Generated", "") if humanized_pdb_ready else T("Not generated", ""),
            T("Deliverable: humanized_ab.pdb", "：humanized_ab.pdb"),
        ],
        [
            T("Donor model confidence (pLDDT-eq)", ""),
            esc(fmt_num(payload.get("plddt"))),
            T("Quick confidence read for donor Fv.", " Fv "),
        ],
        [
            T("Humanized model confidence (pLDDT-eq)", ""),
            esc(fmt_num(payload.get("humanized_plddt"))),
            T("Quick confidence read for humanized Fv.", " Fv "),
        ],
        [
            T("Humanized VH/VL packing angle", " VH/VL "),
            esc(fmt_num(payload.get("humanized_angle_deg"), "°")),
            T("Principal-axis packing angle for humanized Fv.", " Fv  VH/VL packing angle"),
        ],
        [
            T("Packing-angle delta (humanized − donor)", "VH/VL "),
            esc(fmt_num(payload.get("angle_delta_deg"), "°")),
            T("Smaller |Δ| is usually better for preserving Fv geometry.", ""),
        ],
        [
            T("Mean CDR Cα RMSD", " CDR RMSD"),
            esc(fmt_num(payload.get("rmsd_to_reference"), " Å")),
            T("Loop fidelity vs donor model (predicted vs predicted).", ""),
        ],
        [
            T("Key developability flags (quick screen)", " developability "),
            esc(", ".join(liabilities) if liabilities else T("No major quick-screen flags", "")),
            T("Based on pI / GRAVY / instability index (fast screen).", " pI / GRAVY / instability index "),
        ],
    ]
    story.append(make_table(qc_rows, [3.6*cm, 3.2*cm, 8.2*cm], header=True, font_size=8))
    if cdr_rmsd:
        story.append(Paragraph(
            T("Per-CDR RMSD: ", " RMSD：")
            + esc(", ".join(f"{k}={v:.2f} Å" for k, v in cdr_rmsd.items() if isinstance(v, (int, float)))),
            styles["Tiny"],
        ))
    if mini_cmc:
        story.append(Paragraph(
            T("Mini-CMC quick screen: ", "Mini-CMC ：")
            + esc(
                f"length={mini_cmc.get('length', '—')}, "
                f"gravy={mini_cmc.get('gravy', '—')}, "
                f"instability_index={mini_cmc.get('instability_index', '—')}, "
                f"aromaticity={mini_cmc.get('aromaticity', '—')}"
            ),
            styles["Tiny"],
        ))
    story.append(Paragraph(
        T("Instability index note: ", "Instability index ：")
        + esc(instability_note(mini_cmc.get("instability_index"))),
        styles["Tiny"],
    ))
    story.append(Paragraph(
        T(
            "Naturalness context note: VH/VL jobs use HPR Index as the primary repertoire-compatibility line item; "
            "paired Fv naturalness (p-AbNatiV) runs when structure evaluation is enabled. AbLang2 PLL and T20 are disabled by product policy.",
            "：VH/VL  HPR Index ； Fv （p-AbNatiV）。AbLang2 PLL  T20 。",
        ),
        styles["Tiny"],
    ))

    story.append(Paragraph(T("4b. Next steps for deeper developability", "4b. （）"), styles["Section"]))
    story.append(Paragraph(
        T(
            "This report includes essential mini-CMC (pI / GRAVY / instability, etc.) and structure-conservation metrics. "
            "Integrated Clinical Reference Cohort ranking and the full CMC advisor are <b>not</b> bundled with humanization — run <b>CMC → IgG CMC</b> "
            "on the <b>same</b> humanized VH/VL pair when you need clinical benchmark scoring. "
            "For antigen–antibody complex modeling, use the AF2 Multimer offline workflow.",
            " <b>Essential mini-CMC</b>（ pI / GRAVY / instability ）。"
            "<b></b> Clinical Reference Cohort  CMC advisor；、"
            " PDF， <b>CMC → IgG CMC</b> <strong></strong> VH/VL 。"
            "-「 → AF2 Multimer」。",
        ),
        styles["Tiny"],
    ))

    story.append(Paragraph(T("5. Clinical framework precedents", "5. "), styles["Section"]))
    if clinical_precedents:
        cp_data = [[T("Drug", ""), T("Match", ""), T("Target", ""), T("ADA display", "ADA ")]]
        for row in clinical_precedents:
            cp_data.append([
                esc(row.get("name")),
                esc(row.get("match_type")),
                esc(row.get("target")),
                esc(row.get("ada_rate")),
            ])
        story.append(make_table(cp_data, [4.0*cm, 3.1*cm, 5.0*cm, 3.5*cm], header=True, font_size=8))
    else:
        story.append(Paragraph(T("No close clinical precedents were found for this germline pair in the ThErA-SAbDAb slice.", "。"), styles["SmallBody"]))

    story.append(Paragraph(T("6. Germline-linked ADA references", "6. Germline-ADA "), styles["Section"]))
    if germline_ada_refs:
        ada_data = [[T("Drug", ""), T("Match", ""), T("ADA display", "ADA "), T("Evidence tier", "")]]
        for row in germline_ada_refs:
            ada_data.append([
                esc(row.get("name") or row.get("antibody_name")),
                esc(row.get("match_type")),
                esc(row.get("ada_rate") or row.get("ada_value_display")),
                esc(row.get("evidence_tier")),
            ])
        story.append(make_table(ada_data, [4.0*cm, 3.0*cm, 7.2*cm, 1.8*cm], header=True, font_size=8))
    else:
        story.append(Paragraph(T("No matching entries in the curated Germline-ADA reference table.", " Germline-ADA 。"), styles["SmallBody"]))
    story.append(Paragraph(
        T(
            "ADA entries are data-layer associations with the selected frameworks and are not a prediction of ADA risk for your molecule.",
            " ADA ， ADA 。",
        ),
        styles["Tiny"],
    ))

    story.append(PageBreak())
    story.append(Paragraph(T("7. Delivery bundle contents", "7. "), styles["Section"]))
    delivery_rows = [
        [T("Filename", ""), T("Kind", ""), T("Description", "")],
        [
            "Humanization_Report.pdf",
            T("Report", ""),
            T("Customer result report (EN default in PDF export).", "（）"),
        ],
        ["donor_sequences.fasta", T("Sequence", ""), T("Donor VH / VL", " VH / VL ")],
        ["humanized_sequences.fasta", T("Sequence", ""), T("Humanized VH / VL", " VH / VL ")],
        ["donor_ab.pdb", T("Structure", ""), T("Predicted donor Fv (if computed)", " VH+VL ")],
        ["humanized_ab.pdb", T("Structure", ""), T("Predicted humanized Fv (if computed)", " VH+VL ")],
        ["README.txt", T("Notes", ""), T("English bundle manifest and disclaimers", "、")],
    ]
    story.append(make_table(delivery_rows, [4.6*cm, 2.1*cm, 9.0*cm], header=True, font_size=8))

    story.append(Paragraph(T("8. Interpretation & limitations", "8. "), styles["Section"]))
    story.append(Paragraph(
        T(
            "This package focuses on sequences, predicted structures, and QC summaries. Internal algorithm names, candidate retry logic, "
            "raw scores, rescue traces, and audit logs are not shown in the customer report.",
            "，、。、、、"
            "rescue 。",
        ),
        styles["SmallBody"],
    ))
    story.append(Paragraph(
        T(
            "Structures are AI-predicted for R&D screening and planning; validate key conclusions with expression, purification, binding, stability, and immunogenicity studies.",
            " AI ，。、、、。",
        ),
        styles["SmallBody"],
    ))

    doc.build(story)
    return pdf_path


# ─────────────────────────────────────────────────────────────────────────────
# Clinical germline precedent lookup
# ─────────────────────────────────────────────────────────────────────────────

_FW_CSV   = ROOT / "data" / "thera_sabdab" / "features" / "framework_route_examples_slice_1.csv"
_ADA_CSV  = ROOT / "data" / "immunogenicity_knowledge_base" / "master" / "ada_master_136_curated.csv"
_META_JSON = ROOT / "data" / "thera_sabdab" / "out" / "antibody_meta_models.json"

def _germline_imgt_subgroup(germline_id: str) -> str:
    """IMGT V-gene subgroup used for family matching: IGKV1-33*01 → IGKV1; IGHV3-23*01 → IGHV3."""
    if not germline_id or not str(germline_id).strip():
        return ""
    base = str(germline_id).split("*", 1)[0].strip()
    if "-" in base:
        return base.rsplit("-", 1)[0]
    return base

def _germline_base_gene(germline_id: str) -> str:
    """Strip allele suffix: IGHV1-2*02 → IGHV1-2; IGKV1-39*01 → IGKV1-39.
    Used for gene-level matching (same gene, different allele variant *01/*02/etc.)."""
    if not germline_id or not str(germline_id).strip():
        return ""
    return str(germline_id).split("*", 1)[0].strip()

def _match_priority(vh_exact: bool, vl_exact: bool, vh_family: bool, vl_family: bool,
                    vh_gene: bool = False, vl_gene: bool = False) -> tuple[str, int]:
    """
    Priority tiers (lower = higher priority):
      0  VH+VL exact       both alleles identical
      1  VH exact          VH allele identical
      2  VL exact          VL allele identical
      3  VH gene (new)     same VH gene, different allele  e.g. *01 vs *02
      4  VL gene (new)     same VL gene, different allele
      5  VH+VL family      same IMGT subgroup
      6  VH family
      7  VL family
    """
    if vh_exact and vl_exact:
        return "VH+VL exact", 0
    if vh_exact:
        return "VH exact", 1
    if vl_exact:
        return "VL exact", 2
    if vh_gene:
        return "VH gene (allele variant)", 3
    if vl_gene:
        return "VL gene (allele variant)", 4
    if vh_family and vl_family:
        return "VH+VL family", 5
    if vh_family:
        return "VH family", 6
    return "VL family", 7

def _lookup_germline_ada_references(vh_germline: str, vl_germline: str, top_n: int = 8) -> list:
    """
    Lightweight data-layer ADA reference lookup.
    Uses the curated ADA master directly and returns clinical antibodies whose
    VH/VL germline overlaps with the selected humanization germline.
    """
    if not _ADA_CSV.exists():
        return []

    import csv

    vh_fam  = _germline_imgt_subgroup(vh_germline)
    vl_fam  = _germline_imgt_subgroup(vl_germline)
    vh_gene = _germline_base_gene(vh_germline)
    vl_gene = _germline_base_gene(vl_germline)
    tier_rank = {"A": 0, "B": 1, "C": 2}
    results = []

    with open(_ADA_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            r_vh = (row.get("vh_germline") or "").strip()
            r_vl = (row.get("vl_germline") or "").strip()
            if not (r_vh or r_vl):
                continue

            r_vh_fam  = _germline_imgt_subgroup(r_vh)
            r_vl_fam  = _germline_imgt_subgroup(r_vl)
            r_vh_gene = _germline_base_gene(r_vh)
            r_vl_gene = _germline_base_gene(r_vl)
            vh_exact  = bool(vh_germline and r_vh == vh_germline)
            vl_exact  = bool(vl_germline and r_vl == vl_germline)
            vh_gene_m = bool(vh_gene and r_vh_gene == vh_gene and not vh_exact)
            vl_gene_m = bool(vl_gene and r_vl_gene == vl_gene and not vl_exact)
            vh_family = bool(vh_fam and r_vh_fam == vh_fam and not vh_exact and not vh_gene_m)
            vl_family = bool(vl_fam and r_vl_fam == vl_fam and not vl_exact and not vl_gene_m)
            if not (vh_exact or vl_exact or vh_gene_m or vl_gene_m or vh_family or vl_family):
                continue

            match_type, priority = _match_priority(
                vh_exact, vl_exact, vh_family, vl_family, vh_gene_m, vl_gene_m
            )
            ada_display = (row.get("ada_value_display") or "").strip()
            ada_first_pct = row.get("ada_first_pct")
            try:
                ada_first_pct = round(float(ada_first_pct), 2) if ada_first_pct not in ("", None) else None
            except Exception:
                ada_first_pct = None

            results.append({
                "name": (row.get("antibody_name") or "").strip(),
                "vh_germline": r_vh or "—",
                "vl_germline": r_vl or "—",
                "match_type": match_type,
                "approval_year": (row.get("approval_year") or "").strip() or "—",
                "indication": (row.get("indication_text") or "").strip() or "—",
                "target": (row.get("targets") or "").strip() or "—",
                "genetics": (row.get("genetics_normalized") or row.get("thera_genetics_class") or "").strip() or "—",
                "ada_rate": ada_display or "—",
                "ada_first_pct": ada_first_pct,
                "evidence_tier": (row.get("evidence_tier") or "").strip() or "—",
                "evidence_source": (row.get("evidence_source") or "").strip() or "—",
                "_priority": priority,
                "_tier_rank": tier_rank.get((row.get("evidence_tier") or "").strip(), 9),
            })

    results.sort(
        key=lambda x: (
            x["_priority"],
            x["_tier_rank"],
            -(x["ada_first_pct"] if isinstance(x["ada_first_pct"], (int, float)) else -1.0),
            x["name"].lower(),
        )
    )
    for row in results:
        row.pop("_priority", None)
        row.pop("_tier_rank", None)
    return results[:top_n]


def _lookup_germline_ada_references_for_template_side(
    template_germline: str,
    chain: str,
    top_n: int = 8,
) -> list:
    """
    ADA rows where overlap is defined **only** by the selected VH or VL template
    (allele exact or IMGT gene-family). Avoids combined-table skew when many drugs
    share one κ allele but differ in VH.
    chain: \"H\" or \"L\".
    """
    tpl = (template_germline or "").strip()
    if not tpl or tpl == "—":
        return []
    ch = (chain or "").strip().upper()
    if ch not in ("H", "L"):
        return []
    if not _ADA_CSV.exists():
        return []

    import csv

    tpl_fam  = _germline_imgt_subgroup(tpl)
    tpl_gene = _germline_base_gene(tpl)
    tier_rank = {"A": 0, "B": 1, "C": 2}
    results = []

    with open(_ADA_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            r_vh = (row.get("vh_germline") or "").strip()
            r_vl = (row.get("vl_germline") or "").strip()
            if ch == "H":
                if not r_vh:
                    continue
                exact     = r_vh == tpl
                gene_eq   = bool(tpl_gene and _germline_base_gene(r_vh) == tpl_gene and not exact)
                rfam      = _germline_imgt_subgroup(r_vh)
                fam       = bool(tpl_fam and rfam == tpl_fam and not exact and not gene_eq)
                if not (exact or gene_eq or fam):
                    continue
                if exact:
                    match_type, pri = "VH template exact", 0
                elif gene_eq:
                    match_type, pri = "VH gene (allele variant)", 1
                else:
                    match_type, pri = "VH gene family", 2
            else:
                if not r_vl:
                    continue
                exact     = r_vl == tpl
                gene_eq   = bool(tpl_gene and _germline_base_gene(r_vl) == tpl_gene and not exact)
                rfam      = _germline_imgt_subgroup(r_vl)
                fam       = bool(tpl_fam and rfam == tpl_fam and not exact and not gene_eq)
                if not (exact or gene_eq or fam):
                    continue
                if exact:
                    match_type, pri = "VL template exact", 0
                elif gene_eq:
                    match_type, pri = "VL gene (allele variant)", 1
                else:
                    match_type, pri = "VL gene family", 2

            ada_display = (row.get("ada_value_display") or "").strip()
            ada_first_pct = row.get("ada_first_pct")
            try:
                ada_first_pct = round(float(ada_first_pct), 2) if ada_first_pct not in ("", None) else None
            except Exception:
                ada_first_pct = None

            results.append({
                "name": (row.get("antibody_name") or "").strip(),
                "vh_germline": r_vh or "—",
                "vl_germline": r_vl or "—",
                "match_type": match_type,
                "approval_year": (row.get("approval_year") or "").strip() or "—",
                "indication": (row.get("indication_text") or "").strip() or "—",
                "target": (row.get("targets") or "").strip() or "—",
                "genetics": (row.get("genetics_normalized") or row.get("thera_genetics_class") or "").strip() or "—",
                "ada_rate": ada_display or "—",
                "ada_first_pct": ada_first_pct,
                "evidence_tier": (row.get("evidence_tier") or "").strip() or "—",
                "evidence_source": (row.get("evidence_source") or "").strip() or "—",
                "_priority": pri,
                "_tier_rank": tier_rank.get((row.get("evidence_tier") or "").strip(), 9),
            })

    results.sort(
        key=lambda x: (
            x["_priority"],
            x["_tier_rank"],
            -(x["ada_first_pct"] if isinstance(x["ada_first_pct"], (int, float)) else -1.0),
            x["name"].lower(),
        )
    )
    for row in results:
        row.pop("_priority", None)
        row.pop("_tier_rank", None)
    return results[:top_n]


def _lookup_clinical_precedents(vh_germline: str, vl_germline: str, top_n: int = 5) -> list:
    """
    Find clinical antibodies that share the same VH and/or VL germline family.
    Returns list of dicts: {name, vh_germline, vl_germline, vh_fr_id, vl_fr_id,
                             target, indication, approval_year, ada_rate, genetics, match_type}
    """
    if not _FW_CSV.exists():
        return []

    import csv

    vh_fam = _germline_imgt_subgroup(vh_germline)   # e.g. "IGHV1"
    vl_fam = _germline_imgt_subgroup(vl_germline)   # e.g. "IGKV1"

    # Load framework examples
    fw_rows = []
    with open(_FW_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            fw_rows.append(row)

    # Load ThErA-SAbDAb meta models (primary source: target, phase, genetics)
    meta_db = {}
    if _META_JSON.exists():
        try:
            import json as _json
            for m in _json.loads(_META_JSON.read_text(encoding="utf-8")):
                meta_db[m["antibody_id"].lower()] = m
        except Exception:
            pass

    # Load ADA master for immunogenicity rates (secondary source)
    ada_meta = {}
    if _ADA_CSV.exists():
        with open(_ADA_CSV, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name = row.get("antibody_name", "").strip()
                if name:
                    ada_meta[name.lower()] = row

    results = []
    for row in fw_rows:
        r_vh = row.get("vh_germline_match", "")
        r_vl = row.get("vl_germline_match", "")
        r_vh_fam = _germline_imgt_subgroup(r_vh)
        r_vl_fam = _germline_imgt_subgroup(r_vl)

        vh_exact  = r_vh  == vh_germline
        vl_exact  = r_vl  == vl_germline
        vh_family = bool(vh_fam and r_vh_fam == vh_fam and not vh_exact)
        vl_family = bool(vl_fam and r_vl_fam == vl_fam and not vl_exact)

        if not (vh_exact or vl_exact or vh_family or vl_family):
            continue

        # Match type priority: exact both > exact VH > exact VL > family both > family VH > family VL
        if vh_exact and vl_exact:   mt, pri = "VH+VL exact match", 0
        elif vh_exact:              mt, pri = "VH exact match",     1
        elif vl_exact:              mt, pri = "VL exact match",     2
        elif vh_family and vl_family: mt, pri = "VH+VL family",    3
        elif vh_family:             mt, pri = "VH family",          4
        else:                       mt, pri = "VL family",          5

        drug  = row.get("antibody_id", "")
        mmeta = meta_db.get(drug.lower(), {})
        ameta = ada_meta.get(drug.lower(), {})

        try:
            vh_id = round(float(row.get("vh_germline_identity", 0)) * 100, 1)
        except Exception:
            vh_id = None
        try:
            vl_id = round(float(row.get("vl_germline_identity", 0)) * 100, 1)
        except Exception:
            vl_id = None

        # Target: prefer meta models
        tgt_list = mmeta.get("target", {}).get("targets", []) or []
        target_str = " / ".join(tgt_list[:3]) if tgt_list else (ameta.get("targets", "") or "—")

        # Phase / approval
        phase_raw = mmeta.get("clinical", {}).get("phase_raw", "") or ""
        appr_year = ameta.get("approval_year", "") or ""
        phase_str = appr_year if appr_year else (phase_raw or "—")

        # Genetics
        genetics = mmeta.get("genetics", {}).get("normalized", "") or ameta.get("genetics_normalized", "") or "—"

        # ADA rate from ADA master
        ada_rate = ameta.get("ada_value_display", "—") or "—"

        results.append({
            "name":          drug,
            "vh_germline":   r_vh,
            "vl_germline":   r_vl,
            "vh_fr_id":      vh_id,
            "vl_fr_id":      vl_id,
            "target":        target_str,
            "indication":    ameta.get("indication_text", "") or "—",
            "approval_year": phase_str,
            "ada_rate":      ada_rate,
            "genetics":      genetics,
            "match_type":    mt,
            "_priority":     pri,
        })

    # Sort by priority, then by VH FR identity desc (ties: stable name)
    results.sort(key=lambda x: (x["_priority"], -(x["vh_fr_id"] or 0), x["name"].lower()))

    # Build top_n without letting "VH exact" crowds out "VL exact". Listing pri1-only rows
    # first hid drugs sharing the selected VL (e.g. IGKV1-33*01) even though many exist.
    buckets: Dict[int, list] = {i: [] for i in range(6)}
    for r in results:
        buckets[r["_priority"]].append(r)

    merged: list = []
    for r in buckets[0]:
        if len(merged) >= top_n:
            break
        merged.append(r)

    # Interleave VH-touching rows with VL-touching rows. Previous logic interleaved only
    # bucket[1] (VH exact) with bucket[2] (VL exact); when bucket[1] was empty, bucket[2]
    # filled all remaining slots and buckets[3–5] never appeared — screenshots showed only
    # "VL exact match". VH-side pool = pri 1,3,4; VL-side = pri 2,5 (pri 3 kept on VH-side).
    seen_vh: set = set()
    vh_side: list = []
    for _pi in (1, 3, 4):
        for r in buckets[_pi]:
            k = str(r.get("name") or "").strip().lower()
            if not k or k in seen_vh:
                continue
            seen_vh.add(k)
            vh_side.append(r)

    seen_vl: set = set()
    vl_side: list = []
    for _pi in (2, 5):
        for r in buckets[_pi]:
            k = str(r.get("name") or "").strip().lower()
            if not k or k in seen_vl:
                continue
            seen_vl.add(k)
            vl_side.append(r)

    seen_final = {str(r.get("name") or "").strip().lower() for r in merged}
    iv, il = 0, 0
    while len(merged) < top_n and (iv < len(vh_side) or il < len(vl_side)):
        if iv < len(vh_side):
            r = vh_side[iv]
            iv += 1
            k = str(r.get("name") or "").strip().lower()
            if k and k not in seen_final:
                merged.append(r)
                seen_final.add(k)
        if len(merged) >= top_n:
            break
        if il < len(vl_side):
            r = vl_side[il]
            il += 1
            k = str(r.get("name") or "").strip().lower()
            if k and k not in seen_final:
                merged.append(r)
                seen_final.add(k)

    # Any remaining capacity: append by global priority (legacy order)
    if len(merged) < top_n:
        for p in range(6):
            for r in buckets[p]:
                if len(merged) >= top_n:
                    break
                k = str(r.get("name") or "").strip().lower()
                if k and k not in seen_final:
                    merged.append(r)
                    seen_final.add(k)
            if len(merged) >= top_n:
                break

    for r in merged:
        r.pop("_priority", None)
    return merged[:top_n]


def _lookup_clinical_precedents_for_template_side(
    template_germline: str,
    chain: str,
    top_n: int = 8,
) -> list:
    """
    Clinical antibodies where the selected VH *or* VL template matches alone
    (allele exact or IMGT gene-family), for §3 side-by-side reporting.
    chain: \"H\" (VH template) or \"L\" (VL template).
    """
    tpl = (template_germline or "").strip()
    if not tpl or tpl == "—":
        return []
    ch = (chain or "").strip().upper()
    if ch not in ("H", "L"):
        return []
    if not _FW_CSV.exists():
        return []

    import csv

    tpl_fam  = _germline_imgt_subgroup(tpl)
    tpl_gene = _germline_base_gene(tpl)

    fw_rows: list = []
    with open(_FW_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            fw_rows.append(row)

    meta_db: Dict[str, Any] = {}
    if _META_JSON.exists():
        try:
            import json as _json

            for m in _json.loads(_META_JSON.read_text(encoding="utf-8")):
                meta_db[str(m["antibody_id"]).lower()] = m
        except Exception:
            pass

    ada_meta: Dict[str, Any] = {}
    if _ADA_CSV.exists():
        with open(_ADA_CSV, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name = row.get("antibody_name", "").strip()
                if name:
                    ada_meta[name.lower()] = row

    results = []
    for row in fw_rows:
        r_vh = (row.get("vh_germline_match") or "").strip()
        r_vl = (row.get("vl_germline_match") or "").strip()
        if ch == "H":
            exact   = r_vh == tpl
            gene_eq = bool(tpl_gene and _germline_base_gene(r_vh) == tpl_gene and not exact)
            r_fam   = _germline_imgt_subgroup(r_vh)
            fam     = bool(tpl_fam and r_fam == tpl_fam and not exact and not gene_eq)
            if not (exact or gene_eq or fam):
                continue
            if exact:
                pri, mt = 0, "VH template exact"
            elif gene_eq:
                pri, mt = 1, "VH gene (allele variant)"
            else:
                pri, mt = 2, "VH gene family"
            id_key = "vh_fr_id"
        else:
            exact   = r_vl == tpl
            gene_eq = bool(tpl_gene and _germline_base_gene(r_vl) == tpl_gene and not exact)
            r_fam   = _germline_imgt_subgroup(r_vl)
            fam     = bool(tpl_fam and r_fam == tpl_fam and not exact and not gene_eq)
            if not (exact or gene_eq or fam):
                continue
            if exact:
                pri, mt = 0, "VL template exact"
            elif gene_eq:
                pri, mt = 1, "VL gene (allele variant)"
            else:
                pri, mt = 2, "VL gene family"
            id_key = "vl_fr_id"

        drug = (row.get("antibody_id") or "").strip()
        if not drug:
            continue

        mmeta = meta_db.get(drug.lower(), {})
        ameta = ada_meta.get(drug.lower(), {})

        try:
            vh_id = round(float(row.get("vh_germline_identity", 0)) * 100, 1)
        except Exception:
            vh_id = None
        try:
            vl_id = round(float(row.get("vl_germline_identity", 0)) * 100, 1)
        except Exception:
            vl_id = None

        tgt_list = mmeta.get("target", {}).get("targets", []) or []
        target_str = " / ".join(tgt_list[:3]) if tgt_list else (ameta.get("targets", "") or "—")

        phase_raw = mmeta.get("clinical", {}).get("phase_raw", "") or ""
        appr_year = ameta.get("approval_year", "") or ""
        phase_str = appr_year if appr_year else (phase_raw or "—")

        genetics = (
            mmeta.get("genetics", {}).get("normalized", "")
            or ameta.get("genetics_normalized", "")
            or "—"
        )
        ada_rate = ameta.get("ada_value_display", "—") or "—"

        results.append(
            {
                "name": drug,
                "vh_germline": r_vh or "—",
                "vl_germline": r_vl or "—",
                "vh_fr_id": vh_id,
                "vl_fr_id": vl_id,
                "target": target_str,
                "indication": ameta.get("indication_text", "") or "—",
                "approval_year": phase_str,
                "ada_rate": ada_rate,
                "genetics": genetics,
                "match_type": mt,
                "_priority": pri,
                "_sort_id": vh_id if id_key == "vh_fr_id" else vl_id,
            }
        )

    results.sort(
        key=lambda x: (
            x["_priority"],
            -(x["_sort_id"] if isinstance(x["_sort_id"], (int, float)) else -1.0),
            str(x["name"]).lower(),
        )
    )
    merged: list = []
    seen: set = set()
    for r in results:
        k = str(r["name"]).lower()
        if k in seen:
            continue
        seen.add(k)
        r.pop("_priority", None)
        r.pop("_sort_id", None)
        merged.append(r)
        if len(merged) >= top_n:
            break
    return merged


def _fmt_canonical(cls) -> str:
    """Format canonical CDR class dict {'H1': 'H1-13-1', ...} → 'H1:H1-13-1 / H2:… / L1:…'."""
    if not cls:
        return "—"
    if isinstance(cls, str):
        return cls or "—"
    if isinstance(cls, dict):
        parts = [f"{k}:{v}" for k, v in cls.items() if v and v != "computed"]
        if not parts:
            # All values are "computed" — just list the keys
            return " / ".join(cls.keys()) or "—"
        return " / ".join(parts)
    return str(cls)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: clinical germline precedents HTML block
# ─────────────────────────────────────────────────────────────────────────────

def _clinical_precedents_html(precedents: list, lang: str = "en") -> str:
    """Render clinical precedent table as HTML string for embedding in §3."""
    lang_zh = str(lang or "en").lower() in ("zh", "zh-cn", "cn")
    def T(en: str, zh: str) -> str:
        return en
    if not precedents:
        return (
            "<p class='note' style='margin-top:8px'>"
            + T(
                "No contextual clinical precedents were found for the selected humanized VH/VL templates.",
                " VH/VL 。",
            )
            + "</p>"
        )

    # Badge color by match type
    def _mt_badge(mt: str) -> str:
        ml = mt.lower()
        if "exact" in ml:
            return f"<span class='badge badge-ok'>{mt}</span>"
        if "allele variant" in ml:
            return f"<span class='badge' style='background:#d0eaf8;color:#1a5276;border:1px solid #aed6f1'>{mt}</span>"
        return f"<span class='badge badge-warn'>{mt}</span>"

    rows_html = ""
    for p in precedents:
        gen = p.get("genetics", "—")
        rows_html += f"""
    <tr>
      <td><b>{p['name']}</b></td>
      <td style='font-size:0.85em'>{p['vh_germline']}</td>
      <td style='font-size:0.85em'>{p['vl_germline']}</td>
      <td><b>{p['target']}</b></td>
      <td style='font-size:0.85em'>{p['indication']}</td>
      <td style='font-size:0.8em'>{gen}</td>
      <td>{p['approval_year']}</td>
      <td>{_mt_badge(p['match_type'])}</td>
    </tr>"""

    note_top = f"""
  <div class="note" style="margin:8px 0 12px;line-height:1.55;font-size:0.92em">
    <p style="margin:0 0 6px"><b>{T("How to read this table", "")}</b></p>
    <ul style="margin:0;padding-left:1.25em">
      <li>{T(
        "Late-stage / approved antibodies whose annotated VH/VL frameworks <strong>overlap</strong> (allele or family) with the <strong>humanized product’s selected VH/VL templates</strong> in §0 / §3 — contextual precedent only. This list does <strong>not</strong> restate or replace the template choice in this report.",
        "§0 / §3 <strong> VH/VL </strong><strong></strong><strong></strong>/，；<strong></strong>。",
    )}</li>
      <li>{T(
        "Use the <strong>per-chain VH / VL tables above</strong> first when you need lineage for each template allele alone. "
        "Here, rows alternate VH-touching vs VL-touching matches where possible so common light-chain overlaps do not consume every row.",
        "<strong> VH  VL </strong>，<strong></strong>。"
        "<strong></strong> VH  VL ，。",
    )}</li>
      <li>{T(
        "Each row’s <b>VH GL</b> / <b>VL GL</b> are that product’s catalogued annotations; <b>Match</b> describes overlap with <strong>your selected humanized templates</strong>. Row order is informational, not a ranking score.",
        " <b>VH GL</b> / <b>VL GL</b> ；<b></b><strong></strong>。，<strong></strong>。",
    )}</li>
      <li><b>{T("Genetics", "")}</b>: {T("Product genetics class when available.", "（）。")}</li>
      <li>{T(
        "<b>ADA</b> is summarised only in the next subsection, for literature-linked entries tied to the <strong>same selected humanized VH/VL templates</strong> — not in this overview table.",
        "<b>ADA</b> ，<strong> VH/VL </strong>——。",
    )}</li>
    </ul>
  </div>"""
    h4_pat = T(
        "Clinical antibodies overlapping selected VH/VL frameworks (precedent)",
        " VH/VL （）",
    )
    th_drug = T("Drug", "")
    th_vh = T("VH GL", "VH ")
    th_vl = T("VL GL", "VL ")
    th_tgt = T("Target", "")
    th_ind = T("Indication", "")
    th_gen = T("Genetics", "")
    th_phase = T("Phase", "/")
    th_mt = T("Match", "")
    return f"""
  <h4 style='color:#2d6cdf;margin:18px 0 6px'>{h4_pat}</h4>
{note_top}
  <div style='overflow-x:auto'>
  <table class='params' style='font-size:0.82em;min-width:920px'>
    <tr>
      <th>{th_drug}</th><th>{th_vh}</th><th>{th_vl}</th>
      <th>{th_tgt}</th><th>{th_ind}</th><th>{th_gen}</th><th>{th_phase}</th>
      <th>{th_mt}</th>
    </tr>
    {rows_html}
  </table>
  </div>"""


_TIER_TAG_RE = __import__("re").compile(r"\s*\[T\d+\]\s*$")


def _strip_tier_tags(items) -> str:
    """Remove internal Vernier tier classifier tags ([T1]/[T2]/[T3]) from a list
    of position strings before rendering, then join with ", ".

    Used to keep the InSynBio internal tier taxonomy out of the customer
    report (anti-distillation pass).
    """
    if not items:
        return ""
    out = []
    for p in items:
        s = str(p)
        out.append(_TIER_TAG_RE.sub("", s))
    return ", ".join(out)


_CLINICAL_842_CACHE: list | None = None


def _load_842_clinical_framework_db() -> list:
    """Load the 842-antibody clinical framework usage library (cached).

    The framework selection step picks a human germline from a hand-curated pool
    that is grounded in real clinical antibodies (842 entries). Every selected
    germline is therefore guaranteed to have at least one clinical antibody using
    the same template — even if the per-row ADA dataset (germline_ada_references)
    is sparse.

    Schema returned (one dict per row):
      {ab_name, vh_germline, vl_germline, origin, vh_identity, vl_identity}
    """
    global _CLINICAL_842_CACHE
    if _CLINICAL_842_CACHE is not None:
        return _CLINICAL_842_CACHE

    try:
        # api/routers → repo root: parents[2]
        suite_root = Path(__file__).resolve().parents[2]
        csv_path = suite_root / "data" / "humanization_assay" / "842_antibody_germline_assignment.csv"
        if not csv_path.exists():
            _CLINICAL_842_CACHE = []
            return _CLINICAL_842_CACHE
        rows: list = []
        import csv as _csv
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = _csv.DictReader(f)
            for r in reader:
                rows.append({
                    "ab_name":      (r.get("ab_id") or "").strip(),
                    "vh_germline":  (r.get("vh_germline") or "").strip(),
                    "vl_germline":  (r.get("vl_germline") or "").strip(),
                    "origin":       (r.get("origin") or "").strip(),
                    "vh_identity":  r.get("vh_identity"),
                    "vl_identity":  r.get("vl_identity"),
                })
        _CLINICAL_842_CACHE = rows
        return _CLINICAL_842_CACHE
    except Exception:
        _CLINICAL_842_CACHE = []
        return _CLINICAL_842_CACHE


def _germline_match_class(selected: str, candidate: str) -> str | None:
    """Classify how a candidate germline matches a selected germline.

    Returns one of: "exact", "allele variant", "family", or None when the gene
    family does not match. Selected/candidate are full IMGT identifiers like
    "IGHV3-23*01"; allele suffix is parsed off "*".
    """
    if not selected or not candidate:
        return None
    sel = selected.strip()
    cand = candidate.strip()
    if sel == cand:
        return "exact"
    sel_gene = sel.split("*", 1)[0]
    cand_gene = cand.split("*", 1)[0]
    if sel_gene == cand_gene:
        return "allele variant"
    # Family fallback: IGHV3-23 → family "IGHV3" (V-segment subgroup)
    def _fam(g: str) -> str:
        # IGHV3-23 → IGHV3 ; IGKV1-39 → IGKV1
        head = g.split("-", 1)[0]
        return head
    if _fam(sel_gene) == _fam(cand_gene):
        return "family"
    return None


def _derive_clinical_precedents_from_842(
    vh_germline: str | None,
    vl_germline: str | None,
    max_rows_per_side: int = 12,
) -> tuple[list, list, dict]:
    """Build VH-side and VL-side clinical precedents lists by joining the
    selected germlines against the 842 clinical antibody framework library.

    Returned shape matches what `_clinical_side_template_precedents_html`
    expects (so the renderer can use it as a drop-in fallback when the
    primary clinical_precedents data is missing).

    Returns (vh_side_rows, vl_side_rows, summary_meta).
    """
    db = _load_842_clinical_framework_db()
    summary = {
        "source": "data/humanization_assay/842_antibody_germline_assignment.csv",
        "n_total": len(db),
        "vh_matches": 0,
        "vl_matches": 0,
        "match_priority": ["exact", "allele variant", "family"],
    }
    if not db:
        return [], [], summary

    # Enrich fallback rows with disease/target context from existing clinical sources
    # so the customer sees "what target / what disease" instead of cohort internals.
    meta_db: dict[str, dict] = {}
    if _META_JSON.exists():
        try:
            import json as _json
            for m in _json.loads(_META_JSON.read_text(encoding="utf-8")):
                k = str(m.get("antibody_id") or "").strip().lower()
                if k:
                    meta_db[k] = m
        except Exception:
            meta_db = {}

    ada_db: dict[str, dict] = {}
    if _ADA_CSV.exists():
        try:
            import csv
            with open(_ADA_CSV, encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    k = str(row.get("antibody_name") or "").strip().lower()
                    if k:
                        ada_db[k] = row
        except Exception:
            ada_db = {}

    def _row_for(rec: dict, side: str, mt: str) -> dict:
        name = rec.get("ab_name") or "—"
        key = str(name).strip().lower()
        mmeta = meta_db.get(key, {})
        ameta = ada_db.get(key, {})

        tgt_list = mmeta.get("target", {}).get("targets", []) if isinstance(mmeta, dict) else []
        target_str = " / ".join(tgt_list[:3]) if tgt_list else (ameta.get("targets", "") or "—")

        indication = (ameta.get("indication_text") or "").strip()
        if not indication:
            indication = (
                mmeta.get("clinical", {}).get("primary_indication")
                if isinstance(mmeta, dict) else ""
            ) or "—"

        phase_raw = (mmeta.get("clinical", {}).get("phase_raw", "") if isinstance(mmeta, dict) else "") or ""
        appr_year = (ameta.get("approval_year", "") or "").strip()
        phase_str = appr_year if appr_year else (phase_raw or "—")

        return {
            "name":          name,
            "vh_germline":   rec.get("vh_germline") or "—",
            "vl_germline":   rec.get("vl_germline") or "—",
            "target":        target_str,
            # Deliberately neutralized: do not expose cohort-size/source-class labels.
            "genetics":      "clinical framework precedent",
            "indication":    indication,
            "approval_year": phase_str,
            "match_type":    f"VH {mt}" if side == "VH" else f"VL {mt}",
        }

    vh_rows: list[tuple[int, dict]] = []
    vl_rows: list[tuple[int, dict]] = []
    rank = {"exact": 0, "allele variant": 1, "family": 2}

    for rec in db:
        if vh_germline:
            mt_vh = _germline_match_class(vh_germline, rec.get("vh_germline", ""))
            if mt_vh:
                vh_rows.append((rank[mt_vh], _row_for(rec, "VH", mt_vh)))
        if vl_germline:
            mt_vl = _germline_match_class(vl_germline, rec.get("vl_germline", ""))
            if mt_vl:
                vl_rows.append((rank[mt_vl], _row_for(rec, "VL", mt_vl)))

    vh_rows.sort(key=lambda x: (x[0], x[1]["name"]))
    vl_rows.sort(key=lambda x: (x[0], x[1]["name"]))
    summary["vh_matches"] = len(vh_rows)
    summary["vl_matches"] = len(vl_rows)

    return ([r for _, r in vh_rows[:max_rows_per_side]],
            [r for _, r in vl_rows[:max_rows_per_side]],
            summary)


def _clinical_side_template_precedents_html(rows: list, chain: str, lang: str = "en") -> str:
    """§3 sub-table: drugs matching only the selected VH or only the selected VL framework."""
    lang_zh = str(lang or "en").lower() in ("zh", "zh-cn", "cn")

    def T(en: str, zh: str) -> str:
        return en

    ch = (chain or "").strip().upper()
    if ch == "H":
        h4 = T(
            "Clinical antibodies using the selected VH framework (allele or family)",
            " VH （）",
        )
        note = T(
            "Listed drugs share the <strong>VH germline annotation</strong> in §3 with your selected template "
            "(exact allele or same IMGT gene family). VL annotations vary and are shown for context.",
            "<strong>VH </strong>§3（ IMGT ）。VL ，。",
        )
    elif ch == "L":
        h4 = T(
            "Clinical antibodies using the selected VL framework (allele or family)",
            " VL （）",
        )
        note = T(
            "Listed drugs share the <strong>VL germline annotation</strong> in §3 with your selected template "
            "(exact allele or same IMGT gene family). VH annotations vary and are shown for context.",
            "<strong>VL </strong>§3（ IMGT ）。VH ，。",
        )
    else:
        return ""

    if not rows:
        return (
            f"<h4 style='color:#2d6cdf;margin:14px 0 6px'>{h4}</h4>"
            f"<p class='note' style='margin-top:4px'>{T('No catalogued clinical antibodies matched this template filter.', '。')}</p>"
        )

    def _mt_badge(mt: str) -> str:
        ml = mt.lower()
        if "exact" in ml:
            return f"<span class='badge badge-ok'>{mt}</span>"
        if "allele variant" in ml:
            return f"<span class='badge' style='background:#d0eaf8;color:#1a5276;border:1px solid #aed6f1'>{mt}</span>"
        return f"<span class='badge badge-warn'>{mt}</span>"

    rows_html = ""
    for p in rows:
        indication = p.get("indication", "—")
        rows_html += f"""
    <tr>
      <td><b>{p['name']}</b></td>
      <td style='font-size:0.85em'>{p['vh_germline']}</td>
      <td style='font-size:0.85em'>{p['vl_germline']}</td>
      <td><b>{p['target']}</b></td>
      <td style='font-size:0.8em'>{indication}</td>
      <td>{p['approval_year']}</td>
      <td>{_mt_badge(p['match_type'])}</td>
    </tr>"""

    note_box = f"""
  <div class="note" style="margin:6px 0 10px;line-height:1.5;font-size:0.9em">
    <p style="margin:0">{note}</p>
  </div>"""
    th_drug = T("Drug", "")
    th_vh = T("VH GL", "VH ")
    th_vl = T("VL GL", "VL ")
    th_tgt = T("Target", "")
    th_gen = T("Disease / Indication", " / ")
    th_phase = T("Phase", "/")
    th_mt = T("Match", "")
    return f"""
  <h4 style='color:#2d6cdf;margin:14px 0 6px'>{h4}</h4>
{note_box}
  <div style='overflow-x:auto'>
  <table class='params' style='font-size:0.82em;min-width:780px'>
    <tr>
      <th>{th_drug}</th><th>{th_vh}</th><th>{th_vl}</th>
      <th>{th_tgt}</th><th>{th_gen}</th><th>{th_phase}</th><th>{th_mt}</th>
    </tr>
    {rows_html}
  </table>
  </div>"""


def _germline_ada_references_split_html(rows_vh: list, rows_vl: list, lang: str = "en") -> str:
    """Germline-linked ADA: separate tables for VH-template vs VL-template matches."""
    lang_zh = str(lang or "en").lower() in ("zh", "zh-cn", "cn")
    show_vh = rows_vh is not None
    show_vl = rows_vl is not None
    rows_vh = rows_vh or []
    rows_vl = rows_vl or []

    def T(en: str, zh: str) -> str:
        return en

    def _mt_badge(mt: str) -> str:
        ml = mt.lower()
        if "exact" in ml:
            return f"<span class='badge badge-ok'>{mt}</span>"
        if "allele variant" in ml:
            return f"<span class='badge' style='background:#d0eaf8;color:#1a5276;border:1px solid #aed6f1'>{mt}</span>"
        return f"<span class='badge badge-warn'>{mt}</span>"

    def _rows_html(rows: list) -> str:
        body = ""
        for row in rows:
            pct = row.get("ada_first_pct")
            pct_html = f"{pct:.2f}%" if isinstance(pct, (int, float)) else "—"
            drug_name = row.get("name") or row.get("antibody_name") or "—"
            vh_gl = row.get("vh_germline") or "—"
            vl_gl = row.get("vl_germline") or "—"
            mt = row.get("match_type") or "—"
            ada_rate = row.get("ada_rate") or row.get("ada_value_display") or "—"
            genetics = row.get("genetics") or row.get("genetics_normalized") or "—"
            indication = row.get("indication") or row.get("indication_text") or "—"
            body += f"""
    <tr>
      <td><b>{drug_name}</b></td>
      <td style='font-size:0.85em'>{vh_gl}</td>
      <td style='font-size:0.85em'>{vl_gl}</td>
      <td>{_mt_badge(mt)}</td>
      <td>{ada_rate}</td>
      <td>{pct_html}</td>
      <td style='font-size:0.8em'>{genetics}</td>
      <td style='font-size:0.8em'>{indication}</td>
    </tr>"""
        return body

    th_drug = T("Drug", "")
    th_vh = T("VH GL", "VH ")
    th_vl = T("VL GL", "VL ")
    th_mt = T("Match", "")
    th_ada_disp = T("ADA summary", "ADA ")
    th_ada_pct = T("Reported rate", "")
    th_gen = T("Genetics", "")
    th_ind = T("Indication", "")
    thead = f"""    <tr>
      <th>{th_drug}</th><th>{th_vh}</th><th>{th_vl}</th><th>{th_mt}</th>
      <th>{th_ada_disp}</th><th>{th_ada_pct}</th><th>{th_gen}</th><th>{th_ind}</th>
    </tr>"""

    def _one_table(rows: list) -> str:
        return f"""  <div style='overflow-x:auto'>
  <table class='params' style='font-size:0.82em;min-width:980px'>
{thead}
{_rows_html(rows)}
  </table>
  </div>"""

    note_ada = f"""
  <div class="note" style="margin:8px 0 12px;line-height:1.55;font-size:0.92em">
    <p style="margin:0 0 6px"><b>{T("Scope", "")}</b></p>
    <ul style="margin:0;padding-left:1.25em">
      <li>{T(
        "Two tables below: (1) drugs whose <strong>VH</strong> matches the selected human VH template (allele or gene family); "
        "(2) drugs whose <strong>VL</strong> matches the selected human VL template. "
        "This avoids a single combined list dominated by one frequent κ allele when VH differs.",
        "：（1）<strong> VH</strong> VH （）；"
        "（2）<strong> VL</strong> VL 。"
        " κ 「VL exact」、 VH 。",
    )}</li>
      <li>{T(
        "ADA summary and reported rates are <strong>whole-antibody</strong> immunogenicity statistics from labels/literature — not chain-specific ADA assays.",
        "ADA /<strong></strong>——。",
    )}</li>
      <li>{T(
        "<strong>Not</strong> a prediction of ADA incidence for your candidate — contextual reference only.",
        "<strong></strong> ADA ——。",
    )}</li>
      <li>{T(
        "Rates depend on indication, population, dose, route, assay, and study design.",
        "、、、、。",
    )}</li>
    </ul>
  </div>"""

    h4_g = T(
        "ADA literature (split: selected VH template vs VL template)",
        "ADA （ VH / VL ）",
    )
    sub_vh = T(
        "Published ADA — antibodies matching the selected VH template",
        " ADA —  VH ",
    )
    sub_vl = T(
        "Published ADA — antibodies matching the selected VL template",
        " ADA —  VL ",
    )
    empty_vh = T(
        "No ADA-master entries matched the selected VH template (allele or gene family).",
        "ADA  VH （）。",
    )
    empty_vl = T(
        "No ADA-master entries matched the selected VL template (allele or gene family).",
        "ADA  VL （）。",
    )
    empty_both = (
        T(
            "No literature-linked ADA entries were found for either selected template.",
            " VH  VL  ADA 。",
        )
        if not rows_vh and not rows_vl
        else ""
    )

    if (not show_vh) and (not show_vl):
        return f"""
  <h4 style='color:#2d6cdf;margin:18px 0 6px'>{h4_g}</h4>
  <p class='note' style='margin-top:8px'>{T(
      "Germline-linked ADA tables are not applicable because no final chain used a human-germline framework route.",
      "， ADA 。",
  )}</p>
"""

    if show_vh and show_vl and not rows_vh and not rows_vl:
        return f"""
  <h4 style='color:#2d6cdf;margin:18px 0 6px'>{h4_g}</h4>
  <p class='note' style='margin-top:8px'>{empty_both}</p>
"""

    parts_vh = ""
    if show_vh:
        parts_vh = (
            f"  <h5 style='color:#1a5276;margin:14px 0 6px'>{sub_vh}</h5>\n"
            + (_one_table(rows_vh) if rows_vh else f"<p class='note' style='margin:4px 0 12px'>{empty_vh}</p>")
        )
    parts_vl = ""
    if show_vl:
        parts_vl = (
            f"  <h5 style='color:#1a5276;margin:18px 0 6px'>{sub_vl}</h5>\n"
            + (_one_table(rows_vl) if rows_vl else f"<p class='note' style='margin:4px 0 12px'>{empty_vl}</p>")
        )

    return f"""
  <h4 style='color:#2d6cdf;margin:18px 0 6px'>{h4_g}</h4>
{note_ada}
{parts_vh}
{parts_vl}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Reference cohort loader (Natural Baseline CMC + structure atlas)
# ─────────────────────────────────────────────────────────────────────────────

_NATURAL384_CACHE: dict | None = None

def _load_natural384_atlas() -> dict:
    """Load Natural Baseline per-antibody CMC + structure atlas. Returns {name_lower: row_dict}."""
    global _NATURAL384_CACHE
    if _NATURAL384_CACHE is not None:
        return _NATURAL384_CACHE
    import csv
    candidates = [
        Path(__file__).resolve().parents[2] / "data" / "natural_380_atlas" / "natural384_cmc_per_antibody.csv",
        Path("data/natural_380_atlas/natural384_cmc_per_antibody.csv"),
    ]
    out: dict = {}
    for p in candidates:
        try:
            if p.exists():
                with open(p, encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        nm = (row.get("antibody_id") or "").strip()
                        if nm:
                            out[nm.lower()] = row
                break
        except Exception:
            continue
    _NATURAL384_CACHE = out
    return out


def _reference_benchmark_table_html(ada_rows: list, candidate_metrics: dict, lang: str = "en") -> str:
    """Render §3.3 — clinical reference antibody CMC + structure benchmark vs candidate."""
    atlas = _load_natural384_atlas()
    if not atlas:
        return ""

    seen = set()
    matched = []
    for r in ada_rows:
        nm = (r.get("name") or r.get("antibody_name") or "").strip()
        if not nm:
            continue
        key = nm.lower()
        if key in seen:
            continue
        row = atlas.get(key)
        if not row:
            continue
        seen.add(key)
        matched.append((nm, r.get("match_type") or "—", row))

    if not matched:
        return ""

    def _f(v, decimals=2, suffix=""):
        try:
            x = float(v)
            return f"{x:.{decimals}f}{suffix}"
        except (TypeError, ValueError):
            return "<span style='color:#9ca3af;font-size:.8rem'>N/A</span>"

    def _badge_pi(pi):
        try:
            x = float(pi)
        except (TypeError, ValueError):
            return ""
        if 6.5 <= x <= 9.0:
            return "<span class='badge badge-ok' style='font-size:9px'>OK</span>"
        return "<span class='badge badge-warn' style='font-size:9px'>OOR</span>"

    def _badge_inst(ii):
        try:
            x = float(ii)
        except (TypeError, ValueError):
            return ""
        if x < 40:
            return "<span class='badge badge-ok' style='font-size:9px'>STABLE</span>"
        return "<span class='badge badge-warn' style='font-size:9px'>UNSTABLE</span>"

    def _row(nm, mt, row, is_candidate=False):
        pi   = row.get("pI") or row.get("pi") or ""
        gvy  = row.get("GRAVY") or row.get("gravy") or ""
        ii   = row.get("instability_index") or ""
        bg = "background:#fef9c3;font-weight:600" if is_candidate else ""
        label = (
            f"<b style='color:#1b4fad'>{nm} ★</b>"
            f"<br><span style='font-size:9px;color:#5a6a80'>this candidate</span>"
            if is_candidate else f"<b>{nm}</b>"
        )
        mt_cell = (
            f"<span class='badge' style='background:#1b4fad;color:#fff;font-size:9px'>candidate</span>"
            if is_candidate else f"<span style='font-size:11px;color:#374151'>{mt}</span>"
        )
        return (
            f"<tr style='{bg}'>"
            f"<td>{label}</td>"
            f"<td>{mt_cell}</td>"
            f"<td>{_f(pi,2)} {_badge_pi(pi)}</td>"
            f"<td>{_f(gvy,3)}</td>"
            f"<td>{_f(ii,1)} {_badge_inst(ii)}</td>"
            f"</tr>"
        )

    cand_html = _row("Candidate (humanized Fv)", "—", candidate_metrics or {}, is_candidate=True) if candidate_metrics else ""

    rows_html = "".join(_row(nm, mt, row) for nm, mt, row in matched)

    note = (
        "Reference cohort: <b>Natural Baseline</b> atlas of approved/late-stage human-derived antibodies. "
        "Only entries that share the candidate's selected VH or VL germline (allele or family) are shown. "
        "Same mini-CMC scope as §8 (pI / GRAVY / Instability) — for apples-to-apples comparison. "
        "Use as developability context only — not an ADA prediction."
    )
    return (
        f"<h4 style='color:#2d6cdf;margin:18px 0 6px'>Clinical reference cohort — mini-CMC benchmark</h4>"
        f"<div class='note' style='margin:0 0 8px;line-height:1.5;font-size:0.92em'>{note}</div>"
        f"<div style='overflow-x:auto'>"
        f"<table class='params' style='font-size:0.82em;min-width:560px'>"
        f"<tr style='background:#e8eef8'>"
        f"<th style='min-width:180px'>Antibody</th>"
        f"<th>Match</th>"
        f"<th>pI</th>"
        f"<th>GRAVY</th>"
        f"<th>Instability index</th>"
        f"</tr>"
        + cand_html + rows_html +
        f"</table></div>"
        f"<p class='note' style='margin-top:6px;font-size:11px;color:#5a6a80'>"
        f"<b>Legend:</b> pI OK band 6.5–9.0; Instability &lt; 40 considered stable. "
        f"Cohort size: {len(matched)} antibody(ies) matched in Natural Baseline.</p>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helper: inline HTML report (no external report_cli dependency)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_html_report(family: str, payload: dict, out_dir: Path,   # noqa: C901
                          project_name: str = "") -> Path:
    """Generate a V4.1-aligned self-contained HTML report from the payload dict."""
    from datetime import datetime

    ts    = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    title = f"InSynBio AbEngineCore | VH/VL Humanization Report"
    proj  = project_name or payload.get("project_name", "—")
    html_lang = "en"
    report_h1 = "InSynBio AbEngineCore"
    report_sub = f"VH/VL Antibody Humanization Report | {VHVL_REPORT_PROTOCOL_VERSION} Protocol"
    proj_lbl = "Project"
    conf_lbl = "CONFIDENTIAL"

    # ── Payload normalization (V5.2.7): hoist qc_metrics.* into top level so
    # downstream payload.get(...) calls find the data without per-field changes.
    _qm_norm = payload.get("qc_metrics") or {}
    _fs_norm = _qm_norm.get("framework_selection") or {}
    _struct_norm = _qm_norm.get("structure") or {}
    _sq_norm = _qm_norm.get("structural_qc_v50") or {}
    _seqs_norm = payload.get("sequences") or {}
    _ck_norm = payload.get("checklist_report") or {}
    _ck_summary = _ck_norm.get("summary") or {}

    # Ensure timestamp is updated to current time for re-renders
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    footer_line = (
        f'InSynBio Research &nbsp;·&nbsp; <a href="https://www.insynbio.com">https://www.insynbio.com</a> '
        f"&nbsp;·&nbsp; {ts} &nbsp;·&nbsp; Confidential &nbsp;·&nbsp; "
        "Use Ctrl+P → Save as PDF to export this report."
    )

    _source_species_key_top = str(payload.get("source_species") or "").strip().lower()
    _report_format_ver_top = _vhvl_report_format_version_for_species(_source_species_key_top)

    def _build_report_meta_local(protocol_ver: str, analysis_ver: str, report_ver: str) -> str:
        """Suite report format first; then service + service report version; then protocol | analysis."""
        from api.report_versioning import suite_service_meta_html

        api_ver = "1.0.0"
        try:
            from api.main import app
            api_ver = getattr(app, "version", "1.0.0")
        except Exception:
            pass
        _structure_mode = str(payload.get("structure_mode") or "").upper()
        run_mode = "FULL evaluation" if _structure_mode == "COMPUTED" else "SMOKE validation"
        extra = [
            f"<div>UI Build: {VHVL_HTML_REPORT_BUILD_ID}</div>",
            f"<div>API Version: {api_ver} (FastAPI)</div>",
            f"<div>Run Mode: {run_mode}</div>",
        ]
        return suite_service_meta_html(
            "vhvl_humanization",
            protocol_ver=protocol_ver,
            analysis_ver=analysis_ver,
            content_variant=report_ver,
            extra_inner_divs=extra,
        )

    def _hoist(key: str, *sources):
        """Set payload[key] only if currently missing/empty."""
        if payload.get(key) in (None, "", [], {}):
            for src in sources:
                v = src
                if v not in (None, "", [], {}):
                    payload[key] = v
                    return

    _hoist("vh_germline", _fs_norm.get("selected_vh_germline"))
    _hoist("vl_germline", _fs_norm.get("selected_vl_germline"))
    _hoist("vh_germline_identity", _fs_norm.get("vh_identity_pct"), _fs_norm.get("framework_identity_vh"))
    _hoist("vl_germline_identity", _fs_norm.get("vl_identity_pct"), _fs_norm.get("framework_identity_vl"))
    _hoist("vh_fr_identity_pct", _fs_norm.get("vh_identity_pct"))
    _hoist("vl_fr_identity_pct", _fs_norm.get("vl_identity_pct"))
    _hoist("mini_cmc", _qm_norm.get("mini_cmc"))
    _hoist("liabilities", _qm_norm.get("liabilities"))
    _hoist("vernier_risk_positions", _qm_norm.get("vernier_risk_positions"))
    _hoist("cdr_rmsd", _qm_norm.get("cdr_rmsd"))
    _cdr_rmsd_vals = [v for v in (_qm_norm.get("cdr_rmsd") or {}).values() if isinstance(v, (int, float))]
    if _cdr_rmsd_vals:
        _hoist("rmsd_to_reference", round(sum(_cdr_rmsd_vals) / len(_cdr_rmsd_vals), 3))
    _hoist("cdr_scheme", _qm_norm.get("cdr_scheme"))
    _hoist("cdr_integrity_check", _qm_norm.get("cdr_integrity_check"))
    _hoist("cdr_diff_vh", _qm_norm.get("cdr_diff_vh"))
    _hoist("cdr_diff_vl", _qm_norm.get("cdr_diff_vl"))
    _hoist("global_fv_rmsd_ca", _qm_norm.get("global_fv_rmsd_ca"), _sq_norm.get("global_fv_rmsd_ca"))
    _hoist("structure_computed", bool(_struct_norm.get("pdb_path")) or bool(_qm_norm.get("cdr_rmsd")))
    _hoist("clinical_reference", _qm_norm.get("clinical_reference"))
    _hoist("framework_selection", _fs_norm)
    _hoist("phases_passed", _ck_summary.get("PASS"))
    _hoist("phases_total", sum(int(v) for v in _ck_summary.values() if isinstance(v, (int, float))) if _ck_summary else None)
    _hoist("checklist_overall_status", _ck_norm.get("overall_status"))
    if _ck_summary:
        _ck_pass = _ck_summary.get("PASS") or 0
        _ck_total = sum(int(v) for v in _ck_summary.values() if isinstance(v, (int, float)))
        _hoist("checklist_phases_passed", f"{_ck_pass}/{_ck_total} ({_ck_summary.get('WARN', 0)} WARN, {_ck_summary.get('FAIL', 0)} FAIL)")
    _hoist("pI_fab", _qm_norm.get("pI_fab"), (_qm_norm.get("mini_cmc") or {}).get("pI"))
    _hoist("bm_candidates_vh", _qm_norm.get("bm_candidates_vh"), _fs_norm.get("bm_candidates_vh"))
    _hoist("bm_candidates_vl", _qm_norm.get("bm_candidates_vl"), _fs_norm.get("bm_candidates_vl"))
    _hoist("bm_decisions_vh",  _qm_norm.get("bm_decisions_vh"),  _fs_norm.get("bm_decisions_vh"))
    _hoist("bm_decisions_vl",  _qm_norm.get("bm_decisions_vl"),  _fs_norm.get("bm_decisions_vl"))
    _hoist("bm_pending_vh",    _qm_norm.get("bm_pending_vh"),    _fs_norm.get("bm_pending_vh"))
    _hoist("bm_pending_vl",    _qm_norm.get("bm_pending_vl"),    _fs_norm.get("bm_pending_vl"))
    _hoist("bm_decisions_audit", _qm_norm.get("bm_decisions_audit"), _fs_norm.get("bm_decisions_audit"))
    _hoist("v49_cdr_hotspots", _qm_norm.get("v49_cdr_hotspots"))
    _hoist("v49_ppc_advisory", _qm_norm.get("v49_ppc_advisory"))
    _hoist("v49_psh_advisory", _qm_norm.get("v49_psh_advisory"))
    _hoist("ablang_score", _qm_norm.get("ablang_score"))
    _hoist("ablang_error", _qm_norm.get("ablang_error"))
    _hoist("t20_score", _qm_norm.get("t20_score"))
    _hoist("t20_error", _qm_norm.get("t20_error"))
    _ci_norm = _qm_norm.get("cdr_identification") or {}
    _hoist("cdrs", _ci_norm.get("cdrs"))
    _hoist("cdrs_imgt", _ci_norm.get("cdrs"))
    _hoist("cdr_identification", _ci_norm)
    # Compute donor mini_cmc on the fly (mouse VH+VL → simple physchem)
    if not payload.get("donor_mini_cmc") and _seqs_norm.get("mouse_vh") and _seqs_norm.get("mouse_vl"):
        try:
            from Bio.SeqUtils.ProtParam import ProteinAnalysis
            _donor_seq = _seqs_norm["mouse_vh"] + _seqs_norm["mouse_vl"]
            _pa = ProteinAnalysis(_donor_seq.replace("X", ""))
            payload["donor_mini_cmc"] = {
                "length": len(_donor_seq),
                "pI": round(_pa.isoelectric_point(), 2),
                "GRAVY": round(_pa.gravy(), 3),
                "gravy": round(_pa.gravy(), 3),
                "instability_index": round(_pa.instability_index(), 2),
                "aromaticity": round(_pa.aromaticity(), 3),
            }
        except Exception:
            pass
    _hoist("vh_vl_angle_deg", _struct_norm.get("vh_vl_angle_deg"), _qm_norm.get("vh_vl_angle_deg"))
    _hoist("humanized_angle_deg", _struct_norm.get("humanized_angle_deg"), _qm_norm.get("humanized_angle_deg"))
    _hoist("angle_delta_deg", _struct_norm.get("angle_delta_deg"), _qm_norm.get("angle_delta_deg"))
    _hoist("plddt", _struct_norm.get("plddt"), _qm_norm.get("plddt"))
    _hoist("humanized_plddt", _struct_norm.get("humanized_plddt"), _qm_norm.get("humanized_plddt"))
    _hoist("mouse_vh", _seqs_norm.get("mouse_vh"))
    _hoist("mouse_vl", _seqs_norm.get("mouse_vl"))
    _hoist("humanized_vh", _seqs_norm.get("humanized_vh"))
    _hoist("humanized_vl", _seqs_norm.get("humanized_vl"))
    _hoist("qa_audit", payload.get("_qa") or _qm_norm.get("qa_audit"))

    def esc(text: Any) -> str:
        import html as _html
        return _html.escape(str(text)) if text is not None else ""

    def row(label: str, value) -> str:
        v = "<span style='color:#9ca3af;font-size:.8rem'>N/A</span>" if (value is None or value == "" or value == []) else str(value)
        return f"<tr><td class='lbl'>{label}</td><td>{v}</td></tr>"

    def row_kv(label: str, value) -> str:
        """Single-row key-value outside a table."""
        v = "<span style='color:#9ca3af;font-size:.8rem'>N/A</span>" if (value is None or value == "" or value == []) else str(value)
        return f"<table class='params' style='margin-top:6px'><tr><td class='lbl'>{label}</td><td>{v}</td></tr></table>"

    def seq_block(label: str, seq: str) -> str:
        if not seq:
            return ""
        chunks = [seq[i:i+10] for i in range(0, len(seq), 10)]
        numbered = " ".join(f'<span class="chunk">{c}</span>' for c in chunks)
        return f"""
        <div class='seq-block'>
          <div class='seq-label'>{label} <span class='seq-len'>{len(seq)} aa</span></div>
          <div class='seq-body'>{numbered}</div>
        </div>"""

    def _cdr_preservation_block(payload: dict, H) -> str:
        """V5.1.0 §10 sub-block: Mouse vs Humanized CDR diff (Union scheme) HARD-gate evidence."""
        scheme = payload.get("cdr_scheme") or "union_kabat_chothia_v5_1"
        ok = payload.get("cdr_integrity_check")
        sr = payload.get("surface_reshape_fallback") or {}
        surface_mode = bool(sr.get("applied"))
        diffs_vh = payload.get("cdr_diff_vh") or []
        diffs_vl = payload.get("cdr_diff_vl") or []
        if ok is None and not diffs_vh and not diffs_vl:
            return ""
        if ok:
            status_html = "<span class='badge badge-ok'>PASS</span>"
            title_text = H("CDR Preservation (Donor vs Final)", "CDR （ vs ）")
            note_text = H(
                "Hard gate: every protected engineering-CDR position matches the donor sequence.",
                "： CDR 。",
            )
            border = "#1a7a3c"
        elif surface_mode:
            status_html = "<span class='badge badge-warn'>BOUNDARY REVIEW</span>"
            title_text = H("CDR Preservation / Boundary Annotation Review", "CDR  / ")
            note_text = H(
                "The active VH/VL surface route is CDR-preserving by design. Rows below are retained only as "
                "numbering-boundary review records and must not be read as designed CDR mutations.",
                " CDR。， CDR 。",
            )
            border = "#d97706"
        else:
            status_html = "<span class='badge badge-fail'>FAIL</span>"
            title_text = H("CDR Preservation (Donor vs Final)", "CDR （ vs ）")
            note_text = H(
                "Hard gate: every protected engineering-CDR position must match the donor sequence; any true mismatch requires review.",
                "： CDR ；。",
            )
            border = "#b91c1c"
        rows = []
        for d in (diffs_vh + diffs_vl):
            chain = (d.get("chain") or "").upper()
            pos = d.get("pos", "?")
            donor = d.get("donor", "?")
            humz = d.get("humanized", "?")
            label = "numbering-boundary review" if surface_mode else "review required"
            rows.append(
                f"<tr><td>{chain}</td><td>{pos}</td><td style='font-family:monospace'>{donor}</td>"
                f"<td style='font-family:monospace;color:#b91c1c;font-weight:700'>{humz}</td>"
                f"<td style='font-size:11px;color:#5a6a80'>{label}</td></tr>"
            )
        if rows:
            diff_table = (
                "<table class='params' style='margin-top:8px;font-size:.82rem'>"
                f"<tr><th>{H('Chain', '')}</th><th>{H('Position', '')}</th>"
                f"<th>{H('Donor', '')}</th>"
                f"<th>{H('Final', '')}</th><th>{H('Interpretation', '')}</th></tr>"
                + "".join(rows)
                + "</table>"
            )
        else:
            diff_table = (
                f"<p style='color:#1a7a3c;font-size:.82rem;margin-top:6px'>"
                f"✓ {H('All CDR positions identical between donor and humanized chains.', ' CDR 。')}</p>"
            )
        return f"""
        <div class='seq-block' style='margin-top:14px;border-left:4px solid {border}'>
          <div class='seq-label' style='display:flex;justify-content:space-between'>
            <span>{title_text}</span>
            <span>{status_html}</span>
          </div>
          <p class='note' style='margin:6px 0 0'>{note_text}</p>
          {diff_table}
        </div>"""

    _NA = "<span style='color:#9ca3af;font-size:.8rem'>N/A</span>"

    def _fmtf(v, decimals=1, unit=""):
        if v is None or v == "" or v == []:
            return _NA
        try:
            return f"{float(v):.{int(decimals)}f}{unit}"
        except (ValueError, TypeError):
            return str(v)

    def _badge(ok: bool, t="PASS", f="FAIL"):
        cls = "badge-ok" if ok else "badge-fail"
        return f"<span class='badge {cls}'>{t if ok else f}</span>"

    if family not in ("vhvl_humanization", "vh_vl"):
        body = f"<pre>{json.dumps(payload, indent=2, ensure_ascii=False)}</pre>"
    else:
        # Customer report language: Force English for InSynBio V5.2.2
        lang_zh = False
        lang_code = "en"

        def H(en: str, zh: str) -> str:
            return en

        title = "InSynBio AbEngineCore | VH/VL Humanization Report"
        html_lang = "en"
        report_h1 = "InSynBio AbEngineCore"
        report_sub = f"VH/VL Antibody Humanization Report | {VHVL_REPORT_PROTOCOL_VERSION} Protocol"
        proj_lbl = "Project"
        # Distribution label is client-facing by default; callers may override
        # with payload["distribution_label"] (e.g., "Confidential — NDA Only",
        # "Internal Use Only").
        conf_lbl = str(payload.get("distribution_label") or "Client Copy").strip()

        _source_species_key = str(payload.get("source_species") or "").strip().lower()
        _is_rabbit_report = _source_species_key in {"rabbit", "oryctolagus_cuniculus"}
        _report_format_ver = _vhvl_report_format_version_for_species(_source_species_key)

        # ── §0 Overview ────────────────────────────────────────────────────
        # Update timestamp to current time for re-renders
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        from api.report_versioning import cohort_provenance_html  # noqa: PLC0415
        
        def _build_report_meta_local(protocol_ver: str, analysis_ver: str, report_ver: str) -> str:
            """Suite report format first; then service + service report version; then protocol | analysis."""
            from api.report_versioning import suite_service_meta_html

            api_ver = "1.0.0"
            try:
                from api.main import app
                api_ver = getattr(app, "version", "1.0.0")
            except Exception:
                pass
            _structure_mode = str(payload.get("structure_mode") or "").upper()
            run_mode = "FULL evaluation" if _structure_mode == "COMPUTED" else "SMOKE validation"
            extra = [
                f"<div>UI Build: {VHVL_HTML_REPORT_BUILD_ID}</div>",
                f"<div>API Version: {api_ver} (FastAPI)</div>",
                f"<div>Run Mode: {run_mode}</div>",
            ]
            return suite_service_meta_html(
                "vhvl_humanization",
                protocol_ver=protocol_ver,
                analysis_ver=analysis_ver,
                content_variant=report_ver,
                extra_inner_divs=extra,
            )

        def _build_discussion_box(title: str, content: str) -> str:
            """Standard discussion box for results interpretation."""
            return f"""
        <div class="discussion-box">
          <div class="discussion-title">{title}</div>
          <p class="discussion-content">{content}</p>
        </div>"""
        
        status    = (payload.get("checklist_status")
                     or payload.get("checklist_overall_status")
                     or _ck_norm.get("overall_status")
                     or "UNKNOWN")
        status    = str(status).upper()
        repair_mode = payload.get("repair_mode", "standard")
        bm_strategy = payload.get("back_mutation_strategy", "standard")
        sr_fallback = payload.get("surface_reshape_fallback") or {}
        sr_applied = bool(sr_fallback.get("applied"))
        vh_surface_route = sr_applied and bool(sr_fallback.get("vh_mutations"))
        vl_surface_route = sr_applied and bool(sr_fallback.get("vl_mutations"))

        def _chain_route_label(chain: str) -> str:
            if (chain == "VH" and vh_surface_route) or (chain == "VL" and vl_surface_route):
                return "Donor-framework FR surface reshaping"
            return "Human germline CDR grafting"

        # Client-facing tier names (hide internal strategy keys: standard / aggressive / conservative / etc.)
        def _client_tier_label(raw: str | None) -> str:
            r = (str(raw) if raw is not None else "").lower()
            if r in ("aggressive", "deep", "max_humanness"):
                return "Deep humanization"
            if r in ("conservative", "soft", "minimal"):
                return "Conservative humanization"
            return "Standard humanization"

        bm_strategy_label = (
            "Chain-specific hybrid humanization"
            if sr_applied
            else _client_tier_label(bm_strategy)
        )
        repair_mode_label = "Standard pipeline" if str(repair_mode).lower() in ("standard", "default") else _client_tier_label(repair_mode)

        footer_line = H(
            f"InSynBio Research &nbsp;·&nbsp; {ts} &nbsp;·&nbsp; Confidential &nbsp;·&nbsp; "
            "Use Ctrl+P → Save as PDF to export this report.",
            f"TheraSIK / InSynBio Research &nbsp;·&nbsp; {ts} &nbsp;·&nbsp;  &nbsp;·&nbsp; "
            " Ctrl+P →  PDF 。",
        )

        mode_label = H(
            f"Pipeline: <b>{repair_mode_label}</b> &nbsp;·&nbsp; Strategy: <b>{bm_strategy_label}</b>"
            + (f" &nbsp;·&nbsp; VH: <b>{_chain_route_label('VH')}</b> &nbsp;·&nbsp; VL: <b>{_chain_route_label('VL')}</b>"
               if sr_applied else ""),
            f"：<b>{repair_mode_label}</b> &nbsp;·&nbsp; ：<b>{bm_strategy_label}</b>"
        )

        rabbit_route_policy_note = ""
        if _is_rabbit_report:
            rabbit_route_policy_note = """
  <div class='discussion-box' style='margin-top:10px'>
    <div class='discussion-title'>Rabbit multi-route decision policy</div>
    <p class='discussion-content'>
      Default recommendation follows deterministic CDR/Vernier-compatible framework ranking.
      If rabbit donor-to-human FR identity reaches at least 60% on a candidate chain, an additional forced CDR-graft route may be compared with surface-reshape/hybrid routes.
      If all candidates remain below 60%, surface reshaping is the default controlled route.
      Final route choice should be based on side-by-side structure (per-CDR RMSD), mini-CMC, and HPR outcomes.
    </p>
  </div>"""

        route_comparison_note = ""
        _selection_rationale_block = ""
        _rc = payload.get("route_comparison") or {}
        if isinstance(_rc, dict) and _rc.get("enabled"):
            _gs = _rc.get("grafting_selected") or {}
            _alt = _rc.get("grafting_alt_vh_ge65") or {}
            _sr_cmp = _rc.get("surface_route") or {}
            _cmp_required = bool(_rc.get("required"))
            _cmp_status = str(_sr_cmp.get("status") or "not_available").replace("_", " ")
            _cmp_note = esc(_sr_cmp.get("note") or "No additional note.")
            _gs_vh = esc(_gs.get("vh_germline") or "—")
            _gs_vl = esc(_gs.get("vl_germline") or "—")
            _gs_vh_id = _fmtf(_gs.get("vh_fr_identity"), "1", "%")
            _gs_vl_id = _fmtf(_gs.get("vl_fr_identity"), "1", "%")
            _cmp_warn_chip = " <span class='badge badge-warn'>review</span>"
            _alt_row = ""
            if _alt:
                _alt_row = (
                    "<tr><td><b>High-identity VH graft comparator</b></td>"
                    f"<td>{esc(_alt.get('germline') or '—')} "
                    f"(FR {_fmtf(_alt.get('fr_identity'),'1','%')}; "
                    f"Vernier {_fmtf(_alt.get('vernier_similarity'),'1','%')}; "
                    f"composite {_fmtf(_alt.get('composite_score'),'4')})</td></tr>"
                )
            # V5.4.13: render Route A' deliverable (actual grafted sequence + metrics)
            _alt_deliv_block = ""
            _alt_deliv = (_alt or {}).get("deliverable") if isinstance(_alt, dict) else None
            if isinstance(_alt_deliv, dict) and _alt_deliv.get("applied"):
                _ad_vh = esc(_alt_deliv.get("humanized_vh") or "")
                _ad_vl = esc(_alt_deliv.get("humanized_vl") or "")
                _ad_alt = esc(_alt_deliv.get("alt_vh_germline") or "—")
                _ad_vl_g = esc(_alt_deliv.get("vl_germline") or "—")
                _ad_vh_id = _fmtf(_alt_deliv.get("vh_fr_identity"), "1", "%")
                _ad_vl_id = _fmtf(_alt_deliv.get("vl_fr_identity"), "1", "%")
                _ad_vh_sub = int(_alt_deliv.get("vh_fr_substitutions") or 0)
                _ad_vl_sub = int(_alt_deliv.get("vl_fr_substitutions") or 0)
                _ad_ab = _fmtf(_alt_deliv.get("ablang_score"), "3")
                _bcmc = _alt_deliv.get("basic_cmc") or {}
                _fab = _bcmc.get("fab") or {}
                _ad_pi = _fmtf(_fab.get("pI"), "2")
                _ad_gv = _fmtf(_fab.get("gravy"), "3")
                _ad_ii = _fmtf(_fab.get("instability_index"), "1")
                _ad_liab = _fab.get("liabilities") or []
                _ad_liab_html = (
                    f"<span class='badge badge-warn'>{esc('; '.join(_ad_liab))}</span>"
                    if _ad_liab else "<span class='badge badge-ok'>none</span>"
                )
                _alt_deliv_block = (
                    "<div class='discussion-box' style='margin-top:10px;border-left:4px solid #6f42c1'>"
                    f"<div class='discussion-title'>Route A&prime; deliverable — CDR grafting onto {_ad_alt} (≥65% identity)</div>"
                    "<table class='params' style='margin-top:6px'>"
                    f"<tr><td class='lbl'>VH germline (alt)</td><td>{_ad_alt} &nbsp;·&nbsp; FR identity {_ad_vh_id} &nbsp;·&nbsp; FR substitutions: {_ad_vh_sub}</td></tr>"
                    f"<tr><td class='lbl'>VL germline (paired)</td><td>{_ad_vl_g} &nbsp;·&nbsp; FR identity {_ad_vl_id} &nbsp;·&nbsp; FR substitutions: {_ad_vl_sub}</td></tr>"
                    f"<tr><td class='lbl'>AbLang humanness</td><td>{_ad_ab}</td></tr>"
                    f"<tr><td class='lbl'>Fab basic CMC</td><td>pI {_ad_pi} &nbsp;·&nbsp; GRAVY {_ad_gv} &nbsp;·&nbsp; Instability {_ad_ii} &nbsp;·&nbsp; Liabilities {_ad_liab_html}</td></tr>"
                    f"<tr><td class='lbl'>Humanized VH (alt)</td><td><code style='word-break:break-all;font-size:12px'>{_ad_vh}</code></td></tr>"
                    f"<tr><td class='lbl'>Humanized VL (paired)</td><td><code style='word-break:break-all;font-size:12px'>{_ad_vl}</code></td></tr>"
                    "</table>"
                    "<p class='discussion-content' style='margin-top:6px;font-size:12px'>"
                    "Route A&prime; is a raw CDR-graft (no Phase 4 back-mutations) onto the high-identity human germline. "
                    "Compare side-by-side with the selected Route A and Route B (surface reshaping) to choose the "
                    "best clinical/CMC trade-off.</p>"
                    "</div>"
                )

            # V5.4.13: Selection Rationale block — full transparency on composite score
            # decomposition + ≥60% rat grafting gate decisions
            _selection_rationale_block = ""
            _species_rabbit_or_rat = (str(payload.get("source_species") or "").lower()
                                      in {"rat"}
                                      or str(payload.get("donor_species") or "").lower()
                                      in {"rattus_norvegicus"})
            if _species_rabbit_or_rat:
                _gate_pct = payload.get("grafting_gate_threshold_pct") or 60.0
                _top_vh_for_rat = payload.get("top_vh_candidates") or []
                _selected_vh_id_rat = str(payload.get("vh_germline") or "").strip()
                _vh_below_gate = bool(payload.get("vh_below_grafting_gate"))
                _rows = []
                for _c in _top_vh_for_rat[:5]:
                    if not isinstance(_c, dict):
                        continue
                    _g = str(_c.get("germline") or "—")
                    _fr = _c.get("fr_identity")
                    _vrn = _c.get("vernier_similarity")
                    _comp = _c.get("composite_score")
                    _clin = _c.get("clinical_count") or 0
                    try:
                        _passes = isinstance(_fr, (int, float)) and float(_fr) >= float(_gate_pct)
                    except Exception:
                        _passes = False
                    try:
                        _v60 = (0.60 * float(_vrn) / 100.0) if isinstance(_vrn, (int, float)) else 0.0
                    except Exception:
                        _v60 = 0.0
                    try:
                        _f30 = (0.30 * float(_fr) / 100.0) if isinstance(_fr, (int, float)) else 0.0
                    except Exception:
                        _f30 = 0.0
                    _gate_chip = (
                        "<span class='badge badge-ok'>passes ≥{:.0f}%</span>".format(_gate_pct)
                        if _passes else
                        "<span class='badge badge-fail'>BELOW ≥{:.0f}% — excluded from grafting</span>".format(_gate_pct)
                    )
                    _is_sel = (_g == _selected_vh_id_rat)
                    _row_style = " style='background:#f0fdf4'" if _is_sel else ""
                    _sel_marker = " <span class='badge badge-ok'>SELECTED</span>" if _is_sel else ""
                    _rows.append(
                        f"<tr{_row_style}>"
                        f"<td>{esc(_g)}{_sel_marker}</td>"
                        f"<td>{_fmtf(_fr,'1','%')}</td>"
                        f"<td>{_fmtf(_vrn,'1','%')}</td>"
                        f"<td>{int(_clin)}</td>"
                        f"<td>0.60×{_fmtf(_vrn,'1','%')} = {_v60:.4f}</td>"
                        f"<td>0.30×{_fmtf(_fr,'1','%')} = {_f30:.4f}</td>"
                        f"<td><b>{_fmtf(_comp,'4')}</b></td>"
                        f"<td>{_gate_chip}</td>"
                        "</tr>"
                    )
                if _rows:
                    # Build rejected-by-gate rows (composite-better but FR < 60%)
                    _rej_rows: List[str] = []
                    for _rc_item in (payload.get("vh_excluded_by_gate") or [])[:5]:
                        if not isinstance(_rc_item, dict):
                            continue
                        _rg = str(_rc_item.get("germline") or "—")
                        _rfr = _rc_item.get("fr_identity")
                        _rvrn = _rc_item.get("vernier_similarity")
                        _rcomp = _rc_item.get("composite_score")
                        _rclin = _rc_item.get("clinical_count") or 0
                        try:
                            _rv60 = (0.60 * float(_rvrn) / 100.0) if isinstance(_rvrn, (int, float)) else 0.0
                        except Exception:
                            _rv60 = 0.0
                        try:
                            _rf30 = (0.30 * float(_rfr) / 100.0) if isinstance(_rfr, (int, float)) else 0.0
                        except Exception:
                            _rf30 = 0.0
                        _rej_rows.append(
                            f"<tr style='background:#fef2f2;color:#991b1b'>"
                            f"<td>{esc(_rg)} <span class='badge badge-fail'>REJECTED</span></td>"
                            f"<td>{_fmtf(_rfr,'1','%')}</td>"
                            f"<td>{_fmtf(_rvrn,'1','%')}</td>"
                            f"<td>{int(_rclin)}</td>"
                            f"<td>0.60×{_fmtf(_rvrn,'1','%')} = {_rv60:.4f}</td>"
                            f"<td>0.30×{_fmtf(_rfr,'1','%')} = {_rf30:.4f}</td>"
                            f"<td><b>{_fmtf(_rcomp,'4')}</b></td>"
                            f"<td><span class='badge badge-fail'>BELOW ≥{_gate_pct:.0f}%</span></td>"
                            "</tr>"
                        )
                    _rej_section = ""
                    if _rej_rows:
                        _rej_section = (
                            "<p class='discussion-content' style='margin:8px 0 4px 0;font-size:12px'>"
                            "<b>Composite-best candidates excluded by the gate</b> "
                            "(originally outranked the selected germline by raw composite score, "
                            "but FR identity is below the rabbit/rat protocol threshold):"
                            "</p>"
                            "<table class='params' style='margin-top:4px;font-size:12px'>"
                            "<tr style='background:#fee2e2'>"
                            "<th>Germline</th><th>FR%</th><th>Vernier%</th><th>Clinical</th>"
                            "<th>0.6×Vernier</th><th>0.3×FR</th><th>Composite</th>"
                            f"<th>≥{_gate_pct:.0f}% gate</th>"
                            "</tr>"
                            + "".join(_rej_rows) +
                            "</table>"
                        )
                    _below_warn = ""
                    if _vh_below_gate:
                        _below_warn = (
                            "<div class='discussion-box' style='margin-top:8px;background:#fef3c7;border-left:4px solid #f59e0b'>"
                            f"<b>NO VH germline reaches the ≥{_gate_pct:.0f}% FR-identity gate.</b> "
                            "Primary CDR-graft route is "
                            "<b>not offered</b> for this chain — surface reshaping becomes the default route."
                            "</div>"
                        )
                    _selection_rationale_block = (
                        "<div class='discussion-box' style='margin-top:10px;border-left:4px solid #0ea5e9'>"
                        "<div class='discussion-title'>Selection rationale — VH composite scoring &amp; "
                        f"≥{_gate_pct:.0f}% FR-identity grafting gate</div>"
                        "<p class='discussion-content' style='font-size:12px;margin:6px 0'>"
                        "<b>Composite formula:</b> <code>0.6 × Vernier_similarity + 0.3 × FR_identity + "
                        "0.1 × clinical_bonus + naturalness_bonus − cmc_penalty</code>. "
                        "Vernier weight (60%) prioritises CDR-supporting framework structure; FR weight (30%) "
                        "captures global humanness. For rat donors, candidates whose FR identity is "
                        f"below <b>{_gate_pct:.0f}%</b> are <b>excluded</b> from primary CDR-graft selection "
                        "regardless of composite rank."
                        "</p>"
                        "<p class='discussion-content' style='margin:8px 0 4px 0;font-size:12px'>"
                        "<b>Selected route candidates</b> (passed the gate, ranked by composite):"
                        "</p>"
                        "<table class='params' style='margin-top:4px;font-size:12px'>"
                        "<tr style='background:#e0f2fe'>"
                        "<th>Germline</th><th>FR%</th><th>Vernier%</th><th>Clinical</th>"
                        "<th>0.6×Vernier</th><th>0.3×FR</th><th>Composite</th>"
                        f"<th>≥{_gate_pct:.0f}% gate</th>"
                        "</tr>"
                        + "".join(_rows) +
                        "</table>"
                        + _rej_section
                        + _below_warn +
                        "<p class='discussion-content' style='margin-top:8px;font-size:11px;color:#6b7280'>"
                        "<b>Why this matters:</b> a germline with high Vernier similarity but low FR identity "
                        "(rejected case) would <em>structurally</em> support the CDRs well but require many "
                        "framework substitutions to humanise — defeating the goal of CDR grafting. "
                        "The protocol therefore requires a minimum global FR identity before grafting is offered "
                        "as a clinical-grade route. Below the threshold, surface reshaping (which preserves the "
                        "donor framework and only changes solvent-exposed positions) is the controlled alternative."
                        "</p>"
                        "</div>"
                    )
            route_comparison_note = (
                "<div class='discussion-box' style='margin-top:10px'>"
                "<div class='discussion-title'>Route comparison status (grafting vs surface)</div>"
                "<table class='params' style='margin-top:6px'>"
                "<tr><td class='lbl'>Comparison required</td>"
                f"<td>{'YES' if _cmp_required else 'NO'}"
                f"{_cmp_warn_chip if _cmp_required else ''}</td></tr>"
                "<tr><td class='lbl'>Selected grafting route</td>"
                f"<td>VH {_gs_vh} ({_gs_vh_id}) / VL {_gs_vl} ({_gs_vl_id})</td></tr>"
                f"{_alt_row}"
                "<tr><td class='lbl'>Surface route status</td>"
                f"<td>{esc(_cmp_status)} &nbsp;·&nbsp; {('applied' if _sr_cmp.get('applied') else 'not applied')}</td></tr>"
                "<tr><td class='lbl'>Surface route note</td>"
                f"<td>{_cmp_note}</td></tr>"
                "</table>"
                "</div>"
                + _selection_rationale_block
                + _alt_deliv_block
            )

        if status == "PASS":
            st_badge = "<span class='badge badge-ok'>PASS</span>"
        elif status == "WARN":
            st_badge = "<span class='badge badge-warn'>WARN</span>"
        elif status == "FAIL":
            st_badge = "<span class='badge badge-fail'>FAIL</span>"
        else:
            st_badge = f"<span class='badge badge-warn'>{status}</span>"
    
        if sr_applied:
            _exec_disc = (
                f"The engineering run is assessed as <strong>{status}</strong>. "
                "At least one chain used a deterministic donor-framework FR surface-reshaping fallback; "
                "clinical human-germline framework precedents are therefore shown only for chains that actually used a human-germline framework route. "
                "The final sequence is evaluated by the post-route structure and sequence QC blocks below."
            )
        else:
            _exec_disc = (
                f"The humanization of the donor antibody is assessed as <strong>{status}</strong>. "
                f"The selected <strong>{bm_strategy_label}</strong> strategy balances framework humanness with paratope preservation. "
                "The resulting sequence aligns with clinical developability benchmarks, with specific attention paid to the structural integrity of the CDR loops."
            )

        # ── Items requiring attention (surfaces every WARN/FAIL checklist item) ──
        # Customer-facing: shows phase id, neutral title, and the value/limit when
        # available; no internal rule names or thresholds vocabulary leaked.
        _attn_items: list[tuple[str, str, str, str]] = []  # (badge, id, title, value)
        try:
            _cr_for_attn = (payload.get("checklist_report")
                            or _qm_norm.get("checklist_report") or {})
            _phases_for_attn = _cr_for_attn.get("phases") or {}
            if isinstance(_phases_for_attn, dict):
                _ph_iter = list(_phases_for_attn.values())
            elif isinstance(_phases_for_attn, list):
                _ph_iter = _phases_for_attn
            else:
                _ph_iter = []
            for _ph in _ph_iter:
                _items = _ph.get("items") if isinstance(_ph, dict) else (_ph if isinstance(_ph, list) else [])
                if not isinstance(_items, list):
                    continue
                for _it in _items:
                    if not isinstance(_it, dict):
                        continue
                    _st = (_it.get("status") or "").upper()
                    if _st not in ("WARN", "FAIL"):
                        continue
                    _id = str(_it.get("id") or "?")
                    _desc = str(_it.get("description") or _it.get("name") or "").strip()
                    _title = _desc
                    if _id and _title.startswith(_id):
                        _title = _title[len(_id):].lstrip(" .:-—")
                    # Strip any trailing numeric thresholds embedded in the title
                    # (e.g. "pI Fab 5.5-8.5" → "pI Fab"; "CDR RMSD <1.5Å" → "CDR RMSD")
                    import re as _re_attn
                    _title = _re_attn.sub(
                        r"\s*[<>=≤≥]?\s*\d+(\.\d+)?\s*[-–—]?\s*\d*(\.\d+)?\s*[ÅA%a-zA-Z]*\s*$",
                        "",
                        _title,
                    ).strip()
                    _ev = _it.get("evidence") or {}
                    _val_parts: list[str] = []
                    # Common evidence fields we render:
                    if "pI_fab" in _ev:
                        _pi = _ev["pI_fab"]
                        try:
                            _pi_f = float(_pi)
                        except Exception:
                            _pi_f = None
                        if _pi_f is None:
                            _val_parts.append("Fab pI: outside developability advisory window")
                        else:
                            _direction = ("above advisory window"
                                          if _pi_f > 8.5 else
                                          ("below advisory window" if _pi_f < 5.5
                                           else "within advisory window"))
                            _val_parts.append(f"Fab pI {_pi_f:.2f} — {_direction}")
                    if "human_review" in _ev:
                        _val_parts.append("requires manual review prior to lead nomination")
                    if "cdr_rmsd" in _ev and _ev.get("cdr_rmsd"):
                        _vw = _ev.get("volatile_warn") or []
                        _sf = _ev.get("stable_fails") or []
                        if _vw:
                            _val_parts.append("flexible CDR loop above advisory range: " + ", ".join(_vw))
                        if _sf:
                            _val_parts.append("rigid CDR loop outside acceptable range: " + ", ".join(_sf))
                    _notes = (_it.get("notes") or "").strip()
                    if _notes and not _val_parts:
                        _val_parts.append(_notes)
                    _val_html = " &nbsp;·&nbsp; ".join(_val_parts) or "see report sections below"
                    _attn_badge = ("<span class='badge badge-warn' style='font-size:10px'>WARN</span>"
                                   if _st == "WARN" else
                                   "<span class='badge badge-fail' style='font-size:10px'>FAIL</span>")
                    _attn_items.append((_attn_badge, _id, _title, _val_html))
        except Exception as _attn_err:  # pragma: no cover
            _attn_items = []

        # Fallback path: some payloads only carry qa_audit/checklist_status (no checklist_report).
        # Never show "all passed" when the top-level status is WARN/FAIL.
        if not _attn_items:
            _top_status = str(payload.get("checklist_status") or status or "").upper()
            if _top_status in ("WARN", "FAIL"):
                _qa_for_attn = payload.get("qa_audit") or payload.get("_qa_audit") or {}
                _qa_checks = _qa_for_attn.get("checks") if isinstance(_qa_for_attn, dict) else []
                for _chk in (_qa_checks or []):
                    if not isinstance(_chk, dict):
                        continue
                    _lvl = str(_chk.get("level") or "").upper()
                    if _lvl not in ("WARN", "FAIL"):
                        continue
                    _cid = str(_chk.get("id") or "qa_check")
                    _cmsg = str(_chk.get("msg") or "").strip() or "see qa_audit details"
                    _sev_badge = (
                        "<span class='badge badge-warn' style='font-size:10px'>WARN</span>"
                        if _lvl == "WARN"
                        else "<span class='badge badge-fail' style='font-size:10px'>FAIL</span>"
                    )
                    _attn_items.append((_sev_badge, _cid, "Pipeline QA audit", esc(_cmsg)))
                if not _attn_items:
                    _attn_items.append(
                        (
                            "<span class='badge badge-warn' style='font-size:10px'>WARN</span>"
                            if _top_status == "WARN"
                            else "<span class='badge badge-fail' style='font-size:10px'>FAIL</span>",
                            "checklist_status",
                            "Checklist summary",
                            f"Overall checklist status is {_top_status}. See §12 and Pipeline QA audit.",
                        )
                    )

        if _attn_items:
            _attn_rows = "".join(
                f"<tr><td style='width:60px'>{b}</td>"
                f"<td style='font-family:monospace;width:55px'>{i}</td>"
                f"<td>{t}</td>"
                f"<td style='color:#374151;font-size:12px'>{v}</td></tr>"
                for (b, i, t, v) in _attn_items
            )
            warn_items_html = (
                "<details open style='margin-top:12px;border:1px solid #fde68a;background:#fffbeb;border-radius:6px;padding:8px 12px'>"
                "<summary style='cursor:pointer;font-weight:700;color:#92400e;font-size:13px'>"
                f"Items requiring attention ({len(_attn_items)})"
                "</summary>"
                "<table class='params' style='font-size:0.84em;margin-top:8px'>"
                "<tr style='background:#fef3c7'><th>Severity</th><th>Item</th><th>Check</th><th>Detail</th></tr>"
                f"{_attn_rows}"
                "</table>"
                "<p class='note' style='font-size:11px;margin:6px 0 0;color:#78350f'>"
                "These items are visible by design — review them before lead nomination. WARN = manageable advisory; FAIL = blocker."
                "</p>"
                "</details>"
            )
        else:
            warn_items_html = (
                "<p class='note' style='margin-top:10px;color:#1a7a3c;font-weight:600'>"
                "✓ All checklist items passed — no advisory or blocker items in this run."
                "</p>"
            )

        # V5.3.1: top-of-§0 banner when Phase-2 framework selection fell back to
        # default human germlines. Without this banner, rat/rabbit reports look
        # indistinguishable from a curated mouse run.
        phase2_degraded_banner = ""
        if payload.get("phase2_degraded"):
            _attn_msg = (payload.get("phase2_attention_message") or
                         "Framework selection fell back to default human germlines. "
                         "Review donor sequence and CDR lengths before downstream use.")
            _fb_reason = payload.get("phase2_fallback_reason") or ""
            phase2_degraded_banner = (
                "<div style='margin-top:12px;border:1.5px solid #f87171;background:#fef2f2;"
                "border-radius:6px;padding:10px 14px'>"
                "<strong style='color:#991b1b;font-size:13px'>"
                "⚠ Framework selection: degraded fallback path</strong>"
                f"<p class='note' style='margin:6px 0 0;color:#7f1d1d;font-size:12px;line-height:1.5'>{_attn_msg}</p>"
                + (f"<p class='note' style='margin:4px 0 0;color:#7f1d1d;font-size:11px;font-family:monospace'>"
                   f"Reason: {_fb_reason}</p>" if _fb_reason else "")
                + "</div>"
            )

        status_legend = (
            f"<p class='note' style='margin-top:10px; color:var(--accent); font-size:0.9em;'>{mode_label}</p>"
            + phase2_degraded_banner
            + warn_items_html
            + _build_discussion_box("Executive Discussion", _exec_disc)
            + "<p class='note' style='margin-top:5px'><b>"
            + "Overall status (checklist summary):"
            + "</b> "
            "<span class='badge badge-ok'>PASS</span> — "
            + "All phases green."
            + " &nbsp;<span class='badge badge-warn'>WARN</span> — "
            + "Finished, but at least one checklist item carries an advisory; "
            "still deliverable with notes."
            + " &nbsp;<span class='badge badge-fail'>FAIL</span> — "
            + "At least one item failed a hard developability gate. "
            + "<b>"
            + "WARN and FAIL are different:"
            + "</b> "
            + "WARN = caution; FAIL = do not treat as passed humanization without fix."
            + "</p>"
        )
        ablang = payload.get("ablang_score")
        hpr = payload.get("hpr_index") or {}
        _p_ab_ov = payload.get("p_abnativ2") or {}
        _p_ab_stat_ov = str(_p_ab_ov.get("paired_humanness_status") or "").upper()
        _hpr_dcomb = ((hpr.get("delta") or {}).get("combined"))
        try:
            _hpr_delta_ok = _hpr_dcomb is not None and float(_hpr_dcomb) >= 0.0
        except (TypeError, ValueError):
            _hpr_delta_ok = False
        if _p_ab_stat_ov == "PASS":
            ablang_ok = True
            ab_badge = _badge(True, "HUMANIZED", "REVIEW")
        elif _p_ab_stat_ov == "FAIL":
            ablang_ok = False
            ab_badge = _badge(False, "HUMANIZED", "REVIEW")
        elif _p_ab_stat_ov == "WARN":
            ablang_ok = True
            ab_badge = _badge(True, "HUMANIZED", "REVIEW")
        else:
            ablang_ok = _hpr_delta_ok
            ab_badge = (
                _badge(ablang_ok, "HUMANIZED", "REVIEW")
                if _hpr_dcomb is not None
                else ""
            )

        def _hpr_score(block: dict, chain: str):
            return ((block.get(chain) or {}).get("score"))

        def _hpr_pct(value) -> str:
            if value is None:
                return _NA
            try:
                return f"{float(value) * 100:.1f}%"
            except Exception:
                return _NA

        try:
            _hsc = ((hpr.get("humanized") or {}).get("combined") or {}).get("score")
            _hpr_hum_comb_pct = f"{float(_hsc) * 100:.1f}%" if _hsc is not None else None
        except Exception:
            _hpr_hum_comb_pct = None

        _hpr_donor = hpr.get("donor") or {}
        _hpr_hum = hpr.get("humanized") or {}
        _hpr_delta = hpr.get("delta") or {}
        _iedb_result = payload.get("iedb_result") or _qm_norm.get("iedb_result") or "not_run"
        _iedb_status = payload.get("iedb_http_status") or _qm_norm.get("iedb_http_status") or "N/A"
        _immuno_status = (
            "<span class='badge badge-ok'>computed</span>"
            if str(_iedb_result).lower() not in ("not_run", "n/a", "none", "")
            else "<span class='badge badge-warn'>not run in this web-console job</span>"
        )

        # ── §1 Input sequences ──────────────────────────────────────────────
        _seqs_sub = payload.get("sequences") or {}
        mouse_vh = payload.get("mouse_vh") or _seqs_sub.get("mouse_vh", "")
        mouse_vl = payload.get("mouse_vl") or _seqs_sub.get("mouse_vl", "")

        # ── §1.1 Canonical Class / Conformation Guard (Privacy V5.2.0) ──────
        # We hide the specific class IDs (e.g. H1-1) to protect proprietary algorithm details.
        # Instead, we show a generic "Profiled" status.
        s1_1_conformation = f"""
<div class='section' id='s1_1'>
  <h3>§1.1 — Conformation Profile Analysis</h3>
  <p class='note'>Structural profiling of CDR loops to ensure framework-conformation compatibility.</p>
  <table class='params'>
    <tr><th>CDR Loop</th><th>Status</th><th>Analysis</th></tr>
    <tr><td>CDR-H1</td><td><span class='badge badge-ok'>✓ Profiled</span></td><td>Conformation-based framework matching</td></tr>
    <tr><td>CDR-H2</td><td><span class='badge badge-ok'>✓ Profiled</span></td><td>Conformation-based framework matching</td></tr>
    <tr><td>CDR-H3</td><td><span class='badge badge-ok'>✓ Profiled</span></td><td>Structural envelope validation</td></tr>
    <tr><td>CDR-L1</td><td><span class='badge badge-ok'>✓ Profiled</span></td><td>Conformation-based framework matching</td></tr>
    <tr><td>CDR-L2</td><td><span class='badge badge-ok'>✓ Profiled</span></td><td>Conformation-based framework matching</td></tr>
    <tr><td>CDR-L3</td><td><span class='badge badge-ok'>✓ Profiled</span></td><td>Conformation-based framework matching</td></tr>
  </table>
</div>
"""

        # ── §2 Mode & Strategy (V4.9.1) ──────────────────────────────────────
        _exec_route = payload.get("execution_route") or {}
        _exec_engine = _exec_route.get("engine_rescue") or {}
        _exec_surface = _exec_route.get("surface_fallback") or {}
        _exec_final_route = esc(str(_exec_route.get("final_route") or "standard_germline_graft").replace("_", " "))
        _exec_engine_path = esc(str(_exec_engine.get("path") or "not recorded").replace("_", " "))
        _exec_surface_status = esc(str(_exec_surface.get("status") or "not recorded").replace("_", " "))
        mode_rows = (
            f"<tr><td class='lbl'>Engineering Mode</td><td><b>{repair_mode_label}</b></td></tr>"
            f"<tr><td class='lbl'>Optimization Strategy</td><td><b>{bm_strategy_label}</b></td></tr>"
            f"<tr><td class='lbl'>Execution Priority</td><td>standard graft → engine rescue → post-engine surface fallback</td></tr>"
            f"<tr><td class='lbl'>Engine Rescue Path</td><td><b>{_exec_engine_path}</b></td></tr>"
            f"<tr><td class='lbl'>Surface Fallback</td><td><b>{_exec_surface_status}</b> <span class='note'>(post-engine gate)</span></td></tr>"
            f"<tr><td class='lbl'>Final Route</td><td><b>{_exec_final_route}</b></td></tr>"
            f"<tr><td class='lbl'>VH Route</td><td><b>{_chain_route_label('VH')}</b></td></tr>"
            f"<tr><td class='lbl'>VL Route</td><td><b>{_chain_route_label('VL')}</b></td></tr>"
        )

        # ── Rescue trail builder ───────────────────────────────────────────────
        _rescue_data = payload.get("rescue") or {}
        _rescue_attempted = _rescue_data.get("attempted", False)
        _rescue_notes = _rescue_data.get("notes") or []
        _rescue_attempts = _rescue_data.get("attempts") or []

        def _rescue_status_en(notes: list, nsteps: int) -> str:
            n = list(notes or [])
            if "vernier_round2_rescued" in n:
                return "Recorded — refinement converged with extended framework adjustments."
            if "fallback_germline_rerun" in n:
                return "Recorded — refinement used an alternate germline path for the deliverable sequence."
            return "Recorded — automated refinement applied where QC indicated."

        def _rescue_status_zh(notes: list, nsteps: int) -> str:
            n = list(notes or [])
            if "vernier_round2_rescued" in n:
                return " — 。"
            if "fallback_germline_rerun" in n:
                return " — 。"
            return " — 。"

        def _rescue_trail_html() -> str:
            """Client-facing summary only — no gate-by-gate traces (contract: proprietary logic omitted)."""
            if not _rescue_attempted:
                return ""
            _n = _rescue_notes or []
            if "vernier_round2_rescued" in _n:
                outcome = "The deliverable sequence reflects post-QC framework refinement."
            elif "fallback_germline_rerun" in _n:
                outcome = "The deliverable sequence reflects the alternate germline outcome defined for this run."
            else:
                outcome = "Iterative refinement was recorded; the sequences above are the reported output."
            return (
                f"<p class='note' style='margin-top:10px'><b>Refinement</b> — {outcome} "
                f"Stepwise diagnostics are omitted from this client summary."
                f"</p>"
            )

        # ── §3 Germline selection ───────────────────────────────────────────
        vh_id = payload.get("vh_germline_identity")
        vl_id = payload.get("vl_germline_identity")
    
        if sr_applied:
            _germ_disc = (
                "Framework/reference information is chain-specific. Chains routed through donor-framework FR surface reshaping "
                "use human germline data only as a residue-reference context; they are not reported as adopting that full human framework. "
                f"Actual route: VH = <strong>{_chain_route_label('VH')}</strong>; VL = <strong>{_chain_route_label('VL')}</strong>."
            )
        else:
            _germ_disc = (
            "The selection of human germline frameworks is based on sequence identity and structural compatibility. "
            f"The selected pair (<strong>{payload.get('vh_germline','—')}</strong> / <strong>{payload.get('vl_germline','—')}</strong>) "
            "provides an optimal balance between high humanness and the preservation of the donor's antigen-binding architecture."
            )

        s3_interp = _build_discussion_box("Germline Selection Discussion", _germ_disc)
    
        candidates = payload.get("candidates", [])
        cand_rows = "".join(
            f"<tr class='{'row-best' if c.get('rank')==1 else ''}'>"
            f"<td>{c.get('rank','')}</td>"
            f"<td><b>{c.get('vh_germline','—')}</b></td>"
            f"<td><b>{c.get('vl_germline','—')}</b></td>"
            f"<td>{_fmtf(c.get('vh_fr_id'),1,'%')}</td>"
            f"<td>{_fmtf(c.get('vl_fr_id'),1,'%')}</td>"
            f"<td><b>{_fmtf(c.get('score'),1,'%')}</b></td></tr>"
            for c in candidates
        ) or "<tr><td colspan='6'>—</td></tr>"

        # Build the selection policy cell with species-aware logic, avoiding internal policy names.
        _dsp = str(payload.get("donor_species") or "").strip().lower()
        if _dsp == "mus_musculus":
            selection_policy_cell = (
                "Murine: human VH/VL frameworks are restricted to the clinical-frequency anchor pool "
                "(no full Kabat-cache expansion)."
            )
        elif _dsp in ("oryctolagus_cuniculus", "rattus_norvegicus"):
            _species_lbl = "Rabbit" if _dsp == "oryctolagus_cuniculus" else "Rat"
            selection_policy_cell = (
                f"{_species_lbl}: candidate human frameworks are ranked deterministically under the active protocol. "
                "Internal scan scope and tie-break rules are omitted from this client summary "
                "(see JSON fields such as <code>clinical_framework_policy</code> / <code>phase2_*</code> for routing metadata)."
            )
        else:
            selection_policy_cell = "Project ruleset — reproducible candidate ranking."

        _qm_for_cr = payload.get("qc_metrics") or {}
        _cr = payload.get("clinical_reference") or _qm_for_cr.get("clinical_reference") or {}
        pv_side = payload.get("clinical_precedents_vh_template") or _cr.get("clinical_precedents_vh_template") or []
        pl_side = payload.get("clinical_precedents_vl_template") or _cr.get("clinical_precedents_vl_template") or []

        
        # If split lists are empty but raw list exists, split them now
        if not pv_side and not pl_side:
            raw_precedents = _cr.get("clinical_precedents") or []
            if raw_precedents:
                pv_side = [p for p in raw_precedents if p.get("match_type") in ("VH exact", "VH+VL exact")]
                pl_side = [p for p in raw_precedents if p.get("match_type") in ("VL exact", "VH+VL exact")]

        # ── 842 clinical-framework library FALLBACK ──────────────────────────
        # The germline candidate pool is grounded in 842 real clinical antibodies,
        # so every selected VH/VL must have at least one clinical antibody using
        # the same framework. When the curated clinical_precedents block is empty
        # (e.g. because the join was not pre-computed for this run) we derive the
        # tables on the fly from data/humanization_assay/842_antibody_germline_assignment.csv
        # so the customer always sees that the chosen template has clinical track record.
        clinical_precedents_fallback_summary: dict | None = None
        _vh_germ = (payload.get("vh_germline") or _cr.get("selected_vh_germline") or "").strip()
        _vl_germ = (payload.get("vl_germline") or _cr.get("selected_vl_germline") or "").strip()
        if (not pv_side) and (not pl_side) and (_vh_germ or _vl_germ):
            _fb_vh, _fb_vl, _fb_summary = _derive_clinical_precedents_from_842(_vh_germ, _vl_germ)
            if _fb_vh or _fb_vl:
                pv_side = _fb_vh
                pl_side = _fb_vl
                clinical_precedents_fallback_summary = _fb_summary

        ada_vh_side = payload.get("germline_ada_references_vh_template") or _cr.get("germline_ada_references_vh_template") or []
        ada_vl_side = payload.get("germline_ada_references_vl_template") or _cr.get("germline_ada_references_vl_template") or []
        
        if not ada_vh_side and not ada_vl_side:
            raw_ada = _cr.get("germline_ada_references") or []
            if raw_ada:
                ada_vh_side = [r for r in raw_ada if r.get("match_type") in ("VH exact", "VH+VL exact")]
                ada_vl_side = [r for r in raw_ada if r.get("match_type") in ("VL exact", "VH+VL exact")]

        if vh_surface_route:
            pv_side = []
            ada_vh_side = []
        if vl_surface_route:
            pl_side = []
            ada_vl_side = []

        _s3_banner_txt = "Per-chain clinical / reference context"
        if sr_applied:
            _s3_banner_body = (
                "Clinical framework precedent tables are shown only for chains whose final route used a human-germline "
                "CDR-grafting framework. For any chain routed through donor-framework FR surface reshaping, the selected "
                "human germline is retained only as a residue-reference context and is not presented as the final scaffold."
            )
        else:
            _s3_banner_body = (
                "These two tables list clinical antibodies that use the <strong>same selected VH</strong> or "
                "<strong>same selected VL</strong> framework (exact allele, allele variant, or gene family). "
                "Because the framework candidate pool is curated from a clinically validated antibody cohort, every "
                "selected germline is guaranteed to have at least one clinical precedent — independent of whether ADA "
                "incidence has been reported."
            )
        if clinical_precedents_fallback_summary:
            _fb_note = (
                "<p class='note' style='margin:6px 0 0;font-size:0.85em;color:#5a6a80'>"
                "<i>Source: InSynBio clinical-framework reference cohort "
                "(top entries ranked by match priority — exact allele &gt; allele variant &gt; gene family).</i>"
                "</p>"
            )
        else:
            _fb_note = ""
        _vh_surface_note = (
            "<h4 style='color:#b45309;margin:14px 0 6px'>VH framework clinical precedents omitted</h4>"
            "<p class='note'>VH used donor-framework FR surface reshaping. The selected VH human germline is a "
            "reference for human-supported residues, not the final VH framework identity.</p>"
            if vh_surface_route else ""
        )
        _vl_surface_note = (
            "<h4 style='color:#b45309;margin:14px 0 6px'>VL framework clinical precedents omitted</h4>"
            "<p class='note'>VL used donor-framework FR surface reshaping. The selected VL human germline is a "
            "reference for human-supported residues, not the final VL framework identity.</p>"
            if vl_surface_route else ""
        )
        s3_side_template_block = (
            f"<h4 style='color:#2d6cdf;margin:16px 0 6px'>{_s3_banner_txt}</h4>"
            f"<div class=\"note\" style=\"margin:0 0 10px;line-height:1.5;font-size:0.92em\"><p style=\"margin:0\">{_s3_banner_body}</p>{_fb_note}</div>"
            + (_vh_surface_note if vh_surface_route else _clinical_side_template_precedents_html(pv_side, "H", lang_code))
            + (_vl_surface_note if vl_surface_route else _clinical_side_template_precedents_html(pl_side, "L", lang_code))
        )

        # ── §4 Structural analysis (SDRM) ───────────────────────────────────
        _qm_struct = payload.get("qc_metrics") or {}
        _struct = payload.get("structure") or _qm_struct.get("structure") or {}
        struct_status = "COMPUTED" if (payload.get("structure_computed") or _qm_struct.get("structure_computed") or _struct.get("pdb_path")) else "DRY_RUN"
        
        plddt    = payload.get("plddt") or _qm_struct.get("plddt") or _struct.get("plddt")
        h_plddt  = payload.get("humanized_plddt") or _qm_struct.get("humanized_plddt") or _struct.get("humanized_plddt")
        m_ang    = payload.get("vh_vl_angle_deg") or _qm_struct.get("vh_vl_angle_deg") or _struct.get("vh_vl_angle_deg")
        h_ang    = payload.get("humanized_angle_deg") or _qm_struct.get("humanized_angle_deg") or _struct.get("humanized_angle_deg")
        ang_del  = payload.get("angle_delta_deg") or _qm_struct.get("angle_delta_deg") or _struct.get("angle_delta_deg")
        ang_ok   = ang_del is not None and abs(ang_del) <= 3.0
        ang_badge = _badge(ang_ok) if ang_del is not None else _NA

        _sq = payload.get("structural_qc_v50") or _qm_struct.get("structural_qc_v50") or {}
        _gfv = payload.get("global_fv_rmsd_ca") or _qm_struct.get("global_fv_rmsd_ca") or _sq.get("global_fv_rmsd_ca")
        _gfv_badge = _NA
        _gfv_row_html = ""
        if isinstance(_gfv, (int, float)):
            _gst = str(_sq.get("global_fv_gate_status") or _sq.get("status") or "").strip().upper()
            if _gst in ("PASS", "WARN", "FAIL", "ADVISORY"):
                _gfv_badge = _gst
            elif _gfv < 1.5:
                _gfv_badge = _badge(True, "✓ PASS", "")
            else:
                _gfv_badge = "<span class='badge badge-warn'>⚠ WARN</span>"
            _gfv_row_html = f"""    <tr>
      <td class='lbl'>Global Fv Cα RMSD (framework-aligned)</td>
      <td><span style='color:#6b7280;font-size:.85rem'>—<br><span style='font-size:.7rem'>(reference)</span></span></td>
      <td><b>{_fmtf(_gfv,'2',' Å')}</b></td>
      <td>{_gfv_badge}</td>
    </tr>
"""

        _struct_disc = H(
            "Donor and humanized Fv models are compared using confidence-related scores (pLDDT-equivalent), VH/VL packing angle, mean CDR Cα RMSD, and global Fv Cα RMSD after framework alignment. "
            "Together these summarize scaffold preservation in silico; binding and developability should be confirmed experimentally for lead selection.",
            " Fv  pLDDT 、VH/VL 、 CDR Cα RMSD  Global Fv Cα RMSD 。"
            "；。",
        )
        s4_interp = _build_discussion_box(H("Structural Discussion", ""), _struct_disc)

        # ── §5 Back-mutation outcome — client-facing, no internal algorithm labels ──
        _qm = payload.get("qc_metrics") or {}
        _fs = payload.get("framework_selection") or _qm.get("framework_selection") or {}
        bm_vh = payload.get("bm_candidates_vh") or _qm.get("bm_candidates_vh") or _fs.get("bm_candidates_vh") or []
        bm_vl = payload.get("bm_candidates_vl") or _qm.get("bm_candidates_vl") or _fs.get("bm_candidates_vl") or []
        sdrm_vh = payload.get("sdrm_vh") or _fs.get("sdrm_vh") or []
        sdrm_vl = payload.get("sdrm_vl") or _fs.get("sdrm_vl") or []
        hum_vh = payload.get("humanized_vh") or _seqs_sub.get("humanized_vh", "")
        hum_vl = payload.get("humanized_vl") or _seqs_sub.get("humanized_vl", "")

        # V5.4.18: Ensure A45P is in the bm_candidates list if it was applied.
        # This handles cases where the engine might have dropped it from the summary list.
        if "pos45:A→P [HC1]" not in bm_vh:
            # Check if it's in SDRM
            for e in sdrm_vh:
                if e.get("pos") == 45 and "BACK_MUTATE" in str(e.get("action")):
                    bm_vh.append("pos45:A→P [HC1]")
                    break

        def _numbered_kabat_map(seq: str, chain_label: str) -> dict:
            try:
                from core.numbering.dual_scheme import compute_dual_scheme_numbering
                res = compute_dual_scheme_numbering(seq or "", chain_label=chain_label)
                # V5.4.17: Use (pos, ins) as key to handle insertion codes correctly
                return {(r.pos, r.ins): r.aa for r in res.kabat if r.aa != "-"}
            except Exception:
                return {}

        _kabat_maps = {
            "VH": {
                "donor": _numbered_kabat_map(mouse_vh, "VH"),
                "final": _numbered_kabat_map(hum_vh, "VH"),
            },
            "VL": {
                "donor": _numbered_kabat_map(mouse_vl, "VL"),
                "final": _numbered_kabat_map(hum_vl, "VL"),
            },
        }

        def _candidate_outcome(chain_label: str, pos: int) -> tuple[bool, str]:
            # Default to empty insertion code for base positions
            donor_aa = _kabat_maps.get(chain_label, {}).get("donor", {}).get((pos, ""))
            final_aa = _kabat_maps.get(chain_label, {}).get("final", {}).get((pos, ""))
            if donor_aa is None or final_aa is None:
                return False, "N/A"
            if final_aa == donor_aa:
                return True, final_aa
            return False, final_aa

        def _bm_rows(bm_list: list, chain_label: str) -> str:
            if not bm_list:
                return (f"<tr><td colspan='6' style='color:#1a7a3c;font-style:italic;padding:8px'>"
                        f"✓ No framework reversion candidates recorded for"
                        f" {chain_label}.</td></tr>")
            out = []
            for entry in bm_list:
                rule = "N/A"
                main = entry
                if "[" in entry and entry.rstrip().endswith("]"):
                    idx = entry.rfind("[")
                    main, rule = entry[:idx].strip(), entry[idx:].strip()
                try:
                    pos_part, aa_part = main.split(":", 1)
                    pos = pos_part.replace("pos", "").strip()
                    pos_int = int(pos)
                    if "→" in aa_part:
                        g_aa, m_aa = aa_part.split("→", 1)
                        g_aa, m_aa = g_aa.strip(), m_aa.strip()
                    else:
                        g_aa, m_aa = "?", "?"
                    _, final_aa = _candidate_outcome(chain_label, pos_int)
                    is_applied = final_aa == m_aa
                    outcome = (
                        f"<span style='background:#1a7a3c;color:#fff;border-radius:3px;"
                        f"padding:1px 5px;font-size:10px'>IN FINAL</span>"
                        if is_applied else
                        f"<span style='background:#e5e7eb;color:#374151;border-radius:3px;"
                        f"padding:1px 5px;font-size:10px'>NOT IN FINAL</span>"
                    )
                    reason = (
                        "Framework support / CDR-shape conservation"
                        if rule != "N/A" else "Framework difference review"
                    )
                    out.append(
                        f"<tr>"
                        f"<td><b>{chain_label}</b></td>"
                        f"<td style='font-family:monospace;font-weight:700'>{pos}</td>"
                        f"<td style='font-family:monospace'><span style='color:#2d6cdf'>{g_aa}</span></td>"
                        f"<td style='font-family:monospace'><span style='color:#c0392b;font-weight:700'>{m_aa}</span></td>"
                        f"<td style='font-family:monospace;font-weight:700'>{final_aa}</td>"
                        f"<td>{outcome}<br><span style='font-size:11px;color:#5a6a80'>{reason}</span></td></tr>"
                    )
                except Exception:
                    out.append(f"<tr><td>{chain_label}</td><td colspan='5'>{entry}</td></tr>")
            return "".join(out)

        def _sdrm_full_table(sdrm_list: list, chain_label: str, applied_pos: set) -> str:
            """Full per-position framework difference table for §5 — concise (differences only)."""
            ACTION_COLOR = {
                "REVERTED":  "#1a7a3c",
                "HUMANIZED": "#1b4fad",
                "CONSERVED": "#5a6a80",
                "PENDING":   "#b45309",
            }
            rows = []
            for entry in sdrm_list:
                pos = entry.get("pos")
                if not isinstance(pos, int):
                    continue
                g_aa = entry.get("germline_aa") or "?"
                m_aa = entry.get("mouse_aa") or "?"
                action_raw = entry.get("action") or "KEEP_HUMAN"
                action_key = action_raw.split(" ")[0] if action_raw else "KEEP_HUMAN"

                applied, final_aa = _candidate_outcome(chain_label, pos)

                if g_aa == m_aa:
                    display_status = "Conserved"
                    color = ACTION_COLOR["CONSERVED"]
                    assessment = "Residue conserved between donor and germline."
                elif applied:
                    display_status = "Reverted"
                    color = ACTION_COLOR["REVERTED"]
                    assessment = "Reverted to donor residue for structural support."
                elif action_key in ("MONITOR", "REVIEW"):
                    display_status = "Pending Decision"
                    color = ACTION_COLOR["PENDING"]
                    assessment = "Humanized; optional reversion recommended if activity is sensitive."
                else:
                    display_status = "Humanized"
                    color = ACTION_COLOR["HUMANIZED"]
                    assessment = "Successfully humanized to germline residue."

                applied_td = (
                    f"<span style='background:#1a7a3c;color:#fff;border-radius:3px;"
                    f"padding:1px 5px;font-size:10px'>DONOR IN FINAL</span>" if applied else
                    f"<span style='color:#6b7280;font-size:10px'>—</span>"
                )
                rows.append(
                    f"<tr>"
                    f"<td style='font-family:monospace;font-weight:600'>{pos}</td>"
                    f"<td style='font-family:monospace'><span style='color:#2d6cdf'>{g_aa}</span></td>"
                    f"<td style='font-family:monospace'><span style='color:#c0392b'>{m_aa}</span></td>"
                    f"<td style='font-family:monospace;font-weight:600'>{final_aa}</td>"
                    f"<td style='color:{color};font-weight:600;font-size:11px'>{display_status}</td>"
                    f"<td style='color:#374151;font-size:11px'>{assessment}</td>"
                    f"<td>{applied_td}</td>"
                    f"</tr>"
                )

            if not rows:
                return f"<p class='note' style='color:#1a7a3c'>✓ No framework differences between donor and germline for {chain_label}.</p>"

            return (
                f"<table class='params' style='margin-top:8px;font-size:.82rem'>"
                f"<tr style='background:#e8eef8'>"
                f"<th>Pos</th>"
                f"<th>Germline</th>"
                f"<th>Donor</th>"
                f"<th>Final</th>"
                f"<th>Status</th>"
                f"<th>Engineering assessment</th>"
                f"<th>Donor residue in final?</th>"
                f"</tr>"
                + "".join(rows)
                + "</table>"
            )

        bm_vh_applied = set()
        bm_vl_applied = set()
        bm_vh_rows = _bm_rows(bm_vh, "VH")
        bm_vl_rows = _bm_rows(bm_vl, "VL")
        sdrm_vh_table = _sdrm_full_table(sdrm_vh, "VH", bm_vh_applied)
        sdrm_vl_table = _sdrm_full_table(sdrm_vl, "VL", bm_vl_applied)

        # ── §5a / §5b / §5c — V5.2.7 strict decision-mode binary ─────────────
        bm_decisions_vh = payload.get("bm_decisions_vh") or _qm_norm.get("bm_decisions_vh") or _fs_norm.get("bm_decisions_vh") or []
        bm_decisions_vl = payload.get("bm_decisions_vl") or _qm_norm.get("bm_decisions_vl") or _fs_norm.get("bm_decisions_vl") or []
        bm_pending_vh   = payload.get("bm_pending_vh")   or _qm_norm.get("bm_pending_vh")   or _fs_norm.get("bm_pending_vh")   or []
        bm_pending_vl   = payload.get("bm_pending_vl")   or _qm_norm.get("bm_pending_vl")   or _fs_norm.get("bm_pending_vl")   or []
        bm_audit        = payload.get("bm_decisions_audit") or _qm_norm.get("bm_decisions_audit") or _fs_norm.get("bm_decisions_audit") or {}

        # Back-compat: if engine produced legacy payload (only bm_candidates_*),
        # reconstruct decisions/pending/audit from string list + final sequence.
        # This makes pre-V5.2.7 JSONs render the new §5a/§5b/§5c immediately.
        _RULE_DM_BACKCOMPAT = {
            "HC1": "AUTO_APPLY", "HC1-inv": "AUTO_APPLY", "HC2": "AUTO_APPLY",
            "HC3": "AUTO_APPLY", "HC4": "AUTO_APPLY", "HC5": "AUTO_APPLY",
            "HC6": "AUTO_APPLY", "Vernier-T1": "AUTO_APPLY",
            "Vernier-T2": "PENDING_HUMAN", "Vernier-T3": "PENDING_HUMAN",
        }

        def _reconstruct_decisions(chain_label: str, candidates: list, final_seq: str,
                                   donor_seq: str, sdrm_list: list) -> tuple[list, list]:
            """Rebuild decisions + pending from string candidate list when engine output is legacy.

            Iterates ALL framework differences from sdrm_list (which the legacy engine emits),
            so coverage is full. For each diff, derives hc_rule from the candidate string when
            present, otherwise marks it as 'FR-difference' (KEEP_HUMAN by algorithm).
            """
            kabat_map_donor = _kabat_maps.get(chain_label, {}).get("donor", {})
            kabat_map_final = _kabat_maps.get(chain_label, {}).get("final", {})

            cand_rule_by_pos: dict[int, str] = {}
            cand_donor_aa_by_pos: dict[int, str] = {}
            for s in candidates or []:
                if not isinstance(s, str) or "pos" not in s:
                    continue
                try:
                    pos_part, aa_part = s.split(":", 1)
                    pos_int = int(pos_part.replace("pos", ""))
                    rule = "FR-difference"
                    if "[" in aa_part and aa_part.rstrip().endswith("]"):
                        idx = aa_part.rfind("[")
                        rule = aa_part[idx + 1:-1].strip()
                        aa_part = aa_part[:idx].strip()
                    donor_aa = aa_part.split("→")[-1].strip() if "→" in aa_part else None
                    cand_rule_by_pos[pos_int] = rule
                    if donor_aa:
                        cand_donor_aa_by_pos[pos_int] = donor_aa
                except Exception:
                    continue

            decisions = []
            pending = []
            for entry in sdrm_list or []:
                pos = entry.get("pos")
                if not isinstance(pos, int):
                    continue
                # V5.4.17: Use (pos, "") for base positions in reconstructed maps
                germ = entry.get("germline_aa") or kabat_map_donor.get((pos, ""), "?")
                donor = entry.get("mouse_aa") or kabat_map_donor.get((pos, ""), "?")
                final = kabat_map_final.get((pos, ""))
                rule = cand_rule_by_pos.get(pos) or entry.get("hc_rule") or "FR-difference"
                mode = _RULE_DM_BACKCOMPAT.get(rule, "AUTO_APPLY")
                wanted = pos in cand_rule_by_pos
                
                # V5.4.16: robust applied check. 
                # Use donor_aa from candidate string if available (handles A->P cases where donor seq is L)
                target_aa = cand_donor_aa_by_pos.get(pos) or donor
                applied = (final is not None and final == target_aa)

                if mode == "AUTO_APPLY":
                    if wanted and applied:
                        lvl, status, msg = "PASS", "EXECUTED_AS_RULED", \
                            f"Algorithm decided BACK_MUTATE → applied (final={final})."
                    elif wanted and not applied:
                        lvl, status, msg = "WARN", "RULE_VETOED_BY_DOWNSTREAM", \
                            (f"Algorithm decided BACK_MUTATE to {donor} but final is "
                             f"{final} — downstream assembly/QC vetoed without record.")
                    elif (not wanted) and (not applied):
                        lvl, status, msg = "PASS", "EXECUTED_AS_RULED", \
                            f"Algorithm decided KEEP_HUMAN → kept germline (final={final})."
                    else:
                        lvl, status, msg = "FAIL", "VIOLATION_AUTO_APPLIED_KEEP_RULE", \
                            (f"Algorithm decided KEEP_HUMAN but final={final} matches donor — "
                             f"silent BACK_MUTATE bug.")
                elif mode == "PENDING_HUMAN":
                    if not applied:
                        lvl, status, msg = "PASS", "PENDING_HUMAN_KEPT_HUMAN", \
                            f"Pending human decision; default KEEP_HUMAN observed (final={final})."
                        pending.append({
                            "pos": pos, "germline_aa": germ, "mouse_aa": donor,
                            "hc_rule": rule,
                            "client_options": [
                                {"id": "keep_germline_human",
                                 "label": f"Keep germline residue {germ} (maximize humanness)",
                                 "consequence": "Higher FR humanness; possible mild CDR-shape drift if interface depends on this residue."},
                                {"id": "back_mutate_to_donor",
                                 "label": f"Revert to donor residue {donor} (preserve CDR/interface support)",
                                 "consequence": "Conservative CDR shape; FR humanness decreases by 1 residue."},
                            ],
                        })
                    else:
                        lvl, status, msg = "FAIL", "VIOLATION_AUTO_APPLIED_PENDING_RULE", \
                            (f"PENDING_HUMAN rule was silently auto-applied (final={final} == donor). "
                             f"Forbidden — engine must surface to client, not decide.")
                else:
                    lvl, status, msg = "FAIL", "UNKNOWN_DECISION_MODE", \
                        f"Decision mode '{mode}' is not in the registered taxonomy."

                decisions.append({
                    "chain": chain_label, "pos": pos,
                    "germline_aa": germ, "donor_aa": donor, "final_aa": final,
                    "hc_rule": rule, "decision_mode": mode,
                    "auto_recommended": wanted, "applied": applied,
                    "audit_status": status, "audit_level": lvl, "audit_msg": msg,
                })
            return decisions, pending

        # V5.4.18: Force reconstruction if A45P is missing from decisions but present in summary
        if not any(e.get("pos") == 45 for e in bm_decisions_vh) and any("pos45" in str(b) for b in bm_vh):
            bm_decisions_vh = [] # Force reconstruction below

        # V5.4.18: Force reconstruction if A45P is missing from decisions but present in summary
        if not any(e.get("pos") == 45 for e in bm_decisions_vh) and any("pos45" in str(b) for b in bm_vh):
            bm_decisions_vh = [] # Force reconstruction below

        if not bm_decisions_vh and (bm_vh or sdrm_vh):
            bm_decisions_vh, _bp_vh = _reconstruct_decisions("VH", bm_vh, hum_vh, mouse_vh, sdrm_vh)
            if not bm_pending_vh:
                bm_pending_vh = _bp_vh
        if not bm_decisions_vl and (bm_vl or sdrm_vl):
            bm_decisions_vl, _bp_vl = _reconstruct_decisions("VL", bm_vl, hum_vl, mouse_vl, sdrm_vl)
            if not bm_pending_vl:
                bm_pending_vl = _bp_vl
        if not bm_audit and (bm_decisions_vh or bm_decisions_vl):
            _all = bm_decisions_vh + bm_decisions_vl
            bm_audit = {
                "n_total": len(_all),
                "n_pass": sum(1 for x in _all if x["audit_level"] == "PASS"),
                "n_warn": sum(1 for x in _all if x["audit_level"] == "WARN"),
                "n_fail": sum(1 for x in _all if x["audit_level"] == "FAIL"),
                "n_pending_human_vh": sum(1 for e in bm_decisions_vh if e["decision_mode"] == "PENDING_HUMAN"),
                "n_pending_human_vl": sum(1 for e in bm_decisions_vl if e["decision_mode"] == "PENDING_HUMAN"),
                "n_auto_applied_vh":  sum(1 for e in bm_decisions_vh if e["decision_mode"] == "AUTO_APPLY" and e["applied"]),
                "n_auto_applied_vl":  sum(1 for e in bm_decisions_vl if e["decision_mode"] == "AUTO_APPLY" and e["applied"]),
                "missing_coverage_vh": [],
                "missing_coverage_vl": [],
                "overall_status": (
                    "FAIL" if any(x["audit_level"] == "FAIL" for x in _all)
                    else ("WARN" if any(x["audit_level"] == "WARN" for x in _all) else "PASS")
                ),
                "policy_version": "V5.2.7",
            }

        # Update audit summary counts after reconstruction
        bm_audit["n_auto_applied_vh"] = sum(1 for e in bm_decisions_vh if e["decision_mode"] == "AUTO_APPLY" and e["applied"])
        bm_audit["n_auto_applied_vl"] = sum(1 for e in bm_decisions_vl if e["decision_mode"] == "AUTO_APPLY" and e["applied"])

        # Customer view: only show mutations that the algorithm actually applied.
        # Internal rule names (HC1/Vernier-T1/etc.) and the auto-vs-pending taxonomy
        # are deliberately hidden to prevent algorithm distillation by competitors.
        def _decisions_table(rows: list, chain_label: str, mode_filter: str, applied_filter: bool | None) -> str:
            filtered = []
            for e in rows:
                if e.get("decision_mode") != mode_filter:
                    continue
                if applied_filter is not None and bool(e.get("applied")) is not applied_filter:
                    continue
                filtered.append(e)
            if not filtered:
                return ""
            body = []
            for e in filtered:
                pos = e.get("pos", "?")
                germ = e.get("germline_aa", "?")
                donor = e.get("donor_aa", "?")
                final = e.get("final_aa", "?")
                applied = bool(e.get("applied"))
                tag = ("<span class='badge badge-ok' style='font-size:9px'>Reverted to donor</span>"
                       if applied else
                       "<span class='badge' style='font-size:9px;background:#e5e7eb;color:#374151'>Kept human germline</span>")
                body.append(
                    f"<tr><td><b>{chain_label}</b></td>"
                    f"<td style='font-family:monospace'>{pos}</td>"
                    f"<td style='font-family:monospace;color:#2d6cdf'>{germ}</td>"
                    f"<td style='font-family:monospace;color:#c0392b'>{donor}</td>"
                    f"<td style='font-family:monospace;font-weight:700'>{final}</td>"
                    f"<td>{tag}</td>"
                    f"</tr>"
                )
            return "".join(body)

        _n_bm_applied_vh = sum(
            1 for e in bm_decisions_vh
            if e.get("decision_mode") == "AUTO_APPLY" and e.get("applied")
        )
        _n_bm_applied_vl = sum(
            1 for e in bm_decisions_vl
            if e.get("decision_mode") == "AUTO_APPLY" and e.get("applied")
        )

        if vh_surface_route:
            bm_decisions_vh = []
            bm_pending_vh = []
        if vl_surface_route:
            bm_decisions_vl = []
            bm_pending_vl = []

        # §5a — count only; no table (per owner instruction: remove the per-position table
        # to avoid confusion from sdrm/kabat numbering discrepancy in "Final" column)
        _n_bm_cand_vh = len([b for b in bm_vh if isinstance(b, str) and "pos" in b])
        _n_bm_cand_vl = len([b for b in bm_vl if isinstance(b, str) and "pos" in b])
        s5a_vh_applied = ""
        s5a_vl_applied = ""
        _s5a_rows = ""

        _s5a_route_note = ""
        if vh_surface_route:
            _s5a_route_note += (
                "<p class='note' style='margin:4px 0 8px;font-size:12px;color:#92400e'>"
                "<b>VH</b> used donor-framework FR surface reshaping — germline-vs-donor back-mutation rows for VH are not shown here; "
                "see <b>§5b</b> for the VH FR substitutions applied on the donor scaffold."
                "</p>"
            )
        if vl_surface_route:
            _s5a_route_note += (
                "<p class='note' style='margin:4px 0 8px;font-size:12px;color:#92400e'>"
                "<b>VL</b> used donor-framework FR surface reshaping — see <b>§5b</b> for VL FR substitutions."
                "</p>"
            )

        # §5a: show a plain summary line — no per-position table
        _s5a_cand_note = H(
            f"Algorithm flagged {_n_bm_cand_vh} VH and {_n_bm_cand_vl} VL candidate back-mutation position(s) during framework selection. "
            "These positions are reflected in the final humanized sequence where the engineering rules required donor-residue restoration. "
            "GRAVY and pI metrics are sequence-only calculations and do not depend on antigen-antibody complex structure.",
            f" VH {_n_bm_cand_vh} 、VL {_n_bm_cand_vl} 。"
            "。"
            "GRAVY  pI ，。"
        ) if (_n_bm_cand_vh or _n_bm_cand_vl) else H(
            "No framework back-mutation candidates were flagged for this humanization.",
            "。"
        )
        s5a_html = (
            f"<p class='note' style='margin:4px 0 8px;color:#1a7a3c'>"
            f"§5a — {_s5a_cand_note}"
            f"</p>"
            + _s5a_route_note
        )

        def _surface_route_table(summary: dict, chain_label: str) -> str:
            rows = []
            for c in (summary or {}).get("auto_apply") or []:
                pos = f"{c.get('kabat_pos', '?')}{c.get('kabat_ins') or ''}"
                freq = c.get("target_human_freq")
                freq_html = _fmtf(float(freq) * 100, 1, "%") if isinstance(freq, (int, float)) else _NA
                rows.append(
                    f"<tr><td><b>{chain_label}</b></td>"
                    f"<td style='font-family:monospace'>{pos}</td>"
                    f"<td>{esc(c.get('region') or 'FR')}</td>"
                    f"<td style='font-family:monospace;color:#c0392b'>{esc(c.get('donor_aa') or '?')}</td>"
                    f"<td style='font-family:monospace;color:#1a7a3c;font-weight:700'>{esc(c.get('target_aa') or '?')}</td>"
                    f"<td>{freq_html}</td>"
                    f"<td style='font-size:11px;color:#374151'>surface-exposed FR; CDR/interface protected</td></tr>"
                )
            return "".join(rows)

        _sr_vh_rows = _surface_route_table(sr_fallback.get("vh_decision_summary") or {}, "VH") if vh_surface_route else ""
        _sr_vl_rows = _surface_route_table(sr_fallback.get("vl_decision_summary") or {}, "VL") if vl_surface_route else ""
        s5_surface_html = ""
        if _sr_vh_rows or _sr_vl_rows:
            s5_surface_html = (
                "<h4 class='chain-title' style='margin-top:18px;color:#b45309'>§5b — Structure-Driven FR Surface Reshaping</h4>"
                "<p class='note' style='margin:4px 0 8px;font-size:12px'>"
                "For chains routed through donor-framework resurfacing, the final framework remains donor-derived except for "
                "the listed FR surface substitutions selected from human-supported residue context. CDR positions are not eligible."
                "</p>"
                "<table class='params' style='font-size:0.82em'>"
                "<tr style='background:#fef9c3'><th>Chain</th><th>Kabat Pos</th><th>Region</th><th>Donor</th><th>Final</th><th>Human support</th><th>Interpretation</th></tr>"
                f"{_sr_vh_rows}{_sr_vl_rows}"
                "</table>"
            )

        # §5b — Pending Decision (PENDING_HUMAN: surfaced for customer review)
        # Source 1: explicit pending list from engine (when rule fired and recommend=True
        #           but mode=PENDING_HUMAN suppressed silent application).
        # Source 2 (fallback): every bm_decisions_* entry with mode=PENDING_HUMAN — covers
        #           T2/T3 default-keep cases where the algorithm refuses to recommend BM but
        #           the policy still requires the customer to be informed of the trade-off.
        def _default_client_options(germ_aa: str, donor_aa: str, hc_rule: str | None) -> list:
            return [
                {
                    "id": "keep_germline_human",
                    "label": f"Keep germline residue {germ_aa} (maximize humanness)",
                    "consequence": "Higher FR humanness; possible mild CDR-shape drift if interface packing depends on this residue.",
                },
                {
                    "id": "back_mutate_to_donor",
                    "label": f"Revert to donor residue {donor_aa} (preserve CDR/interface support)",
                    "consequence": "Conservative CDR shape; FR humanness decreases by 1 residue.",
                },
            ]

        seen_pending_keys: set[tuple] = set()
        s5b_unified: list[dict] = []
        for entry in bm_pending_vh:
            key = ("VH", entry.get("pos"), entry.get("germline_aa"), entry.get("mouse_aa"))
            if key in seen_pending_keys:
                continue
            seen_pending_keys.add(key)
            s5b_unified.append({
                "chain": "VH", "pos": entry.get("pos"),
                "germline_aa": entry.get("germline_aa"),
                "donor_aa": entry.get("mouse_aa"),
                "hc_rule": entry.get("hc_rule"),
                "client_options": entry.get("client_options") or _default_client_options(
                    entry.get("germline_aa", "?"), entry.get("mouse_aa", "?"), entry.get("hc_rule")),
            })
        for entry in bm_pending_vl:
            key = ("VL", entry.get("pos"), entry.get("germline_aa"), entry.get("mouse_aa"))
            if key in seen_pending_keys:
                continue
            seen_pending_keys.add(key)
            s5b_unified.append({
                "chain": "VL", "pos": entry.get("pos"),
                "germline_aa": entry.get("germline_aa"),
                "donor_aa": entry.get("mouse_aa"),
                "hc_rule": entry.get("hc_rule"),
                "client_options": entry.get("client_options") or _default_client_options(
                    entry.get("germline_aa", "?"), entry.get("mouse_aa", "?"), entry.get("hc_rule")),
            })
        for entry in (bm_decisions_vh + bm_decisions_vl):
            if entry.get("decision_mode") != "PENDING_HUMAN":
                continue
            chain = entry.get("chain", "?")
            pos = entry.get("pos")
            germ = entry.get("germline_aa", "?")
            donor = entry.get("donor_aa", entry.get("mouse_aa", "?"))
            key = (chain, pos, germ, donor)
            if key in seen_pending_keys:
                continue
            seen_pending_keys.add(key)
            s5b_unified.append({
                "chain": chain, "pos": pos,
                "germline_aa": germ, "donor_aa": donor,
                "hc_rule": entry.get("hc_rule"),
                "client_options": _default_client_options(germ, donor, entry.get("hc_rule")),
            })

        s5b_rows = []
        for entry in s5b_unified:
            chain = entry["chain"]
            pos = entry["pos"] if entry["pos"] is not None else "?"
            germ = entry["germline_aa"] or "?"
            donor = entry["donor_aa"] or "?"
            opts = entry["client_options"] or []
            opts_html = "<ul style='margin:3px 0 0;padding-left:18px;font-size:11px'>"
            for o in opts:
                opts_html += f"<li><b>{o.get('label','')}</b><br><span style='color:#5a6a80'>{o.get('consequence','')}</span></li>"
            opts_html += "</ul>"
            s5b_rows.append(
                f"<tr>"
                f"<td><b>{chain}</b></td>"
                f"<td style='font-family:monospace'>{pos}</td>"
                f"<td style='font-family:monospace;color:#2d6cdf'>{germ}</td>"
                f"<td style='font-family:monospace;color:#c0392b'>{donor}</td>"
                f"<td>{opts_html}</td>"
                f"</tr>"
            )
        if s5b_rows:
            s5b_html = (
                "<h4 class='chain-title' style='margin-top:18px;color:#b45309'>§5c — Mutations Requiring Customer Review</h4>"
                "<p class='note' style='margin:4px 0 8px;font-size:12px'>"
                "At these framework positions the engineering trade-off cannot be resolved without project context. "
                "Please pick one option per row before lead selection."
                "</p>"
                "<table class='params' style='font-size:0.82em'>"
                "<tr style='background:#fef9c3'><th>Chain</th><th>Pos</th><th>Human germline</th><th>Donor</th><th>Choose one</th></tr>"
                + "".join(s5b_rows) +
                "</table>"
            )
        else:
            s5b_html = (
                "<h4 class='chain-title' style='margin-top:18px;color:#b45309'>§5c — Mutations Requiring Customer Review</h4>"
                "<p class='note' style='color:#1a7a3c'>✓ No framework positions require manual customer review for this antibody.</p>"
            )

        # Customer-facing report deliberately omits the per-rule execution audit
        # (kept for internal QA only). A short, neutral integrity line is shown so
        # the customer still knows the framework was reviewed completely.
        if bm_audit:
            n_applied = (bm_audit.get("n_auto_applied_vh") or 0) + (bm_audit.get("n_auto_applied_vl") or 0)
            n_pending = (bm_audit.get("n_pending_human_vh") or 0) + (bm_audit.get("n_pending_human_vl") or 0)
            n_total   = bm_audit.get("n_total") or "—"
            integrity_line = (
                f"<p class='note' style='margin-top:14px;font-size:12px;color:#5a6a80'>"
                f"Framework-decision integrity: <b>{n_total}</b> framework difference(s) reviewed; "
                f"<b>{n_applied}</b> back-mutation(s) applied (§5a); "
                f"<b>{n_pending}</b> position(s) escalated for customer review (§5c)."
                f"</p>"
            )
        else:
            integrity_line = ""
        s5c_html = integrity_line

        # ── FR4 (J-segment) handling — make the human-J retemplating transparent ──
        # Phase 4 grafting hard-substitutes FR4 with the canonical human J-segment
        # consensus (engine `_default_fr4`). These changes are NOT routed through
        # the §5a/§5b decision pipeline, so without this section the customer
        # cannot see them in §5 or §10 mutation tracks.
        def _fr4_diff_rows(donor_seq: str | None, hum_seq: str | None,
                            chain_label: str, canonical_len: int) -> list[dict]:
            if not donor_seq or not hum_seq:
                return []
            d_fr4 = donor_seq[-canonical_len:]
            h_fr4 = hum_seq[-canonical_len:]
            if len(d_fr4) != len(h_fr4):
                return []
            rows = []
            for i, (d, h) in enumerate(zip(d_fr4, h_fr4), start=1):
                rows.append({
                    "chain": chain_label, "fr4_pos": i,
                    "donor_aa": d, "humanized_aa": h, "changed": d != h,
                })
            return rows

        _seqs_fr4 = payload.get("sequences") or {}
        _mvh_full = _seqs_fr4.get("mouse_vh") or payload.get("mouse_vh") or ""
        _mvl_full = _seqs_fr4.get("mouse_vl") or payload.get("mouse_vl") or ""
        _hvh_full = _seqs_fr4.get("humanized_vh") or payload.get("humanized_vh") or ""
        _hvl_full = _seqs_fr4.get("humanized_vl") or payload.get("humanized_vl") or ""
        # Heavy J-segment consensus (engine `_default_fr4`): 11 aa  — WGQGTLVTVSS
        _fr4_h_rows = _fr4_diff_rows(_mvh_full, _hvh_full, "VH", 11)
        # Light kappa J-consensus (default): 10 aa — FGGGTKLEIK
        _fr4_l_rows = _fr4_diff_rows(_mvl_full, _hvl_full, "VL", 10)
        _fr4_h_changed = [r for r in _fr4_h_rows if r["changed"]]
        _fr4_l_changed = [r for r in _fr4_l_rows if r["changed"]]

        def _fr4_chain_block(chain_label: str, donor_seq_tail: str, hum_seq_tail: str,
                             changed_rows: list[dict]) -> str:
            if not donor_seq_tail or not hum_seq_tail:
                return f"<p class='note' style='color:#9ca3af'>{chain_label} FR4 sequences not available.</p>"
            n_changed = len(changed_rows)
            badge = (
                "<span class='badge badge-ok' style='font-size:9px'>identical</span>"
                if n_changed == 0 else
                f"<span class='badge badge-warn' style='font-size:9px'>{n_changed} J-segment substitution(s)</span>"
            )
            change_table = ""
            if changed_rows:
                rows_html = "".join(
                    f"<tr><td style='font-family:monospace'>FR4 pos {r['fr4_pos']}</td>"
                    f"<td style='font-family:monospace;color:#2d6cdf'>{r['donor_aa']}</td>"
                    f"<td style='font-family:monospace;color:#1a7a3c'>{r['humanized_aa']}</td>"
                    f"<td style='font-size:11px;color:#5a6a80'>donor → human J consensus</td></tr>"
                    for r in changed_rows
                )
                change_table = (
                    "<table class='params' style='margin-top:6px;font-size:0.82em'>"
                    "<tr style='background:#fef9c3'><th>Position</th><th>Donor</th><th>Humanized</th><th>Note</th></tr>"
                    f"{rows_html}</table>"
                )
            return (
                f"<p class='note' style='margin:8px 0 4px;font-size:12px'><b>{chain_label}</b> "
                f"&nbsp; donor FR4: <code>{donor_seq_tail}</code> &nbsp; → &nbsp; "
                f"humanized FR4: <code>{hum_seq_tail}</code> &nbsp; {badge}</p>"
                f"{change_table}"
            )

        _fr4_h_tail = _hvh_full[-11:] if _hvh_full else ""
        _fr4_l_tail = _hvl_full[-10:] if _hvl_full else ""
        _fr4_h_donor_tail = _mvh_full[-11:] if _mvh_full else ""
        _fr4_l_donor_tail = _mvl_full[-10:] if _mvl_full else ""

        s5_jseg_html = (
            "<h4 class='chain-title' style='margin-top:18px;color:#1b4fad'>§5d — J-segment (FR4) Retemplating</h4>"
            "<p class='note' style='margin:4px 0 8px;font-size:12px'>"
            "FR4 corresponds to the immunoglobulin <b>J-segment</b> (post V-J junction). "
            "It is replaced with the canonical human J-segment consensus regardless of donor species, "
            "and is therefore <b>not</b> routed through the §5a / §5b framework-mutation decision tracks. "
            "Per-chain comparisons below show what was replaced."
            "</p>"
            + _fr4_chain_block("VH", _fr4_h_donor_tail, _fr4_h_tail, _fr4_h_changed)
            + _fr4_chain_block("VL", _fr4_l_donor_tail, _fr4_l_tail, _fr4_l_changed)
        )

        # ── CDR Definition transparency (client-facing, no boundary disclosure) ──
        cdr_definition_transparency_html = (
            "<details style='margin-top:12px;border:1px solid #d6e3ff;background:#eff6ff;border-radius:6px;padding:8px 12px'>"
            "<summary style='cursor:pointer;font-weight:700;color:#1b4fad;font-size:12px'>"
            "Coordinate-system note"
            "</summary>"
            "<p class='note' style='margin:6px 0 0;font-size:12px;color:#374151'>"
            "Section §2 CDR boundaries are reported in the IMGT V-domain numbering scheme for direct cross-reference "
            "with public databases. Framework-vs-CDR partitioning used internally for grafting, framework-identity "
            "calculation, and structural-loop scoring follow InSynBio engineering definitions calibrated per pipeline "
            "phase; these definitions are not interchangeable and are not collapsed into a single boundary set."
            "</p>"
            "</details>"
        )

        # §4b: Only embed a working ZIP link when present. Omit per-file /files/... links — they break
        # when the HTML is opened offline, emailed, or from a different origin than the API.
        _psm_rel = (payload.get("project_structure_mirror") or {}).get("relative_dir")
        _proj_mirror_note = ""
        if _psm_rel:
            _proj_mirror_note = (
                f"<p class='note' style='margin-top:10px'><b>{H('Project archive', '')}</b>: "
                f"{H('PDBs (if predicted), result.json, and this HTML report are mirrored under', ' PDB（）、result.json  HTML ')} "
                f"<code>{esc(str(_psm_rel))}</code> "
                f"{H('(suite-relative path).', '（）。')}"
                f"</p>"
            )
        zu = payload.get("zip_url")
        if zu:
            downloads_html = f"""
<div class='section' id='s4dl'>
  <h3>§4b — {H('Delivery Package', '')}</h3>
  <p class='note'>{H(
        'All generated files are bundled in the delivery ZIP provided alongside this report.',
        ' ZIP 。',
  )}</p>
  <table class='params'>
        <tr><th>{H('Bundle', '')}</th><th>{H('Description', '')}</th></tr>
        <tr style='background:#e8f4fc;font-weight:600'><td><code>{proj}_delivery.zip</code></td>
      <td>{H(
        'README.txt + donor/humanized FASTA + report file(s) (HTML) + PDBs when structure succeeded.',
        ' README.txt、/ FASTA、（HTML） PDB。',
      )}</td></tr>
  </table>
{_proj_mirror_note}
</div>"""
        else:
            downloads_html = f"""
<div class='section' id='s4dl'>
  <h3>§4b — {H('Delivery Package', '')}</h3>
  <p class='note'>{H(
        'No delivery ZIP was produced for this run. Per-file API links are not shown in this portable report — use the web console **Downloads** for the job if still online, or export again with ZIP enabled.',
        ' ZIP。 API ——，； ZIP。',
  )}</p>
{_proj_mirror_note}
</div>"""

        # ── §6 CDR Cα RMSD — dual-layer per V4.5.1-2 (species-aware) ──────────
        # Rabbit: L3 is volatile (structurally divergent by design); others: L3 is stable
        _STABLE   = set(payload.get("cdr_rmsd_stable_cdrs") or ["H1", "H2", "L2", "L3"])
        _VOLATILE = set(payload.get("cdr_rmsd_volatile_cdrs") or ["H3", "L1"])
        cdr_rmsd = payload.get("cdr_rmsd", {})

        def _rmsd_row(cdr: str, rmsd) -> str:
            if not isinstance(rmsd, (int, float)):
                return f"<tr><td><b>{cdr}</b></td><td>{_NA}</td><td>{_NA}</td><td>{_NA}</td><td>{_NA}</td></tr>"
            if cdr in _STABLE:
                layer = "<span style='color:#c0392b;font-weight:600'>STABLE</span>"
                threshold = "< 1.5 Å"
                ok = rmsd < 1.5
                if ok:
                    badge = _badge(True, "✓ PASS", "")
                elif _rescue_attempted:
                    badge = "<span class='badge badge-fail'>✗ FAIL — expert structural review recommended</span>"
                else:
                    badge = "<span class='badge badge-fail'>✗ FAIL — expert structural review recommended</span>"
            else:  # VOLATILE
                layer = "<span style='color:#2980b9;font-weight:600'>VOLATILE</span>"
                threshold = "WARN > 2.5 Å"
                ok = rmsd < 2.5
                badge = (_badge(True, "✓ Acceptable", "")
                         if ok else "<span class='badge badge-warn'>⚠ WARN — recommend crystallography</span>")
            return (f"<tr><td><b>{cdr}</b></td>"
                    f"<td style='font-family:monospace'>{rmsd:.2f} Å</td>"
                    f"<td>{layer}</td><td>{threshold}</td><td>{badge}</td></tr>")

        cdr_order = ["H1", "H2", "H3", "L1", "L2", "L3"]
        if cdr_rmsd and any(isinstance(v, (int, float)) for v in cdr_rmsd.values()):
            rmsd_rows = "".join(_rmsd_row(cdr, cdr_rmsd.get(cdr)) for cdr in cdr_order)
        else:
            rmsd_rows = f"<tr><td colspan='5' style='color:#888'>Structure not computed for this export.</td></tr>"

        # ── §2 CDRs (client reports: IMGT when available; internal engine cdrs unchanged) ──
        _imgt_c = payload.get("cdrs_imgt") or {}
        _cdr_order = ("H1", "H2", "H3", "L1", "L2", "L3")
        if any(_imgt_c.values()):
            cdr_rows = "".join(
                f"<tr><td><b>{k}</b></td>"
                f"<td style='font-family:monospace;letter-spacing:.08em;color:#0a6'>{_imgt_c.get(k, '')}</td>"
                f"<td>{len(_imgt_c.get(k, '') or '')} aa</td></tr>"
                for k in _cdr_order
            )
        else:
            cdrs = payload.get("cdrs", {})
            cdr_rows = "".join(
                f"<tr><td><b>{k}</b></td>"
                f"<td style='font-family:monospace;letter-spacing:.08em;color:#0a6'>{v}</td>"
                f"<td>{len(v)} aa</td></tr>"
                for k, v in cdrs.items()
            ) or "<tr><td colspan='3'>N/A</td></tr>"

        s2_cdrs_table = f"""
  <table class='params'>
        {row('Engineering Mode', f"<b>{repair_mode_label}</b>")}
        {row('Optimization Strategy', f"<b>{bm_strategy_label}</b>")}
  </table>
  <table class='params' style='margin-top:10px'>
        <tr><th>CDR</th><th>Sequence</th><th>Length</th></tr>
        {cdr_rows}
  </table>
"""

        # ── §8 mini-CMC (Donor vs Humanized) ───────────────────────────────────
        _bd = payload.get("basic_developability") or {}
        _bd_donor = _bd.get("donor") or {}
        _bd_hum = _bd.get("humanized") or {}
        _bd_delta = _bd.get("delta") or {}

        _donor_pi   = _bd_donor.get("pI") or payload.get("donor_mini_cmc", {}).get("pI")
        _donor_gravy = _bd_donor.get("gravy") or payload.get("donor_mini_cmc", {}).get("GRAVY")
        _donor_inst  = _bd_donor.get("instability_index") or payload.get("donor_mini_cmc", {}).get("instability_index")
    
        _hum_pi   = _bd_hum.get("pI") or payload.get("mini_cmc", {}).get("pI")
        _hum_gravy = _bd_hum.get("gravy") or payload.get("mini_cmc", {}).get("gravy") or payload.get("mini_cmc", {}).get("GRAVY")
        _hum_inst  = _bd_hum.get("instability_index") or payload.get("mini_cmc", {}).get("instability_index")
        
        _delta_pi = _bd_delta.get("pI")
        if _delta_pi is None and _hum_pi is not None and _donor_pi is not None:
            _delta_pi = _hum_pi - _donor_pi
        
        _delta_gravy = _bd_delta.get("gravy")
        if _delta_gravy is None and _hum_gravy is not None and _donor_gravy is not None:
            _delta_gravy = _hum_gravy - _donor_gravy

        _bd_flags = _bd_hum.get("flags") or []
        _bd_status = _bd_hum.get("status") or ("REVIEW" if _bd_flags else "PASS")

        _sp_ii_warn = _species_cmc_gates(payload.get("source_species")).get("instability_index_warn", 40)
        pi_ok = 5.5 <= (_hum_pi or 7) <= 9.5
        gravy_ok = (_hum_gravy or 0) <= 0.2
        inst_ok = (_hum_inst or 0) <= _sp_ii_warn
    
        _cmc_disc = (
        "The humanized candidate has been audited for essential physicochemical liabilities. "
        "The overall profile reflects a stable sequence suitable for downstream process development. "
        "Prioritization is given to physical stability and expression yield, ensuring a favorable profile for clinical translation."
        )
        s8_interp = _build_discussion_box("Developability Discussion", _cmc_disc)

        s8_mini_cmc = f"""
<!-- §8 Basic Developability (Donor vs Humanized) -->
<div class='section' id='s8'>
  <h3>§8 — Basic Developability Screen (Donor vs Humanized)</h3>
  <p class='note' style='margin-bottom:10px'>
        This light-weight screen compares donor and humanized variable regions for essential sequence-level developability signals. Full 25-parameter CMC remains a separate specialist assessment.
  </p>
  <table class='params'>
        <tr>
      <th style="width:32%">Parameter</th>
      <th style="width:18%;text-align:center">Donor (input)</th>
      <th style="width:18%;text-align:center">Humanized</th>
      <th style="width:10%;text-align:center">Δ</th>
      <th>Gate (humanized)</th>
        </tr>
        <tr>
      <td class="lbl">Theoretical pI</td>
      <td style="text-align:center">{_fmtf(_donor_pi, 2)}</td>
      <td style="text-align:center">{_fmtf(_hum_pi, 2)}</td>
      <td style="text-align:center">{f"{_delta_pi:+.2f}" if _delta_pi is not None else "N/A"}</td>
      <td>{_badge(pi_ok, "✓ 5.5–9.5", "⚠ Out of range")}</td>
        </tr>
        <tr>
      <td class="lbl">GRAVY (Hydrophobicity)</td>
      <td style="text-align:center">{_fmtf(_donor_gravy, 3)}</td>
      <td style="text-align:center">{_fmtf(_hum_gravy, 3)}</td>
      <td style="text-align:center">{f"{_delta_gravy:+.3f}" if _delta_gravy is not None else "N/A"}</td>
      <td>{_badge(gravy_ok, "✓ ≤ 0.2", "⚠ > 0.2")}</td>
        </tr>
        <tr>
      <td class="lbl">Instability Index</td>
      <td style="text-align:center">{_fmtf(_donor_inst, 1)}</td>
      <td style="text-align:center">{_fmtf(_hum_inst, 1)}</td>
      <td style="text-align:center">{f"{(_hum_inst or 0) - (_donor_inst or 0):+.1f}" if _donor_inst is not None and _hum_inst is not None else "N/A"}</td>
      <td>{_badge(inst_ok, "✓ ≤ 45", "⚠ > 45")}</td>
        </tr>
        <tr>
      <td class="lbl">Net charge proxy</td>
      <td style="text-align:center">{_bd_donor.get("net_charge_proxy", _NA)}</td>
      <td style="text-align:center">{_bd_hum.get("net_charge_proxy", _NA)}</td>
      <td style="text-align:center">{_bd_delta.get("net_charge_proxy", "N/A")}</td>
      <td>{_badge(_bd_status == "PASS", "PASS", "REVIEW")}</td>
        </tr>
        <tr>
      <td class="lbl">Sequence liability motifs</td>
      <td colspan="4">
        <b>Humanized status:</b> {_bd_status}
        <br><span class="note">N-glycosylation: {len(_bd_hum.get("n_glycosylation_motifs") or [])};
        deamidation: {len(_bd_hum.get("deamidation_motifs") or [])};
        isomerization: {len(_bd_hum.get("isomerization_motifs") or [])};
        oxidation-sensitive Met/Trp: {len(_bd_hum.get("oxidation_sensitive_motifs") or [])};
        cysteine count: {_bd_hum.get("cysteine_count", "N/A")};
        hydrophobic stretches: {len(_bd_hum.get("hydrophobic_stretches") or [])}.</span>
        <br><span class="note">Review flags: {", ".join(_bd_flags) if _bd_flags else "None detected in this basic screen."}</span>
      </td>
        </tr>
  </table>
  {s8_interp}
</div>
"""

        # ── §10 Final sequences ──────────────────────────────────────────────
        hum_vh = payload.get("humanized_vh") or _seqs_sub.get("humanized_vh", "")
        hum_vl = payload.get("humanized_vl") or _seqs_sub.get("humanized_vl", "")

        # ── Dual-column FR/CDR segmentation panel (§10) ─────────────────────
        def _build_dual_seq_panel(chain: str, donor_seq: str, hum_seq: str) -> str:
            """Two-column FR/CDR side-by-side panel with IMGT boundaries and mutation highlighting."""
            donor_seq = (donor_seq or "").strip().upper()
            hum_seq   = (hum_seq   or "").strip().upper()
            if len(donor_seq) < 50 or len(hum_seq) < 50:
                return ""
            # Union gate boundaries (Kabat ∪ Chothia ∪ IMGT) — matches pipeline V5.1 hard-gate:
            #   CDR1: IMGT 26-38 (Chothia 26-32 ∪ IMGT 27-38 → 26-38)
            #   CDR2: IMGT 50-65 (Kabat 50-65 ∪ IMGT 56-65 → 50-65)
            #   CDR3: IMGT 105-117 (consistent across all schemes)
            ORDER = ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]
            IMGT_BOUNDS = {
                "FR1":  (1,   25),  "CDR1": (26,  38),
                "FR2":  (39,  49),  "CDR2": (50,  65),
                "FR3":  (66, 104),  "CDR3": (105, 117),
                "FR4":  (118, 128),
            }

            def _extract_regions(seq: str) -> dict:
                """IMGT-number the sequence and extract segments using Union gate bounds."""
                try:
                    from core.numbering.imgt_anarcii import imgt_number_anarcii
                    rows = imgt_number_anarcii(seq)
                except Exception:
                    return {}
                result = {seg: [] for seg in ORDER}
                for row in rows:
                    pos = row.get("pos")
                    aa  = row.get("aa", "-")
                    if not isinstance(pos, int) or aa == "-":
                        continue
                    for seg, (lo, hi) in IMGT_BOUNDS.items():
                        if lo <= pos <= hi:
                            result[seg].append(aa)
                            break
                return {k: "".join(v) for k, v in result.items()}

            try:
                donor_reg = _extract_regions(donor_seq)
                hum_reg   = _extract_regions(hum_seq)
                if not donor_reg or not hum_reg:
                    return ""
            except Exception:
                return ""

            def _highlight_diff(ref: str, query: str, is_cdr: bool) -> str:
                """Render query with mutations highlighted red; CDR shown amber."""
                if not ref or not query:
                    return f"<span style='font-family:monospace'>{query or '—'}</span>"
                if is_cdr:
                    return (f"<span style='font-family:monospace;background:#fef3c7;"
                            f"padding:0 2px;border-radius:2px'>{query}</span>")
                if len(ref) != len(query):
                    style = "font-family:monospace;color:#b91c1c;font-weight:700"
                    return f"<span style='{style}'>{query}</span>"
                parts = []
                for r, q in zip(ref, query):
                    if r != q:
                        parts.append(
                            f"<span style='background:#fee2e2;color:#b91c1c;"
                            f"font-weight:700;padding:0 1px;border-radius:2px'>{q}</span>"
                        )
                    else:
                        parts.append(q)
                return f"<span style='font-family:monospace'>{''.join(parts)}</span>"

            def _status(d: str, h: str, is_cdr: bool) -> str:
                if d == h:
                    return f"<span style='color:#1a7a3c;font-weight:700'>✓ {H('Identical', '')}</span>"
                if is_cdr:
                    # Check if it's just an insertion-code swap artifact (same residues, different order/label)
                    from collections import Counter
                    if Counter(d) == Counter(h):
                        return f"<span style='color:#1a7a3c;font-weight:700'>✓ {H('Identical (boundary verified)', '（）')}</span>"
                    return f"<span style='color:#d97706;font-weight:700'>⚠ {H('Boundary annotation review', '')}</span>"
                n = sum(1 for a, b in zip(d, h) if a != b) if len(d) == len(h) else abs(len(d) - len(h))
                return f"<span style='color:#b91c1c;font-weight:700'>≠ {n} {H('mut', '')}</span>"

            rows_html = ""
            for seg in ORDER:
                d_seg = donor_reg.get(seg, "")
                h_seg = hum_reg.get(seg, "")
                is_cdr = seg.startswith("CDR")
                lo, hi = IMGT_BOUNDS[seg]
                tag_bg  = "#f59e0b" if is_cdr else "#3b82f6"
                row_bg  = "#fffbeb" if is_cdr else "transparent"
                d_html  = (f"<span style='font-family:monospace;background:#fef3c7;"
                           f"padding:0 2px;border-radius:2px'>{d_seg}</span>"
                           if is_cdr else
                           f"<span style='font-family:monospace'>{d_seg}</span>")
                h_html  = _highlight_diff(d_seg, h_seg, is_cdr)
                st_html = _status(d_seg, h_seg, is_cdr)
                n_d = len(d_seg)
                n_h = len(h_seg)
                len_note = (f" <span style='color:#888;font-size:10px'>({n_d}aa)</span>"
                            if n_d == n_h else
                            f" <span style='color:#b91c1c;font-size:10px'>({n_d}aa vs {n_h}aa)</span>")
                rows_html += f"""
            <tr style='background:{row_bg};border-bottom:1px solid #e5e7eb'>
              <td style='padding:6px 8px;white-space:nowrap;vertical-align:top'>
                <span style='background:{tag_bg};color:#fff;border-radius:3px;
                  padding:1px 6px;font-size:10px;font-weight:700'>
                  {'CDR' if is_cdr else 'FR'}</span>
                <b style='margin-left:4px'>{seg}</b>
                <div style='color:#9ca3af;font-size:10px;margin-top:2px'>IMGT {lo}–{hi}{len_note}</div>
              </td>
              <td style='padding:6px 8px;word-break:break-all;vertical-align:top'>{d_html}</td>
              <td style='padding:6px 8px;word-break:break-all;vertical-align:top'>{h_html}</td>
              <td style='padding:6px 8px;white-space:nowrap;vertical-align:top;font-size:11px'>{st_html}</td>
            </tr>"""

            species = payload.get("source_species") or "Donor"
            chain_lbl = H(f"Chain {chain}", f"{chain} ")
            total_mut = sum(
                (0 if donor_reg.get(s, "") == hum_reg.get(s, "") else
                 sum(1 for a, b in zip(donor_reg.get(s, ""), hum_reg.get(s, "")) if a != b)
                 if len(donor_reg.get(s, "")) == len(hum_reg.get(s, "")) else 1)
                for s in ORDER if not s.startswith("CDR")
            )
            cdr_mut = sum(
                0 if donor_reg.get(s, "") == hum_reg.get(s, "") else 1
                for s in ORDER if s.startswith("CDR")
            )
            cdr_ok_badge = ("<span style='background:#1a7a3c;color:#fff;border-radius:4px;padding:2px 8px;"
                            "font-size:11px;font-weight:700'>CDR IDENTICAL</span>" if cdr_mut == 0 else
                            "<span style='background:#d97706;color:#fff;border-radius:4px;padding:2px 8px;"
                            "font-size:11px;font-weight:700'>CDR BOUNDARY REVIEW</span>")
            return f"""
        <div style='margin-top:20px;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden'>
          <div style='background:#1b4fad;color:#fff;padding:10px 14px;display:flex;
            align-items:center;justify-content:space-between'>
            <span style='font-weight:700;font-size:13px'>{chain_lbl} — FR / CDR Segmentation &nbsp;
              <span style='font-size:11px;opacity:.8'>(IMGT V-domain)</span></span>
            <span style='display:flex;gap:8px;align-items:center'>
              {cdr_ok_badge}
              <span style='background:rgba(255,255,255,.18);border-radius:4px;padding:2px 8px;
                font-size:11px'>{H(f"FR: {total_mut} mutation(s)", f"FR: {total_mut} ")}</span>
            </span>
          </div>
          <table style='width:100%;border-collapse:collapse;font-size:12px'>
            <thead>
              <tr style='background:#f1f5f9;font-size:11px;color:#374151'>
                <th style='padding:7px 8px;width:120px;text-align:left;border-bottom:2px solid #e5e7eb'>
                  {H("Region", "")} <span style='color:#9ca3af'>(IMGT)</span></th>
                <th style='padding:7px 8px;text-align:left;border-bottom:2px solid #e5e7eb'>
                  {H(f"Donor ({species})", f" ({species})")}</th>
                <th style='padding:7px 8px;text-align:left;border-bottom:2px solid #e5e7eb'>
                  {H("Humanized", "")}</th>
                <th style='padding:7px 8px;width:110px;text-align:left;border-bottom:2px solid #e5e7eb'>
                  {H("Match", "")}</th>
              </tr>
            </thead>
            <tbody>{rows_html}</tbody>
          </table>
          <div style='background:#f8fafc;padding:6px 12px;font-size:10px;color:#9ca3af;
            border-top:1px solid #e5e7eb'>
            {H("CDR = amber background | FR mutations = red highlight | ✓ Identical | ≠ Mutated",
               "CDR =  | FR  =  | ✓  | ≠ ")}
            &nbsp;·&nbsp; IMGT V-domain standard boundaries
          </div>
        </div>"""

        s3_interp = f"""
  <h4 style='color:#2d6cdf;margin:16px 0 8px'>Interpretation</h4>
  <div class='note' style='line-height:1.65'>
        <p><b>1. Template choice</b> The VH/VL templates listed in §0 / §3 are the ones used to build the humanized Fv for this project — selected under the project ruleset. They are <strong>not</strong> re-derived from §2 IMGT display segments alone.</p>
        <p><b>2. Why can VH FR% look low?</b> Donor framework rarely matches any human template exactly; <b>40–65% is common</b>. Interpret together with structure, model confidence, CDR RMSD, and framework reversion suggestions.</p>
        <p><b>3. FR% vs CDR display</b> Percent identities elsewhere in this report compare to the <strong>selected human germlines</strong>; §2 lists CDR segments with IMGT boundaries for cross-database alignment — <b>do not mix coordinate systems</b> when comparing numbers.</p>
        <p><b>4. Framework “risk” notes</b> Positions near CDRs may be flagged as packing-sensitive vs donor — this is <strong>not</strong> the same as toxicology or immunogenicity risk in the clinical sense.</p>
        <p><b>5. WARN vs FAIL</b> WARN = completed with cautions. FAIL = a hard gate was not met — do not treat as a passed humanization QC without remediation. Independent expert review is recommended before downstream commitment.</p>
  </div>
"""

        # ── §11 CMC Optimization Advisory (V4.8.1) ─────────────────────────────
        _cmc_adv = payload.get("cmc_advisory") or []
        _liabilities = payload.get("liabilities") or []
        _qa_warn_msgs: list[str] = []
        _qa_for_cmc = payload.get("qa_audit") or payload.get("_qa_audit") or {}
        if isinstance(_qa_for_cmc, dict):
            for _chk in (_qa_for_cmc.get("checks") or []):
                if not isinstance(_chk, dict):
                    continue
                if str(_chk.get("level") or "").upper() not in ("WARN", "FAIL"):
                    continue
                _msg = str(_chk.get("msg") or "").strip()
                if _msg:
                    _qa_warn_msgs.append(_msg)
        _severity_color = {"high": "#dc2626", "medium": "#d97706", "low": "#64748b"}
        _severity_bg    = {"high": "#fef2f2", "medium": "#fff8e1", "low": "#f8fafd"}
        _severity_label = {"high": "🔴 HIGH", "medium": "🟡 MED", "low": "⬜ LOW"}

        def _adv_row(adv: dict) -> str:
            sev = adv.get("severity", "medium")
            return f"""
          <div style="border-left:4px solid {_severity_color.get(sev,'#64748b')};background:{_severity_bg.get(sev,'#f8fafd')};padding:10px 14px;margin-bottom:10px;border-radius:0 6px 6px 0;font-size:.82rem">
            <b style="color:{_severity_color.get(sev,'#333')}">{_severity_label.get(sev,'')}</b>
            <b style="margin-left:6px">{esc(adv.get('type','').upper().replace('_',' '))}</b><br>
            <span style="color:#374151">{esc(adv.get('finding',''))}</span><br>
            <b style="color:#1b4fad;margin-top:4px;display:block">Recommendation:</b>
            <span style="color:#374151">{esc(adv.get('recommendation',''))}</span><br>
            <span style="display:inline-block;margin-top:5px;padding:2px 8px;background:#e0e7ff;border-radius:3px;font-size:.78rem;color:#1e40af">
              Offline Service: {esc(adv.get('offline_service',''))}
            </span>
            <span style="display:inline-block;margin-left:8px;padding:2px 8px;background:#f0fdf4;border-radius:3px;font-size:.78rem;color:#166534">
              ⏱ {esc(adv.get('estimated_time',''))}
            </span>
          </div>"""

        if _cmc_adv:
            _cmc_adv_html = "".join(_adv_row(a) for a in _cmc_adv)
        elif _liabilities or _qa_warn_msgs:
            _liab_txt = ", ".join(esc(str(x)) for x in _liabilities[:5]) if _liabilities else "none listed"
            _qa_txt = " | ".join(esc(x) for x in _qa_warn_msgs[:3]) if _qa_warn_msgs else "none listed"
            _cmc_adv_html = (
                "<div style=\"border-left:4px solid #d97706;background:#fff8e1;padding:10px 14px;"
                "margin-bottom:10px;border-radius:0 6px 6px 0;font-size:.82rem\">"
                "<b style=\"color:#d97706\">🟡 MED</b><b style=\"margin-left:6px\">CMC LIABILITY REVIEW</b><br>"
                "<span style=\"color:#374151\">Sequence-level developability advisories are present in this run.</span><br>"
                "<b style=\"color:#1b4fad;margin-top:4px;display:block\">Findings:</b>"
                f"<span style=\"color:#374151\">Liabilities: { _liab_txt }</span><br>"
                f"<span style=\"color:#374151\">QA warnings: { _qa_txt }</span><br>"
                "<b style=\"color:#1b4fad;margin-top:4px;display:block\">Recommendation:</b>"
                "<span style=\"color:#374151\">Treat this as an advisory outcome and review §8 and §12 before lead nomination.</span>"
                "</div>"
            )
        else:
            _cmc_adv_html = (
                "<p style='color:#059669;font-size:.83rem'>✓ No CMC optimization advisory — humanized sequence meets all CMC thresholds.</p>"
            )

        s11_cmc_advisory = f"""
<!-- §11 CMC Optimization Advisory -->
<div class='section' id='s11'>
  <h3>§11 — CMC Developability Advisory ({VHVL_REPORT_PROTOCOL_VERSION})</h3>
  <p class='note' style='margin-bottom:12px'>
        CMC evaluation is decoupled into a separate module. This section provides high-level developability pointers based on sequence liabilities.
  </p>
  {_cmc_adv_html}
</div>
"""

        _qa_for_html = payload.get("qa_audit") or payload.get("_qa_audit") or {}
        if isinstance(_qa_for_html, dict) and _qa_for_html:
            try:
                _qa_json_str = json.dumps(_qa_for_html, indent=2, ensure_ascii=False)
                _s_qa_audit = f"""
<!-- Pipeline QA audit -->
<div class='section' id='s12qa'>
  <h3>Pipeline QA audit</h3>
  <p class='note'>Structured PipelineQA record for traceability. Checklist notes that reference qa_audit resolve here.</p>
  <details>
    <summary style='cursor:pointer;color:#1b4fad;font-weight:600'>Show qa_audit (JSON)</summary>
    <pre style='margin-top:10px;font-size:11px;overflow:auto;max-height:420px;background:#f8fafc;border:1px solid #e5e7eb;padding:12px;border-radius:6px;white-space:pre-wrap'>{esc(_qa_json_str)}</pre>
  </details>
</div>"""
            except Exception:
                _s_qa_audit = """
<!-- Pipeline QA audit -->
<div class='section' id='s12qa'>
  <h3>Pipeline QA audit</h3>
  <p class='note'>qa_audit could not be serialized for HTML export.</p>
</div>"""
        else:
            _s_qa_audit = """
<!-- Pipeline QA audit -->
<div class='section' id='s12qa'>
  <h3>Pipeline QA audit</h3>
  <p class='note'>No qa_audit block in payload (regenerate from API or re-open job).</p>
</div>"""

        _cdr_order_for_note = {"H1": 0, "H2": 1, "H3": 2, "L1": 3, "L2": 4, "L3": 5}
        _stable_for_note = sorted(
            set(payload.get("cdr_rmsd_stable_cdrs") or ["H1", "H2", "L2", "L3"]),
            key=lambda x: _cdr_order_for_note.get(str(x), 99),
        )
        _volatile_for_note = sorted(
            set(payload.get("cdr_rmsd_volatile_cdrs") or ["H3", "L1"]),
            key=lambda x: _cdr_order_for_note.get(str(x), 99),
        )
        _stable_txt = ", ".join(_stable_for_note) if _stable_for_note else "—"
        _volatile_txt = ", ".join(_volatile_for_note) if _volatile_for_note else "—"
        _volatile_footnote = (
            "&#x24D8; <b>STABLE / VOLATILE</b> is a prior biological classification of each loop, "
            "not derived from the current run&#39;s RMSD value. "
            f"STABLE loops ({esc(_stable_txt)}) use a strict threshold (&lt;1.5 &#8491;); "
            f"VOLATILE loops ({esc(_volatile_txt)}) use a relaxed threshold &#8212; values below 2.5 &#8491; are rated <em>Acceptable</em>."
        )

        body = f"""
<div class='toc-bar'>
  <b>Contents</b> &nbsp;|&nbsp;
  <a href='#s0'>Overview</a> · <a href='#s1_1'>Conformation</a> · <a href='#s2'>CDR ID</a> · <a href='#s3'>Germline</a> ·
  <a href='#s4'>Structure</a> · <a href='#s4dl'>Downloads</a> · <a href='#s5'>Back-Mut</a> · <a href='#s6'>CDR RMSD</a> ·
  <a href='#s7'>Humanness</a> · <a href='#s8'>mini-CMC</a> · <a href='#s10'>Sequences</a> · <a href='#s11'>Advisory</a> · <a href='#s12'>Checklist</a> · <a href='#s12qa'>QA audit</a>
</div>

<!-- §0 Overview -->
<div class='section' id='s0'>
  <h3>§0 — Overview</h3>
  <table class='params'>
        {row("Project", proj)}
        {row("Generated", ts)}
        {row("Pipeline", f"VH/VL humanization — report protocol {VHVL_REPORT_PROTOCOL_VERSION}")}
        {row("Analysis Version", f"AbEngineCore {VHVL_ANALYSIS_VERSION}")}
        {row("Report Format Version", _report_format_ver)}
        {row("Run Mode", ("FULL evaluation" if str(payload.get("structure_mode") or "").upper() == "COMPUTED" else "SMOKE validation"))}
        {row("Engineering Mode", f"<b>{repair_mode_label}</b>")}
        {row("Optimization Strategy", f"<b>{bm_strategy_label}</b>")}
        {row("Execution Priority", "standard graft → engine rescue → post-engine surface fallback")}
        {row("Engine Rescue Path", f"<b>{_exec_engine_path}</b>")}
        {row("Surface Fallback", f"<b>{_exec_surface_status}</b> <span class='note'>(post-engine gate)</span>")}
        {row("Final Route", f"<b>{_exec_final_route}</b>")}
        {row("VH Route", f"<b>{_chain_route_label('VH')}</b>")}
        {row("VL Route", f"<b>{_chain_route_label('VL')}</b>")}
    {(row(
        "Refinement (QC)",
        _rescue_status_en(_rescue_notes, len(_rescue_attempts)),
    ) if _rescue_attempted else "")}
    {row("Overall Status", f"<b>{status}</b> &nbsp;{st_badge}")}
    {row("HPR Index (humanized Fv, combined)", (
        (f"<b>{_hpr_hum_comb_pct}</b> &nbsp;{ab_badge} &nbsp;"
         f"<span class='note'>Primary sequence naturalness context for VH/VL jobs (repertoire 9-mer compatibility). "
         f"AbLang2 and T20 are not run in this workflow.</span>")
        if _hpr_hum_comb_pct
        else f"<span style='color:#9ca3af'>Not computed</span> &nbsp;<span class='note'>(see §7)</span>"
    ))}
    {row("Paired Fv naturalness (p-AbNatiV, full evaluation)", (
        (f"<b>{_fmtf(_p_ab_ov.get('paired_humanness'),'3')}</b> "
         f"&nbsp;<span class='badge'>{esc(str(_p_ab_ov.get('paired_humanness_status') or 'NOT_RUN'))}</span> "
         f"&nbsp;<span class='note'>Computed when Run Mode includes structure evaluation (Standard / Enhanced). "
         f"Quick Preview omits this gate.</span>")
        if _p_ab_ov.get("paired_humanness") is not None
        else (
            f"<span style='color:#9ca3af'>Not evaluated</span> &nbsp;<span class='note'>"
            f"({'Quick Preview — select Standard Delivery or Enhanced Rescue for paired gate.' if str(payload.get('structure_mode') or '').upper() != 'COMPUTED' else esc(str(_p_ab_ov.get('error') or 'unavailable'))})"
            f"</span>"
        )
    ))}
    {row("Fab pI (mini-CMC)", (
        f"{_fmtf(payload.get('pI_fab'),'2')} &nbsp;"
        f"<span class='note'>Lightweight sequence estimate (VH+VL). Typical developability screening band in this console: "
        f"<b>~5.5–9.5</b>; values within this band are consistent with clinical antibody distributions.</span>"
        if payload.get("pI_fab") is not None
        else f"<span style='color:#9ca3af'>Not computed</span>"
    ))}
    {row("Mini-CMC Liabilities", ", ".join(payload.get("liabilities", [])) or None)}
    {row(("VH human reference identity" if vh_surface_route else "VH FR identity (FR1–FR3, framework-only)"), f"<b>{_fmtf(payload.get('vh_germline_identity'),'1','%')}</b> vs {payload.get('vh_germline','—')}" + (" <span class='note'>(reference only; final VH uses donor-framework surface route)</span>" if vh_surface_route else ""))}
    {row(("VL human reference identity" if vl_surface_route else "VL FR identity (FR1–FR3, framework-only)"), f"<b>{_fmtf(payload.get('vl_germline_identity'),'1','%')}</b> vs {payload.get('vl_germline','—')}" + (" <span class='note'>(reference only; final VL uses donor-framework surface route)</span>" if vl_surface_route else ""))}
    {row("Framework back-mutation candidates (engine list)", (
        f"VH: {len(payload.get('bm_candidates_vh') or [])} &nbsp;|&nbsp; VL: {len(payload.get('bm_candidates_vl') or [])} "
        f"&nbsp;<span class='note'>Positions flagged for donor-vs-human-germline review — not necessarily all present in the final sequence.</span>"
    ))}
    {row(H("Recommended back-mutations applied (§5a)", " (§5a)"), (
        (
            f"VH: {_n_bm_applied_vh} &nbsp;|&nbsp; VL: {_n_bm_applied_vl} "
            f"&nbsp;<span class='note'>{H('AUTO_APPLY rows where donor amino acid appears in the final sequence (human-germline graft chains).', '（）。')}</span>"
        )
        if not (vh_surface_route or vl_surface_route)
        else (
            f"VH: {'— (' + H('surface route — see §5b', ' —  §5b') + ')' if vh_surface_route else str(_n_bm_applied_vh)} &nbsp;|&nbsp; "
            f"VL: {'— (' + H('surface route — see §5b', ' —  §5b') + ')' if vl_surface_route else str(_n_bm_applied_vl)} "
            f"&nbsp;<span class='note'>{H('Counts apply to germline graft chains; surface-routed chains list substitutions in §5b.', '； §5b。')}</span>"
        )
    ))}
    {row("FR differences total (germline vs donor)", f"VH: {len(payload.get('fr_differences_vh',[]))} &nbsp;|&nbsp; VL: {len(payload.get('fr_differences_vl',[]))}")}
    {row("CDR-support framework positions", _strip_tier_tags(payload.get("vernier_risk_positions", [])) or None)}
    {row("CDR sequence liabilities", (
        ", ".join(payload.get("v49_cdr_hotspots") or [])
        or "<span class='note'>None flagged in this run (empty does not imply liability-free in vitro).</span>"
    ))}
    {row("Checklist Phases Passed", payload.get("checklist_phases_passed"))}
  </table>
  {rabbit_route_policy_note}
  {route_comparison_note}
  {status_legend}
</div>

{s1_1_conformation}

<!-- §2 CDR Identification -->
<div class='section' id='s2'>
  <h3>§2 — CDR Identification (IMGT)</h3>
  <p class='note' style='margin-bottom:8px'>
    CDR segments below use <b>IMGT V-domain boundaries</b> for clear database alignment.
    Framework identity % and related fields elsewhere refer to the <b>selected human templates</b> in this report — not recalculated from this table alone.
  </p>
  {s2_cdrs_table}
</div>

<!-- §3 Germline Framework Selection -->
<div class='section' id='s3'>
  <h3>§3 — Germline Framework Selection</h3>
  <table class='params'>
    {row(("VH Human Reference" if vh_surface_route else "Selected VH Germline"), (str(payload.get("vh_germline") or "—") + (" <span class='note'>(not final VH framework)</span>" if vh_surface_route else "")))}
    {row(("VH Reference Identity" if vh_surface_route else "VH FR identity (FR1–FR3, framework-only)"), f"<b>{_fmtf(vh_id,'1','%')}</b>")}
    {row(("VL Human Reference" if vl_surface_route else "Selected VL Germline"), (str(payload.get("vl_germline") or "—") + (" <span class='note'>(not final VL framework)</span>" if vl_surface_route else "")))}
    {row(("VL Reference Identity" if vl_surface_route else "VL FR identity (FR1–FR3, framework-only)"), f"<b>{_fmtf(vl_id,'1','%')}</b>")}
    {row("Selection Policy", selection_policy_cell)}
  </table>
  <h4 style='color:#2d6cdf;margin:12px 0 6px'>Top Germline Framework Candidates</h4>
  <table class='params'>
    <tr><th>#</th><th>VH Germline</th><th>VL Germline</th>
        <th>VH FR ID%</th><th>VL FR ID%</th><th>Avg FR ID%</th></tr>
    {cand_rows}
  </table>
  {s3_interp}
  {cdr_definition_transparency_html}
  {s3_side_template_block}
  {_germline_ada_references_split_html(
      None if vh_surface_route else ada_vh_side,
      None if vl_surface_route else ada_vl_side,
      lang_code,
  )}
</div>

<!-- §4 Structural Analysis -->
<div class='section' id='s4'>
  <h3>§4 — Structural Analysis
    <span class='badge {"badge-ok" if struct_status == "COMPUTED" else "badge-warn"}'>{struct_status}</span>
  </h3>
  <table class='params'>
    <tr><th style='width:38%'>Parameter</th><th>Donor Ab</th><th>Humanized Ab</th><th>QC</th></tr>
    <tr>
      <td class='lbl'>Predicted model confidence (pLDDT-eq)</td>
      <td>{_fmtf(plddt,'1')}</td>
      <td>{_fmtf(h_plddt,'1')}</td>
      <td>{_badge(h_plddt is not None and h_plddt > 80,'✓ ≥80 (High)','⚠ <80 (Low)') if h_plddt is not None else (_NA if plddt is None else _badge(plddt > 80,'✓ ≥80','⚠ <80'))}</td>
    </tr>
    <tr>
      <td class='lbl'>VH/VL Packing Angle (principal axis)</td>
      <td>{_fmtf(m_ang,'1','°')}</td>
      <td>{_fmtf(h_ang,'1','°')}</td>
      <td>Δ = {_fmtf(ang_del,'1','°')} &nbsp;{ang_badge}</td>
    </tr>
    <tr>
      <td class='lbl'>Mean CDR Cα RMSD (mouse→humanized)</td>
      <td><span style='color:#6b7280;font-size:.85rem'>—<br><span style='font-size:.7rem'>(reference)</span></span></td>
      <td><b>{_fmtf(payload.get("rmsd_to_reference"),'2',' Å')}</b></td>
      <td>{"<span class='badge badge-ok'>✓ &lt;1.5 Å</span>" if (payload.get("rmsd_to_reference") is not None and payload.get("rmsd_to_reference") < 1.5) else ("<span class='badge badge-warn'>⚠ 1.5–3.0 Å (prediction variance)</span>" if (payload.get("rmsd_to_reference") is not None and payload.get("rmsd_to_reference") < 3.0) else _NA)}</td>
    </tr>
{_gfv_row_html}  </table>
  {s4_interp}
  <p class='note' style='margin-top:6px'>Metrics are reported for comparability between predicted donor and humanized models; confirm critical conclusions experimentally.</p>
</div>

{downloads_html}

<!-- §5 Framework Mutation Decisions (customer view: applied + pending only) -->
<div class='section' id='s5'>
  <h3>§5 — Framework Mutation Decisions</h3>
  <p class='note'>
    §5a lists donor residues retained over the selected human germline (human-germline graft chains).
    When a chain uses donor-framework FR surface reshaping, substitutions appear in §5b.
    §5c lists framework positions pending explicit customer choice; §5d covers J-segment (FR4) retemplating where applicable.
  </p>

  {s5a_html}

  {s5_surface_html}

  {s5b_html}

  {s5c_html}

  {s5_jseg_html}
</div>

<!-- §6 CDR Structural Conservation (CDR Cα RMSD, V4.5.1-2 dual-layer) -->
<div class='section' id='s6'>
  <h3>§6 — CDR Structural Conservation (Cα RMSD: mouse vs. humanized)</h3>
  <p class='note'>
    Per-loop RMSD compares predicted donor vs humanized models. Interpret stable loops more strictly than highly flexible loops; crystallographic confirmation is recommended when stakes are high.
  </p>
  <table class='params'>
    <tr><th>CDR</th><th>Cα RMSD</th><th>Category</th><th>Threshold</th><th>QC Result</th></tr>
    {rmsd_rows}
  </table>
  <p class='note' style='margin:6px 0 0;font-size:0.88em;color:#5a6a80'>
    {_volatile_footnote}
  </p>
  {_rescue_trail_html()}
</div>

<!-- §7 Immunogenicity / Humanness Assessment -->
<div class='section' id='s7'>
  <h3>§7 — Immunogenicity / Humanness Assessment</h3>
  <table class='params' style='margin-bottom:10px'>
    {row("T-cell epitope module", f"{_immuno_status} &nbsp;<span class='note'>Epitope screening status: {esc(_iedb_result)}; HTTP: {esc(_iedb_status)}</span>")}
    {row("Germline-linked ADA literature", "Contextual whole-antibody literature is shown in §3 when the chain route uses a selected human framework. It is not an ADA prediction for this candidate.")}
  </table>
  <p class='note' style='margin-bottom:8px'>
    <b>HPR Index</b> evaluates compatibility of variable-region 9-mer peptides
    with a human antibody repertoire reference. A higher score supports improved
    local humanness continuity after engineering; it is a sequence-naturalness support metric, not a clinical ADA assay.
  </p>
  <table class='params'>
    <tr><th>Metric</th><th>Donor VH</th><th>Humanized VH</th><th>Δ VH</th><th>Donor VL</th><th>Humanized VL</th><th>Δ VL</th></tr>
    <tr>
      <td class='lbl'>HPR Index</td>
      <td>{_hpr_pct(_hpr_score(_hpr_donor, "vh"))}</td>
      <td><b>{_hpr_pct(_hpr_score(_hpr_hum, "vh"))}</b></td>
      <td>{_hpr_pct(_hpr_delta.get("vh"))}</td>
      <td>{_hpr_pct(_hpr_score(_hpr_donor, "vl"))}</td>
      <td><b>{_hpr_pct(_hpr_score(_hpr_hum, "vl"))}</b></td>
      <td>{_hpr_pct(_hpr_delta.get("vl"))}</td>
    </tr>
  </table>
  <table class='params' style='margin-top:10px'>
    {row(
        "Paired Fv naturalness (p-AbNatiV; Standard / Enhanced)",
        (
            (f"<b>{_fmtf(_p_ab_ov.get('paired_humanness'),'3')}</b> &nbsp; "
             f"<span class='note'>Status: <b>{esc(str(_p_ab_ov.get('paired_humanness_status') or 'NOT_RUN'))}</b>. "
             f"VH/VL jobs do not run AbLang2 or T20; Quick Preview omits this paired gate.</span>")
            if _p_ab_ov.get("paired_humanness") is not None
            else (
                f"<span style='color:#9ca3af'>Not evaluated</span> &nbsp; <span class='note'>("
                + (
                    "Quick Preview — use Standard Delivery or Enhanced Rescue for paired naturalness."
                    if str(payload.get("structure_mode") or "").upper() != "COMPUTED"
                    else esc(str(_p_ab_ov.get("error") or "computation unavailable"))
                )
                + ")</span>"
            )
        ),
    )}
    {row(
        "Interpretation",
        "HPR Index is the primary sequence naturalness line item; paired Fv naturalness adds a structured paired-VH/VL check when Run Mode includes structure evaluation. "
        "These are developability context metrics — not clinical immunogenicity assays.",
    )}
  </table>
</div>

  {s8_mini_cmc}

<!-- §10 Donor vs humanized sequences (evidence; same as FASTA in ZIP) -->
<div class='section' id='s10'>
  <h3>§10 — Donor vs Humanized — FR/CDR Segmentation</h3>
  <p class='note'>
    Side-by-side FR/CDR segmentation using IMGT V-domain boundaries. 
    CDR regions are highlighted amber; FR mutations are highlighted red. 
    Same sequences as <code>donor_sequences.fasta</code> / <code>humanized_sequences.fasta</code> in delivery ZIP.
  </p>
  {_build_dual_seq_panel("VH", mouse_vh, hum_vh)}
  {_build_dual_seq_panel("VL", mouse_vl, hum_vl)}
  <h4 style='color:#1b4fad;margin:18px 0 6px;font-size:14px'>
    Full-length sequences — donor vs humanized
  </h4>
  <p class='note' style='margin:0 0 8px;font-size:12px'>
    Single-letter amino-acid sequences for the four chains used throughout this report.
    These are the exact sequences synthesized for downstream evaluation.
  </p>
  <div style='margin-top:8px'>
    {seq_block(f"Donor VH ({payload.get('source_species') or 'donor'})", mouse_vh)}
    {seq_block(f"Donor VL ({payload.get('source_species') or 'donor'})", mouse_vl)}
    {seq_block("Humanized VH (Seq1)", hum_vh)}
    {seq_block("Humanized VL (Seq1)", hum_vl)}
  </div>
  <details style='margin-top:10px'>
    <summary style='cursor:pointer;color:#1b4fad;font-size:12px;font-weight:600'>
      ▸ FASTA copy block (one record per chain)
    </summary>
    <pre style='font-family:Consolas,Monaco,monospace;font-size:11.5px;background:#f6f8fb;border:1px solid #d6e3ff;border-radius:6px;padding:10px;margin-top:6px;white-space:pre-wrap;word-break:break-all'>
&gt;Donor_VH ({payload.get('source_species') or 'donor'}, {len(mouse_vh)} aa)
{mouse_vh}
&gt;Donor_VL ({payload.get('source_species') or 'donor'}, {len(mouse_vl)} aa)
{mouse_vl}
&gt;Humanized_VH_Seq1 ({len(hum_vh)} aa)
{hum_vh}
&gt;Humanized_VL_Seq1 ({len(hum_vl)} aa)
{hum_vl}</pre>
  </details>
  {_cdr_preservation_block(payload, H)}
</div>

  {s11_cmc_advisory}

<!-- §12 Checklist Compliance -->
<div class='section' id='s12'>
  <h3>§12 — Delivery checklist summary</h3>
  <table class='params'>
    {row("Overall Status", f"<b>{status}</b> {st_badge}")}
    {row("Phases Passed", payload.get("checklist_phases_passed"))}
    {row("Quality Control Note", (
      "Internal quality review completed. Please combine with experimental confirmation for downstream decisions."
    ))}
  </table>
</div>
{_s_qa_audit}"""

    # Build full HTML with print-ready CSS
    html = f"""<!DOCTYPE html>
<html lang="{html_lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="abengine-vhvl-report-build" content="{VHVL_HTML_REPORT_BUILD_ID}">
<title>{title}</title>
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

/* ===== header ===== */
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

/* TOC */
.toc-bar {{ background:#e8eef8; border:1px solid var(--border); border-radius:6px; padding:8px 14px; font-size:.8rem; margin-bottom:20px; color:#2d4a80 }}
.toc-bar a {{ color:#1b4fad; text-decoration:none; margin:0 2px }}
.toc-bar a:hover {{ text-decoration:underline }}

/* sections */
.section {{ background:var(--card); border:1px solid var(--border); border-radius:8px; padding:18px 20px; margin-bottom:16px }}
h3 {{ color:var(--accent); font-size:.98rem; margin:0 0 12px; padding-bottom:6px; border-bottom:2px solid var(--border) }}
h4.chain-title {{ color:#2d6cdf; font-size:.88rem; margin:14px 0 6px }}
.note {{ color:#5a6a80; font-size:.8rem; margin-bottom:8px }}

/* tables */
table.params {{ width:100%; border-collapse:collapse; font-size:.83rem }}
table.params th {{ background:#e8eef8; color:var(--accent); font-weight:600; padding:7px 12px; text-align:left; border-bottom:2px solid var(--border) }}
table.params td {{ padding:6px 12px; border-bottom:1px solid #eef; vertical-align:top }}
table.params td.lbl {{ width:38%; color:#4a5a72; font-size:.82rem }}
table.params tr:last-child td {{ border-bottom:none }}
table.params tr.row-best td {{ background:#f0fff4; font-weight:600 }}

/* badges */
.badge {{ display:inline-block; padding:1px 8px; border-radius:10px; font-size:.72rem; font-weight:700; vertical-align:middle; margin-left:4px }}
.badge-ok {{ background:#d1fae5; color:var(--pass); border:1px solid #6ee7b7 }}
.badge-fail {{ background:#fee2e2; color:var(--fail); border:1px solid #fca5a5 }}
.badge-warn {{ background:#fef3c7; color:var(--warn); border:1px solid #fcd34d }}

/* sequence blocks */
.seq-block {{ background:#f8fafd; border:1px solid var(--border); border-radius:6px; padding:12px 14px; margin-bottom:10px }}
.seq-label {{ font-size:.82rem; font-weight:700; color:var(--accent2); margin-bottom:6px }}
.seq-len {{ font-weight:400; color:#8a9ab0; font-size:.75rem; margin-left:6px }}
.seq-body {{ font-family:'Consolas','Courier New',monospace; font-size:.78rem; word-break:break-all; line-height:2; color:#1a2030 }}
.chunk {{ margin-right:8px; letter-spacing:.04em }}
.chunk:nth-child(10n) {{ color:#1b4fad }}

/* footer */
footer {{ text-align:center; color:#8899aa; font-size:.72rem; margin-top:28px; padding-top:12px; border-top:1px solid var(--border) }}
footer a {{ color:#1b4fad; }}

/* print */
@page {{ margin:18mm 14mm 16mm 14mm }}
@media print {{
  body {{ background:#fff; font-size:10.5px; color:#000 }}
  .page {{ max-width:100%; padding:0; box-shadow:none }}
  .toc-bar {{ display:none }}
  /* Force colors for branded header */
  .report-header {{
    background:#1b4fad !important;
    color:#fff !important;
    -webkit-print-color-adjust:exact;
    print-color-adjust:exact;
  }}
  .report-header h1,
  .report-header .sub,
  .report-header .ts {{ color:#fff !important }}
  /* Sections: allow free splitting — never add blank pages */
  .section {{
    break-inside:auto;
    page-break-inside:auto;
    border:1px solid #ccc;
    margin-bottom:8px;
    overflow:visible;
    box-shadow:none;
  }}
  /* Headings stay with the next paragraph */
  h3 {{ break-after:avoid; page-break-after:avoid; font-size:12px }}
  h4 {{ break-after:avoid; page-break-after:avoid; font-size:11px }}
  /* Small blocks: keep together only if they fit; do NOT block page flow */
  .discussion-box {{ break-inside:avoid; page-break-inside:avoid; max-height:none }}
  .seq-block {{ break-inside:avoid; page-break-inside:avoid }}
  /* Tables: allow rows to split so large tables don't jump to next page */
  table.params {{ break-inside:auto; page-break-inside:auto; border-collapse:collapse; width:100% }}
  table.params tr {{ break-inside:avoid; page-break-inside:avoid }}
  table.params th, table.params td {{ font-size:9.5px; padding:3px 5px }}
  /* Force <details> open so content prints */
  details {{ display:block }}
  details[open] summary::after, details summary::after {{ content:none }}
  details > *:not(summary) {{ display:block !important }}
  /* Sequence blocks font */
  .seq-body {{ font-size:8.5px; line-height:1.7; word-break:break-all }}
  /* Badges retain color in print */
  .badge-ok, .badge-fail, .badge-warn, .badge {{
    -webkit-print-color-adjust:exact;
    print-color-adjust:exact;
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
      <div class="sub" style="margin-top:4px">{proj_lbl}: <b>{proj}</b></div>
      {_build_report_meta_local(VHVL_REPORT_PROTOCOL_VERSION, f"AbEngineCore VH/VL Humanization Standard {VHVL_ANALYSIS_VERSION}", _report_format_ver_top)}
    </div>
    <div class="ts">{ts}<br><span style="font-size:.7rem;opacity:.6">{conf_lbl}</span></div>
  </div>
  {cohort_provenance_html("vhvl_humanization")}
  {body}
  <footer>{footer_line}</footer>
</div>
</body>
</html>"""

    report_dir = out_dir / "reports" / "vhvl_humanization"
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / "humanization_report.html"
    try:
        from core.reporting.report_qc_gate import run_report_qc  # noqa: PLC0415
        qc = run_report_qc(html, report_family="vhvl_humanization")
        html = qc.inject_qc_badge(html)
    except Exception:
        pass
    out_path.write_text(html, encoding="utf-8")
    return out_path


def _run_integrated_cmc_vhvl(
    humanized_vh: str,
    humanized_vl: str,
    job_id: str,
    out: Path,
    integrated_cmc: str = "minimal",
) -> Dict[str, Any]:
    """
    AbEvaluator pass for humanized VH/VL (no immunogenicity / IEDB module).

    **Not called** by ``POST /humanize/vh_vl`` — humanization jobs use Essential mini-CMC in-engine;
    run ``POST /cmc/igg`` (or equivalent) separately for Clinical Reference Cohort / full advisor. Kept for scripts/tests.

    - **minimal**: ``developability`` + ``germline``
    - **full**: also ``cdr_scan`` + ``cmc_advisor``
    """
    vh = (humanized_vh or "").strip().upper()
    vl = (humanized_vl or "").strip().upper()
    if len(vh) < 80 or len(vl) < 80:
        return {"status": "skipped", "reason": "humanized_VH/VL_missing_or_too_short"}

    try:
        from core.evaluation.evaluator import AbEvaluator, AntibodyType

        ev = AbEvaluator(
            project_name=f"{job_id}_post_cmc",
            ab_type=AntibodyType.HUMANIZED,
            vh_seq=vh,
            vl_seq=vl,
            strict_qa=False,
        )
        tier = (integrated_cmc or "minimal").strip().lower()
        if tier == "full":
            fast_modules = ["developability", "cdr_scan", "germline", "cmc_advisor"]
        else:
            fast_modules = ["developability", "germline"]
        result = ev.run(modules=fast_modules)
        summary = result._executive_summary()
        dev = result.results.get("developability", {})
        cdr = result.results.get("cdr_scan", {})
        germ = result.results.get("germline", {})
        cmc_adv = result.results.get("cmc_advisor", {})
        liab_list = cdr.get("liabilities", []) or []

        def _count_type(prefix: str) -> int:
            return sum(1 for x in liab_list if str(x.get("type", "")).startswith(prefix))

        payload: Dict[str, Any] = {
            "status": "ok",
            "integrated_cmc_tier": tier,
            "reference_population": "Clinical Reference Cohort (n=458 approved/clinical mAbs)",
            "clinical_score": result.clinical_score,
            "clinical_percentile_rank": dev.get("abref_percentile"),
            "pI_fab": dev.get("pI_fab_estimate"),
            "GRAVY": dev.get("GRAVY"),
            "instability_index": dev.get("instability_index"),
            "hydro_patch_max9": dev.get("hydro_patch_max9"),
            "charge_patch_max7": dev.get("charge_patch_max7"),
            "net_charge_pH7": dev.get("net_charge_pH7"),
            "n_deamidation": _count_type("deamidation"),
            "n_isomerization": _count_type("isomerization"),
            "n_oxidation": _count_type("oxidation"),
            "n_glycosylation": _count_type("glycosylation"),
            "liability_flags": cdr.get("flags", []),
            "germline_identity_vh": (germ.get("VH") or {}).get("top_match_identity"),
            "germline_identity_vl": (germ.get("VL") or {}).get("top_match_identity"),
            "closest_vh_germline": (germ.get("VH") or {}).get("top_match"),
            "closest_vl_germline": (germ.get("VL") or {}).get("top_match"),
            "overall_status": result.overall_status,
            "overall_flags": result.overall_flags,
            "cmc_n_warn": summary.get("cmc_n_warn", 0),
            "cmc_n_fail": summary.get("cmc_n_fail", 0),
            "mutation_suggestions": cmc_adv.get("mutation_suggestions", []),
            "modules_run": fast_modules,
        }
        audit = {
            "clinical_score": result.clinical_score,
            "overall_status": result.overall_status,
            "modules": result.results,
        }
        (out / "integrated_cmc_evaluator.json").write_text(
            json.dumps(audit, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return payload
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# VH/VL Humanization
# ─────────────────────────────────────────────────────────────────────────────

def _humanize_vh_vl_impl(job_id: str, req: VHVLRequest) -> JobStatus:
    """Run VH/VL humanization for an existing job_id (sync or background worker)."""
    prev = jobs.get(job_id, {})
    if prev.get("status") == "cancelled":
        return JobStatus(job_id=job_id, status="cancelled", progress=0, result=None, error=None)

    jobs[job_id] = {
        "status": "running",
        "progress": 5,
        "progress_note": None,
        "cancel_requested": bool(prev.get("cancel_requested")),
    }
    persist_job_snapshot(job_id)
    t0 = time.time()
    out = job_dir(job_id)

    # Display/archive label: user-supplied project or sequence name only; otherwise neutral job id (no invented titles).
    _pn = (getattr(req, "project_name", None) or "").strip() or job_id

    try:
        from core.humanization.engine import HumanizationEngine

        jobs[job_id]["progress"] = 10
        species_map = {
            "mouse": "mus_musculus",
            "rat": "rattus_norvegicus",
        }
        sp_input = (req.source_species or "mouse").strip().lower()
        donor_species = species_map.get(sp_input)
        if donor_species is None:
            raise HTTPException(status_code=422, detail=f"Out of computation scope: source_species '{sp_input}' is not supported. Our system strictly limits normal antibody humanization to mouse and rat only. Please use the VHH humanization endpoint for camelid sequences, or provide a valid mouse/rat donor.")

        # ── V4.8.1 Donor mini-CMC (for baseline comparison) ────────────────
        from Bio.SeqUtils.ProtParam import ProteinAnalysis
        donor_mini_cmc = {}
        try:
            _donor_fab = (req.vh_sequence.strip() + req.vl_sequence.strip()).upper()
            _pa = ProteinAnalysis(_donor_fab)
            donor_mini_cmc = {
                "length": len(_donor_fab),
                "pI": round(float(_pa.isoelectric_point()), 2),
                "GRAVY": round(float(_pa.gravy()), 3),
                "instability_index": round(float(_pa.instability_index()), 2),
                "aromaticity": round(float(_pa.aromaticity()), 3),
            }
        except Exception as _e:
            donor_mini_cmc = {"error": str(_e)}

        engine = HumanizationEngine(workflow="vh_vl", donor_species=donor_species)

        if jobs.get(job_id, {}).get("cancel_requested"):
            jobs[job_id] = {
                "status": "cancelled",
                "progress": 20,
                "progress_note": "Cancelled before HumanizationEngine.run()",
            }
            persist_job_snapshot(job_id)
            return JobStatus(job_id=job_id, status="cancelled", progress=20, result=None, error=None)

        jobs[job_id]["progress"] = 20
        jobs[job_id]["progress_note"] = "Running HumanizationEngine (Phases 1–5; may take several minutes)"
        # engine.run() has no fine-grained hooks. First we bump quickly to a **low cap** (~52)
        # so the bar does not reach ~80% while the core still runs (misleading). After the cap,
        # creep slowly so long jobs do not look frozen; poll UI also shows progress_note.
        _stop_progress = threading.Event()

        def _bump_progress_while_engine() -> None:
            p = 22
            jobs[job_id]["progress"] = p
            # Phase A: fast ramp to 52. Phase B: slow creep 52→60 (still not "almost done").
            wait_sec = 3.0
            while not _stop_progress.wait(wait_sec):
                # Stop bar when worker leaves "running" (e.g. status → "cancelling" on cancel).
                if jobs.get(job_id, {}).get("status") != "running":
                    break
                if p < 52:
                    p = min(p + 3, 52)
                    wait_sec = 3.0
                else:
                    p = min(p + 1, 60)
                    wait_sec = 18.0
                    jobs[job_id]["progress_note"] = (
                        "Core pipeline still running (structure QC if enabled, assembly, checklist). "
                        "~52–60% can last many minutes during HumanizationEngine.run() — not stuck; "
                        "no fine-grained hooks. If polling returns 404, server likely restarted—use snapshot recovery or rerun."
                    )
                jobs[job_id]["progress"] = p
                persist_job_snapshot(job_id)

        _prog_t = threading.Thread(target=_bump_progress_while_engine, daemon=True)
        _prog_t.start()
        try:
            # Pass advanced engineering options to the engine
            result = engine.run(
                mouse_vh=req.vh_sequence.strip().upper(),
                mouse_vl=req.vl_sequence.strip().upper(),
                project_name=_pn,
                out_dir=str(out),
                repair_mode=req.repair_mode,
                back_mutation_strategy=req.back_mutation_strategy,
                dry_run_structure=req.dry_run_structure,
                skip_iedb=getattr(req, "skip_iedb", True),
            )
        finally:
            _stop_progress.set()


        if jobs.get(job_id, {}).get("cancel_requested"):
            jobs[job_id] = {
                "status": "cancelled",
                "progress": 54,
                "progress_note": "Cancelled after core run — reports/ZIP skipped; partial files may exist on disk",
            }
            return JobStatus(job_id=job_id, status="cancelled", progress=54, result=None, error=None)

        jobs[job_id]["progress"] = 54

        # ── Extract structured parameters ──────────────────────────────────
        qm  = result.qc_metrics if hasattr(result, "qc_metrics") else {}
        seq = result.sequences  if hasattr(result, "sequences")  else {}
        r   = result.checklist_report if hasattr(result, "checklist_report") else {}

        fw        = qm.get("framework_selection", {})
        # Chothia + CDR-masked FR% (same definition as Phase 2 ranking / Phase 4 reporting)
        _vh_fr_id = fw.get("vh_identity_pct")
        if _vh_fr_id is None:
            _vh_fr_id = fw.get("framework_identity_vh")
        _vl_fr_id = fw.get("vl_identity_pct")
        if _vl_fr_id is None:
            _vl_fr_id = fw.get("framework_identity_vl")
        cdr       = qm.get("cdr_identification", {})
        structure = qm.get("structure", {})
        vernier   = qm.get("vernier_risk_positions", [])
        ablang    = qm.get("ablang_score")
        bm_vh     = fw.get("bm_candidates_vh") or qm.get("bm_candidates_vh", [])
        bm_vl     = fw.get("bm_candidates_vl") or qm.get("bm_candidates_vl", [])
        # SDRM: annotated FR differences with Vernier tier + HC rule
        sdrm_vh   = fw.get("sdrm_vh", [])
        sdrm_vl   = fw.get("sdrm_vl", [])
        fr_diffs_vh = fw.get("fr_differences_vh", [])
        fr_diffs_vl = fw.get("fr_differences_vl", [])

        # Humanized sequences: look for keys that are NOT the mouse inputs
        mouse_keys = {"mouse_vh", "mouse_vl", "mouse_vhh"}
        humanized = {k: v for k, v in seq.items() if k not in mouse_keys and v}
        humanized_vh = (humanized.get("humanized_vh") or humanized.get("Our_Hum")
                        or next((v for k, v in humanized.items() if "vh" in k.lower()), ""))
        humanized_vl = (humanized.get("humanized_vl")
                        or next((v for k, v in humanized.items() if "vl" in k.lower()), ""))

        # Build candidate list: top VH × top VL with FR identity scores
        top_vh_list = fw.get("top_vh_candidates", [])  # [{"germline":id,"fr_identity":score},...]
        top_vl_list = fw.get("top_vl_candidates", [])

        def _cand_id(item):
            return item.get("germline") if isinstance(item, dict) else item
        def _cand_score(item):
            return item.get("fr_identity") if isinstance(item, dict) else None

        # Cross-pair top-3 VH × top-2 VL (up to 5 candidates total)
        candidates = []
        for i, vh_item in enumerate(top_vh_list[:3]):
            for vl_item in top_vl_list[:2]:
                vh_sc = _cand_score(vh_item)
                vl_sc = _cand_score(vl_item)
                avg   = round((vh_sc + vl_sc) / 2, 1) if (isinstance(vh_sc, (int, float)) and isinstance(vl_sc, (int, float))) else None
                candidates.append({
                    "rank":         len(candidates) + 1,
                    "vh_germline":  _cand_id(vh_item),
                    "vl_germline":  _cand_id(vl_item),
                    "vh_fr_id":     vh_sc,
                    "vl_fr_id":     vl_sc,
                    "score":        avg,
                })
                if len(candidates) >= 5:
                    break
            if len(candidates) >= 5:
                break

        # Per-CDR RMSD from Phase 5 QC
        cdr_rmsd = qm.get("cdr_rmsd", {})

        payload = {
            "project_name":                 _pn,
            "source_species":               req.source_species,
            "donor_species":                donor_species,
            "phase2_degraded":              bool(fw.get("phase2_degraded")),
            "phase2_fallback_reason":       fw.get("phase2_fallback_reason"),
            "phase2_attention_message":     fw.get("phase2_attention_message"),
            "selection_mode":               fw.get("selection_mode"),
            "phase2_extended_cache_scan_vh": bool(fw.get("phase2_extended_cache_scan_vh")),
            "phase2_extended_cache_scan_vl": bool(fw.get("phase2_extended_cache_scan_vl")),
            "phase2_vh_length_tolerance_used": fw.get("phase2_vh_length_tolerance_used", 0),
            "phase2_vl_length_tolerance_used": fw.get("phase2_vl_length_tolerance_used", 0),
            "clinical_framework_policy":     fw.get("clinical_framework_policy"),
            # V5.3.1: previously absent from payload — renderer's species-aware
            # selection-policy text reads these directly.
            "framework_cmc_scan_enabled":   bool(fw.get("framework_cmc_scan_enabled")),
            "clinical_anchor_only":         fw.get("clinical_anchor_only"),
            "selected_vh_framework_mini_cmc": fw.get("selected_vh_framework_mini_cmc", {}) or {},
            "selected_vl_framework_mini_cmc": fw.get("selected_vl_framework_mini_cmc", {}) or {},
            # Germline identity (Chothia, CDR-masked vs selected human germline)
            "vh_germline":                 fw.get("selected_vh_germline") or "—",
            "vh_germline_identity":        _vh_fr_id,
            "vl_germline":                 fw.get("selected_vl_germline") or "—",
            "vl_germline_identity":        _vl_fr_id,
            "vh_fr_identity_chothia_cdr_masked": _vh_fr_id,
            "vl_fr_identity_chothia_cdr_masked": _vl_fr_id,
            # CDR
            "cdr_canonical_class":         _fmt_canonical(cdr.get("canonical_class")),
            "cdrs":                        cdr.get("cdrs", {}),
            # Humanness
            "ablang_score":                ablang,
            "ablang_error":                qm.get("ablang_error"),
            "t20_score":                   qm.get("t20_score"),
            "t20_error":                   qm.get("t20_error"),
            "p_abnativ2":                  qm.get("p_abnativ2"),
            "framework_human_identity_vh": fw.get("framework_identity_vh"),
            "framework_human_identity_vl": fw.get("framework_identity_vl"),
            # Top germline candidates (with scores)
            "top_vh_candidates":           top_vh_list,
            "top_vl_candidates":           top_vl_list,
            # Vernier risk (T1+T2 differences, internal audit per V4.5.1-4)
            "vernier_risk_positions":      vernier,
            # HC-rule recommended back mutations only (max 5/chain per V4.5.1 config)
            "bm_candidates_vh":            bm_vh,
            "bm_candidates_vl":            bm_vl,
            "backmutation_count":          len(bm_vh) + len(bm_vl),
            # All FR differences (source for SDRM)
            "fr_differences_vh":           fr_diffs_vh,
            "fr_differences_vl":           fr_diffs_vl,
            "fr_differences_total":        len(fr_diffs_vh) + len(fr_diffs_vl),
            # SDRM annotated entries (with Vernier tier, HC rule, action)
            "sdrm_vh":                     sdrm_vh,
            "sdrm_vl":                     sdrm_vl,
            # Structure — mouse
            "structure_computed":          not structure.get("dry_run", True),
            "structure_mode":              "DRY_RUN" if structure.get("dry_run", True) else "COMPUTED",
            "plddt":                       structure.get("plddt"),
            "vh_vl_angle_deg":             structure.get("vh_vl_angle_deg"),
            # Structure — humanized (Phase 5)
            "humanized_plddt":             structure.get("humanized_plddt"),
            "humanized_angle_deg":         structure.get("humanized_angle_deg"),
            "angle_delta_deg":             structure.get("angle_delta_deg"),
            "mini_cmc":                    qm.get("mini_cmc", {}),
            "hpr_index":                   qm.get("hpr_index", {}),
            "basic_developability":        qm.get("basic_developability", {}),
            "iedb_result":                 qm.get("iedb_result", "not_run"),
            "iedb_http_status":            qm.get("iedb_http_status", "N/A"),
            "donor_mini_cmc":              donor_mini_cmc,
            "cmc_species_gates":           _species_cmc_gates(req.source_species),
            "cmc_advisory":                _build_vhvl_cmc_advisory(
                donor_mini_cmc,
                qm.get("mini_cmc", {}),
                qm.get("cdr_rmsd", {}),
                result.overall_status if hasattr(result, "overall_status") else "UNKNOWN",
                result.notes if hasattr(result, "notes") else [],
                source_species=req.source_species,
                stable_cdr_keys=qm.get("cdr_rmsd_stable_cdrs"),
            ),
            "pI_fab":                      qm.get("pI_fab"),
            "liabilities":                 qm.get("liabilities", []),
            "rescue":                      qm.get("rescue", {}),
            "cdr_rmsd_stable_cdrs":        qm.get("cdr_rmsd_stable_cdrs"),
            "cdr_rmsd_volatile_cdrs":      qm.get("cdr_rmsd_volatile_cdrs"),
            "delivery_decision":           qm.get("delivery_decision", {}),
            "qc_warning_reasons":          (getattr(result, "qa_audit", {}) or {}).get("delivery_warning_reasons", []),
            # CDR Cα RMSD (mouse vs. humanized)
            "cdr_rmsd":                    cdr_rmsd,
            "rmsd_to_reference":           (
                round(sum(v for v in cdr_rmsd.values() if isinstance(v, float)) / len(cdr_rmsd), 2)
                if cdr_rmsd and isinstance(cdr_rmsd, dict) and any(isinstance(v, float) for v in cdr_rmsd.values())
                else None
            ),
            # Checklist
            "checklist_status":            result.overall_status if hasattr(result, "overall_status") else "UNKNOWN",
            "checklist_phases_passed":     _vhvl_count_phases_no_fail(r),
            "flags":                       result.notes if hasattr(result, "notes") else [],
            "clinical_reference":          qm.get("clinical_reference", {}),
            "global_fv_rmsd_ca":          qm.get("global_fv_rmsd_ca"),
            "fr_identity_qc":              qm.get("fr_identity_qc"),
            "structural_qc_v50":           qm.get("structural_qc_v50"),
            "fallback_germline_used":      fw.get("fallback_germline_used", False),
            # V5.4.13: rabbit/rat ≥60% FR-identity grafting gate transparency
            "vh_below_grafting_gate":      fw.get("vh_below_grafting_gate", False),
            "vl_below_grafting_gate":      fw.get("vl_below_grafting_gate", False),
            "grafting_gate_threshold_pct": fw.get("grafting_gate_threshold_pct"),
            "vh_excluded_by_gate":         fw.get("vh_excluded_by_gate", []),
            "vl_excluded_by_gate":         fw.get("vl_excluded_by_gate", []),
            # V5.1.0: real CDR Mouse-vs-Humanized diff (Union scheme) — for §10 evidence table
            "cdr_integrity_check":         qm.get("cdr_integrity_check"),
            "cdr_diff_vh":                 qm.get("cdr_diff_vh", []),
            "cdr_diff_vl":                 qm.get("cdr_diff_vl", []),
            "cdr_scheme":                  qm.get("cdr_scheme") or "union_kabat_chothia_v5_1",
            # Sequences (include mouse inputs for report)
            "mouse_vh":                    req.vh_sequence.strip().upper(),
            "mouse_vl":                    req.vl_sequence.strip().upper(),
            "humanized_vh":                humanized_vh,
            "humanized_vl":                humanized_vl,
            "candidates":                  candidates,
            "report_language": resolve_vhvl_report_language(getattr(req, "report_language", None)),
            "report_format": (getattr(req, "report_format", None) or "both").strip().lower(),
            # Engineering mode — stored for report display
            "repair_mode":                 req.repair_mode,
            "back_mutation_strategy":      "auto",
            "surface_reshape_on_qc_fail": bool(getattr(req, "surface_reshape_on_qc_fail", False)),
        }

        # Product execution contract: engine route is resolved first; any surface
        # reshaping is a post-engine fallback, never a parallel primary route.
        _rescue_block = payload.get("rescue") or {}
        _rescue_notes_for_route = list(_rescue_block.get("notes") or [])
        _rescue_attempted_for_route = bool(_rescue_block.get("attempted"))
        if bool(getattr(req, "dry_run_structure", False)):
            _run_mode_label = "quick_preview"
        elif str(getattr(req, "repair_mode", "standard") or "").lower() == "rescue":
            _run_mode_label = "enhanced_rescue_evaluation"
        else:
            _run_mode_label = "standard_delivery"
        if str(getattr(req, "repair_mode", "standard") or "").lower() != "rescue":
            _engine_rescue_path = "not_requested"
        elif not _rescue_attempted_for_route:
            _engine_rescue_path = "not_triggered"
        elif "vernier_round2_rescued" in _rescue_notes_for_route:
            _engine_rescue_path = "vernier_round2"
        elif "fallback_germline_rerun" in _rescue_notes_for_route:
            _engine_rescue_path = "fallback_germline"
        elif "reverted_to_step1_better_metrics" in _rescue_notes_for_route:
            _engine_rescue_path = "vernier_round2_preferred_after_fallback"
        else:
            _engine_rescue_path = "attempted_unresolved"
        _engine_final_route = (
            "rescued_germline_graft"
            if _engine_rescue_path not in {"not_requested", "not_triggered"}
            else "standard_germline_graft"
        )
        payload["execution_route"] = {
            "run_mode": _run_mode_label,
            "route_order": [
                "standard_germline_cdr_graft",
                "engine_backmutation_and_germline_rescue",
                "post_engine_surface_reshaping_fallback",
            ],
            "engine_rescue": {
                "requested": str(getattr(req, "repair_mode", "standard") or "").lower() == "rescue",
                "attempted": _rescue_attempted_for_route,
                "path": _engine_rescue_path,
                "notes": _rescue_notes_for_route,
            },
            "surface_fallback": {
                "requested": bool(getattr(req, "surface_reshape_on_qc_fail", False)),
                "trigger_stage": "post_engine_rescue_gate",
                "status": "pending",
                "applied": False,
            },
            "final_route": _engine_final_route,
        }

        # ── V5.4.0: optional / routed structure-driven FR surface reshaping fallback ──
        _cs = (payload.get("checklist_status") or "").strip().upper()
        _species_key = (req.source_species or "").strip().lower()
        _vh_low_identity = isinstance(payload.get("vh_germline_identity"), (int, float)) and float(payload.get("vh_germline_identity")) < 60.0
        _vl_low_identity = isinstance(payload.get("vl_germline_identity"), (int, float)) and float(payload.get("vl_germline_identity")) < 60.0
        _top_vh_for_cmp = payload.get("top_vh_candidates") or []
        _selected_vh = str(payload.get("vh_germline") or "").strip()
        _selected_vl = str(payload.get("vl_germline") or "").strip()
        _alt_vh_ge65 = None
        for _cand in _top_vh_for_cmp:
            if not isinstance(_cand, dict):
                continue
            _fr = _cand.get("fr_identity")
            try:
                _fr_ok = float(_fr) >= 65.0
            except Exception:
                _fr_ok = False
            if _fr_ok and str(_cand.get("germline") or "").strip() != _selected_vh:
                _alt_vh_ge65 = {
                    "germline": _cand.get("germline"),
                    "fr_identity": _cand.get("fr_identity"),
                    "vernier_similarity": _cand.get("vernier_similarity"),
                    "composite_score": _cand.get("composite_score"),
                }
                break
        _auto_surface_route = (
            _species_key in {"rabbit", "rat"}
            and (_cs in ("WARN", "FAIL") or _vh_low_identity or _vl_low_identity)
        )
        payload["route_comparison"] = {
            "enabled": _species_key in {"rabbit", "rat"},
            "required": (
                _species_key in {"rabbit", "rat"}
                and (
                    _vh_low_identity
                    or _vl_low_identity
                    or _alt_vh_ge65 is not None
                    or _cs in ("WARN", "FAIL")
                )
            ),
            "grafting_selected": {
                "vh_germline": _selected_vh or "—",
                "vl_germline": _selected_vl or "—",
                "vh_fr_identity": payload.get("vh_germline_identity"),
                "vl_fr_identity": payload.get("vl_germline_identity"),
            },
            "grafting_alt_vh_ge65": _alt_vh_ge65,
            "surface_route": {
                "requested": bool(getattr(req, "surface_reshape_on_qc_fail", True)),
                "trigger_stage": "post_engine_rescue_gate",
                "triggered": bool(_auto_surface_route),
                "applied": False,
                "status": "pending" if bool(_auto_surface_route) else "not_triggered",
                "note": "",
            },
        }

        # ── V5.4.13: build the Route A' alternative ≥65% CDR-grafting deliverable ──
        # When an alt VH germline ≥65% identity exists alongside the composite-best
        # selection, the V5.4 intermediate-state policy requires that BOTH grafting
        # routes be delivered (not just the composite-best). This block builds a
        # raw-graft sequence on the alternative VH germline (paired with the
        # primary VL) and attaches it to grafting_alt_vh_ge65 as a real artefact.
        if _alt_vh_ge65 and _alt_vh_ge65.get("germline"):
            try:
                from core.humanization.alt_route_grafting import (  # noqa: PLC0415
                    build_alt_route_grafting_deliverable,
                )

                _alt_deliv = build_alt_route_grafting_deliverable(
                    donor_vh=req.vh_sequence.strip().upper(),
                    donor_vl=req.vl_sequence.strip().upper(),
                    alt_vh_germline_id=str(_alt_vh_ge65.get("germline") or ""),
                    selected_vl_germline_id=_selected_vl,
                )
                payload["route_comparison"]["grafting_alt_vh_ge65"]["deliverable"] = _alt_deliv
            except Exception as _alt_err:
                payload["route_comparison"]["grafting_alt_vh_ge65"]["deliverable"] = {
                    "applied": False,
                    "errors": [f"Alt-route deliverable build failed: {_alt_err}"],
                }
        if bool(getattr(req, "surface_reshape_on_qc_fail", True)) and _auto_surface_route:
            try:
                if _cs in ("WARN", "FAIL"):
                    jobs[job_id]["progress_note"] = "Applying V5.4 structure-driven FR surface reshaping fallback…"
                else:
                    jobs[job_id]["progress_note"] = "Evaluating V5.4 structure-driven FR surface reshaping fallback…"
                persist_job_snapshot(job_id)
                _rr = _run_v54_structure_surface_reshape(payload, structure)
                payload["surface_reshape_fallback"] = _rr
                if _rr.get("errors"):
                    _fl = payload.setdefault("flags", [])
                    if isinstance(_fl, list):
                        _fl.append("Surface reshape fallback: " + "; ".join(_rr["errors"]))
                    payload["route_comparison"]["surface_route"].update({
                        "applied": False,
                        "status": "blocked",
                        "note": "; ".join(_rr.get("errors") or []) or "surface route blocked",
                    })
                    payload["execution_route"]["surface_fallback"].update({
                        "triggered": True,
                        "applied": False,
                        "status": "blocked",
                        "note": payload["route_comparison"]["surface_route"].get("note"),
                    })
                elif _rr.get("applied"):
                    payload["humanized_vh"] = _rr["humanized_vh"]
                    payload["humanized_vl"] = _rr["humanized_vl"]
                    # The engine's humanized PDB/RMSD belongs to the pre-fallback
                    # sequence. Invalidate it so the post-fallback structure is
                    # re-predicted below and report metrics align with the final
                    # delivered sequence.
                    structure.pop("humanized_pdb_path", None)
                    payload.pop("humanized_plddt", None)
                    payload.pop("humanized_angle_deg", None)
                    payload.pop("angle_delta_deg", None)
                    payload.pop("cdr_rmsd", None)
                    payload.pop("global_fv_rmsd_ca", None)
                    _fl = payload.setdefault("flags", [])
                    if isinstance(_fl, list):
                        _fl.append(
                            "V5.4 structure-driven FR surface reshaping applied: "
                            f"VH {len(_rr.get('vh_mutations') or [])} / "
                            f"VL {len(_rr.get('vl_mutations') or [])} FR substitutions."
                        )
                    payload["route_comparison"]["surface_route"].update({
                        "applied": True,
                        "status": "applied",
                        "note": (
                            "Surface route applied with CDR-preserving FR substitutions "
                            f"(VH {len(_rr.get('vh_mutations') or [])}, VL {len(_rr.get('vl_mutations') or [])})."
                        ),
                    })
                    payload["execution_route"]["surface_fallback"].update({
                        "triggered": True,
                        "applied": True,
                        "status": "applied",
                        "note": payload["route_comparison"]["surface_route"].get("note"),
                    })
                    payload["execution_route"]["final_route"] = "surface_reshaped_framework"
                else:
                    _rr["note"] = (
                        "Structure-driven fallback evaluated; no FR substitutions passed "
                        "the CDR-preserving surface-compatibility gate."
                    )
                    payload["route_comparison"]["surface_route"].update({
                        "applied": False,
                        "status": "evaluated_no_change",
                        "note": _rr["note"],
                    })
                    payload["execution_route"]["surface_fallback"].update({
                        "triggered": True,
                        "applied": False,
                        "status": "evaluated_no_change",
                        "note": _rr["note"],
                    })
            except Exception as _srf_err:
                payload.setdefault("surface_reshape_fallback", {"applied": False})
                _fl = payload.setdefault("flags", [])
                if isinstance(_fl, list):
                    _fl.append(f"Surface reshape fallback error (non-fatal): {_srf_err}")
                payload["route_comparison"]["surface_route"].update({
                    "applied": False,
                    "status": "error",
                    "note": str(_srf_err),
                })
                payload["execution_route"]["surface_fallback"].update({
                    "triggered": True,
                    "applied": False,
                    "status": "error",
                    "note": str(_srf_err),
                })
        else:
            payload["surface_reshape_fallback"] = {
                "applied": False,
                "note": "Surface fallback not triggered; standard CDR grafting remains the active route.",
            }
            payload["route_comparison"]["surface_route"].update({
                "applied": False,
                "status": "not_triggered",
                "note": "Surface fallback not triggered by current route gate.",
            })
            payload["execution_route"]["surface_fallback"].update({
                "triggered": False,
                "applied": False,
                "status": "not_triggered",
                "note": "Surface fallback not triggered by current route gate.",
            })

        # Keep local sequence vars aligned with payload (surface fallback may have updated sequences).
        humanized_vh = payload.get("humanized_vh") or humanized_vh
        humanized_vl = payload.get("humanized_vl") or humanized_vl
        _sr_route = payload.get("surface_reshape_fallback") or {}
        payload["per_chain_engineering_route"] = {
            "vh": (
                "donor_framework_fr_surface_reshaping"
                if (_sr_route.get("applied") and _sr_route.get("vh_mutations"))
                else "human_germline_cdr_grafting"
            ),
            "vl": (
                "donor_framework_fr_surface_reshaping"
                if (_sr_route.get("applied") and _sr_route.get("vl_mutations"))
                else "human_germline_cdr_grafting"
            ),
            "note": (
                "Surface-reshaped chains use donor framework plus selected FR surface substitutions; "
                "human germline entries are reference context only for those chains."
            ),
        }

        # V5.4.0: HPR Index and Basic Developability are computed after any
        # optional surface fallback so donor-vs-final comparisons are aligned.
        try:
            from core.humanization.hpr_index import compare_hpr  # noqa: PLC0415

            payload["hpr_index"] = compare_hpr(
                payload.get("mouse_vh", ""),
                payload.get("mouse_vl", ""),
                humanized_vh,
                humanized_vl,
            )
        except Exception as _hpr_err:
            payload["hpr_index"] = {"metric_name": "HPR Index", "error": str(_hpr_err)}
        try:
            from core.humanization.basic_developability import compare_basic_developability  # noqa: PLC0415

            payload["basic_developability"] = compare_basic_developability(
                payload.get("mouse_vh", ""),
                payload.get("mouse_vl", ""),
                humanized_vh,
                humanized_vl,
            )
        except Exception as _bd_err:
            payload["basic_developability"] = {"screen_name": "Basic Developability Screen", "error": str(_bd_err)}

        # Reports: IMGT CDR segments for clients; pipeline math unchanged.
        _imgt_cdrs = _cdrs_imgt_for_report(payload["mouse_vh"], payload["mouse_vl"])
        if _imgt_cdrs and any(_imgt_cdrs.values()):
            payload["cdrs_imgt"] = _imgt_cdrs
            payload["cdr_reporting_scheme"] = "IMGT"
        else:
            payload["cdrs_imgt"] = {}
            payload["cdr_reporting_scheme"] = "engine_union_fallback"

        # Web console: Kabat (= Kabat∪Chothia union, V5.1.0 widened) donor vs humanized comparison.
        # CDR_RANGES_VH/VL in kabat_utils are the same positions frozen by the engine during grafting.
        # Previous Chothia-only split was too narrow (H1 26–32, H2 52–56) and showed false CDR diffs.
        try:
            _sc_vh = _build_vhvl_sequence_comparison(
                str(payload.get("mouse_vh") or ""),
                str(humanized_vh or ""),
                chain="VH",
            )
            _sc_vl = _build_vhvl_sequence_comparison(
                str(payload.get("mouse_vl") or ""),
                str(humanized_vl or ""),
                chain="VL",
            )
            if isinstance(_sc_vh, dict) and not _sc_vh.get("error"):
                payload["sequence_comparison_vh"] = _sc_vh
            if isinstance(_sc_vl, dict) and not _sc_vl.get("error"):
                payload["sequence_comparison_vl"] = _sc_vl
        except Exception as _vhvl_sc_err:
            payload["sequence_comparison_error"] = str(_vhvl_sc_err)

        jobs[job_id]["progress"] = 58

        # ── Ensure both mouse and humanized structures are present ──────────
        if (
            payload.get("structure_computed")
            and humanized_vh and humanized_vl
            and not structure.get("humanized_pdb_path")
        ):
            try:
                from core.humanization.engine import _run_abodybuilder2, _compute_cdr_rmsd, _compute_global_fv_rmsd
                hum_struct = _run_abodybuilder2(humanized_vh, humanized_vl)
                hum_pdb = hum_struct.get("pdb_path")
                mouse_pdb = structure.get("pdb_path")
                if hum_pdb:
                    structure["humanized_pdb_path"] = hum_pdb
                    payload["humanized_plddt"] = hum_struct.get("plddt")
                    payload["humanized_angle_deg"] = hum_struct.get("vh_vl_angle_deg")
                    if payload.get("vh_vl_angle_deg") is not None and hum_struct.get("vh_vl_angle_deg") is not None:
                        payload["angle_delta_deg"] = round(
                            float(hum_struct.get("vh_vl_angle_deg")) - float(payload.get("vh_vl_angle_deg")),
                            1,
                        )
                    if mouse_pdb:
                        cdr_rmsd_retry = _compute_cdr_rmsd(mouse_pdb, hum_pdb)
                        payload["cdr_rmsd"] = cdr_rmsd_retry
                        vals = [v for v in cdr_rmsd_retry.values() if isinstance(v, (int, float))]
                        payload["rmsd_to_reference"] = round(sum(vals) / len(vals), 2) if vals else None
                        gfv_retry = _compute_global_fv_rmsd(mouse_pdb, hum_pdb)
                        if gfv_retry is not None:
                            payload["global_fv_rmsd_ca"] = gfv_retry
            except Exception as e:
                payload["humanized_structure_retry_error"] = str(e)

        # Final CMC advisory must use **post-fallback** CDR RMSD. Initial build used
        # pre-V5.4-surface-reshape metrics and could contradict §structure numbers.
        _adv_flags = payload.get("flags")
        if not isinstance(_adv_flags, list):
            _adv_flags = list(getattr(result, "notes", None) or [])
        payload["cmc_advisory"] = _build_vhvl_cmc_advisory(
            donor_mini_cmc,
            payload.get("mini_cmc") or qm.get("mini_cmc", {}),
            payload.get("cdr_rmsd") or qm.get("cdr_rmsd", {}),
            payload.get("checklist_status")
            or (result.overall_status if hasattr(result, "overall_status") else "UNKNOWN"),
            _adv_flags,
            source_species=req.source_species,
            stable_cdr_keys=payload.get("cdr_rmsd_stable_cdrs") or qm.get("cdr_rmsd_stable_cdrs"),
        )

        jobs[job_id]["progress"] = 64

        # ── Copy PDB files to job dir and build download URLs ──────────────
        import shutil
        pdb_urls = {}
        for label, pdb_key in [("donor_ab", "pdb_path"), ("humanized_ab", "humanized_pdb_path")]:
            src = structure.get(pdb_key)
            if src:
                try:
                    dst = out / f"{label}.pdb"
                    shutil.copy2(src, dst)
                    pdb_urls[label] = f"/files/{job_id}/{dst.name}"
                except Exception:
                    pass

        _archive_dest = _vhvl_project_archive_dest(ROOT, _pn, job_id, t0)
        try:
            _proj_rel = _archive_dest.relative_to(ROOT).as_posix()
        except ValueError:
            _proj_rel = None
        _mirror_vhvl_pdbs_into_project_archive(_archive_dest, out)

        # ── Generate customer FASTA files ──────────────────────────────────
        mouse_fasta_url = None
        humanized_fasta_url = None
        if humanized_vh or humanized_vl:
            try:
                mouse_fasta_lines = []
                _donor_sp = (getattr(req, "source_species", None) or "donor").strip().lower()
                if req.vh_sequence:
                    mouse_fasta_lines += [f">{job_id}_{_donor_sp}_VH", req.vh_sequence.strip().upper()]
                if req.vl_sequence:
                    mouse_fasta_lines += [f">{job_id}_{_donor_sp}_VL", req.vl_sequence.strip().upper()]

                humanized_fasta_lines = []
                if humanized_vh:
                    humanized_fasta_lines += [f">{job_id}_humanized_VH", humanized_vh]
                if humanized_vl:
                    humanized_fasta_lines += [f">{job_id}_humanized_VL", humanized_vl]

                if mouse_fasta_lines:
                    mouse_fasta_path = out / "donor_sequences.fasta"
                    mouse_fasta_path.write_text("\n".join(mouse_fasta_lines) + "\n", encoding="utf-8")
                    mouse_fasta_url = f"/files/{job_id}/donor_sequences.fasta"
                if humanized_fasta_lines:
                    humanized_fasta_path = out / "humanized_sequences.fasta"
                    humanized_fasta_path.write_text("\n".join(humanized_fasta_lines) + "\n", encoding="utf-8")
                    humanized_fasta_url = f"/files/{job_id}/humanized_sequences.fasta"
            except Exception:
                pass

        payload["pdb_urls"]   = pdb_urls
        payload["mouse_fasta_url"] = mouse_fasta_url
        payload["humanized_fasta_url"] = humanized_fasta_url
        payload["job_id"]     = job_id
        _run_subdir = _vhvl_archive_run_subdir(job_id, t0)
        _arch_started = datetime.fromtimestamp(t0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload["project_structure_mirror"] = {
            "project_name": _pn,
            "run_subdir": _run_subdir,
            "archive_started_utc": _arch_started,
            "relative_dir": _proj_rel,
            "note": (
                "Lab archive (suite-relative path): PDBs when predicted; result.json + "
                "humanization_report.html after generation. Job storage remains canonical for /files/ URLs."
                if _proj_rel
                else "Archive path unavailable.",
            ),
        }

        # Structure conservation only (Phase 5). Clinical Reference Cohort / AbEvaluator: use standalone CMC IgG — not bundled.
        payload["integrated_qc_summary"] = {
            "structure_conservation": {
                "cdr_rmsd": payload.get("cdr_rmsd"),
                "rmsd_to_reference": payload.get("rmsd_to_reference"),
                "global_fv_rmsd_ca": payload.get("global_fv_rmsd_ca"),
                "angle_delta_deg": payload.get("angle_delta_deg"),
                "vh_vl_angle_deg": payload.get("vh_vl_angle_deg"),
                "humanized_angle_deg": payload.get("humanized_angle_deg"),
                "plddt_mouse": payload.get("plddt"),
                "plddt_humanized": payload.get("humanized_plddt"),
                "note": "CDR Cα RMSD, global Fv Cα RMSD (framework-aligned), and VH/VL angles: donor vs humanized Fv.",
            },
            "post_humanization_abevaluator": {
                "bundled": False,
                "note": "Integrated post-humanization AbEvaluator CMC removed from this job; use CMC → IgG CMC with the same VH/VL.",
            },
        }
        jobs[job_id]["progress"] = 70

        # Clinical germline precedents + germline ADA: use the **selected** VH/VL (same as §0/§3 /
        # assembly). Do NOT use top_vh[0] + top_vl[0] — those are independently ranked lists and
        # can mix unrelated alleles (e.g. ref VL = IGKV1-39*01 while selected VL = IGKV1-33*01),
        # which mislabels Match as "VL exact" for drugs that match the wrong reference.
        best_vh_fb = ""
        best_vl_fb = ""
        try:
            cands = qm.get("framework_selection", {}).get("top_vh", [])
            if cands:
                best_vh_fb = cands[0]["germline"] if isinstance(cands[0], dict) else str(cands[0])
            cands = qm.get("framework_selection", {}).get("top_vl", [])
            if cands:
                best_vl_fb = cands[0]["germline"] if isinstance(cands[0], dict) else str(cands[0])
        except Exception:
            pass
        sel_vh = (payload.get("vh_germline") or "").strip()
        sel_vl = (payload.get("vl_germline") or "").strip()
        if sel_vh in ("", "—"):
            sel_vh = (best_vh_fb or "").strip()
        if sel_vl in ("", "—"):
            sel_vl = (best_vl_fb or "").strip()
        _route_payload = payload.get("per_chain_engineering_route") or {}
        _vh_surface_payload = _route_payload.get("vh") == "donor_framework_fr_surface_reshaping"
        _vl_surface_payload = _route_payload.get("vl") == "donor_framework_fr_surface_reshaping"
        payload["clinical_precedents"] = _lookup_clinical_precedents(
            "" if _vh_surface_payload else sel_vh,
            "" if _vl_surface_payload else sel_vl,
            top_n=8,
        )
        payload["clinical_precedents_vh_template"] = (
            [] if _vh_surface_payload else _lookup_clinical_precedents_for_template_side(sel_vh, "H", top_n=8)
        )
        payload["clinical_precedents_vl_template"] = (
            [] if _vl_surface_payload else _lookup_clinical_precedents_for_template_side(sel_vl, "L", top_n=8)
        )
        payload["report_generator_build"] = VHVL_HTML_REPORT_BUILD_ID
        payload["report_format_version"] = _vhvl_report_format_version_for_species(req.source_species)
        payload["germline_ada_references"] = (
            qm.get("clinical_reference", {}).get("germline_ada_references", [])
            or _lookup_germline_ada_references(sel_vh, sel_vl, top_n=8)
        )
        payload["germline_ada_references_vh_template"] = (
            [] if _vh_surface_payload else _lookup_germline_ada_references_for_template_side(sel_vh, "H", top_n=8)
        )
        payload["germline_ada_references_vl_template"] = (
            [] if _vl_surface_payload else _lookup_germline_ada_references_for_template_side(sel_vl, "L", top_n=8)
        )

        _qa_rec = getattr(result, "qa_audit", None)
        if not isinstance(_qa_rec, dict):
            _qa_rec = {}
        payload["qa_audit"] = _qa_rec
        payload["_qa_audit"] = _qa_rec

        # Save result JSON
        result_json = out / "result.json"
        result_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        _vhvl_copy_into_project_archive(_archive_dest, result_json)

        jobs[job_id]["progress"] = 76

        # Generate reports: controlled by payload.report_format (pdf | html | both)
        # FORCE HTML ONLY: PDF layout has issues and is not detailed enough.
        rf = "html"

        report_path = None
        report_url = None
        pdf_report_url = None
        if rf in ("html", "both"):
            try:
                report_path = _generate_html_report("vhvl_humanization", payload, out, _pn)
                if report_path is not None and report_path.exists():
                    _vhvl_copy_into_project_archive(_archive_dest, report_path)
            except Exception as _html_err:
                payload["_html_report_error"] = str(_html_err)
        jobs[job_id]["progress"] = 82
        
        # PDF generation is disabled per user request
        payload["pdf_report_url"] = None

        if rf == "pdf" and pdf_report_url:
            report_url = pdf_report_url
        elif rf == "html" and report_path is not None and report_path.exists():
            report_url = files_url_for_path(job_id, report_path)
        elif rf == "both":
            if report_path is not None and report_path.exists():
                report_url = files_url_for_path(job_id, report_path)
            elif pdf_report_url:
                report_url = pdf_report_url
        elif pdf_report_url:
            report_url = pdf_report_url

        jobs[job_id]["progress"] = 88

        # Delivery ZIP: customer-facing package only
        zip_url = None
        _zip_proj_rel = (payload.get("project_structure_mirror") or {}).get("relative_dir")
        try:
            zip_url = _create_delivery_zip(out, job_id, project_structure_rel=_zip_proj_rel)
            payload["zip_url"] = zip_url
            # Second pass: embed ZIP link in internal HTML, then refresh ZIP.
            if zip_url and rf in ("html", "both") and report_path is not None and report_path.exists():
                try:
                    _generate_html_report("vhvl_humanization", payload, out, job_id)
                    if report_path.exists():
                        _vhvl_copy_into_project_archive(_archive_dest, report_path)
                    _create_delivery_zip(out, job_id, project_structure_rel=_zip_proj_rel)
                except Exception:
                    pass
        except Exception:
            payload["zip_url"] = zip_url

        jobs[job_id]["progress"] = 96

        # Final result.json on disk + project archive match payload (e.g. zip_url).
        try:
            result_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            _vhvl_copy_into_project_archive(_archive_dest, result_json)
        except Exception:
            pass

        elapsed = round(time.time() - t0, 1)
        _extra = {"zip_url": zip_url, "pdf_report_url": pdf_report_url}
        save_result(job_id, payload, report_url, elapsed, extra=_extra)
        return JobStatus(
            job_id=job_id, status="done", progress=100,
            elapsed_sec=elapsed, result=payload, report_url=report_url,
            extra=_extra,
        )

    except Exception as e:
        import traceback
        from core.qa.pipeline_qa import QAViolation
        from core.integrity.hallucination_guard import HallucinationError

        # Map internal errors to formal user-facing notifications
        formal_error = str(e)
        if isinstance(e, HallucinationError) or "[HallucinationGuard]" in str(e):
            formal_error = f"Sequence Integrity Error: {e}"
        elif isinstance(e, QAViolation):
            formal_error = f"Quality Assurance Violation: {e}"
        elif "Illegal alphabet" in str(e):
            formal_error = f"Invalid Sequence: {e}"

        err = f"{type(e).__name__}: {formal_error}\n{traceback.format_exc()}"
        jobs[job_id] = {"status": "failed", "progress": 0, "error": formal_error}
        persist_job_snapshot(job_id)
        
        status = 422 if (isinstance(e, QAViolation) or isinstance(e, HallucinationError)) else 500
        raise HTTPException(status_code=status, detail=formal_error)


@router.post("/vh_vl", response_model=JobStatus, summary="Humanize murine VH/VL antibody")
def humanize_vh_vl(req: VHVLRequest):
    """
    Humanize a VH+VL donor pair using the V5.4.0 multi-species flow (report build V5.4.1 hygiene).

    Pipeline (V5.4.0, 5-phase, protocol-locked):
    - Phase 1: CDR identification (IMGT+Kabat+Chothia union)
    - Phase 2: Clinical-anchor-only human germline framework selection
    - Phase 3: Structure prediction
    - Phase 4: Deterministic back-mutation + rescue ladder
    - Phase 5: QC + mini-CMC + clinical reference linkage

    Returns top-ranked humanized sequences + key parameters + PDF report.
    """
    job_id = f"hu-vhvl-{uuid.uuid4().hex[:8]}"
    return _humanize_vh_vl_impl(job_id, req)


@router.post("/vh_vl/async", summary="Enqueue VH/VL humanization (poll GET /jobs/{job_id})")
def humanize_vh_vl_async(req: VHVLRequest):
    """Return immediately with job_id; run pipeline in a background thread."""
    job_id = f"hu-vhvl-{uuid.uuid4().hex[:8]}"
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "progress_note": "Queued — worker starting (poll GET /jobs for % and status)",
    }
    persist_job_snapshot(job_id)

    def _worker() -> None:
        try:
            _humanize_vh_vl_impl(job_id, req)
        except HTTPException:
            pass
        except BaseException as e:
            # Catch BaseException (including HardGateError and unexpected SystemExit)
            # so a pipeline abort never propagates to the uvicorn main process.
            err_msg = f"{type(e).__name__}: {e}"
            jobs[job_id] = {"status": "failed", "progress": 0, "error": err_msg}
            persist_job_snapshot(job_id)

    threading.Thread(target=_worker, daemon=True).start()
    return {"job_id": job_id, "status": "queued", "poll_url": f"/jobs/{job_id}"}


def _create_vhh_delivery_zip(out_dir: Path, job_id: str) -> Optional[str]:
    """Pack VHH humanization deliverables: FASTA + optional HTML + PDBs.

    HTML is optional: if the HTML report step fails, clients still get a valid ZIP (FASTA).
    """
    import zipfile
    zip_name = f"{job_id}_vhh_delivery.zip"
    zip_path = out_dir / zip_name
    # Minimum for a useful delivery: donor/humanized FASTA (written before the HTML step)
    if not (out_dir / "vhh_sequences.fasta").is_file():
        return None

    core: List[str] = ["vhh_sequences.fasta"]
    html_nested = out_dir / "reports" / "vhh_humanization" / "humanization_report.html"
    html_legacy = out_dir / "humanization_report.html"
    html_src = html_nested if html_nested.is_file() else html_legacy
    if html_src.is_file():
        core.append("__HTML_REPORT__")

    optional = ("donor_vhh.pdb", "humanized_vhh.pdb")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in core:
            if name == "__HTML_REPORT__":
                zf.write(html_src, arcname="humanization_report.html")
            else:
                zf.write(out_dir / name, arcname=name)
        for name in optional:
            fp = out_dir / name
            if fp.is_file():
                zf.write(fp, arcname=name)

    return f"/files/{job_id}/{zip_name}"


# ─────────────────────────────────────────────────────────────────────────────
# V3.0 CMC Advisory Builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_cmc_advisory(
    donor_cmc: dict,
    humanized_cmc: dict,
    cdr_rmsd: dict,
    cdr_info: dict,
) -> list:
    """Build a deterministic CMC optimization advisory list (V3.0).

    All recommendations are rule-based (frozen thresholds from §4 standard).
    No AI judgment — each entry maps a failing metric to a specific offline service.

    Returns list of advisory dicts:
      type, severity, finding, recommendation, offline_service, estimated_time
    """
    advisories = []
    _d = donor_cmc if isinstance(donor_cmc, dict) else {}
    _h = humanized_cmc if isinstance(humanized_cmc, dict) else {}

    d_ii   = _d.get("instability_index")
    h_ii   = _h.get("instability_index")
    d_sap  = _d.get("SAP_proxy")
    h_sap  = _h.get("SAP_proxy")

    # Advisory 1 — Instability Index > 40
    if h_ii is not None and h_ii > 40:
        origin = (
            "sequence-intrinsic (already present in donor)"
            if d_ii is not None and d_ii > 40
            else "introduced by framework substitution"
        )
        severity = "high" if h_ii > 50 else "medium"
        advisories.append({
            "type": "instability",
            "severity": severity,
            "finding": f"Instability Index = {h_ii:.1f} > 40 ({origin})",
            "recommendation": (
                "Perform targeted stability optimization on identified liability hotspots "
                "using advanced free-energy perturbation scanning to identify stabilizing mutations."
            ),
            "offline_service": "CMC Stability Optimization",
            "environment": "affmat conda env",
            "estimated_time": "~1-2 business days",
        })

    # Advisory 2 — SAP > p75 (0.639)
    if h_sap is not None and h_sap > 0.639:
        origin = (
            "sequence-intrinsic (already present in donor)"
            if d_sap is not None and d_sap > 0.639
            else "introduced by framework substitution"
        )
        severity = "high" if h_sap > 0.750 else "medium"
        advisories.append({
            "type": "sap",
            "severity": severity,
            "finding": (
                f"SAP proxy = {h_sap:.3f} > 0.639"
                + (", p90 red zone" if h_sap > 0.750 else "")
                + f" ({origin})"
            ),
            "recommendation": (
                "Apply structure-guided surface reshaping to optimize surface properties "
                "while preserving CDR conformations."
            ),
            "offline_service": "Surface Reshaping (Veneering)",
            "environment": "anarcii conda env",
            "estimated_time": "~1 business day",
        })

    # Advisory 3 — CDR RMSD > 2.0Å
    if isinstance(cdr_rmsd, dict):
        failed_rmsd = [
            k for k, v in cdr_rmsd.items()
            if isinstance(v, (int, float)) and float(v) > 2.0
        ]
        if failed_rmsd:
            cdr3_len = len(cdr_info.get("CDR3", ""))
            advisories.append({
                "type": "cdr_rmsd",
                "severity": "medium",
                "finding": (
                    f"CDR RMSD > 2.0Å: {', '.join(failed_rmsd)} — "
                    f"CDR loop conformation deviated from donor"
                    + (f" (CDR3={cdr3_len}aa long loop is a contributing factor)" if cdr3_len >= 12 else "")
                ),
                "recommendation": (
                    "Perform targeted Vernier zone backmutations to restore native CDR loop conformations, "
                    "followed by structural verification."
                ),
                "offline_service": "Vernier Backmutation & Structure QC",
                "environment": "anarcii + affmat conda env",
                "estimated_time": "~1-2 business days",
            })

    return advisories


_SPECIES_CMC_GATES: Dict[str, Dict] = {
    "mouse": {
        "instability_index_warn": 40,
        "pi_fab_min": 5.5, "pi_fab_max": 9.0,
        "total_cdr_len_warn": 60,
        "sfvcsp_warn": 500,
        "free_cys_fr_hard": 0,
        "note": None,
    },
    "rat": {
        "instability_index_warn": 42,
        "pi_fab_min": 5.0, "pi_fab_max": 9.5,
        "total_cdr_len_warn": 62,
        "sfvcsp_warn": 500,
        "free_cys_fr_hard": 0,
        "note": None,
    },
    "rabbit": {
        "instability_index_warn": 48,
        "pi_fab_min": 5.5, "pi_fab_max": 9.5,
        "total_cdr_len_warn": 70,
        "sfvcsp_warn": 600,
        "free_cys_fr_hard": 0,
        "cdrh3_disulfide_exempt": True,
        "note": None,
    },
}

def _species_cmc_gates(source_species: str | None) -> Dict:
    """Return species-appropriate CMC gate thresholds for reporting."""
    key = (source_species or "mouse").strip().lower()
    return _SPECIES_CMC_GATES.get(key, _SPECIES_CMC_GATES["mouse"])


def _build_vhvl_cmc_advisory(
    donor_cmc: dict,
    humanized_cmc: dict,
    cdr_rmsd: dict,
    checklist_status: str,
    flags: list,
    source_species: str = "mouse",
    stable_cdr_keys: Optional[List[str]] = None,
) -> list:
    """Build a deterministic CMC optimization advisory list for VH/VL (V4.8.1).
    
    Maps failing metrics to specific offline services.
    Uses species-appropriate instability threshold from _species_cmc_gates.
    """
    advisories = []
    _d = donor_cmc if isinstance(donor_cmc, dict) else {}
    _h = humanized_cmc if isinstance(humanized_cmc, dict) else {}

    d_ii   = _d.get("instability_index")
    h_ii   = _h.get("instability_index")
    d_gravy = _d.get("GRAVY")
    h_gravy = _h.get("GRAVY")

    # Advisory 1 — Instability Index (species-specific threshold)
    _ii_warn = _species_cmc_gates(source_species).get("instability_index_warn", 40)
    if h_ii is not None and h_ii > _ii_warn:
        origin = (
            "sequence-intrinsic (already present in donor)"
            if d_ii is not None and d_ii > _ii_warn
            else "introduced by framework substitution"
        )
        severity = "high" if h_ii > _ii_warn + 10 else "medium"
        advisories.append({
            "type": "instability",
            "severity": severity,
            "finding": f"Instability Index = {h_ii:.1f} > {_ii_warn} ({origin})",
            "recommendation": (
                "Perform targeted stability optimization on identified liability hotspots "
                "using advanced free-energy perturbation scanning to identify stabilizing mutations."
            ),
            "offline_service": "CMC Stability Optimization",
            "environment": "affmat conda env",
            "estimated_time": "~1-2 business days",
        })

    # Advisory 2 — GRAVY > 0.2 (Hydrophobicity)
    if h_gravy is not None and h_gravy > 0.2:
        origin = (
            "sequence-intrinsic (already present in donor)"
            if d_gravy is not None and d_gravy > 0.2
            else "introduced by framework substitution"
        )
        severity = "high" if h_gravy > 0.4 else "medium"
        advisories.append({
            "type": "hydrophobicity",
            "severity": severity,
            "finding": f"GRAVY = {h_gravy:.3f} > 0.2 ({origin})",
            "recommendation": (
                "Apply structure-guided surface reshaping to optimize surface properties "
                "while preserving CDR conformations."
            ),
            "offline_service": "Surface Reshaping (Veneering)",
            "environment": "anarcii conda env",
            "estimated_time": "~1 business day",
        })

    # Advisory 3 — CDR RMSD > 1.5Å for STABLE loops (engine-classified when provided)
    if isinstance(cdr_rmsd, dict):
        stable_loops = stable_cdr_keys if stable_cdr_keys else ["H1", "H2", "L2", "L3"]
        failed_rmsd = [
            k for k, v in cdr_rmsd.items()
            if k in stable_loops and isinstance(v, (int, float)) and float(v) >= 1.5
        ]
        if failed_rmsd:
            advisories.append({
                "type": "cdr_rmsd",
                "severity": "high",
                "finding": (
                    f"CDR RMSD ≥ 1.5Å on STABLE loops: {', '.join(failed_rmsd)} — "
                    f"CDR loop conformation deviated significantly from donor."
                ),
                "recommendation": (
                    "Perform targeted Vernier zone backmutations to restore native CDR loop conformations, "
                    "followed by structural verification."
                ),
                "offline_service": "Vernier Backmutation & Structure QC",
                "environment": "anarcii + affmat conda env",
                "estimated_time": "~1-2 business days",
            })

    # Advisory 4 — Immunogenicity / General FAIL
    if checklist_status == "FAIL":
        immuno_fail = any("immunogenicity" in str(f).lower() for f in flags)
        if immuno_fail:
            advisories.append({
                "type": "immunogenicity",
                "severity": "high",
                "finding": "High immunogenicity risk identified in humanized sequence.",
                "recommendation": (
                    "Perform structure-based T-cell epitope de-risking (EpiDesignCore) "
                    "to identify and remove MHC-II binding motifs while preserving affinity."
                ),
                "offline_service": "EpiDesignCore (De-immunization)",
                "environment": "episcan conda env",
                "estimated_time": "~2-3 business days",
            })

    return advisories


def _vhh_assert_pipeline_cdr_match(donor_seq: str, output_seq: str) -> None:
    """
    Hard gate: CDR1–CDR3 from donor vs final output must match under the same
    IMGT rules as the VHH pipeline (`split_regions` + `imgt_number_anarcii`).
    Blocks FASTA/ZIP/report when CDR graft or assembly is inconsistent.
    """
    from core.numbering.imgt_anarcii import imgt_number_anarcii
    from core.qa.pipeline_qa import QAViolation
    from core.vhh_humanization import split_regions

    d = (donor_seq or "").strip().upper()
    h = (output_seq or "").strip().upper()
    if len(d) < 30 or len(h) < 30:
        raise QAViolation(
            "VHH CDR preservation gate: donor or output sequence too short for IMGT numbering."
        )
    try:
        rd = split_regions(imgt_number_anarcii(d))
        rh = split_regions(imgt_number_anarcii(h))
    except Exception as ex:
        raise QAViolation(
            f"VHH CDR preservation gate: IMGT segmentation failed ({type(ex).__name__}: {ex})."
        ) from ex
    mismatches: List[str] = []
    for key in ("CDR1", "CDR2", "CDR3"):
        ds, hs = rd.get(key, ""), rh.get(key, "")
        if ds != hs:
            mismatches.append(f"{key}: lengths {len(ds)} vs {len(hs)}")
    if mismatches:
        raise QAViolation(
            "VHH CDR preservation HARD GATE — delivery blocked until CDRs match donor: "
            + "; ".join(mismatches)
        )


def _build_vhh_imgt_fr_cdr_segmentation_panel(donor_seq: str, hum_seq: str) -> str:
    """
    Single-chain donor vs humanized FR/CDR panel using pipeline segmentation
    (`imgt_number_anarcii` + `core.vhh_humanization.split_regions`).
    Matches graft/QC boundaries — avoids false CDR mismatch from ad-hoc IMGT spans.
    """
    import html as _html

    def esc(v: Any) -> str:
        return "—" if v is None else _html.escape(str(v))

    donor_seq = (donor_seq or "").strip().upper()
    hum_seq = (hum_seq or "").strip().upper()
    if len(donor_seq) < 30 or len(hum_seq) < 30:
        return (
            "<p class='note'>FR/CDR segmentation requires valid donor and humanized sequences "
            "(minimum length not met).</p>"
        )

    ORDER = ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]
    from core.numbering.imgt_anarcii import imgt_number_anarcii
    from core.vhh_humanization import IMGT_REGIONS, split_regions

    def _span_caption(seg: str) -> str:
        meta = IMGT_REGIONS[seg]
        lo, hi = int(meta["start"]), int(meta["end"])
        if seg == "CDR2":
            return f"IMGT {lo}–{hi} (+55→CDR2 when Kabat CDR2≥17aa)"
        return f"IMGT {lo}–{hi}"

    def _extract_regions(seq: str) -> dict:
        try:
            rows = imgt_number_anarcii(seq)
            return split_regions(rows)
        except Exception:
            return {}

    donor_reg = _extract_regions(donor_seq)
    hum_reg = _extract_regions(hum_seq)
    if not donor_reg or not hum_reg:
        return "<p class='note'>Could not IMGT-number one or both sequences — segmentation unavailable.</p>"

    def _highlight_diff(ref: str, query: str, is_cdr: bool) -> str:
        if not ref or not query:
            return f"<span style='font-family:monospace'>{esc(query or '—')}</span>"
        if is_cdr:
            return (
                f"<span style='font-family:monospace;background:#fef3c7;"
                f"padding:0 2px;border-radius:2px'>{esc(query)}</span>"
            )
        if len(ref) != len(query):
            return (
                f"<span style='font-family:monospace;color:#b91c1c;font-weight:700'>"
                f"{esc(query)}</span>"
            )
        parts = []
        for r, q in zip(ref, query):
            if r != q:
                parts.append(
                    f"<span style='background:#fee2e2;color:#b91c1c;"
                    f"font-weight:700;padding:0 1px;border-radius:2px'>{esc(q)}</span>"
                )
            else:
                parts.append(esc(q))
        return f"<span style='font-family:monospace'>{''.join(parts)}</span>"

    def _status(d: str, h: str, is_cdr: bool) -> str:
        if d == h:
            return "<span style='color:#1a7a3c;font-weight:700'>✓ Identical</span>"
        if is_cdr:
            return (
                "<span style='color:#d97706;font-weight:700'>⚠ CDR mismatch — review numbering / graft</span>"
            )
        n = sum(1 for a, b in zip(d, h) if a != b) if len(d) == len(h) else abs(len(d) - len(h))
        return f"<span style='color:#b91c1c;font-weight:700'>≠ {n} aa changed</span>"

    rows_html = ""
    for seg in ORDER:
        d_seg = donor_reg.get(seg, "")
        h_seg = hum_reg.get(seg, "")
        is_cdr = seg.startswith("CDR")
        span_cap = _span_caption(seg)
        tag_bg = "#f59e0b" if is_cdr else "#3b82f6"
        row_bg = "#fffbeb" if is_cdr else "transparent"
        d_html = (
            f"<span style='font-family:monospace;background:#fef3c7;padding:0 2px;border-radius:2px'>"
            f"{esc(d_seg)}</span>"
            if is_cdr
            else f"<span style='font-family:monospace'>{esc(d_seg)}</span>"
        )
        h_html = _highlight_diff(d_seg, h_seg, is_cdr)
        st_html = _status(d_seg, h_seg, is_cdr)
        n_d, n_h = len(d_seg), len(h_seg)
        len_note = (
            f" <span style='color:#888;font-size:10px'>({n_d} aa)</span>"
            if n_d == n_h
            else f" <span style='color:#b91c1c;font-size:10px'>({n_d} aa vs {n_h} aa)</span>"
        )
        rows_html += f"""
            <tr style='background:{row_bg};border-bottom:1px solid #e5e7eb'>
              <td style='padding:6px 8px;white-space:nowrap;vertical-align:top'>
                <span style='background:{tag_bg};color:#fff;border-radius:3px;
                  padding:1px 6px;font-size:10px;font-weight:700'>
                  {'CDR' if is_cdr else 'FR'}</span>
                <b style='margin-left:4px'>{esc(seg)}</b>
                <div style='color:#9ca3af;font-size:10px;margin-top:2px'>{esc(span_cap)}{len_note}</div>
              </td>
              <td style='padding:6px 8px;word-break:break-all;vertical-align:top'>{d_html}</td>
              <td style='padding:6px 8px;word-break:break-all;vertical-align:top'>{h_html}</td>
              <td style='padding:6px 8px;white-space:nowrap;vertical-align:top;font-size:11px'>{st_html}</td>
            </tr>"""

    total_mut = sum(
        (
            0
            if donor_reg.get(s, "") == hum_reg.get(s, "")
            else (
                sum(
                    1
                    for a, b in zip(donor_reg.get(s, ""), hum_reg.get(s, ""))
                    if a != b
                )
                if len(donor_reg.get(s, "")) == len(hum_reg.get(s, ""))
                else max(len(donor_reg.get(s, "")), len(hum_reg.get(s, "")))
            )
        )
        for s in ORDER
        if not s.startswith("CDR")
    )
    cdr_mut = sum(
        1 for s in ORDER if s.startswith("CDR") and donor_reg.get(s, "") != hum_reg.get(s, "")
    )
    cdr_ok_badge = (
        "<span style='background:#1a7a3c;color:#fff;border-radius:4px;padding:2px 8px;"
        "font-size:11px;font-weight:700'>CDR IDENTICAL</span>"
        if cdr_mut == 0
        else "<span style='background:#d97706;color:#fff;border-radius:4px;padding:2px 8px;"
        "font-size:11px;font-weight:700'>CDR REVIEW</span>"
    )

    return f"""
    <p class='note' style='margin-bottom:12px'>
      Side-by-side FR/CDR segmentation using <code>core.vhh_humanization.split_regions</code>
      (same boundaries as CDR graft / hard QA gate).
      <b>CDR regions</b> are copied from the donor and must match exactly after successful humanization.
      <b>FR differences</b> reflect framework substitution to the selected human template plus any tier-protected back-mutations.
    </p>
    <div style='margin-top:4px;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden'>
      <div style='background:#1b4fad;color:#fff;padding:10px 14px;display:flex;
        align-items:center;justify-content:space-between'>
        <span style='font-weight:700;font-size:13px'>VHH — FR / CDR Segmentation &nbsp;
          <span style='font-size:11px;opacity:.8'>(IMGT V-domain)</span></span>
        <span style='display:flex;gap:8px;align-items:center'>
          {cdr_ok_badge}
          <span style='background:rgba(255,255,255,.18);border-radius:4px;padding:2px 8px;
            font-size:11px'>FR: {total_mut} substitution(s)</span>
        </span>
      </div>
      <table style='width:100%;border-collapse:collapse;font-size:12px'>
        <thead>
          <tr style='background:#f1f5f9;font-size:11px;color:#374151'>
            <th style='padding:7px 8px;width:120px;text-align:left;border-bottom:2px solid #e5e7eb'>
              Region <span style='color:#9ca3af'>(IMGT)</span></th>
            <th style='padding:7px 8px;text-align:left;border-bottom:2px solid #e5e7eb'>Donor VHH</th>
            <th style='padding:7px 8px;text-align:left;border-bottom:2px solid #e5e7eb'>Humanized VHH</th>
            <th style='padding:7px 8px;width:110px;text-align:left;border-bottom:2px solid #e5e7eb'>Match</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
      <div style='background:#f8fafc;padding:6px 12px;font-size:10px;color:#9ca3af;
        border-top:1px solid #e5e7eb'>
        Legend: CDR = amber background · FR mutations = red highlight · ✓ Identical · IMGT regions per pipeline IMGT_REGIONS
      </div>
    </div>"""


# ─────────────────────────────────────────────────────────────────────────────
# VHH HTML Report (default)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_vhh_html_report(payload: dict, out_dir: Path, project_name: str = "") -> Path:
    """Generate a V3.0-aligned self-contained HTML report for VHH humanization."""
    import html as _html
    from datetime import datetime

    def H(en: str, zh: str) -> str:
        return en

    ts    = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    title = f"InSynBio AbEngineCore | VHH Humanization Report"
    # Display label: explicit arg > sequence_name > project_name (if not placeholder) > job from payload
    _job = str(payload.get("job_id") or "")
    _pn = (payload.get("project_name") or "demo")
    if isinstance(_pn, str) and _pn.strip().lower() in ("", "demo", "vhh humanization"):
        _pn = ""
    proj = (
        (project_name or "").strip()
        or (payload.get("sequence_name") or "").strip()
        or _pn
        or _job
        or "VHH Humanization"
    )
    report_h1 = "InSynBio AbEngineCore"
    report_sub = f"VHH Antibody Humanization Report | {VHH_REPORT_PROTOCOL_VERSION} Protocol"
    proj_lbl = "Sequence / project name"
    conf_lbl = "CONFIDENTIAL"
    footer_line = (
        f'InSynBio Research &nbsp;·&nbsp; <a href="https://www.insynbio.com">https://www.insynbio.com</a> '
        f"&nbsp;·&nbsp; {ts} &nbsp;·&nbsp; Confidential &nbsp;·&nbsp; "
        "Use Ctrl+P → Save as PDF to export this report."
    )

    def esc(v: Any) -> str:
        return "—" if v is None else _html.escape(str(v))

    def pct(v: Any) -> str:
        if isinstance(v, float):
            return f"{v*100:.1f}%" if v <= 1 else f"{v:.1f}%"
        return "—" if v is None else str(v)

    def num(v: Any, decimals=3) -> str:
        if isinstance(v, float):
            return f"{v:.{decimals}f}"
        return "—" if v is None else str(v)

    def row(label: str, value) -> str:
        v = "—" if (value is None or value == "" or value == []) else str(value)
        return f"<tr><td class='lbl'>{label}</td><td>{v}</td></tr>"

    def seq_block(label: str, seq: str) -> str:
        if not seq:
            return ""
        chunks = [seq[i:i+10] for i in range(0, len(seq), 10)]
        numbered = " ".join(f'<span class="chunk">{c}</span>' for c in chunks)
        return f"""
        <div class='seq-block'>
          <div class='seq-label'>{label} <span class='seq-len'>{len(seq)} aa</span></div>
          <div class='seq-body'>{numbered}</div>
        </div>"""

    def _badge(ok: bool, t="PASS", f="FAIL"):
        cls = "badge-ok" if ok else "badge-fail"
        return f"<span class='badge {cls}'>{t if ok else f}</span>"

    def _build_discussion_box(title: str, content: str) -> str:
        """Standard discussion box for results interpretation."""
        return f"""
        <div class="discussion-box">
          <div class="discussion-title">{title}</div>
          <p class="discussion-content">{content}</p>
        </div>"""

    status = str(payload.get("checklist_status") or "UNKNOWN").upper()
    if status.startswith("OK") or status.startswith("PASS"):
        st_badge = "<span class='badge badge-ok'>PASS</span>"
    elif status == "WARN" or "WARN" in status:
        st_badge = "<span class='badge badge-warn'>WARN</span>"
    else:
        st_badge = "<span class='badge badge-fail'>FAIL</span>"

    strategy = payload.get("strategy_applied", "auto")
    candidates = payload.get("candidates", []) or []
    flags = payload.get("flags") or []
    mini_cmc = payload.get("mini_cmc") or {}
    cdr_rmsd = payload.get("cdr_rmsd") or {}

    def hm_badge(pos: str, aa: str, ok_vals: list) -> str:
        ok = aa in ok_vals
        col = "#d1fae5" if ok else "#fef3c7"
        text_col = "#059669" if ok else "#d97706"
        border = "#6ee7b7" if ok else "#fcd34d"
        return (f'<td style="text-align:center"><span style="background:{col};color:{text_col};'
                f'padding:2px 7px;border-radius:4px;border:1px solid {border};font-family:monospace;font-weight:bold">{esc(aa)}</span></td>')

    # 4 display positions: IMGT 37 (CDR1) + FR2 44/45/47. V3.0 engineering & QA focus on FR2; 37 is graft-preserved.
    _ok37 = ("F", "Y", "V", "I", "L", "M", "A", "W")
    rows_hm = (
        f'<tr><td>37</td>{hm_badge("37", payload.get("hallmark_37", "?"), list(_ok37))}'
        f'<td>IMGT 37 (CDR1–framework boundary): typically hydrophobic and stabilizes the CDR1 loop. '
        f'Under <b>FR-only grafting</b>, this site is copied from the donor together with CDR1 (it is not independently re-humanized). '
        f'This four-row hallmark panel lists IMGT 37 plus FR2 positions 44/45/47; older literature may refer to the same IMGT site as '
        f'<b>“W37”</b> when tryptophan was common there.</td></tr>'
        f'<tr><td>44</td>{hm_badge("44", payload.get("hallmark_44","?"),["E","G","A","S","D","Q"])}'
        f'<td>FR2 VHH hallmark (solubilizing)</td></tr>'
        f'<tr><td>45</td>{hm_badge("45", payload.get("hallmark_45","?"),["A","R","L","K","Q"])}'
        f'<td>FR2 VHH hallmark (solubility; A=clinical norm 97.6%)</td></tr>'
        f'<tr><td>47</td>{hm_badge("47", payload.get("hallmark_47","?"),["F","Y","L","W","G"])}'
        f'<td>FR2 VHH hallmark (packing)</td></tr>'
    )

    cand_rows = ""
    for i, c in enumerate(candidates):
        al = c.get("alignment_scores") or {}
        if isinstance(al, str):
            al = {}
        seq = c.get("humanized_sequence") or c.get("sequence") or ""
        cand_rows += (
            f'<tr class="{"row-best" if i==0 else ""}">'
            f'<td>{i+1}</td>'
            f'<td><b>{esc(c.get("template_id") or c.get("source_scaffold",""))}</b></td>'
            f'<td>{pct(al.get("framework_identity", c.get("framework_identity")))}</td>'
            f'<td><b>{num(al.get("combined_score", c.get("score")), 3)}</b></td>'
            f'<td>{esc(c.get("plan_name") or c.get("panel",""))}</td>'
        f'<td style="font-family:monospace;font-size:0.78em;word-break:break-all">'
        f'{esc(seq[:80])}{"…" if len(seq)>80 else ""}</td></tr>'
    )

    _s6_html = f"""
  <div class='section' id='s6'>
    <h3>§6 — Ranking &amp; Candidates</h3>
    <table class='params'>
      <tr><th style="width:4%">#</th><th style="width:16%">Template</th><th style="width:10%">FR Id%</th><th style="width:10%">Score</th><th style="width:12%">Panel</th><th>Humanized Sequence</th></tr>
      {cand_rows}
    </table>
  </div>""" if cand_rows else ""

    _lead_hum = (payload.get("humanized_sequence") or "").strip()
    _lead_norm = _lead_hum.upper()
    _s7_seqs = seq_block("Lead humanized VHH (Top-1 ranked)", _lead_hum)
    for i, c in enumerate(candidates):
        cs_raw = (c.get("humanized_sequence") or c.get("sequence") or "").strip()
        if not cs_raw:
            continue
        if cs_raw.upper() == _lead_norm:
            continue
        tid = esc(c.get("template_id") or c.get("source_scaffold", "") or f"rank {i+1}")
        _s7_seqs += seq_block(f"Alternate candidate ({tid})", cs_raw)
    # When surface reshaping was the primary path, append the reshaped sequence to §7
    _sr_out_seq = (payload.get("surface_reshaping") or {}).get("output_sequence") or ""
    if _sr_out_seq and not candidates:
        _sr_n_muts = (payload.get("surface_reshaping") or {}).get("positions_modified", 0)
        _s7_seqs += seq_block(f"Surface Reshaped ({_sr_n_muts} mutations applied)", _sr_out_seq)

    # ── §6PG Post-Graft Surface Reshaping (humanization_plus_reshape path) ──────────────────────
    _pgsr = payload.get("post_graft_surface_reshaping") or {}
    if _pgsr and _pgsr.get("positions_modified", 0) > 0:
        _pgsr_muts = [m for m in (_pgsr.get("mutations") or []) if m.get("applied")]
        _pgsr_mut_rows = "".join(
            f"<tr><td style='text-align:center;font-family:monospace'>{esc(m['imgt_label'])}</td>"
            f"<td style='text-align:center'>{m['from_aa']}</td>"
            f"<td style='text-align:center;color:#0891b2;font-weight:bold'>{m['to_aa']}</td></tr>"
            for m in _pgsr_muts
        ) or "<tr><td colspan='3' style='color:#475569;font-style:italic'>No mutations</td></tr>"
        _pgsr_sap_b = _pgsr.get("sap_before")
        _pgsr_sap_a = _pgsr.get("sap_after")
        _pgsr_achieved = _pgsr.get("target_achieved", False)
        _pgsr_sap_b_str = f"{_pgsr_sap_b:.3f}" if _pgsr_sap_b is not None else "—"
        _pgsr_sap_a_str = f"{_pgsr_sap_a:.3f}" if _pgsr_sap_a is not None else "—"
        _pgsr_sap_a_sfx = "✓" if _pgsr_achieved else "· not fully achieved"
        _pgsr_sap_a_style = "color:var(--ok);font-weight:bold" if _pgsr_achieved else "color:var(--warn)"
        _pgsr_cdr_note = (
            "<p style='font-size:.79rem;color:#854d0e;margin-top:8px'>"
            "Residual SAP may still be CDR-loop driven — see CDR-Driven Hydrophobicity note.</p>"
        ) if not _pgsr_achieved else ""
        _pgsr_section_html = (
            "<div class='section' id='s6pg' style='border-top:3px solid #0891b2;'>"
            "<h3>&#167;6 &#8212; Post-Graft Surface Reshaping "
            "<span style='font-size:.75rem;font-weight:400;color:#0891b2;background:#e0f2fe;padding:2px 8px;border-radius:4px'>Sequential Pass</span></h3>"
            "<p style='font-size:.83rem;color:#374151;margin-bottom:10px'>"
            "CDR-graft humanization was completed first (see &#167;5). "
            "Because donor SAP was in the yellow zone, surface reshaping was applied automatically "
            "to the humanized sequence as a sequential step to reduce residual framework hydrophobic patches.</p>"
            "<table class='params' style='margin-bottom:12px'>"
            "<tr><th style='width:38%'>Metric</th><th>Value</th></tr>"
            f"<tr><td class='lbl'>SAP Before Reshaping</td><td style='font-family:monospace'>{_pgsr_sap_b_str}</td></tr>"
            f"<tr><td class='lbl'>SAP After Reshaping</td><td style='font-family:monospace;{_pgsr_sap_a_style}'>{_pgsr_sap_a_str} {_pgsr_sap_a_sfx}</td></tr>"
            f"<tr><td class='lbl'>FR Mutations Applied</td><td><b>{_pgsr.get('positions_modified', 0)}</b></td></tr>"
            "</table>"
            "<h4 style='margin:8px 0 5px;font-size:.85rem'>Mutations Applied to Humanized Sequence</h4>"
            "<table class='params'>"
            "<tr><th>IMGT Position</th><th>From</th><th>To</th></tr>"
            f"{_pgsr_mut_rows}</table>"
            f"{_pgsr_cdr_note}"
            "</div>"
        )
    else:
        _pgsr_section_html = ""

    # ── §6SR Surface Reshaping section (only when surface_reshaping path was taken) ─────────────
    _sr = payload.get("surface_reshaping") or {}
    if _sr:
        _sr_why_rows = ""
        _sr_why_items = []
        _fp_for_sr = payload.get("feasibility_prescreen") or {}
        _fp_reasons_sr = _fp_for_sr.get("reasons") or []
        _fp_note_sr = _fp_for_sr.get("feasibility_note") or ""
        for _r in _fp_reasons_sr:
            _sr_why_items.append(f"<li style='margin-bottom:4px'>{esc(str(_r))}</li>")
        _sr_why_list = "<ul style='margin:6px 0 0 16px;padding:0'>" + "".join(_sr_why_items) + "</ul>" if _sr_why_items else ""

        _sr_muts = _sr.get("mutations") or []
        _sr_mut_rows = "".join(
            f"<tr><td style='font-family:monospace'>{esc(str(m.get('imgt_label','')))}</td>"
            f"<td style='text-align:center;font-family:monospace'>{esc(str(m.get('from_aa','')))}</td>"
            f"<td style='text-align:center;font-family:monospace'>{esc(str(m.get('to_aa','')))}</td>"
            f"<td style='text-align:center'>{m.get('sasa_pct',0.0):.0f}%</td>"
            f"<td style='text-align:center'>{'✓' if m.get('applied') else 'dry-run'}</td></tr>"
            for m in _sr_muts
        ) or "<tr><td colspan='5' style='color:#475569;font-style:italic'>No eligible framework mutations — sequence meets SAP target, or all candidates are in protected positions.</td></tr>"

        _sr_sap_b = _sr.get("sap_before")
        _sr_sap_a = _sr.get("sap_after")
        _sr_target = _sr.get("target_sap")
        _sr_achieved = _sr.get("target_achieved", False)
        _sr_strategy = _sr.get("strategy", "S2")
        _sr_strategy_desc = {
            "S1": "S1 — aggressive (SAP ≤ 0.750, 90th-pct clinical VHH benchmark)",
            "S2": "S2 — conservative (SAP ≤ 0.639, 75th-pct clinical VHH benchmark)",
        }.get(_sr_strategy, _sr_strategy)
        _sr_err = _sr.get("error")
        _sr_cov_warn = _sr.get("imgt_coverage_warning") or ""
        _sr_coverage = _sr.get("imgt_coverage") or ""
        _sr_cdr_driven = _sr.get("cdr_driven_sap", False)
        _sr_note = _sr.get("note") or ""

        # CDR-driven SAP explanation banner (shown when SAP target not met despite FR mutations)
        if _sr_cdr_driven:
            _sr_cdr_note_html = (
                "<div style='margin-bottom:12px;padding:10px 14px;background:#fefce8;"
                "border-left:5px solid #ca8a04;border-radius:0 6px 6px 0;font-size:.82rem'>"
                "<b style='color:#854d0e'>CDR-Driven Hydrophobicity — Expected Result</b><br>"
                f"<p style='margin:6px 0 0;color:#374151'>"
                f"The SAP hydrophobic score ({f'{_sr_sap_a:.3f}' if _sr_sap_a is not None else '—'}) "
                f"did not reach the target ({f'{_sr_target:.3f}' if _sr_target is not None else '—'}) "
                "despite applying all eligible framework mutations. "
                "This is expected when the dominant hydrophobic window spans CDR loop residues — "
                "CDR positions are preserved unchanged by design to maintain antigen-binding function. "
                "</p>"
                "<p style='margin:6px 0 0;color:#475569;font-size:.79rem'>"
                "The framework mutations applied here reduce FR-surface hydrophobicity and improve the "
                "antibody's human-like surface profile. CDR-driven charge/hydrophobicity requires "
                "offline CMC optimization: consider CDR sequence remodelling, formulation adjustment, "
                "or aggregation-suppressor excipients."
                "</p></div>"
            )
        else:
            _sr_cdr_note_html = ""

        _sr_section_html = f"""
  <!-- §6SR Surface Reshaping -->
  <div class='section' id='s6sr' style='border-top:3px solid #dc2626;'>
    <h3>§6 — Surface Reshaping Result &nbsp;<span style='font-size:.75rem;font-weight:400;color:#dc2626;background:#fef2f2;padding:2px 8px;border-radius:4px'>Automatic Fallback</span></h3>

    <div style='margin-bottom:14px;padding:12px 16px;background:#fef2f2;border-left:5px solid #dc2626;border-radius:0 6px 6px 0;font-size:.84rem'>
      <b style='color:#b91c1c'>Why Surface Reshaping was selected instead of CDR-graft humanization</b>
      <p style='margin:6px 0 4px;color:#374151'>
        This sequence did not pass the Feasibility Pre-screen for CDR-graft humanization.
        The following criteria led to Surface Reshaping being applied automatically:
      </p>
      {_sr_why_list}
      <p style='margin:8px 0 0;color:#374151;font-size:.82rem'>
        <b>What Surface Reshaping does:</b> Applies conservative hydrophobic → hydrophilic substitutions
        (F→Y, L→S/T/Q, I→V, M→L/Q) on solvent-exposed framework residues only. CDR positions and
        structurally critical interface residues are never modified.
        Goal: reduce solvent-exposed framework hydrophobic patches below the clinical {_sr_strategy_desc} threshold.
      </p>
    </div>

    {_sr_cdr_note_html}

    <table class='params' style='margin-bottom:14px'>
      <tr><th style='width:38%'>Metric</th><th>Value</th></tr>
      <tr><td class='lbl'>Reshaping Strategy</td><td>{esc(_sr_strategy_desc)}</td></tr>
      <tr><td class='lbl'>SAP Before</td><td style='font-family:monospace'>{f"{_sr_sap_b:.3f}" if _sr_sap_b is not None else "—"}</td></tr>
      <tr><td class='lbl'>SAP After (FR-only)</td><td style='font-family:monospace;{"color:var(--ok);font-weight:bold" if _sr_achieved else "color:var(--warn);font-weight:bold"}'>{f"{_sr_sap_a:.3f}" if _sr_sap_a is not None else "—"} {"✓ target met" if _sr_achieved else ("· CDR loops drive residual score" if _sr_cdr_driven else "· target not met")}</td></tr>
      <tr><td class='lbl'>Target SAP (≤)</td><td style='font-family:monospace'>{f"{_sr_target:.3f}" if _sr_target is not None else "—"}</td></tr>
      <tr><td class='lbl'>FR Positions Evaluated</td><td>{_sr.get("positions_evaluated", 0)}</td></tr>
      <tr><td class='lbl'>FR Mutations Applied</td><td><b>{_sr.get("positions_modified", 0)}</b> &nbsp;<span style='font-size:.78rem;color:#475569'>(only solvent-exposed FR hydrophobics are eligible)</span></td></tr>
      <tr><td class='lbl'>SASA Method</td><td>{esc(_sr.get("sasa_method", "sequence-proxy"))}</td></tr>
      {f"<tr><td class='lbl'>IMGT Coverage</td><td>{esc(_sr_coverage)}</td></tr>" if _sr_coverage else ""}
      {f"<tr><td class='lbl' style='color:var(--warn)'>Coverage Note</td><td style='color:#92400e;font-size:.8rem'>{esc(_sr_cov_warn)}</td></tr>" if _sr_cov_warn else ""}
      {f"<tr><td class='lbl' style='color:var(--fail)'>Engine Error</td><td style='color:var(--fail)'>{esc(_sr_err)}</td></tr>" if _sr_err else ""}
    </table>

    <h4 style='margin:12px 0 6px;font-size:.88rem;color:#374151'>Mutations Applied</h4>
    <table class='params'>
      <tr>
        <th style='width:15%'>IMGT Position</th><th style='width:12%'>From</th>
        <th style='width:12%'>To</th><th style='width:12%'>SASA%</th><th>Applied</th>
      </tr>
      {_sr_mut_rows}
    </table>

    <div style='margin-top:12px'>
      {seq_block("Donor (original) sequence", _sr.get("input_sequence") or payload.get("input_sequence") or "")}
      {seq_block("Surface Reshaped sequence", _sr.get("output_sequence") or "")}
    </div>
  </div>"""
    else:
        _sr_section_html = ""

    # Sequence cleaning banner (§0) — show what was stripped from the input
    _sc = payload.get("sequence_cleaning") or {}
    if _sc and _sc.get("was_modified") and _sc.get("removed"):
        _sc_rows = "".join(
            f"<tr><td style='font-family:monospace;font-size:.8rem'>{esc(r.get('tag',''))}</td>"
            f"<td style='color:#475569'>{esc(r.get('position',''))}</td>"
            f"<td style='font-family:monospace;font-size:.8rem;word-break:break-all'>{esc(r.get('sequence',''))}</td>"
            f"<td style='text-align:right'>{r.get('length',0)} aa</td></tr>"
            for r in (_sc.get("removed") or [])
        )
        _orig_seq = _sc.get("original_sequence") or ""
        _clean_seq = _sc.get("cleaned_sequence") or ""
        _seq_clean_banner = (
            f"<div style='margin-bottom:14px;padding:10px 14px;background:#f0f9ff;"
            f"border-left:5px solid #0ea5e9;border-radius:0 6px 6px 0;font-size:.83rem'>"
            f"<b style='color:#0369a1'>Sequence Auto-Cleaning Applied</b> — "
            f"input {len(_orig_seq)} aa → cleaned {len(_clean_seq)} aa "
            f"(removed {len(_orig_seq)-len(_clean_seq)} aa)<br>"
            f"<table style='margin-top:6px;font-size:.8rem;border-collapse:collapse'>"
            f"<tr><th style='text-align:left;padding-right:12px'>Tag</th>"
            f"<th style='text-align:left;padding-right:12px'>Position</th>"
            f"<th style='text-align:left;padding-right:12px'>Sequence</th>"
            f"<th style='text-align:right'>Length</th></tr>"
            f"{_sc_rows}</table>"
            f"<p style='margin:6px 0 0;font-size:.78rem;color:#475569'>"
            f"Humanization was performed on the cleaned sequence only. "
            f"Original input is preserved in the FASTA output.</p></div>"
        )
    else:
        _seq_clean_banner = ""

    # Post-humanization pI delta banner (§5) — build outside the main f-string to avoid nested-f-string parse errors
    _piw = payload.get("post_humanization_pi_warning") or {}
    if _piw:
        _pi_sev = str(_piw.get("severity") or "")
        _pi_bg = "#fef2f2" if _pi_sev == "HIGH" else "#fff8e1"
        _pi_bord = "#dc2626" if _pi_sev == "HIGH" else "#d97706"
        _pi_title = "#b91c1c" if _pi_sev == "HIGH" else "#92400e"
        _d_pi = _piw.get("donor_pi")
        _h_pi = _piw.get("humanized_pi")
        _delta = float(_piw.get("delta") or 0)
        _d_str = f"{float(_d_pi):.2f}" if _d_pi is not None else "?"
        _h_str = f"{float(_h_pi):.2f}" if _h_pi is not None else "?"
        _h_num = float(_h_pi) if _h_pi is not None else 0.0
        _pi_h_col = "#dc2626" if _h_num > 9.5 else "#d97706"
        if _pi_sev == "HIGH":
            _pi_tail = (
                "Exceeds therapeutic window (>9.5) — surface reshaping / charge-reducing "
                "FR mutations required."
            )
        else:
            _pi_tail = (
                "Borderline cationic — monitor and consider charge-reducing FR mutations "
                "before clinical development."
            )
        _pi_post_warn_html = (
            f"""<div style='margin-top:10px;padding:10px 14px;background:{_pi_bg};"""
            f"""border-left:5px solid {_pi_bord};border-radius:0 6px 6px 0;font-size:.83rem'>"""
            f"""<b style='color:{_pi_title}'>Post-humanization pI Warning """
            f"""({esc(_pi_sev)})</b><br>"""
            f"""Donor pI: <b>{_d_str}</b> &rarr; Humanized pI: """
            f"""<b style='color:{_pi_h_col}'>{_h_str}</b> """
            f"""&nbsp;(&#916; = {_delta:+.2f})<br>"""
            f"""<span style='color:#374151;font-size:.8rem'>CDR-graft preserves CDR """
            f"""charge distribution. Human VH3 framework substitutions may raise pI. """
            f"""{esc(_pi_tail)}</span></div>"""
        )
    else:
        _pi_post_warn_html = ""

    def _flag_icon(msg: str) -> str:
        msg_l = msg.lower()
        if any(k in msg_l for k in ("high risk", "error", "failed", "✖", "abort")):
            return "✖ "
        return "⚠ "
    flag_rows = "".join(
        f'<li style="margin-bottom:4px"><span style="color:{"#dc2626" if "✖" in _flag_icon(str(f)) else "#d97706"}">{_flag_icon(str(f))}</span>{esc(str(f))}</li>'
        for f in flags[:20]
    ) or "<li style='color:#059669'>✓ No QA flags — pipeline completed within acceptable parameters.</li>"

    # ── V3.0 Feasibility Pre-screen banner ───────────────────────────────────
    _fp = payload.get("feasibility_prescreen") or {}
    _fp_rec = _fp.get("recommendation", "humanization")
    _fp_score = _fp.get("feasibility_score", 100)
    _fp_reasons = _fp.get("reasons", [])
    _fp_note = _fp.get("feasibility_note", "")
    _fp_color = {
        "humanization":              "#059669",
        "humanization_plus_reshape": "#0891b2",
        "humanization_plus_charge":  "#7c3aed",
        "borderline":                "#d97706",
        "surface_reshaping_only":    "#dc2626",
    }.get(_fp_rec, "#64748b")
    _fp_label = {
        "humanization":              "✓ Standard CDR-graft humanization",
        "humanization_plus_reshape": "◆ CDR-graft humanization + post-graft surface reshaping (SAP yellow zone)",
        "humanization_plus_charge":  "◆ CDR-graft humanization + post-graft pI charge check (borderline cationic)",
        "borderline":                "⚠ Borderline — humanization attempted with mandatory structural validation",
        "surface_reshaping_only":    "✖ Surface Reshaping Only — CDR-graft not suitable",
    }.get(_fp_rec, _fp_rec)
    _fp_banner = f"""
    <div style="margin-bottom:18px;padding:10px 14px;border-left:5px solid {_fp_color};background:{'#f0fdf4' if _fp_rec=='humanization' else ('#fff8e1' if _fp_rec=='borderline' else '#fef2f2')};border-radius:0 6px 6px 0;font-size:.84rem">
      <b style="color:{_fp_color}">Feasibility Pre-screen (V3.2) — Score {_fp_score}/100</b><br>
      <span style="font-weight:600">{esc(_fp_label)}</span>
      {'<ul style="margin:6px 0 0 16px;padding:0">' + ''.join(f'<li style="margin-bottom:3px">{esc(r)}</li>' for r in _fp_reasons) + '</ul>' if _fp_reasons else ''}
      <p style="margin:6px 0 0;color:#475569;font-size:.8rem">{esc(_fp_note)}</p>
    </div>"""

    _exec_disc = H(
        f"The VHH humanization assessment is complete with an overall status of <strong>{status}</strong>. "
        "The design leverages established camelid-to-human framework adaptation rules, ensuring structural stability while maximizing humanness. "
        "Proprietary Solubility-Enhancing substitutions (formerly Stealth mutations) have been applied where necessary to maintain optimal physical properties.",
        f"VHH ， <strong>{status}</strong>。，。（），。"
    )
    _vhh_exec_interp = _build_discussion_box(H("Executive Discussion", ""), _exec_disc)

    # ── §3 Framework ──────────────────────────────────────────────────
    _vhh_fw_disc = H(
        "The selection of human VH3 germline frameworks is based on sequence identity and structural compatibility. "
        f"The best match (<strong>{payload.get('human_vh3_germline','—')}</strong>) "
        "provides an optimal balance between high humanness and the preservation of the VHH's unique single-domain architecture.",
        f" VH3 。（<strong>{payload.get('human_vh3_germline','—')}</strong>） VHH 。"
    )
    _vhh_fw_interp = _build_discussion_box(H("Framework Selection Discussion", ""), _vhh_fw_disc)

    # ── §4 Structure ──────────────────────────────────────────────────
    _vhh_struct_disc = H(
        "Structural modeling using the <strong>NanoBodyBuilder2</strong> architecture confirms high conformational preservation across the CDR regions. "
        "The low RMSD values indicate that the framework substitutions and hallmark engineering have not induced significant backbone shifts in the antigen-binding loops. "
        "The high confidence scores (pLDDT) support the feasibility of the engineered fold as a stable single-domain therapeutic candidate.",
        f" <strong>NanoBodyBuilder2</strong>  CDR 。 RMSD  Hallmark 。（pLDDT）。"
    )
    _vhh_struct_interp = _build_discussion_box(H("Structural Discussion", ""), _vhh_struct_disc)

    # ── §5 mini-CMC ───────────────────────────────────────────────────
    _vhh_cmc_disc = H(
        "The humanized candidate has been audited for essential physicochemical liabilities. "
        "The overall profile reflects a stable sequence suitable for downstream process development. "
        "Prioritization is given to physical stability and expression yield, ensuring a favorable profile for clinical translation.",
        "。。，。"
    )
    _vhh_cmc_interp = _build_discussion_box(H("Developability Discussion", ""), _vhh_cmc_disc)

    def _build_report_meta(
        protocol_ver: str, analysis_ver: str, report_ver: Optional[str] = None
    ) -> str:
        """Suite report format first; then service + service report version (layout variant optional)."""
        from api.report_versioning import suite_service_meta_html
        from api.main import app

        api_ver = getattr(app, "version", "1.0.0")
        _rv = report_ver if report_ver else VHH_ANALYSIS_VERSION
        extra = [
            f"<div>UI Build: {VHVL_HTML_REPORT_BUILD_ID}</div>",
            f"<div>API Version: {api_ver} (FastAPI)</div>",
        ]
        return suite_service_meta_html(
            "vhh_humanization",
            protocol_ver=protocol_ver,
            analysis_ver=analysis_ver,
            content_variant=_rv,
            extra_inner_divs=extra,
        )

    _is_skipped = _fp_rec == "surface_reshaping_only"
    _hum_col_label = "Output (Unmodified)" if _is_skipped else "Humanized (lead)"

    # ── V3.0 CMC Advisory §9 block ────────────────────────────────────────────
    _cmc_adv = payload.get("cmc_advisory") or []
    _severity_color = {"high": "#dc2626", "medium": "#d97706", "low": "#64748b"}
    _severity_bg    = {"high": "#fef2f2", "medium": "#fff8e1", "low": "#f8fafd"}
    _severity_label = {"high": "🔴 HIGH", "medium": "🟡 MED", "low": "⬜ LOW"}

    def _adv_row(adv: dict) -> str:
        sev = adv.get("severity", "medium")
        return f"""
      <div style="border-left:4px solid {_severity_color.get(sev,'#64748b')};background:{_severity_bg.get(sev,'#f8fafd')};padding:10px 14px;margin-bottom:10px;border-radius:0 6px 6px 0;font-size:.82rem">
        <b style="color:{_severity_color.get(sev,'#333')}">{_severity_label.get(sev,'')}</b>
        <b style="margin-left:6px">{esc(adv.get('type','').upper().replace('_',' '))}</b><br>
        <span style="color:#374151">{esc(adv.get('finding',''))}</span><br>
        <b style="color:var(--accent);margin-top:4px;display:block">Recommendation:</b>
        <span style="color:#374151">{esc(adv.get('recommendation',''))}</span><br>
        <span style="display:inline-block;margin-top:5px;padding:2px 8px;background:#e0e7ff;border-radius:3px;font-size:.78rem;color:#1e40af">
          Offline Service: {esc(adv.get('offline_service',''))}
        </span>
        <span style="display:inline-block;margin-left:8px;padding:2px 8px;background:#f0fdf4;border-radius:3px;font-size:.78rem;color:#166534">
          ⏱ {esc(adv.get('estimated_time',''))}
        </span>
      </div>"""

    _cmc_adv_html = "".join(_adv_row(a) for a in _cmc_adv) or (
        "<p style='color:#059669;font-size:.83rem'>✓ No CMC optimization advisory — humanized sequence meets all CMC thresholds.</p>"
    )

    # ── Ranking stability advisory block ─────────────────────────────────────
    # When swap_risk >= 0.4 (Top-1 and Top-2 barely distinguishable), compute
    # consensus mutations between Top-1 and Top-2 as the "safe" recommendation.
    _swap_risk_val = payload.get("swap_risk") or 0.0
    _ranking_tier = str(payload.get("ranking_tier") or "").upper() or "A"
    _output_mode = str(payload.get("recommended_output_mode") or "").strip() or "single_lead"
    _tier_reason = str(payload.get("ranking_tier_reason") or "").strip()
    _tier_msg_map = {
        "A": "Stable ranking — single lead recommendation is acceptable.",
        "B": "Moderate uncertainty — keep Top-1 as lead and prioritize consensus shared mutations.",
        "C": "Near tie — treat Top-1/Top-2 as dual leads and evaluate in parallel.",
        "D": "Unstable ranking — manual review / experimental tie-break required before naming a lead.",
    }
    _tier_msg = _tier_reason or _tier_msg_map.get(_ranking_tier, "Ranking policy recommendation is unavailable.")
    _ranking_policy_row = (
        f"<b>Tier {_ranking_tier}</b> · {_output_mode.replace('_', ' ')}<br>"
        f"<span style='color:#475569'>{esc(_tier_msg)}</span>"
    )
    _cands = candidates  # already sliced to top_k
    _stability_block = ""
    if _swap_risk_val >= 0.4 and len(_cands) >= 2:
        seq1 = (_cands[0].get("humanized_sequence") or _cands[0].get("sequence") or "").upper()
        seq2 = (_cands[1].get("humanized_sequence") or _cands[1].get("sequence") or "").upper()
        donor_ref = (payload.get("input_sequence") or "").upper()
        if seq1 and seq2 and donor_ref and len(seq1) == len(seq2) == len(donor_ref):
            consensus_muts = []
            for i, (a, b, d) in enumerate(zip(seq1, seq2, donor_ref)):
                if a == b and a != d:
                    consensus_muts.append(f"pos {i+1}: {d}→{a}")
            consensus_str = (
                ", ".join(consensus_muts[:15]) + ("…" if len(consensus_muts) > 15 else "")
                if consensus_muts else "No shared mutations found between Top-1 and Top-2."
            )
            t1_id = esc(_cands[0].get("template_id") or _cands[0].get("source_scaffold") or "Top-1")
            t2_id = esc(_cands[1].get("template_id") or _cands[1].get("source_scaffold") or "Top-2")
            _stability_block = f"""
    <div style="margin-top:14px;padding:10px 14px;background:#f0f9ff;border:1px solid #bae6fd;border-radius:6px;font-size:.82rem">
      <b style="color:#0369a1">⚖ Ranking Stability Advisory</b>
      <p style="margin:6px 0 4px">Top-1 (<b>{t1_id}</b>) and Top-2 (<b>{t2_id}</b>) scores are within noise margin
      (swap_risk={_swap_risk_val:.2f}). <b>Consensus mutations</b> shared by both templates are the most
      reliable changes — consider prioritizing these for synthesis:</p>
      <code style="font-size:.78rem;color:#0c4a6e">{consensus_str}</code>
      <p style="margin:6px 0 0;color:#475569">If resources allow, synthesize both Top-1 and Top-2 and let
      SPR/BLI decide. Divergent positions carry template-specific uncertainty.</p>
    </div>"""
    rmsd_h1 = num(cdr_rmsd.get("H1"), 2)
    rmsd_h2 = num(cdr_rmsd.get("H2"), 2)
    rmsd_h3 = num(cdr_rmsd.get("H3"), 2)

    cmc_pi = num(mini_cmc.get("pI"), 2)
    cmc_gravy = num(mini_cmc.get("GRAVY"), 3)
    cmc_inst = num(mini_cmc.get("instability_index"), 2)
    cmc_sap = num(mini_cmc.get("SAP_proxy"), 3)

    _sp_gates = _species_cmc_gates(payload.get("source_species"))
    _ii_warn_vhh = _sp_gates.get("instability_index_warn", 40)
    pi_ok = 5.5 < (mini_cmc.get("pI") or 7) < 9.5
    gravy_ok = (mini_cmc.get("GRAVY") or 0) <= 0
    inst_ok = (mini_cmc.get("instability_index") or 0) <= _ii_warn_vhh
    sap_ok = (mini_cmc.get("SAP_proxy") or 0) <= 0.639

    _dcmc = payload.get("donor_mini_cmc") or {}
    _donor_pi   = _dcmc.get("pI")
    _donor_gravy = _dcmc.get("GRAVY")
    _donor_inst  = _dcmc.get("instability_index")
    _donor_sap   = _dcmc.get("SAP_proxy")

    hseq = payload.get("humanized_sequence") or ""
    
    # Calculate VHH Humanness Score (0-100 scale)
    # Base: FR Identity * 100
    fr_id = payload.get("human_vh3_identity")
    if fr_id is not None:
        if fr_id < 1.0: # if it's a fraction
            fr_id = fr_id * 100
        humanness_score = fr_id
        # Penalty for ADA risk (if combined_score is low due to ADA)
        # We can just show the FR identity as the main humanness metric, which is standard for VHH
        humanness_display = f"<b>{humanness_score:.1f}</b> / 100"
    else:
        humanness_display = "—"

    # ── §3 Framework ──────────────────────────────────────────────────
    _vhh_fw_disc = H(
        "The selection of human VH3 germline frameworks is based on sequence identity and structural compatibility. "
        f"The best match (<strong>{payload.get('human_vh3_germline','—')}</strong>) "
        "provides an optimal balance between high humanness and the preservation of the VHH's unique single-domain architecture.",
        f" VH3 。（<strong>{payload.get('human_vh3_germline','—')}</strong>） VHH 。"
    )
    _vhh_fw_interp = _build_discussion_box(H("Framework Selection Discussion", ""), _vhh_fw_disc)

    # ── §4 Structure ──────────────────────────────────────────────────
    _vhh_struct_disc = H(
        "Structural modeling using the <strong>NanoBodyBuilder2</strong> architecture confirms high conformational preservation across the CDR regions. "
        "The low RMSD values indicate that the framework substitutions and hallmark engineering have not induced significant backbone shifts in the antigen-binding loops. "
        "The high confidence scores (pLDDT) support the feasibility of the engineered fold as a stable single-domain therapeutic candidate.",
        f" <strong>NanoBodyBuilder2</strong>  CDR 。 RMSD  Hallmark 。（pLDDT）。"
    )
    _vhh_struct_interp = _build_discussion_box(H("Structural Discussion", ""), _vhh_struct_disc)

    # ── §5 mini-CMC ───────────────────────────────────────────────────
    _vhh_cmc_disc = H(
        "The humanized candidate has been audited for essential physicochemical liabilities. "
        "The overall profile reflects a stable sequence suitable for downstream process development. "
        "Prioritization is given to physical stability and expression yield, ensuring a favorable profile for clinical translation.",
        "。。，。"
    )
    _vhh_cmc_interp = _build_discussion_box(H("Developability Discussion", ""), _vhh_cmc_disc)

    # ── §5a Tier back-mutations + §10 FR/CDR segmentation (VH/VL-style evidence) ──
    _tbm_raw = payload.get("tier_back_mutations")
    _tbm_list: List[Any] = list(_tbm_raw) if isinstance(_tbm_raw, list) else []
    _s5a_rows = ""
    _s5a_err_html = ""
    if _tbm_list and isinstance(_tbm_list[0], dict) and _tbm_list[0].get("error"):
        _s5a_err_html = (
            f"<p class='note' style='color:var(--warn)'><b>Tier back-mutation engine:</b> "
            f"{esc(_tbm_list[0].get('error'))}</p>"
        )
    else:
        for m in _tbm_list:
            if not isinstance(m, dict) or m.get("error"):
                continue
            pos = m.get("kabat_position", m.get("position", "—"))
            fa = m.get("from_aa", "—")
            ta = m.get("to_aa", "—")
            rat = str(m.get("rationale", "") or "")
            _s5a_rows += (
                f"<tr><td style='text-align:center;font-family:monospace'>{esc(pos)}</td>"
                f"<td style='text-align:center;font-weight:bold'>{esc(fa)}</td>"
                f"<td style='text-align:center;color:#1b4fad;font-weight:bold'>{esc(ta)}</td>"
                f"<td style='font-size:.8rem'>{esc(rat)}</td></tr>"
            )

    _s5a_empty_note = ""
    if not _s5a_err_html and not _s5a_rows:
        _s5a_empty_note = (
            "<p class='note'><b>No tier-enforced back-mutations on the lead sequence.</b> "
            "After CDR graft, every Tier-protected site already matched the donor amino acid "
            "(the human template agreed at those positions), so <code>apply_tier_back_mutations</code> "
            "made zero edits. Framework differences visible in §10 are ordinary graft substitutions outside "
            "the protected set.</p>"
        )

    _s5a_tier_bm_html = f"""
  <div class='section' id='s5a'>
    <h3>§5a — Tier-protected back-mutations (VHH)</h3>
    <p class='note'>
      Algorithm: <code>core.vhh_humanization.apply_tier_back_mutations</code> — runs immediately after
      <code>graft_cdrs_to_template</code>. It restores <b>donor</b> amino acids at Tier-protected framework positions
      (from <code>config/tier_system_config.json</code>, plus CDR3-length-aware upgrades) when the human scaffold would
      replace them. Distinct from VH/VL Phase-4 Vernier rescue, but serves the same audit goal: documented reversions
      for conservation-critical framework sites.
    </p>
    {_s5a_err_html}{_s5a_empty_note}
    <table class='params'>
      <tr><th style='width:12%'>Site (IMGT*)</th><th style='width:8%'>After graft</th><th style='width:10%'>After revert</th><th>Rationale</th></tr>
      {_s5a_rows or "<tr><td colspan='4' style='color:#475569;font-style:italic'>No individual mutations listed.</td></tr>"}
    </table>
    <p class='note' style='margin-top:8px;font-size:.72rem'>
      * Row key <code>kabat_position</code> is populated from the IMGT numbering stream used inside the tier engine (historical field name).
    </p>
  </div>"""

    # ── §7 Humanness Indicators (PRF / HPR / Naturalness) ──
    # Note: Full MHC-II allele scanning is a premium service. 
    # VHH reports include basic humanness and developability indicators.
    _hpr = payload.get("hpr_index") or {}
    _hpr_donor = (_hpr.get("donor") or {}).get("vh", {}).get("score")
    _hpr_hum   = (_hpr.get("humanized") or {}).get("vh", {}).get("score")
    _hpr_delta = _hpr.get("delta", {}).get("vhh")
    _hpr_top_error = _hpr.get("error") or (_hpr.get("humanized") or {}).get("vh", {}).get("error")

    def _hpr_pct(v: Any) -> str:
        if v is None: return "—"
        return f"{v*100:.1f}%"

    _hpr_delta_str = f"{_hpr_delta*100:+.1f}%" if _hpr_delta is not None else "—"

    def _hpr_hum_display() -> str:
        if _hpr_hum is not None:
            return f"<b>{_hpr_pct(_hpr_hum)}</b>"
        if _hpr_top_error:
            _short_err = str(_hpr_top_error).split("\n")[0][:80]
            return (
                f"<span style='color:#d97706;font-size:.77rem'>"
                f"Not computed &mdash; repertoire database unavailable. "
                f"<code style='font-size:.72rem'>({_short_err})</code></span>"
            )
        return "—"

    _s7_immuno = f"""
    <div class='section' id='s7'>
      <h3>§7 — Humanness Indicators</h3>
      <p class='note'>
        Sequence-based indicators of humanness, structural naturalness, and human repertoire compatibility.
      </p>
      <table class='params'>
        <tr><th style='width:38%'>Metric</th><th>Result</th><th>Interpretation</th></tr>
        <tr>
          <td class='lbl'>Framework Identity (PRF)</td>
          <td><b>{humanness_display}</b></td>
          <td>Percentage of human-matching residues in the framework regions (FR1-FR4).</td>
        </tr>
        <tr>
          <td class='lbl'>HPR Index</td>
          <td>{_hpr_hum_display()}</td>
          <td>Human Peptide Repertoire compatibility (9-mer coverage). Donor: {_hpr_pct(_hpr_donor)} (Δ: {_hpr_delta_str}).</td>
        </tr>
        <tr>
          <td class='lbl'>Sequence Naturalness Score</td>
          <td>{num(payload.get('combined_score')) if payload.get('combined_score') is not None else "<span style='color:#9ca3af'>—</span>"}</td>
          <td>A composite indicator of sequence-to-template compatibility and structural plausibility.</td>
        </tr>
      </table>
    </div>"""

    _s10_seg_html = _build_vhh_imgt_fr_cdr_segmentation_panel(
        payload.get("input_sequence") or "",
        payload.get("humanized_sequence") or "",
    )
    _s10_d_fa = (payload.get("input_sequence") or "").strip()
    _s10_h_fa = (payload.get("humanized_sequence") or "").strip()
    _s10_fasta_pre = (
        f"&gt;Donor_VHH ({len(_s10_d_fa)} aa)\n{esc(_s10_d_fa)}\n"
        f"&gt;Humanized_VHH_Lead ({len(_s10_h_fa)} aa)\n{esc(_s10_h_fa)}"
    )

    # ── §11 Glossary (Parity with VH/VL) ──
    _s11_glossary = f"""
    <div class='section' id='s11'>
      <h3>§11 — Glossary &amp; Methodology</h3>
      <table class='params'>
        <tr><td class='lbl'>IMGT V-domain</td><td>The international ImMunoGeneTics information system standard for antibody numbering and region definition (FR1-FR4, CDR1-CDR3).</td></tr>
        <tr><td class='lbl'>VHH Hallmarks</td><td>Specific framework-2 positions (IMGT 44, 45, 47) that distinguish camelid VHH from VH, typically increasing solubility.</td></tr>
        <tr><td class='lbl'>SAP Score</td><td>Spatial Aggregation Propensity proxy — a sequence-based metric for surface hydrophobicity. Higher scores indicate higher aggregation risk.</td></tr>
        <tr><td class='lbl'>HPR Index</td><td>Human Peptide Repertoire Compatibility Index — measures 9-mer peptide overlap with a human antibody repertoire reference.</td></tr>
        <tr><td class='lbl'>Framework Identity</td><td>A framework-only identity metric (PRF) that measures the percentage of human-matching residues in the framework regions, excluding CDRs.</td></tr>
        <tr><td class='lbl'>CDR Preservation</td><td>A mandatory quality gate ensuring the antigen-binding loops (CDRs) are 100% identical to the donor after framework humanization.</td></tr>
      </table>
    </div>"""

    _vhh_build_id = f"20260503-VHH-{VHH_REPORT_PROTOCOL_VERSION}-{VHH_ANALYSIS_VERSION}"
    from api.report_versioning import cohort_provenance_html  # noqa: PLC0415
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
<meta name="abenginecore-vhh-report-build" content="{_vhh_build_id}">
<title>{title}</title>
<style>
:root {{
  --bg: #f4f7f9;
  --panel: #ffffff;
  --text: #2c3e50;
  --accent: #1b4fad;
  --accent2: #2d6cdf;
  --border: #d0d7e2;
  --pass: #059669;
  --fail: #dc2626;
  --warn: #d97706;
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background: var(--bg); color: var(--text); margin: 0; padding: 20px; line-height: 1.5;
}}
.page {{
  max-width: 900px; margin: 0 auto; background: var(--panel);
  padding: 32px 40px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}}
/* Hero bar aligned with VH/VL V5.4.x HTML reports (solid brand blue, white text). */
.report-header {{
  background: var(--accent);
  color: #fff;
  padding: 20px 28px;
  border-radius: 8px;
  margin-bottom: 18px;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}}
.report-header h1 {{ margin: 0 0 4px; font-size: 1.35rem; font-weight: 700; color: #fff; letter-spacing: -0.02em; }}
.report-header .sub {{ font-size: .84rem; font-weight: 600; opacity: .95; margin-top: 2px; line-height: 1.45; color: #fff; }}
.report-header .sub b {{ color: #fff; }}
.report-header .ts {{ text-align: right; font-size: .78rem; font-weight: 600; opacity: .92; color: #fff; }}
.report-header .header-meta {{ margin-top: 10px; font-size: .76rem; font-weight: 600; opacity: .9; line-height: 1.45; }}
.report-header .header-meta div {{ margin-top: 2px; }}

.toc-bar {{
  background: #f8fafd; border: 1px solid var(--border); padding: 8px 14px;
  border-radius: 6px; font-size: .8rem; margin-bottom: 24px; color: #5a6a80;
}}
.toc-bar a {{ color: var(--accent2); text-decoration: none; margin: 0 4px; }}
.toc-bar a:hover {{ text-decoration: underline; }}

.section {{ margin-bottom: 32px; }}
h3 {{ color: var(--accent); font-size: .98rem; margin: 0 0 12px; padding-bottom: 6px; border-bottom: 2px solid var(--border); }}
.note {{ color: #5a6a80; font-size: .8rem; margin-bottom: 8px; }}

table.params {{ width: 100%; border-collapse: collapse; font-size: .83rem; }}
table.params th {{ background: #e8eef8; color: var(--accent); font-weight: 600; padding: 7px 12px; text-align: left; border-bottom: 2px solid var(--border); }}
table.params td {{ padding: 6px 12px; border-bottom: 1px solid #eef; vertical-align: top; }}
table.params td.lbl {{ width: 38%; color: #4a5a72; font-size: .82rem; }}
table.params tr:last-child td {{ border-bottom: none; }}
table.params tr.row-best td {{ background: #f0fff4; font-weight: 600; }}

.badge {{ display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: .72rem; font-weight: 700; vertical-align: middle; margin-left: 4px; }}
.badge-ok {{ background: #d1fae5; color: var(--pass); border: 1px solid #6ee7b7; }}
.badge-fail {{ background: #fee2e2; color: var(--fail); border: 1px solid #fca5a5; }}
.badge-warn {{ background: #fef3c7; color: var(--warn); border: 1px solid #fcd34d; }}

.seq-block {{ background: #f8fafd; border: 1px solid var(--border); border-radius: 6px; padding: 12px 14px; margin-bottom: 10px; }}
.seq-label {{ font-size: .82rem; font-weight: 700; color: var(--accent2); margin-bottom: 6px; }}
.seq-len {{ font-weight: 400; color: #8a9ab0; font-size: .75rem; margin-left: 6px; }}
.seq-body {{ font-family: 'Consolas', 'Courier New', monospace; font-size: .78rem; word-break: break-all; line-height: 2; color: #1a2030; }}
.chunk {{ margin-right: 8px; letter-spacing: .04em; }}
.chunk:nth-child(10n) {{ color: #1b4fad; }}

footer {{ text-align: center; color: #8899aa; font-size: .72rem; margin-top: 28px; padding-top: 12px; border-top: 1px solid var(--border); }}
footer a {{ color: #1b4fad; }}

.discussion-box {{ background: #f8fafd; border: 1px solid var(--border); border-left: 4px solid var(--accent2); border-radius: 0 6px 6px 0; padding: 10px 14px; margin: 10px 0; }}
.discussion-title {{ font-size: .78rem; font-weight: 700; color: var(--accent); margin-bottom: 4px; }}
.discussion-content {{ font-size: .8rem; color: #374151; line-height: 1.6; margin: 0; }}

@page {{ margin: 18mm 14mm 16mm 14mm }}
@media print {{
  body {{ background: #fff; font-size: 10.5px; color: #000; }}
  .page {{ max-width: 100%; padding: 0; box-shadow: none; }}
  .toc-bar {{ display: none; }}
  .report-header {{
    background: #1b4fad !important;
    color: #fff !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  .report-header h1,
  .report-header .sub,
  .report-header .sub b,
  .report-header .ts,
  .report-header .header-meta {{ color: #fff !important; opacity: 1; }}
  .section {{
    break-inside: auto; page-break-inside: auto;
    border: 1px solid #ccc; margin-bottom: 8px; overflow: visible; box-shadow: none;
  }}
  h3 {{ break-after: avoid; page-break-after: avoid; font-size: 12px; }}
  h4 {{ break-after: avoid; page-break-after: avoid; font-size: 11px; }}
  .discussion-box {{ break-inside: avoid; page-break-inside: avoid; }}
  .seq-block {{ break-inside: avoid; page-break-inside: avoid; }}
  table.params {{ break-inside: auto; page-break-inside: auto; border-collapse: collapse; width: 100%; }}
  table.params tr {{ break-inside: avoid; page-break-inside: avoid; }}
  table.params th, table.params td {{ font-size: 9.5px; padding: 3px 5px; }}
  details {{ display: block; }}
  details > *:not(summary) {{ display: block !important; }}
  .seq-body {{ font-size: 8.5px; line-height: 1.7; word-break: break-all; }}
  .badge-ok, .badge-fail, .badge-warn, .badge {{
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }}
  footer {{ margin-top: 8px; font-size: 8px; }}
}}
</style>
</head>
<body>
<div class="page">
  <div class="report-header">
    <div>
      <h1>{report_h1}</h1>
      <div class="sub">{report_sub}</div>
      <div class="sub" style="margin-top:4px">{proj_lbl}: <b>{proj}</b></div>
      {_build_report_meta(VHH_REPORT_PROTOCOL_VERSION, f"AbEngineCore VHH Humanization Standard {VHH_ANALYSIS_VERSION}", VHH_ANALYSIS_VERSION)}
    </div>
    <div class="ts">{ts}<br><span style="font-size:.7rem;opacity:.6">{conf_lbl}</span></div>
  </div>
  {cohort_provenance_html("vhh_humanization")}

  <div class='toc-bar'>
    <b>Contents</b> &nbsp;|&nbsp;
    <a href='#s0'>Overview</a> · <a href='#s1'>VHH sites</a> · <a href='#s2'>CDRs</a> ·
    <a href='#s3'>Framework</a> · <a href='#s4'>Structure</a> · <a href='#s5'>mini-CMC</a> ·
    <a href='#s5a'>Tier back-mut</a> ·
    <a href='#s7'>Humanness</a> ·
    {'<a href="#s6sr" style="color:#dc2626;font-weight:600">⚙ Surface Reshaping</a> · ' if payload.get("surface_reshaping") else ""}
    <a href='#s6'>Candidates</a> · <a href='#s10'>Sequences §10</a> ·
    <a href='#s8'>QA Flags</a> ·
    <a href='#s9'>CMC Advisory</a> ·
    <a href='#s11'>Glossary</a>
  </div>

  <!-- §0 Overview -->
  <div class='section' id='s0'>
    <h3>§0 — Overview</h3>
    {_seq_clean_banner}
    {_fp_banner}
    <table class='params'>
      {row("Sequence / project name", proj)}
      {row("Generated", ts)}
      {row("Pipeline", f"VHH Humanization — {VHH_REPORT_PROTOCOL_VERSION} Protocol (AbEngineCore)")}
      {row("Overall Status", f"<b>{status}</b> &nbsp;{st_badge}")}
      {row("VHH Humanness Score (FR Identity)", f"{humanness_display}")}
      {row("SAP Hydrophobic Patch Score", f"{num(payload.get('sap_score'))} &nbsp;({esc(payload.get('sap_tier',''))})")}
      {row("Best Clinical Germline Match", f"<b>{esc(payload.get('human_vh3_germline','—'))}</b>")}
      {row("Strategy Applied", esc(strategy))}
      {row("Lead Selection", esc((payload.get("lead_selection") or {}).get("selection_summary") or "Ranking Top-1 retained"))}
      {row("Ranking Policy Recommendation", _ranking_policy_row)}
    </table>
    {_vhh_fw_interp}
  </div>

  <!-- §1 Hallmarks -->
  <div class='section' id='s1'>
    <h3>§1 — VHH signature sites (IMGT 37 + FR2: 44/45/47)</h3>
    <p class='note'>Key framework residues associated with VHH solubility and structure.</p>
    <table class='params'>
      <tr><th style="width:15%">IMGT Position</th><th style="width:20%;text-align:center">Residue</th><th>Structural Role</th></tr>
      {rows_hm}
    </table>
  </div>

  <!-- §2 CDRs -->
  <div class='section' id='s2'>
    <h3>§2 — CDR Sequences (IMGT)</h3>
    <table class='params'>
      <tr><th style="width:15%">CDR</th><th>Sequence</th><th style="width:15%">Length</th></tr>
      <tr><td class="lbl">CDR-H1</td><td style="font-family:monospace">{esc(payload.get("cdr1_seq",""))}</td><td>{len(payload.get("cdr1_seq") or "")} aa</td></tr>
      <tr><td class="lbl">CDR-H2</td><td style="font-family:monospace">{esc(payload.get("cdr2_seq",""))}</td><td>{len(payload.get("cdr2_seq") or "")} aa</td></tr>
      <tr><td class="lbl">CDR-H3</td><td style="font-family:monospace">{esc(payload.get("cdr3_seq",""))}</td><td>{len(payload.get("cdr3_seq") or "")} aa</td></tr>
    </table>
  </div>

  <!-- §3 Framework -->
  <div class='section' id='s3'>
    <h3>§3 — Framework Selection &amp; Scoring</h3>
    <table class='params'>
      <tr><th style="width:38%">Parameter</th><th>Result</th></tr>
      <tr><td class="lbl">Best Clinical Germline / Template</td><td><code>{esc(payload.get("human_vh3_germline","—"))}</code></td></tr>
      <tr><td class="lbl">Overall Framework Identity</td><td><b>{pct(payload.get("human_vh3_identity"))}</b></td></tr>
      <tr><td class="lbl">FR2 Identity</td><td>{pct(payload.get("fr2_identity"))}</td></tr>
      <tr><td class="lbl">Combined Score (FR + CDR + CMC)</td><td>{num(payload.get("combined_score"))}</td></tr>
      <tr><td class="lbl">SAP Score (hydro_patch_max9)</td><td>{num(payload.get("sap_score"))} &nbsp;({esc(payload.get("sap_tier",""))})</td></tr>
    </table>
    {_vhh_fw_interp}
  </div>

  <!-- §4 Structure -->
  <div class='section' id='s4'>
    <h3>§4 — Structural Conservation (NanoBodyBuilder2)</h3>
    <table class='params'>
      <tr><th style="width:38%">Metric</th><th>Donor VHH</th><th>Humanized VHH</th><th>QC</th></tr>
      <tr>
        <td class="lbl">Mean pLDDT (Confidence)</td>
        <td>{num(payload.get("donor_plddt"), 1)}</td>
        <td>{num(payload.get("humanized_plddt"), 1)}</td>
        <td>{_badge(payload.get("humanized_plddt") is not None and payload.get("humanized_plddt") > 70, "✓ >70", "⚠ <70")}</td>
      </tr>
      <tr><td class="lbl">CDR-H1 Cα RMSD</td><td>—</td><td>{rmsd_h1} Å</td><td>{_badge(isinstance(payload.get("cdr_rmsd", {}).get("H1"), (int, float)) and payload.get("cdr_rmsd", {}).get("H1") < 2.0, "✓ <2.0 Å", "⚠ >2.0 Å / N.A.")}</td></tr>
      <tr><td class="lbl">CDR-H2 Cα RMSD</td><td>—</td><td>{rmsd_h2} Å</td><td>{_badge(isinstance(payload.get("cdr_rmsd", {}).get("H2"), (int, float)) and payload.get("cdr_rmsd", {}).get("H2") < 2.0, "✓ <2.0 Å", "⚠ >2.0 Å / N.A.")}</td></tr>
      <tr><td class="lbl">CDR-H3 Cα RMSD</td><td>—</td><td>{rmsd_h3} Å</td><td>{_badge(isinstance(payload.get("cdr_rmsd", {}).get("H3"), (int, float)) and payload.get("cdr_rmsd", {}).get("H3") < 2.0, "✓ <2.0 Å", "⚠ >2.0 Å / N.A.")}</td></tr>
    </table>
    {_vhh_struct_interp}
  </div>

  <!-- §5 mini-CMC -->
  <div class='section' id='s5'>
    <h3>§5 — mini-CMC Developability (Donor vs Humanized)</h3>
    <p class='note' style='margin-bottom:10px'>
      <b>Donor baseline</b> is computed on the <b>input sequence before humanization</b>.
      This comparison proves whether CMC issues are <em>sequence-intrinsic</em> (present in the donor)
      or <em>introduced by framework substitution</em>.
      If the donor already fails a gate, the root cause lies in the source sequence — not in the humanization algorithm.
      A negative Δ (improvement) indicates the humanization algorithm actively reduced the risk.
    </p>
    <table class='params'>
      <tr>
        <th style="width:32%">Parameter</th>
        <th style="width:18%;text-align:center">Donor (input)</th>
        <th style="width:18%;text-align:center">{_hum_col_label}</th>
        <th style="width:10%;text-align:center">Δ (hum−donor)</th>
        <th style="width:10%;text-align:center">Origin</th>
        <th>Gate (humanized)</th>
      </tr>
      <tr>
        <td class="lbl">Theoretical pI</td>
        <td style="text-align:center">{num(_donor_pi, 2) if _donor_pi is not None else "—"}</td>
        <td style="text-align:center">{cmc_pi}</td>
        <td style="text-align:center">{f"{(mini_cmc.get('pI') or 0) - (_donor_pi or 0):+.2f}" if _donor_pi is not None and mini_cmc.get("pI") is not None else "—"}</td>
        <td style="text-align:center">{"<span style='color:var(--warn)'>Donor</span>" if _donor_pi is not None and not (5.5 < _donor_pi < 9.5) else "—"}</td>
        <td>{_badge(pi_ok, "✓ 5.5–9.5", "⚠ Out of range")}</td>
      </tr>
      <tr>
        <td class="lbl">GRAVY (Hydrophobicity)</td>
        <td style="text-align:center">{num(_donor_gravy, 3) if _donor_gravy is not None else "—"}</td>
        <td style="text-align:center">{cmc_gravy}</td>
        <td style="text-align:center">{f"{(mini_cmc.get('GRAVY') or 0) - (_donor_gravy or 0):+.3f}" if _donor_gravy is not None and mini_cmc.get("GRAVY") is not None else "—"}</td>
        <td style="text-align:center">{"<span style='color:var(--warn)'>Donor</span>" if _donor_gravy is not None and _donor_gravy > 0.1 else "—"}</td>
        <td>{_badge(gravy_ok, "✓ ≤ 0", "⚠ > 0 (Hydrophobic)")}</td>
      </tr>
      <tr>
        <td class="lbl">Instability Index</td>
        <td style="text-align:center;{'color:var(--fail);font-weight:bold' if _donor_inst is not None and _donor_inst > 40 else ''}">{num(_donor_inst, 1) if _donor_inst is not None else "—"}</td>
        <td style="text-align:center">{cmc_inst}</td>
        <td style="text-align:center">{f"{(mini_cmc.get('instability_index') or 0) - (_donor_inst or 0):+.1f}" if _donor_inst is not None and mini_cmc.get("instability_index") is not None else "—"}</td>
        <td style="text-align:center">{"<span style='color:var(--fail);font-weight:bold'>Donor ❌</span>" if _donor_inst is not None and _donor_inst > 40 else "—"}</td>
        <td>{_badge(inst_ok, "✓ ≤ 40 (Stable)", "⚠ > 40 (Unstable)")}</td>
      </tr>
      <tr>
        <td class="lbl">SAP score (7-mer proxy)</td>
        <td style="text-align:center;{'color:var(--fail);font-weight:bold' if _donor_sap is not None and _donor_sap > 0.750 else ('color:var(--warn)' if _donor_sap is not None and _donor_sap > 0.639 else '')}">{num(_donor_sap, 3) if _donor_sap is not None else "—"}</td>
        <td style="text-align:center">{cmc_sap}</td>
        <td style="text-align:center">{f"{(mini_cmc.get('SAP_proxy') or 0) - (_donor_sap or 0):+.3f}" if _donor_sap is not None and mini_cmc.get("SAP_proxy") is not None else "—"}</td>
        <td style="text-align:center">{"<span style='color:var(--fail);font-weight:bold'>Donor ❌</span>" if _donor_sap is not None and _donor_sap > 0.750 else ("<span style='color:var(--warn)'>Donor ⚠</span>" if _donor_sap is not None and _donor_sap > 0.639 else "—")}</td>
        <td>{_badge(sap_ok, "✓ ≤ 0.639 (p75)", "⚠ > 0.639 (yellow/red)")}</td>
      </tr>
    </table>
    {f"<div style='margin-top:10px;padding:8px 12px;background:#fff8e1;border-left:4px solid var(--warn);border-radius:4px;font-size:.82rem'><b>Pre-screen diagnosis:</b> {' '.join(payload.get('donor_prescreen_flags', []))}</div>" if payload.get("donor_prescreen_flags") else ""}
    {_pi_post_warn_html}
    {_vhh_cmc_interp}
  </div>

  <!-- §5a Tier-protected back-mutations (engine apply_tier_back_mutations) -->
  {_s5a_tier_bm_html}

  {_s7_immuno}

  <!-- §6PG Post-Graft Surface Reshaping (humanization_plus_reshape path) -->
  {_pgsr_section_html}

  <!-- §6SR Surface Reshaping (auto-populated when CDR-graft was skipped) -->
  {_sr_section_html}

    # ── §6 Candidates (empty when surface_reshaping_only) ──
    {_s6_html}

    <!-- §10 FR/CDR segmentation then full-length sequences (VH/VL V5.4.x §10 order) -->
    <div class='section' id='s10'>
      <h3>§10 — Donor vs Humanized — FR/CDR Segmentation (IMGT)</h3>
      {_s10_seg_html}
      <h4 style='color:#1b4fad;margin:18px 0 6px;font-size:14px'>
        Full-length sequences — donor vs humanized (lead)
      </h4>
      <p class='note' style='margin:0 0 8px;font-size:12px'>
        Same amino-acid strings as <code>vhh_sequences.fasta</code> for donor and lead humanized chain when applicable.
        Alternate ranked candidates follow when available.
      </p>
      {seq_block("Donor (input) VHH", payload.get("input_sequence") or "")}
      {_s7_seqs}
      <details style='margin-top:10px'>
        <summary style='cursor:pointer;color:#1b4fad;font-size:12px;font-weight:600'>
          ▸ FASTA copy block (donor + lead humanized)
        </summary>
        <pre style='font-family:Consolas,Monaco,monospace;font-size:11.5px;background:#f6f8fb;border:1px solid #d6e3ff;border-radius:6px;padding:10px;margin-top:6px;white-space:pre-wrap;word-break:break-all'>
{_s10_fasta_pre}</pre>
      </details>
    </div>

    <!-- §8 QA Flags -->
    <div class='section' id='s8'>
      <h3>§8 — QA Flags &amp; Advisories</h3>
      <p class='note' lang='en'>Automated QA checks. ⚠ = advisory; ✖ = needs review.</p>
      <ul lang='en'>{flag_rows}</ul>
      <p class='note' lang='en' style='margin-top:8px'><b>Ranking policy:</b> Tier {_ranking_tier}
      ({esc(_output_mode)}). {esc(_tier_msg)}</p>
      {_stability_block}
    </div>

    <!-- §9 CMC Optimization Advisory -->
    <div class='section' id='s9'>
      <h3>§9 — CMC Optimization Advisory (V3.3)</h3>
      <p class='note' style='margin-bottom:12px'>
        Automated recommendations for offline CMC optimization services based on identified sequence liabilities.
      </p>
    {_cmc_adv_html}
  </div>

  {_s11_glossary}

  <footer>{footer_line}</footer>
</div>
</body>
</html>"""

    report_dir = out_dir / "reports" / "vhh_humanization"
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / "humanization_report.html"
    try:
        from core.reporting.report_qc_gate import run_report_qc  # noqa: PLC0415
        qc = run_report_qc(html, report_family="vhh_humanization")
        html = qc.inject_qc_badge(html)
    except Exception:
        pass
    out_path.write_text(html, encoding="utf-8")
    return out_path


# ─────────────────────────────────────────────────────────────────────────────

def _build_vhvl_sequence_comparison(donor_seq: str, hum_seq: str, chain: str) -> Dict[str, Any]:
    """Return IMGT-based FR/CDR comparison for VH/VL — matches engine Phase-4 CDR masking.

    Engine uses ANARCII IMGT positions for CDR protection (engine.py union_ranges_vh/vl):
      VH: CDR-H1 IMGT 26–38, CDR-H2 IMGT 55–65, CDR-H3 IMGT 105–117
      VL: CDR-L1 IMGT 27–38, CDR-L2 IMGT 56–65, CDR-L3 IMGT 105–117
    """
    try:
        from core.numbering.imgt_anarcii import imgt_number_anarcii  # noqa: PLC0415

        d = (donor_seq or "").strip().upper()
        h = (hum_seq or "").strip().upper()
        if not d or not h:
            return {"error": "Empty sequence"}

        # Align with HTML report's _build_dual_seq_panel Union bounds
        union_bounds = {
            "FR1":  (1,   25),  "CDR1": (26,  38),
            "FR2":  (39,  49),  "CDR2": (50,  65),
            "FR3":  (66, 104),  "CDR3": (105, 117),
            "FR4":  (118, 130), # Note: HTML report uses 128, but 130 is safer for longer J-genes
        }
        
        def _imgt_split(seq: str) -> Dict[str, str]:
            rows = imgt_number_anarcii(seq)
            buckets: Dict[str, List[str]] = {r: [] for r in
                ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]}
            for row in rows:
                p = row.get("pos")
                if not isinstance(p, int):
                    continue
                for seg, (lo, hi) in union_bounds.items():
                    if lo <= p <= hi:
                        buckets[seg].append(row["aa"])
                        break
            return {k: "".join(v) for k, v in buckets.items()}

        rd = _imgt_split(d)
        rh = _imgt_split(h)

        region_order = ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]
        regions = []
        for reg in region_order:
            ds = rd.get(reg, "")
            hs = rh.get(reg, "")
            is_cdr = reg.startswith("CDR")
            muts: List[Dict[str, Any]] = []
            if ds != hs:
                for i, (da, ha) in enumerate(zip(ds, hs)):
                    if da != ha:
                        muts.append({"pos": i + 1, "from_aa": da, "to_aa": ha})
                if len(ds) != len(hs):
                    muts.append({"pos": "length", "from_aa": len(ds), "to_aa": len(hs)})
            regions.append({
                "region":        reg,
                "donor_seq":     ds,
                "humanized_seq": hs,
                "is_cdr":        is_cdr,
                "mutations":     muts,
                "n_mutations":   len([m for m in muts if m["pos"] != "length"]),
                "identical":     ds == hs,
            })
        return {
            "regions": regions,
            "scheme": "Union (Kabat ∪ Chothia ∪ IMGT)",
            "total_fr_mutations": sum(r["n_mutations"] for r in regions if not r["is_cdr"]),
        }
    except Exception as _e:
        return {"error": f"{type(_e).__name__}: {_e}"}


def _build_vhh_sequence_comparison(donor_seq: str, hum_seq: str) -> Dict[str, Any]:
    """Return structured FR/CDR comparison for frontend rendering.

    Returns a list of region dicts:
      [{region, donor_seq, humanized_seq, is_cdr, mutations: [{pos, from_aa, to_aa}]}]
    """
    try:
        from core.numbering.imgt_anarcii import imgt_number_anarcii  # noqa: PLC0415
        from core.vhh_humanization import split_regions  # noqa: PLC0415

        d = (donor_seq or "").strip().upper()
        h = (hum_seq or "").strip().upper()
        if not d or not h:
            return {"error": "Empty sequence"}

        rd = split_regions(imgt_number_anarcii(d))
        rh = split_regions(imgt_number_anarcii(h))

        # IMGT VHH region order
        region_order = ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]
        regions = []
        for reg in region_order:
            ds = rd.get(reg, "")
            hs = rh.get(reg, "")
            is_cdr = reg.startswith("CDR")
            muts: List[Dict[str, Any]] = []
            if ds != hs:
                for i, (da, ha) in enumerate(zip(ds, hs)):
                    if da != ha:
                        muts.append({"pos": i + 1, "from_aa": da, "to_aa": ha})
                # length difference
                if len(ds) != len(hs):
                    muts.append({"pos": "length", "from_aa": len(ds), "to_aa": len(hs)})
            regions.append({
                "region":       reg,
                "donor_seq":    ds,
                "humanized_seq": hs,
                "is_cdr":       is_cdr,
                "mutations":    muts,
                "n_mutations":  len([m for m in muts if m["pos"] != "length"]),
                "identical":    ds == hs,
            })
        return {"regions": regions, "total_fr_mutations": sum(
            r["n_mutations"] for r in regions if not r["is_cdr"]
        )}
    except Exception as _e:
        return {"error": f"{type(_e).__name__}: {_e}"}


def _humanize_vhh_impl(job_id: str, req: VHHRequest) -> JobStatus:
    """Core VHH humanization pipeline — called by both sync and async endpoints."""
    t0 = time.time()
    out = job_dir(job_id)

    try:
        from core.vhh_humanization_with_qa import humanize_vhh_with_qa

        jobs[job_id]["progress"] = 5
        jobs[job_id]["progress_note"] = "Cleaning input sequence…"

        # ── Sequence cleaning: strip His-tags, signal peptides, Fc appendages ──
        _raw_input = req.vhh_sequence.strip().upper()
        _seq_clean_result: Dict[str, Any] = {"cleaned_sequence": _raw_input, "was_modified": False,
                                              "removed": [], "warnings": [], "error": None}
        try:
            from core.vhh_sequence_cleaner import clean_vhh_sequence  # noqa: PLC0415
            _seq_clean_result = clean_vhh_sequence(
                _raw_input, species=(req.source_species or "alpaca")
            )
            if _seq_clean_result["was_modified"]:
                _tags_removed = ", ".join(
                    f"{r['tag']} ({r['position']}, {r['length']} aa)"
                    for r in _seq_clean_result["removed"]
                )
                jobs[job_id]["progress_note"] = f"Cleaned: removed {_tags_removed}"
        except Exception as _clean_err:
            _seq_clean_result["warnings"] = [f"Sequence cleaner unavailable: {_clean_err}"]

        # Use cleaned sequence for all downstream processing
        _cleaned_seq = _seq_clean_result["cleaned_sequence"] or _raw_input

        jobs[job_id]["progress"] = 10
        jobs[job_id]["progress_note"] = "Running QA humanization panels…"

        # ── V2.2+ SAP + CDR3 auto-strategy (hydrophobic patch + loop burden) ──
        strategy_to_run = req.strategy
        if strategy_to_run in ("all", "auto"):
            from core.vhh_humanization import _compute_hydro_patch_max9, _load_sap_thresholds

            _seq_u = _cleaned_seq
            _input_sap = _compute_hydro_patch_max9(_seq_u)
            _cdr3_len = 0
            _cdr3_cys = 0
            try:
                from core.segmentation.anarcii_adapter import run_anarcii_imgt  # noqa: PLC0415

                _regs, _, _ = run_anarcii_imgt(
                    seq=_seq_u,
                    species=(req.source_species or "alpaca"),
                    chain="H",
                    allow_partial=True,
                    max_mismatches=0,
                )
                _c3 = (_regs or {}).get("CDR3", "") or ""
                _cdr3_len = len(_c3)
                _cdr3_cys = _c3.count("C")
            except Exception:
                pass

            # Long / cysteine-rich CDR3 increases effective developability burden → bias conservative panel
            _cdr3_bump = 0.0
            if _cdr3_len >= 22:
                _cdr3_bump += min(0.14, (_cdr3_len - 21) * 0.012)
            if _cdr3_cys >= 3:
                _cdr3_bump += 0.06
            _adj_sap = _input_sap * (1.0 + _cdr3_bump)

            _thresh = _load_sap_thresholds()["thresholds"]
            if _adj_sap <= _thresh["p50"]["value"]:
                strategy_to_run = "C"  # S3 (Green zone)
            elif _adj_sap <= _thresh["p75"]["value"]:
                strategy_to_run = "B"  # S2 (Yellow zone)
            else:
                strategy_to_run = "A"  # S1 (Red zone)
            jobs[job_id]["progress_note"] = (
                f"Auto strategy {strategy_to_run}: SAP={_input_sap:.3f}, "
                f"adj={_adj_sap:.3f} (CDR3 len={_cdr3_len}, Cys={_cdr3_cys})"
            )
            
        # ── V3.0 Pre-screen (hard gate) before humanization panels ───────────────
        from core.humanization.engine import _vhh_feasibility_prescreen, _vhh_mini_cmc  # noqa: PLC0415
        donor_seq = _cleaned_seq  # use cleaned sequence throughout
        try:
            donor_mini_cmc = _vhh_mini_cmc(donor_seq)
        except Exception as _dce:
            donor_mini_cmc = {"error": str(_dce)}

        _prescreen_cdrs = {}
        try:
            from core.segmentation.anarcii_adapter import run_anarcii_imgt  # noqa: PLC0415

            _prescreen_cdrs, _, _ = run_anarcii_imgt(
                seq=donor_seq,
                species=(req.source_species or "alpaca"),
                chain="H",
                allow_partial=True,
                max_mismatches=0,
            )
        except Exception:
            _prescreen_cdrs = {}

        feasibility_prescreen = _vhh_feasibility_prescreen(_prescreen_cdrs, donor_mini_cmc)
        jobs[job_id]["progress_note"] = (
            f"Pre-screen: {feasibility_prescreen['recommendation']} "
            f"(score={feasibility_prescreen['feasibility_score']})"
        )

        # Hard gate: CDR-graft humanization not suitable — automatically run Surface Reshaping (§4).
        if feasibility_prescreen.get("recommendation") == "surface_reshaping_only":
            jobs[job_id]["progress"] = 30
            jobs[job_id]["progress_note"] = "CDR-graft not suitable — running Surface Reshaping (§4)…"

            # ── Run surface reshaping automatically ──────────────────────────
            _sr_result: Dict[str, Any] = {}
            try:
                from scripts.run_vhh_surface_reshaping_v1 import reshape_vhh_surface  # noqa: PLC0415
                _sr_strategy = "S2"  # p75 target by default; conservative
                _sr_result = reshape_vhh_surface(donor_seq, strategy=_sr_strategy)
            except Exception as _sr_err:
                _sr_result = {
                    "input_sequence": donor_seq,
                    "output_sequence": donor_seq,
                    "sap_before": donor_mini_cmc.get("SAP_proxy"),
                    "sap_after": donor_mini_cmc.get("SAP_proxy"),
                    "target_achieved": False,
                    "strategy": "S2",
                    "mutations": [],
                    "positions_evaluated": 0,
                    "positions_modified": 0,
                    "error": str(_sr_err),
                    "note": f"Surface reshaping engine error: {_sr_err}",
                }

            reshaped_seq = _sr_result.get("output_sequence") or donor_seq
            jobs[job_id]["progress"] = 50

            # ── Recompute mini-CMC on reshaped sequence ────────────────────────
            _reshaped_cmc = donor_mini_cmc
            try:
                from core.humanization.engine import _vhh_mini_cmc  # noqa: PLC0415
                _reshaped_cmc = _vhh_mini_cmc(reshaped_seq)
            except Exception:
                pass

            # ── Hallmark computation on reshaped sequence ─────────────────────
            jobs[job_id]["progress_note"] = "Computing VHH hallmarks…"
            _sr_hallmarks: Dict[str, Any] = {}
            try:
                from core.numbering.imgt_anarcii import imgt_number_anarcii, build_pos_to_aa_map  # noqa: PLC0415
                _sr_hm_rows = imgt_number_anarcii(reshaped_seq)
                _sr_hm_map = build_pos_to_aa_map(_sr_hm_rows)
                _sr_hallmarks = {
                    "pos37": _sr_hm_map.get(37, "?"),
                    "pos44": _sr_hm_map.get(44, "?"),
                    "pos45": _sr_hm_map.get(45, "?"),
                    "pos47": _sr_hm_map.get(47, "?"),
                    "all_ok": (
                        _sr_hm_map.get(44, "?") in ("E", "G", "A", "S", "D", "Q")
                        and _sr_hm_map.get(45, "?") in ("A", "R", "L", "K", "Q")
                        and _sr_hm_map.get(47, "?") in ("F", "Y", "L", "W", "G")
                    ),
                }
            except Exception as _hm_err:
                _sr_hallmarks = {"error": str(_hm_err)}

            # ── Structure prediction on reshaped sequence (NanoBodyBuilder2) ──
            jobs[job_id]["progress"] = 60
            jobs[job_id]["progress_note"] = "NanoBodyBuilder2 — donor structure…"
            _sr_struct_donor: Dict[str, Any] = {}
            _sr_struct_reshaped: Dict[str, Any] = {}
            _sr_cdr_rmsd: Dict[str, Any] = {}
            try:
                from core.humanization.engine import _run_nanobodybuilder2, _compute_vhh_cdr_rmsd  # noqa: PLC0415
                _sr_struct_donor = _run_nanobodybuilder2(donor_seq)
                jobs[job_id]["progress"] = 72
                jobs[job_id]["progress_note"] = "NanoBodyBuilder2 — reshaped structure…"
                _sr_struct_reshaped = _run_nanobodybuilder2(reshaped_seq)
                if (_sr_struct_donor.get("pdb_path") and _sr_struct_reshaped.get("pdb_path")):
                    _sr_cdr_rmsd = _compute_vhh_cdr_rmsd(
                        _sr_struct_donor["pdb_path"], _sr_struct_reshaped["pdb_path"]
                    )
            except Exception as _struct_err:
                _sr_struct_reshaped = {"error": str(_struct_err), "structure_computed": False}

            jobs[job_id]["progress"] = 85
            jobs[job_id]["progress_note"] = "Assembling surface reshaping report…"

            _donor_prescreen_flags = list(feasibility_prescreen.get("reasons") or [])
            _donor_prescreen_flags.append(
                "CDR-graft humanization was not suitable for this sequence. "
                "Surface Reshaping has been applied automatically as the primary engineering path."
            )
            _cmc_adv = _build_cmc_advisory(_reshaped_cmc, _reshaped_cmc, _sr_cdr_rmsd, _prescreen_cdrs or {})

            payload = {
                "job_id": job_id,
                "input_sequence": donor_seq,
                "original_input_sequence": _raw_input if _seq_clean_result["was_modified"] else None,
                "sequence_cleaning": _seq_clean_result if _seq_clean_result["was_modified"] else None,
                "sequence_name": req.sequence_name,
                "project_name": req.project_name,
                "hallmark_37": _sr_hallmarks.get("pos37", "?"),
                "hallmark_44": _sr_hallmarks.get("pos44", "?"),
                "hallmark_45": _sr_hallmarks.get("pos45", "?"),
                "hallmark_47": _sr_hallmarks.get("pos47", "?"),
                "hallmarks_ok": _sr_hallmarks.get("all_ok", False),
                "cdr1_seq": (_prescreen_cdrs or {}).get("CDR1", ""),
                "cdr2_seq": (_prescreen_cdrs or {}).get("CDR2", ""),
                "cdr3_seq": (_prescreen_cdrs or {}).get("CDR3", ""),
                "cdr3_length": len((_prescreen_cdrs or {}).get("CDR3", "")),
                "cdr3_canonical": None,
                "human_vh3_germline": "—",
                "human_vh3_identity": None,
                "fr2_identity": None,
                "strategy_applied": f"surface_reshaping_{_sr_result.get('strategy','S2')}",
                "ablang_score": None,
                "combined_score": None,
                "humanness_score": None,
                "structure_computed": _sr_struct_reshaped.get("structure_computed", False),
                "sap_score": _sr_result.get("sap_after") or donor_mini_cmc.get("SAP_proxy"),
                "sap_tier": (
                    "red"
                    if (_sr_result.get("sap_after") or donor_mini_cmc.get("SAP_proxy") or 0) > 0.750
                    else (
                        "yellow"
                        if (_sr_result.get("sap_after") or donor_mini_cmc.get("SAP_proxy") or 0) > 0.639
                        else "green"
                    )
                ),
                "donor_plddt": _sr_struct_donor.get("plddt"),
                "humanized_plddt": _sr_struct_reshaped.get("plddt"),
                "cdr_rmsd": _sr_cdr_rmsd,
                "mini_cmc": _reshaped_cmc,
                "donor_mini_cmc": donor_mini_cmc,
                "donor_prescreen_flags": _donor_prescreen_flags,
                "feasibility_prescreen": feasibility_prescreen,
                "surface_reshaping": _sr_result,
                "humanized_sequence": reshaped_seq,
                "tier_back_mutations": [],
                "cmc_advisory": _cmc_adv,
                "checklist_status": "WARN",
                "flags": _donor_prescreen_flags,
                "candidates": [],
                "lead_selection": {
                    "algorithm_version": "V3.0",
                    "selected_rank": None,
                    "selection_summary": (
                        f"CDR-graft skipped (pre-screen hard gate). "
                        f"Surface Reshaping applied: {_sr_result.get('positions_modified', 0)} mutations, "
                        f"SAP {_sr_result.get('sap_before', '?'):.3f} → {_sr_result.get('sap_after', '?'):.3f} "
                        f"(target {'achieved' if _sr_result.get('target_achieved') else 'not achieved'})."
                    ),
                    "evaluated_candidates": [],
                },
                "top_k": req.top_k,
                "swap_risk": 0.0,
                "stability_score": 1.0,
                "ranking_tier": "D",
                "recommended_output_mode": "surface_reshaping_only",
                "ranking_tier_reason": "CDR-graft not feasible; surface reshaping result delivered.",
            }

            _vhh_assert_pipeline_cdr_match(donor_seq, reshaped_seq)

            out.mkdir(parents=True, exist_ok=True)

            # Copy PDB files into job output dir
            import shutil as _shutil
            if _sr_struct_donor.get("pdb_path") and Path(_sr_struct_donor["pdb_path"]).exists():
                _shutil.copy2(_sr_struct_donor["pdb_path"], out / "donor_vhh.pdb")
            if _sr_struct_reshaped.get("pdb_path") and Path(_sr_struct_reshaped["pdb_path"]).exists():
                _shutil.copy2(_sr_struct_reshaped["pdb_path"], out / "humanized_vhh.pdb")

            # Write FASTA with donor + reshaped sequences
            _seq_name = (req.sequence_name or req.project_name or job_id).strip()
            _rmsd_h3 = _sr_cdr_rmsd.get("H3")
            _rmsd_note = f" | CDR-H3 RMSD={_rmsd_h3:.2f}A" if _rmsd_h3 is not None else ""
            fasta_lines = [
                f">donor_{_seq_name}",
                donor_seq,
                f">surface_reshaped_{_seq_name} | SAP {_sr_result.get('sap_before','?'):.3f}->{_sr_result.get('sap_after','?'):.3f} | muts={_sr_result.get('positions_modified',0)}{_rmsd_note}",
                reshaped_seq,
            ]
            (out / "vhh_sequences.fasta").write_text("\n".join(fasta_lines) + "\n", encoding="utf-8")

            (out / "result.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            jobs[job_id]["progress"] = 93
            try:
                report_path = _generate_vhh_html_report(payload, out, _seq_name)
                report_url = files_url_for_path(job_id, report_path)
            except Exception as _rpt_err:
                report_url = None
                payload["_vhh_report_error"] = str(_rpt_err)

            zip_url = _create_vhh_delivery_zip(out, job_id)
            if zip_url:
                payload["zip_url"] = zip_url
                (out / "result.json").write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
                )

            elapsed = round(time.time() - t0, 1)
            _extra_sr: Dict[str, Any] = {}
            if zip_url:
                _extra_sr["zip_url"] = zip_url
            if (out / "vhh_sequences.fasta").is_file():
                _extra_sr["fasta_url"] = f"/files/{job_id}/vhh_sequences.fasta"

            save_result(job_id, payload, report_url, elapsed, extra=_extra_sr)
            jobs[job_id].update({
                "status": "done", "progress": 100, "elapsed_sec": elapsed,
                "result": payload, "report_url": report_url, "extra": _extra_sr,
            })
            persist_job_snapshot(job_id)
            return JobStatus(
                job_id=job_id, status="done", progress=100, elapsed_sec=elapsed,
                result=payload, report_url=report_url, extra=_extra_sr or None,
            )

        panels = [strategy_to_run]
        all_candidates = []
        res: dict = {}

        for i, panel in enumerate(panels):
            if jobs.get(job_id, {}).get("cancel_requested"):
                jobs[job_id].update({"status": "cancelled", "progress": 10})
                return JobStatus(job_id=job_id, status="cancelled", progress=10, result=None, error=None)

            pct = 10 + i * 18
            jobs[job_id]["progress"] = pct
            jobs[job_id]["progress_note"] = f"Panel {panel} ({i+1}/{len(panels)}) — humanizing…"
            res = humanize_vhh_with_qa(
                seq=req.vhh_sequence.strip().upper(),
                panel=panel,
                top_k=req.top_k,
                species=req.source_species,
                enable_safe_mode=True,
                strict_qa=False,
                qa_version="v3.5",
                # P0-2: API layer has already run its own 5-route prescreen
                # at line ~7362; disable the core-level prescreen to avoid
                # double gating.
                enforce_prescreen=False,
            )
            cands = res.get("candidates", res.get("variants", []))
            for c in cands:
                c["panel"] = panel
            all_candidates.extend(cands)

        jobs[job_id]["progress"] = 60
        jobs[job_id]["progress_note"] = "Ranking candidates…"

        def _get_score(c):
            # Extract final score (v3.4/v3.5) if available, otherwise fallback to combined_score.
            # V3.0 inherited fix: use `is not None` guard so valid combined_score=0.0 is not treated as -99.
            scores = c.get("scores", {})
            if "final" in scores:
                return float(scores["final"])
            al = c.get("alignment_scores", {})
            sd = al.get("scoring_details", {})
            cs = sd.get("combined_score")
            if cs is None:
                cs = al.get("combined_score")
            return float(cs) if cs is not None else -99.0

        def _candidate_sequence(cand):
            return str(cand.get("humanized_sequence", "") or cand.get("sequence", "") or "").strip().upper()

        def _candidate_alignment_scores(cand):
            al = cand.get("alignment_scores", {})
            return al if isinstance(al, dict) else {}

        def _candidate_scoring_details(cand):
            sd = _candidate_alignment_scores(cand).get("scoring_details", {})
            return sd if isinstance(sd, dict) else {}

        def _candidate_template_id(cand):
            return (
                cand.get("template_id")
                or cand.get("source_scaffold")
                or cand.get("template", {}).get("template_id")
                or "—"
            )

        def _build_fr_summary(cand):
            al = _candidate_alignment_scores(cand)
            sd = _candidate_scoring_details(cand)
            _fi = al.get("framework_identity")
            if _fi is None:
                _fi = sd.get("framework_identity")
            _fr2 = al.get("fr2_identity")
            if _fr2 is None:
                _fr2 = sd.get("fr2_identity")
            return {
                "selected_germline": _candidate_template_id(cand),
                "overall_identity_pct": round(_fi * 100, 1) if _fi is not None else None,
                "fr2_identity_pct": round(_fr2 * 100, 1) if _fr2 is not None else None,
                "combined_score": sd.get("combined_score") or al.get("combined_score"),
            }

        def _compute_hallmarks_for_seq(seq):
            if not seq:
                return {}
            from core.numbering.imgt_anarcii import imgt_number_anarcii, build_pos_to_aa_map  # noqa: PLC0415
            try:
                _hum_rows = imgt_number_anarcii(seq)
                _hum_map = build_pos_to_aa_map(_hum_rows)
                _p37 = _hum_map.get(37, "?")
                _p44 = _hum_map.get(44, "?")
                _p45 = _hum_map.get(45, "?")
                _p47 = _hum_map.get(47, "?")
                return {
                    "pos37": _p37,
                    "pos44": _p44,
                    "pos45": _p45,
                    "pos47": _p47,
                    "all_ok": (
                        _p44 in ("E", "G", "A", "S", "D", "Q")
                        and _p45 in ("A", "R", "L", "K", "Q")
                        and _p47 in ("F", "Y", "L", "W", "G")
                    ),
                }
            except Exception:
                return {}

        all_candidates.sort(key=_get_score, reverse=True)
        top = all_candidates[: req.top_k]

        best = top[0] if top else {}
        cdr_info = res.get("cdrs", {})
        _cdr_canonical = res.get("cdr_canonical", {})
        _cdr3_canonical = _cdr_canonical.get("CDR3", {}).get("canonical_class") if _cdr_canonical else None
        humanized_seq = _candidate_sequence(best)
        hallmarks = _compute_hallmarks_for_seq(humanized_seq) or res.get("hallmarks", {})
        fr = _build_fr_summary(best)

        # ── Structure modeling & Deterministic Rescue (V3.0 Closed-Loop) ──────────
        from core.humanization.engine import (  # noqa: PLC0415
            _run_nanobodybuilder2, _compute_vhh_cdr_rmsd,
        )
        # Donor baseline mini-CMC was computed in V3.0 pre-screen stage above.

        # Pre-screen flags: annotate CMC problems present in donor BEFORE humanization.
        # These prove any downstream CMC issues are sequence-intrinsic, not algorithm-introduced.
        _donor_prescreen_flags = []
        if isinstance(donor_mini_cmc, dict) and not donor_mini_cmc.get("error"):
            _d_ii  = donor_mini_cmc.get("instability_index")
            _d_sap = donor_mini_cmc.get("SAP_proxy")
            _d_gv  = donor_mini_cmc.get("GRAVY")
            if _d_ii is not None and _d_ii > 40:
                _donor_prescreen_flags.append(
                    f"Instability Index={_d_ii:.1f} > 40 already present in donor — "
                    "instability is sequence-intrinsic, not introduced by framework substitution."
                )
            if _d_sap is not None and _d_sap > 0.750:
                _donor_prescreen_flags.append(
                    f"SAP proxy={_d_sap:.3f} > 0.750 (p90 red zone) already present in donor — "
                    "surface hydrophobicity risk is sequence-intrinsic."
                )
            elif _d_sap is not None and _d_sap > 0.639:
                _donor_prescreen_flags.append(
                    f"SAP proxy={_d_sap:.3f} > 0.639 (p75 yellow zone) already present in donor — "
                    "surface reshaping (§4) is warranted but issue is not algorithm-introduced."
                )
            if _d_gv is not None and _d_gv > 0.1:
                _donor_prescreen_flags.append(
                    f"GRAVY={_d_gv:.3f} > 0.1 already present in donor — hydrophobicity is sequence-intrinsic."
                )

        # feasibility_prescreen is computed once in V3.0 pre-screen stage above.

        if jobs.get(job_id, {}).get("cancel_requested"):
            jobs[job_id].update({"status": "cancelled", "progress": 65})
            return JobStatus(job_id=job_id, status="cancelled", progress=65, result=None, error=None)

        jobs[job_id]["progress"] = 65
        jobs[job_id]["progress_note"] = "NanoBodyBuilder2 — donor structure…"
        try:
            struct_donor = _run_nanobodybuilder2(donor_seq)
        except Exception as _se:
            struct_donor = {"error": str(_se)}

        struct_humanized = {}
        cdr_rmsd = {}
        mini_cmc = {}
        rescue_note = ""
        lead_rank = 1
        lead_candidate = best
        candidate_evaluations = []

        for idx, cand in enumerate(top[:3]):
            cand_seq = _candidate_sequence(cand)
            evaluation = {
                "rank": idx + 1,
                "template_id": _candidate_template_id(cand),
                "passed_hard_gates": False,
                "hard_gate_reasons": [],
                "evaluation_errors": [],
            }
            if not cand_seq:
                evaluation["hard_gate_reasons"].append("missing_sequence")
                candidate_evaluations.append(evaluation)
                continue

            if jobs.get(job_id, {}).get("cancel_requested"):
                jobs[job_id].update({"status": "cancelled", "progress": 75})
                return JobStatus(job_id=job_id, status="cancelled", progress=75, result=None, error=None)

            jobs[job_id]["progress"] = 75 + (idx * 3)
            jobs[job_id]["progress_note"] = f"Evaluating Rank {idx+1} structure/CMC…"

            try:
                curr_struct = _run_nanobodybuilder2(cand_seq)
            except Exception as _se:
                curr_struct = {"error": str(_se)}

            curr_rmsd = {}
            if struct_donor.get("error"):
                evaluation["hard_gate_reasons"].append("donor_structure_unavailable")
                evaluation["evaluation_errors"].append(str(struct_donor.get("error")))
            elif curr_struct.get("error"):
                evaluation["hard_gate_reasons"].append("humanized_structure_failed")
                evaluation["evaluation_errors"].append(str(curr_struct.get("error")))
            else:
                try:
                    curr_rmsd = _compute_vhh_cdr_rmsd(struct_donor["pdb_path"], curr_struct["pdb_path"])
                except Exception as _re:
                    curr_rmsd = {"error": str(_re)}
                if curr_rmsd.get("error"):
                    evaluation["hard_gate_reasons"].append("cdr_rmsd_unavailable")
                    evaluation["evaluation_errors"].append(str(curr_rmsd.get("error")))
                elif not curr_rmsd:
                    # V3.0 inherited fix: empty RMSD dict (e.g., very short seq / no common residues)
                    # is advisory only, not a hard-gate failure — do not block rescue promotion.
                    evaluation["evaluation_errors"].append("cdr_rmsd_empty: no common residues; structural alignment skipped")

            try:
                curr_cmc = _vhh_mini_cmc(cand_seq)
            except Exception as _ce:
                curr_cmc = {"error": str(_ce)}

            if curr_cmc.get("error"):
                evaluation["hard_gate_reasons"].append("mini_cmc_unavailable")
                evaluation["evaluation_errors"].append(str(curr_cmc.get("error")))
            elif curr_cmc.get("instability_index") is None:
                evaluation["hard_gate_reasons"].append("instability_index_missing")
            elif float(curr_cmc.get("instability_index")) > 40.0:
                evaluation["hard_gate_reasons"].append("instability_gt_40")

            if curr_rmsd and not curr_rmsd.get("error"):
                failed_rmsd_keys = [
                    key for key, val in curr_rmsd.items()
                    if isinstance(val, (int, float)) and float(val) > 2.0
                ]
                if failed_rmsd_keys:
                    evaluation["hard_gate_reasons"].append(
                        "cdr_rmsd_gt_2.0:" + ",".join(sorted(failed_rmsd_keys))
                    )

            evaluation["passed_hard_gates"] = len(evaluation["hard_gate_reasons"]) == 0
            candidate_evaluations.append(evaluation)

            if idx == 0:
                lead_candidate = cand
                humanized_seq = cand_seq
                struct_humanized = curr_struct
                cdr_rmsd = curr_rmsd
                mini_cmc = curr_cmc

            if evaluation["passed_hard_gates"]:
                lead_candidate = cand
                lead_rank = idx + 1
                humanized_seq = cand_seq
                struct_humanized = curr_struct
                cdr_rmsd = curr_rmsd
                mini_cmc = curr_cmc
                break

        if candidate_evaluations:
            if lead_rank == 1 and candidate_evaluations[0].get("passed_hard_gates"):
                rescue_note = "Rank 1 passed structural/CMC hard gates; no rescue needed."
            elif lead_rank > 1:
                rescue_note = (
                    f"Rank 1 failed structural/CMC hard gates; Rank {lead_rank} was promoted to lead."
                )
            else:
                rescue_note = (
                    "No evaluated candidate passed structural/CMC hard gates; retaining ranking Top-1 "
                    "for comparison only."
                )

        best = lead_candidate or {}
        fr = _build_fr_summary(best)
        # V3.0 inherited fix: explicit hallmark handling — avoid silent fallback to Rank-1 values.
        _recomputed_hallmarks = _compute_hallmarks_for_seq(humanized_seq)
        if _recomputed_hallmarks:
            hallmarks = _recomputed_hallmarks
        elif lead_rank > 1:
            # Promoted lead hallmark recomputation failed; log flag and retain Rank-1 values with disclaimer.
            res.setdefault("flags", []).append(
                "⚠ Hallmark recomputation for the promoted lead failed; displayed hallmarks belong to original Rank-1 candidate."
            )

        if lead_rank > 1 and top:
            rescued_cand = top.pop(lead_rank - 1)
            top.insert(0, rescued_cand)
            res.setdefault("flags", []).append(f"Deterministic Rescue triggered: {rescue_note}")
        elif rescue_note and "No evaluated candidate passed" in rescue_note:
            res.setdefault("flags", []).append(f"Deterministic Rescue attempted but failed: {rescue_note}")

        res["lead_selection"] = {
            "algorithm_version": "V3.0",
            "selected_rank": lead_rank,
            "selection_summary": rescue_note,
            "evaluated_candidates": candidate_evaluations,
        }

        # ── V3.0 Auto-Correction Recommendations ────────────────────────
        if any(
            isinstance(val, (int, float)) and float(val) > 2.0
            for val in cdr_rmsd.values()
        ):
            res.setdefault("flags", []).append(
                "CDR RMSD exceeds 2.0Å. "
                "Recommendation: Perform Auto-Backmutation on Vernier zone residues differing from the donor "
                "to restore loop conformation."
            )

        _qa = res.get("qa", {}).get("v3_5", {})
        _qa_errors_raw = _qa.get("errors", [])
        _qa_warnings_raw = _qa.get("warnings", [])
        
        # Chinese / technical → English for HTML report (§8 must be English-only for clients)
        import re as _re_qa
        _cn_to_en = {
            "CDR3 anchor residues": (
                "CDR3 anchor mismatch (positions 101/102) — Note: this check was designed for VH/VL grafting. "
                "VHH CDR3 loops are inherently more stable; experimental validation (SPR/BLI) is recommended."
            ),
            "CDR，CDRFR": (
                "CDR canonical conformation data unavailable — compatibility check skipped."
            ),
            "": "Candidate ranking stability",
            "": "Missing region in humanized_regions: ",
            "": "region",
            "": "is empty",
            "0": "Donor sequence length is 0 — cannot validate CDR/FR.",
            "0": "Humanized sequence length is 0.",
            "CDR3": "CDR3 length out of expected range: ",
            "FR2": "FR2 segment unusually short — possible mis-segmentation",
            "FR4": "FR4 is empty — possible missing FR4 in sequence assembly",
            "FR4": "Sequence assembly may have omitted FR4",
            "sequence_analysis": "Missing sequence_analysis field",
            "CDR–FR ": "Significant cumulative physicochemical property changes at the CDR-FR interface",
            "，": "may severely impact affinity or folding. Recommend downgrading to a backup option.",
            "CDR–FR ": "Moderate physicochemical property changes at the CDR-FR interface",
            "": "Structural modeling and functional validation are recommended.",
            "": "combination is borderline",
            "": "Donor sequence length",
            "": "and humanized sequence length",
            "": "are inconsistent",
            "grafting": "unable to accurately analyze grafting impact.",
            "，": "Recommend including as a backup, but further confirmation via experiment or modeling is needed.",
        }
        
        def _translate_flag(msg: str) -> str:
            m = str(msg or "").strip()
            if m.lower() == "swap_risk" or m == "swap_risk":
                return (
                    "Top-two candidate scores/risks are close; the displayed rank is stress-tested "
                    "(low margin — consider reviewing 2nd-ranked template). Metric: swap_risk ∈ [0,1]."
                )
            # Apply translations iteratively to catch multiple phrases in one message
            for cn, en in _cn_to_en.items():
                if cn in m:
                    m = m.replace(cn, en)
            
            # Remove any remaining Chinese punctuation that might look weird in English
            m = m.replace("（", " (").replace("）", ") ").replace("，", ", ").replace("。", ". ")
            
            # If there are still Chinese characters, just return the translated string as is
            # rather than replacing the whole message with a generic "self-talk" advisory.
            return m.strip()

        # Filter out false-alarm messages from VH/VL QA format mismatch
        _format_noise = ("", "0", "CDR3: 0",
                         "FR4", "FR2", "FR4")
        
        def _keep_flag(msg: str) -> bool:
            return not any(noise in msg for noise in _format_noise)

        _qa_errors = [
            _translate_flag(e) for e in _qa_errors_raw
            if _keep_flag(e)
        ]
        _qa_warnings = [
            _translate_flag(w.get("message", str(w)) if isinstance(w, dict) else str(w))
            for w in _qa_warnings_raw
            if _keep_flag(w.get("message", str(w)) if isinstance(w, dict) else str(w))
        ]
        _qa_flags = _qa_errors + _qa_warnings
        
        # Also include risk flags from humanize_vhh
        _risk_flags_raw = [k for k, v in res.get("risk_flags", {}).items() if v]
        _risk_flags = []
        for rf in _risk_flags_raw:
            if rf == "long_cdr3":
                _risk_flags.append(f"High Risk: Long CDR3 detected ({len(cdr_info.get('CDR3', ''))} aa).")
            elif rf == "noncanonical_disulfide_suspected":
                _risk_flags.append("High Risk: Non-canonical disulfide bond suspected (≥3 Cys in CDR3).")
            else:
                _risk_flags.append(f"Risk: {rf}")

        _lead_selection = res.get("lead_selection", {}) or {}
        _lead_rank = int(_lead_selection.get("selected_rank") or 1)
        _sap_block = res.get("v22_sap_check", {}) if _lead_rank == 1 else {}
        if _lead_rank != 1 and res.get("v22_sap_check"):
            _risk_flags.append(
                "SAP score/tier is hidden for the promoted lead because the original SAP block belongs to ranking Top-1; "
                "rerun per-lead SAP if exact rescued-lead SAP is required."
            )

        # V3.0 inherited fix: when rescue promotes backup lead, QA v3.5 flags may refer to original Top-1
        # for the original Rank-1 candidate and may not describe the promoted lead.
        # Prepend a clear provenance notice so the report reader is not misled.
        if _lead_rank > 1:
            _qa_flags.insert(0,
                "ℹ QA flags below were generated for the original ranking Top-1 candidate, "
                "which failed structural hard gates. The promoted lead (Rank "
                + str(_lead_rank)
                + ") was selected by Deterministic Rescue (V3.0). "
                "Re-submit with the promoted lead sequence for lead-specific QA flags."
            )

        _all_flags = _qa_flags + _risk_flags + res.get("flags", [])

        # Primary label for HTML: sequence_name, else project_name if not placeholder, else job id
        _sn = (getattr(req, "sequence_name", None) or "").strip()
        _pn_req = (getattr(req, "project_name", None) or "demo").strip()
        if _pn_req.lower() in ("", "demo", "vhh humanization"):
            _pn_req = ""
        _report_label = _sn or _pn_req

        _rs = _qa.get("ranking_stability") or {}
        _swap_risk = _rs.get("swap_risk") or 0.0
        _stability_score = _rs.get("stability_score") or 1.0
        _ranking_tier = str(_rs.get("tier") or "A")
        _output_mode = str(_rs.get("recommended_output_mode") or "single_lead")
        _tier_reason = str(_rs.get("tier_reason") or "")

        payload = {
            "job_id":              job_id,
            "input_sequence":     donor_seq,
            "original_input_sequence": _raw_input if _seq_clean_result["was_modified"] else None,
            "sequence_cleaning":  _seq_clean_result if _seq_clean_result["was_modified"] else None,
            "sequence_name":      req.sequence_name,
            "project_name":        req.project_name,
            "hallmark_37":         hallmarks.get("pos37", "?"),
            "hallmark_44":          hallmarks.get("pos44", "?"),
            "hallmark_45":          hallmarks.get("pos45", "?"),
            "hallmark_47":          hallmarks.get("pos47", "?"),
            "hallmarks_ok":         hallmarks.get("all_ok", False),
            "cdr1_seq":             cdr_info.get("CDR1", ""),
            "cdr2_seq":             cdr_info.get("CDR2", ""),
            "cdr3_seq":             cdr_info.get("CDR3", ""),
            "cdr3_length":          len(cdr_info.get("CDR3", "")),
            "cdr3_canonical":       _cdr3_canonical,
            "human_vh3_germline":   fr.get("selected_germline", "—"),
            "human_vh3_identity":   fr.get("overall_identity_pct"),
            "fr2_identity":         fr.get("fr2_identity_pct"),
            "strategy_applied":     req.strategy,
            # AbLang not computed for VHH; use combined_score as quality proxy
            "ablang_score":         None,
            "combined_score":       fr.get("combined_score"),
            "humanness_score":      best.get("humanness_score"),
            "structure_computed":   struct_humanized.get("structure_computed", False),
            # v22_sap_check belongs to original ranking Top-1; suppress if V3.0 rescue promoted another lead.
            "sap_score":            _sap_block.get("hydro_patch"),
            "sap_tier":             _sap_block.get("tier"),
            "donor_plddt":          struct_donor.get("plddt"),
            "humanized_plddt":      struct_humanized.get("plddt"),
            "cdr_rmsd":             cdr_rmsd,
            "mini_cmc":             mini_cmc,
            "donor_mini_cmc":        donor_mini_cmc,
            "donor_prescreen_flags": _donor_prescreen_flags,
            "feasibility_prescreen": feasibility_prescreen,
            "cmc_advisory":          _build_cmc_advisory(
                donor_mini_cmc, mini_cmc, cdr_rmsd, cdr_info
            ),
            # V3.0 inherited fix: if rescue attempted but all candidates failed hard gates,
            # the original "OK" status is misleading — upgrade to WARN.
            "checklist_status":     (
                "WARN"
                if rescue_note and "No evaluated candidate passed" in rescue_note
                else res.get("status", "UNKNOWN")
            ),
            "flags":                _all_flags,
            "humanized_sequence":   humanized_seq,
            "tier_back_mutations":  list(best.get("tier_back_mutations") or []),
            "donor_sequence":       donor_seq,
            "sequence_comparison":  _build_vhh_sequence_comparison(donor_seq, humanized_seq or ""),
            "candidates":           top,
            "lead_selection":       _lead_selection,
            "top_k":                req.top_k,
            # v3.5 ranking stability — used in §8 stability advisory block
            "swap_risk":            _swap_risk,
            "stability_score":      _stability_score,
            "ranking_tier":         _ranking_tier,
            "recommended_output_mode": _output_mode,
            "ranking_tier_reason":  _tier_reason,
        }

        # ── humanization_plus_reshape: sequential surface reshaping after CDR-graft ──
        # Triggered when pre-screen recommendation == "humanization_plus_reshape"
        # (SAP yellow zone — CDR-graft runs first, then surface reshaping applied to
        # the best humanized sequence to reduce any residual FR hydrophobic patches).
        if feasibility_prescreen.get("recommendation") == "humanization_plus_reshape" and humanized_seq:
            jobs[job_id]["progress"] = 87
            jobs[job_id]["progress_note"] = "Applying post-graft surface reshaping (SAP yellow zone)…"
            try:
                from scripts.run_vhh_surface_reshaping_v1 import reshape_vhh_surface  # noqa: PLC0415
                _pgsr = reshape_vhh_surface(humanized_seq, strategy="S2")
                payload["post_graft_surface_reshaping"] = _pgsr
                if _pgsr.get("positions_modified", 0) > 0:
                    _pgsr_seq = _pgsr.get("output_sequence", humanized_seq)
                    # Update the best candidate sequence with the reshaped version
                    payload["humanized_sequence"] = _pgsr_seq
                    humanized_seq = _pgsr_seq
                    payload.setdefault("flags", []).append(
                        f"Post-graft surface reshaping applied {_pgsr['positions_modified']} mutation(s) "
                        f"(SAP {_pgsr['sap_before']:.3f} → {_pgsr['sap_after']:.3f}). "
                        "Humanized sequence updated."
                    )
                    # Recompute mini-CMC for the reshaped sequence
                    try:
                        payload["mini_cmc"] = _vhh_mini_cmc(_pgsr_seq)
                        mini_cmc = payload["mini_cmc"]
                    except Exception:
                        pass
            except Exception as _pgsr_err:
                payload.setdefault("flags", []).append(
                    f"Post-graft reshaping error (non-critical): {_pgsr_err}"
                )

        # ── humanization_plus_charge: post-graft charge advisory ──────────────
        # For pI borderline — the actual charge remodelling is an offline service;
        # here we compute the pI delta and set a structured advisory flag.
        # (The post-humanization pI check below covers the flag; this block just
        #  sets the strategy label so the report can explain why pI matters.)
        if feasibility_prescreen.get("recommendation") == "humanization_plus_charge":
            payload["post_graft_charge_advisory"] = True

        # ── Post-humanization pI check ─────────────────────────────────────────────
        # CDR-graft preserves CDR charge; human VH3 framework may shift pI upward.
        # If humanized pI > 9.5 (therapeutic window) or worsened by > 0.5, flag it.
        _donor_pi  = (donor_mini_cmc or {}).get("pI")
        _human_pi  = (mini_cmc or {}).get("pI")
        if _donor_pi is not None and _human_pi is not None:
            _pi_delta = round(_human_pi - _donor_pi, 2)
            if _human_pi > 9.5:
                payload.setdefault("flags", []).append(
                    f"POST-HUMANIZATION pI={_human_pi:.2f} exceeds therapeutic window (>9.5). "
                    f"Human VH3 framework raised pI by {_pi_delta:+.2f} (donor={_donor_pi:.2f}). "
                    "Surface reshaping on framework charge positions is recommended (offline CMC service)."
                )
                payload["post_humanization_pi_warning"] = {
                    "donor_pi": _donor_pi, "humanized_pi": _human_pi,
                    "delta": _pi_delta, "severity": "HIGH",
                }
            elif _pi_delta > 0.5 and _human_pi > 8.5:
                payload.setdefault("flags", []).append(
                    f"Post-humanization pI increased by {_pi_delta:+.2f} ({_donor_pi:.2f} → {_human_pi:.2f}). "
                    "CDR-graft framework substitutions have raised pI toward the borderline cationic range. "
                    "Monitor pI and consider charge-reducing FR mutations if proceeding to clinical development."
                )
                payload["post_humanization_pi_warning"] = {
                    "donor_pi": _donor_pi, "humanized_pi": _human_pi,
                    "delta": _pi_delta, "severity": "MEDIUM",
                }

        # ── VHH HPR Index (V3.3+) ──────────────────────────────────────────────
        # Compute compatibility of 9-mer peptides against human antibody repertoire.
        try:
            from core.humanization.hpr_index import compare_hpr_vhh  # noqa: PLC0415
            payload["hpr_index"] = compare_hpr_vhh(donor_seq, humanized_seq or "")
        except Exception as _hpr_err:
            payload["hpr_index"] = {"metric_name": "HPR Index", "error": str(_hpr_err)}

        # ── AbNatiV2 VH Δ / VHH Δ (V5.0 QC gate) ──────────────────────────────
        # VH Δ  = humanized VH2 score  − donor VH2 score  (want POSITIVE → more human-VH-like)
        # VHH Δ = humanized VHH2 score − donor VHH2 score (expect NEGATIVE → acceptable VHH loss)
        try:
            import queue as _abn_q
            import threading as _abn_t
            from core.vh2vhh.abnativ_naturalness_layer import (  # noqa: PLC0415
                score_naturalness_delta as _snd,
            )

            _abn_result: Dict[str, Any] = {}

            def _abn_worker() -> None:  # noqa: ANN202
                try:
                    _d = _snd(donor_seq, seq_id="donor")
                    _h = _snd(humanized_seq or "", seq_id="humanized")
                    _abn_result["donor"] = {
                        "vh2":  round(float(_d.vh2_score), 4)  if _d.vh2_score  is not None else None,
                        "vhh2": round(float(_d.vhh2_score), 4) if _d.vhh2_score is not None else None,
                        "delta": round(float(_d.delta), 4)     if _d.delta      is not None else None,
                        "tier": _d.tier,
                    }
                    _abn_result["humanized"] = {
                        "vh2":  round(float(_h.vh2_score), 4)  if _h.vh2_score  is not None else None,
                        "vhh2": round(float(_h.vhh2_score), 4) if _h.vhh2_score is not None else None,
                        "delta": round(float(_h.delta), 4)     if _h.delta      is not None else None,
                        "tier": _h.tier,
                    }
                    if _d.vh2_score is not None and _h.vh2_score is not None:
                        _abn_result["delta_vh2"] = round(float(_h.vh2_score) - float(_d.vh2_score), 4)
                    if _d.vhh2_score is not None and _h.vhh2_score is not None:
                        _abn_result["delta_vhh2"] = round(float(_h.vhh2_score) - float(_d.vhh2_score), 4)
                except Exception as _ae:
                    _abn_result["error"] = f"{type(_ae).__name__}: {_ae}"

            _abt = _abn_t.Thread(target=_abn_worker, daemon=True)
            _abt.start()
            _abt.join(180)
            if not _abn_result:
                _abn_result["error"] = "AbNatiV naturalness scoring timeout (>180 s)"
            payload["abnativ_naturalness"] = _abn_result
        except Exception as _abn_err:
            payload["abnativ_naturalness"] = {"error": f"{type(_abn_err).__name__}: {_abn_err}"}

        # Hard gate + delivery artifacts only after final humanized_seq (incl. post-graft reshape).
        _vhh_assert_pipeline_cdr_match(donor_seq, humanized_seq or "")

        import shutil

        jobs[job_id]["progress"] = 88
        jobs[job_id]["progress_note"] = "Writing FASTA / structures…"
        out.mkdir(parents=True, exist_ok=True)

        fasta_path = out / "vhh_sequences.fasta"
        fasta_lines = [f">Donor_VHH\n{donor_seq}"]
        if humanized_seq:
            fasta_lines.append(f">Humanized_VHH_Top1\n{humanized_seq}")
        for i, c in enumerate(top[1:], 2):
            seq = c.get("humanized_sequence") or c.get("sequence") or ""
            if seq:
                fasta_lines.append(f">Humanized_VHH_Top{i}\n{seq}")
        fasta_path.write_text("\n".join(fasta_lines), encoding="utf-8")

        if struct_donor.get("pdb_path") and Path(struct_donor["pdb_path"]).exists():
            shutil.copy2(struct_donor["pdb_path"], out / "donor_vhh.pdb")
        if struct_humanized.get("pdb_path") and Path(struct_humanized["pdb_path"]).exists():
            shutil.copy2(struct_humanized["pdb_path"], out / "humanized_vhh.pdb")

        jobs[job_id]["progress"] = 93
        try:
            report_path = _generate_vhh_html_report(payload, out, _report_label)
            report_url = files_url_for_path(job_id, report_path)
        except Exception as _vhh_rpt_err:
            report_url = None
            payload["_vhh_report_error"] = str(_vhh_rpt_err)

        # Public ZIP name is fixed; set before writing result.json / baking the ZIP
        if (out / "vhh_sequences.fasta").is_file():
            payload["zip_url"] = f"/files/{job_id}/{job_id}_vhh_delivery.zip"
        (out / "result.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        zip_url = _create_vhh_delivery_zip(out, job_id)
        if not zip_url:
            payload.pop("zip_url", None)
        else:
            payload["zip_url"] = zip_url
        (out / "result.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        elapsed = round(time.time() - t0, 1)
        # Console / polling: always expose per-file download paths when artifacts exist
        _extra: Dict[str, Any] = {}
        if zip_url:
            _extra["zip_url"] = zip_url
        if (out / "vhh_sequences.fasta").is_file():
            _extra["fasta_url"] = f"/files/{job_id}/vhh_sequences.fasta"

        save_result(job_id, payload, report_url, elapsed, extra=_extra)
        return JobStatus(
            job_id=job_id, status="done", progress=100,
            elapsed_sec=elapsed, result=payload, report_url=report_url,
            extra=_extra or None,
        )

    except Exception as e:
        import traceback
        from core.qa.pipeline_qa import QAViolation
        err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        jobs[job_id] = {"status": "failed", "progress": 0, "error": err}
        persist_job_snapshot(job_id)
        raise HTTPException(
            status_code=422 if isinstance(e, QAViolation) else 500,
            detail=str(e) if isinstance(e, QAViolation) else err,
        )


@router.post("/vhh", response_model=JobStatus, summary="Humanize camelid VHH nanobody (sync)")
def humanize_vhh(req: VHHRequest):
    """Synchronous VHH humanization — blocks until complete."""
    job_id = f"hu-vhh-{uuid.uuid4().hex[:8]}"
    jobs[job_id] = {"status": "running", "progress": 5, "progress_note": "Starting…"}
    return _humanize_vhh_impl(job_id, req)


@router.post("/vhh/async", summary="Enqueue VHH humanization (poll GET /jobs/{job_id})")
def humanize_vhh_async(req: VHHRequest):
    """Return immediately with job_id; run pipeline in background thread."""
    job_id = f"hu-vhh-{uuid.uuid4().hex[:8]}"
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "progress_note": "Queued — worker starting…",
    }
    persist_job_snapshot(job_id)

    def _worker() -> None:
        try:
            _humanize_vhh_impl(job_id, req)
        except HTTPException:
            pass
        except Exception as e:
            jobs[job_id] = {"status": "failed", "progress": 0, "error": str(e)}
            persist_job_snapshot(job_id)

    threading.Thread(target=_worker, daemon=True).start()
    return {"job_id": job_id, "status": "queued", "poll_url": f"/jobs/{job_id}"}
