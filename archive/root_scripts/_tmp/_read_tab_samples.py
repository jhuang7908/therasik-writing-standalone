"""Read first card from each of the 4 problem tabs + check filter bars."""
path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
content = open(path, encoding='utf-8').read

import re

def get_full_card(html, start_pos):
    depth = 0
    i = start_pos
    while i < len(html):
        od = html.find('<div', i)
        cd = html.find('</div>', i)
        if od == -1 and cd == -1: break
        if od != -1 and (cd == -1 or od < cd):
            depth += 1; i = od + 4
        else:
            depth -= 1; i = cd + 6
            if depth == 0:
                return html[start_pos:i]
    return html[start_pos:start_pos+2000]

grids = {
    'payload':    (448503, 629096),
    'linker':     (629096, 742044),
    'conjugation':(742044, 802945),
    'experiments':(802945, len(content)),
}

for name, (start, end) in grids.items:
    sec = content[start:end]
    print(f"\n{'='*60}")
    print(f"=== {name.upper} — FILTER BAR ===")
    ctrl = sec.find('<div class="ctrl-row"')
    if ctrl >= 0:
        ctrl_end = sec.find('</div>', ctrl) + 6
        print(sec[ctrl:ctrl_end])
    
    print(f"\n=== {name.upper} — FIRST CARD ===")
    card_pos = sec.find('<div class="card"')
    if card_pos >= 0:
        card = get_full_card(sec, card_pos)
        print(card[:2000])
    
    print(f"\n=== {name.upper} — TAB SECTION DESC ===")
    desc_pos = content.find(f'id="panel-{name}"') if name not in ['payload','linker'] else -1
    # for payload, linker use Chinese panel ids
    if name == 'payload':
        desc_pos = content.find('id="panel-\u4e2a\u8f7d\u8377"')  # panel-
    elif name == 'linker':
        desc_pos = content.find('id="panel-\u4e2a\u9223\u63a5\u5b50"')  # panel-
    if desc_pos >= 0:
        print(content[desc_pos:desc_pos+400])
