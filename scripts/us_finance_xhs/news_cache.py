#!/usr/bin/env python3

"""Daily news cache for US Finance XHS — fetch on server, consume on send."""

from __future__ import annotations



import json

import os

import re

from datetime import datetime, timedelta, timezone

from pathlib import Path

from typing import Any



from us_finance_xhs.fetch_brief import (

    build_brief_markdown,

    fetch_headlines,

    fetch_yahoo_quotes,

    pick_layout_variant,

)



ROOT = Path(__file__).resolve().parents[2]

_ARCHIVE_DAYS = 30





def cache_root(out_root: Path | None = None) -> Path:

    base = out_root or Path(

        os.environ.get("FINANCE_XHS_OUT_ROOT", ROOT / "outputs" / "us_finance_xhs_scheduled")

    )

    return base / "_news_cache"





def _headline_key(item: dict[str, str]) -> str:

    return re.sub(r"\W+", "", (item.get("title") or "").lower())[:100]





def _load_archive(path: Path) -> list[dict[str, Any]]:

    if not path.exists():

        return []

    try:

        return json.loads(path.read_text(encoding="utf-8"))

    except json.JSONDecodeError:

        return []





def _prune_archive(items: list[dict[str, Any]], *, days: int = _ARCHIVE_DAYS) -> list[dict[str, Any]]:

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    kept: list[dict[str, Any]] = []

    for row in items:

        raw = row.get("first_seen") or row.get("fetched_at") or ""

        try:

            ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))

        except ValueError:

            ts = datetime.now(timezone.utc)

        if ts >= cutoff:

            kept.append(row)

    return kept





def update_headlines_archive(

    headlines: list[dict[str, str]],

    *,

    out_root: Path | None = None,

) -> list[dict[str, Any]]:

    """Merge today's headlines into 30-day rolling archive."""

    root = cache_root(out_root)

    root.mkdir(parents=True, exist_ok=True)

    path = root / "headlines_archive.json"

    now = datetime.now(timezone.utc).isoformat()

    archive = {_headline_key(h): h for h in _load_archive(path)}

    for h in headlines:

        key = _headline_key(h)

        if not key:

            continue

        if key in archive:

            row = dict(archive[key])

            row["last_seen"] = now

            row["relevance_score"] = h.get("relevance_score", row.get("relevance_score"))

        else:

            row = dict(h)

            row["first_seen"] = now

            row["last_seen"] = now

        archive[key] = row

    merged = _prune_archive(list(archive.values()))

    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return merged





def send_state_path(out_root: Path | None = None) -> Path:

    return cache_root(out_root) / "send_state.json"





def should_send_now(*, out_root: Path | None = None, interval_days: int | None = None) -> tuple[bool, str]:

    days = interval_days

    if days is None:

        days = int((os.environ.get("FINANCE_XHS_SEND_INTERVAL_DAYS") or "2").strip() or "2")

    path = send_state_path(out_root)

    if not path.exists():

        return True, "no prior send"

    try:

        state = json.loads(path.read_text(encoding="utf-8"))

        last = state.get("last_send_at")

        if not last:

            return True, "empty last_send_at"

        last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))

        delta = datetime.now(timezone.utc) - last_dt

        if delta >= timedelta(days=days):

            return True, f"elapsed {delta.days}d >= {days}d"

        return False, f"elapsed {delta.total_seconds() / 3600:.1f}h < {days}d"

    except (json.JSONDecodeError, ValueError, TypeError) as exc:

        return True, f"state parse error: {exc}"





def record_send(*, out_root: Path | None = None, out_dir: str = "") -> None:

    path = send_state_path(out_root)

    path.parent.mkdir(parents=True, exist_ok=True)

    state: dict[str, Any] = {}
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, TypeError):
            state = {}

    state["last_send_at"] = datetime.now(timezone.utc).isoformat()
    state["last_out_dir"] = out_dir

    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _et_today_iso() -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()


def should_send_recap_today(*, out_root: Path | None = None) -> tuple[bool, str]:
    """Recap is once per America/New_York calendar day (independent of XHS 2-day interval)."""
    path = send_state_path(out_root)
    today = _et_today_iso()
    if not path.exists():
        return True, "no prior recap"
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        last_day = state.get("last_recap_send_day")
        if last_day == today:
            return False, f"recap already sent today ({today} ET)"
        return True, f"last recap day={last_day or 'never'}"
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        return True, f"state parse error: {exc}"


def record_recap_send(*, out_root: Path | None = None, out_dir: str = "") -> None:
    path = send_state_path(out_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    state: dict[str, Any] = {}
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, TypeError):
            state = {}
    now = datetime.now(timezone.utc)
    state["last_recap_send_at"] = now.isoformat()
    state["last_recap_send_day"] = _et_today_iso()
    state["last_recap_out_dir"] = out_dir
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")





def run_daily_fetch(

    *,

    out_root: Path | None = None,

    loan_topic: dict[str, str],

    edition_theme: str = "dual",

) -> dict[str, Any]:

    """Fetch quotes + headlines; maintain 30-day archive; write latest brief."""

    quotes = fetch_yahoo_quotes()

    headlines = fetch_headlines()

    archive = update_headlines_archive(headlines, out_root=out_root)

    layout = pick_layout_variant()

    brief = build_brief_markdown(

        loan_topic=loan_topic,

        quotes=quotes,

        headlines=headlines,

        layout_variant=layout,

        edition_theme=edition_theme,

        archive_headlines=archive,

    )



    root = cache_root(out_root)

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    day_dir = root / day

    day_dir.mkdir(parents=True, exist_ok=True)



    (day_dir / "news_brief.md").write_text(brief, encoding="utf-8")

    (day_dir / "quotes.json").write_text(

        json.dumps(quotes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"

    )

    (day_dir / "headlines.json").write_text(

        json.dumps(headlines, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"

    )

    (day_dir / "headlines_archive.json").write_text(

        json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"

    )

    meta = {

        "fetched_at": datetime.now(timezone.utc).isoformat(),

        "day": day,

        "quotes_count": len(quotes),

        "headlines_count": len(headlines),

        "archive_count": len(archive),

        "loan_topic_id": loan_topic.get("id"),

        "edition_theme": edition_theme,

        "layout_variant": layout.get("id"),

    }

    (day_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")



    latest = root / "latest"

    latest.mkdir(parents=True, exist_ok=True)

    for name in (

        "news_brief.md",

        "quotes.json",

        "headlines.json",

        "headlines_archive.json",

        "meta.json",

    ):

        src = day_dir / name

        if src.exists():

            latest.joinpath(name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")



    return {"ok": True, "day_dir": str(day_dir), "latest": str(latest), **meta}





def load_cached_brief(

    out_root: Path | None = None,

) -> tuple[str, list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:

    """Return brief markdown, quotes, headlines, meta from latest cache."""

    latest = cache_root(out_root) / "latest"

    brief_path = latest / "news_brief.md"

    if not brief_path.exists():

        raise FileNotFoundError(f"No cached brief at {brief_path}; run daily fetch first.")

    brief = brief_path.read_text(encoding="utf-8")

    quotes = json.loads((latest / "quotes.json").read_text(encoding="utf-8"))

    headlines = json.loads((latest / "headlines.json").read_text(encoding="utf-8"))

    meta = {}

    meta_path = latest / "meta.json"

    if meta_path.exists():

        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    return brief, quotes, headlines, meta

