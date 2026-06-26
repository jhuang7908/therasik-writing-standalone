"""
Convert manuscript figures to Antibody Therapeutics (OUP) submission format.

OUP AT spec:
  - 300 dpi (halftone/combination)
  - Double-column width: 170 mm = 2008 px @ 300 dpi
  - Format: TIFF LZW
  - Color: RGB (sRGB, online-only journal)
  - Max file size: 10 MB

Usage:
    python scripts/at_figure_comply.py
"""
from __future__ import annotations
import json
import os
import datetime
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("ERROR: Pillow not installed — pip install Pillow")

FIG_DIR = Path("paper/Submission_Package/data and figure/Figures")
OUT_DIR = Path("paper/Submission_Package/ScholarOne_Upload/Review_B_DeNovo/figures_AT_compliant")
TARGET_DPI = 300
TARGET_W_MM = 170   # double-column
TARGET_W_PX = int(round(TARGET_W_MM / 25.4 * TARGET_DPI))  # 2008

CONVERSIONS = [
    {
        "figure": "Figure_1",
        "source": "Figure1_DeNovo_Ecosystem.png",
        "backend": "matplotlib",
        "rationale": "Highest pixel count (2218px) among Fig1 candidates; programmatic rendering; 188mm@300dpi → downsize to 170mm",
        "out_name": "Figure1_DeNovo_Ecosystem_AT_300dpi.tiff",
    },
    {
        "figure": "Figure_2",
        "source": "Figure2_DualStack_Workflow.png",
        "backend": "Gemini",
        "rationale": "Highest pixel count (3175px) among Fig2 candidates; 269mm@300dpi → downsize to 170mm",
        "out_name": "Figure2_DualStack_Workflow_AT_300dpi.tiff",
    },
]


