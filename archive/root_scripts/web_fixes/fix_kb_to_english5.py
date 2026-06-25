"""Final batch: translate all remaining Chinese ADC filter option labels."""
import os, re

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite'

FIXES = [
    ('><',  '>Radionuclide<'),
    ('><',  '>Protein Toxin<'),
    ('><',      '>Cleavable<'),
    ('><',        '>Very High<'),
    ('><',        '>Moderate<'),
    ('value=""', 'value="radionuclide"'),
    ('value=""', 'value="protein_toxin"'),
    ('value=""',     'value="cleavable"'),
    ('value=""',       'value="very_high"'),
    ('value=""',       'value="moderate"'),
]

SOURCE_DIRS = [
    os.path.join(ROOT, 'therasik-web-source'),
    os.path.join(ROOT, 'docs'),
]

ZH = re.compile(r'[\u4e00-\u9fff]')

for sdir in SOURCE_DIRS:
    fpath = os.path.join(sdir, 'Therasik_ADC_Database.html')
    if not os.path.exists(fpath): continue
    txt = open(fpath, encoding='utf-8').read
    n = sum(1 for old,_ in FIXES if old in txt)
    for old, new in FIXES:
        txt = txt.replace(old, new)
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(txt)
    # verify
    opts = [m for m in re.findall(r'<option[^>]*>([^<]+)</option>', txt) if ZH.search(m)]
    print(f"  [{n} fixed] {os.path.basename(fpath)} — remaining ZH: {opts}")
