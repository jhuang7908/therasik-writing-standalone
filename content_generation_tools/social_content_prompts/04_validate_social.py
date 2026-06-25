#!/usr/bin/env python3
"""Rule-based validator for XHS + WeChat v2.0 JSON SSOT."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def zh_chars(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text or ""))


def validate_xhs(x: dict) -> dict:
    v: list[str] = []
    cards = x.get("cards") or []
    if len(cards) != 6:
        v.append(f"卡片数={len(cards)}，要求6")
    body_n = zh_chars(x.get("body", ""))
    if not (400 <= body_n <= 600):
        v.append(f"正文汉字={body_n}，要求400-600")
    tags = x.get("tags") or []
    if len(tags) != 6:
        v.append(f"标签数={len(tags)}，要求6")
    title_n = zh_chars(x.get("title", ""))
    if title_n > 20:
        v.append(f"标题汉字={title_n}，要求≤20")
    for c in cards:
        if zh_chars(c.get("title", "")) > 15:
            v.append(f"卡片{c.get('page')}标题超长")
        cb = zh_chars(c.get("body", ""))
        if not (40 <= cb <= 80):
            v.append(f"卡片{c.get('page')}正文={cb}，要求40-80")
    return {
        "image_count": len(cards),
        "body_char_count": body_n,
        "compliance": len(v) == 0,
        "violations": v,
    }


def validate_wechat(w: dict) -> dict:
    v: list[str] = []
    secs = w.get("sections") or []
    if len(secs) != 5:
        v.append(f"章节数={len(secs)}，要求5")
    lead = zh_chars(w.get("lead", ""))
    if not (100 <= lead <= 150):
        v.append(f"导语汉字={lead}，要求100-150")
    closing = zh_chars(w.get("closing", ""))
    if not (80 <= closing <= 120):
        v.append(f"结语汉字={closing}，要求80-120")
    total = lead + sum(zh_chars(s.get("body", "")) for s in secs) + closing
    if not (1500 <= total <= 2000):
        v.append(f"总汉字={total}，要求1500-2000")
    img_n = 1 if w.get("hero_image") else 0
    for s in secs:
        if s.get("inline_image"):
            img_n += 1
    if img_n != 3:
        v.append(f"配图数={img_n}，要求3")
    return {
        "image_count": img_n,
        "total_char_count": total,
        "compliance": len(v) == 0,
        "violations": v,
    }


def validate_doc(data: dict) -> dict:
    out = {"format_version": data.get("format_version"), "platforms": {}}
    if "xiaohongshu" in data:
        ann = validate_xhs(data["xiaohongshu"])
        data["xiaohongshu"]["format_annotation"] = ann
        out["platforms"]["xiaohongshu"] = ann
    if "wechat" in data:
        ann = validate_wechat(data["wechat"])
        data["wechat"]["format_annotation"] = ann
        out["platforms"]["wechat"] = ann
    out["pass"] = all(p.get("compliance") for p in out["platforms"].values())
    return out


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "")
    if not path.exists():
        print(f"Missing file: {path}")
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    report = validate_doc(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("pass") else 2


if __name__ == "__main__":
    raise SystemExit(main())
