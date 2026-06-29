#!/usr/bin/env python3
"""Generate WeChat-only social JSON for 美东华人生活圈 from hub_search_index events."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _top_events(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Reuse newsletter priority: import sorter from send_community_newsletters."""
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from send_community_newsletters import filter_events_for_interests

    all_interests = [
        "benefits_gov",
        "education_lang",
        "health_medical",
        "transit_travel",
        "culture_festival",
        "housing_living",
        "deals_savings",
    ]
    matched = filter_events_for_interests(records, all_interests)
    slim = []
    for ev in matched[:limit]:
        slim.append({
            "id": ev.get("id"),
            "module": ev.get("module"),
            "title_zh": ev.get("title_zh"),
            "summary_zh": (ev.get("summary_zh") or "")[:400],
            "url": ev.get("url"),
            "event_date": ev.get("event_date"),
            "first_indexed_at": ev.get("first_indexed_at"),
            "matched_interests": ev.get("matched_interests", []),
        })
    return slim


def _validate_wechat_only(data: dict) -> list[str]:
    violations = []
    wx = data.get("wechat", {})
    sections = wx.get("sections", [])
    if len(sections) != 5:
        violations.append(f"WeChat: sections count={len(sections)}, expected 5")
    lead_len = len(wx.get("lead", ""))
    if not (100 <= lead_len <= 150):
        violations.append(f"WeChat lead length={lead_len}, expected 100-150")
    digest_len = len(wx.get("cover_digest", ""))
    if digest_len and not (50 <= digest_len <= 120):
        violations.append(f"WeChat cover_digest length={digest_len}, expected 50-120")
    return violations


def generate_wechat_content(
    events: list[dict[str, Any]],
    out_path: Path,
    *,
    writer_system: str,
    campaign_id: str,
) -> dict:
    from social_content import (
        SPEC,
        _call_deepseek,
        _clean_json,
    )
    from wechat_ad_bar import inject_ad_bar, load_ad_bar_config
    from wechat_cover import ensure_cover_digest

    user_msg = (
        f"本期 campaign_id: {campaign_id}\n\n"
        f"【民生信息条目 JSON】（共 {len(events)} 条，仅可引用以下内容）:\n"
        f"{json.dumps(events, ensure_ascii=False, indent=2)}\n\n"
        "请输出 format_version v2.0，仅含 wechat 与 format_annotation。"
    )
    system = writer_system + "\n\n## 平台格式规范\n" + SPEC

    print("  [1/2] DeepSeek writing WeChat SSOT...")
    raw = _call_deepseek(user_msg, system, max_tokens=6000)
    raw = _clean_json(raw)
    data = json.loads(raw)

    if "wechat" not in data:
        raise ValueError("LLM output missing wechat field")

    wx = data.setdefault("wechat", {})
    ensure_cover_digest(wx)
    ad_cfg = ROOT / "config" / "uslifehub_wechat_ad_bar.yaml"
    if ad_cfg.exists():
        inject_ad_bar(data, load_ad_bar_config(ad_cfg))
    else:
        inject_ad_bar(data)

    violations = _validate_wechat_only(data)
    if violations:
        print(f"  Validation warnings ({len(violations)}):")
        for v in violations:
            print(f"    - {v}")

    data["_meta"] = {
        "campaign_id": campaign_id,
        "n_source_events": len(events),
        "violations": violations,
    }
    data.setdefault("format_version", "v2.0")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Saved: {out_path}")
    return data


def load_hub_records(index_path: Path) -> list[dict[str, Any]]:
    if not index_path.exists():
        raise FileNotFoundError(f"Hub index not found: {index_path}")
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    return payload.get("records", [])


def build_from_hub(
    index_path: Path,
    out_path: Path,
    cfg: dict,
    campaign_id: str,
) -> dict:
    records = load_hub_records(index_path)
    if not records:
        raise RuntimeError("hub_search_index.json has no records")
    limit = int(cfg.get("max_events_for_prompt", 45))
    events = _top_events(records, limit)
    return generate_wechat_content(
        events,
        out_path,
        writer_system=cfg.get("writer_system", ""),
        campaign_id=campaign_id,
    )
