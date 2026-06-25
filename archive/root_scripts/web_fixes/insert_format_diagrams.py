"""Insert bispecific format schematic diagrams into the Format Selection section."""
import os

PAGE = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source\InSynBio_Bispecific_Antibody_Design_Page.html"

# ── SVG helpers ───────────────────────────────────────────────────────────────
def R(x,y,w,h,fill,label,fs=5.5,tc="white",rx=2):
    ty = y + h/2 + fs*0.35
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"/>'
            f'<text x="{x+w/2}" y="{ty:.1f}" text-anchor="middle" '
            f'font-size="{fs}" fill="{tc}" font-weight="600">{label}</text>')

def arm(x0, y0, vh_fill, vh_label="VH", vl_fill="#a7f3d0", vl_tc="#065f46",
        ch1_fill="#0f766e", cl_fill="#ccfbf1", cl_tc="#065f46", w=22):
    s  = R(x0, y0,      w, 12, vh_fill,  vh_label, fs=6, tc="white")
    s += R(x0, y0+14,   w, 11, vl_fill,  "VL",     fs=6, tc=vl_tc)
    s += R(x0, y0+27,   w, 10, ch1_fill, "CH1",    fs=5.5)
    s += R(x0, y0+39,   w, 10, cl_fill,  "CL",     fs=5.5, tc=cl_tc)
    return s

def fc(x_left, y_top, knob_hole=None, labels=None):
    """Draw Fc: two CH2 + two CH3. knob_hole='left'|'right', labels=('K','R')"""
    xl, xr = x_left, x_left+24
    s  = R(xl, y_top,    22, 10, "#134e4a", "CH2", fs=5)
    s += R(xr, y_top,    22, 10, "#134e4a", "CH2", fs=5)
    s += R(xl, y_top+12, 22, 10, "#0f766e", "CH3", fs=5)
    s += R(xr, y_top+12, 22, 10, "#0f766e", "CH3", fs=5)
    if knob_hole == "kh":  # knob on left CH2, hole on right CH2
        cx = xl + 11; cy = y_top - 1
        s += f'<polygon points="{cx-4},{cy} {cx},{cy-5} {cx+4},{cy}" fill="#ef4444"/>'
        cx2 = xr + 11
        s += f'<circle cx="{cx2}" cy="{cy}" r="3.5" fill="white" stroke="#3b82f6" stroke-width="1.5"/>'
    if labels:  # DEKK-style text labels on CH3
        s += (f'<text x="{xl+11}" y="{y_top+19}" text-anchor="middle" font-size="7" '
              f'fill="#f59e0b" font-weight="800">{labels[0]}</text>')
        s += (f'<text x="{xr+11}" y="{y_top+19}" text-anchor="middle" font-size="7" '
              f'fill="#f59e0b" font-weight="800">{labels[1]}</text>')
    return s

def hinge_lines(lx, rx, cy_top, cy_bot):
    return (f'<line x1="{lx}" y1="{cy_top}" x2="{cx(lx,rx)-11}" y2="{cy_bot}" '
            f'stroke="#9ca3af" stroke-width="1.5"/>'
            f'<line x1="{rx}" y1="{cy_top}" x2="{cx(lx,rx)+11}" y2="{cy_bot}" '
            f'stroke="#9ca3af" stroke-width="1.5"/>')

def cx(lx, rx): return (lx + rx) // 2


# ── Build each format card ────────────────────────────────────────────────────
def card(title, badge, badge_color, key_text, svg_content, vb="0 0 100 96"):
    badge_bg = {"green":"#dcfce7","amber":"#fef9c3","gray":"#f3f4f6"}[badge_color]
    badge_tc = {"green":"#15803d","amber":"#92400e","gray":"#6b7280"}[badge_color]
    return f"""
    <div style="flex:0 0 auto;width:148px;background:#fff;border:1px solid #e5e7eb;
                border-radius:12px;padding:12px 10px 10px;text-align:center;display:flex;
                flex-direction:column;align-items:center;gap:6px;">
      <div style="font-size:11.5px;font-weight:700;color:#111827;line-height:1.3;min-height:30px;
                  display:flex;align-items:center;justify-content:center;">{title}</div>
      <span style="display:inline-block;font-size:9.5px;font-weight:600;padding:2px 8px;
                   border-radius:10px;background:{badge_bg};color:{badge_tc};">{badge}</span>
      <svg viewBox="{vb}" style="width:100%;max-width:120px;height:auto;"
           xmlns="http://www.w3.org/2000/svg">{svg_content}</svg>
      <div style="font-size:10px;color:#6b7280;line-height:1.4;">{key_text}</div>
    </div>"""


