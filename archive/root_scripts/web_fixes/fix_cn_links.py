import re

filepath = 'd:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/whitepaper_therasik_cn.html'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the links to point to the correct Chinese HTML files
replacements = [
    (r'href="case_mumab4d5_humanization_en\.html"', 'href="case_mumab4d5_humanization_zh.html"'),
    (r'href="case_mumab4d5_vhh_en\.html"', 'href="case_mumab4d5_vhh_zh.html"'),
    (r'href="case_mumab4d5_cmc\.html"', 'href="case_mumab4d5_cmc_zh.html"'),
    (r'href="case_fentanyl_hapten_vam\.html"', 'href="case_ab278_fentanyl_affinity_maturation.html"')
]

for old, new in replacements:
    text = re.sub(old, new, text)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print("Links updated in Chinese whitepaper.")
