#!/usr/bin/env python3
"""Fetch affiliate-safe deal cards for the hub promo section (separate from livelihood ITEMS)."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import feedparser
import requests

from hub_modules_ssot import DEAL_MODULE_ZH, normalize_deal_item

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEEDS = (
    "https://slickdeals.net/newsearch.php?searcharea=deals&searchin=first&rss=1",
    "https://feeds.feedburner.com/SlickdealsnetFP",
)

HEADERS = {
    "User-Agent": "InSynBio-NYCHub/1.0 (+https://insynbio.com/us-chinese-life-hub.html)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def _clean(text: str, *, limit: int = 200) -> str:
    t = re.sub(r"<[^>]+>", " ", text or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit]


def _deal_guide() -> dict[str, str]:
    base = (
        "1. 点击链接查看商家页面详情与购买条件；<br>"
        "2. 价格与库存以商家页面为准，折扣可能随时结束；<br>"
        "3. 通过本站链接购买，我们可能会获得少量佣金（不影响您的价格）。"
    )
    return {
        "guide_zh": base,
        "guide_zht": base.replace("点击", "點擊").replace("通过", "通過").replace("可能会", "可能會"),
        "guide_en": (
            "1. Open the merchant page for full terms and availability.<br>"
            "2. Prices and stock change quickly — confirm on the store site.<br>"
            "3. Purchases via our links may earn a small affiliate commission."
        ),
    }


def fetch_deal_items(*, max_items: int = 12, feed_urls: tuple[str, ...] = DEFAULT_FEEDS) -> list[dict[str, Any]]:
    tz = ZoneInfo("America/New_York")
    now = datetime.now(tz)
    run_iso = now.isoformat(timespec="seconds")
    pub_date = now.strftime("%Y-%m-%d")
    guide = _deal_guide()
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    for feed_url in feed_urls:
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
        except Exception as exc:
            print(f"[deals] feed failed {feed_url}: {exc}", flush=True)
            continue

        for entry in parsed.entries or []:
            url = (entry.get("link") or "").strip()
            if not url or url in seen:
                continue
            title_en = _clean(entry.get("title") or "", limit=120)
            if len(title_en) < 8:
                continue
            seen.add(url)
            summary_en = _clean(entry.get("summary") or entry.get("description") or "", limit=180)
            if not summary_en:
                summary_en = "Slickdeals hot deal — see merchant page for details."
            summary_zh = (
                f"{summary_en}（商业促销信息，非政府或社区公益活动；价格以商家页面为准。）"
            )[:220]
            item = normalize_deal_item({
                "id": f"deal_{len(out) + 1:03d}",
                "module": DEAL_MODULE_ZH,
                "content_kind": "deal",
                "city": "纽约",
                "borough": "",
                "area_zh": "全市",
                "area_zht": "全市",
                "area_en": "Citywide",
                "event_date": pub_date,
                "event_time": "",
                "published_at": pub_date,
                "source_published_at": run_iso,
                "date": pub_date,
                "date_kind": "deal",
                "score": 20,
                "relevance": 0,
                "title_zh": f"🔥 {title_en}",
                "title_zht": f"🔥 {title_en}",
                "title_en": title_en,
                "summary_zh": summary_zh,
                "summary_zht": summary_zh,
                "summary_en": summary_en,
                "url": url,
                "first_indexed_at": run_iso,
                "last_seen_at": run_iso,
                **guide,
            })
            out.append(item)
            if len(out) >= max_items:
                return out
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch Slickdeals RSS for hub promo section")
    ap.add_argument("--max-items", type=int, default=12)
    ap.add_argument("--out", type=Path, default=None, help="Optional JSON output path")
    args = ap.parse_args()
    items = fetch_deal_items(max_items=args.max_items)
    payload = {"count": len(items), "items": items}
    print(json.dumps({"count": len(items)}, ensure_ascii=False))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
