"""Quick verification of the final state of all 5 service pages."""
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
    body = c[c.find('<body'):]
    issues = []
    if 'class="service-hero"' in c:
        issues.append("service-hero STILL PRESENT")
    if 'class="main-intro"' not in c:
        issues.append("main-intro MISSING")
    if '.main-intro' not in c:
        issues.append("main-intro CSS MISSING")
    h1s = re.findall(r'<h1[^>]*>(.*?)</h1>', body)
    h1_count = len(h1s)
    has_pattern = 'rgba(13,148,136,0.055)' in c
    # Extract main-intro h1 text
    mi_match = re.search(r'class="main-intro[^"]*".*?<h1[^>]*>(.*?)</h1>', c, re.DOTALL)
    mi_h1 = mi_match.group(1) if mi_match else "NOT FOUND"
    mi_p = re.search(r'class="main-intro[^"]*".*?<h1[^>]*>.*?</h1>\s*<p>(.*?)</p>', c, re.DOTALL)
    mi_p_text = mi_p.group(1)[:60] if mi_p else "NOT FOUND"
    status = "✓" if not issues else "✗"
    print(f"{status} [{name}] h1={h1_count} pattern={has_pattern}")
    print(f"       title: {mi_h1}")
    print(f"       desc: {mi_p_text}...")
    if issues:
        print(f"       ISSUES: {', '.join(issues)}")
    print
