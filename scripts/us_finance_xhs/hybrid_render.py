#!/usr/bin/env python3
"""Hybrid XHS card: 智谱插画底 → Seedream4.5 提质 → 程序叠字（替代 gpt-image-2）。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from render_tier import NO_TEXT_SUFFIX, render_cogview, render_seedream  # noqa: E402

_SIZE = "1024x1536"
_W, _H = 1024, 1536
_SEEDREAM_45 = "doubao-seedream-4-5-251128"


def _font(size: int, bold: bool = False):
    from PIL import ImageFont

    candidates = []
    if bold:
        candidates += [
            "C:/Windows/Fonts/msyhbd.ttc",
            "C:/Windows/Fonts/NotoSansSC-Bold.otf",
        ]
    else:
        candidates += [
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/NotoSansSC-Regular.otf",
            "/System/Library/Fonts/PingFang.ttc",
        ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _illustration_prompt(page: int, card: dict[str, Any]) -> str:
    title = card.get("title") or ""
    if page == 1:
        return (
            "小红书竖版3比4轻松生活化理财手账背景，奶油米色纸纹、手绘贴纸装饰、"
            "粉蓝绿柔和配色、圆角便签留白、可爱小图标点缀，闺蜜聊天笔记感。"
            f"主题氛围：{title}，美国市场一周概览。"
            "大面积中部留白给文字排版，不要深蓝金商务风。"
        )
    return (
        "小红书竖版3比4轻松生活化理财手账背景，奶油米色纸纹、柔和曲线装饰、"
        "右侧留白可放折线图，左侧留白可放要点列表，可爱贴纸风。"
        f"主题氛围：{title}，国债与dai款利率走势。"
        "不要Points Closing APR 教学板块，不要商务深蓝金。"
    )


def _seedream_enhance_prompt(page: int) -> str:
    if page == 1:
        return (
            "在参考图基础上增强生活化手账质感，奶油纸纹更清晰，贴纸更可爱，"
            "色彩更柔和统一，保持无文字无数字，留白给后期排版。"
        )
    return (
        "增强手账质感与柔和配色，保持无文字，右侧适合放简约折线图区域，"
        "左侧适合放短句列表，不要商务模板感。"
    )


def render_illustration_base(
    page: int,
    card: dict[str, Any],
    work_dir: Path,
    *,
    use_seedream: bool = True,
) -> tuple[Path, list[dict[str, Any]]]:
    work_dir.mkdir(parents=True, exist_ok=True)
    log: list[dict[str, Any]] = []
    cog_out = work_dir / f"page{page:02d}_cogview.png"
    meta_c = render_cogview(
        _illustration_prompt(page, card),
        _SIZE,
        cog_out,
        suffix=NO_TEXT_SUFFIX,
    )
    meta_c["pass"] = "1_cogview"
    log.append(meta_c)
    base = cog_out

    if use_seedream:
        from PIL import Image

        sd_out = work_dir / f"page{page:02d}_seedream45.png"
        try:
            meta_s = render_seedream(
                _seedream_enhance_prompt(page),
                _SIZE,
                sd_out,
                model=_SEEDREAM_45,
                suffix=NO_TEXT_SUFFIX,
            )
            meta_s["pass"] = "1b_seedream45"
            log.append(meta_s)
            if sd_out.exists():
                bg = Image.open(cog_out).convert("RGBA").resize((_W, _H))
                top = Image.open(sd_out).convert("RGBA").resize((_W, _H))
                blended = Image.blend(bg, top, alpha=0.38)
                blend_out = work_dir / f"page{page:02d}_blend.png"
                blended.convert("RGB").save(blend_out)
                base = blend_out
                log.append({"pass": "1c_blend", "alpha": 0.38, "path": str(blend_out)})
        except Exception as exc:
            log.append({"pass": "1b_seedream45", "error": str(exc)[:300]})

    return base, log


def _rounded_rect(draw, xy, radius: int, fill, outline=None, width: int = 1):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _draw_pill(draw, pos: tuple[int, int], text: str, font, *, fill, text_fill=(40, 40, 40)):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x0, y0 = pos
    pad_x, pad_y = 28, 16
    box = (x0, y0, x0 + tw + pad_x * 2, y0 + th + pad_y * 2)
    _rounded_rect(draw, box, 28, fill=fill)
    draw.text((box[0] + pad_x, box[1] + pad_y - 2), text, font=font, fill=text_fill)


def _overlay_card1(base: Path, card: dict[str, Any], out: Path, *, tnx: float, gold: float) -> None:
    from PIL import Image, ImageDraw

    img = Image.open(base).convert("RGBA")
    draw = ImageDraw.Draw(img)
    title_f = _font(52, bold=True)
    sub_f = _font(30)
    bullet_f = _font(34)
    small_f = _font(24)
    accent = (255, 120, 140)
    blue = (120, 175, 230)
    green = (130, 200, 150)

    _draw_pill(draw, (60, 70), card.get("title") or "这周市场咋样", title_f, fill=accent, text_fill=(255, 255, 255))
    _draw_pill(draw, (60, 175), card.get("image_caption") or "一周扫一眼就够", sub_f, fill=blue, text_fill=(40, 60, 90))

    bullets = card.get("bullets") or []
    y = 300
    colors = [green, blue, accent]
    for i, b in enumerate(bullets[:3]):
        num = str(i + 1)
        _rounded_rect(draw, (70, y, 120, y + 50), 25, fill=colors[i % 3])
        draw.text((88, y + 8), num, font=bullet_f, fill=(255, 255, 255))
        _rounded_rect(draw, (135, y, 920, y + 50), 22, fill=(255, 255, 255, 210))
        draw.text((165, y + 6), b.lstrip("123 ").strip(), font=bullet_f, fill=(50, 50, 50))
        y += 78

    # mini trend line
    chart_y0, chart_y1 = 1180, 1380
    draw.rectangle((80, chart_y0, 560, chart_y1), fill=(255, 255, 255, 180), outline=(220, 210, 200))
    pts = [(110, 1340), (180, 1310), (250, 1325), (320, 1280), (400, 1295), (480, 1260), (530, 1270)]
    for a, b in zip(pts, pts[1:]):
        draw.line([a, b], fill=(90, 140, 220), width=4)
    for p in pts:
        draw.ellipse((p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5), fill=(255, 160, 90))

    draw.text((620, 1320), "截至2026.06", font=small_f, fill=(100, 100, 100))
    img.convert("RGB").save(out)


def _overlay_card2(base: Path, card: dict[str, Any], out: Path, *, tnx: float, mort: float) -> None:
    from PIL import Image, ImageDraw

    img = Image.open(base).convert("RGBA")
    draw = ImageDraw.Draw(img)
    title_f = _font(48, bold=True)
    bullet_f = _font(32)
    small_f = _font(22)
    cta_f = _font(30, bold=True)
    accent = (255, 120, 140)
    blue = (120, 175, 230)
    green = (130, 200, 150)

    _draw_pill(draw, (60, 65), card.get("title") or "利率这事别硬扛", title_f, fill=accent, text_fill=(255, 255, 255))

    bullets = card.get("bullets") or []
    y = 260
    for i, b in enumerate(bullets[:2]):
        num = str(i + 1)
        _rounded_rect(draw, (60, y, 110, y + 46), 23, fill=green if i == 0 else blue)
        draw.text((78, y + 5), num, font=bullet_f, fill=(255, 255, 255))
        _rounded_rect(draw, (125, y, 500, y + 90), 20, fill=(255, 255, 255, 220))
        text = b.split(" ", 1)[-1] if " " in b else b
        draw.text((145, y + 10), text[:18], font=bullet_f, fill=(45, 45, 45))
        if len(text) > 18:
            draw.text((145, y + 48), text[18:36], font=small_f, fill=(70, 70, 70))
        y += 115

    # chart panel
    draw.rectangle((530, 240, 960, 720), fill=(255, 255, 255, 200), outline=(210, 200, 190))
    draw.text((550, 260), "10年美债 / 30年固定dai款", font=small_f, fill=(80, 80, 80))
    draw.text((550, 295), f"10年约{tnx:.1f}%  ·  30年约{mort:.1f}%", font=bullet_f, fill=(50, 90, 150))
    pts_a = [(560, 650), (640, 600), (720, 580), (800, 520), (880, 500), (940, 480)]
    pts_b = [(560, 700), (640, 680), (720, 650), (800, 620), (880, 590), (940, 570)]
    for pts, col in ((pts_a, (80, 120, 200)), (pts_b, (240, 170, 90))):
        for a, b in zip(pts, pts[1:]):
            draw.line([a, b], fill=col, width=4)
    draw.text((550, 660), "2022–2026", font=small_f, fill=(120, 120, 120))

    _draw_pill(draw, (120, 1320), "案Zi交给她，锁利率更踏实", cta_f, fill=accent, text_fill=(255, 255, 255))
    draw.text((720, 1345), "截至2026.06", font=small_f, fill=(110, 110, 110))
    img.convert("RGB").save(out)


def render_card_hybrid(
    page: int,
    card: dict[str, Any],
    out_path: Path,
    work_dir: Path,
    *,
    quotes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    quotes = quotes or {}
    tnx = float((quotes.get("^TNX") or {}).get("value_pct") or 4.54)
    mort = float((quotes.get("MORTGAGE30US") or {}).get("value_pct") or 6.48)
    gold = float((quotes.get("GC=F") or {}).get("price_usd") or 4330)

    base, log = render_illustration_base(page, card, work_dir)
    text_out = work_dir / f"page{page:02d}_text.png"
    if page == 1:
        _overlay_card1(base, card, text_out, tnx=tnx, gold=gold)
    else:
        _overlay_card2(base, card, text_out, tnx=tnx, mort=mort)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    from shutil import copy2

    copy2(text_out, out_path)
    return {
        "page": page,
        "backend": "hybrid_cogview_seedream45_overlay",
        "passes": log + [{"pass": "2_text_overlay", "path": str(text_out)}],
        "path": str(out_path),
    }


def render_all_cards(
    social: dict[str, Any],
    out_dir: Path,
    *,
    quotes: dict[str, Any] | None = None,
) -> tuple[list[Path], list[dict[str, Any]]]:
    xhs = social.get("xiaohongshu") or social
    cards = xhs.get("cards") or []
    work = out_dir / "_hybrid_work"
    paths: list[Path] = []
    log: list[dict[str, Any]] = []
    for card in cards[:2]:
        page = int(card.get("page") or len(paths) + 1)
        out = out_dir / f"card_{page:02d}.png"
        meta = render_card_hybrid(page, card, out, work, quotes=quotes)
        log.append(meta)
        if out.exists():
            paths.append(out)
    return paths, log
