import re

with open('d:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source/whitepaper_insynbio_en.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if re.search(r'[\u4e00-\u9fa5]', line):
        print(f"Line {i+1}: {line.strip()}")
