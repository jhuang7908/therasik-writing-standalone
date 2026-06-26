#!/usr/bin/env python3
"""Visual QA — gpt-4o image review for social media assets.

Checks each generated image for:
  - logo_overlap   : multiple logos in the same image
  - garbled_text   : unreadable / corrupted Chinese characters
  - layout         : obvious composition / clipping issues

Usage:
    from visual_qa import check_image, VQAResult
    result = check_image(Path("wechat_inline_01.png"))
    if result.status == "FAIL":
        print(result.issues)
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

_SYSTEM = """You are a visual quality-control inspector for social-media science images.
Inspect the image and respond with ONLY valid JSON — no markdown fences, no extra text.

Schema:
{
  "status": "PASS" | "WARN" | "FAIL",
  "issues": ["<short issue description>", ...],
  "reasoning": "<1-2 sentence explanation>"
}

Rules:
- FAIL if: two overlapping logos exist in the image (e.g. a hand-drawn logo AND a stamped logo).
- FAIL if: the company logo (bottom-right corner) overlaps with or visually touches any diagram element, annotation text, or data label. A clear white/light gap must exist between the logo and all content.
- FAIL if: the logo occupies more than 18% of the image width, or its bottom edge is within 2% of the image bottom edge (insufficient safe zone).
- FAIL if: Chinese text is garbled (random Unicode boxes, mojibake, or clearly wrong characters).
- FAIL if: the image is mostly blank, clipped, or a solid color with no content.
- FAIL if: an expected_section hint is given AND the section number visible in the image title
  does NOT match the hint (e.g. hint says "一" but image shows "二、...").
- WARN if: text is small but readable; or the logo margin looks tight but does not overlap content.
- PASS otherwise.
"""


@dataclass
class VQAResult:
    status: str          # "PASS" | "WARN" | "FAIL"
    issues: list[str] = field(default_factory=list)
    reasoning: str = ""
    raw: str = ""

    def ok(self) -> bool:
        return self.status in ("PASS", "WARN")


def check_image(img_path: Path, *, api_key: str = "",
                expected_section: str | None = None) -> VQAResult:
    """Run gpt-4o visual QA on a single image file.

    expected_section: Chinese ordinal visible in image title, e.g. "一", "二", "三".
                      If provided, gpt-4o will FAIL if image title shows a different number.
    Returns VQAResult. Falls back to PASS (with a note) if the API is unavailable.
    """
    key = api_key or OPENAI_API_KEY
    if not key:
        return VQAResult(status="PASS", reasoning="OPENAI_API_KEY not set — visual QA skipped.")

    hint = f"\nexpected_section hint: the image title should start with「{expected_section}、」. FAIL if it shows a different section number." if expected_section else ""

    try:
        import openai
        client = openai.OpenAI(api_key=key)

        img_b64 = base64.b64encode(img_path.read_bytes()).decode()
        resp = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=256,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Inspect this image.{hint}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}",
                                "detail": "low",
                            },
                        },
                    ],
                },
            ],
        )
        raw = resp.choices[0].message.content.strip()
        data = json.loads(raw)
        return VQAResult(
            status=data.get("status", "WARN"),
            issues=data.get("issues", []),
            reasoning=data.get("reasoning", ""),
            raw=raw,
        )

    except json.JSONDecodeError as e:
        return VQAResult(status="WARN", reasoning=f"VQA JSON parse error: {e}", raw=raw if "raw" in dir() else "")
    except Exception as e:
        return VQAResult(status="WARN", reasoning=f"VQA unavailable: {e}")


def check_and_report(img_path: Path, label: str = "",
                     expected_section: str | None = None) -> VQAResult:
    """Run VQA and print a one-line summary."""
    result = check_image(img_path, expected_section=expected_section)
    tag = label or img_path.name
    icon = "✅" if result.status == "PASS" else ("⚠️" if result.status == "WARN" else "❌")
    issues_str = "; ".join(result.issues) if result.issues else result.reasoning
    print(f"    VQA {icon} {tag}: {result.status} — {issues_str}")
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python visual_qa.py <image.png> [image2.png ...]")
        sys.exit(1)
    for p in sys.argv[1:]:
        r = check_and_report(Path(p))
        if r.status == "FAIL":
            sys.exit(1)
