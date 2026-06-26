#!/usr/bin/env python3
"""Render by tier + visual_role (hybrid: cogview / seedream / gpt-image-2)."""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CG = ROOT / "content_generation_tools"

try:
    from dotenv import load_dotenv

    load_dotenv(CG / ".env")
except ImportError:
    pass

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

NO_TEXT_SUFFIX = (
    "禁止任何文字、字母、数字、假拉丁文；仅插画与色块留白；所有文案由后期排版叠加。"
)

ARK_DEFAULT_BASE = "https://ark.cn-beijing.volces.com/api/v3/images/generations"

# OpenAI 风格像素 → 方舟 Seedream size 档位
SEEDREAM_SIZE_MAP = {
    "1024x1024": "1K",
    "1024x1536": "2K",
    "1536x1024": "2K",
}


def load_renderer_config() -> dict:
    path = CG / "renderer_backends.yaml"
    if yaml is None:
        raise RuntimeError("pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def resolve_visual_quality(
    cfg: dict,
    *,
    visual_quality: str | None = None,
    product: str | None = None,
    tier: str | None = None,
) -> dict:
    qmap = cfg.get("image_quality_tiers", {})
    if product:
        pq = cfg.get("product_quality_map", {}).get(product)
        if pq and pq in qmap:
            visual_quality = pq
    if tier and not visual_quality:
        tcfg = cfg.get("tiers", {}).get(tier, {})
        visual_quality = tcfg.get("visual_quality")
    visual_quality = visual_quality or cfg.get("default_visual_quality", "medium")
    if visual_quality not in qmap:
        visual_quality = "medium"
    return dict(qmap[visual_quality]) | {"id": visual_quality}


def resolve_role(cfg: dict, role: str, tier: str) -> dict:
    hybrid = cfg.get("hybrid_render", {})
    roles = hybrid.get("visual_roles", {})
    tier_cfg = cfg.get("tiers", {}).get(tier, {})
    if role in roles:
        r = dict(roles[role])
        r["renderer"] = r.get("renderer", "cogview-4")
        if role == "text_hero":
            r["quality"] = tier_cfg.get("gpt_image_quality") or r.get("default_quality", "low")
            r["size"] = tier_cfg.get("gpt_image_size") or r.get("sizes", {}).get("low_cost", "1024x1024")
        return r
    return {"renderer": "cogview-4", "prompt_suffix": NO_TEXT_SUFFIX}


def _download_image(url: str, out: Path) -> None:
    import urllib.request

    urllib.request.urlretrieve(url, out)


def _save_b64(b64: str, out: Path) -> None:
    out.write_bytes(base64.b64decode(b64))


def to_seedream_size(size: str) -> str:
    s = size.strip()
    if s.upper().endswith("K") or "x" not in s:
        return s
    return SEEDREAM_SIZE_MAP.get(s.lower(), "2K")


def render_cogview(prompt: str, size: str, out: Path, suffix: str = "") -> dict:
    from zhipuai import ZhipuAI

    key = os.environ.get("ZHIPU_API_KEY", "")
    if not key:
        raise RuntimeError("ZHIPU_API_KEY missing in content_generation_tools/.env")

    full_prompt = f"{prompt.strip()} {suffix or NO_TEXT_SUFFIX}".strip()
    client = ZhipuAI(api_key=key)
    resp = client.images.generations(
        model="cogview-4-250304",
        prompt=full_prompt,
        size=size if "x" in size else "1024x1024",
    )
    item = resp.data[0]
    if getattr(item, "b64_json", None):
        _save_b64(item.b64_json, out)
        source = "b64"
    elif getattr(item, "url", None):
        _download_image(item.url, out)
        source = "url"
    else:
        raise RuntimeError("CogView response has no image data")

    return {
        "backend": "cogview-4",
        "model": "cogview-4-250304",
        "size": size,
        "source": source,
        "path": str(out),
        "role": "illustration",
    }


