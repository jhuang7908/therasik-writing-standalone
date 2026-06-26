#!/usr/bin/env python3

"""Mobile-friendly XHS post preview (relative image paths, no QC footer)."""

from __future__ import annotations



import json

from pathlib import Path





def build_post_preview(out_dir: Path) -> Path:

    social_path = out_dir / "social.json"

    if not social_path.exists():

        raise FileNotFoundError(social_path)

    social = json.loads(social_path.read_text(encoding="utf-8"))

    xhs = social.get("xiaohongshu") or social

    cards = xhs.get("cards") or []

    paths = sorted((out_dir / "images").glob("card_*.png"))

    img_html = ""

    for i, p in enumerate(paths):

        title = cards[i].get("title", "") if i < len(cards) else f"图{i+1}"

        cap = cards[i].get("image_caption", "") if i < len(cards) else ""

        img_html += (

            f'<section class="card"><h3>图{i+1} · {title}</h3>'

            f'<img src="images/{p.name}" alt="" loading="lazy"/>'

            f'<p class="cap">{cap}</p></section>'

        )

    paras = [p.strip() for p in (xhs.get("body") or "").split("\n\n") if p.strip()]

    body_html = "".join(f"<p>{p}</p>" for p in paras)

    hook_lines = "".join(

        f"<span>{ln}</span>" for ln in (xhs.get("cover_hook") or "").split("\n") if ln.strip()

    )

    html = f"""<!DOCTYPE html>

<html lang="zh-CN"><head>

<meta charset="utf-8"/>

<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1"/>

<link rel="preconnect" href="https://fonts.googleapis.com"/>

<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>

<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@500;600;700&family=Noto+Sans+SC:wght@400;500&display=swap" rel="stylesheet"/>

<title>{xhs.get("title", "财经小红书")}</title>

<style>

*{{box-sizing:border-box;margin:0;padding:0}}

body{{

  font-family:"Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif;

  max-width:480px;margin:0 auto;padding:20px 16px 32px;

  background:linear-gradient(180deg,#fdf8f3 0%,#f5efe8 100%);

  color:#2c2c2c;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility

}}

.header{{padding:4px 4px 0}}

h1{{

  font-family:"Noto Serif SC","Songti SC",serif;

  font-size:1.4rem;font-weight:700;line-height:1.5;letter-spacing:.04em;color:#1f1f1f

}}

.hook{{

  display:flex;flex-direction:column;gap:6px;margin:14px 0 16px;padding:12px 16px;

  background:rgba(255,255,255,.72);border-radius:12px;border-left:3px solid #e84545

}}

.hook span{{

  color:#d63a3a;font-weight:600;font-size:15px;line-height:1.6;letter-spacing:.02em

}}

.copy{{

  background:#fff;border-radius:14px;padding:20px 18px;margin:0 0 18px;

  box-shadow:0 4px 18px rgba(44,36,28,.06)

}}

.copy p{{

  margin:0 0 16px;font-size:15px;line-height:1.95;letter-spacing:.04em;

  color:#333;text-align:justify;text-justify:inter-ideograph;word-break:break-word

}}

.copy p:last-child{{margin-bottom:0}}

.tags{{

  color:#5b6b8a;margin:0 0 20px;padding:0 4px;font-size:13px;line-height:1.8;

  letter-spacing:.02em;word-break:break-all

}}

.card{{

  background:#fff;border-radius:14px;padding:14px;margin:0 0 18px;

  box-shadow:0 4px 16px rgba(44,36,28,.06)

}}

.card h3{{

  font-family:"Noto Serif SC",serif;font-size:14px;font-weight:600;

  margin:0 0 10px;color:#444;letter-spacing:.03em

}}

.card img{{width:100%;height:auto;border-radius:10px;display:block}}

.cap{{text-align:center;font-size:12px;color:#9a9a9a;margin-top:10px;letter-spacing:.05em}}

</style></head><body>

<div class="header"><h1>{xhs.get("title", "")}</h1></div>

<div class="hook">{hook_lines}</div>

<article class="copy">{body_html}</article>

<div class="tags">{" ".join(xhs.get("tags") or [])}</div>

{img_html}

</body></html>"""

    out = out_dir / "preview.html"

    out.write_text(html, encoding="utf-8")

    return out





def main() -> int:

    import argparse



    ap = argparse.ArgumentParser()

    ap.add_argument("--dir", type=Path, required=True)

    args = ap.parse_args()

    p = build_post_preview(args.dir)

    print(p)

    return 0





if __name__ == "__main__":

    raise SystemExit(main())

