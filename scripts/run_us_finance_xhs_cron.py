#!/usr/bin/env python3

"""

US Finance → 2-card Xiaohongshu — send cron (every 2 days).



Daily fetch:  python scripts/run_us_finance_xhs_fetch.py

Send:         python scripts/run_us_finance_xhs_cron.py

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



_env = ROOT / "content_generation_tools" / ".env"

if _env.exists():

    try:

        from dotenv import load_dotenv



        load_dotenv(_env, override=True)

    except ImportError:

        pass



from us_finance_xhs.news_cache import should_send_now  # noqa: E402

from us_finance_xhs.pipeline import parse_notify_emails, run_pipeline  # noqa: E402



_DEFAULT_RECIPIENTS = "christina600@gmail.com,mail.jing.huang@gmail.com"





def main() -> int:

    ap = argparse.ArgumentParser(description="Run US finance XHS send pipeline (cron)")

    ap.add_argument("--email", default="", help="Override recipients (comma-separated)")

    ap.add_argument(

        "--out-root",

        type=Path,

        default=Path(os.environ.get("FINANCE_XHS_OUT_ROOT", ROOT / "outputs" / "us_finance_xhs_scheduled")),

    )

    ap.add_argument("--loan-topic-index", type=int, default=None)

    ap.add_argument("--skip-render", action="store_true")

    ap.add_argument("--skip-guard", action="store_true")

    ap.add_argument("--no-cache", action="store_true", help="Live-fetch brief instead of daily cache")

    ap.add_argument("--force-send", action="store_true", help="Ignore 2-day send interval")

    ap.add_argument("--dry-fetch", action="store_true", help="Only fetch brief, no LLM")

    args = ap.parse_args()



    if args.no_cache:

        os.environ["FINANCE_XHS_USE_CACHE"] = "0"



    recipients = parse_notify_emails(args.email) or parse_notify_emails(_DEFAULT_RECIPIENTS)

    os.environ.setdefault("FINANCE_XHS_NOTIFY_EMAILS", _DEFAULT_RECIPIENTS)



    if not args.dry_fetch and not args.force_send:

        ok, reason = should_send_now(out_root=args.out_root)

        if not ok:

            print(json.dumps({"ok": True, "skipped": True, "reason": reason}, ensure_ascii=False, indent=2))

            return 0



    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    out_dir = args.out_root / ts



    if args.dry_fetch:

        from us_finance_xhs.fetch_brief import (

            build_brief_markdown,

            fetch_headlines,

            fetch_yahoo_quotes,

            pick_layout_variant,

        )

        from us_finance_xhs.pipeline import pick_loan_topic



        out_dir.mkdir(parents=True, exist_ok=True)

        topic = pick_loan_topic(run_index=args.loan_topic_index)

        layout = pick_layout_variant(run_index=args.loan_topic_index)

        brief = build_brief_markdown(

            loan_topic=topic,

            quotes=fetch_yahoo_quotes(),

            headlines=fetch_headlines(),

            layout_variant=layout,

        )

        p = out_dir / "news_brief.md"

        p.write_text(brief, encoding="utf-8")

        print(json.dumps({"ok": True, "brief": str(p), "loan_topic": topic.get("id")}, indent=2))

        return 0



    summary = run_pipeline(

        out_dir=out_dir,

        notify_email=",".join(recipients),

        loan_topic_index=args.loan_topic_index,

        skip_render=args.skip_render,

        skip_guard=args.skip_guard,

    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    return 0 if summary.get("ok") else 2





if __name__ == "__main__":

    raise SystemExit(main())

