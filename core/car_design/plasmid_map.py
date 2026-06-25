"""
Circular plasmid map SVG generator for CAR constructs.

Generates a publication-quality circular SVG showing all construct features
(promoter, CAR domains, linkers, payload, safety switch, regulatory elements)
as colored arcs on a circular backbone.
"""
from __future__ import annotations

import math
from typing import Any

_CATEGORY_COLORS: dict[str, str] = {
    "Promoter": "#0d9488",
    "Signal Peptide": "#94a3b8",
    "Antigen Binder": "#2563eb",
    "Hinge & Spacer": "#f59e0b",
    "Transmembrane Domain": "#8b5cf6",
    "Costimulatory Domain": "#3b82f6",
    "Primary Signaling Domain": "#dc2626",
    "Linker & Peptide": "#d1d5db",
    "Safety Switch": "#ef4444",
    "Engineering Module": "#ec4899",
    "Armored Payload": "#f97316",
    "Secreted Payload": "#f97316",
    "Regulatory Element": "#6b7280",
    "Logic Gate & Switch": "#7c3aed",
}

_VECTOR_BACKBONE: dict[str, dict[str, Any]] = {
    "lentiviral_LV": {
        "name": "Lentiviral Vector",
        "backbone_features": [
            {"name": "5' LTR", "size_bp": 600},
            {"name": "Ψ packaging", "size_bp": 350},
            {"name": "RRE", "size_bp": 800},
            {"name": "cPPT", "size_bp": 120},
        ],
        "tail_features": [
            {"name": "WPRE", "size_bp": 600},
            {"name": "3' SIN-LTR", "size_bp": 400},
        ],
        "total_backbone_bp": 4500,
    },
    "gamma_retroviral_RV": {
        "name": "γ-Retroviral Vector",
        "backbone_features": [
            {"name": "5' LTR", "size_bp": 550},
            {"name": "Ψ+", "size_bp": 300},
        ],
        "tail_features": [
            {"name": "3' LTR", "size_bp": 550},
        ],
        "total_backbone_bp": 3500,
    },
    "sleeping_beauty_SB": {
        "name": "Sleeping Beauty Transposon",
        "backbone_features": [
            {"name": "IR/DR-L", "size_bp": 230},
        ],
        "tail_features": [
            {"name": "IR/DR-R", "size_bp": 230},
            {"name": "polyA", "size_bp": 250},
        ],
        "total_backbone_bp": 3000,
    },
    "mRNA_LNP": {
        "name": "mRNA (LNP-delivered)",
        "backbone_features": [
            {"name": "5' cap + UTR", "size_bp": 80},
        ],
        "tail_features": [
            {"name": "3' UTR + polyA", "size_bp": 200},
        ],
        "total_backbone_bp": 500,
    },
}


def _polar(cx: float, cy: float, r: float, angle_deg: float) -> tuple[float, float]:
    rad = math.radians(angle_deg - 90)
    return cx + r * math.cos(rad), cy + r * math.sin(rad)


def _arc_path(cx: float, cy: float, r: float, start_deg: float, end_deg: float) -> str:
    span = end_deg - start_deg
    large = 1 if span > 180 else 0
    x1, y1 = _polar(cx, cy, r, start_deg)
    x2, y2 = _polar(cx, cy, r, end_deg)
    return f"M {x1:.1f},{y1:.1f} A {r},{r} 0 {large} 1 {x2:.1f},{y2:.1f}"


def _label_pos(cx: float, cy: float, r: float, mid_deg: float, offset: float = 0) -> tuple[float, float, str]:
    x, y = _polar(cx, cy, r + offset, mid_deg)
    anchor = "start" if 0 < mid_deg < 180 else "end" if 180 < mid_deg < 360 else "middle"
    return x, y, anchor


