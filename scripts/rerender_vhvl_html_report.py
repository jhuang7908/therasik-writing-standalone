#!/usr/bin/env python3
"""
Re-render VH/VL humanization_report.html from an existing job result.json
using current _generate_html_report / clinical + germline-ADA lookups.

Usage:
  python scripts/rerender_vhvl_html_report.py hu-vhvl-f9e71716
  python scripts/rerender_vhvl_html_report.py .job_storage/hu-vhvl-f9e71716
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.routers.humanization import (  # noqa: E402
    VHVL_HTML_REPORT_BUILD_ID,
    _generate_html_report,
    _lookup_clinical_precedents,
    _lookup_clinical_precedents_for_template_side,
    _lookup_germline_ada_references,
    _lookup_germline_ada_references_for_template_side,
)


def _fallback_top_germline(payload: dict, key: str) -> str:
    cands = payload.get(key) or []
    if not cands:
        return ""
    c0 = cands[0]
    if isinstance(c0, dict):
        return (c0.get("germline") or "").strip()
    return str(c0).strip()


def refresh_clinical_ada(payload: dict) -> None:
    """Align with api/routers/humanization.py post-fix logic."""
    sel_vh = (payload.get("vh_germline") or "").strip()
    sel_vl = (payload.get("vl_germline") or "").strip()
    if sel_vh in ("", "—"):
        sel_vh = _fallback_top_germline(payload, "top_vh_candidates")
    if sel_vl in ("", "—"):
        sel_vl = _fallback_top_germline(payload, "top_vl_candidates")

    sr = payload.get("surface_reshape_fallback") or {}
    routes = payload.setdefault("per_chain_engineering_route", {})
    vh_surface = bool(sr.get("applied") and sr.get("vh_mutations")) or routes.get("vh") == "donor_framework_fr_surface_reshaping"
    vl_surface = bool(sr.get("applied") and sr.get("vl_mutations")) or routes.get("vl") == "donor_framework_fr_surface_reshaping"
    if vh_surface:
        routes["vh"] = "donor_framework_fr_surface_reshaping"
    if vl_surface:
        routes["vl"] = "donor_framework_fr_surface_reshaping"
    routes.setdefault("vh", "human_germline_cdr_grafting")
    routes.setdefault("vl", "human_germline_cdr_grafting")
    routes.setdefault(
        "note",
        "Surface-reshaped chains use donor framework plus selected FR surface substitutions; "
        "human germline entries are reference context only for those chains.",
    )

    payload["clinical_precedents"] = _lookup_clinical_precedents(
        "" if vh_surface else sel_vh,
        "" if vl_surface else sel_vl,
        top_n=8,
    )
    payload["clinical_precedents_vh_template"] = (
        [] if vh_surface else _lookup_clinical_precedents_for_template_side(sel_vh, "H", top_n=8)
    )
    payload["clinical_precedents_vl_template"] = (
        [] if vl_surface else _lookup_clinical_precedents_for_template_side(sel_vl, "L", top_n=8)
    )
    payload["report_generator_build"] = VHVL_HTML_REPORT_BUILD_ID
    qm_cr = (payload.get("clinical_reference") or {})
    payload["germline_ada_references"] = (
        qm_cr.get("germline_ada_references", [])
        or _lookup_germline_ada_references(sel_vh, sel_vl, top_n=8)
    )
    payload["germline_ada_references_vh_template"] = (
        [] if vh_surface else _lookup_germline_ada_references_for_template_side(sel_vh, "H", top_n=8)
    )
    payload["germline_ada_references_vl_template"] = (
        [] if vl_surface else _lookup_germline_ada_references_for_template_side(sel_vl, "L", top_n=8)
    )

    # V5.4.12: dual-route comparison visibility for rabbit/rat reports
    sp = str(payload.get("source_species") or "").strip().lower()
    if sp in {"rabbit", "oryctolagus_cuniculus", "rat", "rattus_norvegicus"}:
        top_vh = payload.get("top_vh_candidates") or []
        selected_vh = str(payload.get("vh_germline") or "").strip()
        alt_vh_ge65 = None
        for c in top_vh:
            if not isinstance(c, dict):
                continue
            try:
                fr_ok = float(c.get("fr_identity")) >= 65.0
            except Exception:
                fr_ok = False
            if fr_ok and str(c.get("germline") or "").strip() != selected_vh:
                alt_vh_ge65 = {
                    "germline": c.get("germline"),
                    "fr_identity": c.get("fr_identity"),
                    "vernier_similarity": c.get("vernier_similarity"),
                    "composite_score": c.get("composite_score"),
                }
                break
        srfb = payload.get("surface_reshape_fallback") or {}
        sr_note = "; ".join(srfb.get("errors") or []) if isinstance(srfb, dict) else ""
        sr_applied = bool(isinstance(srfb, dict) and srfb.get("applied"))
        sr_status = "applied" if sr_applied else ("blocked" if sr_note else "not_triggered")
        payload["route_comparison"] = {
            "enabled": True,
            "required": bool(
                alt_vh_ge65
                or (isinstance(payload.get("vh_germline_identity"), (int, float)) and float(payload.get("vh_germline_identity")) < 60.0)
                or (isinstance(payload.get("vl_germline_identity"), (int, float)) and float(payload.get("vl_germline_identity")) < 60.0)
                or str(payload.get("checklist_status") or "").upper() in {"WARN", "FAIL"}
            ),
            "grafting_selected": {
                "vh_germline": payload.get("vh_germline"),
                "vl_germline": payload.get("vl_germline"),
                "vh_fr_identity": payload.get("vh_germline_identity"),
                "vl_fr_identity": payload.get("vl_germline_identity"),
            },
            "grafting_alt_vh_ge65": alt_vh_ge65,
            "surface_route": {
                "requested": bool(payload.get("surface_reshape_on_qc_fail", True)),
                "triggered": sr_applied or bool(sr_note),
                "applied": sr_applied,
                "status": sr_status,
                "note": sr_note or str((srfb or {}).get("note") or ""),
            },
        }

        # V5.4.13: build the Route A' alternative ≥65% CDR-grafting deliverable
        if alt_vh_ge65 and alt_vh_ge65.get("germline"):
            try:
                from core.humanization.alt_route_grafting import (  # noqa: PLC0415
                    build_alt_route_grafting_deliverable,
                )
                donor_vh = (payload.get("mouse_vh") or "").strip().upper()
                donor_vl = (payload.get("mouse_vl") or "").strip().upper()
                if donor_vh and donor_vl:
                    deliv = build_alt_route_grafting_deliverable(
                        donor_vh=donor_vh,
                        donor_vl=donor_vl,
                        alt_vh_germline_id=str(alt_vh_ge65.get("germline") or ""),
                        selected_vl_germline_id=str(payload.get("vl_germline") or ""),
                    )
                    payload["route_comparison"]["grafting_alt_vh_ge65"]["deliverable"] = deliv
            except Exception as e:
                payload["route_comparison"]["grafting_alt_vh_ge65"]["deliverable"] = {
                    "applied": False,
                    "errors": [f"Alt-route deliverable build failed: {e}"],
                }


def main() -> None:
    ap = argparse.ArgumentParser(description="Re-render VH/VL HTML report from result.json")
    ap.add_argument(
        "job_or_dir",
        help="Job id (e.g. hu-vhvl-f9e71716) or path to job directory",
    )
    args = ap.parse_args()

    raw = args.job_or_dir.strip()
    if Path(raw).is_dir():
        job_dir = Path(raw).resolve()
        job_id = job_dir.name
    else:
        job_id = raw
        job_dir = ROOT / ".job_storage" / job_id

    result_path = job_dir / "result.json"
    if not result_path.is_file():
        print(f"Missing {result_path}", file=sys.stderr)
        sys.exit(1)

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    refresh_clinical_ada(payload)
    result_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = _generate_html_report("vhvl_humanization", payload, job_dir, job_id)
    print(report_path.resolve())


if __name__ == "__main__":
    main()
