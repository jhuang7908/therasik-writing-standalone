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
    
    # Check service-hero present
    has_hero = 'class="service-hero"' in c
    print(f"  service-hero: {'YES' if has_hero else 'NO'}")
    
    # Check CSS added
    has_css = '.service-hero {' in c or '.service-hero{' in c
    print(f"  service-hero CSS: {'YES' if has_css else 'NO'}")
    
    # Extract service-hero content
    m = re.search(r'<div class="service-hero">(.*?)</div>', c, re.DOTALL)
    if m:
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip
        text = re.sub(r'\s+', ' ', text)
        print(f"  hero text: {text[:150]}")
    
    # Check h1 count in body
    body_idx = c.find('<body')
    h1_tags = re.findall(r'<h1[^/]', c[body_idx:])
    h2_after = re.findall(r'<h2[^/]', c[body_idx:])
    print(f"  h1 count in body: {len(h1_tags)}  h2 count: {len(h2_after)}")
    
    # Check back-link text
    bl = re.search(r'class="back-link"[^>]*>(.*?)</a>', c[body_idx:], re.DOTALL)
    if bl:
        bl_text = re.sub(r'<[^>]+>', '', bl.group(1)).strip
        print(f"  back-link: {bl_text[:60]}")
