"""Fix SVG opacity syntax and column width in bispecific page."""
import re, os

BASE = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source"
FILE = "InSynBio_Bispecific_Antibody_Design_Page.html"
path = os.path.join(BASE, FILE)

content = open(path, encoding="utf-8").read()

# 1. Fix 8-digit hex colors → split into fill + fill-opacity
# e.g., fill="#0d948899" -> fill="#0d9488" fill-opacity="0.6"
def fix_hex_opacity(m):
    attr = m.group(1)     # "fill" or "stroke"
    color6 = m.group(2)   # first 6 hex digits
    alpha_hex = m.group(3)  # last 2 hex digits
    alpha = round(int(alpha_hex, 16) / 255, 2)
    return f'{attr}="#{color6}" {attr}-opacity="{alpha}"'

content = re.sub(
    r'(fill|stroke)="#([0-9a-fA-F]{6})([0-9a-fA-F]{2})"',
    fix_hex_opacity,
    content
)

# 2. Fix Technology column width: 110px -> 160px
content = content.replace(
    "grid-template-columns:110px 130px 1fr 180px",
    "grid-template-columns:160px 120px 1fr 170px"
)

open(path, "w", encoding="utf-8").write(content)
print("Fixed opacity syntax and column width.")

# Verify a sample
m = re.search(r'(fill="#[0-9a-fA-F]{8}")', content)
print("Remaining 8-digit hex:", m.group(0) if m else "None — all clean")
