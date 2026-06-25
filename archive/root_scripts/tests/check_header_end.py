"""Find the exact </header> closing tag + what follows in each service page"""
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

    idx = c.find('</header>')
    if idx >= 0:
        snippet = c[idx:idx+300]
        clean = re.sub(r'\s+', ' ', snippet).strip
        print(f"[{name}] header closes at char {idx}:")
        print(f"  {clean[:250]}")
    
    # Also find first h1 in body
    body_idx = c.find('<body')
    h1_m = re.search(r'<h1([^>]*)>(.*?)</h1>', c[body_idx:], re.DOTALL)
    if h1_m:
        print(f"  First h1 attrs: {h1_m.group(1).strip}")
        print(f"  First h1 text:  {re.sub(r'<[^>]+>','',h1_m.group(2)).strip[:80]}")
    print
