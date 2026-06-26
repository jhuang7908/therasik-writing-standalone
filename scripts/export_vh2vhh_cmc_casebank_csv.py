#!/usr/bin/env python
"""
Export VH->VHH CMC issue casebank JSONL to CSV tables.

Input:
  data/vh_to_vhh_casebank/cmc_issue_sequences.jsonl

Outputs:
  1) vh2vhh_cmc_issue_rows.csv      (one row per sequence x issue flag)
  2) vh2vhh_cmc_issue_summary.csv   (grouped count by issue code/source)
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _parse_issue_code(flag: str) -> str:
    s = str(flag or "").strip()
    if not s:
        return "UNKNOWN"
    parts = s.split(":")
    if len(parts) >= 3:
        code = parts[2]
    else:
        code = parts[-1]
    # Drop trailing details in parentheses for stable grouping keys
    return code.split("(")[0].strip() or "UNKNOWN"


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {i}: {exc}") from exc


def build_issue_rows(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for rec in records:
        case_id = rec.get("case_id")
        job_id = rec.get("job_id")
        source_class = rec.get("source_class")
        source_type = rec.get("source_type")
        sequence_name = rec.get("sequence_name")
        demo_id = rec.get("demo_id")
        selected_strategy = rec.get("selected_strategy")
        selected_template_id = rec.get("selected_template_id")
        selected_germline = rec.get("selected_germline")

        common = {
            "case_id": case_id,
            "job_id": job_id,
            "source_class": source_class,
            "source_type": source_type,
            "sequence_name": sequence_name,
            "demo_id": demo_id,
            "selected_strategy": selected_strategy,
            "selected_template_id": selected_template_id,
            "selected_germline": selected_germline,
        }

        best_status = rec.get("best_cmc_status")
        best_score = rec.get("best_cmc_score")
        best_flags = rec.get("best_cmc_flags") or []
        converted_seq = rec.get("converted_sequence")
        for flag in best_flags:
            rows.append(
                {
                    **common,
                    "sequence_scope": "best_converted",
                    "candidate_id": "selected_best",
                    "clinical_status": best_status,
                    "clinical_score": best_score,
                    "issue_flag": flag,
                    "issue_code": _parse_issue_code(str(flag)),
                    "sequence": converted_seq,
                }
            )

        for c in rec.get("candidate_issues") or []:
            c_flags = c.get("overall_flags") or []
            for flag in c_flags:
                rows.append(
                    {
                        **common,
                        "sequence_scope": "candidate",
                        "candidate_id": c.get("candidate_id"),
                        "clinical_status": c.get("clinical_status"),
                        "clinical_score": c.get("clinical_score"),
                        "issue_flag": flag,
                        "issue_code": _parse_issue_code(str(flag)),
                        "sequence": c.get("sequence"),
                    }
                )
    return rows


def write_rows_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    fields = [
        "case_id",
        "job_id",
        "source_class",
        "source_type",
        "sequence_name",
        "demo_id",
        "selected_strategy",
        "selected_template_id",
        "selected_germline",
        "sequence_scope",
        "candidate_id",
        "clinical_status",
        "clinical_score",
        "issue_code",
        "issue_flag",
        "sequence",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def write_summary_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    counter: Counter = Counter()
    for r in rows:
        key = (r.get("source_class"), r.get("issue_code"), r.get("clinical_status"))
        counter[key] += 1

    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["source_class", "issue_code", "clinical_status", "n_rows"],
        )
        writer.writeheader()
        for (source_class, issue_code, clinical_status), n in sorted(counter.items()):
            writer.writerow(
                {
                    "source_class": source_class,
                    "issue_code": issue_code,
                    "clinical_status": clinical_status,
                    "n_rows": n,
                }
            )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description="Export VH->VHH CMC issue casebank JSONL to CSV")
    ap.add_argument(
        "--jsonl",
        type=Path,
        default=root / "data" / "vh_to_vhh_casebank" / "cmc_issue_sequences.jsonl",
        help="Input casebank JSONL path",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=root / "data" / "vh_to_vhh_casebank",
        help="Output directory for CSV files",
    )
    args = ap.parse_args()

    in_path = args.jsonl
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_path = out_dir / "vh2vhh_cmc_issue_rows.csv"
    summary_path = out_dir / "vh2vhh_cmc_issue_summary.csv"

    if not in_path.exists():
        rows: List[Dict[str, Any]] = []
        write_rows_csv(rows, rows_path)
        write_summary_csv(rows, summary_path)
        print(f"[EMPTY] casebank not found yet: {in_path}")
        print(f"[OK] rows_csv={rows_path}")
        print(f"[OK] summary_csv={summary_path}")
        return 0

    records = list(_iter_jsonl(in_path))
    rows = build_issue_rows(records)
    write_rows_csv(rows, rows_path)
    write_summary_csv(rows, summary_path)

    print(f"[OK] records={len(records)} rows={len(rows)}")
    print(f"[OK] rows_csv={rows_path}")
    print(f"[OK] summary_csv={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

