#!/usr/bin/env python3

"""Strip AI audit labels + XHS compliance word substitution for publish-facing fields."""

from __future__ import annotations



import re

from typing import Any



_AI_MARKERS = [

    r"\[推断\]",

    r"〔原文未明确〕",

    r"\(原文未明确\)",

    r"原文未明确",

    r"\[verified\]",

    r"\[unverified\]",

    r"\[estimated\]",

]

_TAG_IN_BODY = re.compile(r"#\S+")



# Longer phrases first — 小红书禁借贷广告敏感词

_COMPLIANCE_REPLACEMENTS: list[tuple[str, str]] = [

    (r"商业贷款", "商业房dai"),

    (r"商业房贷", "商业房dai"),

    (r"住房贷款", "住房dai"),

    (r"房屋贷款", "房屋dai"),

    (r"抵押贷款", "抵押dai"),

    (r"按揭贷款", "按揭dai"),

    (r"房贷", "房dai"),

    (r"贷款", "dai款"),

    (r"借款广告", "理财笔记"),

    (r"立即申请", "多了解"),

    (r"私信领", "先搞懂"),

]



_AD_PHRASES = [

    r"最低利率保证",

    r"保证最低利率",

    r"秒批额度",

    r"免费领取额度",

]





def _apply_compliance(text: str) -> str:

    t = text or ""

    for pat, repl in _COMPLIANCE_REPLACEMENTS:

        t = re.sub(pat, repl, t, flags=re.IGNORECASE)

    for pat in _AD_PHRASES:

        t = re.sub(pat, "", t, flags=re.IGNORECASE)

    return t





def _clean_text(text: str) -> str:

    t = text or ""

    for pat in _AI_MARKERS:

        t = re.sub(pat, "", t)

    t = _TAG_IN_BODY.sub("", t)

    t = _apply_compliance(t)

    t = re.sub(r"[ \t]+", " ", t)

    t = re.sub(r"\n{3,}", "\n\n", t)

    return t.strip()





def deep_sanitize(val: Any) -> Any:
    if isinstance(val, dict):
        new_dict = {}
        for k, v in val.items():
            if k == "tags" and isinstance(v, list):
                cleaned_tags = []
                for t in v:
                    if isinstance(t, str):
                        tag = t.strip()
                        for pat in _AI_MARKERS:
                            tag = re.sub(pat, "", tag)
                        tag = _apply_compliance(tag)
                        if tag and not tag.startswith("#"):
                            tag = f"#{tag.lstrip('#')}"
                        if tag:
                            cleaned_tags.append(tag)
                new_dict[k] = cleaned_tags
            elif k in ("bullets", "bullet") and isinstance(v, list):
                new_dict[k] = [_clean_text(str(b)) for b in v if _clean_text(str(b))]
            else:
                new_dict[k] = deep_sanitize(v)
        return new_dict
    elif isinstance(val, list):
        return [deep_sanitize(item) for item in val]
    elif isinstance(val, str):
        return _clean_text(val)
    return val


def sanitize_xhs(xhs: dict[str, Any]) -> dict[str, Any]:
    return deep_sanitize(xhs)


def sanitize_doc(data: dict[str, Any]) -> dict[str, Any]:
    return deep_sanitize(data)

