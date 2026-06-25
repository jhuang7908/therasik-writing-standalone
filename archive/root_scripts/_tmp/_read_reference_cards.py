"""Read full first card from Programs and Antigens as reference, plus full CSS."""
path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
content = open(path, encoding='utf-8').read()

# Read CSS
css_start = content.find('<style>')
css_end = content.find('</style>')
css = content[css_start:css_end+8]
print("=== CSS (first 6000 chars) ===")
print(css[:6000])

print("\n\n=== FULL PROGRAMS CARD 1 ===")
sec = content[21625:199611]
import re
cards = [m.start() for m in re.finditer(r'<div class="card"', sec)]
if cards:
    # Get first card — find its end by counting div depth
    start = cards[0]
    depth = 0
    i = start
    while i < len(sec):
        od = sec.find('<div', i)
        cd = sec.find('</div>', i)
        if od == -1 and cd == -1: break
        if od != -1 and (cd == -1 or od < cd):
            depth += 1; i = od + 4
        else:
            depth -= 1; i = cd + 6
            if depth == 0:
                print(sec[start:i])
                break

print("\n\n=== FULL ANTIGENS CARD 1 ===")
sec2 = content[199611:448503]
cards2 = [m.start() for m in re.finditer(r'<div class="card"', sec2)]
if cards2:
    start = cards2[0]
    depth = 0
    i = start
    while i < len(sec2):
        od = sec2.find('<div', i)
        cd = sec2.find('</div>', i)
        if od == -1 and cd == -1: break
        if od != -1 and (cd == -1 or od < cd):
            depth += 1; i = od + 4
        else:
            depth -= 1; i = cd + 6
            if depth == 0:
                print(sec2[start:i])
                break
