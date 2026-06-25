content = open('therasik-web-source/Therasik_ADC_Database.html', encoding='utf-8').read
import re

# Fix Toxicology cc-brief
old = '<div class="cc-brief">NHP is critical if the antibody cross-reacts with monkey antigen. Evaluates on-target off-tumor tox and payload-driven t\u2026</div>'
new = '<div class="cc-brief">: NHP /  (MTD, TK) · : on-target off-tumor  ·  LD₅₀ vs </div>'

if old in content:
    content = content.replace(old, new)
    open('therasik-web-source/Therasik_ADC_Database.html', 'w', encoding='utf-8').write(content)
    print('Fixed Toxicology Tox cc-brief')
else:
    # Try with regex
    m = re.search(r'<div class="cc-brief">NHP is critical[^<]*…[^<]*</div>', content)
    if m:
        content = content.replace(m.group(0), new)
        open('therasik-web-source/Therasik_ADC_Database.html', 'w', encoding='utf-8').write(content)
        print('Fixed Toxicology Tox cc-brief (regex)')
    else:
        print('Not found')
        # Show context
        idx = content.find('Toxicology Tox')
        print(repr(content[idx:idx+200]))
