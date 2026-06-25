"""Deep dive: page-wrap, sidebar, main, hero-banner CSS per service page"""
import re

PAGES = [
    ("docs/Therasik_Antibody_Page.html",   ""),
    ("docs/Therasik_ADC_Design_Page.html", "ADC"),
    ("docs/Therasik_CART_Page.html",       "CAR-T"),
    ("docs/Therasik_Bispecific_Page.html", ""),
    ("docs/Therasik_Vaccine_Design.html",  ""),
]

TARGET_SELECTORS = [
    'page-wrap', 'sidebar', r'\.main\b', 'hero-banner', 'hero-bg',
    r'\.content\b', 'breadcrumb', 'subtitle',
    r'h1\b', r'h2\b', r'h3\b',
    'section-title', 'eyebrow', 'trust-card',
]

for path, name in PAGES:
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read

    print(f"\n{'='*70}")
    print(f"[{name}]")

    for sel in TARGET_SELECTORS:
        # Build pattern for CSS rule
        pat = rf'\.{sel}\s*\{{([^}}]{{0,250}})\}}'
        m = re.search(pat, c, re.DOTALL)
        if m:
            inner = re.sub(r'\s+', ' ', m.group(1).strip)
            print(f"  .{sel}: {inner[:180]}")

    # Check for hero-banner HTML element
    hb = re.search(r'class="hero-banner"', c)
    print(f"  hero-banner element: {'YES' if hb else 'NO'}")

    # h1 in body - font-size
    h1_css = re.findall(r'(?:h1|\.h1)\s*\{[^}]*font-size:\s*([^;]+)', c)
    print(f"  h1 font-sizes (CSS): {h1_css}")

    # Check if sidebar has fixed/sticky positioning
    sidebar_pos = re.search(r'\.sidebar\s*\{[^}]*position:\s*([^;]+)', c)
    print(f"  sidebar position: {sidebar_pos.group(1).strip if sidebar_pos else 'static'}")
