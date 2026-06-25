import re

path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
content = open(path, encoding='utf-8').read

# Tab sections by grid position
sections = {
    'Payload':  (448466, 629059),
    'Linker':   (629059, 742007),
    'Conjugation': (742007, 802908),
}

for tab_name, (start, end) in sections.items:
    sec = content[start:end]
    titles = re.findall(r'<div class="card-title">([^<]+)</div>', sec)
    print(f'\n=== {tab_name} tab ({len(titles)} cards) ===')
    no_pat = []
    for title in titles:
        marker = f'<div class="card-title">{title}</div>'
        t_pos = sec.find(marker)
        window = sec[t_pos:t_pos+3500]
        # Check for patent section (Chinese or English markers)
        has_pat = ('\u4e13\u5229\u4fe1\u606f' in window or     # 
                   'Patent' in window[300:] or 
                   'US' in window[300:] or
                   'patent' in window[300:].lower or
                   'WO' in window[300:])
        mark = 'OK  ' if has_pat else 'MISS'
        if not has_pat:
            no_pat.append(title)
        print(f'  {mark}: {title}')
    print(f'  → Missing patent: {len(no_pat)} cards')
    if no_pat:
        for t in no_pat:
            print(f'     - {t}')
