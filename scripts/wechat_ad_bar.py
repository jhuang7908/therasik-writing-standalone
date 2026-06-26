#!/usr/bin/env python3
"""Fixed WeChat ad/promo bar for humanized-mice weekly reports (SSOT from YAML)."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Callable

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "wechat_ad_bar.yaml"


def resolve_logo_path(cfg: dict[str, Any] | None = None) -> Path | None:
    c = cfg or load_ad_bar_config()
    rel = c.get("logo_path", "assets/nextvivo_logo.png")
    p = ROOT / rel
    return p if p.exists() else None


def resolve_qr_path(cfg: dict[str, Any] | None = None) -> Path | None:
    c = cfg or load_ad_bar_config()
    rel = (c.get("qr_path") or "").strip()
    if not rel:
        return None
    p = Path(rel)
    if not p.is_absolute():
        p = ROOT / rel
    return p if p.exists() else None


def load_ad_bar_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG
    if not cfg_path.exists():
        raise FileNotFoundError(f"WeChat ad bar config missing: {cfg_path}")
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    if not data.get("title"):
        raise ValueError(f"Invalid ad bar config: {cfg_path}")
    return data


def ad_bar_dict(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    c = cfg or load_ad_bar_config()
    return {
        "heading": c.get("heading", "— 合作咨询 · 广告栏 —"),
        "title": c.get("title", ""),
        "tagline": c.get("tagline", ""),
        "body": (c.get("body") or "").strip(),
        "bullets": list(c.get("bullets") or []),
        "cta_primary": c.get("cta_primary", ""),
        "cta_secondary": c.get("cta_secondary", ""),
        "qr_label": c.get("qr_label", ""),
        "contacts": list(c.get("contacts") or []),
        "footer_note": c.get("footer_note", ""),
    }


def inject_ad_bar(social_data: dict[str, Any], cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    wx = social_data.setdefault("wechat", {})
    wx["ad_bar"] = ad_bar_dict(cfg)
    return social_data


from logo_safe_zone import prepare_logo_rgba

# Re-export for callers
_prepare_logo_rgba = prepare_logo_rgba


AD_WIDTH = 900
AD_BANNER_H = 360
AD_BANNER_SIZE = (AD_WIDTH, AD_BANNER_H)
AD_BANNER_RATIO = AD_WIDTH / AD_BANNER_H


def _font(size: int, bold: bool = False):
    from cjk_fonts import cjk_font
    return cjk_font(size, bold=bold)


def build_ad_banner_bg_prompt() -> str:
    """gpt-image-2: decorative background only — text/logo added by PIL."""
    return (
        "A compact WeChat end-of-article service card background, 900x360 horizontal card. "
        "The background is elegant, bright, soft pale mint green and daylight-white with a subtle premium biotech feel. "
        "Strictly NO text, NO letters, NO numbers, NO words, NO logos, and NO watermarks. "
        "Visual design elements: "
        "A soft rounded card border, very light teal inner glow, and a gentle vertical rhythm like an elegant brochure card. "
        "Most of the canvas should be clean plain empty background for text overlay. "
        "Right side may contain very faint scientific line-art accents only. "
        "No busy patterns, no large blank white glare, no edge clipping. Premium, compact, readable."
    )


def build_ad_banner_prompt(cfg: dict[str, Any]) -> str:
    """Deprecated alias — use build_ad_banner_bg_prompt()."""
    return build_ad_banner_bg_prompt()


def crop_to_ad_banner_size(img_bytes: bytes) -> bytes:
    from PIL import Image

    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = im.size
    ratio = w / h
    if ratio > AD_BANNER_RATIO:
        new_w = int(h * AD_BANNER_RATIO)
        left = (w - new_w) // 2
        im = im.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / AD_BANNER_RATIO)
        top = (h - new_h) // 2
        im = im.crop((0, top, w, top + new_h))
    im = im.resize(AD_BANNER_SIZE, Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def crop_to_ad_content_size(img_bytes: bytes) -> bytes:
    return crop_to_ad_banner_size(img_bytes)


def _paste_inline_logo(img, logo_path: Path, *, x: int = 48, y: int = 72, target_w: int = 150):
    """Small logo placed inline with organization name."""
    from PIL import Image

    logo = prepare_logo_rgba(logo_path)
    lh = int(logo.height * target_w / max(logo.width, 1))
    logo = logo.resize((target_w, lh), Image.LANCZOS)
    base = img.convert("RGBA")
    base.paste(logo, (x, y), mask=logo)
    return base.convert("RGB"), x + target_w + 18, y + max(0, (lh - 28) // 2)


def _paste_qr_block(img, c: dict[str, Any], *, x: int, y: int, size: int = 118):
    """Right-side QR block. Uses real qr_path when provided; otherwise draws a placeholder."""
    from PIL import Image, ImageDraw

    draw = ImageDraw.Draw(img)
    box_pad = 12
    box = (x - box_pad, y - box_pad, x + size + box_pad, y + size + 42)
    draw.rounded_rectangle(box, radius=16, fill="#f8fffc", outline="#99d5c9", width=2)

    qr_path = resolve_qr_path(c)
    if qr_path:
        qr = Image.open(qr_path).convert("RGB").resize((size, size), Image.LANCZOS)
        img.paste(qr, (x, y))
    else:
        draw.rounded_rectangle((x, y, x + size, y + size), radius=8, fill="#ffffff", outline="#0d9488", width=2)
        # Placeholder QR-like pattern so the layout is visible before the real QR is provided.
        cell = size // 9
        for row in range(9):
            for col in range(9):
                if row in (0, 1, 7, 8) or col in (0, 1, 7, 8) or (row + col) % 3 == 0:
                    if 1 < row < 7 and 1 < col < 7 and (row + col) % 3 != 0:
                        continue
                    draw.rectangle(
                        (x + col * cell + 2, y + row * cell + 2, x + (col + 1) * cell - 2, y + (row + 1) * cell - 2),
                        fill="#0f766e",
                    )
        draw.text((x + size // 2, y + size // 2), "QR", font=_font(22, True), fill="#0f766e", anchor="mm")

    label = c.get("qr_label") or "扫码添加客服微信"
    draw.text((x + size // 2, y + size + 22), label, font=_font(15, True), fill="#0f766e", anchor="mm")
    return img


def _draw_ad_text(img, c: dict[str, Any]):
    """Exact YAML copy — compact card with inline logo + organization name."""
    from PIL import ImageDraw
    from wechat_cover import wrap_text_cn

    w, h = img.size
    qr_size = 118
    qr_x = w - qr_size - 58
    qr_y = 138
    text_right = qr_x - 36
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, w, 56), fill="#ecfdf5")
    draw.text((w // 2, 28), c.get("heading", ""), font=_font(18, True), fill="#0f766e", anchor="mm")

    logo_path = resolve_logo_path(c)
    title_x, title_y = 48, 76
    if logo_path:
        img, title_x, title_y = _paste_inline_logo(img, logo_path, x=48, y=68, target_w=150)
        draw = ImageDraw.Draw(img)

    title_font = _font(25, True)
    title = c.get("title", "")[:24]
    draw.text((title_x, title_y), title, font=title_font, fill="#111827")
        
    tagline_font = _font(18, True)
    tagline_lines = wrap_text_cn(c.get("tagline", ""), draw, tagline_font, text_right - 48)
    y = 128
    for line in tagline_lines[:1]:
        draw.text((48, y), line, font=tagline_font, fill="#0d9488")
        y += 30
        
    y += 6
    bullet_font = _font(17)
    for bullet in (c.get("bullets") or [])[:3]:
        draw.ellipse((52, y + 5, 64, y + 17), fill="#0d9488")
        bullet_lines = wrap_text_cn(bullet, draw, bullet_font, text_right - 96)
        for line in bullet_lines[:1]:
            draw.text((78, y), line, font=bullet_font, fill="#374151")
        y += 30
        
    cta_font = _font(18, True)
    cta_lines = wrap_text_cn(c.get("cta_primary", ""), draw, cta_font, text_right - 48)
    cta_y = min(y + 10, h - 52)
    for line in cta_lines[:1]:
        draw.text((48, cta_y), line, font=cta_font, fill="#0f766e")

    img = _paste_qr_block(img, c, x=qr_x, y=qr_y, size=qr_size)
    return img


def _compose_ad_banner(content_img, c: dict[str, Any], logo_path: Path | None):
    return _draw_ad_text(content_img.copy(), c)


def render_ad_bar_html(ad: dict[str, Any], *, embed_cid: str | None = None) -> str:
    bullets = "".join(
        f'<li style="margin:6px 0">{b}</li>' for b in ad.get("bullets") or []
    )
    contacts = ad.get("contacts") or []
    contact_html = " · ".join(
        f'<span><b>{c.get("label", "")}</b> {c.get("value", "")}</span>'
        for c in contacts
    )
    img_html = ""
    if embed_cid:
        img_html = (
            f'<p style="text-align:center;margin:16px 0">'
            f'<img src="cid:{embed_cid}" alt="广告栏" '
            f'style="max-width:100%;border-radius:8px;border:1px solid #cdeee7"/>'
            f"</p>"
        )
    return f"""
