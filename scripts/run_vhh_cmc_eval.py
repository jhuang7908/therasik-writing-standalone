#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_vhh_cmc_eval.py — InSynBio AbEngineCore VHH CMC Developability Evaluator
=============================================================================
 VHH  CMC ，
 VHH42 （39  VHH + 3 SAbDab  VHH），
、 ADI 。

 458-IgG 
--------------------------
  IgG CMC  : run_ab_evaluator.py   → AbRef-458 （458  IgG Fab ）
  VHH CMC  : run_vhh_cmc_eval.py  → VHH42   （42 / VHH ）

 core/cmc/ ，：
  IgG  : data/reference/AbRef458_stats_v1.json
  VHH  : data/reference/VHH42_reference_stats_v1.json


----
（）：
    python scripts/run_vhh_cmc_eval.py \\
        --project Caplacizumab_v2 \\
        --seq QVQLVESGG... \\
        [--source-type humanized_camelid] \\
        [--out-dir projects/Caplacizumab_v2/cmc_eval]

（FASTA ）：
    python scripts/run_vhh_cmc_eval.py \\
        --project VHH_panel \\
        --fasta my_vhh_panel.fasta \\
        [--out-dir results/vhh_panel_cmc]

（JSON ）：
    python scripts/run_vhh_cmc_eval.py \\
        --project VHH_panel \\
        --json my_vhh_panel.json \\  # [{id, sequence}, ...] or {id: sequence, ...}
        [--out-dir results/vhh_panel_cmc]

：
    python scripts/run_vhh_cmc_eval.py \\
        --project my_vhh \\
        --seq-file my_vhh.fa \\
        [--out-dir results/]

：
    --source-type   camelid_wt | transgenic_mouse | murine_wt_vh | conventional_vh | humanized
                    (，)
    --ref-stats     （ VHH42_reference_stats_v1.json）
    --json-only      JSON， MD
    --no-percentile （）
    --out-dir       （ projects/<project>/cmc_eval）

（15  + ADI ）
----------------------------------
  Developability : pI, GRAVY, instability_index, net_charge_pH7,
                   hydro_patch_max9, charge_patch_max7
  Aggregation    : SAP_score, agg_motifs, hydro_cluster_count
  Chemical liab. : glycosylation_sites, deamidation_sites,
                   isomerization_sites, oxidation_sites, free_cys
  Composite      : ADI (0-100, VHH42-calibrated percentile gate)

ADI 
--------
  100      VHH42 
  80-99   Excellent —  WARN 
  60-79   Acceptable —  FAIL （ VHH ）
  40-59   Moderate risk —  VHH 
  <40     High risk — ，


--------
  data/reference/VHH42_reference_stats_v1.json  — 
  data/humanization_assay/vhh42_cmc_reference.json — 
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Suite root
# ─────────────────────────────────────────────────────────────────────────────
_SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SUITE_ROOT))

_VHH42_REF_STATS = _SUITE_ROOT / "data" / "reference" / "VHH42_reference_stats_v1.json"
_VHH42_FULL_REF  = _SUITE_ROOT / "data" / "humanization_assay" / "vhh42_cmc_reference.json"

# ─────────────────────────────────────────────────────────────────────────────
# Import VHH CMC engine (AbEngineCore core module)
# ─────────────────────────────────────────────────────────────────────────────
from core.cmc.vhh_cmc_engine import (
    _VHH_THRESHOLDS, _METRIC_LABELS, _METRIC_DISPLAY_ORDER,
    compute_vhh_metrics_full as compute_vhh_metrics,
    compute_flags, compute_adi_vhh, adi_grade,
    compute_percentile_ranks, load_vhh_ref, evaluate_single_vhh,
)


# ─────────────────────────────────────────────────────────────────────────────
# CLI utilities (not in engine — CLI-layer only)
# ─────────────────────────────────────────────────────────────────────────────

def _die(msg: str, code: int = 1) -> None:
    print(f"\n[ERROR] {msg}", file=sys.stderr)
    sys.exit(code)


