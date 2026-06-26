"""Merge per-journal PMC hit-rate reports into one corpus manifest.

Usage:
    python services/writing_memory/ingest/merge_hitrate_reports.py \
        --pnas  services/writing_memory/ingest/_out/pmc_hitrate_20260525T041148Z.json \
        --elife services/writing_memory/ingest/_out/pmc_hitrate_20260525T035459Z.json \
        --plos  services/writing_memory/ingest/_out/pmc_hitrate_20260525T035459Z.json

If --elife and --plos point to the same multi-journal report, each journal
block is extracted by key.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _journal_block(report: dict, key: str) -> dict:
    for j in report.get("journals", []):
        if j.get("key") == key:
            return j
    raise KeyError(f"Journal {key!r} not found in {report}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pnas", required=True, type=Path)
    ap.add_argument("--elife", required=True, type=Path)
    ap.add_argument("--plos", required=True, type=Path)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "_out" / "corpus_manifest.json",
    )
    args = ap.parse_args()

    pnas = _journal_block(_load(args.pnas), "pnas")
    elife = _journal_block(_load(args.elife), "elife")
    plos = _journal_block(_load(args.plos), "plos_med")

    manifest = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_qualified": sum(j["fully_qualified"] for j in (pnas, elife, plos)),
        "sources": {
            "pnas": str(args.pnas),
            "elife": str(args.elife),
            "plos_med": str(args.plos),
        },
        "journals": {
            "pnas": {
                "display": pnas["display"],
                "qualified_count": pnas["fully_qualified"],
                "qualified_pmids": pnas["qualified_pmids"],
            },
            "elife": {
                "display": elife["display"],
                "qualified_count": elife["fully_qualified"],
                "qualified_pmids": elife["qualified_pmids"],
            },
            "plos_med": {
                "display": plos["display"],
                "qualified_count": plos["fully_qualified"],
                "qualified_pmids": plos["qualified_pmids"],
            },
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}  (total={manifest['total_qualified']} PMIDs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
