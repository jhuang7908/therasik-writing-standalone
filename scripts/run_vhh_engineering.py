#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_vhh_engineering.py — InSynBio AbEngineCore Unified VHH CLI
===============================================================
 VHH 。


----
Path A   /  VHH ：
    python scripts/run_vhh_engineering.py \\
        --project Caplacizumab_hum \\
        --source-type camelid_wt \\
        --seq QVQLVESGG... \\
        [--strategy S1|S2|S3] \\
        [--out-dir projects/Caplacizumab_hum/delivery]

Path B1   sdAb （ VHH ）：
    python scripts/run_vhh_engineering.py \\
        --project Mouse_sdAb_opt \\
        --source-type transgenic_mouse \\
        --seq QVQLVESGG... \\
        [--out-dir ...]

Path C2   VH →  + （）：
    python scripts/run_vhh_engineering.py \\
        --project MuVH_to_VHH \\
        --source-type murine_wt_vh \\
        --seq EVQLVESGG... \\
        [--strategy S2|S3] \\
        [--out-dir ...]

Path C1   VH → VHH （）：
    python scripts/run_vhh_engineering.py \\
        --project TrastuzumabVHH \\
        --source-type conventional_vh \\
        --seq EVQLVESGG...   \\   #  VH （）
        [--vhh-seq QVQLVESGG...]  \\   #  VHH （ Stage2 ）
        [--out-dir ...]

：
    --seq-file <path>       （ / FASTA / JSON）
    --strategy  S1|S2|S3    （ Path A/C2 ， auto）
    --dry-run               ，
    --json-only              JSON ， MD
    --out-dir <path>        （ projects/<project>/delivery_vhh_<pathway>）


---------------------
  Path A  camelid_wt     :  vhh_39_clinical_atlas (39)  |  IGHV germline | tier_system_config.json
  Path B1 transgenic_mouse: ， Tier0+Tier1 | 
  Path C2 murine_wt_vh   : camelization rules (44/45/47 FR2 hallmarks) + Tier0-3 | 
  Path C1 conventional_vh: vh_to_vhh_converter.py Stage1+Stage2 |  (Hallmark + Stealth)

Governance
----------
  route → config/tier_system_config.json § strategy_definitions.routing_logic
  standards  → docs/VHH_HUMANIZATION_DESIGN_STANDARD.md ()
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Suite root & sys.path
# ─────────────────────────────────────────────────────────────────────────────
_SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SUITE_ROOT))

import scripts.anarci_shim  # MUST be first — shims anarci for ImmuneBuilder
from scripts.pipeline_policy import get_runtime_policy