def render_seedream(
    prompt: str,
    size: str,
    out: Path,
    *,
    model: str = "doubao-seedream-4-5-251128",
    suffix: str = "",
    sequential: str = "disabled",
    watermark: bool = False,
    response_format: str = "url",
) -> dict:
    import requests

    key = (
        os.environ.get("ARK_API_KEY")
        or os.environ.get("VOLC_SPEECH_API_KEY")
        or os.environ.get("VOLC_ACCESS_KEY", "")
    )
    if not key:
        raise RuntimeError("ARK_API_KEY missing in content_generation_tools/.env")

    api_base = os.environ.get("ARK_API_BASE", ARK_DEFAULT_BASE)
    full_prompt = f"{prompt.strip()} {suffix}".strip() if suffix else prompt.strip()
    seedream_size = to_seedream_size(size)

    payload = {
        "model": model,
        "prompt": full_prompt,
        "sequential_image_generation": sequential,
        "response_format": response_format,
        "size": seedream_size,
        "stream": False,
        "watermark": watermark,
    }

    resp = requests.post(
        api_base,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        json=payload,
        timeout=180,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Seedream HTTP {resp.status_code}: {resp.text[:500]}")

    body = resp.json()
    items = body.get("data") or []
    if not items:
        raise RuntimeError(f"Seedream empty data: {json.dumps(body, ensure_ascii=False)[:500]}")

    paths: list[str] = []
    for i, item in enumerate(items):
        target = out if len(items) == 1 else out.with_name(f"{out.stem}_{i + 1:02d}{out.suffix}")
        if item.get("b64_json"):
            _save_b64(item["b64_json"], target)
        elif item.get("url"):
            _download_image(item["url"], target)
        else:
            raise RuntimeError("Seedream item has no url/b64_json")
        paths.append(str(target))

    usage = body.get("usage", {})
    return {
        "backend": "seedream",
        "model": model,
        "size": seedream_size,
        "sequential_image_generation": sequential,
        "watermark": watermark,
        "source": response_format,
        "path": paths[0],
        "paths": paths,
        "count": len(paths),
        "usage": usage,
        "cny_est": round(0.25 * len(paths), 2) if "4-5" in model else None,
    }


def render_gemini_image(
    prompt: str,
    out: Path,
    *,
    model: str = "gemini-2.5-flash-image",
    suffix: str = "",
    image_size: str | None = None,
) -> dict:
    """Gemini native image (Nano Banana / Nano Banana Pro).

    image_size: optional Nano Banana Pro resolution tier ("1K" / "2K" / "4K").
    When None, the API default is used (preserves prior behavior).
    """
    import requests

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing in content_generation_tools/.env")

    full_prompt = f"{prompt.strip()} {suffix}".strip() if suffix else prompt.strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    gen_cfg: dict = {"responseModalities": ["IMAGE"]}
    if image_size:
        size_norm = image_size.strip().upper()
        if size_norm in ("1K", "2K", "4K"):
            gen_cfg["imageConfig"] = {"imageSize": size_norm}
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": gen_cfg,
    }
    resp = requests.post(
        url,
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json=payload,
        timeout=180,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Gemini image HTTP {resp.status_code}: {resp.text[:500]}")

    body = resp.json()
    parts = (body.get("candidates") or [{}])[0].get("content", {}).get("parts") or []
    inline = None
    for part in parts:
        if "inlineData" in part:
            inline = part["inlineData"]
            break
        if "inline_data" in part:
            inline = part["inline_data"]
            break
    if not inline or not inline.get("data"):
        raise RuntimeError(f"Gemini image empty response: {json.dumps(body, ensure_ascii=False)[:400]}")

    out.parent.mkdir(parents=True, exist_ok=True)
    _save_b64(inline["data"], out)
    return {
        "backend": "gemini-image",
        "model": model,
        "image_size": (image_size or "default"),
        "source": "b64",
        "path": str(out),
        "role": "text_hero",
    }


def render_gpt_image(
    prompt: str, size: str, model: str, out: Path, quality: str | None = None, suffix: str = ""
) -> dict:
    from openai import OpenAI

    # Automatically map the virtual model "gpt-image-2" to the actual API model using renderer_backends.yaml
    if model == "gpt-image-2":
        try:
            cfg = load_renderer_config()
            models_map = cfg.get("backends", {}).get("gpt-image-2", {}).get("models", {})
            if quality == "high":
                model = models_map.get("high") or "gpt-image-2"
            elif quality == "low":
                model = models_map.get("economy") or "gpt-image-1-mini"
            else:
                model = models_map.get("medium") or "gpt-image-2"
        except Exception:
            if quality == "high":
                model = "gpt-image-2"
            elif quality == "low":
                model = "gpt-image-1-mini"
            else:
                model = "gpt-image-2"

    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY missing in content_generation_tools/.env")

    full_prompt = f"{prompt.strip()} {suffix}".strip() if suffix else prompt.strip()
    client = OpenAI(api_key=key)
    kwargs: dict = {
        "model": model,
        "prompt": full_prompt,
        "n": 1,
        "size": size if "x" in size else "1024x1024",
    }
    if quality:
        kwargs["quality"] = quality
    elif model.startswith("gpt-image-2") or model.startswith("gpt-image-1"):
        kwargs["quality"] = "medium"

    resp = client.images.generate(**kwargs)
    item = resp.data[0]
    if getattr(item, "b64_json", None):
        _save_b64(item.b64_json, out)
        source = "b64"
    elif getattr(item, "url", None):
        _download_image(item.url, out)
        source = "url"
    else:
        raise RuntimeError("gpt-image response has no image data")

    return {
        "backend": "gpt-image-2",
        "model": model,
        "size": size,
        "quality": quality,
        "source": source,
        "path": str(out),
        "role": "text_hero",
    }


def _try_openai_backup(
    prompt: str,
    size: str,
    out: Path,
    vq: dict,
    suffix: str,
    model: str,
) -> dict:
    quality = vq.get("gpt_image_quality", "medium")
    result = render_gpt_image(prompt, size, model, out, quality=quality, suffix=suffix)
    result["backup"] = True
    result["visual_quality"] = vq.get("id")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Content Studio hybrid renderer")
    parser.add_argument("--tier", choices=["draft", "pro", "pro_hybrid", "premium"], default="pro")
    parser.add_argument(
        "--visual-quality",
        choices=["low", "medium", "high"],
        default=None,
        help="客户画质档：low草图 medium社交/PPT high海报/出版物",
    )
    parser.add_argument(
        "--product",
        choices=[
            "internal_draft",
            "ppt",
            "xiaohongshu",
            "wechat",
            "whitepaper",
            "product_catalog",
            "commercial_poster",
            "publication",
            "ppt_voice",
        ],
        default=None,
        help="按产品自动选 visual-quality",
    )
    parser.add_argument(
        "--fallback-openai",
        action="store_true",
        help="主引擎失败时用 OpenAI gpt-image-2 备份（需有额度）",
    )
    parser.add_argument(
        "--role",
        choices=["illustration", "text_hero", "full_page_premium", "auto"],
        default="auto",
    )
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--size", default=None, help="1024x1024 | 1024x1536 | 2K | 1K")
    parser.add_argument("--quality", choices=["low", "medium", "high"], default=None)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "render_test" / "image.png")
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--renderer",
        choices=["cogview-4", "seedream", "gpt-image-2", "gemini-image", "nano-banana-pro-2k", "nano_banana_pro_2k", "auto"],
        default="auto",
    )
    parser.add_argument(
        "--sequential",
        choices=["disabled", "auto"],
        default="disabled",
        help="Seedream: disabled=单图, auto=组图",
    )
    parser.add_argument("--watermark", action="store_true", help="Seedream 保留水印（默认关）")
    args = parser.parse_args()

    cfg = load_renderer_config()
    tier_cfg = cfg["tiers"].get(args.tier, cfg["tiers"]["pro"])
    vq = resolve_visual_quality(
        cfg, visual_quality=args.visual_quality, product=args.product, tier=args.tier
    )

    if args.role == "auto":
        role = "illustration"
        if args.renderer in ("gpt-image-2", "gemini-image", "nano-banana-pro-2k", "nano_banana_pro_2k"):
            role = "text_hero"
        elif args.renderer == "seedream":
            role = "text_hero"
    else:
        role = args.role

    role_cfg = resolve_role(cfg, role, args.tier)
    renderer = args.renderer if args.renderer != "auto" else role_cfg.get("renderer", "cogview-4")
    size = args.size or vq.get("gpt_image_size") or role_cfg.get("size") or "1024x1024"
    suffix = role_cfg.get("prompt_suffix", "")
    gpt_model = args.model or cfg["backends"]["gpt-image-2"]["models"].get("medium") or "gpt-image-2"
    gpt_quality = args.quality or vq.get("gpt_image_quality") or tier_cfg.get("gpt_image_quality") or "medium"

    args.out.parent.mkdir(parents=True, exist_ok=True)

    try:
        if renderer == "cogview-4":
            result = render_cogview(args.prompt, size, args.out, suffix=suffix or NO_TEXT_SUFFIX)
        elif renderer == "seedream":
            sd_cfg = cfg.get("backends", {}).get("seedream", {})
            default_model = (
                sd_cfg.get("models", {}).get("standard_45", {}).get("endpoint_id")
                or "doubao-seedream-4-5-251128"
            )
            model = args.model or default_model
            if role == "illustration":
                suffix = suffix or NO_TEXT_SUFFIX
            result = render_seedream(
                args.prompt,
                size,
                args.out,
                model=model,
                suffix=suffix,
                sequential=args.sequential,
                watermark=args.watermark,
            )
            result["role"] = role
        elif renderer in ("gemini-image", "nano-banana-pro-2k", "nano_banana_pro_2k"):
            model = args.model or "gemini-3-pro-image-preview"
            result = render_gemini_image(args.prompt, args.out, model=model, suffix=suffix)
            result["role"] = role
        else:
            result = render_gpt_image(
                args.prompt, size, gpt_model, args.out, quality=gpt_quality, suffix=suffix
            )
    except Exception as primary_exc:
        # Fallback to Gemini (Nano Banana Pro 2K) if gpt-image-2 fails (e.g. billing limit)
        if renderer == "gpt-image-2":
            try:
                result = render_gemini_image(args.prompt, args.out, model="gemini-3-pro-image-preview", suffix=suffix)
                result["role"] = role
                result["primary_error"] = str(primary_exc)
                result["fallback_used"] = "gemini-image"
                result["tier"] = args.tier
                result["visual_quality"] = vq.get("id")
                result["strategy"] = tier_cfg.get("strategy", "hybrid")
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0
            except Exception as gemini_exc:
                pass
        
        backup_cfg = cfg.get("openai_backup", {})
        if not args.fallback_openai or not backup_cfg.get("enabled"):
            raise
        result = _try_openai_backup(
            args.prompt, size, args.out, vq, suffix, gpt_model
        )
        result["primary_error"] = str(primary_exc)

    result["tier"] = args.tier
    result["visual_quality"] = vq.get("id")
    result["strategy"] = tier_cfg.get("strategy", "hybrid")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
