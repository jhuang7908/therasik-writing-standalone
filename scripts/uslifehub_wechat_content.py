#!/usr/bin/env python3
"""Generate WeChat + dual-persona XHS JSON for 美东华人生活圈 from hub index."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _top_events(
    records: list[dict[str, Any]],
    limit: int,
    interests: list[str] | None = None,
) -> list[dict[str, Any]]:
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from send_community_newsletters import filter_events_for_interests

    if not interests:
        interests = [
            "benefits_gov", "education_lang", "health_medical", "transit_travel",
            "culture_festival", "housing_living", "deals_savings",
        ]
    matched = filter_events_for_interests(records, interests)
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


def _write_llm_json(
    events: list[dict[str, Any]],
    out_path: Path,
    *,
    writer_system: str,
    campaign_id: str,
    user_hint: str,
    required_fields: tuple[str, ...],
) -> dict:
    from social_content import SPEC, _call_deepseek, _clean_json, _validate
    from wechat_ad_bar import inject_ad_bar, load_ad_bar_config
    from wechat_cover import ensure_cover_digest

    user_msg = (
        f"本期 campaign_id: {campaign_id}\n"
        f"{user_hint}\n\n"
        f"【民生信息条目 JSON】（共 {len(events)} 条，仅可引用以下内容）:\n"
        f"{json.dumps(events, ensure_ascii=False, indent=2)}"
    )
    system = writer_system + "\n\n## 平台格式规范\n" + SPEC

    raw = _call_deepseek(user_msg, system, max_tokens=8000)
    raw = _clean_json(raw)
    data = json.loads(raw)

    for field in required_fields:
        if field not in data:
            raise ValueError(f"LLM output missing {field}")

    if "wechat" in required_fields:
        ensure_cover_digest(data.setdefault("wechat", {}))
        ad_cfg = ROOT / "config" / "uslifehub_wechat_ad_bar.yaml"
        if ad_cfg.exists():
            inject_ad_bar(data, load_ad_bar_config(ad_cfg))
        else:
            inject_ad_bar(data)

    if "xiaohongshu" in data and "wechat" in data:
        violations = _validate(data)
    elif "xiaohongshu" in data:
        stub = {
            "xiaohongshu": data["xiaohongshu"],
            "wechat": {
                "lead": "x" * 120,
                "sections": [{"title": "t", "body": "x" * 300}] * 5,
                "cover_digest": "x" * 80,
            },
        }
        violations = [v for v in _validate(stub) if v.startswith("XHS")]
    else:
        violations = [v for v in _validate(data) if v.startswith("WeChat")]

    if violations:
        print(f"  Validation warnings ({len(violations)}):")
        for v in violations[:8]:
            print(f"    - {v}")

    data["_meta"] = {
        "campaign_id": campaign_id,
        "n_source_events": len(events),
        "source_event_ids": [str(e.get("id", "")) for e in events if e.get("id")],
        "violations": violations,
    }
    data.setdefault("format_version", "v2.0")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Saved: {out_path.name}")
    return data


def load_hub_records(index_path: Path) -> list[dict[str, Any]]:
    if not index_path.exists():
        raise FileNotFoundError(f"Hub index not found: {index_path}")
    return json.loads(index_path.read_text(encoding="utf-8")).get("records", [])


def build_wechat_from_hub(
    index_path: Path,
    out_path: Path,
    cfg: dict,
    campaign_id: str,
) -> dict:
    records = load_hub_records(index_path)
    limit = int(cfg.get("max_events_for_prompt", 45))
    events = _top_events(records, limit)
    print("  [WeChat] DeepSeek writing official account SSOT...")
    return _write_llm_json(
        events,
        out_path,
        writer_system=cfg.get("wechat_writer_system", ""),
        campaign_id=campaign_id,
        user_hint="请仅输出 wechat 与 format_annotation（不要 xiaohongshu）。",
        required_fields=("wechat",),
    )


def build_xhs_variant_from_hub(
    index_path: Path,
    out_path: Path,
    variant: dict,
    campaign_id: str,
    *,
    exclude_event_ids: set[str] | None = None,
) -> dict:
    records = load_hub_records(index_path)
    interests = variant.get("interests") or []
    limit = int(variant.get("max_events", 28))
    events = _top_events(records, limit, interests=interests)
    if exclude_event_ids:
        events = [e for e in events if str(e.get("id", "")) not in exclude_event_ids]
        if len(events) < 8:
            events = _top_events(records, limit, interests=interests)
    label = variant.get("label", variant.get("id", "xhs"))
    print(f"  [XHS/{label}] DeepSeek writing variant SSOT...")
    hint = (
        f"小红书人设：{label}。"
        f"请仅输出 xiaohongshu 与 format_annotation（不要 wechat）。"
        f"必须与同批次另一小红书版本在标题、卡片叙事、选取条目上明显不同。"
    )
    return _write_llm_json(
        events,
        out_path,
        writer_system=variant.get("writer_system", ""),
        campaign_id=campaign_id,
        user_hint=hint,
        required_fields=("xiaohongshu",),
    )


def build_from_hub(index_path: Path, out_path: Path, cfg: dict, campaign_id: str) -> dict:
    """Legacy: wechat-only main social.json."""
    return build_wechat_from_hub(index_path, out_path, cfg, campaign_id)
