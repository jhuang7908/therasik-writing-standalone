"""Multi-Agent PPT Pipeline
=========================
Stage 1  OutlineAgent   → slide plan (titles, types, key points per slide)
Stage 2  SlideAgent     → per-slide full content (parallel calls)
Stage 3  DesignAgent    → layout assignment + image prompt per slide
Stage 4  Assembler      → merge into ContentDoc for renderer

Each stage uses a targeted prompt so the LLM produces tight, focused output.
Document text (from PDF/Word) is injected into Stage 1 as grounding context.
"""
from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

logger = logging.getLogger(__name__)

# ── LLM call helper ────────────────────────────────────────────────────────────

def _chat(messages: list[dict], model: str, api_key: str,
          base_url: Optional[str] = None, max_tokens: int = 4096,
          temperature: float = 0.6) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model, messages=messages,
        max_tokens=max_tokens, temperature=temperature,
    )
    return resp.choices[0].message.content


def _parse_json(raw: str) -> dict | list:
    raw = raw.strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw.strip())


def _llm_call(messages: list[dict], keys: dict, max_tokens: int = 4096,
              temperature: float = 0.6, model_pref: str = "auto") -> str:
    """Try preferred model → DeepSeek → GPT fallback."""
    # 1. Try Anthropic if preferred
    if (model_pref == "claude" or "claude" in model_pref) and keys.get("anthropic"):
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=keys["anthropic"])
            # Mapping user request to available system slugs
            model_slug = "claude-4.6-sonnet-medium-thinking" 
            system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_msgs = [m for m in messages if m["role"] != "system"]
            resp = client.messages.create(
                model=model_slug, max_tokens=max_tokens, system=system_msg,
                messages=user_msgs, temperature=temperature
            )
            return resp.content[0].text
        except Exception as e:
            logger.warning("Claude failed: %s", e)

    # 2. Try GPT-5.5 if preferred
    if (model_pref == "gpt5" or "gpt-5" in model_pref) and keys.get("openai"):
        try:
            return _chat(messages, "gpt-5.5-medium", keys["openai"],
                         None, max_tokens, temperature)
        except Exception as e:
            logger.warning("GPT-5.5 failed: %s", e)

    # 3. Try DeepSeek Reasoner if preferred
    if model_pref == "reasoner" and keys.get("deepseek"):
        try:
            return _chat(messages, "deepseek-reasoner", keys["deepseek"],
                         "https://api.deepseek.com/v1", max_tokens, temperature)
        except Exception as e:
            logger.warning("DeepSeek Reasoner failed: %s", e)

    # 4. Try Kimi if preferred
    if (model_pref == "kimi" or "kimi" in model_pref) and keys.get("kimi"):
        try:
            return _chat(messages, "kimi-k2.6", keys["kimi"],
                         "https://api.moonshot.cn/v1", max_tokens, temperature)
        except Exception as e:
            logger.warning("Kimi failed: %s", e)

    # 5. Standard Fallback Chain
    if keys.get("deepseek"):
        try:
            return _chat(messages, "deepseek-chat", keys["deepseek"],
                         "https://api.deepseek.com/v1", max_tokens, temperature)
        except Exception as e:
            logger.warning("DeepSeek failed: %s", e)
    if keys.get("openai"):
        return _chat(messages, "gpt-4o-mini", keys["openai"],
                     max_tokens=max_tokens, temperature=temperature)
    raise RuntimeError("No API key available")


# ══════════════════════════════════════════════════════════════════════════════
# Stage 1: OutlineAgent
# ══════════════════════════════════════════════════════════════════════════════

OUTLINE_SYSTEM = """你是一位资深 PPT 策划师（OutlineAgent），擅长麦肯锡、BCG 等顶级咨询公司的叙事框架。
你的任务是根据用户需求和参考文献，制定一份逻辑严密、具有说服力的 PPT 大纲。

策划原则：
1. 逻辑架构：采用金字塔原理，确保从背景、挑战到解决方案的逻辑闭环。
2. 叙事节奏：封面吸引人，章节过渡清晰，内容页重点突出，结尾有力。
3. 视觉预判：为每一页预设最合适的视觉呈现方式。

输出严格为合法 JSON 数组，每项代表一张幻灯片，格式如下：
[
  {
    "index": 1,
    "slide_type": "cover|section|content|data|image_story|quote|closing",
    "title": "幻灯片标题",
    "key_points": ["关键点1", "关键点2", "关键点3"],
    "needs_image": true|false,
    "image_concept": "一句话描述配图内容（如不需要图写null）。要求：描述具体的画面构图、色彩基调和专业意象（如：极简商务摄影、科技感光效、高调冷色调等）"
  }
]

slide_type 含义：
- cover      封面（只有一张，在第一位）
- section    章节分隔页（无需要点）
- content    普通内容页（要点+标题）
- data       数据/图表页（数字、统计、对比）
- image_story图文故事页（左/右图+文字说明）
- quote      引用/金句页（单一核心金句）
- closing    结尾/致谢/联系页（最后一张）

只输出 JSON 数组，无任何额外文字。"""


