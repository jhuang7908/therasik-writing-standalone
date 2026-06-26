#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_bispecific_vhh_cmc.py  v2.0.0  [CLI wrapper]
=================================================
InSynBio AbEngineCore — Bispecific VHH CMC Assessment Pipeline (CLI)

This script is a THIN CLI WRAPPER.
All engine logic lives in:
  core/cmc/vhh_cmc_engine.py        — per-arm VHH CMC (15 metrics, ADI, flags, percentiles)
  core/cmc/bispecific_cmc_engine.py — fusion pI matrix, SmartLink™ recommendation, report

Standard: docs/BISPECIFIC_VHH_CMC_STANDARD.md  V1.0

Usage
-----
  Panel mode (recommended — multi-variant screening):
    python run_bispecific_vhh_cmc.py \\
        --panel-a armA.fasta --panel-b armB.fasta \\
        --outdir ./results/my_project

  Single pair (FASTA file or raw sequence string):
    python run_bispecific_vhh_cmc.py \\
        --arm-a VHH_A.fasta --arm-b VHH_B.fasta \\
        --outdir ./results/my_project

  Inline sequences (quick single pair):
    python run_bispecific_vhh_cmc.py \\
        --seq-a EVQLLES...VSS --name-a "VHH-A" \\
        --seq-b EVQLLES...VSS --name-b "VHH-B" \\
        --outdir ./results/my_project

  Custom linkers:
    python run_bispecific_vhh_cmc.py \\
        --panel-a a.fasta --panel-b b.fasta \\
        --linkers "(G4S)3:GGGGSGGGGSGGGGS" "(G4S)3+3E:GGGGSGGGGSGGGGSEEE" \\
        --outdir ./results/my_project

Output
------
  {outdir}/
    cmc_report.json   — full machine-readable results
    cmc_report.md     — human-readable Markdown report
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ── suite root ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
SUITE_ROOT  = SCRIPT_DIR.parent
sys.path.insert(0, str(SUITE_ROOT))

# ── AbEngineCore imports ──────────────────────────────────────────────────────
from core.cmc.vhh_cmc_engine import (
    load_vhh_ref, evaluate_single_vhh, DEFAULT_VHH42_REF,
)
from core.cmc.bispecific_cmc_engine import (
    compute_fusion_matrix, select_recommendations, generate_markdown,
    DEFAULT_LINKERS, ER_PI_WARN, ER_PI_CRIT, ER_PH,
)


# ═════════════════════════════════════════════════════════════════════════════
# FASTA / sequence utilities (CLI-layer only — not in engine)
# ═════════════════════════════════════════════════════════════════════════════

def parse_fasta(path: Path) -> Dict[str, str]:
    """Parse multi-entry FASTA → {name: sequence}."""
    seqs: Dict[str, str] = {}
    current_name: Optional[str] = None
    current_seq: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if current_name is not None:
                seqs[current_name] = "".join(current_seq).upper()
            current_name = line[1:].split()[0]
            current_seq = []
        else:
            current_seq.append(line)
    if current_name is not None:
        seqs[current_name] = "".join(current_seq).upper()
    return seqs


def seq_from_arg(arg: str) -> str:
    """Accept a raw sequence string or a single-entry FASTA file path."""
    p = Path(arg)
    if p.is_file():
        entries = parse_fasta(p)
        if not entries:
            raise ValueError(f"No sequences found in {arg}")
        return next(iter(entries.values()))
    return arg.upper().replace(" ", "").replace("\n", "")


