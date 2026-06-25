"""
Add SVG structural diagrams to each row of the Bispecific Format Selection table.
The diagram is inserted inside the Technology column (below name + company text).
"""
import re, os

BASE = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source"
FILE = "InSynBio_Bispecific_Antibody_Design_Page.html"

# ── SVG templates (viewBox="0 0 88 72") ────────────────────────────────────
# Common base: Y-shaped bispecific with two Fab arms + Fc
# Arm A = teal, Arm B = amber, Fc = gray

def svg_wrap(inner, extra_label=""):
    return (
        '<svg viewBox="0 0 88 72" xmlns="http://www.w3.org/2000/svg" '
        'style="width:88px;height:72px;display:block;margin-top:8px;flex-shrink:0;" '
        'aria-hidden="true">'
        + inner + extra_label +
        '</svg>'
    )

# ── Shared Fab arm blocks ───────────────────────────────────────────────────
def fab_a(vh_fill, vl_fill, ch1_fill="#0d948899", cl_fill="#5eead499"):
    """Left Fab arm (Arm A)"""
    return (
        f'<rect x="2"  y="2"  width="15" height="13" rx="1.5" fill="{vh_fill}"/>'
        f'<rect x="18" y="2"  width="15" height="13" rx="1.5" fill="{vl_fill}"/>'
        f'<rect x="2"  y="16" width="15" height="11" rx="1.5" fill="{ch1_fill}"/>'
        f'<rect x="18" y="16" width="15" height="11" rx="1.5" fill="{cl_fill}"/>'
    )

def fab_b(vh_fill, vl_fill, ch1_fill="#f59e0b99", cl_fill="#fcd34d99"):
    """Right Fab arm (Arm B)"""
    return (
        f'<rect x="53" y="2"  width="15" height="13" rx="1.5" fill="{vh_fill}"/>'
        f'<rect x="69" y="2"  width="15" height="13" rx="1.5" fill="{vl_fill}"/>'
        f'<rect x="53" y="16" width="15" height="11" rx="1.5" fill="{ch1_fill}"/>'
        f'<rect x="69" y="16" width="15" height="11" rx="1.5" fill="{cl_fill}"/>'
    )

HINGE = (
    '<line x1="17" y1="27" x2="34" y2="40" stroke="#9ca3af" stroke-width="1.5"/>'
    '<line x1="71" y1="27" x2="54" y2="40" stroke="#9ca3af" stroke-width="1.5"/>'
)

def fc(ch3_inner=""):
    return (
        '<rect x="30" y="40" width="16" height="10" rx="1.5" fill="#e5e7eb" stroke="#9ca3af" stroke-width="0.8"/>'
        '<rect x="42" y="40" width="16" height="10" rx="1.5" fill="#e5e7eb" stroke="#9ca3af" stroke-width="0.8"/>'
        '<rect x="30" y="52" width="16" height="11" rx="1.5" fill="#d1d5db" stroke="#9ca3af" stroke-width="0.8"/>'
        '<rect x="42" y="52" width="16" height="11" rx="1.5" fill="#d1d5db" stroke="#9ca3af" stroke-width="0.8"/>'
        + ch3_inner
    )

ARM_LABELS = (
    '<text x="9"  y="71" text-anchor="middle" font-size="7" fill="#0d9488" font-weight="700" font-family="sans-serif">Arm A</text>'
    '<text x="77" y="71" text-anchor="middle" font-size="7" fill="#f59e0b" font-weight="700" font-family="sans-serif">Arm B</text>'
)

# ── 1. KiH: knob (●) on CH3-A, hole (○) on CH3-B ──────────────────────────
SVG_KIH = svg_wrap(
    fab_a("#0d9488", "#5eead4") +
    fab_b("#f59e0b", "#fcd34d") +
    HINGE +
    fc(
        '<circle cx="38" cy="57" r="3"   fill="#0d9488"/>'
        '<circle cx="50" cy="57" r="3"   fill="white" stroke="#9ca3af" stroke-width="1.2"/>'
    ) +
    ARM_LABELS +
    '<text x="38" y="68" text-anchor="middle" font-size="6" fill="#0d9488" font-family="sans-serif">●knob</text>'
    '<text x="50" y="68" text-anchor="middle" font-size="6" fill="#9ca3af" font-family="sans-serif">○hole</text>'
)

# ── 2. DuoBody/DEKK: FAE shown as ⇄ at CH3 junction ──────────────────────
SVG_DUOBODY = svg_wrap(
    fab_a("#0d9488", "#5eead4") +
    fab_b("#f59e0b", "#fcd34d") +
    HINGE +
    fc() +
    ARM_LABELS +
    '<text x="44" y="60" text-anchor="middle" font-size="8" fill="#7c3aed" font-weight="700" font-family="sans-serif">⇄</text>'
    '<text x="44" y="70" text-anchor="middle" font-size="6" fill="#7c3aed" font-family="sans-serif">FAE</text>'
)