def outline_agent(brief: str, slide_count: int, lang: str,
                  doc_text: str, keys: dict, model_pref: str = "auto") -> list[dict]:
    """Stage 1: produce a structured slide plan."""
    doc_section = f"\n\n【参考文献摘录（优先使用以下内容策划PPT，确保专业度）】\n{doc_text[:5000]}" if doc_text else ""
    user_msg = (f"幻灯片数量：{slide_count} 张（含封面和结尾）\n"
                f"语言：{'中文' if lang=='zh' else lang}\n"
                f"用户需求：{brief}"
                + doc_section)
    messages = [{"role": "system", "content": OUTLINE_SYSTEM},
                {"role": "user",   "content": user_msg}]
    # Use higher token limit for Reasoner
    raw = _llm_call(messages, keys, max_tokens=4096, temperature=0.6, model_pref=model_pref)
    plan = _parse_json(raw)
    logger.info("OutlineAgent: %d slides planned", len(plan))
    return plan


# ══════════════════════════════════════════════════════════════════════════════
# Stage 1.5: CriticAgent (The "Pick-y" Reviewer)
# ══════════════════════════════════════════════════════════════════════════════

CRITIC_SYSTEM = """你是一位挑剔的 PPT 审计专家（CriticAgent）。
你的任务是审查策划师（OutlineAgent）给出的大纲，并提出改进建议。

挑刺标准：
1. 逻辑性：从背景到结论的逻辑链条是否完整？是否有跳跃？
2. 冗余度：是否有重复的内容或相似的幻灯片？
3. 专业度：文风是否符合商务/学术规范？
4. 视觉感：预设的图片概念是否能有效辅助文字理解，还是仅仅是装饰？

输出要求：
如果你认为大纲完美，只输出 "PASS"。
如果你认为有改进空间，请列出具体的修改建议（保持简洁）。"""

def critic_agent(plan: list[dict], brief: str, keys: dict, model_pref: str = "kimi") -> str:
    """Stage 1.5: Review the plan and provide feedback."""
    user_msg = f"用户需求：{brief}\n\n当前策划大纲：\n{json.dumps(plan, ensure_ascii=False)}"
    messages = [{"role": "system", "content": CRITIC_SYSTEM},
                {"role": "user",   "content": user_msg}]
    feedback = _llm_call(messages, keys, max_tokens=1024, temperature=0.3, model_pref=model_pref)
    return feedback


# ══════════════════════════════════════════════════════════════════════════════
# Stage 2: SlideAgent (per-slide, run in parallel)
# ══════════════════════════════════════════════════════════════════════════════

SLIDE_SYSTEM = """你是一位 PPT 内容撰写专家（SlideAgent），文风专业、精炼、富有洞察力。
你将根据策划师提供的大纲，撰写每一页的详细内容。

写作准则：
1. 语言风格：专业商务感，多用动词和名词，少用形容词。避免口水话。
2. 精炼度：每个要点（bullet）严格控制在 15-20 字以内，确保在幻灯片上易于阅读。
3. 数据支撑：数据页必须包含具体的量化指标。
4. 事实依据：严格基于参考文献，不编造。

输出格式（严格 JSON，无多余文字）：
{
  "title": "幻灯片标题",
  "subtitle": "副标题或主旨句（总结本页核心洞察，可为空）",
  "bullets": ["要点1", "要点2", "要点3"],
  "body": "适合正文段落的长文本（仅在需要深度解释时使用）",
  "stat_numbers": ["关键数字1", "关键数字2"],
  "quote_text": "金句全文（仅 quote 类型填写）"
}"""


def slide_agent(slide_spec: dict, brief: str, doc_text: str, keys: dict, model_pref: str = "auto") -> dict:
    """Stage 2: write full content for a single slide."""
    doc_hint = f"\n参考文献摘录：{doc_text[:1500]}" if doc_text else ""
    user_msg = (f"幻灯片规格：\n{json.dumps(slide_spec, ensure_ascii=False)}\n\n"
                f"整体演示主题：{brief}" + doc_hint)
    messages = [{"role": "system", "content": SLIDE_SYSTEM},
                {"role": "user",   "content": user_msg}]
    raw = _llm_call(messages, keys, max_tokens=1024, temperature=0.7, model_pref=model_pref)
    content = _parse_json(raw)
    logger.info("SlideAgent: slide %d (%s) done", slide_spec["index"], slide_spec["slide_type"])
    return content


