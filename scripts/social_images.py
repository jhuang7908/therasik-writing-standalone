"""
social_images.py — Generate social media images for XHS (6 cards) and WeChat (3 images).

Render routing (per pipeline_rules.yaml):
  - Scientific data panels  → gpt-image-2
  - Illustrative/brand art  → CogView-4 (cost-efficient)

All images get NextVivo logo bottom-right (no text watermark).
"""

import os, sys, json, time, base64, requests, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

ROOT = Path(__file__).parent.parent
FROZEN_WECHAT_DEFAULT = ROOT / "data" / "frozen" / "humanized_mice_front_immunol_2026" / "wechat"
for _env in [ROOT / "content_generation_tools" / ".env", ROOT / ".env"]:
    if _env.exists():
        for _l in _env.read_text(encoding="utf-8").splitlines():
            _l = _l.strip()
            if _l and not _l.startswith("#") and "=" in _l:
                _k, _v = _l.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
        break

LOGO_PATH  = ROOT / "assets" / "nextvivo_logo.png"
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
ZHIPU_KEY  = os.environ.get("ZHIPU_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")

# ── Image generation helpers ──────────────────────────────────────────────────

def _prepare_logo_rgba(logo_path: Path) -> Image.Image:
    """Load logo; drop solid black backdrop so it reads on light/dark covers."""
    logo = Image.open(logo_path).convert("RGBA")
    px = logo.load()
    w, h = logo.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r < 45 and g < 45 and b < 45:
                px[x, y] = (r, g, b, 0)
    return logo


def _stamp_logo(
    img_bytes: bytes,
    *,
    width_pct: float = 0.10,
    margin_pct: float = 0.04,
    with_backdrop: bool = False,
    corner: str = "bottom-right",
) -> bytes:
    """Logo in safe corner; cover uses bottom-left to avoid illustration overlap.
    margin_pct=0.04 ensures 4% safe zone from image edges — prevents content overlap.
    """
    if not LOGO_PATH.exists():
        return img_bytes
    slide = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    logo = _prepare_logo_rgba(LOGO_PATH)
    W, H = slide.size
    lw = int(W * width_pct)
    lh = int(logo.height * lw / max(logo.width, 1))
    logo = logo.resize((lw, lh), Image.LANCZOS)
    pad_x = int(W * margin_pct)
    pad_y = int(H * margin_pct)
    if corner == "bottom-left":
        x, y = pad_x, H - lh - pad_y
    else:
        x, y = W - lw - pad_x, H - lh - pad_y
    comp = Image.new("RGBA", slide.size)
    comp.paste(slide, (0, 0))
    if with_backdrop:
        from PIL import ImageDraw

        pill_pad = max(8, int(lw * 0.07))
        pill = Image.new("RGBA", slide.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(pill)
        draw.rounded_rectangle(
            (x - pill_pad, y - pill_pad, x + lw + pill_pad, y + lh + pill_pad),
            radius=max(8, pill_pad),
            fill=(255, 255, 255, 240),
            outline=(13, 148, 136, 160),
            width=2,
        )
        comp = Image.alpha_composite(comp, pill)
    comp.paste(logo, (x, y), mask=logo)
    buf = io.BytesIO()
    comp.convert("RGB").save(buf, "PNG")
    return buf.getvalue()


def stamp_cover_logo(img_bytes: bytes) -> bytes:
    """Cover: bottom-left logo — avoids blocking right-side illustration."""
    return _stamp_logo(
        img_bytes, width_pct=0.20, margin_pct=0.028, with_backdrop=True, corner="bottom-left"
    )


def _gpt_generate(prompt: str, size: str = "1024x1024") -> bytes:
    """图内文字优先用真实 gpt-image-2(high)（中文不乱码）。"""
    resp = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
        json={"model": "gpt-image-2", "prompt": prompt, "n": 1,
              "size": size, "quality": "high"},
        timeout=180,
    )
    data = resp.json()
    if "data" not in data:
        raise RuntimeError(f"gpt-image-2 error: {data}")
    return base64.b64decode(data["data"][0]["b64_json"])


