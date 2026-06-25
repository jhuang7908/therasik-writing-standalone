"""LLM Router — converts a user brief into a validated ContentDoc JSON.

Routing strategy:
  1. DeepSeek-chat (cheap, fast, strong Chinese) → primary
  2. GPT-4o-mini → fallback if DeepSeek fails or is slow
  3. Claude Haiku → second fallback

Output: a ContentDoc dict ready for image routing + file rendering.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import httpx
from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """你是 Creative Studio 内容策划 AI。
用户提供业务描述，你输出一个严格符合 ContentDoc JSON 协议的对象。

规则：
1. 只输出一个合法 JSON 对象，首尾无多余文字，无 markdown 代码块包裹。
2. 顶层字段: doc_type, meta, brand, blocks（数组）。
3. doc_type 取值: ppt | xiaohongshu | wechat | whitepaper。
4. 每个 block 必须有: block_id, layout, text（含 title 和 bullets 数组）。
5. text 字段使用: title（标题）、subtitle（副标题）、body（正文段落字符串）。
6. bullets 是 block 顶层字段（不在 text 内），为字符串数组，每项一个要点。
7. layout 取值: cover | section | title_bullets | two_column | image_left | image_right | big_number | quote
8. visual 字段可选，如需配图写: "prompt_zh":"[图片描述中文]", "style":"realistic|flat|watercolor|ink", "tier":"stock|standard|premium"。
   对 PPT 封面 (cover) 和 image_left/image_right 布局，建议加 visual 字段。
9. PPT: 按用户要求的页数生成 slide; 小红书: 3-5 张 card; 公众号: 标题+正文+结尾; 白皮书: 10-15 个 section。
10. 语言: 内容全用中文，除非用户明确要求英文。

示例 block (PPT封面):
{
  "block_id": "slide_1",
  "layout": "cover",
  "text": {"title": "AI 驱动的商业分析", "subtitle": "洞察数据，赋能决策"},
  "bullets": [],
  "visual": {"prompt_zh": "现代科技办公室，数据可视化大屏，蓝紫渐变背景，4K超清", "style": "realistic", "tier": "standard"}
}

示例 block (内容页):
{
  "block_id": "slide_2",
  "layout": "title_bullets",
  "text": {"title": "核心优势"},
  "bullets": ["降低研发成本 40%", "提升命中率 3 倍", "全流程自动化"]
}

示例 block (图文页):
{
  "block_id": "slide_3",
  "layout": "image_right",
  "text": {"title": "技术架构", "body": "基于深度学习的多模态融合框架"},
  "bullets": [],
  "visual": {"prompt_zh": "AI神经网络架构图，科技蓝配色，简洁现代", "style": "flat", "tier": "standard"}
}"""


# ---------- helpers ----------

def _strip_json(text: str) -> str:
    """Strip markdown code fences if model wraps output."""
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _build_user_message(brief: str, doc_type: str,
                        template_hint: Optional[str]) -> str:
    parts = [f"业务类型: {doc_type}", f"用户需求: {brief}"]
    if template_hint:
        parts.append(f"模板风格参考: {template_hint}")
    return "\n".join(parts)


# ---------- LLM backends ----------

def _call_deepseek(messages: list[dict]) -> str:
    client = OpenAI(api_key=settings.deepseek_api_key,
                    base_url=settings.deepseek_base_url)
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        max_tokens=4096,
        temperature=0.6,
    )
    return resp.choices[0].message.content


def _call_openai(messages: list[dict]) -> str:
    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=4096,
        temperature=0.6,
    )
    return resp.choices[0].message.content


def _call_claude(messages: list[dict]) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    # Extract system prompt from messages list
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    user_msgs = [m for m in messages if m["role"] != "system"]
    resp = client.messages.create(
        model="claude-haiku-4-5",
        system=system,
        messages=user_msgs,
        max_tokens=4096,
    )
    return resp.content[0].text


# ---------- main entrypoint ----------

_BACKENDS = [
    ("deepseek", _call_deepseek),
    ("openai",   _call_openai),
    ("claude",   _call_claude),
]


def generate_content_doc(brief: str, doc_type: str,
                         template_hint: Optional[str] = None) -> dict[str, Any]:
    """Call LLM router → validated ContentDoc dict.

    Returns:
        ContentDoc dict with extra _meta field:
            _meta.llm_backend: which model succeeded
            _meta.raw_tokens: approximate prompt tokens
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_message(brief, doc_type, template_hint)},
    ]
    last_error = None
    for backend_name, fn in _BACKENDS:
        try:
            raw = fn(messages)
            content = json.loads(_strip_json(raw))
            content["_meta"] = {"llm_backend": backend_name}
            logger.info("LLM router: %s succeeded for doc_type=%s", backend_name, doc_type)
            return content
        except Exception as exc:
            logger.warning("LLM router: %s failed: %s", backend_name, exc)
            last_error = exc

    raise RuntimeError(f"All LLM backends failed. Last error: {last_error}") from last_error
