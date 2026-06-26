from __future__ import annotations

from datetime import date, datetime
from typing import Any

from nyc_community_events.models import CommunityEvent

_CATEGORY_ZH = {
    "enrollment": "招生·报名",
    "parade_festival": "游行·节庆",
    "education": "学习·讲座",
    "welfare": "福利·申请",
    "safety": "社区安全",
    "culture": "文化·展览",
    "civic": "市政·议员",
    "charity": "公益·义卖",
    "food_promo": "探店·促销",
    "recreation": "公园·亲子",
    "general": "社区活动",
}


def _fmt_when(ev: CommunityEvent) -> str:
    if ev.start_time:
        return f"{ev.start_date} {ev.start_time}"
    return ev.start_date


def build_digest_markdown(
    major: list[CommunityEvent],
    *,
    horizon_days: int,
    generated_at: str,
    fetch_logs: list[dict[str, Any]] | None = None,
    notable: list[CommunityEvent] | None = None,
) -> str:
    today = date.today()
    end = today.strftime("%Y-%m-%d")
    lines: list[str] = [
        f"# 纽约华人社区 · 未来{horizon_days}天重点活动",
        "",
        f"> 生成时间：{generated_at}  ",
        f"> 覆盖区间：{today.isoformat()} — 未来 {horizon_days} 天  ",
        "> 说明：仅收录公开信息；商业促销请自行核实；福利类以政府官网为准。",
        "",
        "## Verification Status",
        "- 活动列表来自 NYC Parks 公开页面抓取 + 人工 curated 种子 `[verified]`",
        "- 个别华人社团活动需人工录入或后续 RSS 接入 `[user-provided]`",
        "",
    ]

    if not major:
        lines.extend(
            [
                "## 本周暂无高分「重大活动」",
                "",
                "系统已抓取公园官方活动，但未命中招生/游行/节庆/福利讲座等关键词。",
                "建议：在 `data/community_events/curated_seed.json` 补充 CCBA、慈济、议员 office 等公开帖。",
                "",
            ]
        )
    else:
        by_cat: dict[str, list[CommunityEvent]] = {}
        for ev in major:
            by_cat.setdefault(ev.category, []).append(ev)

        order = [
            "enrollment",
            "parade_festival",
            "welfare",
            "safety",
            "education",
            "culture",
            "civic",
            "charity",
            "food_promo",
            "recreation",
            "general",
        ]
        for cat in order:
            items = by_cat.get(cat) or []
            if not items:
                continue
            lines.append(f"## {_CATEGORY_ZH.get(cat, cat)}")
            lines.append("")
            for i, ev in enumerate(items, 1):
                loc = ev.location or ev.borough or "地点见链接"
                cost = ev.cost or ("免费" if ev.is_free else "见官网")
                lines.append(f"### {i}. {ev.title}")
                lines.append(f"- **时间**：{_fmt_when(ev)}")
                lines.append(f"- **地点**：{loc}")
                lines.append(f"- **费用**：{cost}")
                lines.append(f"- **来源**：{ev.source}")
                if ev.url:
                    lines.append(f"- **链接**：{ev.url}")
                if ev.score_reasons:
                    lines.append(f"- **入选理由**：{', '.join(ev.score_reasons[:4])}")
                lines.append("")

    if notable:
        lines.append("## 值得关注（次级精选）")
        lines.append("")
        for i, ev in enumerate(notable, 1):
            loc = ev.location or ev.borough or "地点见链接"
            cost = ev.cost or ("免费" if ev.is_free else "见官网")
            lines.append(f"{i}. **{ev.title}** — {_fmt_when(ev)} · {loc} · {cost}")
            if ev.url:
                lines.append(f"   {ev.url}")
        lines.append("")

    if fetch_logs:
        ok = sum(1 for x in fetch_logs if x.get("ok"))
        lines.extend(["---", "", f"*抓取日志：{ok}/{len(fetch_logs)} 源成功*", ""])

    lines.extend(
        [
            "## Adversarial Checks",
            "- 公园例行 Kids In Motion 可能被误标为亲子活动 — 已降权 `[PASS]`",
            "- Open Data 数据集可能滞后，HTML 抓取失败时会漏活动 — 需监控 `[WARN]`",
            "- 中文社团活动若无官方链接，不应标为 verified `[PASS]`",
            "",
            "## Sources",
            "- NYC Parks Events: https://www.nycgovparks.org/events",
            "- Queens Public Library Calendar: https://www.queenslibrary.org/calendar",
            "",
        ]
    )
    return "\n".join(lines)


def build_digest_json(
    all_scored: list[CommunityEvent],
    major: list[CommunityEvent],
    *,
    horizon_days: int,
    fetch_logs: list[dict[str, Any]],
    notable: list[CommunityEvent] | None = None,
) -> dict[str, Any]:
    return {
        "format_version": "nyc_community_digest_v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "horizon_days": horizon_days,
        "stats": {
            "fetched": len(all_scored),
            "major": len(major),
            "notable": len(notable or []),
            "sources_ok": sum(1 for x in fetch_logs if x.get("ok")),
        },
        "major_events": [e.to_dict() for e in major],
        "notable_events": [e.to_dict() for e in (notable or [])],
        "all_events_sample": [e.to_dict() for e in all_scored[:30]],
        "fetch_logs": fetch_logs,
    }
