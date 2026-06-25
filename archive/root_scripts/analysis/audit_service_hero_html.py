"""Check the actual hero HTML structure (first 80 lines after header ends)"""
import re

PAGES = [
    ("docs/Therasik_Antibody_Page.html",   ""),
    ("docs/Therasik_ADC_Design_Page.html", "ADC"),
    ("docs/Therasik_CART_Page.html",       "CAR-T"),
    ("docs/Therasik_Bispecific_Page.html", ""),
    ("docs/Therasik_Vaccine_Design.html",  ""),
]

for path, name in PAGES:
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read

    # Find end of </header>
    header_end = c.find('</header>')
    if header_end < 0:
        header_end = c.find('</nav>')
    snippet = c[header_end:header_end+1200] if header_end >= 0 else c[2000:3200]

    # Extract class names from first 1000 chars after header
    classes = re.findall(r'class="([^"]+)"', snippet[:1000])
    # Strip inline styles for cleanliness
    clean = re.sub(r' style="[^"]{0,200}"', ' [style]', snippet)
    clean = re.sub(r'<svg[^>]*>.*?</svg>', '<svg/>', clean, flags=re.DOTALL)
    clean = re.sub(r'\s+', ' ', clean).strip

    print(f"\n{'='*70}")
    print(f"[{name}]  classes found after header: {classes[:8]}")
    print(f"First 800 chars of hero HTML:")
    print(clean[:800])
