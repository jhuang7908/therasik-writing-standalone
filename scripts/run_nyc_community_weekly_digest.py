#!/usr/bin/env python3
"""Compatibility entrypoint for the NYC Community Events Digest workflow.

The workflow historically called this file directly. Keep the old CLI surface
while delegating to the maintained nyc_community_events pipeline.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


def _compact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Print a short CI-friendly summary instead of the full event payload."""
    keys = (
        "ok",
        "pipeline_version",
        "generated_at",
        "horizon_days",
        "sources_fetched",
        "total_events_in_window",
        "total_events_scored",
        "markdown_path",
        "cache_path",
        "email",
    )
    return {key: payload.get(key) for key in keys if key in payload}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NYC community events digest")
    parser.add_argument("--days", type=int, default=7, help="Forward-looking event window")
    parser.add_argument("--email", action="store_true", help="Send digest email via configured SMTP")
    parser.add_argument(
        "--legacy-single-source",
        action="store_true",
        help="Use legacy Parks + curated seed mode instead of the multi-source pipeline",
    )
    args = parser.parse_args()

    from nyc_community_events.pipeline import run_daily_digest

    payload = run_daily_digest(
        horizon_days=args.days,
        send_email=args.email,
        use_multi_source=not args.legacy_single_source,
    )
    print(json.dumps(_compact_payload(payload), ensure_ascii=False, indent=2))
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