<div style="margin:28px 0;padding:20px 22px;background:linear-gradient(135deg,#ecfdf5 0%,#f0fdfa 100%);
            border:2px solid #0d9488;border-radius:12px">
  <p style="text-align:center;color:#0f766e;font-size:13px;font-weight:bold;margin:0 0 10px">
    {ad.get('heading', '')}
  </p>
  {img_html}
  <h3 style="color:#0f766e;margin:0 0 6px;font-size:20px">{ad.get('title', '')}</h3>
  <p style="color:#115e59;font-size:15px;font-weight:bold;margin:0 0 12px">{ad.get('tagline', '')}</p>
  <p style="line-height:1.85;color:#1f2937;margin:0 0 12px">{ad.get('body', '')}</p>
  <ul style="margin:0 0 14px 18px;padding:0;color:#374151;line-height:1.7">{bullets}</ul>
  <p style="margin:10px 0;color:#0d9488;font-weight:bold">{ad.get('cta_primary', '')}</p>
  <p style="margin:6px 0;color:#0d9488">{ad.get('cta_secondary', '')}</p>
  <p style="margin:14px 0 8px;font-size:13px;color:#4b5563">{contact_html}</p>
  <p style="margin:8px 0 0;font-size:11px;color:#9ca3af">{ad.get('footer_note', '')}</p>
