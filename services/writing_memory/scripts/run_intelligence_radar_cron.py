#!/usr/bin/env python3
"""
Run all due literature-radar watches (weekly / monthly).

Schedule on VPS (example — daily 08:00 UTC checks due watches):
  0 8 * * * cd /srv/services/writing_memory && .venv/bin/python scripts/run_intelligence_radar_cron.py

Env:
  INTEL_RADAR_CRON_KEY  — sent as X-Intel-Radar-Cron-Key when calling HTTP mode
  WRITING_MEMORY_BASE   — default https://write.insynbio.com
  OPENALEX_EMAIL, LAB_SMTP_* — same as writing-memory service

Direct mode (default): imports app LLM + store in-process (no HTTP).
  python scripts/run_intelligence_radar_cron.py --direct

HTTP mode:
  python scripts/run_intelligence_radar_cron.py --base https://write.insynbio.com
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _http_run_due(base: str, cron_key: str) -> dict:
    url = base.rstrip("/") + "/intelligence/radar/run-due"
    headers = {"Content-Type": "application/json"}
    if cron_key:
        headers["X-Intel-Radar-Cron-Key"] = cron_key
    body = json.dumps({"cron_key": cron_key or None}).encode("utf-8")
    req = Request(url, data=body, method="POST", headers=headers)
    with urlopen(req, timeout=600) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _direct_run_due() -> dict:
    from intelligence_radar import run_due_watches

    # Minimal LLM shim — import from app when running on server with same env.
    import app as wm_app

    return run_due_watches(llm_complete=wm_app._llm_complete)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run due Module 4 literature radar watches")
    ap.add_argument("--base", default=os.environ.get("WRITING_MEMORY_BASE", "https://write.insynbio.com"))
    ap.add_argument("--direct", action="store_true", help="Run in-process (VPS with app on same host)")
    args = ap.parse_args()
    cron_key = (os.environ.get("INTEL_RADAR_CRON_KEY") or "").strip()

    try:
        if args.direct:
            os.chdir(_ROOT)
            result = _direct_run_due()
        else:
            result = _http_run_due(args.base, cron_key)
    except HTTPError as e:
        print("HTTP error:", e.code, e.read().decode("utf-8", errors="replace")[:500], file=sys.stderr)
        return 1
    except URLError as e:
        print("URL error:", e.reason, file=sys.stderr)
        return 1
    except Exception as e:
        print("Failed:", e, file=sys.stderr)
        return 1

    print(json.dumps({
        "due_count": result.get("due_count"),
        "ran": result.get("ran"),
        "results": [
            {
                "watch_id": r.get("watch_id"),
                "ok": r.get("ok"),
                "new_count": r.get("new_count"),
                "report_id": r.get("report_id"),
                "email_sent": (r.get("email") or {}).get("sent"),
            }
            for r in (result.get("results") or [])
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
