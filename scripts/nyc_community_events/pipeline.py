"""NYC Community Events — Daily pipeline orchestrator (v2.0).

Fetches from 30+ sources, scores, filters by 30-day retention window,
generates digest JSON and markdown, optionally sends notification emails.
"""
from __future__ import annotations

import json
import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from nyc_community_events.cache import write_daily_cache
from nyc_community_events.digest import build_digest_json, build_digest_markdown
from nyc_community_events.fetch_sources import (
    fetch_all_sources,
    fetch_parks_events,
    load_curated_seed,
    within_horizon,
)
from nyc_community_events.scoring import filter_major_events, filter_notable_events, score_event

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "nyc_community_event_sources.json"


def _load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def _parse_notify_emails() -> list[str]:
    raw = os.environ.get("NYC_COMMUNITY_NOTIFY_EMAILS") or os.environ.get("FINANCE_XHS_NOTIFY_EMAILS") or ""
    return [x.strip() for x in raw.replace(";", ",").split(",") if x.strip()]


def _smtp_send(subject: str, body_md: str, *, to_addrs: list[str]) -> dict[str, Any]:
    host = os.environ.get("INSYNBIO_SMTP_HOST") or os.environ.get("LAB_SMTP_HOST") or ""
    port = int(os.environ.get("INSYNBIO_SMTP_PORT") or os.environ.get("LAB_SMTP_PORT") or "587")
    user = os.environ.get("INSYNBIO_SMTP_USER") or os.environ.get("LAB_SMTP_USER") or ""
    password = os.environ.get("INSYNBIO_SMTP_PASS") or os.environ.get("LAB_SMTP_PASS") or ""
    if not host or not to_addrs:
        return {"ok": False, "reason": "smtp_or_recipients_missing"}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user or "contact@insynbio.com"
    msg["To"] = ", ".join(to_addrs)
    msg.attach(MIMEText(body_md, "plain", "utf-8"))

    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.sendmail(msg["From"], to_addrs, msg.as_string())
        return {"ok": True, "to": to_addrs}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:400]}


def run_daily_digest(
    *,
    out_root: Path | None = None,
    horizon_days: int | None = None,
    send_email: bool = False,
    use_multi_source: bool = True,
) -> dict[str, Any]:
    """Run the complete daily digest pipeline.

    Args:
        out_root: Output directory. Defaults to outputs/nyc_community_events.
        horizon_days: Forward-looking window for "upcoming" events.
        send_email: Send digest via SMTP.
        use_multi_source: If True, fetch from all 32 configured sources.
                          If False, legacy behavior (Parks + curated seed only).
    """
    cfg = _load_config()
    days = horizon_days or int(cfg.get("horizon_days") or 7)
    boroughs = cfg.get("boroughs_preferred") or ["Queens", "Brooklyn", "Manhattan"]
    threshold = int(cfg.get("major_score_threshold") or 50)
    max_items = int(cfg.get("digest_max_items") or 25)
    exclude_routine = bool(cfg.get("exclude_routine_from_major", True))
    retention = int(cfg.get("retention_days", 30))
    today = date.today()

    if use_multi_source:
        all_events, logs = fetch_all_sources(cfg, deep_dive=True, max_detail_pages=5)
    else:
        list_urls = [src["urls"][0] for src in cfg.get("sources", [])
                     if src.get("parse_module") == "parsers.nyc_parks"]
        if not list_urls:
            list_urls = cfg.get("parks_list_pages") or []
        parks_events, logs = fetch_parks_events(list_urls)
        seed_rel = cfg.get("curated_seed_path") or "data/community_events/curated_seed.json"
        curated = load_curated_seed(ROOT / seed_rel)
        all_events = parks_events + curated

    in_window = [ev for ev in all_events if within_horizon(ev, today=today, days=days)]

    scored = [score_event(ev, boroughs_preferred=boroughs) for ev in in_window]

    quality_cfg = cfg.get("quality_scoring", {})
    for ev in scored:
        if ev.is_free is True:
            ev.score += quality_cfg.get("is_free_bonus", 15)
        if any(kw in (ev.title + ev.description).lower()
               for kw in ("中文", "chinese", "cantonese", "mandarin", "普通话", "粤语")):
            ev.score += quality_cfg.get("chinese_language_support_bonus", 20)

    major = filter_major_events(
        scored,
        threshold=threshold,
        exclude_routine=exclude_routine,
        max_items=max_items,
    )
    notable = filter_notable_events(
        scored,
        major=major,
        min_score=35,
        max_score=threshold - 1,
        exclude_routine=exclude_routine,
        max_items=12,
    )

    payload = build_digest_json(scored, major, horizon_days=days, fetch_logs=logs, notable=notable)
    md = build_digest_markdown(
        major,
        horizon_days=days,
        generated_at=payload["generated_at"],
        fetch_logs=logs,
        notable=notable,
    )

    payload["pipeline_version"] = "2.0.0"
    payload["sources_fetched"] = len(cfg.get("sources", []))
    payload["retention_days"] = retention
    payload["total_events_in_window"] = len(in_window)
    payload["total_events_scored"] = len(scored)

    out_base = out_root or Path(os.environ.get("NYC_COMMUNITY_OUT_ROOT", ROOT / "outputs" / "nyc_community_events"))
    out_base.mkdir(parents=True, exist_ok=True)
    day_tag = today.strftime("%Y%m%d")
    md_path = out_base / f"weekly_digest_{day_tag}.md"
    md_path.write_text(md, encoding="utf-8")
    payload["markdown_path"] = str(md_path)
    payload["ok"] = True

    cache_path = write_daily_cache(payload, out_root=out_base)
    payload["cache_path"] = str(cache_path)

    if send_email:
        subject = f"纽约华人社区 · 未来{days}天重点活动 ({today.isoformat()})"
        payload["email"] = _smtp_send(subject, md, to_addrs=_parse_notify_emails())

    return payload
