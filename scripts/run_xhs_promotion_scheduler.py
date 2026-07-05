#!/usr/bin/env python3
"""Compatibility entrypoint for the legacy XHS Promotion Scheduler workflow.

The maintained finance/XHS implementation now lives in:
- run_us_finance_xhs_fetch.py for daily cache refresh
- run_us_finance_xhs_cron.py for scheduled send

This wrapper keeps older GitHub Actions workflows alive while forwarding to the
current scripts.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


def _run_fetch() -> int:
    from run_us_finance_xhs_fetch import main as fetch_main

    old_argv = sys.argv[:]
    try:
        sys.argv = ["run_us_finance_xhs_fetch.py"]
        return int(fetch_main())
    finally:
        sys.argv = old_argv


def _run_cron(*, force_send: bool, skip_render: bool, skip_guard: bool) -> int:
    from run_us_finance_xhs_cron import main as cron_main

    old_argv = sys.argv[:]
    argv = ["run_us_finance_xhs_cron.py"]
    if force_send:
        argv.append("--force-send")
    if skip_render:
        argv.append("--skip-render")
    if skip_guard:
        argv.append("--skip-guard")
    try:
        sys.argv = argv
        return int(cron_main())
    finally:
        sys.argv = old_argv


def main() -> int:
    parser = argparse.ArgumentParser(description="Legacy XHS promotion scheduler compatibility wrapper")
    parser.add_argument("command", nargs="?", default="run", choices=("run", "fetch", "send"))
    parser.add_argument("--campaign", default="us_finance", help="Legacy campaign selector; us_finance is supported")
    parser.add_argument("--due", action="store_true", help="Accepted for legacy workflow compatibility")
    parser.add_argument("--schedule-utc", default="", help="Accepted for legacy workflow compatibility")
    parser.add_argument("--force", action="store_true", help="Force scheduled send")
    parser.add_argument("--force-send", action="store_true", help="Force scheduled send")
    parser.add_argument("--skip-email", action="store_true", help="Refresh cache only; do not send")
    parser.add_argument("--skip-render", action="store_true")
    parser.add_argument("--skip-guard", action="store_true")
    args = parser.parse_args()

    campaign = args.campaign.replace("-", "_").lower()
    if campaign not in {"", "us_finance", "finance", "xhs"}:
        parser.error(f"unsupported campaign: {args.campaign}")

    if args.command == "fetch" or args.skip_email:
        return _run_fetch()
    return _run_cron(
        force_send=args.force or args.force_send,
        skip_render=args.skip_render,
        skip_guard=args.skip_guard,
    )


if __name__ == "__main__":
    raise SystemExit(main())
