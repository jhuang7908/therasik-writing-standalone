#!/usr/bin/env python3
"""
scripts/export_ccfr_replacement_list.py

Extract and display the CC-FR replacement list from config/cc_fr_table_vhvl_v1.json.

Outputs:
  1. config/cc_fr_replacement_list_vhvl.json  — machine-readable flat list
  2. docs/cc_fr_replacement_list_vhvl.md      — human-readable comparison table

Columns in the comparison:
  family | fr_seg | pos | trigger_aa | old_first | cc_fr_best | cc_fr_freq | n_used | support | pos_type | verdict

Verdict categories:
  CONFIRMED   — CC-FR agrees with old rule
  UPGRADED    — CC-FR differs, has clinical data (n >= threshold)
  NO_DATA     — no clinical occurrence of any candidate at this position
  BOUNDARY    — deep_boundary position, CC-FR result unreliable

Usage
-----
  python scripts/export_ccfr_replacement_list.py
  python scripts/export_ccfr_replacement_list.py --min-n 5 --families IGHV1 IGHV3 IGHV4
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

SUITE_ROOT = Path(__file__).resolve().parents[1]
_TABLE_PATH = SUITE_ROOT / "config" / "cc_fr_table_vhvl_v1.json"
_OUT_JSON   = SUITE_ROOT / "config" / "cc_fr_replacement_list_vhvl.json"
_OUT_MD     = SUITE_ROOT / "docs"   / "cc_fr_replacement_list_vhvl.md"

_OLD_SUBS = {
    "F": ["Y"],
    "L": ["S", "T", "Q"],
    "I": ["V"],
    "M": ["L", "Q"],
}

_RARE_FAMILIES = {"IGHV1/OR15", "IGHV3/OR16"}   # skip chimeric/orphon loci


def extract_rows(ccfr: dict, min_n: int = 5,
                 families: List[str] | None = None) -> List[dict]:
    rows = []
    for family in sorted(ccfr):
        if family in _RARE_FAMILIES:
            continue
        if families and family not in families:
            continue
        for fr_seg in ["FR1", "FR2", "FR3"]:
            seg = ccfr[family].get(fr_seg, {})
            for pos_str, entry in sorted(seg.items(), key=lambda x: int(x[0])):
                pos      = int(pos_str)
                support  = entry.get("support_level", "L3_sparse")
                pos_type = entry.get("position_type", "unknown")
                n_used   = entry.get("n_used", 0)
                aa_freq  = entry.get("aa_freq", {})
                aa_top5  = entry.get("aa_top5", [])
                trig_map = entry.get("trigger_analysis", {})

                for trigger_aa, t in trig_map.items():
                    old_first = t.get("old_first_choice", "")
                    cc_best   = t.get("cc_fr_best_aa", "")
                    cc_freq   = t.get("cc_fr_best_freq", 0.0)
                    cc_cands  = t.get("cc_fr_candidates", [])
                    changed   = t.get("changed", False)

                    # Verdict
                    if pos_type == "deep_boundary":
                        verdict = "BOUNDARY"
                    elif n_used < min_n or not cc_best or cc_freq == 0.0:
                        verdict = "NO_DATA"
                    elif changed:
                        verdict = "UPGRADED"
                    else:
                        verdict = "CONFIRMED"

                    # Effective recommendation
                    if verdict == "UPGRADED":
                        recommended = cc_best
                    elif verdict == "CONFIRMED":
                        recommended = old_first  # same
                    else:
                        recommended = old_first  # keep old by default

                    rows.append({
                        "family":      family,
                        "fr_segment":  fr_seg,
                        "fr_pos":      pos,
                        "trigger_aa":  trigger_aa,
                        "old_first":   old_first,
                        "old_all":     _OLD_SUBS.get(trigger_aa, []),
                        "cc_fr_best":  cc_best,
                        "cc_fr_freq":  round(cc_freq, 4),
                        "cc_fr_all":   cc_cands,
                        "recommended": recommended,
                        "n_used":      n_used,
                        "support":     support,
                        "pos_type":    pos_type,
                        "verdict":     verdict,
                        "aa_top5_clinical": aa_top5,
                        # Full freq dict for this position (all AAs observed)
                        "aa_freq_clinical": {
                            k: round(v, 4)
                            for k, v in sorted(aa_freq.items(),
                                               key=lambda x: -x[1])[:10]
                        },
                    })
    return rows


def render_markdown(rows: List[dict]) -> str:
    from collections import Counter

    verdict_counts = Counter(r["verdict"] for r in rows)
    upgraded = [r for r in rows if r["verdict"] == "UPGRADED"]
    confirmed = [r for r in rows if r["verdict"] == "CONFIRMED"]

    lines = [
        "# CC-FR Replacement List — VH/VL",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Overview",
        "",
        "| Verdict | Count | Meaning |",
        "|---------|-------|---------|",
        f"| UPGRADED  | {verdict_counts['UPGRADED']}  | CC-FR clinical context differs from old rule — use CC-FR |",
        f"| CONFIRMED | {verdict_counts['CONFIRMED']} | CC-FR agrees with old rule — old rule validated |",
        f"| BOUNDARY  | {verdict_counts['BOUNDARY']}  | Deep-boundary position — keep old rule (CDR-adjacent) |",
        f"| NO_DATA   | {verdict_counts['NO_DATA']}   | No clinical occurrence — keep old rule as fallback |",
        "",
        "---",
        "",
        "## UPGRADED Positions (CC-FR differs from old rule)",
        "",
        "These are positions where the clinical 9-mer context recommends a **different**",
        "first-choice AA than the old conservative substitution table.",
        "",
        "| Family | Seg | Pos | AA | Old First | CC-FR Best | CC-FR Freq | n | Support | Type |",
        "|--------|-----|-----|----|-----------|------------|------------|---|---------|------|",
    ]

    for r in sorted(upgraded, key=lambda x: (x["family"], x["fr_segment"], x["fr_pos"])):
        lines.append(
            f"| {r['family']} | {r['fr_segment']} | {r['fr_pos']:2d} | {r['trigger_aa']} "
            f"| {r['old_first']} | **{r['cc_fr_best']}** "
            f"| {r['cc_fr_freq']:.4f} | {r['n_used']} | {r['support']} | {r['pos_type']} |"
        )

    # Per-family upgrade detail
    lines += [
        "",
        "### Upgrade Detail (per position, with full clinical AA frequency)",
        "",
    ]
    current_family = None
    for r in sorted(upgraded, key=lambda x: (x["family"], x["fr_segment"], x["fr_pos"])):
        if r["family"] != current_family:
            current_family = r["family"]
            n_ab = r["n_used"]
            lines += [f"#### {current_family}  (n_antibodies ≈ {n_ab})", ""]

        freq_str = ", ".join(f"{aa}={f:.3f}" for aa, f in r["aa_freq_clinical"].items())
        lines.append(
            f"- **{r['fr_segment']}[{r['fr_pos']}]** `{r['trigger_aa']}`→  "
            f"old: `{r['old_first']}` → CC-FR: **`{r['cc_fr_best']}`** "
            f"(freq={r['cc_fr_freq']:.4f})"
        )
        lines.append(f"  - Clinical distribution: {freq_str}")

    # Confirmed section (summary only)
    lines += [
        "",
        "---",
        "",
        "## CONFIRMED Positions (old rule validated by clinical data)",
        "",
        "| Family | Seg | Pos | AA | Rule | CC-FR Freq | n | Support |",
        "|--------|-----|-----|----|------|------------|---|---------|",
    ]
    for r in sorted(confirmed, key=lambda x: (x["family"], x["fr_segment"], x["fr_pos"])):
        lines.append(
            f"| {r['family']} | {r['fr_segment']} | {r['fr_pos']:2d} | {r['trigger_aa']} "
            f"| {r['old_first']} | {r['cc_fr_freq']:.4f} | {r['n_used']} | {r['support']} |"
        )

    return "\n".join(lines)


def render_flat_table(rows: List[dict]) -> str:
    """Plain text summary table for quick review."""
    lines = [
        f"{'Family':<10} {'Seg':<5} {'Pos':>3} {'AA':<3} "
        f"{'OldFirst':<9} {'CCBest':<7} {'Freq':>6} {'n':>5} {'Verdict':<12} {'Type'}",
        "-" * 90,
    ]
    for r in sorted(rows, key=lambda x: (x["verdict"], x["family"], x["fr_segment"], x["fr_pos"])):
        lines.append(
            f"{r['family']:<10} {r['fr_segment']:<5} {r['fr_pos']:>3} {r['trigger_aa']:<3} "
            f"{r['old_first']:<9} {r['cc_fr_best'] or '—':<7} {r['cc_fr_freq']:>6.4f} "
            f"{r['n_used']:>5} {r['verdict']:<12} {r['pos_type']}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export CC-FR replacement list")
    parser.add_argument("--table", default=str(_TABLE_PATH))
    parser.add_argument("--out-json", default=str(_OUT_JSON))
    parser.add_argument("--out-md",   default=str(_OUT_MD))
    parser.add_argument("--min-n", type=int, default=5,
                        help="Min n_used to count as having clinical data")
    parser.add_argument("--families", nargs="*", default=None,
                        help="Filter to specific germline families (e.g. IGHV1 IGHV3)")
    parser.add_argument("--print-table", action="store_true",
                        help="Print plain-text summary to stdout")
    args = parser.parse_args()

    table = json.loads(Path(args.table).read_text(encoding="utf-8"))
    ccfr  = table.get("vhvl_ccfr", table)

    rows = extract_rows(ccfr, min_n=args.min_n, families=args.families)

    # Stats
    from collections import Counter
    v = Counter(r["verdict"] for r in rows)
    print(f"[export] Total entries:  {len(rows)}")
    print(f"         UPGRADED:       {v['UPGRADED']}")
    print(f"         CONFIRMED:      {v['CONFIRMED']}")
    print(f"         BOUNDARY:       {v['BOUNDARY']}")
    print(f"         NO_DATA:        {v['NO_DATA']}")

    # JSON
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_meta": {
            "tool":         "export_ccfr_replacement_list.py",
            "version":      "v1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "min_n":        args.min_n,
            "families":     args.families,
            "source_table": args.table,
        },
        "replacement_list": rows,
    }
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[out] JSON → {out_json}")

    # Markdown
    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_markdown(rows), encoding="utf-8")
    print(f"[out] Markdown → {out_md}")

    # Plain text
    if args.print_table:
        print("\n" + render_flat_table(rows))

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
