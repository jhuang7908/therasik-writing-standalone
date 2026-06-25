"""
Replace bispecific format SVGs with clean, minimal line-art style.
Approach: binding heads (circles) + arm lines + Fc rectangles.
Size: viewBox="0 0 72 56", displayed at 64x50px.
Colors: thin strokes, very light fills — matches website aesthetic.
"""
import re, os

BASE = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source"
FILE = "InSynBio_Bispecific_Antibody_Design_Page.html"

W = "style=\"width:64px;height:50px;display:block;margin-top:6px;flex-shrink:0;\""

def svg(body):
    return (
        f'<svg viewBox="0 0 72 56" xmlns="http://www.w3.org/2000/svg" {W} aria-hidden="true">'
        + body +
        '</svg>'
    )

# ── Shared primitives ────────────────────────────────────────────────────────
# Standard Y-shape base: two binding heads + arm lines + hinge + Fc
# Arm A = teal, Arm B = gray-amber

def y_base(head_a, head_b, hinge_extra="", fc_inner="", fc_label=""):
    return (
        # Binding head A (teal)
        head_a +
        # Arm A
        '<line x1="13" y1="14" x2="28" y2="28" stroke="#0d9488" stroke-width="1.2" stroke-linecap="round"/>'
        # Binding head B
        + head_b +
        # Arm B
        '<line x1="59" y1="14" x2="44" y2="28" stroke="#6b7280" stroke-width="1.2" stroke-linecap="round"/>'
        # Hinge
        '<line x1="28" y1="28" x2="44" y2="28" stroke="#9ca3af" stroke-width="1"/>'
        + hinge_extra +
        # Fc CH2
        '<rect x="28" y="31" width="16" height="9" rx="1.5" fill="#f9fafb" stroke="#d1d5db" stroke-width="1"/>'
        # Fc CH3
        '<rect x="28" y="42" width="16" height="9" rx="1.5" fill="#f3f4f6" stroke="#d1d5db" stroke-width="1"/>'
        + fc_inner + fc_label
    )

# Standard binding heads
HEAD_A = '<circle cx="13" cy="8" r="6" fill="#e6fffa" stroke="#0d9488" stroke-width="1.2"/>'
HEAD_B = '<circle cx="59" cy="8" r="6" fill="#fff7ed" stroke="#d97706" stroke-width="1.2"/>'

# ── 1. KiH ─────────────────────────────────────────────────────────────────
# Knob (●) on left CH3, Hole (○) on right CH3
SVG_KIH = svg(y_base(
    HEAD_A, HEAD_B,
    fc_inner=(
        '<circle cx="33" cy="46" r="2.2" fill="#0d9488"/>'        # knob
        '<circle cx="45" cy="46" r="2.2" fill="#f9fafb" stroke="#9ca3af" stroke-width="0.9"/>'  # hole
    ),
    fc_label=(
        '<text x="33" y="55" text-anchor="middle" font-size="5.5" fill="#0d9488" font-family="Inter,sans-serif">●</text>'
        '<text x="45" y="55" text-anchor="middle" font-size="5.5" fill="#9ca3af" font-family="Inter,sans-serif">○</text>'
    )
))

# ── 2. DuoBody / DEKK ──────────────────────────────────────────────────────
# FAE symbol between Fc halves
SVG_DUOBODY = svg(y_base(
    HEAD_A, HEAD_B,
    fc_inner=(
        '<text x="36" y="38" text-anchor="middle" font-size="7" fill="#7c3aed" font-weight="600" font-family="Inter,sans-serif">⇄</text>'
    ),
    fc_label=(
        '<text x="36" y="55" text-anchor="middle" font-size="5.5" fill="#7c3aed" font-family="Inter,sans-serif">FAE</text>'
    )
))

# ── 3. Common Light Chain ───────────────────────────────────────────────────
# LC bridge arc above both heads
SVG_COMMONLC = svg(
    # Same gray LC marker on both arms
    '<path d="M7 4 Q36 -3 65 4" stroke="#9ca3af" stroke-width="1" fill="none" stroke-dasharray="2,1.5"/>'
    '<text x="36" y="3" text-anchor="middle" font-size="5" fill="#9ca3af" font-family="Inter,sans-serif">shared LC</text>'
    + y_base(
        HEAD_A, HEAD_B,
        fc_label=(
            '<text x="36" y="55" text-anchor="middle" font-size="5.5" fill="#6b7280" font-family="Inter,sans-serif">=LC</text>'
        )
    )
)

# ── 4. CrossMab / CrossFab ─────────────────────────────────────────────────
# × crossover mark on Arm B head
SVG_CROSSMAB = svg(y_base(
    HEAD_A,
    # Head B with crossover symbol
    '<circle cx="59" cy="8" r="6" fill="#fff7ed" stroke="#d97706" stroke-width="1.2"/>'
    '<line x1="55" y1="4" x2="63" y2="12" stroke="#dc2626" stroke-width="1.2" stroke-linecap="round"/>'
    '<line x1="63" y1="4" x2="55" y2="12" stroke="#dc2626" stroke-width="1.2" stroke-linecap="round"/>',
    fc_label=(
        '<text x="36" y="55" text-anchor="middle" font-size="5.5" fill="#dc2626" font-family="Inter,sans-serif">domain swap</text>'
    )
))