# ── 1. KiH ────────────────────────────────────────────────────────────────────
svg_kih = (
    arm(2,  3, "#0d9488", "VH1") +
    arm(76, 3, "#0891b2", "VH2") +
    hinge_lines(13, 87, 53, 63) +
    fc(27, 63, knob_hole="kh") +
    # legend
    f'<polygon points="16,91 19,87 22,91" fill="#ef4444"/>'
    f'<text x="24" y="92" font-size="5" fill="#6b7280">Knob</text>'
    f'<circle cx="62" cy="89" r="3.5" fill="white" stroke="#3b82f6" stroke-width="1.5"/>'
    f'<text x="67" y="92" font-size="5" fill="#6b7280">Hole</text>'
)
card_kih = card("Knob-into-Hole (KiH)", "✓ Approved", "green",
                "Steric HC heterodimerization via T366W / T366S/L368A mutations", svg_kih)


# ── 2. DuoBody / DEKK ─────────────────────────────────────────────────────────
svg_duo = (
    arm(2,  3, "#0d9488", "VH1") +
    arm(76, 3, "#0891b2", "VH2") +
    hinge_lines(13, 87, 53, 63) +
    fc(27, 63, labels=("K", "R")) +
    f'<text x="50" y="92" text-anchor="middle" font-size="5" fill="#6b7280">K409R / F405L exchange</text>'
)
card_duo = card("DuoBody® / DEKK", "✓ Approved", "green",
                "Fab-arm exchange post-expression; electrostatic steering on CH3", svg_duo)


# ── 3. Common Light Chain ─────────────────────────────────────────────────────
svg_clc = (
    # left arm — VH1 different, VL same color
    arm(2,  3, "#0d9488", "VH1") +
    # right arm — VH2 different color, VL SAME color as left
    arm(76, 3, "#0891b2", "VH2") +
    # Highlight both VL with outline to show "same"
    f'<rect x="1" y="16" width="24" height="12" rx="3" fill="none" '
    f'stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="3,2"/>'
    f'<rect x="75" y="16" width="24" height="12" rx="3" fill="none" '
    f'stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="3,2"/>'
    f'<text x="50" y="24" text-anchor="middle" font-size="7" fill="#f59e0b" font-weight="700">=</text>' +
    hinge_lines(13, 87, 53, 63) +
    fc(27, 63) +
    f'<text x="50" y="91" text-anchor="middle" font-size="5" fill="#f59e0b" font-weight="600">Same LC sequence</text>'
)
card_clc = card("Common Light Chain", "✓ Approved", "green",
                "Identical LC on both arms — eliminates LC mispairing without domain swap", svg_clc)