def _nano_generate(prompt: str, size: str = "1024x1024") -> bytes:
    """Nano Banana Pro (Gemini 3 Pro Image) 2K——中文文字渲染极佳，作为一级回退。"""
    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY missing for Nano Banana Pro fallback")
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "gemini-3-pro-image-preview:generateContent")
    resp = requests.post(
        url,
        headers={"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"responseModalities": ["IMAGE"],
                                   "imageConfig": {"imageSize": "2K"}}},
        timeout=180,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Nano Banana Pro HTTP {resp.status_code}: {resp.text[:300]}")
    parts = (resp.json().get("candidates") or [{}])[0].get("content", {}).get("parts") or []
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            return base64.b64decode(inline["data"])
    raise RuntimeError("Nano Banana Pro empty image response")


def render_gpt(prompt: str, size: str = "1024x1024", *, allow_cogview: bool = False) -> bytes:
    """图内中文渲染链：gpt-image-2(high) → Nano Banana Pro 2K。默认禁止 CogView（会乱码）。"""
    errors = []
    for name, fn in (("gpt-image-2", _gpt_generate), ("nano_banana_pro", _nano_generate)):
        try:
            return fn(prompt, size)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}")
    if allow_cogview:
        try:
            return render_cogview(prompt, size)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"cogview-4: {exc}")
    raise RuntimeError("All text-safe image backends failed -> " + " | ".join(errors))


def _render_gpt_edit(bg_bytes: bytes, engrave_prompt: str) -> bytes:
    """gpt-image-2 edit: engrave Chinese text on CogView background."""
    import io
    b64_bg = base64.b64encode(bg_bytes).decode()
    resp = requests.post(
        "https://api.openai.com/v1/images/edits",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        files={"image": ("bg.png", io.BytesIO(bg_bytes), "image/png")},
        data={"model": "gpt-image-2", "prompt": engrave_prompt, "n": "1", "size": "1024x1024"},
        timeout=120,
    )
    data = resp.json()
    if "data" not in data:
        raise RuntimeError(f"gpt-image-2 edit error: {data}")
    return base64.b64decode(data["data"][0]["b64_json"])


def render_cogview(prompt: str, size: str = "1024x1024") -> bytes:
    resp = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/images/generations",
        headers={"Authorization": f"Bearer {ZHIPU_KEY}", "Content-Type": "application/json"},
        json={"model": "cogview-4", "prompt": prompt, "size": size},
        timeout=120,
    )
    data = resp.json()
    url  = data.get("data", [{}])[0].get("url", "")
    if not url:
        raise RuntimeError(f"CogView-4 error: {data}")
    return requests.get(url, timeout=60).content


def save_image(img_bytes: bytes, path: Path,
               *,
               vqa: bool = True,
               regen_fn=None,
               max_retries: int = 3,
               expected_section: str | None = None):
    """Save image with PIL logo stamp, then run gpt-4o visual QA.

    If QA returns FAIL and regen_fn is provided, regenerate and re-check
    in a loop until PASS/WARN or max_retries is exhausted.
    """
    from visual_qa import check_and_report
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_stamp_logo(img_bytes))
    print(f"    saved {path.name}  ({path.stat().st_size // 1024}KB)")
    if not vqa:
        return
    result = check_and_report(path, expected_section=expected_section)
    if result.ok() or regen_fn is None:
        return
    for attempt in range(1, max_retries + 1):
        print(f"    VQA FAIL — regenerating {path.name} (attempt {attempt}/{max_retries})...")
        try:
            new_bytes = regen_fn()
            path.write_bytes(_stamp_logo(new_bytes))
            print(f"    re-saved {path.name}  ({path.stat().st_size // 1024}KB)")
            result = check_and_report(path, label=f"{path.name} attempt {attempt}",
                                      expected_section=expected_section)
            if result.ok():
                break
        except Exception as e:
            print(f"    [WARN] regeneration attempt {attempt} failed: {e}")
            break
    if not result.ok():
        print(f"    [WARN] {path.name} still FAIL after {max_retries} retries — keeping last version")


# ── XHS: 6 card images (1024×1024 square) ────────────────────────────────────

