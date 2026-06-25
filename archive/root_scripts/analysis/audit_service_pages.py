"""
audit_service_pages.py  ── 2026-04-07
Compare CSS consistency across the 5 AI service pages.
"""
import re

PAGES = [
    ("docs/Therasik_Antibody_Page.html",   ""),
    ("docs/Therasik_ADC_Design_Page.html", "ADC"),
    ("docs/Therasik_CART_Page.html",       "CAR-T"),
    ("docs/Therasik_Bispecific_Page.html", ""),
    ("docs/Therasik_Vaccine_Design.html",  ""),
]

def extract(content, pattern, flags=0):
    m = re.search(pattern, content, flags)
    return m.group(1).strip if m else "NOT FOUND"

def first_of(content, patterns):
    for p in patterns:
        m = re.search(p, content)
        if m:
            return m.group(0)[:80]
    return "NOT FOUND"

results = {}
for path, name in PAGES:
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read
    results[name] = {
        "path": path,
        "content": c,
    }

print("=" * 80)
print("HERO / PAGE-HEADER SECTION")
print("=" * 80)
for name, d in results.items:
    c = d["content"]
    # Check for hero or page-header
    has_hero = bool(re.search(r'class="hero"', c))
    has_page_header = bool(re.search(r'class="page-header"', c))
    hero_bg = extract(c, r'\.hero\s*\{([^}]{0,300})\}', re.DOTALL)
    ph_bg   = extract(c, r'\.page-header\s*\{([^}]{0,300})\}', re.DOTALL)
    print(f"\n[{name}]")
    print(f"  has .hero: {has_hero}   has .page-header: {has_page_header}")
    if has_hero:
        print(f"  .hero CSS: {hero_bg[:180]}")
    if has_page_header:
        print(f"  .page-header CSS: {ph_bg[:180]}")

print("\n" + "=" * 80)
print("PRIMARY COLOR / ROOT VARIABLES")
print("=" * 80)
for name, d in results.items:
    c = d["content"]
    root = extract(c, r':root\s*\{([^}]+)\}', re.DOTALL)
    primary = re.search(r'--primary[^:]*:\s*([^;]+)', root or '')
    text_col = re.search(r'--text[^:]*:\s*([^;]+)', root or '')
    print(f"[{name}]  --primary: {primary.group(1).strip if primary else 'NOT FOUND'}"
          f"   --text: {text_col.group(1).strip if text_col else 'NOT FOUND'}")

print("\n" + "=" * 80)
print("H1 / H2 FONT SIZES")
print("=" * 80)
for name, d in results.items:
    c = d["content"]
    h1s = re.findall(r'h1\s*\{[^}]*font-size:\s*([^;]+)', c)
    h2s = re.findall(r'h2\s*\{[^}]*font-size:\s*([^;]+)', c)
    print(f"[{name}]  h1 font-sizes: {h1s[:4]}   h2 font-sizes: {h2s[:4]}")

print("\n" + "=" * 80)
print("BODY FONT-FAMILY")
print("=" * 80)
for name, d in results.items:
    c = d["content"]
    ff = extract(c, r'body\s*\{[^}]*font-family:\s*([^;]+)')
    print(f"[{name}]  body font-family: {ff[:80]}")

print("\n" + "=" * 80)
print("CARD STYLES")
print("=" * 80)
for name, d in results.items:
    c = d["content"]
    card = extract(c, r'\.(?:service-)?card\s*\{([^}]{0,200})\}', re.DOTALL)
    print(f"[{name}]  .card: {card[:120]}")

print("\n" + "=" * 80)
print("SECTION PADDING / MAX-WIDTH")
print("=" * 80)
for name, d in results.items:
    c = d["content"]
    page = extract(c, r'\.page\s*\{([^}]+)\}', re.DOTALL)
    print(f"[{name}]  .page: {page[:120]}")

print("\n" + "=" * 80)
print("MOBILE BREAKPOINTS PRESENT")
print("=" * 80)
for name, d in results.items:
    c = d["content"]
    mq = re.findall(r'@media\s*\(max-width:\s*(\d+px)\)', c)
    print(f"[{name}]  breakpoints: {sorted(set(mq))}")

print("\n" + "=" * 80)
print("GOOGLE FONTS LOADED")
print("=" * 80)
for name, d in results.items:
    c = d["content"]
    fonts = re.findall(r'family=([^&"\']+)', c)
    print(f"[{name}]  fonts: {fonts[:5]}")

print("\n" + "=" * 80)
print("HERO / HEADER BACKGROUND PATTERN")
print("=" * 80)
for name, d in results.items:
    c = d["content"]
    has_pattern = "repeating-linear-gradient" in c
    has_svg_bg  = "hero-bg.svg" in c or "hero-banner" in c
    print(f"[{name}]  repeating-gradient: {has_pattern}   svg hero banner: {has_svg_bg}")