class PlasmidMapGenerator:
    """Generate circular SVG plasmid maps from CAR element lists."""

    def __init__(self, library_idx: dict[str, dict]):
        self._lib = library_idx

    def generate_svg(
        self,
        element_ids: list[str],
        vector_type: str = "lentiviral_LV",
        construct_name: str = "CAR Construct",
        width: int = 600,
        height: int = 600,
    ) -> str:
        cx, cy = width / 2, height / 2
        backbone_r = min(width, height) * 0.32
        feature_r = backbone_r + 14
        label_r = backbone_r + 40

        segments = self._build_segments(element_ids, vector_type)
        total_bp = sum(s["size_bp"] for s in segments)

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'style="font-family:Inter,Helvetica,Arial,sans-serif;background:#fff;">',
            '<defs>',
            f'  <filter id="fs"><feDropShadow dx="0" dy="1" stdDeviation="2" flood-opacity=".08"/></filter>',
            '</defs>',
        ]

        svg_parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{backbone_r}" '
            f'fill="none" stroke="#d1d5db" stroke-width="3"/>'
        )

        angle = 0.0
        for seg in segments:
            span = (seg["size_bp"] / total_bp) * 360
            if span < 0.5:
                angle += span
                continue

            end_angle = angle + span
            color = seg.get("color", "#94a3b8")

            path = _arc_path(cx, cy, feature_r, angle, end_angle)
            svg_parts.append(
                f'<path d="{path}" fill="none" stroke="{color}" stroke-width="10" '
                f'stroke-linecap="round" opacity="0.85" filter="url(#fs)"/>'
            )

            mid = angle + span / 2
            lx, ly, anchor = _label_pos(cx, cy, label_r, mid, offset=8)

            display_name = seg["name"]
            if len(display_name) > 18:
                display_name = display_name[:16] + "…"

            font_size = 8.5 if span > 15 else 7 if span > 8 else 0
            if font_size > 0:
                rotation = mid if 90 < mid < 270 else mid
                if 90 < mid < 270:
                    rotation = mid + 180
                    anchor = {"start": "end", "end": "start"}.get(anchor, anchor)

                svg_parts.append(
                    f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
                    f'font-size="{font_size}" fill="#374151" '
                    f'transform="rotate({rotation:.1f},{lx:.1f},{ly:.1f})">'
                    f'{display_name}</text>'
                )

            angle = end_angle

        svg_parts.append(
            f'<text x="{cx}" y="{cy - 10}" text-anchor="middle" '
            f'font-size="13" font-weight="700" fill="#111827">{construct_name}</text>'
        )
        svg_parts.append(
            f'<text x="{cx}" y="{cy + 8}" text-anchor="middle" '
            f'font-size="11" fill="#6b7280">{total_bp:,} bp</text>'
        )

        vec_data = _VECTOR_BACKBONE.get(vector_type, {})
        vec_name = vec_data.get("name", vector_type)
        svg_parts.append(
            f'<text x="{cx}" y="{cy + 24}" text-anchor="middle" '
            f'font-size="9" fill="#9ca3af">{vec_name}</text>'
        )

        legend_y = height - 70
        legend_x = 20
        cats_seen: dict[str, str] = {}
        for seg in segments:
            cat = seg.get("category", "")
            if cat and cat not in cats_seen:
                cats_seen[cat] = seg.get("color", "#94a3b8")
        for i, (cat, color) in enumerate(list(cats_seen.items())[:8]):
            x = legend_x + (i % 4) * 145
            y = legend_y + (i // 4) * 16
            svg_parts.append(
                f'<rect x="{x}" y="{y}" width="8" height="8" rx="2" fill="{color}"/>'
                f'<text x="{x + 12}" y="{y + 7}" font-size="7.5" fill="#6b7280">{cat}</text>'
            )

        svg_parts.append('</svg>')
        return "\n".join(svg_parts)

    def _build_segments(self, element_ids: list[str], vector_type: str) -> list[dict]:
        vec = _VECTOR_BACKBONE.get(vector_type, _VECTOR_BACKBONE.get("lentiviral_LV", {}))
        segments: list[dict] = []

        for feat in vec.get("backbone_features", []):
            segments.append({
                "name": feat["name"],
                "size_bp": feat["size_bp"],
                "category": "Vector Backbone",
                "color": "#9ca3af",
            })

        for eid in element_ids:
            e = self._lib.get(eid, {})
            seq = e.get("sequence", "")
            is_dna = e.get("sequence_type") == "DNA"
            if is_dna:
                size_bp = len(seq) if seq else 300
            else:
                size_bp = len(seq) * 3 if seq else 300

            if size_bp < 30:
                size_bp = 300

            cat = e.get("category", "Unknown")
            color = _CATEGORY_COLORS.get(cat, "#94a3b8")
            name = e.get("name", eid)

            segments.append({
                "name": name,
                "size_bp": size_bp,
                "category": cat,
                "color": color,
                "element_id": eid,
            })

        for feat in vec.get("tail_features", []):
            segments.append({
                "name": feat["name"],
                "size_bp": feat["size_bp"],
                "category": "Regulatory Element",
                "color": "#6b7280",
            })

        return segments


def generate_plasmid_svg(
    element_ids: list[str],
    library_idx: dict[str, dict],
    vector_type: str = "lentiviral_LV",
    construct_name: str = "CAR Construct",
) -> str:
    """Convenience function: generate plasmid SVG from element IDs."""
    return PlasmidMapGenerator(library_idx).generate_svg(
        element_ids, vector_type, construct_name,
    )
