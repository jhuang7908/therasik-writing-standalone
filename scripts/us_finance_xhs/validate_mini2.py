#!/usr/bin/env python3

"""Validate finance XHS mini (2-card) JSON."""

from __future__ import annotations



import json

import re

import sys

from pathlib import Path





def zh_chars(text: str) -> int:

    return len(re.findall(r"[\u4e00-\u9fff]", text or ""))





def validate_xhs_mini(x: dict) -> dict:

    v: list[str] = []

    cards = x.get("cards") or []

    if len(cards) != 2:

        v.append(f"卡片数={len(cards)}，要求2")

    body_n = zh_chars(x.get("body", ""))

    if not (180 <= body_n <= 320):

        v.append(f"正文汉字={body_n}，要求180-320")

    tags = x.get("tags") or []

    if len(tags) != 5:

        v.append(f"标签数={len(tags)}，要求5")

    title_n = zh_chars(x.get("title", ""))

    if title_n > 20:

        v.append(f"标题汉字={title_n}，要求≤20")

    for c in cards:

        if zh_chars(c.get("title", "")) > 15:

            v.append(f"卡片{c.get('page')}标题超长")

        cb = zh_chars(c.get("body", ""))

        if not (50 <= cb <= 120):

            v.append(f"卡片{c.get('page')}正文={cb}，要求50-120")

        bullets = c.get("bullets") or []

        if not (2 <= len(bullets) <= 4):

            v.append(f"卡片{c.get('page')} bullets={len(bullets)}，要求2-4")

    roles = [c.get("image_role") for c in cards]

    if cards and roles[0] != "cover":

        v.append("第1张须为 cover")

    if len(cards) > 1 and roles[1] != "content":

        v.append("第2张须为 content")

    return {

        "image_count": len(cards),

        "body_char_count": body_n,

        "compliance": len(v) == 0,

        "violations": v,

    }





def validate_doc(data: dict) -> dict:

    x = data.get("xiaohongshu") or data

    ann = validate_xhs_mini(x)

    if "xiaohongshu" in data:

        data["xiaohongshu"]["format_annotation"] = ann

    return {"pass": ann["compliance"], "xiaohongshu": ann}





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

