import re

for path in [
    "docs/Therasik_Bispecific_Page.html",
    "docs/Therasik_Antibody_Page.html",
]:
    with open(path,'r',encoding='utf-8') as f: c = f.read()
    body_idx = c.find('<body')
    for m in re.finditer(r'<h1[^/][^>]*>', c[body_idx:]):
        start = body_idx + m.start()
        print(f"[{path.split('/')[-1]}] h1 at +{m.start()}: ...{c[start:start+80]}...")
    print()
