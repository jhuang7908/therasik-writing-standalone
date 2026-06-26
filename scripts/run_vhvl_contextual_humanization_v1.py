#!/usr/bin/env python3
"""
scripts/run_vhvl_contextual_humanization_v1.py
=================================================
CLI wrapper for the 3-layer Contextual Substitution Engine.

Designed as a side-by-side replacement for the old single-AA mapping table
(_CONSERVATIVE_SUBS) used in run_vhh_surface_reshaping_v1.py.
This is for VH/VL — VHH must keep using its own protected pipeline.

Examples
--------
1. Inline CLI test on Atezolizumab (IGHV3-23 family):
    python scripts/run_vhvl_contextual_humanization_v1.py \\
        --fr1 EVQLVESGGGLVQPGGSLRLSCAAS \\
        --cdr1 GFTFSDSWIH \\
        --fr2 WVRQAPGKGLEWVA \\
        --cdr2 WISPYGGSTYYADSVKG \\
        --fr3 RFTISADTSKNTAYLQMNSLRAEDTAVYYCAR \\
        --vh-germline IGHV3-23 \\
        --report

2. JSON-only output for pipeline integration:
    python scripts/run_vhvl_contextual_humanization_v1.py ... --json-only

3. Read inputs from a JSON file:
    python scripts/run_vhvl_contextual_humanization_v1.py \\
        --input-json my_antibody.json --report
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

SUITE_ROOT = Path(__file__).resolve().parents[1]
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

from core.humanization.contextual_substitution_engine import (
    ContextualSubstitutionEngine,
    HumanizationResult,
)


def render_text_report(res: HumanizationResult) -> str:
    """Human-readable summary."""
    lines = []
    lines.append("=" * 72)
    lines.append("VH/VL CONTEXTUAL HUMANIZATION REPORT (3-Layer Engine v1)")
    lines.append("=" * 72)
    lines.append(f"VH germline       : {res.vh_germline or 'unspecified'}")
    lines.append(f"Family            : {res.family or 'unspecified'}")
    lines.append(f"Sequence length   : {len(res.input_seq)} (FR1+CDR1+FR2+CDR2+FR3)")
    lines.append("")
    lines.append("─ Position Statistics ─")
    lines.append(f"  FR positions evaluated : {res.n_positions_evaluated}")
    lines.append(f"  Replacements applied   : {res.n_replacements}")
    lines.append(f"  Positions protected    : {res.n_protected}")
    lines.append(f"  Replacements vetoed    : {res.n_vetoed}")
    lines.append(f"  Positions kept (no-data): {res.n_no_data}")
    lines.append("")
    lines.append("─ Decision Source (which layer made the call) ─")
    for layer, count in sorted(res.summary_by_layer.items()):
        lines.append(f"  {layer:12s} : {count}")
    lines.append("")

    # Detailed mutation list (REPLACED only)
    replacements = [d for d in res.decisions if d.decision == "REPLACED"]
    if replacements:
        lines.append(f"─ Replacements ({len(replacements)}) ─")
        lines.append(f"  {'pos':>4s} {'seg':<4s} {'fr_pos':>6s}  {'orig→new':<10s}  {'layer':<10s}  evidence")
        for d in replacements:
            ev_str = ""
            if d.layer == "layer-2":
                ev_str = f"votes {d.evidence.get('top_aa_votes')} vs {d.evidence.get('original_aa_votes')}"
            elif d.layer == "layer-3":
                ev_str = (f"freq {d.evidence.get('candidate_freq', 0):.3f} vs "
                          f"{d.evidence.get('original_freq', 0):.3f} "
                          f"[n={d.evidence.get('n_used')}, {d.evidence.get('support_level')}]")
            lines.append(
                f"  {d.position:>4d} {d.fr_segment:<4s} {d.fr_pos:>6d}  "
                f"{d.original_aa}→{d.proposed_aa:<8s}  {d.layer:<10s}  {ev_str}"
            )
        lines.append("")

    # Vetoed list
    vetoed = [d for d in res.decisions if d.decision == "VETOED"]
    if vetoed:
        lines.append(f"─ CMC-Vetoed Replacements ({len(vetoed)}) ─")
        for d in vetoed:
            lines.append(
                f"  {d.position:>4d} {d.fr_segment:<4s} pos{d.fr_pos:>3d}  "
                f"{d.original_aa}→{d.proposed_aa}  reason: {d.evidence.get('veto_reason')}"
            )
        lines.append("")

    # Sequence diff
    lines.append("─ Sequence Diff ─")
    lines.append(f"  Input : {res.input_seq}")
    lines.append(f"  Output: {res.output_seq}")
    diff = "".join("|" if a == b else "*" for a, b in zip(res.input_seq, res.output_seq))
    lines.append(f"  Diff  : {diff}")
    lines.append("")
    lines.append("=" * 72)
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="VH/VL contextual humanization CLI")
    p.add_argument("--fr1", help="VH FR1 sequence")
    p.add_argument("--cdr1", help="VH CDR1 sequence")
    p.add_argument("--fr2", help="VH FR2 sequence")
    p.add_argument("--cdr2", help="VH CDR2 sequence")
    p.add_argument("--fr3", help="VH FR3 sequence")
    p.add_argument("--vh-germline", default="", help="VH germline (e.g. IGHV3-23)")
    p.add_argument("--input-json", help="Path to JSON with the segment fields above")
    p.add_argument("--report", action="store_true", help="Print human-readable report")
    p.add_argument("--json-only", action="store_true", help="Print JSON only")
    p.add_argument("--out-json", help="Save JSON result to this path")
    p.add_argument("--out-md", help="Save Markdown report to this path")
    args = p.parse_args()

    # Resolve input source
    if args.input_json:
        data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        fr1, cdr1 = data["fr1"], data.get("cdr1", "")
        fr2, cdr2 = data["fr2"], data.get("cdr2", "")
        fr3 = data["fr3"]
        germline = data.get("vh_germline", args.vh_germline)
    else:
        if not (args.fr1 and args.fr2 and args.fr3):
            p.error("Must provide --fr1 --fr2 --fr3 (or --input-json)")
        fr1, cdr1 = args.fr1, args.cdr1 or ""
        fr2, cdr2 = args.fr2, args.cdr2 or ""
        fr3 = args.fr3
        germline = args.vh_germline

    # Run engine
    engine = ContextualSubstitutionEngine(verbose=False)
    result = engine.humanize_fr(
        fr1=fr1, cdr1=cdr1, fr2=fr2, cdr2=cdr2, fr3=fr3,
        vh_germline=germline,
    )

    if args.report or not args.json_only:
        print(render_text_report(result))

    if args.json_only or args.out_json:
        result_dict = engine.to_dict(result)
        if args.out_json:
            out_path = Path(args.out_json)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(result_dict, indent=2, ensure_ascii=False),
                                encoding="utf-8")
            print(f"\n[saved] JSON → {out_path}")
        if args.json_only:
            print(json.dumps(result_dict, indent=2, ensure_ascii=False))

    if args.out_md:
        out_md = Path(args.out_md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(render_text_report(result), encoding="utf-8")
        print(f"[saved] Markdown → {out_md}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