# ═════════════════════════════════════════════════════════════════════════════
# CLI argument parser
# ═════════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_bispecific_vhh_cmc",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""\
            InSynBio AbEngineCore v2.0 — Bispecific VHH CMC Assessment Pipeline
            =====================================================================
            Industrial-grade CMC analysis for dual-VHH bispecific constructs.
            Standard: docs/BISPECIFIC_VHH_CMC_STANDARD.md  V1.0

            Engine modules:
              core/cmc/vhh_cmc_engine.py        (per-arm: 15 metrics, ADI, flags)
              core/cmc/bispecific_cmc_engine.py  (fusion pI matrix, SmartLink™)

            Input modes (choose one):
              Panel mode  : --panel-a <fasta> --panel-b <fasta>
              Single pair : --arm-a <fasta/seq> --arm-b <fasta/seq>
              Inline      : --seq-a <seq> --name-a <name> --seq-b <seq> --name-b <name>
        """),
        epilog=textwrap.dedent("""\
            Examples:
              python run_bispecific_vhh_cmc.py \\
                  --panel-a armA.fasta --panel-b armB.fasta \\
                  --outdir ./results/proj1

              python run_bispecific_vhh_cmc.py \\
                  --seq-a EVQLLES...VSS --name-a "VHH-A" \\
                  --seq-b EVQLLES...VSS --name-b "VHH-B" \\
                  --outdir ./results/proj2

              python run_bispecific_vhh_cmc.py \\
                  --panel-a a.fasta --panel-b b.fasta \\
                  --linkers "(G4S)3:GGGGSGGGGSGGGGS" "(G4S)3+3E:GGGGSGGGGSGGGGSEEE" \\
                  --outdir ./results/proj3
        """),
    )

    inp = p.add_argument_group("Input (Panel mode — recommended for multi-variant analysis)")
    inp.add_argument("--panel-a", metavar="FASTA", help="Multi-entry FASTA for Arm A variants")
    inp.add_argument("--panel-b", metavar="FASTA", help="Multi-entry FASTA for Arm B variants")

    sing = p.add_argument_group("Input (Single-pair mode)")
    sing.add_argument("--arm-a", metavar="FASTA_OR_SEQ",
                      help="Arm A: FASTA file path or raw sequence string")
    sing.add_argument("--arm-b", metavar="FASTA_OR_SEQ",
                      help="Arm B: FASTA file path or raw sequence string")
    sing.add_argument("--name-a", metavar="NAME", default="ArmA",
                      help="Display name for Arm A (default: ArmA)")
    sing.add_argument("--name-b", metavar="NAME", default="ArmB",
                      help="Display name for Arm B (default: ArmB)")
    sing.add_argument("--seq-a", metavar="SEQ", help="Inline amino acid sequence for Arm A")
    sing.add_argument("--seq-b", metavar="SEQ", help="Inline amino acid sequence for Arm B")

    cfg = p.add_argument_group("Analysis parameters")
    cfg.add_argument("--linkers", metavar="NAME:SEQ", nargs="+",
                     help="Custom linker definitions (format: 'Name:SEQUENCE'). "
                          "Replaces default linker panel.")
    cfg.add_argument("--er-pi-threshold", type=float, default=ER_PI_WARN, metavar="FLOAT",
                     help=f"Fusion pI above which expression risk is flagged (default: {ER_PI_WARN})")
    cfg.add_argument("--er-ph", type=float, default=ER_PH, metavar="FLOAT",
                     help=f"ER lumen pH for net charge calculation (default: {ER_PH})")
    cfg.add_argument("--ref", metavar="PATH", default=None,
                     help="JSON reference statistics file (default: VHH42_reference_stats_v1.json)")
    cfg.add_argument("--no-percentile", action="store_true",
                     help="Skip VHH42 percentile rank calculation (speeds up large panels)")

    out = p.add_argument_group("Output")
    out.add_argument("--outdir", metavar="DIR", default="./cmc_output",
                     help="Output directory (created if absent, default: ./cmc_output)")
    out.add_argument("--prefix", metavar="STR", default="cmc_report",
                     help="Output file prefix (default: cmc_report)")
    out.add_argument("--no-md", action="store_true", help="Skip Markdown report generation")

    p.add_argument("--quiet", "-q", action="store_true", help="Suppress progress messages")
    p.add_argument("--version", action="version", version="%(prog)s 2.0.0")

    return p


# ═════════════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════════════

def _flag_icon(flag: str) -> str:
    return {"pass": "✅", "warn": "⚠️", "critical": "🔴",
            "PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(flag, "—")


def main() -> int:
    parser = build_parser()
    args   = parser.parse_args()
    quiet  = args.quiet

    def log(msg: str) -> None:
        if not quiet:
            print(msg, flush=True)

    # Evidence Gate — pre-flight knowledge check
    if not quiet:
        try:
            from core.resources.evidence_gate import EvidenceGate, print_evidence_banner
            _gate = EvidenceGate(enable_network=False)
            arm_label = getattr(args, "name_a", "") or "bispecific"
            _evidence_ctx = _gate.check(antibody_name=arm_label)
            print_evidence_banner(_evidence_ctx)
        except Exception as e:
            log(f"[Bispecific-CMC] Evidence gate skipped: {e}")

    # ── resolve sequences ──────────────────────────────────────────────────
    arm_a_seqs: Dict[str, str] = {}
    arm_b_seqs: Dict[str, str] = {}

    if args.panel_a:
        arm_a_seqs = parse_fasta(Path(args.panel_a))
        log(f"[+] Arm A: loaded {len(arm_a_seqs)} variants from {args.panel_a}")
    elif args.arm_a:
        arm_a_seqs = {args.name_a: seq_from_arg(args.arm_a)}
        log(f"[+] Arm A: 1 sequence loaded ({args.name_a})")
    elif args.seq_a:
        arm_a_seqs = {args.name_a: args.seq_a.upper().replace(" ", "")}
        log(f"[+] Arm A: inline ({args.name_a}, {len(arm_a_seqs[args.name_a])} aa)")
    else:
        parser.error("Arm A input required: --panel-a, --arm-a, or --seq-a")

    if args.panel_b:
        arm_b_seqs = parse_fasta(Path(args.panel_b))
        log(f"[+] Arm B: loaded {len(arm_b_seqs)} variants from {args.panel_b}")
    elif args.arm_b:
        arm_b_seqs = {args.name_b: seq_from_arg(args.arm_b)}
        log(f"[+] Arm B: 1 sequence loaded ({args.name_b})")
    elif args.seq_b:
        arm_b_seqs = {args.name_b: args.seq_b.upper().replace(" ", "")}
        log(f"[+] Arm B: inline ({args.name_b}, {len(arm_b_seqs[args.name_b])} aa)")
    else:
        parser.error("Arm B input required: --panel-b, --arm-b, or --seq-b")

    # ── load reference ─────────────────────────────────────────────────────
    ref_path  = Path(args.ref) if args.ref else DEFAULT_VHH42_REF
    if not ref_path.exists():
        print(f"[ERROR] Reference file not found: {ref_path}", file=sys.stderr)
        return 1
    ref_stats = load_vhh_ref(ref_path)
    log(f"[+] Reference: {ref_path.name} (VHH42, n=42)")

    # ── resolve linkers ────────────────────────────────────────────────────
    if args.linkers:
        linkers: Dict[str, str] = {}
        for item in args.linkers:
            parts = item.split(":", 1)
            if len(parts) != 2:
                print(f"[ERROR] Linker format must be 'Name:SEQUENCE', got: {item}",
                      file=sys.stderr)
                return 1
            linkers[parts[0]] = parts[1].upper()
        log(f"[+] Linkers: {len(linkers)} custom ({', '.join(linkers)})")
    else:
        linkers = DEFAULT_LINKERS
        log(f"[+] Linkers: {len(linkers)} default ({', '.join(linkers)})")

    er_threshold = args.er_pi_threshold
    skip_pct     = args.no_percentile

    # ── Step 1: Individual VHH CMC ─────────────────────────────────────────
    w = 66
    log(f"\n{'='*w}")
    log(f"  InSynBio AbEngineCore v2.0 — Bispecific VHH CMC Pipeline")
    log(f"{'─'*w}")
    log(f"  Arm A: {len(arm_a_seqs)}   Arm B: {len(arm_b_seqs)}   "
        f"Linkers: {len(linkers)}   ER threshold: pI > {er_threshold}")
    log(f"{'='*w}\n")

    log("[1/4] Individual VHH CMC (15 metrics × PASS/WARN/FAIL, VHH42 ref)...")
    arm_a_results: List[Dict] = []
    arm_b_results: List[Dict] = []

    for name, seq in arm_a_seqs.items():
        if not seq:
            log(f"      SKIP {name} — empty")
            continue
        r = evaluate_single_vhh(name, seq, ref_stats, skip_pct,
                                 er_pi_warn=er_threshold, er_pi_crit=ER_PI_CRIT)
        arm_a_results.append(r)
        log(f"      [A] {name[:36]:36s} pI={r['metrics']['pI']:.1f}  "
            f"SAP={r['metrics']['SAP_score']:.3f}  ADI={r['adi_score']:.0f} "
            f"[{r['adi_grade']}]  W={r['n_warn']} F={r['n_fail']}  "
            f"ER:{_flag_icon(r['pi_flag'])}")

    for name, seq in arm_b_seqs.items():
        if not seq:
            log(f"      SKIP {name} — empty")
            continue
        r = evaluate_single_vhh(name, seq, ref_stats, skip_pct,
                                 er_pi_warn=er_threshold, er_pi_crit=ER_PI_CRIT)
        arm_b_results.append(r)
        log(f"      [B] {name[:36]:36s} pI={r['metrics']['pI']:.1f}  "
            f"SAP={r['metrics']['SAP_score']:.3f}  ADI={r['adi_score']:.0f} "
            f"[{r['adi_grade']}]  W={r['n_warn']} F={r['n_fail']}  "
            f"ER:{_flag_icon(r['pi_flag'])}")

    if not arm_a_results or not arm_b_results:
        print("[ERROR] No valid sequences in one or both arms.", file=sys.stderr)
        return 1

    # ── Step 2: Fusion pI matrix ───────────────────────────────────────────
    n_combos = len(arm_a_results) * len(arm_b_results) * len(linkers)
    log(f"\n[2/4] Fusion pI matrix ({n_combos} combinations)...")
    fusion_matrix = compute_fusion_matrix(arm_a_results, arm_b_results, linkers, er_threshold)
    best = fusion_matrix[0]
    log(f"      Best: {best['arm_a']} + {best['linker']} + {best['arm_b']}  "
        f"pI={best['fusion_pi']}  NC={best['fusion_nc']:+.1f}  {_flag_icon(best['pi_flag'])}")

    # ── Step 3: SmartLink™ recommendations ────────────────────────────────
    log("\n[3/4] SmartLink™ recommendation...")
    arm_a_dict = {r["name"]: r for r in arm_a_results}
    arm_b_dict = {r["name"]: r for r in arm_b_results}
    recs = select_recommendations(fusion_matrix, arm_a_dict, arm_b_dict, er_threshold)
    p = recs["primary"]
    log(f"      Primary  : {p['arm_a']} — {p['linker']} — {p['arm_b']}  "
        f"pI={p['fusion_pi']}  NC={p['fusion_nc']:+.1f}  [{_flag_icon(p['pi_flag'])}]")
    if recs["runner_up"]:
        ru = recs["runner_up"]
        log(f"      Runner-up: {ru['arm_a']} — {ru['linker']} — {ru['arm_b']}  pI={ru['fusion_pi']}")
    log(f"      PASS/WARN/CRIT: {recs['n_passing']}/{recs['n_warning']}/{recs['n_critical']}")

    # ── Step 4: Write outputs ──────────────────────────────────────────────
    log("\n[4/4] Writing outputs...")
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    prefix = args.prefix
    ts     = datetime.now().isoformat(timespec="seconds")

    report = {
        "meta": {
            "tool":            "InSynBio AbEngineCore — Bispecific VHH CMC Pipeline",
            "version":         "2.0.0",
            "standard":        "BISPECIFIC_VHH_CMC_STANDARD V1.0",
            "timestamp":       ts,
            "reference":       str(ref_path),
            "er_pi_threshold": er_threshold,
            "er_ph":           ER_PH,
            "linkers":         linkers,
            "adi_method":      "flag_discrete_4cat (core.cmc.vhh_cmc_engine, aligned with run_vhh_cmc_eval)",
            "n_arm_a":         len(arm_a_results),
            "n_arm_b":         len(arm_b_results),
            "n_combos":        n_combos,
        },
        "arm_a":           arm_a_results,
        "arm_b":           arm_b_results,
        "fusion_matrix":   fusion_matrix,
        "recommendations": recs,
    }

    json_path = outdir / f"{prefix}.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"      JSON:     {json_path}")

    if not args.no_md:
        md_path = outdir / f"{prefix}.md"
        md_path.write_text(
            generate_markdown(
                arm_a_results=arm_a_results,
                arm_b_results=arm_b_results,
                fusion_matrix=fusion_matrix,
                recommendations=recs,
                ref_stats=ref_stats,
                er_threshold=er_threshold,
                meta={"timestamp": ts},
            ),
            encoding="utf-8",
        )
        log(f"      Markdown: {md_path}")

    # ── Summary ────────────────────────────────────────────────────────────
    all_r    = arm_a_results + arm_b_results
    n_p      = sum(1 for r in all_r if r["overall_status"] == "PASS")
    n_w      = sum(1 for r in all_r if r["overall_status"] == "WARN")
    n_f      = sum(1 for r in all_r if r["overall_status"] == "FAIL")
    adi_vals = [r["adi_score"] for r in all_r]

    log(f"\n{'='*w}")
    log(f"  Results Summary")
    log(f"{'─'*w}")
    log(f"  Individual VHH : PASS={n_p}  WARN={n_w}  FAIL={n_f}")
    log(f"  ADI            : mean={sum(adi_vals)/len(adi_vals):.1f}  "
        f"min={min(adi_vals):.1f}  max={max(adi_vals):.1f}")
    log(f"  Fusion combos  : PASS={recs['n_passing']}  WARN={recs['n_warning']}  "
        f"CRIT={recs['n_critical']}")
    log(f"  Recommendation : {p['arm_a']} — {p['linker']} — {p['arm_b']}  pI={p['fusion_pi']}")
    log(f"{'='*w}\n")

    final_code = 0 if n_f == 0 else 1

    # Self-Evolution: emit RunEvent
    try:
        from core.evolution.event_collector import EventCollector
        _collector = EventCollector()
        _run_event = _collector.from_cmc_result(
            project_id=f"{args.name_a}_{args.name_b}" if hasattr(args, "name_b") else args.name_a,
            family="bispecific_vhh_cmc",
            entrypoint="run_bispecific_vhh_cmc.py",
            n_pass=n_p, n_warn=n_w, n_fail=n_f,
            adi_score=sum(adi_vals) / len(adi_vals) if adi_vals else None,
            evidence_ctx=_evidence_ctx,
            exit_code=final_code,
        )
        _collector.emit(_run_event)
    except Exception:
        pass

    return final_code


if __name__ == "__main__":
    sys.exit(main())
