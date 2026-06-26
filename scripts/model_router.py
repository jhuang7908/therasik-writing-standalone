"""
智慧模型分配路由 — InSynBio Content Studio
------------------------------------------
路由策略：
  科学文稿（英文/双语学术精度优先）→ Claude / GPT-4o
  中文社媒文案（公众号/小红书）      → DeepSeek / Kimi
  视觉质量审核（VQA）               → GPT-4o Vision
  图像生成（无字插画）               → Zhipu CogView (¥0.06/张)
  图像生成（中文文字英雄图）          → gpt-image-2
  图像生成（中文社交视觉/组图）       → Doubao Seedream
  图像生成（英文文字英雄图）          → Gemini or gpt-image-2
"""

from __future__ import annotations
import os
from typing import Literal

# ── Task category types ─────────────────────────────────────────────────────

WritingTask = Literal[
    "scientific_article",    # PubMed-grounded bilingual content
    "wechat_copy",           # 公众号图文
    "xhs_copy",              # 小红书卡片文案
    "ppt_narration",         # PPT 演讲稿/备注
    "fact_check",            # 引用核实
    "review_critic",         # 第三方内容评审
]

ImageTask = Literal[
    "illustration_no_text",  # 无字科学插画 / 背景
    "text_hero_cn",          # 中文标题大字图（封面/ad bar）
    "text_hero_en",          # 英文标题大字图
    "social_group_cn",       # 小红书/公众号组图（≤15张）
    "vqa",                   # GPT-4o 视觉质量审核（不生成图）
]


# ── Provider config ──────────────────────────────────────────────────────────

PROVIDERS = {
    # Writing
    "claude": {
        "env_key": "ANTHROPIC_API_KEY",
        "model": "claude-opus-4-5",
        "tasks": ["scientific_article", "fact_check", "review_critic", "ppt_narration"],
        "strengths": "科学精度、长上下文、双语英中",
        "cost_tier": "medium",
    },
    "gpt4o": {
        "env_key": "OPENAI_API_KEY",
        "model": "gpt-4o",
        "tasks": ["scientific_article", "vqa", "fact_check"],
        "strengths": "VQA视觉审核、英文写作",
        "cost_tier": "medium",
    },
    "deepseek": {
        "env_key": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
        "api_base": "https://api.deepseek.com/v1",
        "tasks": ["wechat_copy", "xhs_copy", "ppt_narration"],
        "strengths": "中文流畅、低成本、快速",
        "cost_tier": "low",
    },
    "kimi": {
        "env_key": "MOONSHOT_API_KEY",
        "model": "moonshot-v1-32k",
        "api_base": "https://api.moonshot.cn/v1",
        "tasks": ["wechat_copy", "xhs_copy", "review_critic"],
        "strengths": "中文内容审核、长文档理解",
        "cost_tier": "low",
    },
    # Image generation
    "gpt-image-2": {
        "env_key": "OPENAI_API_KEY",
        "model": "gpt-image-2",
        "tasks": ["text_hero_cn", "text_hero_en"],
        "strengths": "CJK 文字渲染最可靠",
        "cost_tier": "high",
    },
    "cogview": {
        "env_key": "ZHIPU_API_KEY",
        "model": "cogview-4-250304",
        "tasks": ["illustration_no_text"],
        "strengths": "无字插画最便宜 ¥0.06/张",
        "cost_tier": "low",
    },
    "seedream": {
        "env_key": "DOUBAO_IMAGE_TOKEN",
        "model": "doubao-seedream-4-5-251128",
        "api_base": "https://ark.cn-beijing.volces.com/api/v3/images/generations",
        "tasks": ["social_group_cn", "illustration_no_text"],
        "strengths": "中国社交视觉风格、支持组图 ¥0.25/张",
        "cost_tier": "medium",
    },
    "gemini-image": {
        "env_key": "GEMINI_API_KEY",
        "model": "gemini-2.5-flash-image",
        "tasks": ["text_hero_en"],
        "strengths": "英文字图融合极佳、OpenAI 额度超限备选",
        "cost_tier": "low",
    },
}

