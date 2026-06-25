import os

BASE = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source"
pages = [f for f in os.listdir(BASE) if f.endswith(".html")]
print(f"Total HTML pages: {len(pages)}")
print()

missing = []
for p in sorted(pages):
    path = os.path.join(BASE, p)
    with open(path, encoding="utf-8") as f:
        head = f.read()[:3000]
    has_noai = "noai" in head
    has_aitrain = "AI-Training" in head
    has_headless = "webdriver" in head.lower() or "headless" in head.lower()
    if not has_noai or not has_aitrain:
        missing.append(p)
        status = []
        if not has_noai: status.append("MISSING noai")
        if not has_aitrain: status.append("MISSING AI-Training")
        print(f"  {p}: {' | '.join(status)}")

print()
print(f"Pages missing anti-AI tag: {len(missing)}")
print(f"Pages OK: {len(pages) - len(missing)}")