# Same style SSOT as codex-ppt deck_spec (手绘技术解释风)
CODEX_STYLE = (
    "Style: clean hand-drawn technical explainer, whiteboard marker style, airy whitespace, "
    "near-white paper background #FCFBF7, soft graphite marker lines, "
    "pale blue #BFD7F1 accents, sage green #CFE2D1 highlights, coral red #E8705A for warnings. "
    "Large readable Chinese headings, compact handwritten Chinese annotations, thin black marker weight. "
    "Text-image fusion: all Chinese text baked into the image. NO garbled text. "
    "No logo, no watermark, no brand mark, no company name in the image. "
)

XHS_CARD_STYLE = CODEX_STYLE + "Square format 1:1 (1024x1024), Xiaohongshu card layout. "


def _slide_img(slide_dir: Path | None, slide_num: int) -> Path | None:
    """Return path to PPT slide image if it exists (1-indexed)."""
    if not slide_dir:
        return None
    p = slide_dir / f"slide_{slide_num:02d}.png"
    return p if p.exists() else None


def _crop_to_square(img_bytes: bytes) -> bytes:
    """Centre-crop 16:9 image to 1:1 square for XHS."""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top  = (h - side) // 2
    img  = img.crop((left, top, left + side, top + side))
    buf  = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _pil_text_card(bg_bytes: bytes, title: str, body: str, bullets: list[str]) -> bytes:
    """2-panel XHS card: top 62% = slide image, bottom 38% = white panel with text.

    This avoids darkening the hand-drawn illustration and prevents text-on-text clutter.
    Output is always square (1080×1080).
    """
    from cjk_fonts import cjk_font

    SIDE = 1080
    IMG_H = int(SIDE * 0.62)   # image zone height
    TXT_H = SIDE - IMG_H        # text zone height

    # ── Image zone: crop to 16:9 then resize to fill top panel ──────────────
    src = Image.open(io.BytesIO(bg_bytes)).convert("RGB")
    sw, sh = src.size
    # Crop landscape to fill 1080 wide × IMG_H tall (centre crop)
    target_ratio = SIDE / IMG_H
    if sw / sh > target_ratio:
        new_w = int(sh * target_ratio)
        x0 = (sw - new_w) // 2
        src = src.crop((x0, 0, x0 + new_w, sh))
    else:
        new_h = int(sw / target_ratio)
        y0 = (sh - new_h) // 2
        src = src.crop((0, y0, sw, y0 + new_h))
    img_zone = src.resize((SIDE, IMG_H), Image.LANCZOS)

    # ── Text zone: white/light gradient panel ────────────────────────────────
    txt_zone = Image.new("RGB", (SIDE, TXT_H), (250, 250, 252))

    # Thin accent bar at top of text zone
    accent_bar = Image.new("RGB", (SIDE, 5), (41, 128, 185))
    txt_zone.paste(accent_bar, (0, 0))

    draw = ImageDraw.Draw(txt_zone)
    pad   = int(SIDE * 0.055)
    max_w = SIDE - 2 * pad

    ft_title  = cjk_font(int(TXT_H * 0.155), bold=True)
    ft_bullet = cjk_font(int(TXT_H * 0.098))

    def draw_wrapped(text: str, font, color, start_y: int, line_h_ratio: float = 1.35) -> int:
        """Returns y after last drawn line."""
        y = start_y
        line = ""
        for ch in text:
            test = line + ch
            if draw.textlength(test, font=font) > max_w:
                draw.text((pad, y), line, font=font, fill=color)
                y += int(font.size * line_h_ratio)
                line = ch
            else:
                line = test
        if line:
            draw.text((pad, y), line, font=font, fill=color)
            y += int(font.size * line_h_ratio)
        return y

    y = int(TXT_H * 0.07)  # start after accent bar
    y = draw_wrapped(title[:28], ft_title, (30, 30, 60), y)
    y += int(TXT_H * 0.04)
    for b in bullets[:3]:
        y = draw_wrapped(f"· {b}", ft_bullet, (55, 85, 130), y)

    # ── Composite final square ───────────────────────────────────────────────
    canvas = Image.new("RGB", (SIDE, SIDE))
    canvas.paste(img_zone, (0, 0))
    canvas.paste(txt_zone, (0, IMG_H))

    buf = io.BytesIO()
    canvas.save(buf, "PNG")
    return buf.getvalue()


