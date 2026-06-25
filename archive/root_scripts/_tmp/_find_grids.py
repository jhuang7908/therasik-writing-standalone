import re
content = open(r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html', encoding='utf-8').read()
grids = [(m.start(), m.group()) for m in re.finditer(r'id="grid[^"]*"', content)]
for pos, g in grids:
    print(pos, repr(g))
