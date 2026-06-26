#!/usr/bin/env python3
"""
Daily US finance news fetch for XHS pipeline (server cron).

  systemctl enable --now us-finance-xhs-fetch.timer
"""
from __future__ import annotations

import json
import os
import sys
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

from us_finance_xhs.news_cache import run_daily_fetch  # noqa: E402
from us_finance_xhs.fetch_brief import pick_edition_theme  # noqa: E402
from us_finance_xhs.pipeline import pick_loan_topic  # noqa: E402


def main() -> int:
    out_root = Path(os.environ.get("FINANCE_XHS_OUT_ROOT", ROOT / "outputs" / "us_finance_xhs_scheduled"))
    topic = pick_loan_topic()
    theme = pick_edition_theme()
    result = run_daily_fetch(out_root=out_root, loan_topic=topic, edition_theme=theme)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
