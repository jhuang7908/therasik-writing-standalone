"""
Therasik assistant (DeepSeek-chat only). Server-side; no client model override.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

_KB_CACHE: Dict[str, Any] = {}


def _format_kb_json(data: Dict[str, Any], *, locale: str, header: str) -> str:
    lines = [
        f"\n\n{header}:",
        f"Version: {data.get('version', 'unknown')}",
    ]
    purpose = data.get("purpose")
    if purpose:
        lines.append(f"Purpose: {purpose}")
    policies = data.get("output_policy") or data.get("display_policy") or []
    if policies:
        lines.append("\n[Policy]")
        for policy in policies:
            lines.append(f"- {policy}")
    is_zh = locale.startswith("zh")
    nih = data.get("nih_ncbi_data_access")
    if isinstance(nih, dict):
        lines.append("\n[NIH / NCBI data access]")
        summary = nih.get("summary_zh") if is_zh else nih.get("summary_en")
        if summary:
            lines.append(f"- {summary}")
        for tier in nih.get("tiers") or []:
            lines.append(
                f"- {tier.get('id')}: {tier.get('how')} "
                f"(assistant: {tier.get('assistant_behavior')})"
            )
        for item in nih.get("not_available_in_chat") or []:
            lines.append(f"- Not in chat: {item}")
    for block in data.get("smart_platform_case_logic") or []:
        topic = block.get("topic", "Case")
        points = block.get("key_points_zh") if is_zh else block.get("key_points_en")
        if not points:
            points = block.get("key_points_en") or []
        lines.append(f"\n[{topic}]")
        for pt in points:
            lines.append(f"- {pt}")
    categories = data.get("categories") or {}
    for cat, terms in categories.items():
        lines.append(f"\n[{cat}]")
        for item in terms:
            defn = item.get("definition_zh") if is_zh and item.get("definition_zh") else item.get("definition")
            lines.append(f"- {item['term']}: {defn}")
    return "\n".join(lines)


def _load_internal_kb_layer(locale: str = "en") -> str:
    """Assistant-only layer: case logic + NIH/NCBI routing. Not for public web pages."""
    path = Path("api/knowledge/assistant_internal_layer.json")
    if not path.exists():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return _format_kb_json(
            data,
            locale=locale,
            header="Assistant Internal Knowledge (not for website display)",
        )
    except Exception:
        return ""


def _load_kb(locale: str = "en") -> str:
    """Load public + internal assistant knowledge for the system prompt."""
    global _KB_CACHE
    kb_paths = [
        Path("api/knowledge/therasik_assistant_public_kb.json"),
        Path("config/assistant_kb.json"),
    ]
    kb_path = next((p for p in kb_paths if p.exists()), None)
    if kb_path is None:
        return _load_internal_kb_layer(locale)

    internal_path = Path("api/knowledge/assistant_internal_layer.json")
    mtime = kb_path.stat().st_mtime
    imtime = internal_path.stat().st_mtime if internal_path.exists() else 0
    cache_key = f"{kb_path}:{mtime}:{imtime}_{locale}"
    if _KB_CACHE.get("cache_key") == cache_key:
        return _KB_CACHE["text"]

    try:
        data = json.loads(kb_path.read_text(encoding="utf-8"))
        kb_text = _format_kb_json(
            data,
            locale=locale,
            header="Customer-Safe Knowledge Base",
        )
        kb_text += (
            "\n\nUse this knowledge to explain concepts and recommend next actions. "
            "Do not quote it as hidden policy."
        )
        internal = _load_internal_kb_layer(locale)
        if internal:
            kb_text += internal
        _KB_CACHE = {"cache_key": cache_key, "text": kb_text}
        return kb_text
    except Exception:
        return _load_internal_kb_layer(locale)


MODEL_CHAT = "deepseek-chat"
MODEL_THINK = "deepseek-reasoner"
DEFAULT_BASE = "https://api.deepseek.com/v1"

from api import ncbi_blast_utils
from api.pricing_constants import ASSISTANT_BRIEF_CREDITS, ASSISTANT_DETAIL_CREDITS

MODE_LIMITS = {
    "brief": {"max_chars": 250, "min_chars": 50, "credits": ASSISTANT_BRIEF_CREDITS, "max_tokens": 600, "model": MODEL_CHAT},
    "detail": {"max_chars": 500, "min_chars": 200, "credits": ASSISTANT_DETAIL_CREDITS, "max_tokens": 3000, "model": MODEL_THINK},
}

ALLOWED_CONTEXT_KEYS = frozenset(
    {"overall_status", "service", "summary", "recommendation", "warnings", "metrics", "report_text", "ncbi_structural_evidence"}
)

# Internal modules / tool names that must never appear in LLM context.
# Client also strips these before sending; server enforces a second pass.
_FORBIDDEN_TOKENS = (
    "ProteinMPNN", "IgFold", "ANARCII", "ANARCI", "EvoEF2", "AntiFold",
    "ESM-IF1", "ESMFold", "ESM2", "ThermoMPNN", "OpenMM", "PDBFixer",
    "HADDOCK", "HADDOCK3", "AbLang", "ImmuneBuilder", "ABodyBuilder2",
    "ABodyBuilder", "NanoBodyBuilder2", "NanoBodyBuilder", "PRODIGY",
    "LinearDesign", "LinearFold", "EpiScan", "NetMHCpan", "AutoDock",
    "AlphaFold", "RoseTTAFold", "AbNatiV", "abenginecore",
    "vh_vl_humanization_v", "vhh_humanization", "tools_registry",
    "config/abenginecore", "abenginecore_registry",
    "DeepSeek", "深度求索", "英矽生信",
    "AbRef-1142", "AbRef", "1142", "1,142", "1143", "1,143",
    "germline selection", "germline ranking", "back-mutation",
    "framework selection logic", "decision tree", "private database",
    "胚系选择", "胚系排序", "回复突变", "回突变", "决策树",
    "数据库规模", "内部阈值", "私有数据库", "工具链",
)


def _redact_internals(text: str, replacement: str = "[internal]") -> str:
    """Remove internal tool/algorithm names from text before sending to the LLM."""
    if not text:
        return text
    out = text
    for token in _FORBIDDEN_TOKENS:
        # case-insensitive replace, keep readable placeholder
        try:
            import re as _re
            out = _re.sub(_re.escape(token), replacement, out, flags=_re.IGNORECASE)
        except Exception:
            pass
    return out


# Residue-level prescriptions only — must not match broad strategic Q&A
# (e.g. "recommend humanization workflow" or "graft CDRs onto frameworks").
_SEQUENCE_PRESCRIPTION_RE = re.compile(
    r"(?i)"
    r"(?:recommend|suggest|propose|try|consider|advise).{0,40}"
    r"(?:mutat|substitut|replac|modif|graft|back[- ]?mutat).{0,32}"
    r"(?:at|position|residue|site|\bcdr\b|framework|\bfr\b|\d+\s*(?:位|号))"
    r"|(?:mutat(?:e|ion|ing)|substitut\w+|replac\w+|redesign\w+).{0,48}"
    r"(?:position|residue|site|\bcdr\b|framework|sequence|loop|\bat\s+\d|\d+\s*(?:位|号))"
    r"|(?:graft\w+|back[- ]?mutat\w+).{0,32}"
    r"(?:at|position|residue|site|\bat\s+\d|\d+\s*(?:位|号))"
    r"|(?:建议|推荐|可考虑|尝试|宜|应).{0,32}"
    r"(?:突变|替换|graft|回复突变|回突变).{0,24}"
    r"(?:位点|残基|\bCDR\b|框架|序列|\d+号)"
    r"|(?:建议|推荐).{0,24}(?:位点|残基|\d+号).{0,20}(?:突变|替换|改为|换成)"
    r"|(?:突变|替换|改为|换成|修改为|graft).{0,28}"
    r"(?:序列|位点|残基|\bCDR\b|框架|FR|环)"
    r"|[A-Z]\d+\s*[→>-]\s*[A-Z]"
)
_POINT_MUTATION_TOKEN_RE = re.compile(r"\b[A-Z][A-Z]?\d+[A-Z]\b")
_AA_ARROW_RE = re.compile(r"\b[A-Z]\s*[→>-]\s*[A-Z]\b")


def _redirect_interpretation_only(assistant_name: str) -> str:
    if assistant_name.lower() == "insynbio":
        return (
            "This assistant only answers questions and interprets completed computational "
            "reports. It cannot prescribe any mutation, substitution, CDR/framework change, "
            "graft, or sequence redesign for your molecule. Run the appropriate platform "
            "workflow (humanization, CMC evaluation, Virtual Affinity Maturation, etc.) for "
            "in silico sequence-level outputs, then validate in the lab."
        )
    return (
        "本助手仅用于回答和解释问题，解读已有计算报告中的结果。"
        "不能对您的序列给出任何突变、替换、graft 或序列改造建议。"
        "如需序列级方案，请使用平台对应正式计算流程（如人源化、CMC 评估、虚拟亲和力成熟等），"
        "并在湿实验中验证。"
    )


def _enforce_no_speculative_design(
    answer: str,
    report_context: Optional[Dict[str, Any]],
    assistant_name: str = "Therasik",
) -> str:
    """Block chat-only residue/sequence prescriptions; allow strategic KB Q&A."""
    text = (answer or "").strip()
    if not text:
        return text
    ctx = report_context or {}
    ctx_blob = json.dumps(ctx, ensure_ascii=False)
    has_report = bool(ctx_blob.strip() and ctx_blob.strip() not in ("{}", "null"))
    mut_tokens = _POINT_MUTATION_TOKEN_RE.findall(text)
    aa_arrows = _AA_ARROW_RE.findall(text)
    unsupported = [t for t in mut_tokens if t not in ctx_blob]
    unsupported += [a for a in aa_arrows if a not in ctx_blob]

    if unsupported:
        return _redirect_interpretation_only(assistant_name)

    if mut_tokens and all(t in ctx_blob for t in mut_tokens):
        stripped = re.sub(r"\b[A-Z][A-Z]?\d+[A-Z]\b", "", text)
        if not _SEQUENCE_PRESCRIPTION_RE.search(stripped):
            return text

    if _SEQUENCE_PRESCRIPTION_RE.search(text):
        if not has_report:
            return _redirect_interpretation_only(assistant_name)
        return _redirect_interpretation_only(assistant_name)

    return text


def _sanitize_public_answer(text: str, assistant_name: str = "Therasik") -> str:
    """Final guardrail for customer-visible assistant replies."""
    t = _mask_identity(text or "", assistant_name=assistant_name)
    is_english_brand = assistant_name.lower() == "insynbio"
    internal_rule_msg = (
        "This judgment comes from the platform's internal engineering rules."
        if is_english_brand
        else "该判断来自平台内部工程规则。"
    )
    reasoning_msg = "engineering rationale" if is_english_brand else "工程判断过程"
    internal_method_msg = "platform internal method" if is_english_brand else "平台内部方法"
    leak_patterns = [
        (r"(?i)(because|原因是).{0,80}(rule|threshold|decision tree|germline|back-mutation)", internal_rule_msg),
        (r"(因为|原因是).{0,80}(阈值|决策树|胚系|回复突变|回突变)", internal_rule_msg),
        (r"(?i)step[- ]by[- ]step reasoning|chain of thought|hidden reasoning", reasoning_msg),
        (r"逐步推理|思维链|隐藏推理|内心推理", reasoning_msg),
    ]
    for pattern, repl in leak_patterns:
        t = re.sub(pattern, repl, t)
    t = _redact_internals(t, replacement=internal_method_msg)
    t = re.sub(r"(?:Therasik\s*)?平台内部方法(?:\s*平台内部方法)+", "平台内部方法", t)
    t = re.sub(r"(?:InSynBio\s*)?platform internal method(?:\s*platform internal method)+", "platform internal method", t, flags=re.IGNORECASE)
    return t.strip()

_RATE: Dict[int, List[float]] = {}
_RATE_WINDOW_SEC = 60.0
_RATE_MAX_PER_WINDOW = 30


def _api_key() -> str:
    key = (os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("deepseek_not_configured")
    return key


def _api_base() -> str:
    return (os.environ.get("DEEPSEEK_API_BASE") or DEFAULT_BASE).rstrip("/")


def _model_name() -> str:
    raw = (os.environ.get("DEEPSEEK_MODEL") or MODEL_CHAT).strip().lower()
    if raw != MODEL_CHAT:
        return MODEL_CHAT
    return MODEL_CHAT


def sanitize_report_context(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not raw or not isinstance(raw, dict):
        return {}
    out: Dict[str, Any] = {}
    for k, v in raw.items():
        if k not in ALLOWED_CONTEXT_KEYS:
            continue
        if k == "warnings" and isinstance(v, list):
            out[k] = [_redact_internals(str(x)[:200]) for x in v[:8]]
        elif k == "metrics" and isinstance(v, list):
            slim = []
            for m in v[:12]:
                if isinstance(m, dict):
                    slim.append(
                        {
                            "label": _redact_internals(str(m.get("label", ""))[:80]),
                            "value": _redact_internals(str(m.get("value", ""))[:120]),
                        }
                    )
            out[k] = slim
        elif k == "report_text":
            # Full attached report excerpt (post-redaction). Cap to ~6000 chars
            # so we keep DeepSeek input under ~2k tokens for cost safety.
            out[k] = _redact_internals(str(v)[:6000])
        else:
            out[k] = _redact_internals(str(v)[:1200])
    blob = json.dumps(out, ensure_ascii=False)
    if len(blob) > 8000:
        # Hard cap on the whole context to control cost.
        rt = out.get("report_text") or ""
        out = {
            "overall_status": str(out.get("overall_status", ""))[:80],
            "summary": str(out.get("summary", ""))[:1200],
            "report_text": rt[:4500],
        }
    return out


def check_rate_limit(uid: int) -> bool:
    now = time.time()
    bucket = _RATE.setdefault(uid, [])
    cutoff = now - _RATE_WINDOW_SEC
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= _RATE_MAX_PER_WINDOW:
        return False
    bucket.append(now)
    return True


def truncate_answer(text: str, max_chars: int) -> str:
    t = (text or "").strip()
    if len(t) <= max_chars:
        return t
    cut = t[:max_chars]
    # Prefer breaking at sentence / clause boundary
    for sep in ("。", "！", "？", ". ", "；", "; ", ", ", "，"):
        idx = cut.rfind(sep)
        if idx >= max(20, max_chars // 3):
            return cut[: idx + len(sep)].strip()
    return cut.rstrip() + "…"


def build_messages(
    user_message: str,
    mode: str,
    report_context: Dict[str, Any],
    locale: str = "zh",
    assistant_name: str = "Therasik",
) -> List[Dict[str, str]]:
    limits = MODE_LIMITS[mode]
    max_chars = limits["max_chars"]
    ctx_block = ""
    if report_context:
        ctx_block = (
            "\n\nReport context (facts only; do not invent beyond this JSON):\n"
            + json.dumps(report_context, ensure_ascii=False)
        )
    # InSynBio defaults to English; Therasik defaults to Chinese
    if assistant_name.lower() == "insynbio":
        lang_hint = "Reply in English unless the user wrote in Chinese."
    else:
        lang_hint = (
            "Reply in Chinese unless the user wrote in English."
            if locale.startswith("zh")
            else "Reply in the same language as the user."
        )

    kb_block = _load_kb(locale=locale)

    if mode == "detail":
        mode_hint = "【深度解读模式】：请根据报告上下文提供结构化解释，涵盖指标含义、风险评估及对应的科学验证建议。保持专业且冷静的语气。"
    else:
        mode_hint = "【简快解读模式】：请直接给出核心解释或结论，保持回答精炼。"

    min_chars = limits.get("min_chars", 0)

    if assistant_name.lower() == "insynbio":
        scope_definition = (
            "5. [Authorized Scope]: You may answer without an attached report for educational/strategic "
            "questions in these domains: Smart CAR-T/CAR-M architecture; Smart ADC (target, linker, "
            "payload, DAR framing); bispecific/multispecific format strategy; CMC/developability risk "
            "categories; antibody humanization principles; nanobody/VHH concepts. "
            "For each answer: give conclusion, risk category, concept-level rationale, the matching "
            "console workflow name (e.g., cart-invivo-blood, VH/VL Humanization, VHH Humanization, "
            "IgG/VHH CMC Snapshot, Bispecific Analyzer), and wet-lab validation route. "
            "(a) Explain antibody engineering and CMC terminology; "
            "(b) Interpret metrics, warnings, and conclusions in attached Report context when present; "
            "(c) Route residue-level or molecule-specific sequence design to formal platform workflows. "
            "Do NOT refuse strategic CAR/ADC/bispecific/CMC/humanization/VHH questions solely because "
            "no report is attached. "
            "For business inquiries, suggest contact@insynbio.com.\n"
        )
    else:
        scope_definition = (
            "5. 【授权功能范围】：以下领域可在无报告时作知识性/策略性解答："
            "Smart CAR-T/CAR-M 架构；Smart ADC（靶点、连接子、载荷、DAR 框架）；"
            "双特异/多特异格式策略；CMC/可开发性风险类别；抗体人源化原则；纳米抗体/VHH 概念。"
            "回答须包含：结论、风险类别、概念级解释、对应 Console 流程名"
            "（如 cart-invivo-blood、VH/VL 人源化、VHH 人源化、IgG/VHH CMC Snapshot、双特异分析器）"
            "及湿实验验证路线。\n"
            "   (a) 解释抗体工程与 CMC 术语；\n"
            "   (b) 有 Report context 时解读其中的指标、预警和结论；\n"
            "   (c) 残基级或分子特异序列设计须引导至平台正式计算模块。\n"
            "不要仅因未附加报告就拒绝 CAR/ADC/双特异/CMC/人源化/VHH 的策略性问题。\n"
            "商业咨询请联系 contact@therasik.com。\n"
        )

    system = (
        f"【身份设定】：你是 {assistant_name} 专业药物设计解读助手。\n\n"
        f"{mode_hint}\n\n"
        "你的任务是基于报告上下文和客户安全知识库提供专业解读。你的回复总字符数（含标点）必须在 {min_chars} 到 {max_chars} 字之间。"
        + (" 请提供详尽的分析，确保字数不少于 200 字。" if mode == "detail" else " 必须简洁有力，控制在 50-250 字。")
        + "\n【工作准则】：\n"
        f"1. 身份：如被问及身份，回答“我是 {assistant_name} 药物设计解读助手”。不要讨论底层模型。\n"
        "2. 事实依据：有 Report context 时以其字段为主；无报告时可用知识库回答 Smart CAR-T、Smart ADC、"
        "双特异、CMC/可开发性、人源化、纳米抗体/VHH 等概念与策略问题。\n"
        "3. 输出形态：专业解释、风险类别、Console 正式流程名称、科学验证路线；"
        "禁止无报告依据的残基级突变或序列处方。\n"
        + scope_definition
        + "6. 语气：专业、冷静、直接，不使用社交辞令。\n"
        "7. 结尾：直接结束回答，免责声明由平台统一显示。\n"
        f"8. 语言：{lang_hint}"
        + kb_block
        + ctx_block
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message.strip()[:500]},
    ]


def _mask_identity(text: str, assistant_name: str = "Therasik") -> str:
    if not text:
        return text
    import re
    # Case-insensitive replacements for all known identity markers
    t = re.sub(r'(?i)deepseek', assistant_name, text)
    t = re.sub(r'深度求索', assistant_name, t)
    if assistant_name.lower() == "insynbio":
        t = re.sub(r'(?i)therasik', assistant_name, t)
    else:
        t = re.sub(r'(?i)\binsynbio\b', assistant_name, t)
        t = re.sub(r'英矽生信', assistant_name, t)
    
    t = re.sub(r'(?i)openai', assistant_name, t)
    t = re.sub(r'(?i)\banthropic\b', assistant_name, t)
    t = re.sub(r'(?i)\bclaude\b', assistant_name, t)
    t = re.sub(r'(?i)\bchatgpt\b', assistant_name, t)
    t = re.sub(r'(?i)gpt-4', f'{assistant_name}-Engine', t)
    t = re.sub(r'(?i)gpt-3\.5', f'{assistant_name}-Engine', t)
    t = re.sub(r'(?i)large language model', 'Expert System', t)
    t = re.sub(r'(?i)AI model', 'Expert System', t)
    t = re.sub(r'语言模型', '专家系统', t)
    t = re.sub(r'人工智能', '专家系统', t)
    return t


def call_deepseek_chat(messages: List[Dict[str, str]], max_tokens: int, model: str = MODEL_CHAT, assistant_name: str = "Therasik") -> Tuple[str, Dict[str, Any]]:
    url = f"{_api_base()}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3 if model == MODEL_CHAT else 1.0, # Reasoner usually prefers 1.0 or default
    }
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, json=payload, headers=headers)
    if resp.status_code >= 400:
        raise RuntimeError(f"deepseek_http_{resp.status_code}")
    data = resp.json()
    choice = (data.get("choices") or [{}])[0]
    content = ((choice.get("message") or {}).get("content") or "").strip()
    content = _sanitize_public_answer(content, assistant_name=assistant_name)
    usage = data.get("usage") or {}
    return content, usage


def run_assistant_chat(
    *,
    user_message: str,
    mode: str,
    report_context: Optional[Dict[str, Any]],
    locale: str = "zh",
    assistant_name: str = "Therasik",
) -> Dict[str, Any]:
    if mode not in MODE_LIMITS:
        raise ValueError("invalid_mode")
    limits = MODE_LIMITS[mode]
    ctx = sanitize_report_context(report_context)
    
    # Accuracy Boost: In 'Think' mode, perform a local NCBI BLAST search if a sequence is available
    ncbi_facts = ""
    if mode == "detail":
        # Extract sequence from message or context
        seq_to_search = ""
        # 1. Try to find a long sequence in the user message
        seq_match = re.search(r'[A-Z]{30,}', user_message.upper())
        if seq_match:
            seq_to_search = seq_match.group(0)
        # 2. If not in message, check report context (e.g., from a humanization run)
        elif report_context and "summary" in report_context:
            # Heuristic: look for sequence-like strings in summary
            sm = re.search(r'[A-Z]{30,}', str(report_context["summary"]).upper())
            if sm:
                seq_to_search = sm.group(0)
        
        if seq_to_search:
            hits = ncbi_blast_utils.search_pdb_seqres(seq_to_search)
            ncbi_facts = ncbi_blast_utils.format_hits_for_assistant(hits)
            if ncbi_facts:
                # Add to context so build_messages can include it
                ctx["ncbi_structural_evidence"] = ncbi_facts

    messages = build_messages(user_message, mode, ctx, locale=locale, assistant_name=assistant_name)
    raw, usage = call_deepseek_chat(messages, limits["max_tokens"], model=limits["model"], assistant_name=assistant_name)
    answer = truncate_answer(_sanitize_public_answer(raw, assistant_name=assistant_name), limits["max_chars"])
    answer = _enforce_no_speculative_design(answer, ctx, assistant_name=assistant_name)
    answer = truncate_answer(answer, limits["max_chars"])
    return {
        "answer": answer,
        "char_count": len(answer),
        "max_chars": limits["max_chars"],
        "credits": limits["credits"],
        "mode": mode,
        "model": limits["model"],
        "usage": usage,
    }
