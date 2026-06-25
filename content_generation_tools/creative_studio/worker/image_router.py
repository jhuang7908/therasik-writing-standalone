"""Image Router — resolves each block's visual.prompt_zh into an image URL.

Tier hierarchy (cheapest → premium):
  template_only  No AI generation; keep template placeholder image.
  stock          Return a royalty-free stock placeholder (no API call, free).
  standard       GPT-Image-1 / DALL-E 3 (good quality, reasonable cost).
  premium        GPT-Image-2 (best quality + best Chinese prompt handling).

Auto tier selection:
  - doc_type="xiaohongshu" → premium (visuals are the product)
  - doc_type="ppt"         → standard (1 hero image per slide)
  - doc_type="whitepaper"  → stock or standard
  - block.visual.tier overrides the default
"""
from __future__ import annotations

import base64
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Optional

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Local output path for dev; production uses S3 upload
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs" / "images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Fallback stock placeholder (a solid grey PNG, base64)
_STOCK_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9Q"
    "DwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

DOC_TYPE_DEFAULTS = {
    "xiaohongshu": "premium",
    "ppt":         "standard",
    "wechat":      "standard",
    "whitepaper":  "stock",
}


def _tier_for_block(block: dict, doc_type: str, override: Optional[str]) -> str:
    if override and override != "auto":
        return override
    vis = block.get("visual") or {}
    block_tier = vis.get("tier")
    if block_tier and block_tier in ("template_only", "stock", "standard", "premium"):
        return block_tier
    return DOC_TYPE_DEFAULTS.get(doc_type, "standard")


# ---------- generation backends ----------

def _gen_gpt_image_2(prompt: str) -> bytes:
    """Generate with gpt-image-2 (best Chinese support)."""
    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.images.generate(
        model="gpt-image-2",
        prompt=prompt,
        n=1,
        size="1024x1024",
    )
    item = resp.data[0]
    if getattr(item, "b64_json", None):
        return base64.b64decode(item.b64_json)
    # Download URL
    import httpx
    return httpx.get(item.url, timeout=30).content


def _gen_gpt_image_1(prompt: str) -> bytes:
    """Generate with DALL-E 3 / gpt-image-1 (standard tier)."""
    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        n=1,
        size="1024x1024",
    )
    item = resp.data[0]
    if getattr(item, "b64_json", None):
        return base64.b64decode(item.b64_json)
    import httpx
    return httpx.get(item.url, timeout=30).content


def _stock_placeholder() -> bytes:
    return base64.b64decode(_STOCK_B64)


# ---------- save helper ----------

def _save_image(img_bytes: bytes, name: str) -> str:
    """Save to local outputs/images/ and return file path (or S3 URL in prod)."""
    out_path = OUTPUT_DIR / f"{name}.png"
    out_path.write_bytes(img_bytes)
    return str(out_path)


# ---------- main entrypoint ----------

def resolve_images(content_doc: dict, doc_type: str,
                   image_tier_override: Optional[str] = None) -> dict:
    """Iterate all blocks with visual.prompt_zh, generate/resolve images.

    Adds visual.resolved = {"url": <path_or_url>, "tier_used": <tier>}
    to each resolved block. Mutates and returns content_doc in-place.

    Credit cost estimate added to _meta.image_credits.
    """
    TIER_CREDITS = {"template_only": 0, "stock": 0, "standard": 10, "premium": 20}
    total_image_credits = 0

    for block in content_doc.get("blocks", []):
        vis = block.get("visual")
        if not vis:
            continue
        prompt = vis.get("prompt_zh") or vis.get("prompt_en", "")
        if not prompt:
            continue

        tier = _tier_for_block(block, doc_type, image_tier_override)
        name = f"{content_doc.get('meta', {}).get('doc_id', 'doc')}_{block.get('block_id', uuid.uuid4().hex[:8])}"
        img_bytes: Optional[bytes] = None

        try:
            if tier == "template_only":
                vis["resolved"] = {"url": None, "tier_used": "template_only"}
                continue
            elif tier == "stock":
                img_bytes = _stock_placeholder()
            elif tier == "standard":
                img_bytes = _gen_gpt_image_1(prompt)
            elif tier == "premium":
                img_bytes = _gen_gpt_image_2(prompt)
        except Exception as exc:
            logger.warning("Image generation failed (tier=%s): %s. Falling back to stock.", tier, exc)
            # Degrade gracefully
            try:
                img_bytes = _gen_gpt_image_1(prompt)
                tier = "standard"
            except Exception:
                img_bytes = _stock_placeholder()
                tier = "stock"

        path = _save_image(img_bytes, name)
        vis["resolved"] = {"url": path, "tier_used": tier}
        total_image_credits += TIER_CREDITS.get(tier, 10)

    meta = content_doc.setdefault("_meta", {})
    meta["image_credits"] = total_image_credits
    return content_doc
