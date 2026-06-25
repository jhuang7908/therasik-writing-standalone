"""Final checks: hero-bg.svg usage, main content CSS, h2 sizes"""
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

    print(f"\n[{name}]")

    # hero-bg.svg context
    idx = c.find('hero-bg.svg')
    if idx >= 0:
        print(f"  hero-bg.svg: ...{c[max(0,idx-60):idx+40]}...")
    else:
        print(f"  hero-bg.svg: NOT PRESENT")

    # .main CSS
    main_css = re.search(r'\.main\s*\{([^}]+)\}', c, re.DOTALL)
    if main_css:
        inner = re.sub(r'\s+', ' ', main_css.group(1).strip)
        print(f"  .main: {inner[:200]}")
    else:
        print(f"  .main: NOT FOUND (using <main> tag)")

    # h2 CSS rules
    h2_rules = re.findall(r'h2\s*\{([^}]+)\}', c, re.DOTALL)
    for r in h2_rules[:3]:
        inner = re.sub(r'\s+', ' ', r.strip)
        print(f"  h2 rule: {inner[:120]}")

    # Section heading (.section-title or similar)
    for sel in ['section-title', 'section-header', 'h2-icon']:
        m = re.search(rf'\.{sel}\s*\{{([^}}]+)\}}', c, re.DOTALL)
        if m:
            inner = re.sub(r'\s+', ' ', m.group(1).strip)
            print(f"  .{sel}: {inner[:120]}")

    # Content padding
    for pat in [r'\.content\s*\{([^}]+)\}', r'main\s*\{([^}]+)\}']:
        m = re.search(pat, c, re.DOTALL)
        if m:
            inner = re.sub(r'\s+', ' ', m.group(1).strip)
            print(f"  content/main: {inner[:150]}")
            break