def generate_xhs_images(social_data: dict, out_dir: Path, *, force: bool = False,
                        slide_dir: Path | None = None):
    """Generate 6 XHS card images.
    
    If slide_dir has PPT slides, reuse them as backgrounds (PIL text overlay).
    Otherwise fall back to gpt-image-2 full render.
    """
    print("  Generating XHS cards...")
    cards = social_data.get("xiaohongshu", {}).get("cards", [])

    for i, card in enumerate(cards, 1):
        out = out_dir / f"xhs_card_{i:02d}.png"
        if out.exists() and not force:
            print(f"    card {i}: cached")
            continue

        title   = card.get("title", "")
        body    = card.get("body", "")
        bullets = card.get("bullets", [])
        caption = card.get("image_caption", "")

        slide_path = _slide_img(slide_dir, i)

        if slide_path:
            # Reuse PPT slide: new 2-panel design (top=image, bottom=text panel)
            try:
                print(f"    card {i}: reuse slide_{i:02d} + 2-panel layout...")
                bg = slide_path.read_bytes()
                card_bytes = _pil_text_card(bg, title, body[:120], bullets)
                save_image(card_bytes, out)
                continue
            except Exception as e:
                print(f"    [WARN] slide reuse failed for card {i}: {e}, falling back to gpt-image-2")

        # Fallback: gpt-image-2 full render
        try:
            bullet_text = "  ".join(f"• {b}" for b in bullets)
            prompt = (
                XHS_CARD_STYLE +
                f"Xiaohongshu card {i}/6. "
                f"Chinese title: {title}. Body: {body}. Points: {bullet_text}. "
                f"Visual: {caption}. Hand-drawn technical explainer, all Chinese text baked in, NO garbled characters."
            )
            print(f"    card {i} (gpt-image-2 fallback)...")
            img = render_gpt(prompt, size="1024x1024")
            save_image(img, out)
            time.sleep(2)
        except Exception as e:
            print(f"    [WARN] card {i} failed: {e}")


# ── WeChat: 封面图 + 2 正文配图 + 文末广告栏 ─────────────────────────────────

WECHAT_INLINE_STYLE = CODEX_STYLE + "Wide format 16:9 for WeChat article inline illustration. "


def _copy_frozen_wechat_asset(name: str, out_path: Path, frozen_dir: Path | None) -> bool:
    """Use pinned cover/ad bar PNG when present (approved layout, no CI font drift)."""
    if not frozen_dir:
        return False
    src = frozen_dir / name
    if not src.exists():
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, out_path)
    print(f"    {name}: pinned from {src.parent.name}/ (approved SSOT)")
    return True


def generate_wechat_cover(social_data: dict, out_dir: Path, *, force: bool = False, frozen_dir: Path | None = None):
    """封面图 900×383 — gpt-image-2 生成，群聊外链预览，正文内不显示。"""
    from wechat_cover import cover_fields_from_wechat, render_cover_png

    out = out_dir / "wechat_cover.png"
    if _copy_frozen_wechat_asset("wechat_cover.png", out, frozen_dir):
        return
    if out.exists() and not force:
        print("    cover: cached")
        return
    wx = social_data.get("wechat", {})
    fields = cover_fields_from_wechat(wx)
    print("    cover (gpt-image-2 → 900×383)...")

    def _render(prompt: str, size: str) -> bytes:
        return render_gpt(prompt, size)

    render_cover_png(out, render_fn=_render, **fields)


