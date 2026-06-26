#!/usr/bin/env python3
"""
run_ab_evaluator.py — AbEvaluator 
===============================================

 AbEvaluator， abenginecore 。
、 CI 。

:
  python scripts/run_ab_evaluator.py --project my_ab --pdb antibody.pdb --vh-seq "QVQL..." --vl-seq "DIQM..." -o out.json
  python scripts/run_ab_evaluator.py --project my_ab --pdb ab.pdb --cdr-json cdr.json --modules tap developability -o out.json

: docs/ABEVALUATOR_CLI_REFERENCE.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure suite root in path
SCRIPT_DIR = Path(__file__).resolve().parent
SUITE_ROOT = SCRIPT_DIR.parent
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))


def load_cdr_json(path: str) -> dict:
    """Load CDR sequences from JSON file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CDR JSON not found: {path}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("CDR JSON must be a dict with H1,H2,H3,L1,L2,L3 keys")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="run_ab_evaluator",
        description="Run AbEvaluator on an antibody.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--project", "-p", required=True, help="Project name.")
    ap.add_argument("--type", dest="ab_type", default="fully_human",
                    choices=["fully_human", "humanized", "mouse_parent"],
                    help="Antibody type (default: fully_human).")
    ap.add_argument("--pdb", dest="pdb_path", default=None, help="PDB path.")
    ap.add_argument("--ref-pdb", dest="ref_pdb_path", default=None,
                    help="Reference PDB (for humanized delta_vs_mouse).")
    ap.add_argument("--vh-chain", default="H", help="VH chain ID.")
    ap.add_argument("--vl-chain", default="L", help="VL chain ID.")
    ap.add_argument("--vh-seq", default=None, help="VH sequence.")
    ap.add_argument("--vl-seq", default=None, help="VL sequence.")
    ap.add_argument("--antigen-chain", default=None, help="Antigen chain ID (for binding_site).")
    ap.add_argument("--cdr-json", default=None, help="Path to CDR sequences JSON (for tap).")
    ap.add_argument("--modules", nargs="*", default=None,
                    help="Modules to run (default: all applicable).")
    ap.add_argument("--out", "-o", default=None, help="Output JSON path.")
    ap.add_argument("--use-iedb", action="store_true", help="Enable IEDB API for immunogenicity.")
    ap.add_argument("--no-strict-qa", action="store_true", help="Disable strict QA abort.")

    args = ap.parse_args()

    # Evidence Gate — pre-flight knowledge check
    _evidence_ctx = None
    try:
        from core.resources.evidence_gate import EvidenceGate, print_evidence_banner
        _gate = EvidenceGate(enable_network=False)
        _evidence_ctx = _gate.check(antibody_name=args.project)
        print_evidence_banner(_evidence_ctx)
    except Exception as e:
        print(f"[CMC] Evidence gate skipped: {e}", flush=True)

    cdr_seqs = None
    if args.cdr_json:
        cdr_seqs = load_cdr_json(args.cdr_json)

    from core.evaluation import AbEvaluator, AntibodyType

    ev = AbEvaluator(
        project_name=args.project,
        ab_type=AntibodyType(args.ab_type),
        pdb_path=args.pdb_path,
        ref_pdb_path=args.ref_pdb_path,
        vh_chain=args.vh_chain,
        vl_chain=args.vl_chain,
        vh_seq=args.vh_seq,
        vl_seq=args.vl_seq,
        antigen_chain=args.antigen_chain,
        cdr_seqs=cdr_seqs,
        use_iedb=args.use_iedb,
        strict_qa=not args.no_strict_qa,
    )
    result = ev.run(modules=args.modules)

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

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"[run_ab_evaluator] Saved → {args.out}")
    else:
        print(text)

    final_code = 0 if result.overall_status != "FAIL" else 2

    # Self-Evolution: emit RunEvent
    try:
        from core.evolution.event_collector import EventCollector
        _collector = EventCollector()
        _run_event = _collector.from_evidence_gate(
            project_id=args.project,
            family="cmc_evaluation",
            entrypoint="run_ab_evaluator.py",
            evidence_ctx=_evidence_ctx,
            exit_code=final_code,
        )
        _collector.emit(_run_event)
    except Exception:
        pass

    return final_code


if __name__ == "__main__":
    sys.exit(main())