# ── 4. CrossMab / CrossFab ───────────────────────────────────────────────────
# Arm A normal, Arm B: CH1 and CL positions swapped
svg_cross = (
    # Arm A: normal
    R(2,  3, 22, 12, "#0d9488", "VH1", fs=6) +
    R(2,  17, 22, 11, "#a7f3d0", "VL",  fs=6, tc="#065f46") +
    R(2,  30, 22, 10, "#0f766e", "CH1") +
    R(2,  42, 22, 10, "#ccfbf1", "CL",  tc="#065f46") +
    # Arm B: VH2 normal, then CL↔CH1 SWAPPED
    R(76, 3, 22, 12, "#0891b2", "VH2", fs=6) +
    R(76, 17, 22, 11, "#a7f3d0", "VL",  fs=6, tc="#065f46") +
    R(76, 30, 22, 10, "#ccfbf1", "CL*", tc="#065f46") +  # swapped: CL where CH1 was
    R(76, 42, 22, 10, "#0f766e", "CH1*") +               # swapped: CH1 where CL was
    # Cross arrows on Arm B
    f'<path d="M 74,35 Q 68,36 68,42 L 74,44" fill="none" stroke="#f59e0b" stroke-width="1.5" marker-end="url(#arr)"/>'
    f'<path d="M 74,47 Q 68,46 68,40 L 74,38" fill="none" stroke="#f59e0b" stroke-width="1.5"/>'
    # Simple swap indicator (two arrows)
    f'<text x="70" y="40" text-anchor="middle" font-size="8" fill="#f59e0b">⇅</text>' +
    hinge_lines(13, 87, 53, 63) +
    fc(27, 63) +
    f'<text x="50" y="91" text-anchor="middle" font-size="5" fill="#f59e0b">⇅ CH1/CL swapped in Arm B</text>'
)
card_cross = card("CrossMab / CrossFab", "✓ Approved", "green",
                  "CH1/CL domain exchange prevents LC mispairing via structural incompatibility", svg_cross)


# ── 5. BiTE (tandem scFv) ─────────────────────────────────────────────────────
# Linear: [VH1][VL1] ~~~ [VH2][VL2]   — no Fc
svg_bite = (
    # scFv1 (anti-CD3)
    R(2, 12, 22, 13, "#0d9488", "VH", fs=6) +
    f'<line x1="24" y1="18" x2="32" y2="18" stroke="#9ca3af" stroke-width="1.5" stroke-dasharray="2,2"/>'
    + R(32, 12, 22, 13, "#a7f3d0", "VL", fs=6, tc="#065f46") +
    f'<text x="33" y="9" text-anchor="middle" font-size="5" fill="#0d9488" font-weight="600">anti-CD3</text>'
    # Long flexible linker
    f'<line x1="54" y1="18" x2="70" y2="18" stroke="#9ca3af" stroke-width="1" stroke-dasharray="2,2"/>'
    f'<text x="62" y="14" text-anchor="middle" font-size="5" fill="#9ca3af">(G4S)₃</text>'
    # scFv2 (anti-tumor)
    + R(70, 12, 22, 13, "#0891b2", "VH", fs=6) +
    f'<line x1="92" y1="18" x2="100" y2="18" stroke="#9ca3af" stroke-width="1.5" stroke-dasharray="2,2"/>'
    + f'<text x="82" y="9" text-anchor="middle" font-size="5" fill="#0891b2" font-weight="600">anti-Tumor</text>'
    # No Fc banner
    f'<rect x="18" y="36" width="64" height="14" rx="4" fill="#fef2f2" stroke="#fca5a5" stroke-width="1"/>'
    f'<text x="50" y="46" text-anchor="middle" font-size="7" fill="#dc2626" font-weight="700">No Fc · Short t½</text>'
    f'<text x="50" y="60" text-anchor="middle" font-size="5" fill="#9ca3af">Continuous IV infusion required</text>'
)
card_bite = card("BiTE (tandem scFv)", "⚠ Legacy", "amber",
                 "No Fc → hours t½; requires continuous IV infusion; CRS risk",
                 svg_bite, vb="0 0 100 68")


# ── 6. Asymmetric Bridging IgG ────────────────────────────────────────────────
svg_bridge = (
    # Left arm: binds FIXa (red circle on top)
    f'<circle cx="13" cy="5" r="5" fill="#ef4444" opacity="0.85"/>'
    f'<text x="13" y="7.5" text-anchor="middle" font-size="4.5" fill="white">FIXa</text>'
    f'<line x1="13" y1="10" x2="13" y2="14" stroke="#9ca3af" stroke-width="1"/>' +
    arm(2,  14, "#0d9488", "VH1") +
    # Right arm: binds FX (blue circle on top)
    f'<circle cx="87" cy="5" r="5" fill="#3b82f6" opacity="0.85"/>'
    f'<text x="87" y="7.5" text-anchor="middle" font-size="4.5" fill="white">FX</text>'
    f'<line x1="87" y1="10" x2="87" y2="14" stroke="#9ca3af" stroke-width="1"/>' +
    arm(76, 14, "#0891b2", "VH2") +
    hinge_lines(13, 87, 64, 74) +
    fc(27, 74)
)
card_bridge = card("Asymmetric Bridging IgG", "✓ Approved", "green",
                   "Bridges two proteins for signaling relay; geometry is critical design parameter",
                   svg_bridge, vb="0 0 100 100")