def generate_wechat_images(social_data: dict, out_dir: Path, *, force: bool = False,
                           frozen_dir: Path | None = None, slide_dir: Path | None = None,
                           inline_sections: list[int] | None = None):
    """Generate inline illustrations for selected sections — cover is separate.

    inline_sections: 1-indexed list of section numbers to illustrate (default [2,3,4]).
    Priority: frozen pinned > PPT slide reuse > gpt-image-2 new generation.
    """
    if inline_sections is None:
        inline_sections = [1, 2, 3]
    print(f"  Generating WeChat inline images for sections {inline_sections}...")
    wx       = social_data.get("wechat", {})
    sections = wx.get("sections", [])

    img_counter = 0  # sequential output numbering: 01, 02, 03 ...
    for idx, sec in enumerate(sections):
        num     = idx + 1
        if num not in inline_sections:
            continue
        img_counter += 1
        name    = f"wechat_inline_{img_counter:02d}.png"
        out_img = out_dir / name
        # 1. Try pinned frozen asset (skipped when force=True to allow regeneration)
        if not force and _copy_frozen_wechat_asset(name, out_img, frozen_dir):
            continue
        if out_img.exists() and not force:
            print(f"    inline {num}: cached")
            continue
        # 2. Reuse corresponding PPT slide (same 16:9 format — no crop needed)
        slide_path = _slide_img(slide_dir, num)
        if slide_path:
            try:
                print(f"    inline {num}: reuse slide_{num:02d} (no re-render)")
                shutil.copy2(slide_path, out_img)
                continue
            except Exception as e:
                print(f"    [WARN] slide copy failed: {e}")
        # 3. Fallback: gpt-image-2
        heading = sec.get("heading", "")
        body    = sec.get("body", "")[:200]
        prompt  = (
            WECHAT_INLINE_STYLE +
            f"Inline scientific illustration for section: {heading}. "
            f"Content summary: {body}. "
            f"Horizontal format 16:9."
        )
        try:
            print(f"    inline {img_counter} (gpt-image-2)...")
            img = render_gpt(prompt, size="1536x1024")
            _cn_ordinals = ["一","二","三","四","五","六","七","八","九","十"]
            exp_sec = _cn_ordinals[num - 1] if num <= len(_cn_ordinals) else None
            save_image(img, out_img,
                       regen_fn=lambda p=prompt: render_gpt(p, size="1536x1024"),
                       expected_section=exp_sec)
            time.sleep(2)
        except Exception as e:
            print(f"    [WARN] inline {img_counter} failed: {e}")


def generate_wechat_ad_banner(out_dir: Path, *, force: bool = False, frozen_dir: Path | None = None,
                              ad_bar_config: Path | None = None):
    """Fixed promo banner — gpt-image-2 layout + real logo overlay."""
    from wechat_ad_bar import load_ad_bar_config, render_ad_banner_png

    out = out_dir / "wechat_ad_bar.png"
    if _copy_frozen_wechat_asset("wechat_ad_bar.png", out, frozen_dir):
        return
    if out.exists() and not force:
        print("    ad banner: cached")
        return
    cfg = load_ad_bar_config(ad_bar_config) if ad_bar_config and ad_bar_config.exists() else None
    print("    ad banner (gpt-image-2 bg + PIL text + in-image logo zone)...")
    render_ad_banner_png(out, cfg, render_fn=render_gpt)


def generate_all_images(social_data: dict, out_dir: Path, *, force: bool = False,
                        frozen_wechat_dir: Path | None = None,
                        slide_dir: Path | None = None,
                        inline_sections: list[int] | None = None,
                        ad_bar_config: Path | None = None):
    """Generate all social images (XHS + WeChat cover/inline/ad).
    
    slide_dir: path to PPT slide images (slide_01.png … slide_06.png).
               When provided, XHS and WeChat inline images reuse slides instead
               of calling gpt-image-2 again — ensures style consistency.
    inline_sections: 1-indexed section numbers to illustrate (default [2,3,4]).
    """
    frozen = frozen_wechat_dir
    if frozen is None and FROZEN_WECHAT_DEFAULT.exists():
        frozen = FROZEN_WECHAT_DEFAULT
    generate_xhs_images(social_data, out_dir / "xhs", force=force, slide_dir=slide_dir)
    wx_dir = out_dir / "wechat"
    generate_wechat_cover(social_data, wx_dir, force=force, frozen_dir=frozen)
    generate_wechat_images(social_data, wx_dir, force=force, frozen_dir=frozen,
                           slide_dir=slide_dir, inline_sections=inline_sections)
    generate_wechat_ad_banner(wx_dir, force=force, frozen_dir=frozen, ad_bar_config=ad_bar_config)
    print(f"  All social images saved to {out_dir}")


if __name__ == "__main__":
    social_json = ROOT / "outputs" / "social_test" / "social.json"
    if social_json.exists():
        data = json.loads(social_json.read_text(encoding="utf-8"))
        generate_all_images(data, ROOT / "outputs" / "social_test" / "images")
    else:
        print("Run social_content.py first to generate social.json")