# ══════════════════════════════════════════════════════════════════════════════
# Stage 3: DesignAgent (rule-based + LLM refinement)
# ══════════════════════════════════════════════════════════════════════════════

VISUAL_SYSTEM = """你是一位视觉创意总监（VisualConsultant）。
你的任务是将平淡的 PPT 配图描述转化为极具质感的专业摄影/设计指令。

风格指南：
- 核心风格：极简主义、高端商务摄影、徕卡质感。
- 构图要求：大面积留白、电影感光效、微距或深度透视。
- 避免：AI 塑料感、饱和度过高、低幼插画、混乱的堆砌。

请将用户的原始描述转化为一段 50 字以内的专业 Prompt。"""

def visual_consultant(concept: str, keys: dict, model_pref: str = "kimi") -> str:
    """Refine image concept into a professional visual prompt."""
    messages = [{"role": "system", "content": VISUAL_SYSTEM},
                {"role": "user",   "content": f"原始描述：{concept}"}]
    prompt = _llm_call(messages, keys, max_tokens=256, temperature=0.6, model_pref=model_pref)
    return prompt.strip()


TYPE_TO_LAYOUT = {
    "cover":       "cover",
    "section":     "section",
    "content":     "title_bullets",
    "data":        "big_number",
    "image_story": "image_right",   # alternates below
    "quote":       "quote",
    "closing":     "cover",
}

def design_agent(slide_spec: dict, slide_content: dict,
                 slide_idx: int, keys: dict = None, model_pref: str = "auto") -> dict:
    """Stage 3: assign layout and build visual prompt."""
    stype = slide_spec.get("slide_type", "content")
    layout = TYPE_TO_LAYOUT.get(stype, "title_bullets")

    # Alternate image_story between left and right
    if stype == "image_story":
        layout = "image_left" if slide_idx % 2 == 0 else "image_right"

    # Build bullets: prefer explicit bullets, fall back to key_points from outline
    bullets = slide_content.get("bullets") or []
    if not bullets and slide_content.get("stat_numbers"):
        bullets = slide_content["stat_numbers"]
    if not bullets:
        bullets = slide_spec.get("key_points", [])

    # Visual prompt
    visual = None
    if slide_spec.get("needs_image") and slide_spec.get("image_concept"):
        concept = slide_spec["image_concept"]
        # Use VisualConsultant for premium/kimi tiers
        if keys and model_pref in ("premium", "kimi", "claude"):
            logger.info("VisualConsultant refining prompt for slide %d...", slide_idx)
            refined = visual_consultant(concept, keys, model_pref=model_pref)
            prompt = refined
        else:
            prompt = concept + "，专业商务风格，高清"

        visual = {
            "prompt_zh": prompt,
            "style": "realistic" if stype in ("cover", "image_story", "section") else "flat",
            "tier": "standard",
        }

    block = {
        "block_id": f"slide_{slide_spec['index']}",
        "layout": layout,
        "text": {
            "title":    slide_content.get("title")    or slide_spec.get("title", ""),
            "subtitle": slide_content.get("subtitle") or "",
            "body":     slide_content.get("body")     or "",
            "caption":  "",
        },
        "bullets": bullets,
    }
    if slide_content.get("quote_text"):
        block["text"]["body"] = slide_content["quote_text"]
    if visual:
        block["visual"] = visual

    logger.info("DesignAgent: slide %d → layout=%s, image=%s",
                slide_spec["index"], layout, bool(visual))
    return block


# ══════════════════════════════════════════════════════════════════════════════
# Main entrypoint
# ══════════════════════════════════════════════════════════════════════════════

