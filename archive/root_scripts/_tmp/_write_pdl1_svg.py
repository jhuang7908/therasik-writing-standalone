import shutil

SVG = """\
<svg width="1200" height="675" viewBox="0 0 1200 675" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1200" y2="675" gradientUnits="userSpaceOnUse">
      <stop offset="0"    stop-color="#f0fdfa"/>
      <stop offset="0.55" stop-color="#ffffff"/>
      <stop offset="1"    stop-color="#ccfbf1"/>
    </linearGradient>
    <linearGradient id="line" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0d9488" stop-opacity="0.75"/>
      <stop offset="1" stop-color="#2dd4bf" stop-opacity="0.30"/>
    </linearGradient>
    <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1.2" fill="#0d9488" opacity="0.09"/>
    </pattern>
    <filter id="soft">
      <feGaussianBlur stdDeviation="6" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <rect width="1200" height="675" fill="url(#bg)"/>
  <rect width="1200" height="675" fill="url(#dots)"/>

  <!-- Two abstract binding-trajectory curves -->
  <g opacity="0.55" fill="none" stroke="url(#line)" stroke-width="6"
     stroke-linecap="round" stroke-linejoin="round" filter="url(#soft)">
    <path d="M200 260 C 360 200, 480 340, 620 280 S 840 180, 1040 240"/>
    <path d="M220 440 C 370 380, 480 500, 640 430 S 840 320, 1040 400"
          stroke-width="4" opacity="0.80"/>
  </g>

  <!-- Teal anchor nodes -->
  <g fill="#0d9488" opacity="0.22">
    <circle cx="620" cy="280" r="11"/>
    <circle cx="640" cy="430" r="10"/>
    <circle cx="1040" cy="240" r="8"/>
  </g>

  <!-- Ab1 epitope node (sky, lateral flank) -->
  <circle cx="490" cy="342" r="16" fill="#0ea5e9" opacity="0.16" filter="url(#soft)"/>
  <circle cx="490" cy="342" r="8"  fill="#0ea5e9" opacity="0.50"/>

  <!-- Ab2 epitope node (purple, PD-1 interface) -->
  <circle cx="760" cy="312" r="16" fill="#7c3aed" opacity="0.18" filter="url(#soft)"/>
  <circle cx="760" cy="312" r="8"  fill="#7c3aed" opacity="0.48"/>

  <!-- Shared epitope dashed arc -->
  <path d="M498 340 C 560 290, 680 286, 752 314"
        fill="none" stroke="#7c3aed" stroke-width="2.5"
        stroke-linecap="round" stroke-dasharray="8 6" opacity="0.38"/>

  <!-- Text block -->
  <g font-family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif">
    <text x="40" y="72"  font-size="14" fill="#0f766e" font-weight="800" letter-spacing="2" opacity="0.9">CASE STUDY</text>
    <text x="40" y="118" font-size="34" fill="#111827" font-weight="750">PD-L1 Dual-Clone</text>
    <text x="40" y="158" font-size="24" fill="#7c3aed" font-weight="700" opacity="0.75">Epitope Structural Profiling</text>
    <text x="40" y="188" font-size="13" fill="#6b7280" font-weight="500">Non-blocking ADC route vs. blocking ICI route - AF2-Multimer</text>
  </g>
</svg>
"""

dest_docs = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\docs\images\case-pdl1-panel.svg"
dest_web  = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\images\case-pdl1-panel.svg"

with open(dest_docs, "w", encoding="utf-8") as f:
    f.write(SVG)
shutil.copy(dest_docs, dest_web)
print("Done")
