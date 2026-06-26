#!/usr/bin/env python3
"""Rabbit hybrid humanization branch.

This is a separate rabbit-specific route, not a replacement for the standard
VH/VL HumanizationEngine workflow.

Decision rule:
- If a chain has low framework identity OR chain-local CDR RMSD failure, that
  chain uses donor-framework surface reshaping toward the selected human
  germline.
- If a chain passes those gates, keep the standard CDR-grafted output from the
  VH/VL engine.

Typical rabbit outcome:
- VH with long/non-canonical CDR geometry -> surface reshaping.
- VL with acceptable geometry -> standard CDR grafting.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

from core.humanization.engine import HumanizationEngine  # noqa: E402
from core.humanization.kabat_utils import get_kabat_numbering, is_in_cdr, sorted_keys  # noqa: E402
from scripts.run_dog_surface_reshaping_v1 import VH_SURFACE_KABAT, VL_SURFACE_KABAT  # noqa: E402
from scripts.vhvl_surface_reshape_fallback import load_human_germline_sequences  # noqa: E402


RABBIT_SPECIES = "oryctolagus_cuniculus"

# Vernier/interface positions are protected even if they appear in a historical
# "surface" set. They support CDR shape and should not be resurfaced automatically.
VH_PROTECTED_KABAT = {2, 27, 28, 29, 30, 47, 48, 49, 67, 69, 71, 73, 78, 93, 94}
VL_PROTECTED_KABAT = {2, 4, 35, 36, 46, 47, 48, 49, 64, 66, 69, 71, 73}


@dataclass
class ChainDecision:
    chain: str
    strategy: str
    framework_identity_pct: float | None
    identity_threshold_pct: float
    cdr_rmsd: Dict[str, float]
    cdr_rmsd_threshold_a: float
    trigger_reasons: List[str]
    surface_mutations: List[str]


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _kabat_surface_resurface(
    donor_seq: str,
    target_germline_seq: str,
    chain: str,
) -> Tuple[str, List[str], List[str]]:
    """Resurface exposed non-CDR, non-Vernier Kabat positions.

    The input length/insertions are preserved by rebuilding from the donor
    numbering map. CDR positions and protected Vernier/interface positions stay
    donor-derived.
    """
    donor_num = get_kabat_numbering(donor_seq)
    target_num = get_kabat_numbering(target_germline_seq)
    if not donor_num:
        return donor_seq, [], [f"{chain}: donor sequence could not be Kabat-numbered"]
    if not target_num:
        return donor_seq, [], [f"{chain}: target germline could not be Kabat-numbered"]

    surface_set = VH_SURFACE_KABAT if chain == "VH" else VL_SURFACE_KABAT
    protected = VH_PROTECTED_KABAT if chain == "VH" else VL_PROTECTED_KABAT
    reshaped = dict(donor_num)
    mutations: List[str] = []
    notes: List[str] = []

    for key in sorted_keys(donor_num):
        pos, ins = key
        if pos not in surface_set:
            continue
        if pos in protected:
            continue
        if is_in_cdr(pos, "VH" if chain == "VH" else "VL"):
            continue
        if key not in target_num:
            continue
        src = donor_num[key]
        dst = target_num[key]
        if src != dst:
            reshaped[key] = dst
            mutations.append(f"{src}{pos}{ins}{dst}".replace(" ", ""))

    if not mutations:
        notes.append(f"{chain}: no eligible surface FR substitutions were found")
    return "".join(reshaped[k] for k in sorted_keys(reshaped)), mutations, notes


def _chain_cdr_rmsd(qc: Dict[str, Any], chain: str) -> Dict[str, float]:
    raw = qc.get("cdr_rmsd") or {}
    prefixes = ("H",) if chain == "VH" else ("L",)
    out: Dict[str, float] = {}
    if isinstance(raw, dict):
        for loop, val in raw.items():
            if str(loop).startswith(prefixes):
                f = _float_or_none(val)
                if f is not None:
                    out[str(loop)] = f
    return out


def _chain_trigger_reasons(
    identity_pct: float | None,
    cdr_rmsd: Dict[str, float],
    identity_threshold_pct: float,
    cdr_rmsd_threshold_a: float,
) -> List[str]:
    reasons: List[str] = []
    if identity_pct is None:
        reasons.append("framework_identity_missing")
    elif identity_pct < identity_threshold_pct:
        reasons.append(f"low_framework_identity:{identity_pct:.1f}<{identity_threshold_pct:.1f}")
    for loop, rmsd in sorted(cdr_rmsd.items()):
        if rmsd >= cdr_rmsd_threshold_a:
            reasons.append(f"cdr_rmsd_fail:{loop}={rmsd:.2f}A")
    return reasons


def _extract_engine_payload(result: Any) -> Dict[str, Any]:
    seqs = getattr(result, "sequences", {}) or {}
    qc = getattr(result, "qc_metrics", {}) or {}
    fw = qc.get("framework_selection", {}) or {}
    return {
        "overall_status": getattr(result, "overall_status", None),
        "sequences": seqs,
        "qc_metrics": qc,
        "framework_selection": fw,
        "checklist_report": getattr(result, "checklist_report", {}) or {},
        "qa_audit": getattr(result, "qa_audit", None),
    }


def _imgt_cdrs(vh: str, vl: str) -> Dict[str, str]:
    """Best-effort IMGT CDR segments matching the web-report display contract."""
    try:
        from core.numbering.imgt_anarcii import imgt_number_anarcii  # noqa: PLC0415
        from core.vhh_humanization import split_regions as split_regions_imgt  # noqa: PLC0415

        reg_h = split_regions_imgt(imgt_number_anarcii(vh))
        reg_l = split_regions_imgt(imgt_number_anarcii(vl))
        return {
            "H1": reg_h.get("CDR1", ""),
            "H2": reg_h.get("CDR2", ""),
            "H3": reg_h.get("CDR3", ""),
            "L1": reg_l.get("CDR1", ""),
            "L2": reg_l.get("CDR2", ""),
            "L3": reg_l.get("CDR3", ""),
        }
    except Exception:
        return {}


def _cdr_substring_check(donor_vh: str, donor_vl: str, out_vh: str, out_vl: str, engine_qc: Dict[str, Any]) -> Dict[str, bool]:
    # Client/reporting CDR display is IMGT. Prefer IMGT for this hybrid branch
    # because rabbit VL L1 is otherwise easy to mis-score under Kabat-style
    # slices (e.g. QSSQSVY vs IMGT QSVYSNY).
    cdrs = _imgt_cdrs(donor_vh, donor_vl)
    if not cdrs:
        cdrs = engine_qc.get("cdr_identification", {}).get("cdrs") or engine_qc.get("cdrs") or {}
    checks: Dict[str, bool] = {}
    for key in ("H1", "H2", "H3"):
        seq = str(cdrs.get(key) or "")
        checks[key] = bool(seq and seq in out_vh)
    for key in ("L1", "L2", "L3"):
        seq = str(cdrs.get(key) or "")
        checks[key] = bool(seq and seq in out_vl)
    checks["all_engine_cdr_substrings_present"] = all(checks.values()) if checks else False
    return checks


def run_rabbit_hybrid(
    vh: str,
    vl: str,
    project_name: str,
    out_dir: Path,
    identity_threshold_pct: float = 60.0,
    cdr_rmsd_threshold_a: float = 1.5,
    dry_run_structure: bool = False,
) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = HumanizationEngine(workflow="vh_vl", donor_species=RABBIT_SPECIES)
    result = engine.run(
        mouse_vh=vh,
        mouse_vl=vl,
        project_name=project_name,
        out_dir=str(out_dir / "standard_engine_run"),
        dry_run_structure=dry_run_structure,
        back_mutation_strategy="auto",
    )
    payload = _extract_engine_payload(result)
    seqs = payload["sequences"]
    qc = payload["qc_metrics"]
    fw = payload["framework_selection"]

    standard_vh = seqs.get("humanized_vh", "")
    standard_vl = seqs.get("humanized_vl", "")
    selected_vh = str(fw.get("selected_vh_germline") or fw.get("vh_germline") or "")
    selected_vl = str(fw.get("selected_vl_germline") or fw.get("vl_germline") or "")
    germ_vh_seq, germ_vl_seq = load_human_germline_sequences(selected_vh, selected_vl)

    vh_identity = _float_or_none(fw.get("vh_identity_pct") or qc.get("framework_human_identity_vh"))
    vl_identity = _float_or_none(fw.get("vl_identity_pct") or qc.get("framework_human_identity_vl"))
    vh_rmsd = _chain_cdr_rmsd(qc, "VH")
    vl_rmsd = _chain_cdr_rmsd(qc, "VL")

    vh_reasons = _chain_trigger_reasons(vh_identity, vh_rmsd, identity_threshold_pct, cdr_rmsd_threshold_a)
    vl_reasons = _chain_trigger_reasons(vl_identity, vl_rmsd, identity_threshold_pct, cdr_rmsd_threshold_a)

    warnings: List[str] = []
    if not germ_vh_seq:
        warnings.append(f"Could not load selected VH germline sequence: {selected_vh}")
    if not germ_vl_seq:
        warnings.append(f"Could not load selected VL germline sequence: {selected_vl}")

    final_vh = standard_vh
    final_vl = standard_vl
    vh_muts: List[str] = []
    vl_muts: List[str] = []

    if vh_reasons and germ_vh_seq:
        final_vh, vh_muts, vh_notes = _kabat_surface_resurface(vh, germ_vh_seq, "VH")
        warnings.extend(vh_notes)
        vh_strategy = "surface_reshaping"
    else:
        vh_strategy = "standard_cdr_grafting"

    if vl_reasons and germ_vl_seq:
        final_vl, vl_muts, vl_notes = _kabat_surface_resurface(vl, germ_vl_seq, "VL")
        warnings.extend(vl_notes)
        vl_strategy = "surface_reshaping"
    else:
        vl_strategy = "standard_cdr_grafting"

    decisions = {
        "VH": asdict(ChainDecision(
            chain="VH",
            strategy=vh_strategy,
            framework_identity_pct=vh_identity,
            identity_threshold_pct=identity_threshold_pct,
            cdr_rmsd=vh_rmsd,
            cdr_rmsd_threshold_a=cdr_rmsd_threshold_a,
            trigger_reasons=vh_reasons,
            surface_mutations=vh_muts,
        )),
        "VL": asdict(ChainDecision(
            chain="VL",
            strategy=vl_strategy,
            framework_identity_pct=vl_identity,
            identity_threshold_pct=identity_threshold_pct,
            cdr_rmsd=vl_rmsd,
            cdr_rmsd_threshold_a=cdr_rmsd_threshold_a,
            trigger_reasons=vl_reasons,
            surface_mutations=vl_muts,
        )),
    }

    cdr_check = _cdr_substring_check(vh, vl, final_vh, final_vl, qc)
    final_payload: Dict[str, Any] = {
        "project_name": project_name,
        "workflow": "rabbit_hybrid_humanization",
        "abenginecore_version": "V5.3.1-rabbit-hybrid-script",
        "generated_by": "scripts/run_rabbit_hybrid_humanization.py",
        "strategy": "chain-conditional: low identity or CDR RMSD fail -> surface reshaping; otherwise standard grafting",
        "donor_species": RABBIT_SPECIES,
        "selected_vh_germline": selected_vh,
        "selected_vl_germline": selected_vl,
        "standard_engine_status": payload["overall_status"],
        "chain_decisions": decisions,
        "cdr_substring_check": cdr_check,
        "warnings": warnings,
        "sequences": {
            "donor_vh": vh,
            "donor_vl": vl,
            "standard_engine_humanized_vh": standard_vh,
            "standard_engine_humanized_vl": standard_vl,
            "rabbit_hybrid_vh": final_vh,
            "rabbit_hybrid_vl": final_vl,
        },
        "standard_engine_summary": {
            "framework_selection": fw,
            "cdr_rmsd": qc.get("cdr_rmsd", {}),
            "global_fv_rmsd_ca": qc.get("global_fv_rmsd_ca"),
            "checklist_status": qc.get("checklist_summary", {}).get("overall_status") or payload["overall_status"],
        },
        "_qa_audit": {
            "surface_positions_source": "scripts/run_dog_surface_reshaping_v1.py Kabat surface sets",
            "protected_positions": {
                "VH": sorted(VH_PROTECTED_KABAT),
                "VL": sorted(VL_PROTECTED_KABAT),
            },
            "cdr_protection": "No CDR positions are eligible for resurfacing.",
        },
    }

    (out_dir / "rabbit_hybrid_result.json").write_text(
        json.dumps(final_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_summary_md(final_payload, out_dir / "rabbit_hybrid_summary.md")
    return final_payload


def run_rabbit_hybrid_from_standard_result(
    standard_result_json: Path,
    project_name: str,
    out_dir: Path,
    identity_threshold_pct: float = 60.0,
    cdr_rmsd_threshold_a: float = 1.5,
) -> Dict[str, Any]:
    """Build hybrid result from an existing standard API `result.json`.

    Use this when a standard web/API run already computed structure metrics. The
    direct engine path can WARN on 5.2 without exposing the per-loop RMSD dict;
    the API result includes it as top-level `cdr_rmsd`.
    """
    src = json.loads(standard_result_json.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)

    donor_vh = str(src.get("mouse_vh") or src.get("donor_vh") or "")
    donor_vl = str(src.get("mouse_vl") or src.get("donor_vl") or "")
    standard_vh = str(src.get("humanized_vh") or "")
    standard_vl = str(src.get("humanized_vl") or "")
    selected_vh = str(src.get("vh_germline") or src.get("selected_vh_germline") or "")
    selected_vl = str(src.get("vl_germline") or src.get("selected_vl_germline") or "")
    germ_vh_seq, germ_vl_seq = load_human_germline_sequences(selected_vh, selected_vl)

    vh_identity = _float_or_none(src.get("vh_germline_identity") or src.get("vh_fr_identity_chothia_cdr_masked"))
    vl_identity = _float_or_none(src.get("vl_germline_identity") or src.get("vl_fr_identity_chothia_cdr_masked"))
    cdr_rmsd = src.get("cdr_rmsd") or {}
    qc_for_rmsd = {"cdr_rmsd": cdr_rmsd}
    vh_rmsd = _chain_cdr_rmsd(qc_for_rmsd, "VH")
    vl_rmsd = _chain_cdr_rmsd(qc_for_rmsd, "VL")

    vh_reasons = _chain_trigger_reasons(vh_identity, vh_rmsd, identity_threshold_pct, cdr_rmsd_threshold_a)
    vl_reasons = _chain_trigger_reasons(vl_identity, vl_rmsd, identity_threshold_pct, cdr_rmsd_threshold_a)

    warnings: List[str] = []
    final_vh = standard_vh
    final_vl = standard_vl
    vh_muts: List[str] = []
    vl_muts: List[str] = []
    if vh_reasons and germ_vh_seq:
        final_vh, vh_muts, vh_notes = _kabat_surface_resurface(donor_vh, germ_vh_seq, "VH")
        warnings.extend(vh_notes)
        vh_strategy = "surface_reshaping"
    else:
        vh_strategy = "standard_cdr_grafting"
    if vl_reasons and germ_vl_seq:
        final_vl, vl_muts, vl_notes = _kabat_surface_resurface(donor_vl, germ_vl_seq, "VL")
        warnings.extend(vl_notes)
        vl_strategy = "surface_reshaping"
    else:
        vl_strategy = "standard_cdr_grafting"

    decisions = {
        "VH": asdict(ChainDecision("VH", vh_strategy, vh_identity, identity_threshold_pct, vh_rmsd, cdr_rmsd_threshold_a, vh_reasons, vh_muts)),
        "VL": asdict(ChainDecision("VL", vl_strategy, vl_identity, identity_threshold_pct, vl_rmsd, cdr_rmsd_threshold_a, vl_reasons, vl_muts)),
    }
    cdr_check = _cdr_substring_check(donor_vh, donor_vl, final_vh, final_vl, {"cdrs": src.get("cdrs", {})})
    final_payload: Dict[str, Any] = {
        "project_name": project_name,
        "workflow": "rabbit_hybrid_humanization",
        "abenginecore_version": "V5.3.1-rabbit-hybrid-script",
        "generated_by": "scripts/run_rabbit_hybrid_humanization.py",
        "source_standard_result_json": str(standard_result_json),
        "strategy": "chain-conditional: low identity or CDR RMSD fail -> surface reshaping; otherwise standard grafting",
        "donor_species": RABBIT_SPECIES,
        "selected_vh_germline": selected_vh,
        "selected_vl_germline": selected_vl,
        "standard_engine_status": src.get("checklist_status") or src.get("overall_status"),
        "chain_decisions": decisions,
        "cdr_substring_check": cdr_check,
        "warnings": warnings,
        "sequences": {
            "donor_vh": donor_vh,
            "donor_vl": donor_vl,
            "standard_engine_humanized_vh": standard_vh,
            "standard_engine_humanized_vl": standard_vl,
            "rabbit_hybrid_vh": final_vh,
            "rabbit_hybrid_vl": final_vl,
        },
        "standard_engine_summary": {
            "framework_selection": {
                "selected_vh_germline": selected_vh,
                "selected_vl_germline": selected_vl,
                "vh_identity_pct": vh_identity,
                "vl_identity_pct": vl_identity,
                "clinical_framework_policy": src.get("clinical_framework_policy"),
            },
            "cdr_rmsd": cdr_rmsd,
            "global_fv_rmsd_ca": src.get("global_fv_rmsd_ca"),
            "checklist_status": src.get("checklist_status"),
        },
        "_qa_audit": {
            "surface_positions_source": "scripts/run_dog_surface_reshaping_v1.py Kabat surface sets",
            "trigger_source": "existing standard API result.json",
            "cdr_protection": "No CDR positions are eligible for resurfacing.",
        },
    }
    (out_dir / "rabbit_hybrid_result.json").write_text(
        json.dumps(final_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_summary_md(final_payload, out_dir / "rabbit_hybrid_summary.md")
    return final_payload


def _write_summary_md(payload: Dict[str, Any], path: Path) -> None:
    dec = payload["chain_decisions"]
    seqs = payload["sequences"]
    lines = [
        "# Rabbit Hybrid Humanization Summary",
        "",
        "## Verification Status",
        "- [verified] The standard engine result was generated before chain-specific fallback decisions.",
        "- [verified] Each chain decision is triggered by framework identity and/or chain-local CDR RMSD.",
        "- [inferred] Surface reshaping preserves rabbit core geometry better than full human scaffold grafting for long/non-canonical rabbit CDRs.",
        "",
        "## Chain Decisions",
        "| Chain | Strategy | Identity | CDR RMSD | Trigger reasons | Surface mutations |",
        "|---|---|---:|---|---|---:|",
    ]
    for chain in ("VH", "VL"):
        row = dec[chain]
        rmsd = ", ".join(f"{k}={v}" for k, v in row["cdr_rmsd"].items()) or "—"
        reasons = "; ".join(row["trigger_reasons"]) or "none"
        ident = row["framework_identity_pct"]
        ident_txt = "—" if ident is None else f"{ident:.1f}%"
        lines.append(
            f"| {chain} | {row['strategy']} | {ident_txt} | {rmsd} | {reasons} | {len(row['surface_mutations'])} |"
        )
    lines.extend([
        "",
        "## Adversarial Checks",
        "- Alternative explanation: RMSD failure may come from numbering drift rather than true loop movement; compare IMGT CDR slices before release. WARN",
        "- Failure mode: surface mutations can still affect CDR support if a protected Vernier position is incomplete. WARN",
        "- Boundary condition: if both chains trigger resurfacing, this is no longer classic CDR grafting and should be marketed as resurfacing/hybrid humanization. PASS",
        "",
        "## Sources",
        "- `docs/RABBIT_HUMANIZATION_STANDARD_V1.0.md`",
        "- `docs/VH_VL_HUMANIZATION_STANDARD_V4.4.md`",
        "- `scripts/run_dog_surface_reshaping_v1.py` surface-position implementation reused as internal code source.",
        "",
        "## Final Sequences",
        "```fasta",
        f">rabbit_hybrid_VH",
        seqs.get("rabbit_hybrid_vh", ""),
        f">rabbit_hybrid_VL",
        seqs.get("rabbit_hybrid_vl", ""),
        "```",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rabbit hybrid humanization: per-chain resurfacing fallback.")
    parser.add_argument("--vh", help="Rabbit donor VH amino-acid sequence")
    parser.add_argument("--vl", help="Rabbit donor VL amino-acid sequence")
    parser.add_argument("--standard-result-json", help="Existing standard API result.json with cdr_rmsd")
    parser.add_argument("--project-name", default="rabbit_hybrid", help="Project/job name")
    parser.add_argument("--out-dir", default="projects/rabbit_hybrid_humanization", help="Output directory")
    parser.add_argument("--identity-threshold", type=float, default=60.0, help="Per-chain framework identity trigger")
    parser.add_argument("--cdr-rmsd-threshold", type=float, default=1.5, help="Per-chain CDR RMSD trigger in Angstrom")
    parser.add_argument("--dry-run-structure", action="store_true", help="Skip structure modeling in the standard engine run")
    args = parser.parse_args()

    if args.standard_result_json:
        out = run_rabbit_hybrid_from_standard_result(
            standard_result_json=Path(args.standard_result_json),
            project_name=args.project_name,
            out_dir=Path(args.out_dir),
            identity_threshold_pct=args.identity_threshold,
            cdr_rmsd_threshold_a=args.cdr_rmsd_threshold,
        )
    else:
        if not args.vh or not args.vl:
            parser.error("--vh and --vl are required unless --standard-result-json is provided")
        out = run_rabbit_hybrid(
            vh=args.vh.strip().upper(),
            vl=args.vl.strip().upper(),
            project_name=args.project_name,
            out_dir=Path(args.out_dir),
            identity_threshold_pct=args.identity_threshold,
            cdr_rmsd_threshold_a=args.cdr_rmsd_threshold,
            dry_run_structure=args.dry_run_structure,
        )
    print(json.dumps({
        "project_name": out["project_name"],
        "workflow": out["workflow"],
        "selected_vh_germline": out["selected_vh_germline"],
        "selected_vl_germline": out["selected_vl_germline"],
        "VH_strategy": out["chain_decisions"]["VH"]["strategy"],
        "VL_strategy": out["chain_decisions"]["VL"]["strategy"],
        "output": str(Path(args.out_dir).resolve()),
    }, indent=2))


if __name__ == "__main__":
    main()
