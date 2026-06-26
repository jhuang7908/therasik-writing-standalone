#!/usr/bin/env python3
"""Build preview.html with base64-embedded images (single portable file)."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path


def b64_uri(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    mime = "jpeg" if suffix in ("jpg", "jpeg") else "png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{data}"


def build_post_preview(out_dir: Path) -> Path:
    social_path = out_dir / "social.json"
    if not social_path.exists():
        raise FileNotFoundError(social_path)
    social = json.loads(social_path.read_text(encoding="utf-8"))
    xhs = social.get("xiaohongshu") or social
    paths = sorted((out_dir / "images").glob("card_*.png"))
    cards = xhs.get("cards") or []
    img_html = ""
    for i, p in enumerate(paths):
        title = cards[i].get("title", "") if i < len(cards) else f"图{i+1}"
        cap = cards[i].get("image_caption", "") if i < len(cards) else ""
        img_html += (
            f'<section class="card"><h3>图{i+1} · {title}</h3>'
            f'<img src="{b64_uri(p)}" alt=""/><p class="cap">{cap}</p></section>'
        )
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<title>{xhs.get("title", "财经小红书")}</title>
<style>
body{{font-family:"PingFang SC","Microsoft YaHei",sans-serif;max-width:420px;margin:24px auto;padding:16px;background:#f5f5f5}}
h1{{font-size:1.2rem}}.hook{{color:#FF2442;font-weight:600;white-space:pre-line;margin:12px 0}}
.body{{line-height:1.75;font-size:15px;color:#333}}.tags{{color:#576b95;margin:16px 0;font-size:14px}}
.card{{background:#fff;border-radius:12px;padding:12px;margin:16px 0;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.card img{{width:100%;border-radius:8px}}.cap{{text-align:center;font-size:12px;color:#888}}
.meta{{font-size:12px;color:#999;margin-top:20px}}
</style></head><body>
<h1>{xhs.get("title", "")}</h1>
<div class="hook">{xhs.get("cover_hook", "")}</div>
<div class="body">{xhs.get("body", "")}</div>
<div class="tags">{" ".join(xhs.get("tags") or [])}</div>
{img_html}
<p class="meta">单文件预览 · 图片已内嵌 · 非投资建议</p>
</body></html>"""
    out = out_dir / "preview.html"
    out.write_text(html, encoding="utf-8")
    return out


def build_style_examples_preview(out_dir: Path, gpt_card: Path | None = None) -> Path:
    styles = [
        ("editorial_soft", "Seedream · 编辑感轻插画（推荐默认）", "card1_editorial_soft.png"),
        ("minimal_line", "Seedream · 极简线稿", "card1_minimal_line.png"),
        ("warm_sketch", "Seedream · 暖色手账风", "card1_warm_sketch.png"),
    ]
    blocks = ""
    for key, label, fname in styles:
        p = out_dir / fname
        if not p.exists():
            continue
        blocks += f"""
<div class="card"><strong>{key}</strong> · {label}
<img src="{b64_uri(p)}" alt=""/>
<p class="note">FINANCE_XHS_IMAGE_STYLE={key}</p></div>"""

    if gpt_card and gpt_card.exists():
        blocks += f"""
<div class="card"><strong>gpt_infographic</strong> · gpt-image-2 · 商业信息图（旧版）
<img src="{b64_uri(gpt_card)}" alt=""/>
<p class="note">FINANCE_XHS_IMAGE_STYLE=gpt_infographic</p></div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<title>财经小红书 · 风格例子</title>
<style>
body{{font-family:"PingFang SC","Microsoft YaHei",sans-serif;max-width:480px;margin:24px auto;padding:16px;background:#f0f0f0}}
.card{{background:#fff;border-radius:12px;padding:14px;margin:14px 0;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.card img{{width:100%;border-radius:8px}}.tag{{display:inline-block;background:#eee;padding:2px 8px;border-radius:4px;font-size:12px;margin-right:6px}}
.body{{line-height:1.75;font-size:15px;white-space:pre-wrap}}.hook{{color:#FF2442;font-weight:600;margin:8px 0}}
.note{{font-size:12px;color:#888;margin-top:6px}}
</style></head><body>
<h1>财经小红书 · 风格例子（单文件·图已内嵌）</h1>
<h2>文案例子</h2>
<div class="card">
<strong>标题</strong> 美债到4.5% 贷款会变贵吗<br/>
<div class="hook">纳指跌近5%<br/>10年国债收益率上行</div>
<div class="body">这周美股压力不小：纳指跌4.68%，标普500跌2.59%，道指小跌0.32%。10年期美债收益率升到4.536%，黄金期货跌到4348.8美元。

对想贷款的人来说，国债收益率往上走，银行报价往往也会跟着紧。别只比 headline rate，APR 才更接近真实成本。</div>
<p><span class="tag">#美国财经</span><span class="tag">#房贷利率</span><span class="tag">#美债</span><span class="tag">#ClosingCosts</span><span class="tag">#理财笔记</span></p>
</div>
<h2>配图风格（卡1）</h2>
{blocks}
<p class="note">拷贝本 HTML 到任意目录均可看图。</p>
</body></html>"""
    out = out_dir / "preview.html"
    out.write_text(html, encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True, help="Output folder with social.json+images or style pngs")
    ap.add_argument("--mode", choices=["post", "style_examples"], default="post")
    ap.add_argument("--gpt-card", type=Path, default=None, help="Optional gpt-image-2 card for style_examples")
    args = ap.parse_args()
    if args.mode == "style_examples":
        p = build_style_examples_preview(args.dir, args.gpt_card)
    else:
        p = build_post_preview(args.dir)
    print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
