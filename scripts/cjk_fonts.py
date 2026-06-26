#!/usr/bin/env python3
"""Cross-platform Chinese font for PIL (Windows + Linux CI)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (bold_path, regular_path) — first match wins
_FONT_PAIRS: list[tuple[str, str]] = [
    (
        str(ROOT / "assets" / "fonts" / "NotoSansSC-Bold.otf"),
        str(ROOT / "assets" / "fonts" / "NotoSansSC-Regular.otf"),
    ),
    (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ),
    (
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ),
    ("C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc"),
    ("C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc"),
]


def cjk_font(size: int, *, bold: bool = False):
    """Load a CJK-capable TrueType font; raises if only bitmap default available."""
    from PIL import ImageFont

    for bold_path, regular_path in _FONT_PAIRS:
        path = bold_path if bold else regular_path
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    raise RuntimeError(
        "No CJK font found. Install fonts-noto-cjk (Linux) or add assets/fonts/NotoSansSC-*.otf"
    )
