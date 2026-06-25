"""Print the first 30 lines of <main class="main"> for each service page"""
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
    idx = c.find('<main class="main">')
    if idx < 0:
        idx = c.find('<main class="main" ')
    snippet = c[idx:idx+1400]
    print(f"\n{'='*70}\n[{name}] {path}")
    print(repr(snippet[:1400]))
