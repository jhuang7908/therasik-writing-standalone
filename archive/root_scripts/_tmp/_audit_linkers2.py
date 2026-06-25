import re
path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
content = open(path, encoding='utf-8').read()

# Find linker panel by grid id
p2 = content.find('id="grid\u9223\u63a5\u5b50"')
p3 = content.find('id="gridConj"')
print(f'grid linker: {p2}, gridConj: {p3}')

linker_sec = content[p2:p3]
titles = re.findall(r'<div class="card-title">([^<]+)</div>', linker_sec)
print(f'Total: {len(titles)} linker cards')

no_patent = []
for title in titles:
    marker = f'<div class="card-title">{title}</div>'
    t_pos = linker_sec.find(marker)
    window = linker_sec[t_pos:t_pos+3500]
    has_patent = '\u4e13\u5229' in window or 'patent' in window.lower() or 'US' in window[200:]
    mark = 'OK  ' if has_patent else 'MISS'
    print(f'  {mark}: {title}')
    if not has_patent:
        no_patent.append(title)

print(f'\nMissing patent info: {len(no_patent)} cards')
