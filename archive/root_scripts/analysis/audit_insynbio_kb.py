import os, re
ZH = re.compile(r'[\u4e00-\u9fff]')
pages = [
    'insynbio-web-source/ada_database.html',
    'insynbio-web-source/adc_database.html',
    'insynbio-web-source/antibody-guide.html',
    'insynbio-web-source/component-browser.html',
]
for p in pages:
    if not os.path.exists(p):
        print(f'MISSING: {p}'); continue
    txt = open(p, encoding='utf-8').read()
    th_zh  = [m for m in re.findall(r'<th[^>]*>([^<]+)</th>', txt) if ZH.search(m)]
    opt_zh = [m for m in re.findall(r'<option[^>]*>([^<]+)</option>', txt) if ZH.search(m)]
    lbl_zh = [m for m in re.findall(r'class="dk"[^>]*>([^<]+)<', txt) if ZH.search(m)]
    uses_ada_json = 'ada_db_data.json' in txt
    print(f'{os.path.basename(p)} | ada_json:{uses_ada_json}')
    print(f'  TH:{th_zh[:4]}')
    print(f'  OPT:{opt_zh[:6]}')
    print(f'  LBL:{lbl_zh[:4]}')
    print()
