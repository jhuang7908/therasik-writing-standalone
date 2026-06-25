from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def bump_internal_patch(version: str) -> str:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(-.+)?$", version)
    if not match:
        return "0.1.1-internal"
    major, minor, patch, suffix = match.groups()
    return f"{major}.{minor}.{int(patch) + 1}{suffix or ''}"


def cmd_record(args) -> int:
    skill_dir = Path(args.skill_dir)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case_id": args.case_id,
        "failure_class": args.failure_class,
        "lesson": args.lesson,
        "rule_change": args.rule_change,
        "source": args.source,
    }
    case_log = skill_dir / "case_learning_log.jsonl"
    with case_log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    manifest_path = skill_dir / "skill_version_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {"version": "0.1.0-internal"}
    old_version = manifest.get("version", "0.1.0-internal")
    new_version = bump_internal_patch(old_version)
    manifest["version"] = new_version
    manifest["last_updated"] = record["timestamp"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ledger = skill_dir / "version_ledger.jsonl"
    ledger_record = {
        "timestamp": record["timestamp"],
        "object_type": "skill",
        "object_id": "therasik-academic-writing-suite",
        "old_version": old_version,
        "new_version": new_version,
        "change_type": "qa_gate_added",
        "reason": args.lesson,
        "source": args.source,
        "files_changed": ["case_learning_log.jsonl", "skill_version_manifest.json"],
        "qa_status_after_change": "NOT_RUN",
    }
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ledger_record, ensure_ascii=False) + "\n")

    print(f"Recorded to {case_log}")
    return 0


def cmd_list(args) -> int:
    skill_dir = Path(args.skill_dir)
    case_log = skill_dir / "case_learning_log.jsonl"

    if not case_log.exists():
        print("No learning events recorded yet.")
        return 0

    records = []
    with case_log.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not records:
        print("No learning events recorded yet.")
        return 0

    if getattr(args, "json", False):
        print(json.dumps(records, ensure_ascii=False, indent=2))
        return 0

    # Count failure classes
    failure_counts: dict[str, int] = {}
    for r in records:
        fc = r.get("failure_class", "unknown")
        failure_counts[fc] = failure_counts.get(fc, 0) + 1

    print(f"Learning log: {case_log}")
    print(f"Total events: {len(records)}")
    print()
    print(f"{'#':<4} {'case_id':<30} {'failure_class':<30} {'source':<20} timestamp")
    print("-" * 100)
    for i, r in enumerate(records, 1):
        ts = r.get("timestamp", "")[:19]
        print(
            f"{i:<4} {r.get('case_id', ''):<30} {r.get('failure_class', ''):<30}"
            f" {r.get('source', ''):<20} {ts}"
        )

    print()
    print("Failure class counts:")
    for fc, count in sorted(failure_counts.items(), key=lambda x: -x[1]):
        print(f"  {fc}: {count}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Record or list skill learning events")
    parser.add_argument("skill_dir", help="Path to skill root directory")
    sub = parser.add_subparsers(dest="command")

    # record sub-command
    p_record = sub.add_parser("record", help="Record a new learning event")
    p_record.add_argument("--case-id", required=True)
    p_record.add_argument("--failure-class", required=True)
    p_record.add_argument("--lesson", required=True)
    p_record.add_argument("--rule-change", default="")
    p_record.add_argument("--source", default="user_feedback")

    # list sub-command
    p_list = sub.add_parser("list", help="List recorded learning events")
    p_list.add_argument("--json", action="store_true", help="Output raw JSON")

    # Backward-compat: if called without sub-command but with --case-id, treat as 'record'
    args, remainder = parser.parse_known_args()
    if args.command is None:
        # Reconstruct args with 'record' defaults for backward compat
        if "--case-id" in remainder:
            sys.argv.insert(2, "record")
            args = parser.parse_args()
        else:
            parser.print_help()
            return 2

    if args.command == "record":
        return cmd_record(args)
    elif args.command == "list":
        return cmd_list(args)
    else:
        parser.print_help()
        return 2


import sys

if __name__ == "__main__":
    raise SystemExit(main())