</div>"""


def _render_ad_banner_pil(out_path: Path, c: dict[str, Any]) -> Path:
    """PIL-only fallback: flat card + text + in-image logo zone."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", AD_BANNER_SIZE, "#f4fffc")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((24, 16, AD_WIDTH - 24, AD_BANNER_H - 16), radius=16, fill="#ffffff", outline="#0d9488", width=2)
    logo_path = resolve_logo_path(c)
    composed = _compose_ad_banner(img, c, logo_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    composed.save(out_path, "PNG", optimize=True)
    return out_path


def render_ad_banner_png(
    out_path: Path,
    cfg: dict[str, Any] | None = None,
    *,
    render_fn: Callable[[str, str], bytes] | None = None,
) -> Path:
    """Ad banner: gpt-image-2 bg + PIL text + logo in bottom-right safe zone."""
    from PIL import Image

    c = cfg or load_ad_bar_config()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    logo_path = resolve_logo_path(c)

    if render_fn:
        try:
            raw = render_fn(build_ad_banner_bg_prompt(), "1536x1024")
            cropped = crop_to_ad_banner_size(raw)
            content = Image.open(io.BytesIO(cropped)).convert("RGB")
            composed = _compose_ad_banner(content, c, logo_path)
            composed.save(out_path, "PNG", optimize=True)
            return out_path
        except Exception as exc:
            print(f"    [WARN] AI ad banner failed ({exc}), PIL fallback")

    return _render_ad_banner_pil(out_path, c)


def ensure_ad_assets(social_data: dict[str, Any], img_dir: Path) -> dict[str, Any]:
    inject_ad_bar(social_data)
    banner = img_dir / "wechat_ad_bar.png"
    if not banner.exists():
        render_ad_banner_png(banner)
        print(f"    ad banner saved: {banner.name}")
    return social_data
