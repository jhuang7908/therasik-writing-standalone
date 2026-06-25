"""Check where id='platform' and id='overview' anchor targets are on each page"""
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
    # Find all id attributes
    ids_found = re.findall(r'<[^>]+\bid=["\']([^"\']+)["\'][^>]*>', c)
    print(f"  All element IDs: {ids_found[:12]}")
    # Find first h1 full tag
    body_idx = c.find('<body')
    h1_tags = re.findall(r'(<h1[^>]*>)', c[body_idx:])
    print(f"  h1 tags in body: {h1_tags[:3]}")
    # Find what comes just before <div class="page-wrap">
    pw_idx = c.find('<div class="page-wrap">')
    if pw_idx > 0:
        before = c[max(0,pw_idx-100):pw_idx+100]
        print(f"  context around page-wrap: ...{before}...")
