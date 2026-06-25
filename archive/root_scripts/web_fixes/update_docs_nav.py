"""Update docs/ folder nav to match therasik-web-source"""
import re, os, shutil

ROOT = 'docs'
SRC = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source'

# Pages that we maintain in both docs/ and web-source
SYNC_FROM_WEB = [
    'therasik_index.html',
    'Therasik_ADA_Database.html',
    'Therasik_ADC_Database.html',
    'Therasik_Antibody_Guide.html',
    'Therasik_Component_Browser.html',
    'Therasik_Vaccine_KB.html',
    'Therasik_OurTech.html',
    'Therasik_Immunogenicity.html',
]

# For service pages, copy from docs/ → web-source (they were updated in docs/)
# Actually the web-source was already updated. Let's just run nav update on docs/ service pages
import sys
sys.path.insert(0, r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite')

PATTERN_6 = re.compile(
    r'\n      <a href="[^"]*#case-studies"></a>'
    r'\n      <a href="[^"]*#about"></a>'
    r'\n      <a href="[^"]*#workflow"></a>'
    r'\n      <a href="[^"]*#contact"></a>'
)
PATTERN_4 = re.compile(
    r'\n    <a href="[^"]*#case-studies"></a>'
    r'\n    <a href="[^"]*#about"></a>'
    r'\n    <a href="[^"]*#workflow"></a>'
    r'\n    <a href="[^"]*#contact"></a>'
)

# Load the new nav blocks from update_nav_about.py
exec(open(r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\update_nav_about.py').read.split('# ══════════════════════════════════════════════════════════════════\n# PROCESS FILES')[0])

changed = []
for fname in sorted(os.listdir(ROOT)):
    if not fname.endswith('.html'):
        continue
    path = os.path.join(ROOT, fname)
    orig = open(path, encoding='utf-8').read
    c = orig

    if PATTERN_4.search(c):
        c = PATTERN_4.sub(NEW_NAV_4, c)
    elif PATTERN_6.search(c):
        c = PATTERN_6.sub(NEW_NAV_6, c)

    # About section for therasik index
    if fname == 'therasik_index.html' and OLD_ABOUT in c:
        c = c.replace(OLD_ABOUT, NEW_ABOUT, 1)

    if c != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        changed.append(fname)
        print(f'✓ docs/{fname}')

print(f'\n{len(changed)} docs files updated.')
