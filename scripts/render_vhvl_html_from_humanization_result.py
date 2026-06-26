#!/usr/bin/env python3
"""
Rebuild api-style VH/VL humanization_report.html from a saved humanization_result.json
(off-line; requires conda env with FastAPI stack + Bio), mirroring payload assembly in
api/routers/humanization.py::_humanize_vh_vl_impl (reports section).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _build_payload(data: dict, req: SimpleNamespace, donor_species: str) -> dict:
    from Bio.SeqUtils.ProtParam import ProteinAnalysis

    from api.public_locale import resolve_vhvl_report_language
    from api.routers.humanization import (
        VHVL_HTML_REPORT_BUILD_ID,
        _build_vhvl_cmc_advisory,
        _cdrs_imgt_for_report,
        _fmt_canonical,
        _lookup_clinical_precedents,
        _lookup_clinical_precedents_for_template_side,
        _lookup_germline_ada_references,
        _lookup_germline_ada_references_for_template_side,
        _species_cmc_gates,
        _vhvl_count_phases_no_fail,
    )

    result = SimpleNamespace(
        overall_status=data.get("overall_status"),
        notes=data.get("notes") or [],
        qa_audit=data.get("qa_audit") or {},
    )

    qm = data.get("qc_metrics") or {}
    seq = data.get("sequences") or {}
    r = data.get("checklist_report") or {}

    donor_mini_cmc: dict = {}
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
    except Exception as e:
        donor_mini_cmc = {"error": str(e)}

    fw = qm.get("framework_selection", {})
    _vh_fr_id = fw.get("vh_identity_pct")
    if _vh_fr_id is None:
        _vh_fr_id = fw.get("framework_identity_vh")
    _vl_fr_id = fw.get("vl_identity_pct")
    if _vl_fr_id is None:
        _vl_fr_id = fw.get("framework_identity_vl")

    cdr = qm.get("cdr_identification", {})
    structure = qm.get("structure", {})
    vernier = qm.get("vernier_risk_positions", [])
    ablang = qm.get("ablang_score")
    bm_vh = fw.get("bm_candidates_vh") or qm.get("bm_candidates_vh", [])
    bm_vl = fw.get("bm_candidates_vl") or qm.get("bm_candidates_vl", [])
    sdrm_vh = fw.get("sdrm_vh", [])
    sdrm_vl = fw.get("sdrm_vl", [])
    fr_diffs_vh = fw.get("fr_differences_vh", [])
    fr_diffs_vl = fw.get("fr_differences_vl", [])

    mouse_keys = {"mouse_vh", "mouse_vl", "mouse_vhh"}
    humanized = {k: v for k, v in seq.items() if k not in mouse_keys and v}
    humanized_vh = humanized.get("humanized_vh") or humanized.get("Our_Hum") or next(
        (v for k, v in humanized.items() if "vh" in k.lower()), ""
    )
    humanized_vl = humanized.get("humanized_vl") or next(
        (v for k, v in humanized.items() if "vl" in k.lower()), ""
    )

    top_vh_list = fw.get("top_vh_candidates", [])
    top_vl_list = fw.get("top_vl_candidates", [])

    def _cand_id(item):
        return item.get("germline") if isinstance(item, dict) else item

    def _cand_score(item):
        return item.get("fr_identity") if isinstance(item, dict) else None

    candidates = []
    for _vh_item in top_vh_list[:3]:
        for _vl_item in top_vl_list[:2]:
            vh_sc = _cand_score(_vh_item)
            vl_sc = _cand_score(_vl_item)
            avg = (
                round((vh_sc + vl_sc) / 2, 1)
                if (isinstance(vh_sc, (int, float)) and isinstance(vl_sc, (int, float)))
                else None
            )
            candidates.append(
                {
                    "rank": len(candidates) + 1,
                    "vh_germline": _cand_id(_vh_item),
                    "vl_germline": _cand_id(_vl_item),
                    "vh_fr_id": vh_sc,
                    "vl_fr_id": vl_sc,
                    "score": avg,
                }
            )
            if len(candidates) >= 5:
                break
        if len(candidates) >= 5:
            break

    cdr_rmsd = qm.get("cdr_rmsd", {})

    payload = {
        "source_species": req.source_species,
        "donor_species": donor_species,
        "phase2_degraded": bool(fw.get("phase2_degraded")),
        "phase2_fallback_reason": fw.get("phase2_fallback_reason"),
        "selection_mode": fw.get("selection_mode"),
        "phase2_extended_cache_scan_vh": bool(fw.get("phase2_extended_cache_scan_vh")),
        "phase2_extended_cache_scan_vl": bool(fw.get("phase2_extended_cache_scan_vl")),
        "clinical_framework_policy": fw.get("clinical_framework_policy"),
        "vh_germline": fw.get("selected_vh_germline") or "—",
        "vh_germline_identity": _vh_fr_id,
        "vl_germline": fw.get("selected_vl_germline") or "—",
        "vl_germline_identity": _vl_fr_id,
        "vh_fr_identity_chothia_cdr_masked": _vh_fr_id,
        "vl_fr_identity_chothia_cdr_masked": _vl_fr_id,
        "cdr_canonical_class": _fmt_canonical(cdr.get("canonical_class")),
        "cdrs": cdr.get("cdrs", {}),
        "ablang_score": ablang,
        "framework_human_identity_vh": fw.get("framework_identity_vh"),
        "framework_human_identity_vl": fw.get("framework_identity_vl"),
        "top_vh_candidates": top_vh_list,
        "top_vl_candidates": top_vl_list,
        "vernier_risk_positions": vernier,
        "bm_candidates_vh": bm_vh,
        "bm_candidates_vl": bm_vl,
        "backmutation_count": len(bm_vh) + len(bm_vl),
        "fr_differences_vh": fr_diffs_vh,
        "fr_differences_vl": fr_diffs_vl,
        "fr_differences_total": len(fr_diffs_vh) + len(fr_diffs_vl),
        "sdrm_vh": sdrm_vh,
        "sdrm_vl": sdrm_vl,
        "structure_computed": not structure.get("dry_run", True),
        "structure_mode": "DRY_RUN" if structure.get("dry_run", True) else "COMPUTED",
        "plddt": structure.get("plddt"),
        "vh_vl_angle_deg": structure.get("vh_vl_angle_deg"),
        "humanized_plddt": structure.get("humanized_plddt"),
        "humanized_angle_deg": structure.get("humanized_angle_deg"),
        "angle_delta_deg": structure.get("angle_delta_deg"),
        "mini_cmc": qm.get("mini_cmc", {}),
        "donor_mini_cmc": donor_mini_cmc,
        "cmc_species_gates": _species_cmc_gates(req.source_species),
        "cmc_advisory": _build_vhvl_cmc_advisory(
            donor_mini_cmc,
            qm.get("mini_cmc", {}),
            qm.get("cdr_rmsd", {}),
            result.overall_status if hasattr(result, "overall_status") else "UNKNOWN",
            result.notes if hasattr(result, "notes") else [],
            source_species=req.source_species,
            stable_cdr_keys=qm.get("cdr_rmsd_stable_cdrs"),
        ),
        "pI_fab": qm.get("pI_fab"),
        "liabilities": qm.get("liabilities", []),
        "rescue": qm.get("rescue", {}),
        "cdr_rmsd_stable_cdrs": qm.get("cdr_rmsd_stable_cdrs"),
        "cdr_rmsd_volatile_cdrs": qm.get("cdr_rmsd_volatile_cdrs"),
        "delivery_decision": qm.get("delivery_decision", {}),
        "qc_warning_reasons": (getattr(result, "qa_audit", {}) or {}).get("delivery_warning_reasons", []),
        "cdr_rmsd": cdr_rmsd,
        "rmsd_to_reference": (
            round(sum(v for v in cdr_rmsd.values() if isinstance(v, float)) / len(cdr_rmsd), 2)
            if cdr_rmsd
            and isinstance(cdr_rmsd, dict)
            and any(isinstance(v, float) for v in cdr_rmsd.values())
            else None
        ),
        "checklist_status": result.overall_status if hasattr(result, "overall_status") else "UNKNOWN",
        "checklist_phases_passed": _vhvl_count_phases_no_fail(r),
        "flags": result.notes if hasattr(result, "notes") else [],
        "clinical_reference": qm.get("clinical_reference", {}),
        "global_fv_rmsd_ca": qm.get("global_fv_rmsd_ca"),
        "fr_identity_qc": qm.get("fr_identity_qc"),
        "structural_qc_v50": qm.get("structural_qc_v50"),
        "fallback_germline_used": fw.get("fallback_germline_used", False),
        "cdr_integrity_check": qm.get("cdr_integrity_check"),
        "cdr_diff_vh": qm.get("cdr_diff_vh", []),
        "cdr_diff_vl": qm.get("cdr_diff_vl", []),
        "cdr_scheme": qm.get("cdr_scheme") or "union_kabat_chothia_v5_1",
        "mouse_vh": req.vh_sequence.strip().upper(),
        "mouse_vl": req.vl_sequence.strip().upper(),
        "humanized_vh": humanized_vh,
        "humanized_vl": humanized_vl,
        "candidates": candidates,
        "report_language": resolve_vhvl_report_language(getattr(req, "report_language", None)),
        "report_format": (getattr(req, "report_format", None) or "both").strip().lower(),
        "repair_mode": req.repair_mode,
        "back_mutation_strategy": "auto",
        "surface_reshape_on_qc_fail": bool(getattr(req, "surface_reshape_on_qc_fail", False)),
        "pdb_urls": {},
        "mouse_fasta_url": None,
        "humanized_fasta_url": None,
        "job_id": getattr(req, "job_id", "") or data.get("project_name", "offline_render"),
    }

    _imgt_cdrs = _cdrs_imgt_for_report(payload["mouse_vh"], payload["mouse_vl"])
    if _imgt_cdrs and any(_imgt_cdrs.values()):
        payload["cdrs_imgt"] = _imgt_cdrs
        payload["cdr_reporting_scheme"] = "IMGT"
    else:
        payload["cdrs_imgt"] = {}
        payload["cdr_reporting_scheme"] = "engine_union_fallback"

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

    best_vh_fb = ""
    best_vl_fb = ""
    try:
        cands = fw.get("top_vh", [])
        if cands:
            best_vh_fb = cands[0]["germline"] if isinstance(cands[0], dict) else str(cands[0])
        cands = fw.get("top_vl", [])
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
    payload["clinical_precedents"] = _lookup_clinical_precedents(sel_vh, sel_vl, top_n=8)
    payload["clinical_precedents_vh_template"] = _lookup_clinical_precedents_for_template_side(
        sel_vh, "H", top_n=8
    )
    payload["clinical_precedents_vl_template"] = _lookup_clinical_precedents_for_template_side(
        sel_vl, "L", top_n=8
    )
    payload["report_generator_build"] = VHVL_HTML_REPORT_BUILD_ID
    payload["germline_ada_references"] = (
        qm.get("clinical_reference", {}).get("germline_ada_references", [])
        or _lookup_germline_ada_references(sel_vh, sel_vl, top_n=8)
    )
    payload["germline_ada_references_vh_template"] = _lookup_germline_ada_references_for_template_side(
        sel_vh, "H", top_n=8
    )
    payload["germline_ada_references_vl_template"] = _lookup_germline_ada_references_for_template_side(
        sel_vl, "L", top_n=8
    )

    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description="Render VH/VL humanization_report.html from JSON.")
    ap.add_argument("--json", type=Path, required=True, help="humanization_result.json path")
    ap.add_argument("--out-dir", type=Path, default=None, help="Output directory (default: JSON parent)")
    ap.add_argument("--source-species", default="mouse")
    ap.add_argument("--report-language", default="zh")
    ap.add_argument("--repair-mode", default="standard")
    ap.add_argument("--job-id", default="", help="Job / project label in HTML footer")
    args = ap.parse_args()

    data = json.loads(args.json.read_text(encoding="utf-8"))
    seq = data.get("sequences") or {}
    out_dir = args.out_dir or args.json.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    species_map = {
        "mouse": "mus_musculus",
        "rat": "rattus_norvegicus",
        "rabbit": "oryctolagus_cuniculus",
    }
    donor_species = species_map.get((args.source_species or "mouse").strip().lower(), "mus_musculus")

    req = SimpleNamespace(
        source_species=args.source_species,
        vh_sequence=seq.get("mouse_vh", ""),
        vl_sequence=seq.get("mouse_vl", ""),
        repair_mode=args.repair_mode,
        report_language=args.report_language,
        report_format="html",
        surface_reshape_on_qc_fail=False,
        job_id=args.job_id or data.get("project_name", "offline"),
    )

    payload = _build_payload(data, req, donor_species)
    payload["project_name"] = data.get("project_name", payload.get("job_id"))

    from api.routers.humanization import _generate_html_report

    path = _generate_html_report(
        "vhvl_humanization",
        payload,
        out_dir,
        args.job_id or data.get("project_name", "humanization"),
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
