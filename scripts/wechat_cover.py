#!/usr/bin/env python3
"""WeChat Official Account 封面图 — 群聊/订阅号外链预览用，正文内不显示。

后台发布时：上传 cover 图 → 取消勾选「封面显示在正文中」。
标准比例 2.35:1，建议 900×383 px。gpt-image-2 背景 + PIL 文字 + 图内 logo 安全区。
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Callable

COVER_SIZE = (900, 383)
COVER_RATIO = COVER_SIZE[0] / COVER_SIZE[1]

ROOT = Path(__file__).resolve().parent.parent


def cover_fields_from_wechat(wx: dict[str, Any]) -> dict[str, str]:
    return {
        "title": wx.get("title", "人源化小鼠免疫评估"),
        "subtitle": wx.get("subtitle", ""),
        "digest": wx.get("cover_digest") or wx.get("lead", "")[:120],
    }


def ensure_cover_digest(wx: dict[str, Any]) -> None:
    if wx.get("cover_digest"):
        return
    lead = (wx.get("lead") or "").strip()
    if lead:
        wx["cover_digest"] = lead[:120]


def wrap_text_cn(text: str, draw, font, max_width: int) -> list[str]:
    """Wrap Chinese/English mixed text into lines based on pixel width."""
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w > max_width and current_line:
            lines.append(current_line)
            current_line = char
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)
    return lines


def build_cover_prompt(title: str, subtitle: str = "", digest: str = "") -> str:
    """gpt-image-2: background + upper-right illustration only (text via PIL)."""
    hook = (digest or subtitle or title)[:80]
    return (
        "A click-worthy premium biotech magazine cover background, wide 2.35:1 WeChat article cover. "
        "The style is sophisticated and visually engaging: luminous pale mint, deep teal accents, soft warm amber highlights, clean daylight depth. "
        "Strictly NO text, NO letters, NO numbers, NO words, NO logos, and NO watermarks anywhere in the image. "
        "Visual design elements: "
        "On the right half, create a striking hero illustration: a white humanized lab mouse with a subtle glowing immune-cell network inside, "
        "surrounded by elegant PD-1, antibody, and tumor-cell visual metaphors. Use depth, rim light, and clean scientific curves. "
        "Keep the left 56 percent of the image mostly open and softly illuminated for title overlay. "
        "Keep the bottom-right logo zone perfectly plain, clean, and pattern-free. "
        "No clutter, no tiny labels, no diagram annotations, no edge overflow. The image should make readers want to click."
    )


def crop_to_cover_size(img_bytes: bytes) -> bytes:
    from PIL import Image

    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = im.size
    ratio = w / h
    if ratio > COVER_RATIO:
        new_w = int(h * COVER_RATIO)
        left = (w - new_w) // 2
        im = im.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / COVER_RATIO)
        top = (h - new_h) // 2
        im = im.crop((0, top, w, top + new_h))
    im = im.resize(COVER_SIZE, Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _draw_cover_text(img, *, title: str, subtitle: str = "", digest: str = ""):
    """PIL text — left column, stops before logo safe zone."""
    from PIL import ImageDraw
    from logo_safe_zone import COVER_LOGO_ZONE

    draw = ImageDraw.Draw(img)
    w, h = img.size
    text_right = int(w * COVER_LOGO_ZONE[0]) - 32

    def _font(size: int, bold: bool = False):
        from cjk_fonts import cjk_font
        return cjk_font(size, bold=bold)

    draw.rounded_rectangle((32, 26, 210, 58), radius=13, fill="#0d9488")
    draw.text((121, 42), "人源化小鼠·科研简报", font=_font(14, True), fill="#ffffff", anchor="mm")
    draw.rounded_rectangle((224, 26, 342, 58), radius=13, fill="#f59e0b")
    draw.text((283, 42), "本周焦点", font=_font(14, True), fill="#ffffff", anchor="mm")
    
    title_font = _font(31, True)
    title_lines = wrap_text_cn(title, draw, title_font, text_right)
    y = 78
    for line in title_lines[:2]:
        draw.text((40, y), line, font=title_font, fill="#111827")
        y += 42
        
    y += 2
    if subtitle:
        sub_font = _font(17, True)
        sub_lines = wrap_text_cn(subtitle, draw, sub_font, text_right)
        for line in sub_lines[:1]:
            draw.text((40, y), line, font=sub_font, fill="#0f766e")
            y += 26
            
    y += 8
    if digest:
        digest_font = _font(15)
        digest_lines = wrap_text_cn(digest, draw, digest_font, text_right)
        for line in digest_lines[:2]:
            draw.text((40, y), line, font=digest_font, fill="#4b5563")
            y += 22
            
    return img


def finalize_cover(
    content_bytes: bytes,
    *,
    title: str,
    subtitle: str = "",
    digest: str = "",
    logo_path: Path | None = None,
) -> bytes:
    """PIL text + in-image logo in reserved zone — no overlap with text/patterns."""
    from logo_safe_zone import COVER_LOGO_ZONE, place_logo_in_zone
    from PIL import Image

    img = Image.open(io.BytesIO(content_bytes)).convert("RGB")
    img = _draw_cover_text(img, title=title, subtitle=subtitle, digest=digest)
    lp = logo_path or (ROOT / "assets" / "nextvivo_logo.png")
    if lp.exists():
        img = place_logo_in_zone(img, lp, COVER_LOGO_ZONE)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def place_cover_logo(content_bytes: bytes, logo_path: Path | None = None) -> bytes:
    from logo_safe_zone import COVER_LOGO_ZONE, place_logo_in_zone_bytes

    lp = logo_path or (ROOT / "assets" / "nextvivo_logo.png")
    return place_logo_in_zone_bytes(content_bytes, lp, COVER_LOGO_ZONE)


def append_cover_logo_strip(content_bytes: bytes, logo_path: Path | None = None) -> bytes:
    return place_cover_logo(content_bytes, logo_path)


def render_cover_pil_fallback(
    out_path: Path,
    *,
    title: str,
    subtitle: str = "",
    digest: str = "",
) -> Path:
    from PIL import Image

    img = Image.new("RGB", COVER_SIZE, "#ecfdf5")
    img = _draw_cover_text(img, title=title, subtitle=subtitle, digest=digest)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path


def render_cover_png(
    out_path: Path,
    *,
    title: str,
    subtitle: str = "",
    digest: str = "",
    render_fn: Callable[[str, str], bytes] | None = None,
    stamp_logo_fn: Callable[[bytes], bytes] | None = None,
) -> Path:
    """Generate cover: gpt-image-2 bg → 900×383 → PIL text + logo safe zone."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    logo_path = ROOT / "assets" / "nextvivo_logo.png"

    def _finalize(b: bytes) -> bytes:
        if stamp_logo_fn:
            return stamp_logo_fn(b)
        return finalize_cover(
            b, title=title, subtitle=subtitle, digest=digest,
            logo_path=logo_path if logo_path.exists() else None,
        )

    if render_fn:
        try:
            prompt = build_cover_prompt(title, subtitle, digest)
            raw = render_fn(prompt, "1536x1024")
            cropped = crop_to_cover_size(raw)
            out_path.write_bytes(_finalize(cropped))
            return out_path
        except Exception as exc:
            print(f"    [WARN] AI cover failed ({exc}), PIL fallback")

    render_cover_pil_fallback(out_path, title=title, subtitle=subtitle, digest=digest)
    if out_path.exists():
        out_path.write_bytes(_finalize(out_path.read_bytes()))
    return out_path
