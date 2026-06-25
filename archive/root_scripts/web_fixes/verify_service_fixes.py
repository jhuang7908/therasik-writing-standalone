import re

PAGES = [
    ("docs/Therasik_Antibody_Page.html",   ""),
    ("docs/Therasik_ADC_Design_Page.html", "ADC"),
    ("docs/Therasik_CART_Page.html",       "CAR-T"),
    ("docs/Therasik_Bispecific_Page.html", ""),
    ("docs/Therasik_Vaccine_Design.html",  ""),
]

print("── --text-muted ──────────────────────────────────────────")
for path, name in PAGES:
    with open(path,'r',encoding='utf-8') as f: c = f.read
    m = re.search(r'--text-muted:\s*([^;]+)', c)
    print(f"  [{name}] {m.group(1).strip if m else 'NOT FOUND'}")

print("\n── --text ────────────────────────────────────────────────")
for path, name in PAGES:
    with open(path,'r',encoding='utf-8') as f: c = f.read
    m = re.search(r'--text:\s*([^;]+)', c)
    print(f"  [{name}] {m.group(1).strip if m else 'NOT FOUND'}")

print("\n── .trust-card background ───────────────────────────────")
for path, name in PAGES:
    with open(path,'r',encoding='utf-8') as f: c = f.read
    m = re.search(r'\.trust-card\s*\{[^}]*background:\s*([^;]+)', c, re.DOTALL)
    val = m.group(1).strip[:80] if m else 'NOT FOUND'
    ok = 'f5f8ff' not in val
    print(f"  [{name}] {'OK' if ok else 'BLUE TINT!'} {val}")

print("\n── Antibody page h1 title ───────────────────────────────")
with open("docs/Therasik_Antibody_Page.html",'r',encoding='utf-8') as f: c = f.read
body_start = c.find('<body')
h1 = re.search(r'<h1[^>]*>([^<]+)</h1>', c[body_start:])
print(f"  h1: {h1.group(1).strip if h1 else 'NOT FOUND'}")
old_name = '' in c
print(f"  old name still present: {old_name}")

print("\n── ADC breadcrumb CSS ───────────────────────────────────")
with open("docs/Therasik_ADC_Design_Page.html",'r',encoding='utf-8') as f: c = f.read
has_bc = '.breadcrumb' in c
print(f"  .breadcrumb CSS present: {has_bc}")
