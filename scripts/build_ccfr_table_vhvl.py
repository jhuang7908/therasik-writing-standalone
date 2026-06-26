#!/usr/bin/env python3
"""
scripts/build_ccfr_table_vhvl.py

Build the Clinical-Context FR Replacement (CC-FR) table for VH/VL antibodies.

Method
------
1. Load 842 clinical antibodies (engineered_459_atlas + natural_380_atlas).
2. For each antibody concatenate: FR1 + CDR1 + FR2 + CDR2 + FR3 (real CDRs).
3. Slide a 9-mer window over the full string; for each FR position record:
   - Which AAs appear across the 842 library (grouped by IGHV family).
   - Whether covering 9-mer windows are pure_fr / boundary / deep_boundary.
4. Compute conditional AA frequency per (family, FR-segment, FR-position).
5. For each old-table trigger AA (F/L/I/M), find which candidate
   (from _OLD_CONSERVATIVE_SUBS) the clinical library prefers.
6. Write config/cc_fr_table_vhvl_v1.json.

Backoff hierarchy (when family n is sparse):
  L1  germline family, n >= 20        → high confidence
  L2f germline family, 5 <= n < 20    → medium confidence
  L2a all-VH clinical pool, n >= 5    → medium confidence
  L3  sparse (n < 5)                  → advisory only

Usage
-----
  python scripts/build_ccfr_table_vhvl.py
  python scripts/build_ccfr_table_vhvl.py --output config/cc_fr_table_vhvl_v1.json --verbose
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SUITE_ROOT = Path(__file__).resolve().parents[1]

_ATLAS_PATHS = [
    SUITE_ROOT / "data" / "engineered_459_atlas" / "master_table.csv",
    SUITE_ROOT / "data" / "natural_380_atlas" / "master_table.csv",
]

_DEFAULT_OUTPUT = SUITE_ROOT / "config" / "cc_fr_table_vhvl_v1.json"

# Old conservative substitution table (from run_vhh_surface_reshaping_v1.py)
_OLD_CONSERVATIVE_SUBS: Dict[str, List[str]] = {
    "F": ["Y"],
    "L": ["S", "T", "Q"],
    "I": ["V"],
    "M": ["L", "Q"],
}

_WINDOW_SIZE = 9
_BOUNDARY_THRESHOLD = 4   # FR positions within 4 of CDR boundary → deep_boundary
_N_HIGH = 20              # L1 threshold
_N_MEDIUM = 5             # L2 threshold


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_atlas(verbose: bool = False) -> List[dict]:
    rows = []
    for path in _ATLAS_PATHS:
        if not path.exists():
            print(f"[WARN] Atlas not found: {path}")
            continue
        with open(path, encoding="utf-8") as f:
            batch = list(csv.DictReader(f))
        valid = [r for r in batch if r.get("vh_fr1") and r.get("vh_fr2") and r.get("vh_fr3")]
        if verbose:
            print(f"[load] {path.name}: {len(valid)}/{len(batch)} rows with full VH FRs")
        rows.extend(valid)
    print(f"[load] Total: {len(rows)} antibodies")
    return rows


def _germline_family(germline_str: str) -> str:
    """IGHV3-23*04 → IGHV3"""
    g = (germline_str or "").strip().upper()
    if "-" in g:
        return g.split("-")[0]
    if "*" in g:
        return g.split("*")[0]
    return g


# ---------------------------------------------------------------------------
# Segment mapping helpers
# ---------------------------------------------------------------------------

def build_concat_and_map(
    fr1: str, cdr1: str, fr2: str, cdr2: str, fr3: str
) -> Tuple[str, List[Tuple[str, int]]]:
    """
    Concatenate segments and return (concat_seq, segment_map).
    segment_map[i] = (segment_name, position_within_segment)
    Segment names: FR1, CDR1, FR2, CDR2, FR3.
    """
    seg_map: List[Tuple[str, int]] = []
    concat_parts = []
    for name, seq in [("FR1", fr1), ("CDR1", cdr1), ("FR2", fr2), ("CDR2", cdr2), ("FR3", fr3)]:
        for i, aa in enumerate(seq):
            seg_map.append((name, i))
            concat_parts.append(aa)
    return "".join(concat_parts), seg_map


def _window_type(seg_map: List[Tuple[str, int]], w_start: int) -> str:
    """Classify a 9-mer window: pure_fr if all positions in same FR segment, else boundary."""
    segs = {seg_map[i][0] for i in range(w_start, w_start + _WINDOW_SIZE)}
    if len(segs) == 1 and next(iter(segs)).startswith("FR"):
        return "pure_fr"
    return "boundary"


def _boundary_dist(seg_map: List[Tuple[str, int]], concat_pos: int,
                   seg_lengths: Dict[str, int]) -> int:
    """
    Distance (in AA) from this FR position to the nearest CDR boundary edge.
    0 = adjacent to CDR; large = deep interior.
    """
    seg_name, seg_pos = seg_map[concat_pos]
    if not seg_name.startswith("FR"):
        return 0
    fr_len = seg_lengths.get(seg_name, 1)
    dist_left = seg_pos           # distance from start of FR (CDR on left)
    dist_right = fr_len - 1 - seg_pos  # distance from end of FR (CDR on right)
    return min(dist_left, dist_right)


def _classify_position(boundary_dist: int, covering_window_types: set) -> str:
    """Assign pure_fr / boundary / deep_boundary to a position."""
    if boundary_dist < _BOUNDARY_THRESHOLD:
        return "deep_boundary"
    if "boundary" in covering_window_types:
        return "boundary"
    return "pure_fr"


# ---------------------------------------------------------------------------
# Core statistics
# ---------------------------------------------------------------------------

def compute_stats(rows: List[dict], verbose: bool = False) -> dict:
    """
    Returns:
        family_stats[family][fr_seg][fr_pos] = Counter({AA: count})
        all_vh_stats[fr_seg][fr_pos] = Counter({AA: count})
        position_meta[fr_seg][fr_pos] = {position_type, boundary_dist}
    """
    family_stats: Dict[str, Dict[str, Dict[int, Counter]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(Counter))
    )
    all_vh_stats: Dict[str, Dict[int, Counter]] = defaultdict(lambda: defaultdict(Counter))
    position_meta: Dict[str, Dict[int, dict]] = defaultdict(dict)

    n_ok = 0
    for row in rows:
        family = _germline_family(row.get("vh_germline", ""))
        if not family.startswith("IGHV"):
            continue

        fr1  = row.get("vh_fr1",  "").upper().strip()
        cdr1 = row.get("vh_cdr1", "").upper().strip()
        fr2  = row.get("vh_fr2",  "").upper().strip()
        cdr2 = row.get("vh_cdr2", "").upper().strip()
        fr3  = row.get("vh_fr3",  "").upper().strip()
        if not (fr1 and fr2 and fr3):
            continue

        seg_lengths = {
            "FR1": len(fr1), "CDR1": len(cdr1),
            "FR2": len(fr2), "CDR2": len(cdr2), "FR3": len(fr3),
        }
        concat, seg_map = build_concat_and_map(fr1, cdr1, fr2, cdr2, fr3)
        L = len(concat)

        for concat_pos, (seg_name, seg_pos) in enumerate(seg_map):
            if not seg_name.startswith("FR"):
                continue
            aa = concat[concat_pos]
            if not aa.isalpha():
                continue

            # Accumulate counts
            family_stats[family][seg_name][seg_pos][aa] += 1
            all_vh_stats[seg_name][seg_pos][aa] += 1

            # Compute position metadata once per (seg_name, seg_pos)
            if seg_pos not in position_meta[seg_name]:
                w_starts = range(
                    max(0, concat_pos - _WINDOW_SIZE + 1),
                    min(concat_pos + 1, L - _WINDOW_SIZE + 1),
                )
                covering_types = {_window_type(seg_map, k) for k in w_starts}
                bd = _boundary_dist(seg_map, concat_pos, seg_lengths)
                pos_type = _classify_position(bd, covering_types)
                position_meta[seg_name][seg_pos] = {
                    "position_type": pos_type,
                    "boundary_dist": bd,
                }

        n_ok += 1

    if verbose:
        print(f"[stats] Processed {n_ok} antibodies")
        fam_counts = {}
        for f in family_stats:
            total = 0
            for seg in family_stats[f].values():
                for cnt in seg.values():
                    total += sum(cnt.values())
            fam_counts[f] = total
        for f, n in sorted(fam_counts.items(), key=lambda x: -x[1])[:8]:
            print(f"  {f}: {n} position-observations")

    return {
        "family_stats": family_stats,
        "all_vh_stats": all_vh_stats,
        "position_meta": position_meta,
    }


# ---------------------------------------------------------------------------
# Table compilation
# ---------------------------------------------------------------------------

def compile_table(stats: dict, verbose: bool = False) -> dict:
    """Convert raw counters into the final CC-FR JSON table."""
    family_stats  = stats["family_stats"]
    all_vh_stats  = stats["all_vh_stats"]
    position_meta = stats["position_meta"]

    table: dict = {}
    n_changed = 0
    n_confirmed = 0
    n_no_data = 0

    for family in sorted(family_stats.keys()):
        table[family] = {}
        for fr_seg in ["FR1", "FR2", "FR3"]:
            table[family][fr_seg] = {}
            fam_seg  = family_stats[family].get(fr_seg, {})
            all_seg  = all_vh_stats.get(fr_seg, {})
            all_positions = sorted(set(list(fam_seg.keys()) + list(all_seg.keys())))

            for fr_pos in all_positions:
                fam_cnt = fam_seg.get(fr_pos, Counter())
                all_cnt = all_seg.get(fr_pos, Counter())
                n_fam   = sum(fam_cnt.values())
                n_all   = sum(all_cnt.values())

                # Select counts and support level
                if n_fam >= _N_HIGH:
                    support = "L1"
                    use_cnt = fam_cnt
                    n_used  = n_fam
                elif n_fam >= _N_MEDIUM:
                    support = "L2_family"
                    use_cnt = fam_cnt
                    n_used  = n_fam
                elif n_all >= _N_MEDIUM:
                    support = "L2_all_vh"
                    use_cnt = all_cnt
                    n_used  = n_all
                else:
                    support = "L3_sparse"
                    use_cnt = all_cnt
                    n_used  = n_all

                total = sum(use_cnt.values()) or 1
                aa_freq   = {aa: round(cnt / total, 4)
                             for aa, cnt in use_cnt.most_common()}
                aa_ranked = [aa for aa, _ in use_cnt.most_common()]

                meta = position_meta.get(fr_seg, {}).get(fr_pos, {
                    "position_type": "unknown", "boundary_dist": -1
                })

                # Per trigger-AA: find CC-FR best candidate vs old table
                trigger_analysis: dict = {}
                for trigger_aa, old_list in _OLD_CONSERVATIVE_SUBS.items():
                    old_first = old_list[0]
                    # Score each candidate by clinical frequency
                    scored = [(cand, aa_freq.get(cand, 0.0)) for cand in old_list]
                    scored.sort(key=lambda x: -x[1])
                    best_aa, best_freq = scored[0]

                    changed = best_aa != old_first and best_freq > 0
                    if changed:
                        n_changed += 1
                    elif best_freq > 0:
                        n_confirmed += 1
                    else:
                        n_no_data += 1

                    trigger_analysis[trigger_aa] = {
                        "old_first_choice":  old_first,
                        "cc_fr_best_aa":     best_aa,
                        "cc_fr_best_freq":   best_freq,
                        "cc_fr_candidates":  [{"aa": aa, "freq": f} for aa, f in scored],
                        "changed":           changed,
                        "confidence":        support,
                    }

                table[family][fr_seg][str(fr_pos)] = {
                    "n_family":    n_fam,
                    "n_all_vh":    n_all,
                    "n_used":      n_used,
                    "support_level": support,
                    "position_type": meta["position_type"],
                    "boundary_dist": meta["boundary_dist"],
                    "aa_freq":       aa_freq,
                    "aa_top5":       aa_ranked[:5],
                    "trigger_analysis": trigger_analysis,
                }

    if verbose:
        print(f"\n[compile] changed decisions:   {n_changed}")
        print(f"[compile] confirmed decisions:  {n_confirmed}")
        print(f"[compile] no clinical data:     {n_no_data}")

    return table


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def build_output(table: dict, rows: List[dict]) -> dict:
    return {
        "_meta": {
            "tool":         "build_ccfr_table_vhvl.py",
            "version":      "v1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_antibodies": len(rows),
            "window_size":  _WINDOW_SIZE,
            "boundary_threshold": _BOUNDARY_THRESHOLD,
            "support_levels": {
                "L1":          f"family n >= {_N_HIGH}",
                "L2_family":   f"family {_N_MEDIUM} <= n < {_N_HIGH}",
                "L2_all_vh":   f"all-VH n >= {_N_MEDIUM}",
                "L3_sparse":   f"n < {_N_MEDIUM} (advisory only)",
            },
            "position_types": {
                "pure_fr":       "all 9-mer windows covering this position stay within same FR",
                "boundary":      "some 9-mer windows cross CDR boundary (use with care)",
                "deep_boundary": f"within {_BOUNDARY_THRESHOLD} positions of CDR edge (keep old rule)",
            },
            "old_conservative_subs": _OLD_CONSERVATIVE_SUBS,
            "source_atlases": [str(p) for p in _ATLAS_PATHS],
        },
        "vhvl_ccfr": table,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Build CC-FR table for VH/VL antibodies")
    parser.add_argument("--output", default=str(_DEFAULT_OUTPUT),
                        help="Output JSON path")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    rows  = load_atlas(verbose=args.verbose)
    if not rows:
        print("[ERROR] No antibody rows loaded. Check atlas paths.")
        return 1

    stats = compute_stats(rows, verbose=args.verbose)
    table = compile_table(stats, verbose=args.verbose)
    out   = build_output(table, rows)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[done] CC-FR table written → {out_path}")
    print(f"       Families: {list(table.keys())}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
