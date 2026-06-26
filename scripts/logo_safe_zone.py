#!/usr/bin/env python3
"""Place brand logo inside image canvas — reserved empty zone, no text/pattern overlap."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Tuple

# (x0, y0, x1, y1) as fractions of width/height
ZoneFrac = Tuple[float, float, float, float]

COVER_LOGO_ZONE: ZoneFrac = (0.70, 0.74, 0.98, 0.96)
AD_LOGO_ZONE: ZoneFrac = (0.57, 0.66, 0.96, 0.94)


def _zone_pixels(w: int, h: int, zone: ZoneFrac) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = zone
    return int(w * x0), int(h * y0), int(w * x1), int(h * y1)


def prepare_logo_rgba(logo_path: Path):
    from PIL import Image

    logo = Image.open(logo_path).convert("RGBA")
    datas = logo.getdata()
    newData = []
    for item in datas:
        r, g, b, a = item
        # If it is close to black, make it transparent with a soft edge to prevent jagged halos
        if r < 40 and g < 40 and b < 40:
            newData.append((0, 0, 0, 0))
        elif r < 60 and g < 60 and b < 60:
            avg = (r + g + b) / 3
            alpha = int((avg - 40) / 20 * 255)
            newData.append((r, g, b, max(0, min(255, alpha))))
        else:
            newData.append(item)
    logo.putdata(newData)
    return logo


def place_logo_in_zone(
    img,
    logo_path: Path,
    zone: ZoneFrac,
    *,
    fill_rgb: tuple[int, int, int] = (240, 253, 250),
    with_box: bool = False,
):
    """Wipe patterns in zone, center logo inside — stays within full canvas, seamless without border."""
    from PIL import Image, ImageDraw

    base = img.convert("RGBA")
    w, h = base.size
    zx0, zy0, zx1, zy1 = _zone_pixels(w, h, zone)
    pad = max(4, int(min(zx1 - zx0, zy1 - zy0) * 0.06))
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    if with_box:
        draw.rounded_rectangle(
            (zx0, zy0, zx1, zy1),
            radius=max(8, pad),
            fill=(*fill_rgb, 252),
            outline=(13, 148, 136, 90),
            width=1,
        )
    else:
        # Seamless integration: fill the zone with a feathered, semi-transparent background color
        # to clear any background textures/lines, but do NOT draw any outline/border!
        # This keeps the logo integrated with zero pattern overlap.
        draw.rounded_rectangle(
            (zx0, zy0, zx1, zy1),
            radius=max(8, pad),
            fill=(*fill_rgb, 230),  # Soft alpha fill to fade background patterns
            outline=(0, 0, 0, 0),
            width=0,
        )

    base = Image.alpha_composite(base, overlay)

    logo = prepare_logo_rgba(logo_path)
    zw, zh = zx1 - zx0 - 2 * pad, zy1 - zy0 - 2 * pad
    lw = zw
    lh = int(logo.height * lw / max(logo.width, 1))
    if lh > zh:
        lh = zh
        lw = int(logo.width * lh / max(logo.height, 1))
    logo = logo.resize((lw, lh), Image.LANCZOS)
    lx = zx0 + pad + (zw - lw) // 2
    ly = zy0 + pad + (zh - lh) // 2
    base.paste(logo, (lx, ly), mask=logo)
    return base.convert("RGB")


def place_logo_in_zone_bytes(
    img_bytes: bytes,
    logo_path: Path,
    zone: ZoneFrac,
) -> bytes:
    from PIL import Image

    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    if not logo_path.exists():
        return img_bytes
    out = place_logo_in_zone(img, logo_path, zone)
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
