"""Augment an existing smart_cmc_result.json with structure-derived CMC metrics
using already-predicted Fv PDB files (baseline_fv.pdb / selected_fv.pdb).

This avoids re-running ImmuneBuilder + the DeepFR generator + balanced_guard on
candidates whose selection logic is sequence-only. Only the
`baseline_snapshot`, `drift_parameters`, `selected_candidate.evaluation`,
and `generator_best_polish_comparison` fields are refreshed; guard decisions
and the chosen sequence are preserved.

Usage:
    conda run -n anarcii python scripts/augment_smart_cmc_with_structure.py \
        --drug-dir projects/clinical_ref_mAbs_smart_cmc/Ipilimumab \
        --aligned-html-name Ipilimumab_SMART_CMC_CONSOLE.html
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

THIS = Path(__file__).resolve()
ROOT = THIS.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.run_smart_cmc_orchestrator import (  # noqa: E402
    SMART_CMC_PROTOCOL_VERSION,
    SMART_CMC_ANALYSIS_VERSION,
    SMART_CMC_REPORT_FORMAT_VERSION,
    _evaluate_regular_block,
    _extract_drift_parameters,
    _build_generator_best_polish_comparison,
    _render_md_report,
    _render_console_style_report,
    _render_console_style_html,
)


def _load_polish_result(drug_dir: Path) -> Dict[str, Any] | None:
    p = drug_dir / "_generator_deepfr_ctx_cmc" / "polish_result.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def augment_one(drug_dir: Path,
                aligned_html_name: str | None,
                bump_versions: bool = True) -> None:
    json_path = drug_dir / "smart_cmc_result.json"
    if not json_path.is_file():
        print(f"  [skip] {drug_dir.name}: smart_cmc_result.json missing")
        return

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    origin = payload.get("origin") or "fully_human"

    baseline_eval_old = payload.get("baseline_snapshot") or {}
    base_vh = baseline_eval_old.get("vh_sequence")
    base_vl = baseline_eval_old.get("vl_sequence")

    selected_old = payload.get("selected_candidate") or {}
    selected_eval_old = selected_old.get("evaluation") or {}
    sel_vh = selected_eval_old.get("vh_sequence") or base_vh
    sel_vl = selected_eval_old.get("vl_sequence") or base_vl

    baseline_pdb = drug_dir / "baseline_fv.pdb"
    selected_pdb = drug_dir / "selected_fv.pdb"
    if not baseline_pdb.is_file():
        print(f"  [skip] {drug_dir.name}: baseline_fv.pdb missing -> use --predict-structure rerun")
        return
    if not selected_pdb.is_file():
        # If selected sequence equals baseline, reuse baseline pdb as selected
        if sel_vh == base_vh and sel_vl == base_vl:
            selected_pdb = baseline_pdb
            print(f"  [info] {drug_dir.name}: selected==baseline; reusing baseline_fv.pdb for selected")
        else:
            print(f"  [skip] {drug_dir.name}: selected_fv.pdb missing and selected != baseline")
            return

    print(f"  [eval] {drug_dir.name}: re-evaluating baseline with {baseline_pdb.name}")
    baseline_eval_new = _evaluate_regular_block(
        base_vh, base_vl, origin, fv_pdb_path=baseline_pdb,
    )
    drift_new = _extract_drift_parameters(
        baseline_eval_new["regular_ab_developability"]
    )
    print(f"  [eval] {drug_dir.name}: re-evaluating selected with {selected_pdb.name}")
    selected_eval_new = _evaluate_regular_block(
        sel_vh, sel_vl, origin, fv_pdb_path=selected_pdb,
    )

    payload["baseline_snapshot"] = baseline_eval_new
    payload["drift_parameters"] = drift_new
    if selected_old:
        selected_old["evaluation"] = selected_eval_new
        payload["selected_candidate"] = selected_old

    polish_result = _load_polish_result(drug_dir) or {}
    guard_rows = payload.get("guard_results_top") or []
    payload["generator_best_polish_comparison"] = _build_generator_best_polish_comparison(
        baseline_eval_new, polish_result, guard_rows, payload.get("selected_candidate"),
    )

    versioning = payload.setdefault("versioning", {})
    if bump_versions:
        versioning["protocol_version"] = SMART_CMC_PROTOCOL_VERSION
        versioning["analysis_version"] = SMART_CMC_ANALYSIS_VERSION
        versioning["report_format_version"] = SMART_CMC_REPORT_FORMAT_VERSION

    versioning.setdefault("structure_augmentation", {})
    versioning["structure_augmentation"] = {
        "applied": True,
        "baseline_fv_pdb": str(baseline_pdb),
        "selected_fv_pdb": str(selected_pdb),
        "method": "augment_smart_cmc_with_structure.py (sequence-only guard preserved)",
    }

    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  [json] {drug_dir.name}: smart_cmc_result.json updated")

    md_path = drug_dir / "SMART_CMC_WEB_CONSOLE_STYLE.md"
    html_path = drug_dir / "SMART_CMC_WEB_CONSOLE_STYLE.html"
    audit_path = drug_dir / "SMART_CMC_AUDIT.md"
    _render_md_report(audit_path, payload)
    _render_console_style_report(md_path, payload)
    _render_console_style_html(html_path, payload)
    if aligned_html_name:
        (drug_dir / aligned_html_name).write_text(
            html_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
        print(f"  [aligned] {aligned_html_name}")
    print(f"  [ok] {drug_dir.name}: structure-augmented + reports refreshed")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drug-dir", action="append", required=True)
    ap.add_argument("--aligned-html-name", action="append", default=None)
    ap.add_argument("--no-bump", action="store_true")
    args = ap.parse_args()

    aligned = args.aligned_html_name or []
    print(
        f"Augmenting with versions: protocol={SMART_CMC_PROTOCOL_VERSION} "
        f"analysis={SMART_CMC_ANALYSIS_VERSION} "
        f"report_format={SMART_CMC_REPORT_FORMAT_VERSION}"
    )
    for i, d in enumerate(args.drug_dir):
        ah = aligned[i] if i < len(aligned) else None
        augment_one(Path(d), aligned_html_name=ah, bump_versions=not args.no_bump)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