# ── Routing table ────────────────────────────────────────────────────────────

ROUTING: dict[str, str] = {
    # Writing tasks → provider key
    "scientific_article": "claude",     # US model first for scientific accuracy
    "fact_check":         "claude",     # US model for citation grounding
    "review_critic":      "kimi",       # Chinese content review → Kimi
    "wechat_copy":        "deepseek",   # 公众号中文 → DeepSeek
    "xhs_copy":           "deepseek",   # 小红书中文 → DeepSeek
    "ppt_narration":      "deepseek",   # PPT 备注 → DeepSeek
    # Image tasks → provider key
    "illustration_no_text": "cogview",  # No text → cheapest
    "text_hero_cn":         "gpt-image-2",  # CN text → gpt-image-2
    "text_hero_en":         "gemini-image", # EN text → Gemini
    "social_group_cn":      "seedream",     # XHS/WeChat group → Seedream
    "vqa":                  "gpt4o",        # Visual QA → GPT-4o Vision
}

# Fallback chain when primary provider key is missing or quota exceeded
FALLBACK: dict[str, str] = {
    "claude":       "gpt4o",
    "gpt4o":        "claude",
    "deepseek":     "kimi",
    "kimi":         "deepseek",
    "cogview":      "seedream",
    "seedream":     "cogview",
    "gpt-image-2":  "seedream",
    "gemini-image": "gpt-image-2",
}


def route(task: WritingTask | ImageTask, prefer_cheap: bool = False) -> dict:
    """
    Return the provider config dict for a given task.

    Args:
        task: Task category string.
        prefer_cheap: If True, prefers the cheapest available provider for
                      tasks that have cost_tier="low" alternatives.

    Returns:
        Provider config dict with keys: env_key, model, api_base (optional),
        strengths, cost_tier. Also includes 'provider_name' and 'key_present'.

    Example:
        cfg = route("scientific_article")
        # → {'provider_name': 'claude', 'model': 'claude-opus-4-5', ...}
    """
    provider_name = ROUTING.get(task)
    if not provider_name:
        raise ValueError(f"Unknown task: {task!r}. Valid tasks: {list(ROUTING)}")

    cfg = dict(PROVIDERS[provider_name])
    cfg["provider_name"] = provider_name
    cfg["key_present"] = bool(os.environ.get(cfg["env_key"]))

    # Try fallback if key is missing
    if not cfg["key_present"]:
        fallback_name = FALLBACK.get(provider_name)
        if fallback_name and os.environ.get(PROVIDERS[fallback_name]["env_key"]):
            cfg = dict(PROVIDERS[fallback_name])
            cfg["provider_name"] = fallback_name
            cfg["key_present"] = True
            cfg["_via_fallback"] = True

    return cfg


def route_summary() -> list[dict]:
    """Return routing table as a list of dicts for logging/reporting."""
    rows = []
    for task, provider_name in ROUTING.items():
        cfg = PROVIDERS[provider_name]
        key_ok = bool(os.environ.get(cfg["env_key"]))
        rows.append({
            "task": task,
            "provider": provider_name,
            "model": cfg["model"],
            "key_env": cfg["env_key"],
            "key_present": key_ok,
            "cost_tier": cfg["cost_tier"],
        })
    return rows


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 60)
    print("InSynBio 智慧模型分配路由 — 当前状态")
    print("=" * 60)
    rows = route_summary()
    col = {"task": 25, "provider": 14, "model": 30, "key_present": 6, "cost_tier": 6}
    header = f"{'Task':<25} {'Provider':<14} {'Model':<30} {'Key':>6} {'Cost':>6}"
    print(header)
    print("-" * len(header))
    for r in rows:
        key_str = "✅" if r["key_present"] else "❌"
        print(f"{r['task']:<25} {r['provider']:<14} {r['model']:<30} {key_str:>6} {r['cost_tier']:>6}")
    print()
    missing = [r for r in rows if not r["key_present"]]
    if missing:
        print(f"⚠️  {len(missing)} provider(s) missing key — fallback chain will activate.")
    else:
        print("All providers configured ✅")
