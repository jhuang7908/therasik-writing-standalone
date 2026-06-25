"""HTML Renderer — converts ContentDoc to styled HTML for XHS / WeChat / Whitepaper.

The HTML is self-contained (inline CSS) so it can be:
  - Opened directly in browser
  - Converted to PDF via puppeteer / weasyprint
  - Screenshot for PNG export
"""
from __future__ import annotations

import html as _html
import json
from pathlib import Path
from typing import Optional


# ---------- style presets per doc_type ----------

_STYLES: dict[str, dict] = {
    "xiaohongshu": {
        "max_width": "400px",
        "font_family": "'PingFang SC', 'Microsoft YaHei', sans-serif",
        "body_bg": "#fff9f5",
        "card_bg": "#ffffff",
        "card_radius": "16px",
        "card_shadow": "0 4px 20px rgba(0,0,0,.10)",
        "headline_color": "#1a1a1a",
        "body_color": "#444",
        "accent": "#fe2c55",
        "gap": "20px",
    },
    "wechat": {
        "max_width": "600px",
        "font_family": "'PingFang SC', 'Microsoft YaHei', sans-serif",
        "body_bg": "#f0f0f0",
        "card_bg": "#ffffff",
        "card_radius": "4px",
        "card_shadow": "0 1px 4px rgba(0,0,0,.08)",
        "headline_color": "#333",
        "body_color": "#555",
        "accent": "#07c160",
        "gap": "12px",
    },
    "whitepaper": {
        "max_width": "800px",
        "font_family": "'Times New Roman', 'SimSun', serif",
        "body_bg": "#f8f8f8",
        "card_bg": "#ffffff",
        "card_radius": "0",
        "card_shadow": "none",
        "headline_color": "#111",
        "body_color": "#333",
        "accent": "#1a56db",
        "gap": "0",
    },
}


def _e(text: str) -> str:
    """HTML-escape text."""
    return _html.escape(str(text or ""))


def _render_block(block: dict, st: dict) -> str:
    text = block.get("text", {})
    headline = text.get("headline", "")
    sub = text.get("subheadline", "")
    paras = text.get("body_paragraphs", [])
    bullets = text.get("bullets", [])
    vis = block.get("visual", {})
    resolved_url = (vis.get("resolved") or {}).get("url")

    parts: list[str] = ["<div class='block'>"]

    # Hero image
    if resolved_url and Path(resolved_url).exists():
        parts.append(f"<img src='{_e(resolved_url)}' class='block-img' alt=''>")
    elif vis.get("prompt_zh"):
        # Placeholder with prompt text
        parts.append(f"<div class='img-placeholder'>{_e(vis['prompt_zh'])}</div>")

    if headline:
        parts.append(f"<h2 class='headline'>{_e(headline)}</h2>")
    if sub:
        parts.append(f"<p class='subheadline'>{_e(sub)}</p>")
    for p in paras:
        parts.append(f"<p class='para'>{_e(p)}</p>")
    if bullets:
        items = "".join(f"<li>{_e(b)}</li>" for b in bullets)
        parts.append(f"<ul class='bullets'>{items}</ul>")

    parts.append("</div>")
    return "\n".join(parts)


def render_html(content_doc: dict, doc_type: str,
                template_id: str, out_path: str) -> str:
    st = _STYLES.get(doc_type, _STYLES["wechat"])
    meta = content_doc.get("meta", {})
    title = _e(meta.get("title", "Creative Studio Document"))
    blocks_html = "\n".join(_render_block(b, st) for b in content_doc.get("blocks", []))

    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: {st['body_bg']};
    font-family: {st['font_family']};
    padding: 32px 16px;
    color: {st['body_color']};
  }}
  .wrapper {{
    max-width: {st['max_width']};
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: {st['gap']};
  }}
  .block {{
    background: {st['card_bg']};
    border-radius: {st['card_radius']};
    box-shadow: {st['card_shadow']};
    padding: 24px;
    overflow: hidden;
  }}
  .block-img {{
    width: 100%;
    max-height: 320px;
    object-fit: cover;
    border-radius: 8px;
    margin-bottom: 16px;
  }}
  .img-placeholder {{
    width: 100%;
    height: 180px;
    background: #e8eaed;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #999;
    font-size: 13px;
    margin-bottom: 16px;
    padding: 12px;
    text-align: center;
  }}
  .headline {{
    font-size: 20px;
    font-weight: 700;
    color: {st['headline_color']};
    margin-bottom: 8px;
    line-height: 1.4;
  }}
  .subheadline {{
    font-size: 15px;
    color: {st['accent']};
    margin-bottom: 10px;
    font-weight: 500;
  }}
  .para {{
    font-size: 15px;
    line-height: 1.8;
    color: {st['body_color']};
    margin-bottom: 8px;
  }}
  .bullets {{
    padding-left: 20px;
    margin-top: 8px;
  }}
  .bullets li {{
    font-size: 14px;
    line-height: 1.7;
    color: {st['body_color']};
    margin-bottom: 4px;
  }}
</style>
</head>
<body>
<div class="wrapper">
{blocks_html}
</div>
</body>
</html>"""

    Path(out_path).write_text(page, encoding="utf-8")
    return out_path
