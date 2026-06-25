"""Insert new linker cards into the database HTML."""

path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Read cards from the fix script
src = open(r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/_fix_linker_additions.py', encoding='utf-8').read()
import re
m = re.search(r"new_linker_cards = '''(.*?)'''", src, re.DOTALL)
if m:
    cards_html = m.group(1)
    marker = '<!-- \u2550\u2550\u2550 CONJUGATION \u2550\u2550\u2550 -->'
    if marker in content:
        content = content.replace(marker, cards_html + '\n\n' + marker)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print('Done. Inserted', len(cards_html), 'chars of new linker cards.')
    else:
        print('ERROR: marker not found')
else:
    print('ERROR: could not extract cards from fix script')
