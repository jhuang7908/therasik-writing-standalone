#!/usr/bin/env python3
"""
abenginecore.py — Unified CLI entry for AbEngineCore
====================================================

Goal: provide a single, stable command to run the standard VH/VL project gate:
  - verify (V4.4) + optional fix (render report, PDF, package)
  - Phase4→Phase5 Vernier second-round rescue is executed inside verify --fix

Examples (Windows / PowerShell):
  python abenginecore.py verify fxy_2c2 projects/fxy_2c2_Redesign
  python abenginecore.py fix    fxy_2c2 projects/fxy_2c2_Redesign

Or use the wrapper:
  .\\abenginecore.cmd fix fxy_2c2 projects\\fxy_2c2_Redesign
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import json
import csv


SCRIPT_DIR = Path(__file__).resolve().parent
SUITE_ROOT = SCRIPT_DIR.parent
for p in (SUITE_ROOT, SCRIPT_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def _cmd_verify(
    ab_id: str,
    project_dir: str,
    fix: bool,
    use_iedb: bool = False,
    skip_pdf: bool = True,
) -> int:
    from scripts.verify_vhvl_v44_project import verify  # noqa: PLC0415

    return int(
        verify(
            ab_id=ab_id,
            project_dir=Path(project_dir),
            fix=fix,
            use_iedb=use_iedb,
            skip_pdf=skip_pdf,
        )
    )


def _cmd_package(ab_id: str, project_dir: str, make_zip: bool) -> int:
    """
    Package delivery only — no gates, no recompute.
    Renders client report (MD→PDF if needed) and assembles delivery directory/ZIP.
    """
    from scripts.package_delivery import package_delivery  # noqa: PLC0415

    package_delivery(ab_id, Path(project_dir), make_zip=make_zip)
    return 0


def _cmd_new(
    ab_id: str,
    vh: str | None,
    vl: str | None,
    vh_fasta: str | None,
    vl_fasta: str | None,
    opt_a: bool,
    force_germline_vh: str | None,
    force_germline_vl: str | None,
) -> int:
    """
    Create new VH/VL humanization project and run full pipeline.
    Equivalent to: python scripts/run_vhvl_v44_pipeline.py --id X --vh "..." --vl "..."
    With --opt-a: forces IGHV3-23*01 when automatic selection yields pI>8.5.
    """
    if vh is None and vl is None:
        if not vh_fasta or not vl_fasta:
            raise ValueError("Provide --vh/--vl sequences or --vh-fasta/--vl-fasta.")
        vh = _read_fasta_sequence(vh_fasta)
        vl = _read_fasta_sequence(vl_fasta)
    if vh is None or vl is None:
        raise ValueError("Both VH and VL sequences are required.")

    argv = [
        "run_vhvl_v44_pipeline.py",
        "--id", ab_id,
        "--vh", vh,
        "--vl", vl,
    ]
    if opt_a:
        argv.extend(["--force-germline-vh", "IGHV3-23*01"])
    if force_germline_vh:
        argv.extend(["--force-germline-vh", force_germline_vh])
    if force_germline_vl:
        argv.extend(["--force-germline-vl", force_germline_vl])

    old_argv = sys.argv
    try:
        sys.argv = argv
        from scripts.run_vhvl_v44_pipeline import main as pipeline_main  # noqa: PLC0415
        return int(pipeline_main())
    finally:
        sys.argv = old_argv


def _cmd_export_internal(ab_id: str, project_dir: str, enrich_immuno: bool) -> int:
    """
    Export internal audit artifacts (JSON/MD/PDF) from existing results.json only.
    Does NOT run verify gates and does NOT recompute structures.
    """
    from scripts.verify_vhvl_v44_project import export_internal_only  # noqa: PLC0415

    return int(export_internal_only(ab_id=ab_id, project_dir=Path(project_dir), enrich_immuno=bool(enrich_immuno)))


def _read_fasta_sequences(fasta_path: str) -> list[dict[str, str]]:
    """
    Read ALL sequences from a FASTA file.

    Returns: list of {"id": header, "sequence": AA}
    """
    p = Path(fasta_path)
    if not p.exists():
        raise FileNotFoundError(f"FASTA file not found: {p}")

    try:
        from Bio import SeqIO  # type: ignore

        out: list[dict[str, str]] = []
        with open(p, "r", encoding="utf-8") as f:
            for record in SeqIO.parse(f, "fasta"):
                seq = str(record.seq).upper().replace("-", "").replace(" ", "")
                if not seq:
                    continue
                out.append({"id": str(record.id), "sequence": seq})
        if not out:
            raise ValueError("FASTA contains no valid sequences")
        return out
    except ImportError:
        # Minimal FASTA fallback
        out: list[dict[str, str]] = []
        cur_id: str | None = None
        cur_lines: list[str] = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if cur_id is not None:
                    seq = "".join(cur_lines).upper().replace("-", "").replace(" ", "")
                    if seq:
                        out.append({"id": cur_id, "sequence": seq})
                cur_id = line[1:].strip() or "seq"
                cur_lines = []
                continue
            if cur_id is None:
                continue
            cur_lines.append(line)
        if cur_id is not None:
            seq = "".join(cur_lines).upper().replace("-", "").replace(" ", "")
            if seq:
                out.append({"id": cur_id, "sequence": seq})
        if not out:
            raise ValueError("FASTA contains no valid sequences")
        return out


def _read_fasta_sequence(fasta_path: str) -> str:
    p = Path(fasta_path)
    if not p.exists():
        raise FileNotFoundError(f"FASTA file not found: {p}")

    try:
        from Bio import SeqIO  # type: ignore

        with open(p, "r", encoding="utf-8") as f:
            record = next(SeqIO.parse(f, "fasta"))
        seq = str(record.seq).upper().replace("-", "").replace(" ", "")
        if not seq:
            raise ValueError("FASTA contains empty sequence")
        return seq
    except ImportError:
        # Minimal FASTA fallback
        seq_lines = []
        started = False
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if started:
                    break
                started = True
                continue
            if started:
                seq_lines.append(line)
        seq = "".join(seq_lines).upper().replace("-", "").replace(" ", "")
        if not seq:
            raise ValueError("FASTA contains no sequence")
        return seq


def _cmd_dog_caninize_auto(
    project_name: str,
    vh: str | None,
    vl: str | None,
    vh_fasta: str | None,
    vl_fasta: str | None,
    out_dir: str | None,
    demo: bool,
) -> int:
    """
    Fully automated dog caninization (structure-gated) with surface-reshaping fallback.
    VHH is intentionally excluded from this unified CLI entry.
    """
    from scripts.run_dog_caninization_auto_v1 import run_pipeline  # noqa: PLC0415

    if demo:
        vh = "QVQLVQSGVEVKKPGASVKVSCKASGYTFTNYYMYWVRQAPGQGLEWMGINPSNGGTNFNEKFKNRVTLTTDSSTTTAYMELKSLQFDDTAVYYCARRDYRFDMGFDYWGQGTTVTVSS"
        vl = "EIVLTQSPATLSLSPGERATLSCRASKGVSTSGYSYLHWYQQKPGQAPRLLIYLASYLESGVPARFSGSGSGTDFTLTISSLEPEDFAVYYCQHSRDLPLTFGGGTKVEIK"
        vh_fasta = None
        vl_fasta = None

    if (vh is None) != (vl is None):
        raise ValueError("Must provide BOTH --vh and --vl, or use --vh-fasta and --vl-fasta.")

    if vh is None and vl is None:
        if not vh_fasta or not vl_fasta:
            raise ValueError("Provide --vh/--vl sequences or --vh-fasta/--vl-fasta.")
        vh = _read_fasta_sequence(vh_fasta)
        vl = _read_fasta_sequence(vl_fasta)

    assert vh is not None and vl is not None
    target_out = Path(out_dir) if out_dir else (SUITE_ROOT / "projects" / project_name / "dog_caninization_auto_v1")
    report_json = run_pipeline(mouse_vh=vh, mouse_vl=vl, project_name=project_name, out_dir=target_out)
    payload = json.loads(Path(report_json).read_text(encoding="utf-8"))
    overall_pass = bool(payload.get("overall_pass"))
    print(str(report_json))
    return 0 if overall_pass else 2


def _cmd_evaluate(
    project_name: str,
    ab_type: str,
    pdb_path: str | None,
    ref_pdb_path: str | None,
    vh_chain: str,
    vl_chain: str,
    vh_seq: str | None,
    vl_seq: str | None,
    antigen_chain: str | None,
    cdr_json_path: str | None,
    modules: list[str] | None,
    out: str | None,
    use_iedb: bool,
    strict_qa: bool,
) -> int:
    from core.evaluation.evaluator import AbEvaluator, AntibodyType  # noqa: PLC0415

    cdr_seqs = None
    if cdr_json_path:
        import json
        p = Path(cdr_json_path)
        if p.exists():
            cdr_seqs = json.loads(p.read_text(encoding="utf-8"))

    ev = AbEvaluator(
        project_name=project_name,
        ab_type=AntibodyType(ab_type),
        pdb_path=pdb_path,
        ref_pdb_path=ref_pdb_path,
        vh_chain=vh_chain,
        vl_chain=vl_chain,
        vh_seq=vh_seq,
        vl_seq=vl_seq,
        antigen_chain=antigen_chain,
        cdr_seqs=cdr_seqs,
        use_iedb=use_iedb,
        strict_qa=strict_qa,
    )
    result = ev.run(modules=modules)

    payload = {
        "project_name": result.project_name,
        "ab_type": result.ab_type.value,
        "overall_status": result.overall_status,
        "modules_run": result.modules_run,
        "overall_flags": result.overall_flags,
        "generated_at": result.generated_at,
        "results": result.results,
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if out:
        op = Path(out)
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0 if result.overall_status != "FAIL" else 2


def _cmd_batch(manifest_csv: str, action: str, continue_on_error: bool, make_zip: bool = False) -> int:
    """
    Batch-run verify/fix/package for multiple VH/VL projects from a CSV manifest.

    CSV columns (header required):
      - ab_id
      - project_dir
    """
    path = Path(manifest_csv)
    if not path.exists():
        raise FileNotFoundError(f"Manifest CSV not found: {path}")

    txt = path.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(txt.splitlines()))
    if not rows:
        raise ValueError("Manifest CSV is empty")
    for k in ("ab_id", "project_dir"):
        if k not in rows[0]:
            raise ValueError("Manifest CSV must have header columns: ab_id, project_dir")

    n_ok = 0
    n_fail = 0
    for i, r in enumerate(rows, start=1):
        ab_id = (r.get("ab_id") or "").strip()
        project_dir = (r.get("project_dir") or "").strip()
        if not ab_id or not project_dir:
            n_fail += 1
            msg = f"[batch] row {i}: missing ab_id/project_dir"
            print(msg, file=sys.stderr)
            if not continue_on_error:
                return 2
            continue
        try:
            if action == "package":
                code = _cmd_package(ab_id=ab_id, project_dir=project_dir, make_zip=make_zip)
            else:
                fix = action == "fix"
                code = _cmd_verify(ab_id=ab_id, project_dir=project_dir, fix=fix)
            if code == 0:
                n_ok += 1
            else:
                n_fail += 1
                if not continue_on_error:
                    return int(code)
        except Exception as e:
            n_fail += 1
            print(f"[batch] row {i}: {ab_id} ERROR: {e}", file=sys.stderr)
            if not continue_on_error:
                return 2

    print(f"[batch] done: ok={n_ok}, fail={n_fail}", file=sys.stderr)
    return 0 if n_fail == 0 else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="abenginecore",
        description="InSynBio AbEngineCore — unified CLI entry.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Common usage:\n"
            "  abenginecore verify   <ab_id> <project_dir>\n"
            "  abenginecore fix      <ab_id> <project_dir>\n"
            "  abenginecore package  <ab_id> <project_dir> [--zip]\n"
            "  abenginecore new      <ab_id> --vh <SEQ> --vl <SEQ> [--opt-a]\n"
            "  abenginecore export-internal <ab_id> <project_dir>\n"
            "  abenginecore dog      --name <project> --vh <SEQ> --vl <SEQ>\n"
            "  abenginecore batch    fix|verify|package --manifest <CSV> [--zip]\n"
            "\n"
            "Notes:\n"
            "  - `fix`: CMC design (if pI>8.5) → Phase4 audit → client report → package delivery\n"
            "  - `package`: delivery-only, no gates, no recompute (use when report/PDB already updated)\n"
            "  - `new`: create project from sequences, supports --opt-a (force IGHV3-23*01)\n"
            "  - `batch package --zip`: batch delivery ZIP without running gates\n"
            "  - Use --use-iedb to enable live IEDB API for immunogenicity\n"
            "  - VHH CLI is intentionally excluded from this unified entry (not yet mature).\n"
        ),
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    p_verify = sub.add_parser("verify", help="Verify a VH/VL project (V4.4 gate).")
    p_verify.add_argument("ab_id", type=str, help="Antibody id (e.g. fxy_2c2)")
    p_verify.add_argument("project_dir", type=str, help="Project directory (e.g. projects/fxy_2c2_Redesign)")
    p_verify.add_argument("--fix", action="store_true", help="Render reports + package delivery.")
    p_verify.add_argument("--use-iedb", action="store_true", help="Enable live IEDB API for immunogenicity (CMC design eval)")
    p_verify.add_argument("--pdf", action="store_true", help="Generate PDF reports (default: skip PDF for speed)")

    p_fix = sub.add_parser("fix", help="Verify + fix (alias for `verify --fix`).")
    p_fix.add_argument("ab_id", type=str, help="Antibody id (e.g. fxy_2c2)")
    p_fix.add_argument("project_dir", type=str, help="Project directory (e.g. projects/fxy_2c2_Redesign)")
    p_fix.add_argument("--use-iedb", action="store_true", help="Enable live IEDB API for immunogenicity (CMC design eval)")
    p_fix.add_argument("--pdf", action="store_true", help="Generate PDF reports (default: skip PDF for speed)")

    p_package = sub.add_parser("package", help="Package delivery only (no gates, no recompute). Render report+PDF, assemble delivery dir/ZIP.")
    p_package.add_argument("ab_id", type=str, help="Antibody id (e.g. fxy_2c2)")
    p_package.add_argument("project_dir", type=str, help="Project directory (e.g. projects/fxy_2c2_Redesign)")
    p_package.add_argument("--zip", action="store_true", help="Generate ZIP archive (default: directory only)")

    p_new = sub.add_parser("new", help="Create new VH/VL humanization project (full pipeline from sequences).")
    p_new.add_argument("ab_id", type=str, help="Antibody id (e.g. my_ab, fxy_2e2_opta)")
    p_new.add_argument("--vh", dest="vh", default=None, help="Mouse VH amino acid sequence.")
    p_new.add_argument("--vl", dest="vl", default=None, help="Mouse VL amino acid sequence.")
    p_new.add_argument("--vh-fasta", dest="vh_fasta", default=None, help="FASTA path for VH (first record used).")
    p_new.add_argument("--vl-fasta", dest="vl_fasta", default=None, help="FASTA path for VL (first record used).")
    p_new.add_argument("--opt-a", action="store_true", help="Option A: force IGHV3-23*01 when auto selection yields pI>8.5.")
    p_new.add_argument("--force-germline-vh", default=None, help="Force specific VH germline (e.g. IGHV3-23*01).")
    p_new.add_argument("--force-germline-vl", default=None, help="Force specific VL germline (e.g. IGKV1-39*01).")

    p_export = sub.add_parser("export-internal", help="Export internal audit artifacts only (no gates, no recompute).")
    p_export.add_argument("ab_id", type=str, help="Antibody id (e.g. fxy_2c2)")
    p_export.add_argument("project_dir", type=str, help="Project directory (e.g. projects/fxy_2c2_Redesign)")
    p_export.add_argument(
        "--enrich-immuno",
        action="store_true",
        help="Optional: recompute offline immunogenicity audit fields if missing (slower; for legacy results).",
    )

    p_dog = sub.add_parser("dog", help="Dog caninization (auto, structure-gated; surface reshaping fallback).")
    p_dog.add_argument("--name", dest="project_name", required=True, help="Project name (output under projects/<name>/).")
    p_dog.add_argument("--vh", dest="vh", default=None, help="Mouse VH amino acid sequence.")
    p_dog.add_argument("--vl", dest="vl", default=None, help="Mouse VL amino acid sequence.")
    p_dog.add_argument("--vh-fasta", dest="vh_fasta", default=None, help="FASTA path for VH (first record used).")
    p_dog.add_argument("--vl-fasta", dest="vl_fasta", default=None, help="FASTA path for VL (first record used).")
    p_dog.add_argument("--out-dir", dest="out_dir", default=None, help="Output directory (optional).")
    p_dog.add_argument("--demo", action="store_true", help="Run with built-in demo sequences (Pembrolizumab).")

    p_eval = sub.add_parser("evaluate", help="Run AbEvaluator on an antibody (fully-human / humanized / mouse_parent).")
    p_eval.add_argument("project_name", type=str, help="Evaluation project name.")
    p_eval.add_argument("--type", dest="ab_type", default="fully_human",
                        choices=["fully_human", "humanized", "mouse_parent"],
                        help="Antibody type (default: fully_human).")
    p_eval.add_argument("--pdb", dest="pdb_path", default=None, help="PDB path (required for structure modules).")
    p_eval.add_argument("--ref-pdb", dest="ref_pdb_path", default=None,
                        help="Reference PDB (required for humanized delta_vs_mouse).")
    p_eval.add_argument("--vh-chain", default="H", help="VH chain id in PDB (default: H).")
    p_eval.add_argument("--vl-chain", default="L", help="VL chain id in PDB (default: L).")
    p_eval.add_argument("--vh-seq", default=None, help="VH amino-acid sequence (optional).")
    p_eval.add_argument("--vl-seq", default=None, help="VL amino-acid sequence (optional).")
    p_eval.add_argument("--antigen-chain", default=None, help="Antigen chain ID (required for binding_site).")
    p_eval.add_argument("--cdr-json", default=None, help="Path to CDR sequences JSON (required for tap).")
    p_eval.add_argument("--use-iedb", action="store_true", help="Enable IEDB API for immunogenicity.")
    p_eval.add_argument("--modules", nargs="*", default=None,
                        help="Modules to run (default: all applicable). Example: structure_13param delta_vs_mouse developability")
    p_eval.add_argument("--out", "-o", default=None, help="Output JSON path (default: stdout).")
    p_eval.add_argument("--no-strict-qa", action="store_true",
                        help="Disable strict QA hard-abort in evaluator.")

    p_batch = sub.add_parser("batch", help="Batch-run verify/fix/package for multiple VH/VL projects (CSV manifest).")
    p_batch.add_argument("action", choices=["verify", "fix", "package"], help="Action: verify (gate only), fix (gate+report+package), package (delivery only)")
    p_batch.add_argument("--manifest", "-m", required=True, help="CSV path with header: ab_id,project_dir")
    p_batch.add_argument("--continue-on-error", action="store_true", help="Continue even if a row fails.")
    p_batch.add_argument("--zip", action="store_true", help="For action=package: generate ZIP (ignored for verify/fix)")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "verify":
        return _cmd_verify(
            args.ab_id,
            args.project_dir,
            fix=bool(args.fix),
            use_iedb=bool(getattr(args, "use_iedb", False)),
            skip_pdf=not bool(getattr(args, "pdf", False)),
        )
    if args.cmd == "fix":
        return _cmd_verify(
            args.ab_id,
            args.project_dir,
            fix=True,
            use_iedb=bool(getattr(args, "use_iedb", False)),
            skip_pdf=not bool(getattr(args, "pdf", False)),
        )
    if args.cmd == "package":
        return _cmd_package(
            args.ab_id,
            args.project_dir,
            make_zip=bool(getattr(args, "zip", False)),
        )
    if args.cmd == "new":
        return _cmd_new(
            ab_id=args.ab_id,
            vh=getattr(args, "vh", None),
            vl=getattr(args, "vl", None),
            vh_fasta=getattr(args, "vh_fasta", None),
            vl_fasta=getattr(args, "vl_fasta", None),
            opt_a=bool(getattr(args, "opt_a", False)),
            force_germline_vh=getattr(args, "force_germline_vh", None),
            force_germline_vl=getattr(args, "force_germline_vl", None),
        )
    if args.cmd == "export-internal":
        return _cmd_export_internal(args.ab_id, args.project_dir, enrich_immuno=bool(getattr(args, "enrich_immuno", False)))
    if args.cmd == "dog":
        return _cmd_dog_caninize_auto(
            project_name=args.project_name,
            vh=args.vh,
            vl=args.vl,
            vh_fasta=args.vh_fasta,
            vl_fasta=args.vl_fasta,
            out_dir=args.out_dir,
            demo=bool(args.demo),
        )
    if args.cmd == "evaluate":
        return _cmd_evaluate(
            project_name=args.project_name,
            ab_type=args.ab_type,
            pdb_path=args.pdb_path,
            ref_pdb_path=args.ref_pdb_path,
            vh_chain=args.vh_chain,
            vl_chain=args.vl_chain,
            vh_seq=args.vh_seq,
            vl_seq=args.vl_seq,
            antigen_chain=getattr(args, "antigen_chain", None),
            cdr_json_path=getattr(args, "cdr_json", None),
            modules=args.modules,
            out=args.out,
            use_iedb=bool(getattr(args, "use_iedb", False)),
            strict_qa=not bool(args.no_strict_qa),
        )
    if args.cmd == "batch":
        return _cmd_batch(
            args.manifest,
            action=args.action,
            continue_on_error=bool(args.continue_on_error),
            make_zip=bool(getattr(args, "zip", False)),
        )

    raise RuntimeError(f"Unhandled command: {args.cmd!r}")


if __name__ == "__main__":
    raise SystemExit(main())

