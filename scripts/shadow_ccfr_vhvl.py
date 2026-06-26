#!/usr/bin/env python3
"""
scripts/shadow_ccfr_vhvl.py

Shadow-mode comparison: old conservative-subs table vs CC-FR table.

For each FR position in the input VH sequence that would be triggered
(i.e. current AA is in {F, L, I, M}), this script reports:
  - Old table first choice
  - CC-FR recommended AA (from clinical 9-mer context statistics)
  - Whether they agree or differ
  - Position confidence and type (pure_fr / boundary / deep_boundary)

Output: JSON + Markdown per-position difference report.

Usage
-----
  python scripts/shadow_ccfr_vhvl.py \\
      --vh EVKLVESGGGLVQPGGSLRLSCAASGFAFSSYDMSWVRQAPGKRLEWVATISFGGGRYTYYPDTVKGRFTISRDNAKNSHYLQMNSLRAEDTAVYYCAR \\
      --vh-germline IGHV3-23 \\
      --fr1 EVKLVESGGGLVQPGGSLRLSCAAS \\
      --cdr1 GFAFSSYD \\
      --fr2 MSWVRQAPGKRLEWVAT \\
      --cdr2 ISGGGRYT \\
      --fr3 YYPDTVKGRFTISRDNAKNSHYLQMNSLRAEDTAVYYC \\
      --out . --report

  # Or pipe from JSON file:
  python scripts/shadow_ccfr_vhvl.py --input-json frags.json --vh-germline IGHV3-23 --report
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SUITE_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_TABLE = SUITE_ROOT / "config" / "cc_fr_table_vhvl_v1.json"

_OLD_CONSERVATIVE_SUBS: Dict[str, List[str]] = {
    "F": ["Y"],
    "L": ["S", "T", "Q"],
    "I": ["V"],
    "M": ["L", "Q"],
}

_SURFACE_HYDROPHOBIC = frozenset("FILMV")   # trigger set for surface-reshaping context


# ---------------------------------------------------------------------------
# Load CC-FR table
# ---------------------------------------------------------------------------

def load_table(path: Path) -> dict:
    if not path.exists():
        print(f"[ERROR] CC-FR table not found: {path}")
        print("        Run: python scripts/build_ccfr_table_vhvl.py")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _family(germline_str: str) -> str:
    g = (germline_str or "").strip().upper()
    if "-" in g:
        return g.split("-")[0]
    if "*" in g:
        return g.split("*")[0]
    return g


# ---------------------------------------------------------------------------
# Per-position lookup
# ---------------------------------------------------------------------------

def lookup_position(
    table: dict,
    family: str,
    fr_seg: str,
    fr_pos: int,
    trigger_aa: str,
) -> Optional[dict]:
    """Return trigger_analysis entry for given family/seg/pos/trigger_aa or None."""
    ccfr = table.get("vhvl_ccfr", table)
    seg_data = ccfr.get(family, {}).get(fr_seg, {})
    pos_entry = seg_data.get(str(fr_pos))
    if pos_entry is None:
        # Try all-VH fallback key (not in table by family → use IGHV1 as sentinel? No.)
        return None
    return {
        "position_type":  pos_entry.get("position_type", "unknown"),
        "boundary_dist":  pos_entry.get("boundary_dist", -1),
        "support_level":  pos_entry.get("support_level", "L3_sparse"),
        "n_family":       pos_entry.get("n_family", 0),
        "n_used":         pos_entry.get("n_used", 0),
        "aa_top5":        pos_entry.get("aa_top5", []),
        "aa_freq":        pos_entry.get("aa_freq", {}),
        "trigger":        pos_entry.get("trigger_analysis", {}).get(trigger_aa),
    }


# ---------------------------------------------------------------------------
# Shadow comparison
# ---------------------------------------------------------------------------

def run_shadow(
    table: dict,
    family: str,
    fr1: str,
    fr2: str,
    fr3: str,
    verbose: bool = False,
) -> Tuple[List[dict], dict]:
    """
    Compare old table vs CC-FR for every triggered FR position.
    Returns (per_position_rows, summary_stats).
    """
    segments = [("FR1", fr1), ("FR2", fr2), ("FR3", fr3)]
    rows = []

    n_total = 0
    n_triggered = 0
    n_changed = 0
    n_confirmed = 0
    n_no_data = 0
    n_deep_boundary = 0

    for fr_seg, fr_seq in segments:
        for fr_pos, aa in enumerate(fr_seq.upper()):
            n_total += 1
            if aa not in _OLD_CONSERVATIVE_SUBS:
                continue

            n_triggered += 1
            old_first = _OLD_CONSERVATIVE_SUBS[aa][0]
            old_all   = _OLD_CONSERVATIVE_SUBS[aa]

            lookup = lookup_position(table, family, fr_seg, fr_pos, aa)

            if lookup is None:
                n_no_data += 1
                row = {
                    "fr_segment":     fr_seg,
                    "fr_pos":         fr_pos,
                    "from_aa":        aa,
                    "old_first":      old_first,
                    "old_candidates": old_all,
                    "cc_fr_best_aa":  None,
                    "cc_fr_freq":     0.0,
                    "position_type":  "unknown",
                    "boundary_dist":  -1,
                    "support_level":  "no_data",
                    "n_used":         0,
                    "changed":        False,
                    "status":         "NO_DATA",
                    "recommendation": f"Keep old rule ({old_first}) — no clinical data",
                }
                rows.append(row)
                continue

            pos_type = lookup["position_type"]
            if pos_type == "deep_boundary":
                n_deep_boundary += 1

            trig = lookup.get("trigger") or {}
            cc_best  = trig.get("cc_fr_best_aa")
            cc_freq  = trig.get("cc_fr_best_freq", 0.0)
            changed  = trig.get("changed", False)
            conf     = lookup["support_level"]
            n_used   = lookup["n_used"]

            # Decision logic
            if pos_type == "deep_boundary":
                status = "KEEP_OLD_BOUNDARY"
                recommendation = f"Keep old rule ({old_first}) — deep_boundary position"
            elif conf == "L3_sparse":
                status = "KEEP_OLD_SPARSE"
                recommendation = f"Keep old rule ({old_first}) — sparse clinical data (n={n_used})"
            elif not cc_best or cc_freq == 0.0:
                status = "KEEP_OLD_NO_MATCH"
                recommendation = f"Keep old rule ({old_first}) — no clinical match for candidates"
                n_no_data += 1
            elif changed:
                n_changed += 1
                status = "CC_FR_DIFFERS"
                recommendation = (
                    f"CC-FR suggests {cc_best} (freq={cc_freq:.3f}, n={n_used}, {conf})"
                    f" vs old rule {old_first}"
                )
            else:
                n_confirmed += 1
                status = "CONFIRMED"
                recommendation = (
                    f"CC-FR confirms {old_first} (freq={cc_freq:.3f}, n={n_used}, {conf})"
                )

            row = {
                "fr_segment":     fr_seg,
                "fr_pos":         fr_pos,
                "from_aa":        aa,
                "old_first":      old_first,
                "old_candidates": old_all,
                "cc_fr_best_aa":  cc_best,
                "cc_fr_freq":     round(cc_freq, 4),
                "cc_fr_candidates": trig.get("cc_fr_candidates", []),
                "aa_top5_clinical": lookup.get("aa_top5", []),
                "aa_freq_clinical":  {
                    k: v for k, v in list(lookup.get("aa_freq", {}).items())[:8]
                },
                "position_type":  pos_type,
                "boundary_dist":  lookup["boundary_dist"],
                "support_level":  conf,
                "n_family":       lookup["n_family"],
                "n_used":         n_used,
                "changed":        changed,
                "status":         status,
                "recommendation": recommendation,
            }
            rows.append(row)
            if verbose:
                marker = "≠" if changed else "="
                print(f"  {fr_seg}[{fr_pos:2d}] {aa} → old:{old_first} {marker} cc:{cc_best or '?'}"
                      f"  ({status}, {conf})")

    summary = {
        "family":            family,
        "fr_positions_total": n_total,
        "triggered":         n_triggered,
        "confirmed":         n_confirmed,
        "changed":           n_changed,
        "no_data":           n_no_data,
        "deep_boundary_skip": n_deep_boundary,
        "agreement_rate":    round(n_confirmed / n_triggered, 3) if n_triggered else None,
        "change_rate":       round(n_changed / n_triggered, 3) if n_triggered else None,
    }
    return rows, summary


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def render_markdown(rows: List[dict], summary: dict, family: str) -> str:
    lines = [
        f"# CC-FR Shadow Report — VH {family}",
        f"",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Germline family | {summary['family']} |",
        f"| FR positions scanned | {summary['fr_positions_total']} |",
        f"| Triggered (F/L/I/M) | {summary['triggered']} |",
        f"| CC-FR confirms old rule | {summary['confirmed']} |",
        f"| CC-FR differs from old rule | {summary['changed']} |",
        f"| Deep-boundary (kept old) | {summary['deep_boundary_skip']} |",
        f"| No clinical data | {summary['no_data']} |",
        f"| Agreement rate | {summary.get('agreement_rate', 'N/A')} |",
        f"| Change rate | {summary.get('change_rate', 'N/A')} |",
        f"",
        f"## Per-Position Detail",
        f"",
        f"| Seg | Pos | AA | Old Rule | CC-FR Best | CC-FR Freq | n_used | Type | Level | Status |",
        f"|-----|-----|----|----------|------------|------------|--------|------|-------|--------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['fr_segment']} | {r['fr_pos']:2d} | {r['from_aa']} "
            f"| {r['old_first']} "
            f"| {r['cc_fr_best_aa'] or '—'} "
            f"| {r['cc_fr_freq']:.3f} "
            f"| {r['n_used']} "
            f"| {r['position_type']} "
            f"| {r['support_level']} "
            f"| {r['status']} |"
        )

    # Highlight differences
    changed_rows = [r for r in rows if r["status"] == "CC_FR_DIFFERS"]
    if changed_rows:
        lines += [
            f"",
            f"## CC-FR Differs from Old Rule ({len(changed_rows)} positions)",
            f"",
        ]
        for r in changed_rows:
            lines.append(
                f"- **{r['fr_segment']} pos {r['fr_pos']}** ({r['from_aa']} →):"
                f" old=**{r['old_first']}**, CC-FR=**{r['cc_fr_best_aa']}**"
                f" (freq={r['cc_fr_freq']:.3f}, n={r['n_used']}, {r['support_level']})"
            )
            # Show full frequency table for this position
            freq = r.get("aa_freq_clinical", {})
            if freq:
                top = sorted(freq.items(), key=lambda x: -x[1])[:6]
                lines.append(f"  - Clinical freq at this position: "
                             + ", ".join(f"{a}={f:.3f}" for a, f in top))

    confirmed_rows = [r for r in rows if r["status"] == "CONFIRMED"]
    if confirmed_rows:
        lines += [
            f"",
            f"## CC-FR Confirms Old Rule ({len(confirmed_rows)} positions)",
            f"",
        ]
        for r in confirmed_rows:
            lines.append(
                f"- **{r['fr_segment']} pos {r['fr_pos']}** ({r['from_aa']} → {r['old_first']})"
                f": confirmed, freq={r['cc_fr_freq']:.3f}, n={r['n_used']}"
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="CC-FR shadow comparison for VH/VL")
    parser.add_argument("--fr1",  required=True, help="VH FR1 sequence (pre-split)")
    parser.add_argument("--cdr1", required=True, help="VH CDR1 sequence")
    parser.add_argument("--fr2",  required=True, help="VH FR2 sequence")
    parser.add_argument("--cdr2", required=True, help="VH CDR2 sequence")
    parser.add_argument("--fr3",  required=True, help="VH FR3 sequence")
    parser.add_argument("--vh-germline", required=True,
                        help="VH germline (e.g. IGHV3-23*04 or IGHV3)")
    parser.add_argument("--table",  default=str(_DEFAULT_TABLE),
                        help="CC-FR table JSON path")
    parser.add_argument("--out",    default=".", help="Output directory")
    parser.add_argument("--report", action="store_true", help="Write Markdown report")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    table  = load_table(Path(args.table))
    family = _family(args.vh_germline)
    print(f"[shadow] Germline family: {family}")

    rows, summary = run_shadow(
        table, family,
        fr1=args.fr1.strip().upper(),
        fr2=args.fr2.strip().upper(),
        fr3=args.fr3.strip().upper(),
        verbose=args.verbose,
    )

    print(f"\n[summary]  triggered={summary['triggered']}"
          f"  confirmed={summary['confirmed']}"
          f"  changed={summary['changed']}"
          f"  no_data={summary['no_data']}"
          f"  agreement={summary.get('agreement_rate')}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "_meta": {
            "tool": "shadow_ccfr_vhvl.py",
            "version": "v1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "vh_germline": args.vh_germline,
            "family": family,
        },
        "summary": summary,
        "per_position": rows,
    }

    json_path = out_dir / f"ccfr_shadow_{family}.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[out] JSON → {json_path}")

    if args.report:
        md = render_markdown(rows, summary, family)
        md_path = out_dir / f"ccfr_shadow_{family}.md"
        md_path.write_text(md, encoding="utf-8")
        print(f"[out] Markdown → {md_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