# ── 3. Common LC: both CLs same gray, VHs different colors ────────────────
SVG_COMMONLC = svg_wrap(
    # Arm A: teal VH, gray VL, gray CL
    '<rect x="2"  y="2"  width="15" height="13" rx="1.5" fill="#0d9488"/>'
    '<rect x="18" y="2"  width="15" height="13" rx="1.5" fill="#9ca3af"/>'
    '<rect x="2"  y="16" width="15" height="11" rx="1.5" fill="#0d948899"/>'
    '<rect x="18" y="16" width="15" height="11" rx="1.5" fill="#9ca3af99"/>'
    # Arm B: amber VH, same gray VL, same gray CL
    '<rect x="53" y="2"  width="15" height="13" rx="1.5" fill="#f59e0b"/>'
    '<rect x="69" y="2"  width="15" height="13" rx="1.5" fill="#9ca3af"/>'
    '<rect x="53" y="16" width="15" height="11" rx="1.5" fill="#f59e0b99"/>'
    '<rect x="69" y="16" width="15" height="11" rx="1.5" fill="#9ca3af99"/>'
    # Bracket indicating same LC
    '<path d="M18 1 L18 0 L71 0 L71 1" stroke="#6b7280" stroke-width="0.8" fill="none"/>'
    '<text x="44" y="-1" text-anchor="middle" font-size="6" fill="#6b7280" font-family="sans-serif">same LC</text>'
    + HINGE + fc() + ARM_LABELS +
    '<text x="44" y="71" text-anchor="middle" font-size="6.5" fill="#6b7280" font-weight="600" font-family="sans-serif">= LC</text>'
)

# ── 4. CrossMab/CrossFab: one arm has VH↔VL domain crossover ──────────────
SVG_CROSSMAB = svg_wrap(
    # Arm A: normal teal
    fab_a("#0d9488", "#5eead4") +
    # Arm B: VH/VL swapped (VH shown lighter, VL shown darker = swapped)
    '<rect x="53" y="2"  width="15" height="13" rx="1.5" fill="#fcd34d"/>'  # VL in VH position
    '<rect x="69" y="2"  width="15" height="13" rx="1.5" fill="#f59e0b"/>'  # VH in VL position
    '<rect x="53" y="16" width="15" height="11" rx="1.5" fill="#9ca3af99"/>'  # CL in CH1 position
    '<rect x="69" y="16" width="15" height="11" rx="1.5" fill="#f59e0b99"/>'  # CH1 in CL position
    # Cross symbol on Arm B
    '<line x1="53" y1="2" x2="84" y2="27" stroke="#dc2626" stroke-width="1.2" opacity="0.6"/>'
    '<line x1="84" y1="2" x2="53" y2="27" stroke="#dc2626" stroke-width="1.2" opacity="0.6"/>'
    + HINGE + fc() + ARM_LABELS +
    '<text x="69" y="71" text-anchor="middle" font-size="6" fill="#dc2626" font-family="sans-serif">×-swap</text>'
)

# ── 5. BiTE: two scFv boxes, NO Fc ─────────────────────────────────────────
SVG_BITE = svg_wrap(
    # scFv 1 (anti-CD3, teal)
    '<rect x="4"  y="10" width="30" height="22" rx="3" fill="#e0f2f1" stroke="#0d9488" stroke-width="1.5"/>'
    '<text x="19" y="20" text-anchor="middle" font-size="7" fill="#0d9488" font-weight="700" font-family="sans-serif">scFv-1</text>'
    '<text x="19" y="30" text-anchor="middle" font-size="6" fill="#0d9488" font-family="sans-serif">anti-CD3</text>'
    # Linker
    '<rect x="35" y="18" width="18" height="6" rx="3" fill="#d1d5db"/>'
    '<text x="44" y="23" text-anchor="middle" font-size="5.5" fill="#6b7280" font-family="sans-serif">linker</text>'
    # scFv 2 (anti-tumor, amber)
    '<rect x="54" y="10" width="30" height="22" rx="3" fill="#fffbeb" stroke="#f59e0b" stroke-width="1.5"/>'
    '<text x="69" y="20" text-anchor="middle" font-size="7" fill="#f59e0b" font-weight="700" font-family="sans-serif">scFv-2</text>'
    '<text x="69" y="30" text-anchor="middle" font-size="6" fill="#f59e0b" font-family="sans-serif">anti-tumor</text>'
    # No Fc label
    '<rect x="28" y="46" width="32" height="14" rx="3" fill="#f3f4f6" stroke="#e5e7eb" stroke-width="1" stroke-dasharray="3,2"/>'
    '<text x="44" y="56" text-anchor="middle" font-size="7" fill="#9ca3af" font-family="sans-serif">no Fc</text>'
    # lines from scFv to "no Fc"
    '<line x1="19" y1="32" x2="35" y2="46" stroke="#d1d5db" stroke-width="1" stroke-dasharray="2,2"/>'
    '<line x1="69" y1="32" x2="53" y2="46" stroke="#d1d5db" stroke-width="1" stroke-dasharray="2,2"/>'
    '<text x="44" y="71" text-anchor="middle" font-size="6.5" fill="#9ca3af" font-family="sans-serif">short t½ · no FcRn</text>'
)

