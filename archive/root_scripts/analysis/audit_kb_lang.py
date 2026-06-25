import os, re

pages = [
    'therasik-web-source/Therasik_ADC_Database.html',
    'therasik-web-source/Therasik_Component_Browser.html',
    'therasik-web-source/Therasik_Vaccine_KB.html',
    'therasik-web-source/Therasik_Antibody_Guide.html',
    'therasik-web-source/Therasik_ADA_Database.html',
]

ZH = re.compile(r'[\u4e00-\u9fff]')

for p in pages:
    if not os.path.exists(p): continue
    txt = open(p, encoding='utf-8').read()
    th_zh  = [m for m in re.findall(r'<th[^>]*>([^<]+)</th>', txt) if ZH.search(m)]
    opt_zh = [m for m in re.findall(r'<option[^>]*>([^<]+)</option>', txt) if ZH.search(m)]
    h3_zh  = [m for m in re.findall(r'<h3[^>]*>([^<]+)</h3>', txt) if ZH.search(m)]
    lbl_zh = [m for m in re.findall(r'class="dk"[^>]*>([^<]+)<', txt) if ZH.search(m)]
    print(f'{os.path.basename(p)}:')
    print(f'  TH headers (ZH): {th_zh[:8]}')
    print(f'  Options  (ZH): {opt_zh[:6]}')
    print(f'  H3 sections (ZH): {h3_zh[:4]}')
    print(f'  .dk labels  (ZH): {lbl_zh[:6]}')
    print()
