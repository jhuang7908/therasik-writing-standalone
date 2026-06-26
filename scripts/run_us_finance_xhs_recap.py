#!/usr/bin/env python3
"""
US Finance → 1-card WeChat Moments / Daily 收盘复盘.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

# Optional dotenv
_env = ROOT / "content_generation_tools" / ".env"
if _env.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env, override=True)
    except ImportError:
        pass

# Force loading from /etc/insynbio/finance-xhs.env if exists
_etc_env = Path("/etc/insynbio/finance-xhs.env")
if _etc_env.exists():
    for line in _etc_env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        key = k.strip()
        val = v.strip()
        if key and val and not os.environ.get(key):
            os.environ[key] = val

from us_finance_xhs.news_cache import should_send_recap_today  # noqa: E402
from us_finance_xhs.recap_pipeline import run_recap_pipeline, parse_notify_emails  # noqa: E402

_DEFAULT_RECIPIENTS = "christina600@gmail.com,mail.jing.huang@gmail.com"

def main() -> int:
    ap = argparse.ArgumentParser(description="Run US finance WeChat Moments/Recap sending pipeline")
    ap.add_argument("--email", default="", help="Override recipients (comma-separated)")
    ap.add_argument(
        "--out-root",
        type=Path,
        default=Path(os.environ.get("FINANCE_XHS_OUT_ROOT", ROOT / "outputs" / "us_finance_xhs_scheduled")),
    )
    ap.add_argument("--skip-render", action="store_true")
    ap.add_argument("--skip-guard", action="store_true")
    ap.add_argument("--no-cache", action="store_true", help="Live-fetch brief instead of using cache")
    ap.add_argument("--force-send", action="store_true", help="Ignore any interval or force-run")
    args = ap.parse_args()

    # Determine recipients
    notify_email = args.email or os.environ.get("FINANCE_XHS_NOTIFY_EMAILS") or _DEFAULT_RECIPIENTS
    recipients = parse_notify_emails(notify_email)
    if not recipients:
        print("Error: No recipients found to send recap emails to.")
        return 1

    # Override force render parameters for WeChat recap to modern minimal
    os.environ["FINANCE_XHS_IMAGE_STYLE"] = "modern_office_minimal"
    
    print(f"Starting WeChat Moments /收盘复盘 daily recap pipeline...")
    print(f"Recipients: {recipients}")
    print(f"Output directory root: {args.out_root}")

    if not args.force_send:
        ok, reason = should_send_recap_today(out_root=args.out_root)
        if not ok:
            print(f"Skip recap: {reason}")
            return 0
    
    try:
        summary = run_recap_pipeline(
            out_root=str(args.out_root),
            notify_email=notify_email,
            use_cache=not args.no_cache,
            force_fetch=args.no_cache
        )
        print("\nPipeline run succeeded!")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary.get("ok") else 1
    except Exception as exc:
        print(f"\nPipeline execution failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    sys.exit(main())
