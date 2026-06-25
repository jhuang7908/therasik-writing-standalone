import re

files = [
    ('docs/Therasik_ADA_Database.html', 'ADA'),
    ('docs/Therasik_ADC_Database.html', 'ADC'),
    ('docs/Therasik_Antibody_Guide.html', 'Guide'),
    ('docs/Therasik_Component_Browser.html', 'CAR'),
    ('docs/Therasik_Vaccine_KB.html', 'Vaccine'),
]
for path, name in files:
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    # Find page-header block (everything between opening div and first closing div that ends the block)
    start = c.find('<div class="page-header">')
    if start == -1:
        print(f'=== {name}: NO page-header found ===')
        continue
    end = c.find('</div>', start + 100)
    # Grab the next 600 chars after the opening tag for content
    snippet = c[start:start+800]
    text = re.sub(r'<[^>]+>', '', snippet).strip()
    text = re.sub(r'\s+', ' ', text)
    print(f'=== {name} ===')
    print(text[:500])
    print()
