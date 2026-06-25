"""Translate ADC payload mechanism names to English."""
import os, re

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite'

# These are payload/mechanism dropdown option text values
MECH_MAP = {
    'DNA ':             'DNA Damaging Agent',
    'RNA  II  Inhibitor': 'RNA Pol II Inhibitor',
    'RNA  II Inhibitor':  'RNA Pol II Inhibitor',
    ' Agonist':        'Immunostimulatory Agonist',
    ' Inhibitor':        'Spliceosome Inhibitor',
    ' Inhibitor':      'Tubulin Inhibitor',
    ' I  Inhibitor': 'Topoisomerase I Inhibitor',
    ' I Inhibitor':  'Topoisomerase I Inhibitor',
    ' II Inhibitor': 'Topoisomerase II Inhibitor',
    'DNA ':              'DNA Alkylating Agent',
    'MMAE ':           'MMAE (Tubulin)',
    '':            'Tubulin Polymerization',
    'RNA ':              'RNA Polymerase',
    '':              'Protein Synthesis',
    '':                'Apoptosis',
    '':                'Immune Activation',
}

SOURCE_DIRS = [
    os.path.join(ROOT, 'therasik-web-source'),
    os.path.join(ROOT, 'docs'),
]

for sdir in SOURCE_DIRS:
    fpath = os.path.join(sdir, 'Therasik_ADC_Database.html')
    if not os.path.exists(fpath): continue
    txt = open(fpath, encoding='utf-8').read
    n = 0
    for zh, en in MECH_MAP.items:
        if zh in txt:
            txt = txt.replace(zh, en)
            n += 1
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(txt)
    print(f"  [{n}] {os.path.basename(fpath)}")

# Final check: print any remaining ZH in ADC options
import re as _re
ZH = _re.compile(r'[\u4e00-\u9fff]')
for sdir in SOURCE_DIRS:
    fpath = os.path.join(sdir, 'Therasik_ADC_Database.html')
    if not os.path.exists(fpath): continue
    txt = open(fpath, encoding='utf-8').read
    opts = [m for m in _re.findall(r'<option[^>]*>([^<]+)</option>', txt) if ZH.search(m)]
    print(f"  Remaining ZH opts: {opts}")
