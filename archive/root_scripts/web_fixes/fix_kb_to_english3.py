"""Fix last remaining Chinese in ADC filter options."""
import os

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite'

FIXES = {
    'Therasik_ADC_Database.html': [
        ('><', '>Low<'),
        ('value=""', 'value="low"'),
        ('All ', 'All Mechanisms'),
        ('Bcl-xL ', 'Bcl-xL Inhibitor'),
        # any remaining Chinese mechanism names
        ('', ' Inhibitor'),
        ('', ' Agonist'),
        ('', ' Binder'),
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
        n = 0
        for old, new in fixes:
            if old in txt:
                txt = txt.replace(old, new)
                n += 1
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(txt)
        print(f"  [{n}] {os.path.basename(fpath)}")
print("Done.")
