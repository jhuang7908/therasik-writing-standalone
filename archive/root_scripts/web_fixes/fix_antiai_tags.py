"""Add anti-AI meta tags to pages that are missing them."""
import os, re

BASE = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source"

# Pages to protect (public-facing content pages with proprietary data)
PROTECT = [
    "immunogenicity_study.html",
    "ada_database.html",
    "InSynBio_Showcase.html",
    "case_mumab4d5_humanization_zh.html",
    "case_mumab4d5_cmc.html",
    "Antibody_Developability_Assessment_Page.html",
    "404.html",
    "thanks.html",
    "thanks_zh.html",
]

META_TAGS = '  <meta name="robots" content="noai, noimageai">\n  <meta name="AI-Training" content="opt-out">\n'

fixed = 0
for p in PROTECT:
    path = os.path.join(BASE, p)
    if not os.path.exists(path):
        continue
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if "noai" in content[:3000]:
        continue
    # Insert after <head> or <meta charset...>
    if '<meta charset=' in content:
        content = re.sub(
            r'(<meta charset=[^>]+>)',
            r'\1\n' + META_TAGS.rstrip(),
            content, count=1
        )
    elif '<head>' in content:
        content = content.replace('<head>', '<head>\n' + META_TAGS, 1)
    else:
        continue
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"FIXED: {p}")
    fixed += 1

print(f"\nTotal fixed: {fixed}")
