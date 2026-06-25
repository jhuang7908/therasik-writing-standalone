import re
content = open('therasik-web-source/Therasik_ADC_Database.html', encoding='utf-8').read()
for m in re.finditer(r'<div class="cc-brief">[^<]*…[^<]*</div>', content):
    title_m = list(re.finditer(r'<div class="card-title">([^<]+)</div>', content[:m.start()]))
    title = title_m[-1].group(1) if title_m else 'Unknown'
    print(f'Title: {title}')
    print(f'Brief: {m.group(0)[:150]}')
