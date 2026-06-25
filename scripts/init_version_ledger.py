from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir")
    parser.add_argument("--object-id", default="therasik-academic-writing-suite")
    parser.add_argument("--version", default="0.1.0-internal")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    ledger = project_dir / "version_ledger.jsonl"
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "object_type": "skill",
        "object_id": args.object_id,
        "old_version": None,
        "new_version": args.version,
        "change_type": "create",
        "reason": "Initialize internal self-use academic writing suite with strict workflow and QA versioning.",
        "source": "system_refactor",
        "files_changed": [],
        "qa_status_after_change": "NOT_RUN",
    }
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(str(ledger))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