def _parse_fasta(text: str) -> List[Dict[str, str]]:
    """Parse FASTA text into list of {id, sequence}."""
    entries = []
    current_id = None
    seq_parts: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if current_id is not None:
                entries.append({"id": current_id, "sequence": "".join(seq_parts).upper()})
            parts = line[1:].split()
            current_id = parts[0] if parts else f"seq_{len(entries)+1}"
            seq_parts = []
        else:
            seq_parts.append(line)
    if current_id is not None and seq_parts:
        entries.append({"id": current_id, "sequence": "".join(seq_parts).upper()})
    return entries


def _load_sequences(args: argparse.Namespace) -> List[Dict[str, str]]:
    """Return list of {id, sequence} from CLI arguments."""
    # Single inline sequence
    if args.seq:
        return [{"id": args.project, "sequence": args.seq.strip().upper()}]

    # Single file (FASTA or plain text)
    if getattr(args, "seq_file", None):
        fp = Path(args.seq_file)
        if not fp.exists():
            _die(f": {fp}")
        text = fp.read_text(encoding="utf-8").strip()
        if text.startswith(">"):
            seqs = _parse_fasta(text)
            if not seqs:
                _die(f"FASTA : {fp}")
            if len(seqs) == 1:
                seqs[0]["id"] = seqs[0].get("id", args.project)
            return seqs
        if text.startswith("{"):
            data = json.loads(text)
            for key in ("sequence", "vhh", "VHH", "seq", "aa"):
                if key in data:
                    return [{"id": args.project, "sequence": data[key].strip().upper()}]
            _die(f"JSON : {fp}")
        return [{"id": args.project, "sequence": text.upper()}]

    # FASTA batch
    if getattr(args, "fasta", None):
        fp = Path(args.fasta)
        if not fp.exists():
            _die(f"FASTA : {fp}")
        seqs = _parse_fasta(fp.read_text(encoding="utf-8"))
        if not seqs:
            _die(f"FASTA : {fp}")
        return seqs

    # JSON batch
    if getattr(args, "json_input", None):
        fp = Path(args.json_input)
        if not fp.exists():
            _die(f"JSON : {fp}")
        data = json.loads(fp.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [{"id": e.get("id", f"VHH{i+1:03d}"), "sequence": e.get("sequence","").upper()}
                    for i, e in enumerate(data)]
        if isinstance(data, dict):
            # {id: sequence} flat dict
            if all(isinstance(v, str) for v in data.values()):
                return [{"id": k, "sequence": v.upper()} for k, v in data.items()]
            # {id: {sequence: ...}} object dict
            result = []
            for k, v in data.items():
                if isinstance(v, dict):
                    seq = v.get("sequence", v.get("vhh", v.get("seq", "")))
                    result.append({"id": k, "sequence": seq.upper()})
                elif isinstance(v, str):
                    result.append({"id": k, "sequence": v.upper()})
            return result
        _die(f"JSON :  list[{{id, sequence}}]  {{id: sequence}}")

    _die(" --seq / --seq-file / --fasta / --json ")


# ─────────────────────────────────────────────────────────────────────────────
# Per-entry evaluation (thin wrapper over engine)
# ─────────────────────────────────────────────────────────────────────────────

def _load_ref_stats(ref_path: Path) -> Dict[str, Any]:
    return load_vhh_ref(ref_path)


def evaluate_one(
    entry: Dict[str, str],
    ref_stats: Dict[str, Any],
    source_type: str = "",
    skip_percentile: bool = False,
) -> Dict[str, Any]:
    """Evaluate one VHH entry dict ({id, sequence}) using the AbEngineCore engine."""
    result = evaluate_single_vhh(
        name=entry["id"],
        seq=entry["sequence"],
        ref_stats=ref_stats,
        skip_percentile=skip_percentile,
    )
    # Re-map keys to match legacy output schema used by render_*_md
    return {
        "vhh_id":                    result["name"],
        "sequence":                  result["sequence"],
        "sequence_length":           result["length"],
        "source_type":               source_type,
        "cmc_metrics":               result["metrics"],
        "risk_flags":                result["risk_flags"],
        "percentile_ranks_vs_vhh42": result["percentile_ranks_vs_vhh42"],
        "adi_score":                 result["adi_score"],
        "adi_grade":                 result["adi_grade"],
        "n_warn":                    result["n_warn"],
        "n_fail":                    result["n_fail"],
        "overall_status":            result["overall_status"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Report rendering
# ─────────────────────────────────────────────────────────────────────────────

def _flag_icon(flag: str) -> str:
    return {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "NA": "—"}.get(flag, flag)


def render_single_md(result: Dict[str, Any], project: str) -> str:
    m = result["cmc_metrics"]
    flags = result["risk_flags"]
    pct = result["percentile_ranks_vs_vhh42"]
    adi = result["adi_score"]
    grade = result["adi_grade"]

    lines = [
        f"# VHH CMC ",
        f"",
        f"> ：{project}  ",
        f"> VHH ID：{result['vhh_id']}  ",
        f"> ：{result['sequence_length']} aa  ",
        f"> ：{datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"> ：VHH42（39  VHH + 3 SAbDab  VHH）",
        "",
        "---",
        "",
        "##  ADI ",
        "",
        f"|  |  | WARN | FAIL |",
        f"|---|---|---|---|",
        f"| **{adi:.0f} / 100** | **{grade}** | {result['n_warn']} | {result['n_fail']} |",
        "",
        "> ADI ：100=VHH42；80-99=Excellent；60-79=Acceptable；40-59=；<40=",
        "",
        "---",
        "",
        "## ",
        "",
        "|  |  |  | vs VHH42  |",
        "|---|---|---|---|",
    ]

    for key in _METRIC_DISPLAY_ORDER:
        val = m.get(key)
        if val is None:
            continue
        flag = flags.get(key, "PASS")
        rank = pct.get(key, "N/A")
        v_str = ("%.3f" % val) if isinstance(val, float) else str(val)
        lines.append(
            f"| {_METRIC_LABELS.get(key, key)} | {v_str} | {_flag_icon(flag)} {flag} | {rank} |"
        )

    # Chemical liability positions
    pos = m.get("_positions", {})
    has_positions = any(pos.get(k) for k in ("glycosylation", "deamidation", "isomerization", "oxidation", "free_cys"))
    if has_positions:
        lines += ["", "### （0-base ）", ""]
        for k, label in [("glycosylation", "N-"), ("deamidation", ""),
                         ("isomerization", ""), ("oxidation", " M/W"),
                         ("free_cys", " Cys")]:
            positions = pos.get(k, [])
            if positions:
                lines.append(f"- **{label}**： {positions}")

    lines += [
        "",
        "---",
        "",
        "## VHH42 ",
        "",
        "|  | p25 | p50 | p75 |  VHH |  |",
        "|---|---|---|---|---|---|",
    ]

    # Load full ref stats for the table
    ref_stats = _load_ref_stats(_VHH42_REF_STATS)
    for key in _METRIC_DISPLAY_ORDER:
        val = m.get(key)
        rs = ref_stats.get(key, {})
        if not rs or val is None:
            continue
        flag = flags.get(key, "PASS")
        v_str = ("%.3f" % val) if isinstance(val, float) else str(val)
        lines.append(
            "| %s | %.3g | %.3g | %.3g | **%s** | %s %s |" % (
                _METRIC_LABELS.get(key, key),
                rs.get("p25", 0), rs.get("p50", 0), rs.get("p75", 0),
                v_str,
                _flag_icon(flag), flag,
            )
        )

    lines += [
        "",
        "---",
        "",
        "## ",
        "",
        f"```",
        result["sequence"],
        f"```",
        "",
        "*Report generated by AbEngineCore VHH CMC Evaluator · InSynBio*",
    ]
    return "\n".join(lines)


def render_batch_md(
    results: List[Dict[str, Any]],
    project: str,
    ref_stats: Dict[str, Any],
) -> str:
    n_pass = sum(1 for r in results if r["overall_status"] == "PASS")
    n_warn = sum(1 for r in results if r["overall_status"] == "WARN")
    n_fail = sum(1 for r in results if r["overall_status"] == "FAIL")

    lines = [
        f"# VHH CMC ",
        f"",
        f"> ：{project}  ",
        f"> ：{len(results)}   ",
        f"> ：VHH42  ",
        f"> ：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## ",
        "",
        f"|  |  |  |",
        f"|---|---|---|",
        f"| PASS（ WARN/FAIL） | {n_pass} | {100*n_pass//len(results)}% |",
        f"| WARN（） | {n_warn} | {100*n_warn//len(results)}% |",
        f"| FAIL（） | {n_fail} | {100*n_fail//len(results)}% |",
        "",
        "ADI ：**%.1f**   ：**%.1f**" % (
            statistics.mean(r["adi_score"] for r in results),
            sorted(r["adi_score"] for r in results)[len(results)//2],
        ),
        "",
        "---",
        "",
        "## ",
        "",
        "| # | ID | len | pI | GRAVY | instab | charge | SAP | agg | ADI | Grade | Status |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for i, r in enumerate(results, 1):
        m = r["cmc_metrics"]
        lines.append(
            "| %d | %s | %d | %.1f | %.3f | %.1f | %.1f | %.3f | %d | **%.0f** | %s | %s |" % (
                i, r["vhh_id"][:28], r["sequence_length"],
                m.get("pI") or 0, m.get("GRAVY") or 0, m.get("instability_index") or 0,
                m.get("net_charge_pH7") or 0, m.get("SAP_score") or 0, m.get("agg_motifs") or 0,
                r["adi_score"], r["adi_grade"], r["overall_status"],
            )
        )

    # Detail sections for non-PASS entries
    problem_entries = [r for r in results if r["overall_status"] != "PASS"]
    if problem_entries:
        lines += ["", "---", "", "## WARN / FAIL ", ""]
        for r in problem_entries:
            flags = r["risk_flags"]
            bad_flags = {k: v for k, v in flags.items() if v in ("WARN", "FAIL")}
            lines += [
                f"### {r['vhh_id']} — ADI {r['adi_score']:.0f} [{r['adi_grade']}]",
                "",
                "|  |  |  |",
                "|---|---|---|",
            ]
            for k, flag in bad_flags.items():
                v = r["cmc_metrics"].get(k, "?")
                v_str = ("%.3f" % v) if isinstance(v, float) else str(v)
                lines.append(
                    f"| {_METRIC_LABELS.get(k, k)} | {v_str} | {_flag_icon(flag)} {flag} |"
                )
            lines.append("")

    lines += [
        "---",
        "",
        "*Report generated by AbEngineCore VHH CMC Evaluator · InSynBio*",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_vhh_cmc_eval.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""\
            InSynBio AbEngineCore — VHH CMC （）
            =========================================================
             VHH  CMC + ADI ，
             VHH42 。
             IgG  run_ab_evaluator.py， VHH 。
        """),
    )
    p.add_argument("--project", "-p", required=True, metavar="ID",
                   help=" /  ID")

    # Sequence input (mutually exclusive)
    seq_group = p.add_mutually_exclusive_group()
    seq_group.add_argument("--seq", "-s", default="", metavar="AA",
                           help=" VHH （）")
    seq_group.add_argument("--seq-file", "-f", default="", metavar="PATH",
                           help="（ / FASTA / JSON）")
    seq_group.add_argument("--fasta", metavar="PATH",
                           help=" FASTA （ VHH）")
    seq_group.add_argument("--json", dest="json_input", metavar="PATH",
                           help=" JSON ：[{id,sequence},...]  {id:seq,...}")

    p.add_argument("--source-type", default="",
                   choices=["", "camelid_wt", "transgenic_mouse", "murine_wt_vh",
                            "conventional_vh", "humanized"],
                   help="VHH （）")
    p.add_argument("--ref-stats", default="", metavar="PATH",
                   help=f"（ {_VHH42_REF_STATS.name}）")
    p.add_argument("--out-dir", default="", metavar="PATH",
                   help="（ projects/<project>/cmc_eval）")
    p.add_argument("--json-only", action="store_true",
                   help=" JSON ， Markdown ")
    p.add_argument("--no-percentile", action="store_true",
                   help=" VHH42 （）")
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # Evidence Gate — pre-flight knowledge check
    _evidence_ctx = None
    try:
        from core.resources.evidence_gate import EvidenceGate, print_evidence_banner
        _gate = EvidenceGate(enable_network=False)
        _evidence_ctx = _gate.check(antibody_name=args.project)
        print_evidence_banner(_evidence_ctx)
    except Exception as e:
        print(f"[VHH-CMC] Evidence gate skipped: {e}", file=sys.stderr)

    # Reference stats
    ref_path = Path(args.ref_stats) if args.ref_stats else _VHH42_REF_STATS
    if not ref_path.exists():
        print(f"[WARN] : {ref_path}，", file=sys.stderr)
    ref_stats = _load_ref_stats(ref_path)

    # Output directory
    out_dir = (
        Path(args.out_dir)
        if args.out_dir
        else _SUITE_ROOT / "projects" / args.project / "cmc_eval"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load sequences
    sequences = _load_sequences(args)
    is_batch = len(sequences) > 1

    w = 62
    print(f"\n{'='*w}")
    print(f"  InSynBio AbEngineCore — VHH CMC ")
    print(f"{'─'*w}")
    print(f"      : {args.project}")
    print(f"    : {len(sequences)}")
    print(f"      : {ref_path.name}")
    print(f"      : {out_dir}")
    print(f"{'='*w}\n")

    # Evaluate
    results = []
    for i, entry in enumerate(sequences, 1):
        vid = entry["id"]
        seq = entry["sequence"]
        if not seq:
            print(f"[{i:03d}] SKIP {vid} — ")
            continue

        print(f"[{i:03d}/{len(sequences):03d}] {vid[:40]:40s}  len={len(seq)}")
        result = evaluate_one(
            entry,
            ref_stats=ref_stats,
            source_type=args.source_type,
            skip_percentile=args.no_percentile,
        )
        m = result["cmc_metrics"]
        print(f"       pI={m.get('pI') or 0:.1f}  GRAVY={m.get('GRAVY') or 0:.3f}  "
              f"instab={m.get('instability_index') or 0:.1f}  charge={m.get('net_charge_pH7') or 0:.1f}  "
              f"SAP={m.get('SAP_score') or 0:.3f}  agg={m.get('agg_motifs') or 0}  "
              f"ADI={result['adi_score']:.0f} [{result['adi_grade']}]  "
              f"WARN={result['n_warn']} FAIL={result['n_fail']}")
        results.append(result)

    if not results:
        _die("")

    # ── Save outputs ──────────────────────────────────────────────────────────
    run_ts = datetime.now().isoformat(timespec="seconds")
    output_payload = {
        "_meta": {
            "project": args.project,
            "run_time": run_ts,
            "n_sequences": len(results),
            "source_type": args.source_type,
            "reference": str(ref_path),
            "pipeline": "run_vhh_cmc_eval",
            "version": "1.0",
        },
        "results": results,
    }

    json_path = out_dir / "vhh_cmc_eval_report.json"
    json_path.write_text(
        json.dumps(output_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[Done] JSON  : {json_path}")

    if not args.json_only:
        if is_batch:
            md_text = render_batch_md(results, args.project, ref_stats)
        else:
            md_text = render_single_md(results[0], args.project)
        md_path = out_dir / "vhh_cmc_eval_report.md"
        md_path.write_text(md_text, encoding="utf-8")
        print(f"[Done] MD    : {md_path}")

    # ── Summary ───────────────────────────────────────────────────────────────
    adi_vals = [r["adi_score"] for r in results]
    n_pass = sum(1 for r in results if r["overall_status"] == "PASS")
    n_warn = sum(1 for r in results if r["overall_status"] == "WARN")
    n_fail = sum(1 for r in results if r["overall_status"] == "FAIL")

    print(f"\n{'='*w}")
    print(f"  ")
    print(f"{'─'*w}")
    print(f"  PASS : {n_pass:2d}   WARN : {n_warn:2d}   FAIL : {n_fail:2d}")
    print(f"  ADI  :  {sum(adi_vals)/len(adi_vals):.1f}  "
          f" {sorted(adi_vals)[len(adi_vals)//2]:.1f}  "
          f" {min(adi_vals):.1f}")
    if n_fail > 0:
        print(f"\n  [WARN] {n_fail}  VHH  FAIL ，")
    print(f"{'='*w}\n")

    final_code = 0 if n_fail == 0 else 1

    # Self-Evolution: emit RunEvent
    try:
        from core.evolution.event_collector import EventCollector
        _collector = EventCollector()
        _run_event = _collector.from_cmc_result(
            project_id=args.project,
            family="vhh_cmc",
            entrypoint="run_vhh_cmc_eval.py",
            n_pass=n_pass, n_warn=n_warn, n_fail=n_fail,
            adi_score=sum(adi_vals) / len(adi_vals) if adi_vals else None,
            evidence_ctx=_evidence_ctx,
            exit_code=final_code,
        )
        _collector.emit(_run_event)
    except Exception:
        pass

    sys.exit(final_code)


if __name__ == "__main__":
    main()
