import re

with open('d:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source/whitepaper_insynbio_en.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if re.search(r'[^\x00-\x7F\u4e00-\u9fa5\u3000-\u303F\uFF00-\uFFEF\u2000-\u206F]', line):
        print(f"Line {i+1}: {line.strip()}")
