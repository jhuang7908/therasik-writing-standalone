with open("docs/Therasik_Antibody_Page.html","r",encoding="utf-8") as f:
    c = f.read
import re
for m in re.finditer('', c):
    start = max(0, m.start-80)
    end = min(len(c), m.end+80)
    print(repr(c[start:end]))
    print
