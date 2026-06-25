"""Fix remaining Chinese option values in ADC and CAR KB pages."""
import os

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite'

FIXES = {
    'Therasik_ADC_Database.html': [
        ('><', '>Hematologic<'),
        ('><', '>Autoimmune<'),
        ('><', '>Neurologic<'),
        ('><', '>Other<'),
        ('><', '>High<'),
        ('><', '>Medium<'),
        # value= attributes too
        ('value=""', 'value="hematologic"'),
        ('value=""', 'value="autoimmune"'),
        ('value=""', 'value="neurologic"'),
        ('value=""', 'value="other"'),
        ('value=""', 'value="high"'),
        ('value=""', 'value="medium"'),
    ],
    'Therasik_Component_Browser.html': [
        ('><', '>Universal<'),
        ('value=""', 'value="universal"'),
    ],
}

SOURCE_DIRS = [
    os.path.join(ROOT, 'therasik-web-source'),
    os.path.join(ROOT, 'docs'),
]

for fname, fixes in FIXES.items:
    for sdir in SOURCE_DIRS:
        fpath = os.path.join(sdir, fname)
        if not os.path.exists(fpath): continue
        txt = open(fpath, encoding='utf-8').read
        n = sum(1 for old, _ in fixes if old in txt)
        for old, new in fixes:
            txt = txt.replace(old, new)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(txt)
        print(f"  [{n} fixes] {os.path.basename(fpath)}")
print("Done.")
