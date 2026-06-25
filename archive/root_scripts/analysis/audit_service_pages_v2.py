"""
audit_service_pages_v2.py  ── 2026-04-07
Detailed structural audit of service page hero/intro sections.
"""
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

    print(f"\n{'='*70}")
    print(f"  {name}  ({path.replace('docs/','')}) — {len(c):,} chars")
    print(f"{'='*70}")

    # 1. Find the hero/intro section class names used
    body_start = c.find('<body')
    first_2000 = c[body_start:body_start+2000] if body_start >= 0 else c[:2000]
    divs = re.findall(r'<(?:div|section|header)[^>]*class="([^"]+)"', first_2000)
    print(f"  First elements after <body>: {divs[:8]}")

    # 2. Background/gradient of hero/intro areas
    hero_css_patterns = [
        r'\.(hero|page-hero|intro|service-hero|hero-section)\s*\{([^}]{0,300})\}',
        r'\.(header-hero|top-banner|hero-wrap)\s*\{([^}]{0,300})\}',
    ]
    found_any = False
    for pat in hero_css_patterns:
        for m in re.finditer(pat, c, re.DOTALL):
            print(f"  CSS .{m.group(1)}: {m.group(2)[:150].strip}")
            found_any = True
    if not found_any:
        print(f"  (no standard hero CSS class found)")

    # 3. Check for SVG hero banner
    has_svg = 'hero-bg.svg' in c or 'hero-banner' in c
    has_pattern = 'repeating-linear-gradient' in c
    print(f"  svg hero-bg.svg: {has_svg}  repeating-gradient pattern: {has_pattern}")

    # 4. Body background
    body_bg = re.search(r'body\s*\{[^}]*background(?:-color)?:\s*([^;]+)', c)
    print(f"  body bg: {body_bg.group(1).strip if body_bg else 'inherit'}")

    # 5. Main h1 in body (first h1 after body open)
    h1_m = re.search(r'<h1[^>]*>(.{0,120})</h1>', c[body_start:] if body_start>=0 else c)
    if h1_m:
        h1_text = re.sub(r'<[^>]+>', '', h1_m.group(1)).strip
        print(f"  page h1 text: {h1_text[:80]}")

    # 6. --text-muted / --border values
    muted = re.search(r'--text-muted:\s*([^;]+)', c)
    border = re.search(r'--border:\s*([^;]+)', c)
    print(f"  --text-muted: {muted.group(1).strip if muted else 'n/a'}   --border: {border.group(1).strip if border else 'n/a'}")

    # 7. Section/content wrapper max-width
    maxws = re.findall(r'max-width:\s*(\d+px)', c)
    print(f"  max-widths used: {sorted(set(maxws))}")
