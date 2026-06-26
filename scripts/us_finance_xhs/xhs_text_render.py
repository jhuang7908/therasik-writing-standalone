#!/usr/bin/env python3
"""XHS 图文混编卡片渲染链：gpt-image-2(high) → Nano Banana Pro 2K → 智谱 CogView。

图内中文文字由 gpt-image-2 优先渲染（quality=high，保真度最好）；失败时按优先级
回退到 Nano Banana Pro（Gemini 3 Pro Image）、最后 CogView。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import render_tier

_PKG = Path(__file__).resolve().parent
_XHS_SIZE = "1024x1536"
_GPT_MODEL = "gpt-image-2"
# Nano Banana Pro 2K (Gemini 3 Pro Image preview)
_NANO_BANANA_PRO_2K = "gemini-3-pro-image-preview"

_STYLE = (
    "小红书竖版3比4信息图，轻松活泼生活化手账风，奶油米色纸纹、手绘贴纸、粉蓝绿柔和配色。"
    "口语化中文排版，阿拉伯数字编号1/2/3。禁止出现「贷款」二字，涉及借款写「dai款」或「房dai」。"
    "不要深蓝金商务模板，不要Points Closing APR教学板块，不要借贷广告导流。"
)


def _load_layout_variant(variant_id: str | None) -> dict[str, str]:
    variants = json.loads((_PKG / "layout_variants.json").read_text(encoding="utf-8"))
    if variant_id:
        for v in variants:
            if v.get("id") == variant_id:
                return v
    return variants[0] if variants else {}


def _as_of_label() -> str:
    return datetime.now().strftime("%m/%d/%Y")


def _resolve_fallback_model() -> str:
    alias = (os.environ.get("FINANCE_XHS_IMAGE_FALLBACK") or "nano_banana_pro_2k").strip().lower()
    if alias in ("nano_banana_pro_2k", "nano-banana-pro-2k", "gemini-pro", "gemini"):
        return _NANO_BANANA_PRO_2K
    return alias if alias.startswith("gemini") else _NANO_BANANA_PRO_2K


def build_card_prompt(
    page: int,
    card: dict[str, Any],
    *,
    tnx: float | None = None,
    mort: float | None = None,
    layout_variant: dict[str, str] | None = None,
    loan_category: str = "residential",
    edition_theme: str = "event",
) -> str:
    raw_bullets = list(card.get("bullets") or [])
    hot = list(card.get("hot_takes") or [])
    body_snip = (card.get("body") or "")[:100]
    tnx = tnx if tnx is not None else 4.54
    layout = layout_variant or {}
    as_of = _as_of_label()
    layout_hint = layout.get("card1_hint") or layout.get("card2_hint") or ""
    layout_label = layout.get("label") or "手账风"
    mort = mort if mort is not None else 6.48

    if hot and len(hot) == len(raw_bullets):
        bullets_block = "\n".join(
            f"- 要点{i + 1}逐字照抄：{b}\n  对应「辣评」气泡内逐字照抄：{h}"
            for i, (b, h) in enumerate(zip(raw_bullets, hot))
        )
        hot_rule = "每条要点配一个「辣评」气泡，气泡内必须逐字填入上面对应的辣评短句，绝不可留空。"
    else:
        bullets_block = "\n".join(f"- {b}" for b in raw_bullets)
        hot_rule = "不要画任何「辣评」气泡或空白对话框，避免出现没有文字的空泡。"

    if page == 1:
        return (
            f"{_STYLE}\n"
            f"【图1·财经故事】版式：{layout_label}。{layout.get('card1_hint', layout_hint)}\n"
            f"大标题逐字照抄：{card.get('title')}\n"
            f"副标题逐字照抄：{card.get('image_caption')}\n"
            f"故事语气参考：{body_snip}\n"
            f"要点与辣评逐字照抄不可改字：\n{bullets_block}\n"
            f"{hot_rule}\n"
            f"底部小字逐字照抄：截至{as_of}。可加简约新闻/折线装饰。"
            "像闺蜜讲近一月财经故事。"
        )

    cat_note = "住宅房dai" if loan_category == "residential" else "商业房dai"
    return (
        f"{_STYLE}\n"
        f"【图2·dai款涨知识·{cat_note}】版式：{layout_label}。{layout.get('card2_hint', layout_hint)}\n"
        f"大标题逐字照抄：{card.get('title')}\n"
        f"知识讲解参考：{body_snip}\n"
        f"要点逐字照抄不可改字：\n{bullets_block}\n"
        f"{hot_rule}\n"
        f"可选右侧简约折线图：10年美债与30年固定dai款利率，标注10年约{tnx:.1f}%、30年约{mort:.1f}%。\n"
        f"底部小字逐字照抄：截至{as_of}。主菜是科普，不要借贷广告。"
    )


def _gpt_image_quality() -> str:
    q = (os.environ.get("FINANCE_XHS_IMAGE_QUALITY") or "high").strip().lower()
    return q if q in ("low", "medium", "high") else "high"


def _render_gpt(prompt: str, out_path: Path) -> dict[str, Any]:
    quality = _gpt_image_quality()
    result = render_tier.render_gpt_image(
        prompt, _XHS_SIZE, _GPT_MODEL, out_path, quality=quality
    )
    result["backend"] = "gpt-image-2"
    result["resolution_tier"] = f"gpt_image_{quality}"
    result["fallback_from"] = None
    return result


def _nano_resolution() -> str:
    # Nano Banana Pro tiers: 1K / 2K / 4K (no 3K). Default 2K.
    r = (os.environ.get("FINANCE_XHS_NANO_RESOLUTION") or "2K").strip().upper()
    return r if r in ("1K", "2K", "4K") else "2K"


def _render_nano(prompt: str, out_path: Path) -> dict[str, Any]:
    model = _resolve_fallback_model()
    res = _nano_resolution()
    result = render_tier.render_gemini_image(prompt, out_path, model=model, image_size=res)
    result["backend"] = "nano_banana_pro"
    result["model"] = model
    result["resolution_tier"] = f"nano_banana_pro_{res.lower()}"
    result["fallback_from"] = None
    return result


def _render_cogview(prompt: str, out_path: Path) -> dict[str, Any]:
    # 非空 suffix 以覆盖 render_tier 的默认 NO_TEXT_SUFFIX，允许图内中文文字
    result = render_tier.render_cogview(
        prompt, _XHS_SIZE, out_path, suffix="图中中文标题与数字需清晰可读、排版整齐"
    )
    result["backend"] = "cogview-4"
    result["resolution_tier"] = "cogview_text"
    result["fallback_from"] = None
    return result


def render_xhs_card(
    prompt: str,
    out_path: Path,
    *,
    force_backend: str | None = None,
) -> dict[str, Any]:
    """图文混编渲染：优先 gpt-image-2(high)，回退 Nano Banana Pro，最次 CogView。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    force = (force_backend or os.environ.get("FINANCE_XHS_FORCE_RENDERER") or "").strip().lower()

    if force in ("gemini", "gemini-pro", "gemini-3-pro-image-preview", "nano_banana_pro_2k", "nano-banana-pro-2k"):
        return _render_nano(prompt, out_path)
    if force in ("cogview", "cogview-4", "zhipu", "智谱"):
        return _render_cogview(prompt, out_path)
    if force == "gpt-image-2":
        return _render_gpt(prompt, out_path)
    if force not in ("", "auto"):
        raise ValueError(f"Unknown FINANCE_XHS_FORCE_RENDERER: {force}")

    chain = [
        ("gpt-image-2", _render_gpt),
        ("nano_banana_pro_2k", _render_nano),
        ("cogview-4", _render_cogview),
    ]
    errors: list[dict[str, str]] = []
    for name, fn in chain:
        try:
            result = fn(prompt, out_path)
            if errors:
                result["fallback_from"] = errors[-1]["backend"]
                result["fallback_chain"] = errors
            return result
        except Exception as exc:  # noqa: BLE001
            errors.append({"backend": name, "error": str(exc)[:300]})

    raise RuntimeError(f"All image backends failed: {errors}")


def _is_openai_quota_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(
        k in msg for k in ("insufficient", "quota", "billing", "rate limit", "exceeded", "hard limit")
    )