# ── 6. Bridging IgG: arm tips show two target molecules being bridged ───────
SVG_BRIDGING = svg_wrap(
    fab_a("#0d9488", "#5eead4") +
    fab_b("#f59e0b", "#fcd34d") +
    # Target A at Arm A tip
    '<circle cx="10" cy="0" r="5" fill="#dbeafe" stroke="#3b82f6" stroke-width="1.2"/>'
    '<text x="10" y="3" text-anchor="middle" font-size="5.5" fill="#1d4ed8" font-weight="700" font-family="sans-serif">T1</text>'
    # Target B at Arm B tip
    '<circle cx="78" cy="0" r="5" fill="#fce7f3" stroke="#ec4899" stroke-width="1.2"/>'
    '<text x="78" y="3" text-anchor="middle" font-size="5.5" fill="#9d174d" font-weight="700" font-family="sans-serif">T2</text>'
    + HINGE + fc() + ARM_LABELS +
    '<text x="44" y="71" text-anchor="middle" font-size="6" fill="#6b7280" font-family="sans-serif">geometry-critical</text>'
)

# ── 7. VHH-Fc: two single-domain VHH on top of Fc ─────────────────────────
SVG_VHH_FC = svg_wrap(
    # VHH-A (single domain, hexagonal shape)
    '<polygon points="16,2 27,8 27,20 16,26 5,20 5,8" fill="#e0f2f1" stroke="#0d9488" stroke-width="1.5"/>'
    '<text x="16" y="16" text-anchor="middle" font-size="7" fill="#0d9488" font-weight="700" font-family="sans-serif">VHH</text>'
    # VHH-B
    '<polygon points="72,2 83,8 83,20 72,26 61,20 61,8" fill="#fffbeb" stroke="#f59e0b" stroke-width="1.5"/>'
    '<text x="72" y="16" text-anchor="middle" font-size="7" fill="#f59e0b" font-weight="700" font-family="sans-serif">VHH</text>'
    # connecting lines to Fc
    '<line x1="16" y1="26" x2="33" y2="40" stroke="#9ca3af" stroke-width="1.5"/>'
    '<line x1="72" y1="26" x2="55" y2="40" stroke="#9ca3af" stroke-width="1.5"/>'
    + fc() +
    '<text x="9"  y="71" text-anchor="middle" font-size="6.5" fill="#0d9488" font-weight="700" font-family="sans-serif">VHH-A</text>'
    '<text x="79" y="71" text-anchor="middle" font-size="6.5" fill="#f59e0b" font-weight="700" font-family="sans-serif">VHH-B</text>'
    '<text x="44" y="71" text-anchor="middle" font-size="6" fill="#7c3aed" font-family="sans-serif">no mispairing</text>'
)

# ── Map format IDs to SVGs ──────────────────────────────────────────────────
FORMAT_SVGS = {
    "Knob-into-Hole (KiH)":          SVG_KIH,
    "DuoBody® / DEKK":               SVG_DUOBODY,
    "Common Light Chain":             SVG_COMMONLC,
    "CrossMab / CrossFab":            SVG_CROSSMAB,
    "BiTE (tandem scFv)":             SVG_BITE,
    "Asymmetric Bridging IgG":        SVG_BRIDGING,
    "VHH-Fc Fusion":                  SVG_VHH_FC,
}

# ── Patch the HTML ─────────────────────────────────────────────────────────
path = os.path.join(BASE, FILE)
content = open(path, encoding="utf-8").read()

# Also update grid to accommodate diagram column
# Current: grid-template-columns:200px 130px 1fr 180px
# New: add 104px column for diagram at the start

for fmt_name, svg_code in FORMAT_SVGS.items():
    # Find the div containing this format name and insert SVG after the company line
    # Pattern: <div style="font-size:13px;font-weight:700;...">FORMAT_NAME</div>\n            <div style="font-size:11px;...">COMPANY</div>
    # We insert the SVG right after the company div (closing </div>), before the outer </div>

    escaped_name = fmt_name.replace("®", "®").replace("™", "™")

    pattern = (
        r'(<div style="font-size:13px;font-weight:700;color:#111827;">'
        + re.escape(fmt_name) +
        r'</div>\s*<div style="font-size:11px;[^"]*">[^<]*</div>)'
    )

    replacement = r'\1\n            ' + svg_code.replace('\\', '\\\\')

    new_content = re.sub(pattern, replacement, content, count=1)
    if new_content != content:
        content = new_content
        print(f"  Added SVG: {fmt_name}")
    else:
        print(f"  No match:  {fmt_name}")

# Also update the grid column to make Technology column wider (200->220px) 
# so the SVG fits alongside the text without overflow
content = content.replace(
    "grid-template-columns:200px 130px 1fr 180px",
    "grid-template-columns:110px 130px 1fr 180px",
)
# Actually we want the SVG inside the 1st column, so keep same grid but allow
# the tech column to expand a bit. Let's set it to align-items:start properly.

open(path, "w", encoding="utf-8").write(content)
print(f"\nDone: {FILE}")