# ─────────────────────────────────────────────────────────────────────────────
# Source-type constants (mirrors tier_system_config.json § routing_logic)
# ─────────────────────────────────────────────────────────────────────────────
SOURCE_TYPES = {
    "camelid_wt": {
        "pathway": "A",
        "label": "Path A —  /  VHH ",
        "engine_workflow": "vhh",
        "tiers": "Tier 0-3",
        "goal": "， VHH ",
        "requires_vhh_seq": False,
        "valid_strategies": ["S1", "S2", "S3"],
        "delivery_suffix": "humanization",
    },
    "transgenic_mouse": {
        "pathway": "B1",
        "label": "Path B1 —  VHH sdAb ",
        "engine_workflow": "vhh",
        "tiers": "Tier 0 + Tier 1 ()",
        "goal": " SHM ， / Tm、、pI",
        "requires_vhh_seq": False,
        "valid_strategies": [],          # strategy not applicable — developability only
        "delivery_suffix": "dev_opt",
    },
    "murine_wt_vh": {
        "pathway": "C2",
        "label": "Path C2 —  VH （ + ）",
        "engine_workflow": "vhh",
        "tiers": "Camelization rules + Tier 0-3",
        "goal": " VH-VL （FR2 hallmark 44/45/47 ），",
        "requires_vhh_seq": False,
        "valid_strategies": ["S2", "S3"],
        "delivery_suffix": "dual_engineering",
    },
    "conventional_vh": {
        "pathway": "C1",
        "label": "Path C1 —  VH → VHH ",
        "engine_workflow": "vhh_conversion",
        "tiers": "VH-to-VHH converter (Stage1 + Stage2)",
        "goal": " VH→VHH ， VL （Hallmark + Stealth）",
        "requires_vhh_seq": False,  # optional Stage2
        "valid_strategies": [],
        "delivery_suffix": "conversion",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# CLI argument parser
# ─────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_vhh_engineering.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""\
            InSynBio AbEngineCore — VHH 
            ============================================
             VHH ：
              camelid_wt      Path A   VHH 
              transgenic_mouse Path B1  sdAb 
              murine_wt_vh    Path C2  VH （+）
              conventional_vh Path C1  VH 
        """),
    )

    # ── Mandatory ────────────────────────────────────────────────────────────
    p.add_argument(
        "--project", "-p", required=True,
        metavar="ID",
        help=" /  ID（：caplacizumab_opt）",
    )
    p.add_argument(
        "--source-type", "-t",
        required=True,
        choices=list(SOURCE_TYPES.keys()),
        metavar="TYPE",
        help=(
            "VHH （）："
            " camelid_wt | transgenic_mouse | murine_wt_vh | conventional_vh"
        ),
    )

    # ── Sequence input ────────────────────────────────────────────────────────
    seq_group = p.add_mutually_exclusive_group()
    seq_group.add_argument(
        "--seq", "-s",
        default="",
        metavar="AA",
        help="（VHH ， Path C  VH ）",
    )
    seq_group.add_argument(
        "--seq-file", "-f",
        default="",
        metavar="PATH",
        help="（ / FASTA / JSON）",
    )
    p.add_argument(
        "--vhh-seq",
        default="",
        metavar="AA",
        help=(
            "[Path C ]  VHH ， Stage2 。"
            "  Stage1（）。"
        ),
    )

    # ── Pipeline options ──────────────────────────────────────────────────────
    p.add_argument(
        "--strategy",
        choices=["S1", "S2", "S3", "auto"],
        default="auto",
        help=(
            "（ Path A / C2 ）："
            " S1= | S2= | S3= | auto= CDR3 （）"
        ),
    )
    p.add_argument(
        "--source-subtype",
        choices=["human_mab", "murine_mab", "phage_display_vh"],
        default="human_mab",
        help="[Path C1 ] VH （ human_mab）",
    )

    # ── Output ───────────────────────────────────────────────────────────────
    p.add_argument(
        "--out-dir",
        default="",
        metavar="PATH",
        help="（ projects/<project>/delivery_vhh_<pathway>）",
    )
    p.add_argument(
        "--json-only",
        action="store_true",
        help=" JSON ， Markdown ",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="，",
    )

    return p


# ─────────────────────────────────────────────────────────────────────────────
# Sequence loading
# ─────────────────────────────────────────────────────────────────────────────

def _load_sequence(seq_str: str, seq_file: str, label: str = "sequence") -> str:
    """Return cleaned sequence from inline string or file."""
    if seq_str:
        return seq_str.strip().upper()
    if seq_file:
        fp = Path(seq_file)
        if not fp.is_file():
            _die(f"{label} : {fp}")
        text = fp.read_text(encoding="utf-8").strip()
        if text.startswith(">"):          # FASTA
            lines = text.splitlines()
            return "".join(l.strip() for l in lines if not l.startswith(">")).upper()
        if text.startswith("{"):          # JSON
            data = json.loads(text)
            for key in ("sequence", "vhh", "vh", "VHH", "VH", "seq", "aa"):
                if key in data:
                    return data[key].strip().upper()
            _die(f" JSON  {fp} （: sequence/vhh/vh/seq/aa）")
        return text.upper()              # plain text
    return ""


def _die(msg: str, code: int = 1) -> None:
    print(f"\n[ERROR] {msg}", file=sys.stderr)
    sys.exit(code)


# ─────────────────────────────────────────────────────────────────────────────
# Routing banner
# ─────────────────────────────────────────────────────────────────────────────

def _print_banner(
    project: str,
    src_type: str,
    meta: Dict[str, Any],
    strategy: str,
    runtime_policy: Dict[str, Any],
) -> None:
    w = 62
    struct_policy = runtime_policy.get("structure_policy") or {}
    eval_policy = runtime_policy.get("evaluator_policy") or {}
    print(f"\n{'='*w}")
    print(f"  InSynBio AbEngineCore — VHH ")
    print(f"{'─'*w}")
    print(f"        : {project}")
    print(f"    : {src_type}")
    print(f"        : {meta['label']}")
    print(f"    : {meta['tiers']}")
    print(f"    : {meta['goal']}")
    if strategy != "auto" and meta["valid_strategies"]:
        print(f"  : {strategy}")
    elif meta["valid_strategies"]:
        print(f"  : auto（ CDR3  S1/S2/S3）")
    else:
        print(f"  : N/A（）")
    print(f"    : {struct_policy.get('default_predictor', 'N/A')}")
    print(f"    : {', '.join(eval_policy.get('allowed_modules') or []) or 'N/A'}")
    print(f"{'='*w}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Path A / B1 / C2  — HumanizationEngine (vhh_humanization workflow)
# ─────────────────────────────────────────────────────────────────────────────

def _run_humanization_path(
    seq: str,
    project: str,
    source_type: str,
    meta: Dict[str, Any],
    strategy: str,
    out_dir: Path,
    json_only: bool,
    runtime_policy: Dict[str, Any],
) -> int:
    """
    Execute HumanizationEngine for Path A, B1, C2.
    Returns exit code (0=success, 1=fail).
    """
    try:
        from core.humanization.engine import HumanizationEngine
    except ImportError as e:
        _die(f" HumanizationEngine: {e}")

    engine_kwargs: Dict[str, Any] = {
        "mouse_vh": seq,
        "mouse_vl": "",               # VHH — no VL
        "project_name": project,
        "out_dir": str(out_dir),
        # Note: routing is determined by CLI --source-type + tier config; do not pass
        # unknown kwargs into HumanizationEngine.run() (engine accepts only VH/VL/strategy).
    }

    # Strategy selection
    if strategy != "auto" and meta["valid_strategies"]:
        engine_kwargs["strategy"] = strategy
    elif not meta["valid_strategies"]:
        # B1: no S1/S2/S3 routing in CLI — HumanizationEngine VHH only accepts S1/S2/S3
        engine_kwargs["strategy"] = runtime_policy.get("default_strategy") or "S2"

    engine = HumanizationEngine(workflow=meta["engine_workflow"])
    result = engine.run(**engine_kwargs)

    out_dir.mkdir(parents=True, exist_ok=True)
    report_stem = f"vhh_{meta['delivery_suffix']}_report"

    json_path = result.save_report(out_dir / f"{report_stem}.json")
    print(f"[Done] JSON : {json_path}")
    print(f"[Done]  : {result.overall_status}")

    if not json_only:
        # md_path = result.save_report_md(out_dir / f"{report_stem}.md")
        # print(f"[Done] MD   : {md_path}")
        pass

    # Best sequence output
    for seq_key in ("humanized_vhh", "optimized_vhh", "vhh"):
        best = result.sequences.get(seq_key, "")
        if best:
            fa_path = out_dir / f"{project}_{meta['delivery_suffix']}.fa"
            fa_path.write_text(f">{project}_{seq_key}\n{best}\n", encoding="utf-8")
            print(f"[Done] FASTA: {fa_path}")
            break

    return 0 if result.overall_status in ("PASS", "WARN") else 1


# ─────────────────────────────────────────────────────────────────────────────
# Path C1 — VH→VHH conversion (vhh_conversion_pipeline)
# ─────────────────────────────────────────────────────────────────────────────

def _run_conversion_path(
    vh_seq: str,
    vhh_seq: str,
    project: str,
    source_subtype: str,
    out_dir: Path,
    json_only: bool,
    runtime_policy: Dict[str, Any],
) -> int:
    """
    Execute VH-to-VHH conversion pipeline (Stage1 + optional Stage2).
    Returns exit code.
    """
    try:
        from scripts.vhh_conversion_pipeline import run_stage1, run_stage2, render_md_report
    except ImportError as e:
        _die(f" vhh_conversion_pipeline: {e}")

    out_dir.mkdir(parents=True, exist_ok=True)
    results_list = []
    entry_id = project

    # Stage 1 — VH feasibility
    print("[Path C1] Stage 1: VH→VHH …")
    s1 = run_stage1(vh_seq, source_type=source_subtype)
    entry: Dict[str, Any] = {
        "entry_id": entry_id,
        "source_type": source_subtype,
        "stage1_feasibility": s1,
        "_meta": {
            "pipeline": "vhh_conversion",
            "run_time": datetime.now().isoformat(timespec="seconds"),
        },
    }

    # Stage 2 — VHH quality (optional)
    if vhh_seq:
        print("[Path C1] Stage 2:  VHH …")
        allowed_modules = (runtime_policy.get("evaluator_policy") or {}).get("allowed_modules") or None
        s2_list = run_stage2(
            [{"sequence_id": f"{entry_id}_converted", "sequence": vhh_seq}],
            modules=allowed_modules,
        )
        entry["stage2_vhh_quality"] = s2_list
    else:
        entry["stage2_vhh_quality"] = [{"status": "SKIPPED", "reason": "--vhh-seq not provided"}]
        print("[Path C1] Stage 2 （ --vhh-seq）")

    results_list.append(entry)

    # Save JSON
    json_path = out_dir / "vhh_conversion_report.json"
    json_path.write_text(json.dumps({"results": results_list}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Done] JSON : {json_path}")

    # Save MD
    if not json_only:
        md_text = render_md_report(results_list)
        md_path = out_dir / "vhh_conversion_report.md"
        md_path.write_text(md_text, encoding="utf-8")
        print(f"[Done] MD   : {md_path}")

    # Feasibility verdict
    feasibility = s1.get("feasibility", {})
    verdict = feasibility.get("verdict", "UNKNOWN")
    risk = feasibility.get("risk_level", "?")
    print(f"[Done] : {verdict}  : {risk}")
    return 0 if verdict in ("FEASIBLE", "FEASIBLE_WITH_CAUTION") else 1


# ─────────────────────────────────────────────────────────────────────────────
# Dry-run summary
# ─────────────────────────────────────────────────────────────────────────────

def _print_dry_run(
    source_type: str,
    meta: Dict[str, Any],
    seq: str,
    vhh_seq: str,
    strategy: str,
    out_dir: Path,
    runtime_policy: Dict[str, Any],
) -> None:
    struct_policy = runtime_policy.get("structure_policy") or {}
    eval_policy = runtime_policy.get("evaluator_policy") or {}
    print("\n[DRY-RUN] ")
    print(f"         : {meta['pathway']} — {meta['label']}")
    print(f"    : {meta['engine_workflow']}")
    print(f"     : {meta['tiers']}")
    print(f"     : {len(seq)} aa" if seq else "         : ")
    if vhh_seq:
        print(f"  VHH    : {len(vhh_seq)} aa (Stage2 )")
    if meta["valid_strategies"]:
        strat_used = strategy if strategy != "auto" else "auto（CDR3 ）"
        print(f"   : {strat_used}（: {', '.join(meta['valid_strategies'])}）")
    else:
        print(f"   : ")
    print(f"     : {struct_policy.get('default_predictor', 'N/A')}")
    print(f"     : {', '.join(eval_policy.get('allowed_modules') or []) or 'N/A'}")
    print(f"     : {out_dir}")
    print("\n  [INFO]  --dry-run=False \n")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    src_type = args.source_type
    meta = SOURCE_TYPES[src_type]
    runtime_policy = get_runtime_policy(src_type)
    meta = dict(meta)
    meta["valid_strategies"] = list(runtime_policy.get("allowed_strategies") or [])

    # ── Sequence loading ──────────────────────────────────────────────────────
    seq = _load_sequence(args.seq, args.seq_file, label="")
    vhh_seq = args.vhh_seq.strip().upper() if args.vhh_seq else ""

    if not seq and not args.dry_run:
        _die(" --seq <AA>  --seq-file <PATH>。Path C  VH 。")

    # ── Strategy validation ───────────────────────────────────────────────────
    if (args.strategy not in ("auto",) + tuple(meta["valid_strategies"])
            and meta["valid_strategies"]):
        _die(
            f"--strategy {args.strategy}  {src_type} (Path {meta['pathway']}) 。"
            f" : {', '.join(meta['valid_strategies'])} | auto"
        )
    if args.strategy != "auto" and not meta["valid_strategies"]:
        print(
            f"[WARN] Path {meta['pathway']}  --strategy，。",
            file=sys.stderr,
        )
    default_predictor = ((runtime_policy.get("structure_policy") or {}).get("default_predictor") or "").strip()
    if default_predictor != "NanoBodyBuilder2":
        _die(
            f"{src_type} ： SSOT default_predictor={default_predictor!r}。"
            " VHH  NanoBodyBuilder2。"
        )

    # ── Output directory ──────────────────────────────────────────────────────
    out_dir = (
        Path(args.out_dir)
        if args.out_dir
        else _SUITE_ROOT / "projects" / args.project / f"delivery_vhh_{meta['delivery_suffix']}"
    )

    # ── Evidence Gate — pre-flight knowledge check ─────────────────────────
    try:
        from core.resources.evidence_gate import EvidenceGate, print_evidence_banner
        _gate = EvidenceGate(enable_network=False)
        _evidence_ctx = _gate.check(antibody_name=args.project)
        print_evidence_banner(_evidence_ctx)
    except Exception as e:
        print(f"[VHH] Evidence gate skipped: {e}", file=sys.stderr)
        _evidence_ctx = None

    # ── Banner ────────────────────────────────────────────────────────────────
    _print_banner(args.project, src_type, meta, args.strategy, runtime_policy)

    # ── Dry-run shortcut ──────────────────────────────────────────────────────
    if args.dry_run:
        _print_dry_run(src_type, meta, seq, vhh_seq, args.strategy, out_dir, runtime_policy)
        sys.exit(0)

    # ── Dispatch ─────────────────────────────────────────────────────────────
    if src_type in ("camelid_wt", "transgenic_mouse", "murine_wt_vh"):
        code = _run_humanization_path(
            seq=seq,
            project=args.project,
            source_type=src_type,
            meta=meta,
            strategy=args.strategy,
            out_dir=out_dir,
            json_only=args.json_only,
            runtime_policy=runtime_policy,
        )
    elif src_type == "conventional_vh":
        code = _run_conversion_path(
            vh_seq=seq,
            vhh_seq=vhh_seq,
            project=args.project,
            source_subtype=args.source_subtype,
            out_dir=out_dir,
            json_only=args.json_only,
            runtime_policy=runtime_policy,
        )
    else:
        _die(f" source-type: {src_type}")

    # Self-Evolution: emit RunEvent
    try:
        from core.evolution.event_collector import EventCollector
        _collector = EventCollector()
        _run_event = _collector.from_evidence_gate(
            project_id=args.project,
            family="vhh_humanization",
            entrypoint="run_vhh_engineering.py",
            evidence_ctx=_evidence_ctx,
            exit_code=code,
        )
        _collector.emit(_run_event)
    except Exception:
        pass

    sys.exit(code)


if __name__ == "__main__":
    main()
