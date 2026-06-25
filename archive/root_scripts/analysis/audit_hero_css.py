import re

files = [
    ('docs/Therasik_ADA_Database.html', 'ADA'),
    ('docs/Therasik_ADC_Database.html', 'ADC'),
    ('docs/Therasik_Antibody_Guide.html', 'Guide'),
    ('docs/Therasik_Component_Browser.html', 'CAR'),
    ('docs/Therasik_Vaccine_KB.html', 'Vaccine'),
]

props = ['page-header', 'font-family', 'font-size', 'color', 'line-height', 'max-width']

for path, name in files:
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    print(f'=== {name} ===')
    # Extract all .page-header CSS rules
    for m in re.finditer(r'\.page-header[^{]*\{([^}]+)\}', c):
        selector_start = m.start()
        # Get the selector text
        sel_match = re.search(r'(\.page-header[^{]*)\{', c[selector_start:selector_start+100])
        selector = sel_match.group(1).strip() if sel_match else '?'
        rules = m.group(1).strip()
        print(f'  [{selector}]  {rules[:200]}')
    print()