def to_rgb(img: Image.Image) -> Image.Image:
    """Composite RGBA/P onto white, return RGB."""
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    if img.mode == "P":
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def process(conv: dict) -> dict:
    src = FIG_DIR / conv["source"]
    dst = OUT_DIR / conv["out_name"]

    img = Image.open(src)
    orig_size = img.size
    orig_mode = img.mode
    orig_meta_dpi = img.info.get("dpi", (72, 72))[0]

    img = to_rgb(img)

    w, h = img.size
    if w != TARGET_W_PX:
        new_h = int(round(h * TARGET_W_PX / w))
        img = img.resize((TARGET_W_PX, new_h), Image.LANCZOS)

    img.save(str(dst), format="TIFF", compression="tiff_lzw",
             dpi=(TARGET_DPI, TARGET_DPI))

    kb = dst.stat().st_size // 1024
    pw = round(img.size[0] / TARGET_DPI * 25.4, 1)
    ph = round(img.size[1] / TARGET_DPI * 25.4, 1)

    status = "PASS" if kb < 10_240 else "WARN: >10MB"
    entry = {
        "figure": conv["figure"],
        "source": conv["source"],
        "source_backend": conv["backend"],
        "rationale": conv["rationale"],
        "source_size_px": list(orig_size),
        "source_mode": orig_mode,
        "source_meta_dpi": round(orig_meta_dpi),
        "output": conv["out_name"],
        "output_size_px": list(img.size),
        "output_dpi": TARGET_DPI,
        "output_mode": "RGB",
        "output_format": "TIFF-LZW",
        "print_size_mm": [pw, ph],
        "file_size_kb": kb,
        "compliance": status,
    }

    print(f"  {conv['out_name']}")
    print(f"    {orig_size} {orig_mode} {round(orig_meta_dpi)}dpi"
          f"  →  {img.size} RGB 300dpi TIFF-LZW  {kb} KB")
    print(f"    print: {pw}mm x {ph}mm @ 300dpi  [{status}]")
    print()
    return entry


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"OUP Antibody Therapeutics figure compliance conversion")
    print(f"Target: {TARGET_DPI} dpi | {TARGET_W_MM}mm double-column ({TARGET_W_PX}px)")
    print(f"Format: TIFF-LZW | Color: RGB")
    print()

    figures = []
    for conv in CONVERSIONS:
        figures.append(process(conv))

    report = {
        "_generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "journal": "Antibody Therapeutics",
        "publisher": "Oxford University Press",
        "issn": "2516-4236",
        "submission_system": "ScholarOne",
        "spec": {
            "dpi": TARGET_DPI,
            "column_width_mm": TARGET_W_MM,
            "column_width_px": TARGET_W_PX,
            "format": "TIFF-LZW",
            "color_mode": "RGB",
            "max_file_size_mb": 10,
            "oup_reference": "https://academic.oup.com/antibodytherapeutics/pages/General_Instructions",
        },
        "figures": figures,
        "overall": "PASS" if all(f["compliance"] == "PASS" for f in figures) else "WARN",
        "upload_instructions": [
            "Log in to ScholarOne: https://mc.manuscriptcentral.com/antibodytherapeutics",
            "Step 5 (File Upload): select File Type = 'Figure'",
            "Upload Figure1_DeNovo_Ecosystem_AT_300dpi.tiff as Figure 1",
            "Upload Figure2_DualStack_Workflow_AT_300dpi.tiff as Figure 2",
            "Figure legends are embedded in the DOCX manuscript (end of file)",
        ],
    }

    report_path = OUT_DIR / "AT_figure_compliance_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path = OUT_DIR / "AT_figure_compliance_report.md"
    lines = [
        "# Antibody Therapeutics — Figure Compliance Report",
        "",
        f"Generated: {report['_generated_at']}  ",
        f"Journal: {report['journal']} (OUP) · ISSN {report['issn']}  ",
        f"Submission system: {report['submission_system']}  ",
        f"Overall: **{report['overall']}**",
        "",
        "## OUP AT Spec Applied",
        "",
        "| Parameter | Requirement | Applied |",
        "|-----------|-------------|---------|",
        f"| Resolution | ≥ 300 dpi (combination/halftone) | **300 dpi** |",
        f"| Width | 170 mm double-column | **{TARGET_W_MM} mm ({TARGET_W_PX} px)** |",
        f"| Format | TIFF (LZW compressed) | **TIFF-LZW** |",
        f"| Color mode | RGB (sRGB, online-only OA journal) | **RGB** |",
        f"| Max size | < 10 MB | See table below |",
        "",
        "## Figure Outputs",
        "",
        "| Figure | Output file | Size px | Print size | DPI | Format | KB | Status |",
        "|--------|-------------|---------|-----------|-----|--------|----|--------|",
    ]
    for f in figures:
        lines.append(
            f"| {f['figure']} | `{f['output']}` | "
            f"{f['output_size_px'][0]}×{f['output_size_px'][1]} | "
            f"{f['print_size_mm'][0]}×{f['print_size_mm'][1]} mm | "
            f"{f['output_dpi']} | {f['output_format']} | "
            f"{f['file_size_kb']} | **{f['compliance']}** |"
        )

    lines += [
        "",
        "## Source Selection Rationale",
        "",
    ]
    for f in figures:
        lines.append(f"- **{f['figure']}** ({f['source_backend']}): {f['rationale']}")

    lines += [
        "",
        "## ScholarOne Upload Steps",
        "",
    ]
    for i, step in enumerate(report["upload_instructions"], 1):
        lines.append(f"{i}. {step}")

    lines += [
        "",
        "## What Changed vs Source Files",
        "",
        "| Issue | Source | Fixed in Output |",
        "|-------|--------|-----------------|",
        "| DPI metadata wrong (200/250 dpi) | matplotlib / Gemini originals | Set to 300 dpi |",
        "| RGBA transparency | matplotlib / Gemini originals | Composited onto white → RGB |",
        "| Wrong format (PNG) | Both originals | Converted to TIFF-LZW |",
        "| Width mismatch (188mm/269mm) | Both originals | Resized to 170mm (Lanczos) |",
        "",
        "---",
        "*Report generated by `scripts/at_figure_comply.py`*",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Compliance report → {report_path}")
    print(f"Markdown summary → {md_path}")
    print(f"\nOverall: {report['overall']}")


if __name__ == "__main__":
    main()
