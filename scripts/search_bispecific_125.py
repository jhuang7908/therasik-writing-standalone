#!/usr/bin/env python3
"""
Search the bispecific_125 library (metadata SSOT: data/design_rules/bispecific_125_knowledge.json).

Notes:
  - The 125 JSON contains antibody_id, targets, format, phase, demand_type — not amino acid sequences.
  - For VH/VL strings and SP34-class fingerprints, cross-reference bispecific_75_atlas/master_table.csv
    (--with-75) or data/design_rules/igg_like_50_four_arm_fab.json for known Fab arms.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def suite_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_records(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data["records"])


def load_75_ids_and_sp34(path: Path) -> tuple[set[str], list[tuple[str, str]]]:
    """Return (ids_in_75, [(antibody_id, field)] where vh2 contains SP34 fingerprint)."""
    ids: set[str] = set()
    sp34_hits: list[tuple[str, str]] = []
    needle = "GYTFTRYTMHW"
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            aid = (row.get("antibody_id") or "").strip()
            if aid:
                ids.add(aid)
            for key in ("vh1_seq", "vh2_seq", "vl1_seq", "vl2_seq"):
                seq = row.get(key) or ""
                if needle in seq and aid:
                    sp34_hits.append((aid, key))
    return ids, sp34_hits


def main() -> int:
    ap = argparse.ArgumentParser(description="Search bispecific_125_knowledge.json")
    ap.add_argument(
        "--knowledge",
        type=Path,
        default=None,
        help="Path to bispecific_125_knowledge.json (default: suite data/design_rules/)",
    )
    ap.add_argument("--cd3", action="store_true", help="Only entries whose targets mention CD3")
    ap.add_argument(
        "--demand",
        choices=["TCE", "dual_tumor", "immune_costim", "other"],
        help="Filter by demand_type",
    )
    ap.add_argument(
        "--format-class",
        dest="format_class",
        choices=["bispecific_scFv_like", "bispecific_IgG_like"],
        help="Filter by format_class",
    )
    ap.add_argument("--query", "-q", default="", help="Substring match on antibody_id (case-insensitive)")
    ap.add_argument(
        "--target-substr",
        default="",
        help="Substring match on target_raw / targets joined (case-insensitive)",
    )
    ap.add_argument(
        "--with-75",
        action="store_true",
        help="Annotate rows that exist in bispecific_75_atlas (sequence-rich subset)",
    )
    ap.add_argument(
        "--sp34-fingerprint",
        action="store_true",
        help="After filtering, list only antibody_ids that have GYTFTRYTMHW in 75-atlas vh* sequences",
    )
    ap.add_argument("--json", action="store_true", help="Print JSON array instead of TSV")
    args = ap.parse_args()

    root = suite_root()
    know_path = args.knowledge or (root / "data/design_rules/bispecific_125_knowledge.json")
    if not know_path.is_file():
        print(f"Missing {know_path}", file=sys.stderr)
        return 2

    records = load_records(know_path)
    ids_75: set[str] = set()
    sp34_map: dict[str, list[str]] = {}
    atlas_path = root / "data/bispecific_75_atlas/master_table.csv"
    if args.with_75 or args.sp34_fingerprint:
        if not atlas_path.is_file():
            print(f"Missing {atlas_path} (needed for --with-75 / --sp34-fingerprint)", file=sys.stderr)
            return 2
        ids_75, sp34_hits = load_75_ids_and_sp34(atlas_path)
        for aid, fld in sp34_hits:
            sp34_map.setdefault(aid, []).append(fld)

    q = args.query.strip().lower()
    ts = args.target_substr.strip().lower()

    out: list[dict] = []
    for r in records:
        if args.cd3:
            if not any("CD3" in (t or "") for t in r.get("targets", [])):
                continue
        if args.demand and r.get("demand_type") != args.demand:
            continue
        if args.format_class and r.get("format_class") != args.format_class:
            continue
        if q and q not in (r.get("antibody_id") or "").lower():
            continue
        if ts:
            raw = (r.get("target_raw") or "").lower()
            joined = " ".join(r.get("targets") or []).lower()
            if ts not in raw and ts not in joined:
                continue
        aid = r.get("antibody_id") or ""
        if args.sp34_fingerprint:
            if aid not in sp34_map:
                continue
        row = dict(r)
        if args.with_75:
            row["_in_bispecific_75"] = aid in ids_75
        if args.sp34_fingerprint or args.with_75:
            row["_sp34_fingerprint_fields"] = sp34_map.get(aid, [])
        out.append(row)

    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    # TSV to stdout
    if not out:
        print("(no matches)")
        return 0
    cols = [
        "antibody_id",
        "demand_type",
        "format_class",
        "phase_bucket",
        "target_raw",
        "format_raw",
    ]
    if args.with_75:
        cols.append("_in_bispecific_75")
    if args.sp34_fingerprint or (args.with_75 and sp34_map):
        cols.append("_sp34_fingerprint_fields")

    print("\t".join(cols))
    for r in out:
        print("\t".join(str(r.get(c, "")) for c in cols))

    print(f"\n# matches: {len(out)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
