"""ContentDoc — Pydantic v2 models for Creative Studio (protocol v0.1).

This is the typed, validated mirror of ``content_doc.schema.json``. The
renderer and the LLM/image routers all exchange ``ContentDoc`` instances.

Usage::

    from content_doc import ContentDoc
    doc = ContentDoc.model_validate_json(raw_json)   # validates
    doc = ContentDoc.model_validate(dict_payload)
    payload = doc.model_dump(exclude_none=True)
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class DocType(str, Enum):
    ppt = "ppt"
    xiaohongshu = "xiaohongshu"
    wechat = "wechat"
    whitepaper = "whitepaper"


class DocStatus(str, Enum):
    draft = "draft"
    rendered = "rendered"
    failed = "failed"


class Layout(str, Enum):
    cover = "cover"
    section = "section"
    title_bullets = "title_bullets"
    two_column = "two_column"
    image_left = "image_left"
    image_right = "image_right"
    big_number = "big_number"
    quote = "quote"
    card = "card"
    chapter = "chapter"


class VisualRole(str, Enum):
    background = "background"
    illustration = "illustration"
    hero = "hero"
    texture = "texture"
    icon = "icon"


class AspectRatio(str, Enum):
    r16_9 = "16:9"
    r3_4 = "3:4"
    r4_3 = "4:3"
    r1_1 = "1:1"
    r9_16 = "9:16"
    a4 = "a4"


class Tier(str, Enum):
    template_only = "template_only"
    stock = "stock"
    standard = "standard"
    premium = "premium"


class Provider(str, Enum):
    template_only = "template_only"
    stock = "stock"
    flux = "flux"
    sdxl = "sdxl"
    qwen = "qwen"
    jimeng = "jimeng"
    gpt_image_2 = "gpt_image_2"


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
_HEX = r"^#[0-9A-Fa-f]{6}$"


class Meta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    generated_at: datetime
    status: DocStatus = DocStatus.draft
    llm_model: Optional[str] = None
    request_summary: Optional[str] = None
    credit_estimate: Optional[int] = Field(default=None, ge=0)


class Brand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    primary_color: Optional[str] = Field(default=None, pattern=_HEX)
    secondary_color: Optional[str] = Field(default=None, pattern=_HEX)
    font_family: Optional[str] = None
    logo_asset_id: Optional[str] = None


class Text(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = None
    subtitle: Optional[str] = None
    body: Optional[str] = None
    caption: Optional[str] = None
    tag: Optional[str] = None


class Resolved(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Provider
    asset_id: Optional[str] = None
    asset_url: Optional[str] = None
    credit_cost: Optional[int] = Field(default=None, ge=0)
    cached: Optional[bool] = None


class Visual(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: str
    role: VisualRole
    aspect_ratio: AspectRatio
    preferred_tier: Tier
    prompt_en: Optional[str] = None
    negative: Optional[str] = None
    resolved: Optional[Resolved] = None


class Block(BaseModel):
    model_config = ConfigDict(extra="forbid")
    block_id: str
    layout: Layout
    text: Text
    visual: Optional[Visual] = None
    bullets: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ContentDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "0.1"
    doc_type: DocType
    meta: Meta
    blocks: List[Block] = Field(min_length=1)
    locale: str = "zh-CN"
    template_id: Optional[str] = None
    brand: Optional[Brand] = None


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if target is None:
        print("usage: python content_doc.py <content_doc.json>")
        raise SystemExit(2)
    doc = ContentDoc.model_validate_json(target.read_text(encoding="utf-8"))
    print(f"OK  doc_type={doc.doc_type.value}  blocks={len(doc.blocks)}")
    print(json.dumps(doc.model_dump(mode="json", exclude_none=True),
                     ensure_ascii=False, indent=2)[:400] + " ...")
