#!/usr/bin/env python3
"""
 muMAb4D5 → V4.4.1 ， huMAb4D5-8（trastuzumab Fv） QA 。

：`data/sequence_cache/mumab4d5_verified.fasta`
  - ：>muMAb4D5_VH / >muMAb4D5_VL（VL  C  RT → 107 aa， SEQ ID NO:41 /  Kabat FR4 ）
  -  Fv：>huMAb4D5-8_VH / >huMAb4D5-8_VL（107 aa ）

： `run_vhvl_v44_pipeline.py`，：IGHV3-23*01 + IGKV1-39*01。

 QA：
  - ： Fab  ABodyBuilder2 （pipeline  *_mouse.pdb）
  - AbEvaluator：`delta_vs_mouse` + `structure_13param`（ pipeline ）
  -  `pairwise_clinical_vs_de_novo`：`validate_humanization.run_comparison`（ PDB vs  PDB）

：
  python scripts/run_mumab4d5_spliced_v441_compare_clinical.py
  python scripts/run_mumab4d5_spliced_v441_compare_clinical.py --compare-only   #  results.json 

：ImmuneBuilder（ IMMUNEBUILDER_PYTHON）；。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

AA_LINE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY]+$")
FASTA_PATH = SUITE / "data" / "sequence_cache" / "mumab4d5_verified.fasta"
AB_ID = "mumab4d5_spliced"
#  Fv （US5821337 / 1FVC）
FORCE_VH = "IGHV3-23*01"
FORCE_VL = "IGKV1-39*01"


def _seq_after_marker(text: str, header_substr: str) -> str:
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith(">") and header_substr in ln:
            for j in range(i + 1, len(lines)):
                s = lines[j].strip()
                if s.startswith(";"):
                    continue
                if s.startswith(">"):
                    continue
                if AA_LINE.match(s):
                    return s
            break
    raise ValueError(f"No amino-acid sequence found after header containing {header_substr!r}")


def _load_parent_and_clinical() -> Tuple[str, str, str, str]:
    raw = FASTA_PATH.read_text(encoding="utf-8", errors="replace")
    vh_m = _seq_after_marker(raw, "muMAb4D5_VH")
    vl_m = _seq_after_marker(raw, "muMAb4D5_VL")
    if vl_m.endswith("RT") and len(vl_m) >= 109:
        vl_m = vl_m[:-2]
    vh_h = _seq_after_marker(raw, "huMAb4D5-8_VH")
    # Use "huMAb4D5-8_VL |" so we do not match >huMAb4D5-8_VL_RCSDisplay
    vl_h = _seq_after_marker(raw, "huMAb4D5-8_VL |")
    if vl_h.endswith("RT"):
        vl_h = vl_h[:-2]
    return vh_m, vl_m, vh_h, vl_h


def _run_pipeline() -> None:
    vh_m, vl_m, _, _ = _load_parent_and_clinical()
    old = sys.argv[:]
    sys.argv = [
        "run_vhvl_v44_pipeline.py",
        "--id",
        AB_ID,
        "--vh",
        vh_m,
        "--vl",
        vl_m,
        "--force-germline-vh",
        FORCE_VH,
        "--force-germline-vl",
        FORCE_VL,
        "--skip-verify",
    ]
    try:
        from scripts.run_vhvl_v44_pipeline import main as pipe_main

        rc = pipe_main()
        if rc != 0:
            raise SystemExit(rc)
    finally:
        sys.argv = old


def _eval_block(ev: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(ev, dict):
        return {"status": "missing"}
    res = ev.get("results") or {}
    st = res.get("structure_13param") or {}
    dm = res.get("delta_vs_mouse") or {}
    metrics = (st.get("metrics") or {}) if st.get("status") == "PASS" else {}
    delta = (dm.get("delta") or {}) if dm.get("status") == "PASS" else {}
    return {
        "overall_status": ev.get("overall_status"),
        "structure_13param_status": st.get("status"),
        "vh_vl_angle_deg": metrics.get("vh_vl_angle_deg"),
        "vernier_dual_numbering_n": len(metrics.get("vernier_dual_numbering") or []),
        "delta_vs_mouse_status": dm.get("status"),
        "angle_delta_vs_parent": (delta.get("vh_vl_angle") or {}).get("delta"),
        "angle_gate_pass": (delta.get("vh_vl_angle") or {}).get("pass"),
        "rmsd_global": delta.get("rmsd_global"),
        "delta_conclusion": delta.get("conclusion"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="muMAb4D5 spliced V4.4.1 vs clinical structure QA")
    ap.add_argument(
        "--compare-only",
        action="store_true",
        help="Skip pipeline; read projects/%s_Redesign/%s_results.json and PDBs only."
        % (AB_ID, AB_ID),
    )
    args = ap.parse_args()

    project_dir = SUITE / "projects" / f"{AB_ID}_Redesign"
    structures_dir = project_dir / "structures"
    results_path = project_dir / f"{AB_ID}_results.json"

    if not args.compare_only:
        _run_pipeline()

    if not results_path.exists():
        print(f"[FATAL] Missing {results_path}", file=sys.stderr)
        return 2

    results = json.loads(results_path.read_text(encoding="utf-8"))
    seq = results.get("sequences") or {}
    final_v = str(results.get("_meta", {}).get("final_version") or "v1")
    final_tag = final_v if final_v in ("v1", "v2") else "v1"
    rel_mouse = (results.get("structure") or {}).get("mouse_pdb")
    pdb_mouse = SUITE / rel_mouse if rel_mouse else (structures_dir / f"{AB_ID}_mouse.pdb")
    key_pdb = "v2_pdb" if final_tag == "v2" and results.get("structure", {}).get("v2_pdb") else "v1_pdb"
    rel_hp = (results.get("structure") or {}).get(key_pdb) or (results.get("structure") or {}).get("v1_pdb")
    pdb_denovo = (SUITE / rel_hp) if rel_hp else (structures_dir / f"{AB_ID}_humanized_{final_tag}.pdb")

    _, _, vh_clin, vl_clin = _load_parent_and_clinical()
    pdb_clinical = structures_dir / f"{AB_ID}_clinical_huMAb4D5-8_predicted.pdb"

    if not pdb_mouse.exists() or not pdb_denovo.exists():
        print(
            "[FATAL] Missing mouse or de novo PDB. Check ImmuneBuilder / paths:\n"
            f"  mouse={pdb_mouse}\n  de_novo={pdb_denovo}",
            file=sys.stderr,
        )
        return 3

    if not pdb_clinical.exists():
        from scripts.run_vhvl_v44_pipeline import _run_immunebuilder_via_script  # noqa: PLC0415

        ok, err = _run_immunebuilder_via_script(vh_clin, vl_clin, pdb_clinical)
        if not ok:
            print(f"[FATAL] Clinical Fab prediction failed: {err}", file=sys.stderr)
            return 4

    from core.evaluation.evaluator import AbEvaluator, AntibodyType  # noqa: PLC0415

    ev_clinical = AbEvaluator(
        project_name=f"{AB_ID}_clinical_ref",
        ab_type=AntibodyType.HUMANIZED,
        pdb_path=str(pdb_clinical),
        ref_pdb_path=str(pdb_mouse),
        vh_seq=vh_clin,
        vl_seq=vl_clin,
        strict_qa=False,
        use_iedb=False,
    )
    r_clinical = ev_clinical.run(
        modules=["structure_13param", "cdr_scan", "developability", "immunogenicity", "delta_vs_mouse"]
    )
    clinical_summary = {
        "sequences": {"VH": vh_clin, "VL": vl_clin},
        "pdb": str(pdb_clinical.relative_to(SUITE)).replace("\\", "/"),
        "evaluator": _eval_block(
            {
                "overall_status": r_clinical.overall_status,
                "results": r_clinical.results,
            }
        ),
    }

    internal = results.get("_internal") or {}
    ev_dn_final = internal.get("evaluation_v2") if final_tag == "v2" else internal.get("evaluation_v1")
    de_novo_summary = {
        "final_version": final_tag,
        "sequences": {
            "VH": seq.get(f"{final_tag}_VH") or seq.get("v2_VH") or seq.get("v1_VH"),
            "VL": seq.get(f"{final_tag}_VL") or seq.get("v2_VL") or seq.get("v1_VL"),
        },
        "pdb": str(pdb_denovo.relative_to(SUITE)).replace("\\", "/"),
        "evaluator": _eval_block(ev_dn_final),
    }

    pairwise: Dict[str, Any] = {}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "validate_humanization",
            str(SUITE / "scripts" / "validate_humanization.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        if hasattr(mod, "run_comparison"):
            pairwise["clinical_pdb_ref__de_novo_target"] = mod.run_comparison(
                str(pdb_clinical), str(pdb_denovo)
            )
            pairwise["de_novo_ref__clinical_target"] = mod.run_comparison(
                str(pdb_denovo), str(pdb_clinical)
            )
    except Exception as e:
        pairwise["error"] = str(e)

    out: Dict[str, Any] = {
        "_meta": {
            "standard": "VH/VL Humanization V4.4.1 (config vh_vl_humanization_v44.json)",
            "parent_fasta": str(FASTA_PATH.relative_to(SUITE)).replace("\\", "/"),
            "forced_germline": {"VH": FORCE_VH, "VL": FORCE_VL},
            "reference_mouse_pdb": str(pdb_mouse.relative_to(SUITE)).replace("\\", "/"),
            "note": (
                "Both clinical and de novo humanized Fabs are evaluated vs the SAME predicted "
                "parent (spliced muMAb4D5) structure for delta_vs_mouse comparability."
            ),
        },
        "clinical_huMAb4D5_8": clinical_summary,
        "de_novo_humanized_from_spliced_parent": de_novo_summary,
        "pairwise_predicted_fabs": pairwise,
    }

    out_dir = project_dir / "internal"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "structure_fidelity_vs_clinical.json"
    out_json.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    pw = pairwise.get("clinical_pdb_ref__de_novo_target") or {}
    cdr_mx = pw.get("cdr_rmsd_max")
    pw_conc = pw.get("conclusion")
    md_lines = [
        f"# muMAb4D5 spliced parent — V4.4.1 vs clinical structure QA",
        "",
        f"- Output: `{out_json.relative_to(SUITE).as_posix()}`",
        f"- Parent mouse PDB (common ref): `{out['_meta']['reference_mouse_pdb']}`",
        "",
        "## Clinical huMAb4D5-8 (predicted Fab)",
        f"- VH/VL angle (predicted): {clinical_summary['evaluator'].get('vh_vl_angle_deg')}",
        f"- vs spliced parent: angle_delta {clinical_summary['evaluator'].get('angle_delta_vs_parent')}° (gate {clinical_summary['evaluator'].get('angle_gate_pass')})",
        "",
        "## De novo humanized (from spliced parent, pipeline final)",
        f"- version: {de_novo_summary['final_version']}",
        f"- VH/VL angle (predicted): {de_novo_summary['evaluator'].get('vh_vl_angle_deg')}",
        f"- vs spliced parent: angle_delta {de_novo_summary['evaluator'].get('angle_delta_vs_parent')}° (gate {de_novo_summary['evaluator'].get('angle_gate_pass')})",
        "",
        "## Pairwise (clinical predicted vs de novo predicted)",
        f"- VH/VL angle |Δ|: {pw.get('vh_vl_angle', {}).get('delta')}",
        f"- CDR backbone RMSD max (H/L loops): {cdr_mx}",
        f"- `run_comparison` conclusion: {pw_conc}",
        "",
        "Full CDR loop RMSD table: see JSON `pairwise_predicted_fabs.clinical_pdb_ref__de_novo_target.cdr_rmsd`.",
        "",
    ]
    out_md = out_dir / "structure_fidelity_vs_clinical.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"[OK] Wrote {out_json}")
    print(f"[OK] Wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
