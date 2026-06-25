import os, re

base = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source"
main_pages = [
    "index.html",
    "InSynBio_Antibody_Developability_Assessment_Page.html",
    "InSynBio_Bispecific_Antibody_Design_Page.html",
    "InSynBio_CART_Design_Page.html",
    "immunogenicity_study.html",
    "case_bispecific_vhvl_pairing.html",
    "case_mumab4d5_humanization_en.html",
    "antibody-guide.html",
]

for p in main_pages:
    path = os.path.join(base, p)
    if not os.path.exists(path):
        print(f"{p} -- NOT FOUND")
        continue
    with open(path, encoding="utf-8") as f:
        content = f.read()
    # Extract header section only
    header_end = content.find("</header>")
    header = content[:header_end+200] if header_end > 0 else content[:3000]
    # Find menu-title links
    links = re.findall(r'href="([^"]+)"[^>]*>.*?menu-title[^>]*>([^<]+)', header, re.DOTALL)
    has_immuno = "immunogenicity" in header.lower()
    print(f"{p} [immuno_in_nav={has_immuno}]:")
    for href, title in links:
        marker = " <-- IMMUNO" if "immunogen" in href.lower() or "immunogen" in title.lower() else ""
        print(f"  {title.strip():<45} {href}{marker}")
    print()