def run_multi_agent_pipeline(brief: str, doc_type: str, slide_count: int,
                              lang: str, doc_text: str,
                              keys: dict, model_tier: str = "standard") -> dict:
    """Run all 3 stages and return a ContentDoc dict ready for ppt_renderer.

    Args:
        brief:       User's natural language request
        doc_type:    "ppt" (only ppt supported for now)
        slide_count: Target number of slides
        lang:        "zh" | "en" | "bilingual"
        doc_text:    Extracted text from uploaded document (may be empty)
        keys:        {"deepseek": str|None, "openai": str|None, "anthropic": str|None}
        model_tier:  "standard" (DeepSeek) | "premium" (Claude/GPT-5)
    """
    # Define model preferences per stage
    if model_tier == "premium":
        outline_pref = "reasoner"  # DeepSeek R1 for deep logic
        slide_pref   = "claude"    # Claude for premium copy
    elif model_tier == "kimi":
        outline_pref = "kimi"      # Kimi K2.6 for outline
        slide_pref   = "kimi"      # Kimi K2.6 for slides
    else:
        outline_pref = "auto"      # DeepSeek Chat
        slide_pref   = "auto"      # DeepSeek Chat

    # Stage 1: Outline
    logger.info("=== Stage 1: OutlineAgent (%s) ===", outline_pref)
    try:
        plan = outline_agent(brief, slide_count, lang, doc_text, keys, model_pref=outline_pref)
        
        # Stage 1.5: Critic & Refine (only for premium/kimi tiers)
        if model_tier in ("premium", "kimi"):
            logger.info("=== Stage 1.5: CriticAgent Review ===")
            feedback = critic_agent(plan, brief, keys, model_pref=outline_pref)
            if feedback.strip().upper() != "PASS":
                logger.info("Critic feedback: %s", feedback)
                # Re-run outline agent with feedback
                messages = [
                    {"role": "system", "content": OUTLINE_SYSTEM},
                    {"role": "user",   "content": f"用户需求：{brief}\n\n初版大纲：\n{json.dumps(plan, ensure_ascii=False)}\n\n审计专家建议：\n{feedback}\n\n请根据建议优化大纲，输出最终版 JSON。"}
                ]
                raw = _llm_call(messages, keys, max_tokens=2048, temperature=0.4, model_pref=outline_pref)
                plan = _parse_json(raw)
                logger.info("OutlineAgent: Plan refined based on critic feedback")
                
    except Exception as e:
        logger.error("OutlineAgent failed: %s — falling back to simple plan", e)
        plan = _fallback_plan(brief, slide_count)

    # ... (clamp and re-index logic remains same) ...
    if len(plan) > slide_count:
        plan = plan[:slide_count-1] + [plan[-1]]
    while len(plan) < slide_count:
        n = len(plan) + 1
        plan.insert(-1, {"index": n, "slide_type": "content",
                          "title": f"第 {n} 章", "key_points": [],
                          "needs_image": False, "image_concept": None})
    for i, s in enumerate(plan, 1):
        s["index"] = i

    # Stage 2: SlideAgent (parallel, max 4 workers)
    logger.info("=== Stage 2: SlideAgent (parallel, %d slides, %s) ===", len(plan), slide_pref)
    slide_contents: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {
            ex.submit(slide_agent, spec, brief, doc_text, keys, model_pref=slide_pref): spec["index"]
            for spec in plan
        }
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                slide_contents[idx] = fut.result()
            except Exception as e:
                logger.warning("SlideAgent slide %d failed: %s", idx, e)
                spec = next(s for s in plan if s["index"] == idx)
                slide_contents[idx] = {
                    "title": spec.get("title", f"第{idx}页"),
                    "subtitle": "", "bullets": spec.get("key_points", []),
                    "body": "", "stat_numbers": [], "quote_text": ""
                }

    # Stage 3: DesignAgent (rule-based, instantaneous)
    logger.info("=== Stage 3: DesignAgent ===")
    blocks = []
    for spec in plan:
        idx = spec["index"]
        block = design_agent(spec, slide_contents[idx], idx, keys=keys, model_pref=outline_pref)
        # If premium or kimi, upgrade visual tier to leverage our competitive edge
        if model_tier in ("premium", "kimi") and "visual" in block:
            block["visual"]["tier"] = "premium"
            block["visual"]["model_pref"] = "gpt5" # GPT-Imagine2
        blocks.append(block)

    content_doc = {
        "doc_type": doc_type,
        "meta": {"title": brief[:60], "lang": lang,
                 "source_doc": bool(doc_text), "agent_pipeline": "v1",
                 "model_tier": model_tier},
        "brand": {},
        "blocks": blocks,
    }
    logger.info("=== Pipeline complete: %d blocks ===", len(blocks))
    return content_doc


def _fallback_plan(brief: str, n: int) -> list[dict]:
    """Simple rule-based plan when OutlineAgent LLM call fails."""
    labels = (["封面"] +
              [f"核心内容 {i}" for i in range(1, max(1, n-2))] +
              ["总结"])
    types  = (["cover"] +
              ["content"] * max(1, n-2) +
              ["closing"])
    return [{"index": i+1, "slide_type": types[min(i, len(types)-1)],
             "title": labels[min(i, len(labels)-1)],
             "key_points": [], "needs_image": i == 0, "image_concept": brief[:40]}
            for i in range(n)]