# ── 7. VHH-Fc Fusion ─────────────────────────────────────────────────────────
svg_vhh = (
    # Left VHH (amber, no VL)
    R(2,  12, 22, 14, "#f59e0b", "VHH1", fs=6, tc="white") +
    f'<text x="13" y="10" text-anchor="middle" font-size="5" fill="#92400e">No LC</text>'
    f'<line x1="13" y1="26" x2="13" y2="36" stroke="#9ca3af" stroke-width="1.5"/>'
    # Right VHH (amber, no VL)
    + R(76, 12, 22, 14, "#f59e0b", "VHH2", fs=6, tc="white") +
    f'<text x="87" y="10" text-anchor="middle" font-size="5" fill="#92400e">No LC</text>'
    f'<line x1="87" y1="26" x2="87" y2="36" stroke="#9ca3af" stroke-width="1.5"/>'
    # Hinge (shorter — no Fab constant domains)
    f'<line x1="13" y1="36" x2="38" y2="46" stroke="#9ca3af" stroke-width="1.5"/>'
    f'<line x1="87" y1="36" x2="62" y2="46" stroke="#9ca3af" stroke-width="1.5"/>' +
    fc(27, 46) +
    f'<text x="50" y="80" text-anchor="middle" font-size="5" fill="#f59e0b" font-weight="600">Single domain · No chain mispairing</text>'
)
card_vhh = card("VHH-Fc Fusion", "Limited", "gray",
                "No chain mispairing risk; compact; requires VHH camelization & humanization",
                svg_vhh, vb="0 0 100 85")


# ── Assemble section ──────────────────────────────────────────────────────────
SECTION = f"""
      <!-- ── Format Visual Diagrams ─────────────────────────────────────── -->
      <div style="margin:18px 0 24px;">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.7px;
                    color:#9ca3af;margin-bottom:10px;">Format at a glance — structural schematics</div>
        <div style="display:flex;gap:10px;overflow-x:auto;padding-bottom:8px;">
          {card_kih}{card_duo}{card_clc}{card_cross}{card_bite}{card_bridge}{card_vhh}
        </div>
        <div style="font-size:10.5px;color:#9ca3af;margin-top:6px;">
          <span style="color:#0d9488;font-weight:600;">■</span> VH domain &nbsp;
          <span style="color:#a7f3d0;font-weight:600;border:1px solid #0d9488;padding:0 2px;">■</span> VL domain &nbsp;
          <span style="color:#f59e0b;font-weight:600;">■</span> VHH (single domain) &nbsp;
          <span style="color:#134e4a;font-weight:600;">■</span> Fc (CH2–CH3) &nbsp;
          <span style="color:#ef4444;">▲</span> Knob &nbsp;
          <span style="color:#3b82f6;font-weight:600;">○</span> Hole
        </div>
      </div>
      <!-- ── END Format Visual Diagrams ────────────────────────────────── -->
"""

# ── Insert into page ──────────────────────────────────────────────────────────
INSERT_BEFORE = '<div style="display:flex;flex-direction:column;gap:6px;margin:14px 0 6px;">'

with open(PAGE, encoding="utf-8") as f:
    content = f.read()

if INSERT_BEFORE not in content:
    print("ERROR: insertion point not found")
else:
    if "Format at a glance" in content:
        print("Already inserted, skipping")
    else:
        content = content.replace(INSERT_BEFORE, SECTION + INSERT_BEFORE, 1)
        with open(PAGE, "w", encoding="utf-8") as f:
            f.write(content)
        print("Done — format diagrams inserted")