# ── 5. BiTE ─────────────────────────────────────────────────────────────────
# No Fc — two scFv ovals connected by linker
SVG_BITE = svg(
    # scFv 1
    '<rect x="2" y="10" width="24" height="18" rx="4" fill="#e6fffa" stroke="#0d9488" stroke-width="1.2"/>'
    '<text x="14" y="18" text-anchor="middle" font-size="6" fill="#0d9488" font-weight="600" font-family="Inter,sans-serif">scFv</text>'
    '<text x="14" y="26" text-anchor="middle" font-size="5" fill="#0d9488" font-family="Inter,sans-serif">anti-CD3</text>'
    # Linker
    '<path d="M26 19 Q36 15 36 19 Q36 23 46 19" stroke="#9ca3af" stroke-width="1" fill="none"/>'
    # scFv 2
    '<rect x="46" y="10" width="24" height="18" rx="4" fill="#fff7ed" stroke="#d97706" stroke-width="1.2"/>'
    '<text x="58" y="18" text-anchor="middle" font-size="6" fill="#d97706" font-weight="600" font-family="Inter,sans-serif">scFv</text>'
    '<text x="58" y="26" text-anchor="middle" font-size="5" fill="#d97706" font-family="Inter,sans-serif">anti-tumor</text>'
    # No Fc dashed box
    '<rect x="22" y="36" width="28" height="12" rx="2" fill="none" stroke="#e5e7eb" stroke-width="1" stroke-dasharray="2,2"/>'
    '<text x="36" y="44" text-anchor="middle" font-size="5.5" fill="#d1d5db" font-family="Inter,sans-serif">no Fc</text>'
)

# ── 6. Bridging IgG ─────────────────────────────────────────────────────────
# Target molecules at arm tips
SVG_BRIDGING = svg(y_base(
    # Head A with target T1
    '<circle cx="13" cy="8" r="6" fill="#dbeafe" stroke="#3b82f6" stroke-width="1.2"/>'
    '<text x="13" y="11" text-anchor="middle" font-size="6" fill="#1d4ed8" font-weight="700" font-family="Inter,sans-serif">T1</text>',
    # Head B with target T2
    '<circle cx="59" cy="8" r="6" fill="#fce7f3" stroke="#db2777" stroke-width="1.2"/>'
    '<text x="59" y="11" text-anchor="middle" font-size="6" fill="#9d174d" font-weight="700" font-family="Inter,sans-serif">T2</text>',
    fc_label=(
        '<text x="36" y="55" text-anchor="middle" font-size="5.5" fill="#6b7280" font-family="Inter,sans-serif">geometry-critical</text>'
    )
))

# ── 7. VHH-Fc ───────────────────────────────────────────────────────────────
# Diamond-shaped VHH heads (single domain, compact)
SVG_VHH_FC = svg(y_base(
    # VHH-A: diamond shape (single domain)
    '<rect x="7" y="3" width="12" height="12" rx="1" fill="#e6fffa" stroke="#0d9488" stroke-width="1.2" transform="rotate(45 13 9)"/>',
    # VHH-B: diamond shape
    '<rect x="53" y="3" width="12" height="12" rx="1" fill="#fff7ed" stroke="#d97706" stroke-width="1.2" transform="rotate(45 59 9)"/>',
    fc_label=(
        '<text x="36" y="55" text-anchor="middle" font-size="5.5" fill="#7c3aed" font-family="Inter,sans-serif">no mispairing</text>'
    )
))

# ── Map format names to SVGs ─────────────────────────────────────────────────
FORMAT_SVGS = {
    "Knob-into-Hole (KiH)":   SVG_KIH,
    "DuoBody® / DEKK":        SVG_DUOBODY,
    "Common Light Chain":      SVG_COMMONLC,
    "CrossMab / CrossFab":     SVG_CROSSMAB,
    "BiTE (tandem scFv)":      SVG_BITE,
    "Asymmetric Bridging IgG": SVG_BRIDGING,
    "VHH-Fc Fusion":           SVG_VHH_FC,
}

# ── Patch HTML ───────────────────────────────────────────────────────────────
path = os.path.join(BASE, FILE)
content = open(path, encoding="utf-8").read()

# Remove existing SVGs (inserted by previous script) — they sit between </div> and </div>
# Pattern: the old SVG starts with <svg viewBox="0 0 88 72" or <svg viewBox="0 0 80 60"
content = re.sub(
    r'\s*<svg viewBox="0 0 (?:88|80) (?:72|60)"[^>]*>.*?</svg>',
    '',
    content,
    flags=re.DOTALL
)
print("Removed old SVGs")

# Insert new SVGs after company name div
for fmt_name, svg_code in FORMAT_SVGS.items():
    pattern = (
        r'(<div style="font-size:13px;font-weight:700;color:#111827;">'
        + re.escape(fmt_name) +
        r'</div>\s*<div style="font-size:11px;[^"]*">[^<]*</div>)'
    )
    replacement = r'\1' + '\n            ' + svg_code
    new_content = re.sub(pattern, replacement, content, count=1)
    if new_content != content:
        content = new_content
        print(f"  Inserted: {fmt_name}")
    else:
        print(f"  No match: {fmt_name}")

open(path, "w", encoding="utf-8").write(content)
print(f"\nDone.")
